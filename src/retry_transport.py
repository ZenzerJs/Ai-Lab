"""Resilient HTTP Retry Transport Module.

Provides an HTTP retry transport supporting exponential backoff, full jitter,
configurable status code and exception filters, Retry-After header parsing,
and pluggable execution adapters.
"""

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
import enum
import http.client
import random
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
import urllib.error
import urllib.request


class JitterStrategy(str, enum.Enum):
    """Jitter strategies for backoff delay calculation."""

    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


DEFAULT_RETRY_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
)


@dataclass
class RetryConfig:
    """Configuration parameters for retry transport policies.

    Attributes:
        max_retries: Maximum number of retry attempts (0 means only 1 initial try).
        base_delay: Initial base backoff delay in seconds.
        max_delay: Upper bound ceiling for any single backoff delay in seconds.
        backoff_factor: Multiplier for exponential backoff.
        jitter: Jitter strategy to apply (defaults to JitterStrategy.FULL).
        retry_status_codes: Set of HTTP status codes eligible for retry.
        retry_exceptions: Tuple of exception types eligible for retry.
        respect_retry_after: Whether to parse and respect the HTTP Retry-After header.
        raise_on_status: Whether to raise MaxRetriesExceededError if retry attempts
            are exhausted with a retryable status code, instead of returning the response.
    """

    max_retries: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: JitterStrategy = JitterStrategy.FULL
    retry_status_codes: Set[int] = field(
        default_factory=lambda: set(DEFAULT_RETRY_STATUS_CODES)
    )
    retry_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRY_EXCEPTIONS
    respect_retry_after: bool = True
    raise_on_status: bool = False

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.base_delay <= 0:
            raise ValueError(f"base_delay must be > 0, got {self.base_delay}")
        if self.max_delay < self.base_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= base_delay ({self.base_delay})"
            )
        if self.backoff_factor <= 1.0:
            raise ValueError(f"backoff_factor must be > 1.0, got {self.backoff_factor}")


@dataclass
class HTTPResponse:
    """Normalized HTTP response container.

    Attributes:
        status_code: HTTP status code integer.
        headers: Case-insensitive dictionary of response headers.
        body: Raw response content bytes.
        url: Request URL string.
    """

    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    url: str = ""

    def get_header(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Case-insensitively lookup a header value."""
        target = key.lower()
        for k, v in self.headers.items():
            if k.lower() == target:
                return v
        return default


@dataclass
class RetryAttemptRecord:
    """Record of an individual attempt execution."""

    attempt: int
    status_code: Optional[int] = None
    error: Optional[str] = None
    delay_applied: float = 0.0


@dataclass
class RetryTelemetry:
    """Telemetry and audit ledger for a sequence of retry attempts."""

    total_attempts: int = 0
    total_delay_seconds: float = 0.0
    history: List[RetryAttemptRecord] = field(default_factory=list)

    def record_attempt(
        self,
        attempt: int,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
        delay_applied: float = 0.0,
    ) -> None:
        self.total_attempts = attempt + 1
        self.total_delay_seconds += delay_applied
        self.history.append(
            RetryAttemptRecord(
                attempt=attempt,
                status_code=status_code,
                error=error,
                delay_applied=delay_applied,
            )
        )


class RetryError(Exception):
    """Base exception for retry errors."""


class MaxRetriesExceededError(RetryError):
    """Raised when maximum retry attempts are exhausted without success."""

    def __init__(
        self,
        message: str,
        last_response: Optional[HTTPResponse] = None,
        last_exception: Optional[Exception] = None,
        telemetry: Optional[RetryTelemetry] = None,
    ) -> None:
        super().__init__(message)
        self.last_response = last_response
        self.last_exception = last_exception
        self.telemetry = telemetry


def parse_retry_after(header_value: Optional[str], current_time: Optional[float] = None) -> Optional[float]:
    """Parse HTTP Retry-After header as integer/float seconds or HTTP date.

    Args:
        header_value: Raw Retry-After header string.
        current_time: Epoch timestamp used to calculate delta for HTTP-date format.

    Returns:
        Delay in seconds if parseable and positive, else None.
    """
    if not header_value:
        return None

    clean_val = header_value.strip()

    # Try integer/float seconds representation
    try:
        seconds = float(clean_val)
        return max(0.0, seconds)
    except ValueError:
        pass

    # Try IMF-fixdate / RFC 2822 / RFC 850 date representation
    try:
        dt = parsedate_to_datetime(clean_val)
        target_ts = dt.timestamp()
        now = current_time if current_time is not None else time.time()
        delta = target_ts - now
        return max(0.0, delta)
    except Exception:
        return None


class RetryTransport:
    """Resilient HTTP transport wrapper providing backoff, jitter, and retry filtering."""

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        random_fn: Optional[Callable[[float, float], float]] = None,
        on_retry: Optional[Callable[[int, Union[HTTPResponse, Exception], float], None]] = None,
    ) -> None:
        """Initialize the RetryTransport.

        Args:
            config: Retry policy configuration.
            sleeper: Pluggable sleep function (e.g. for mock time travel).
            random_fn: Pluggable uniform float generator `(low, high) -> float`.
            on_retry: Callback invoked before each backoff sleep with (attempt, cause, delay).
        """
        self.config: RetryConfig = config or RetryConfig()
        self.sleeper: Callable[[float], None] = sleeper or time.sleep
        self.random_fn: Callable[[float, float], float] = random_fn or random.uniform
        self.on_retry: Optional[Callable[[int, Union[HTTPResponse, Exception], float], None]] = on_retry
        self._last_decorrelated_delay: float = self.config.base_delay

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate the unjittered exponential backoff ceiling for a zero-indexed attempt.

        Formula: min(max_delay, base_delay * (backoff_factor ** attempt))
        """
        raw_backoff = self.config.base_delay * (self.config.backoff_factor ** attempt)
        return min(self.config.max_delay, raw_backoff)

    def calculate_delay(
        self,
        attempt: int,
        retry_after: Optional[float] = None,
    ) -> float:
        """Calculate the final sleep delay considering strategy and Retry-After header.

        Args:
            attempt: The retry attempt counter (0 for 1st retry, 1 for 2nd retry, etc.).
            retry_after: Optional delay parsed from Retry-After response header.

        Returns:
            Calculated sleep duration in seconds, clamped to config.max_delay.
        """
        capped_exp = self.calculate_backoff(attempt)

        if self.config.jitter == JitterStrategy.NONE:
            delay = capped_exp
        elif self.config.jitter == JitterStrategy.FULL:
            # Full Jitter: Sleep = uniform(0, min(max_delay, base_delay * 2^attempt))
            delay = self.random_fn(0.0, capped_exp)
        elif self.config.jitter == JitterStrategy.EQUAL:
            # Equal Jitter: Sleep = (delay / 2) + uniform(0, delay / 2)
            half = capped_exp / 2.0
            delay = half + self.random_fn(0.0, half)
        elif self.config.jitter == JitterStrategy.DECORRELATED:
            # Decorrelated Jitter: Sleep = min(max_delay, uniform(base_delay, prev_delay * 3))
            high = max(self.config.base_delay, self._last_decorrelated_delay * 3.0)
            delay = min(self.config.max_delay, self.random_fn(self.config.base_delay, high))
            self._last_decorrelated_delay = delay
        else:
            delay = capped_exp

        # If Retry-After header was specified and respected, prioritize it
        if self.config.respect_retry_after and retry_after is not None:
            delay = max(delay, retry_after)

        return min(self.config.max_delay, max(0.0, delay))

    def is_retryable_status(self, status_code: int) -> bool:
        """Check if an HTTP status code is eligible for retry."""
        return status_code in self.config.retry_status_codes

    def is_retryable_exception(self, exc: Exception) -> bool:
        """Check if an exception is eligible for retry."""
        return isinstance(exc, self.config.retry_exceptions)

    def execute(
        self,
        request_fn: Callable[[], HTTPResponse],
    ) -> Tuple[HTTPResponse, RetryTelemetry]:
        """Execute a request callable with resilience retry policies.

        Args:
            request_fn: Zero-argument callable returning an HTTPResponse.

        Returns:
            Tuple of (HTTPResponse, RetryTelemetry).

        Raises:
            MaxRetriesExceededError: When retries are exhausted and configured to raise.
            Exception: Re-raises the last non-retryable or final exhausted exception.
        """
        telemetry = RetryTelemetry()
        last_response: Optional[HTTPResponse] = None
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            is_final_attempt = attempt >= self.config.max_retries

            try:
                response = request_fn()
                last_response = response

                # Check if status code indicates retry is needed
                if self.is_retryable_status(response.status_code):
                    if is_final_attempt:
                        telemetry.record_attempt(
                            attempt=attempt,
                            status_code=response.status_code,
                            delay_applied=0.0,
                        )
                        if self.config.raise_on_status:
                            raise MaxRetriesExceededError(
                                f"Max retries ({self.config.max_retries}) exhausted on HTTP {response.status_code}",
                                last_response=response,
                                telemetry=telemetry,
                            )
                        return response, telemetry

                    # Extract Retry-After if available
                    retry_after: Optional[float] = None
                    if self.config.respect_retry_after:
                        retry_after = parse_retry_after(response.get_header("Retry-After"))

                    delay = self.calculate_delay(attempt, retry_after=retry_after)
                    telemetry.record_attempt(
                        attempt=attempt,
                        status_code=response.status_code,
                        delay_applied=delay,
                    )

                    if self.on_retry:
                        self.on_retry(attempt, response, delay)

                    self.sleeper(delay)
                    continue

                # Successful or non-retryable status
                telemetry.record_attempt(
                    attempt=attempt,
                    status_code=response.status_code,
                    delay_applied=0.0,
                )
                return response, telemetry

            except Exception as exc:
                # If the exception itself is MaxRetriesExceededError from nested raise_on_status, re-raise
                if isinstance(exc, MaxRetriesExceededError):
                    raise

                last_exception = exc

                # Check if exception is retryable
                if not self.is_retryable_exception(exc) or is_final_attempt:
                    telemetry.record_attempt(
                        attempt=attempt,
                        error=f"{type(exc).__name__}: {str(exc)}",
                        delay_applied=0.0,
                    )
                    raise MaxRetriesExceededError(
                        f"Retry failed after {attempt} retries: {str(exc)}",
                        last_exception=exc,
                        telemetry=telemetry,
                    ) from exc

                delay = self.calculate_delay(attempt)
                telemetry.record_attempt(
                    attempt=attempt,
                    error=f"{type(exc).__name__}: {str(exc)}",
                    delay_applied=delay,
                )

                if self.on_retry:
                    self.on_retry(attempt, exc, delay)

                self.sleeper(delay)

        # Fallback safeguard
        if last_response is not None:
            return last_response, telemetry
        raise MaxRetriesExceededError(
            "Max retries exceeded without result",
            last_response=last_response,
            last_exception=last_exception,
            telemetry=telemetry,
        )

    def send(
        self,
        request: Union[urllib.request.Request, str],
        timeout: Optional[float] = None,
        **urlopen_kwargs: Any,
    ) -> Tuple[HTTPResponse, RetryTelemetry]:
        """Send an HTTP request via standard library urllib with resilience retry handling.

        Args:
            request: URL string or urllib.request.Request object.
            timeout: Optional socket timeout in seconds.
            **urlopen_kwargs: Additional arguments passed to urllib.request.urlopen.

        Returns:
            Tuple of (HTTPResponse, RetryTelemetry).
        """
        def _request_adapter() -> HTTPResponse:
            try:
                req_obj = request
                if isinstance(req_obj, str):
                    req_obj = urllib.request.Request(req_obj)

                with urllib.request.urlopen(req_obj, timeout=timeout, **urlopen_kwargs) as resp:
                    headers = {k: v for k, v in resp.headers.items()}
                    body = resp.read()
                    return HTTPResponse(
                        status_code=resp.status,
                        headers=headers,
                        body=body,
                        url=resp.geturl(),
                    )
            except urllib.error.HTTPError as http_err:
                headers = {k: v for k, v in http_err.headers.items()} if http_err.headers else {}
                body = http_err.read() if hasattr(http_err, "read") else b""
                return HTTPResponse(
                    status_code=http_err.code,
                    headers=headers,
                    body=body,
                    url=http_err.geturl() if hasattr(http_err, "geturl") else "",
                )

        return self.execute(_request_adapter)
