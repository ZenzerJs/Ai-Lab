"""Unit and Mock Tests for Resilient HTTP Retry Transport.

All tests utilize virtual time travel, mock callables, and simulated urllib responses.
No live external network requests are executed.
"""

from datetime import datetime, timezone
import email.utils
import http.client
import math
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

from src.retry_transport import (
    DEFAULT_RETRY_STATUS_CODES,
    HTTPResponse,
    JitterStrategy,
    MaxRetriesExceededError,
    RetryConfig,
    RetryTransport,
    parse_retry_after,
)


class MockSleeper:
    """Virtual sleep recorder avoiding wall-clock delays."""

    def __init__(self) -> None:
        self.slept_intervals: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept_intervals.append(seconds)

    @property
    def total_slept(self) -> float:
        return sum(self.slept_intervals)


class TestRetryConfig(unittest.TestCase):
    """Test validation and default parameters of RetryConfig."""

    def test_default_config(self) -> None:
        config = RetryConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.base_delay, 0.5)
        self.assertEqual(config.max_delay, 30.0)
        self.assertEqual(config.backoff_factor, 2.0)
        self.assertEqual(config.jitter, JitterStrategy.FULL)
        self.assertTrue({429, 500, 502, 503, 504}.issubset(config.retry_status_codes))
        self.assertTrue(config.respect_retry_after)
        self.assertFalse(config.raise_on_status)

    def test_invalid_parameters_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            RetryConfig(max_retries=-1)
        with self.assertRaises(ValueError):
            RetryConfig(base_delay=0)
        with self.assertRaises(ValueError):
            RetryConfig(base_delay=10.0, max_delay=5.0)
        with self.assertRaises(ValueError):
            RetryConfig(backoff_factor=1.0)


class TestBackoffAndJitter(unittest.TestCase):
    """Test exponential backoff calculations and jitter distributions."""

    def test_exponential_backoff_un_jittered(self) -> None:
        config = RetryConfig(
            max_retries=5,
            base_delay=1.0,
            max_delay=16.0,
            backoff_factor=2.0,
            jitter=JitterStrategy.NONE,
        )
        transport = RetryTransport(config=config)

        # attempt 0: 1.0 * (2^0) = 1.0
        # attempt 1: 1.0 * (2^1) = 2.0
        # attempt 2: 1.0 * (2^2) = 4.0
        # attempt 3: 1.0 * (2^3) = 8.0
        # attempt 4: 1.0 * (2^4) = 16.0
        # attempt 5: 1.0 * (2^5) = 32.0 -> clamped to max_delay 16.0
        expected = [1.0, 2.0, 4.0, 8.0, 16.0, 16.0]
        for attempt, exp_val in enumerate(expected):
            self.assertEqual(transport.calculate_delay(attempt), exp_val)

    def test_full_jitter_bounds(self) -> None:
        config = RetryConfig(
            max_retries=4,
            base_delay=0.5,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=JitterStrategy.FULL,
        )
        transport = RetryTransport(config=config)

        # Full jitter delay must always be in [0, min(max_delay, base * factor^attempt)]
        for attempt in range(6):
            cap = min(10.0, 0.5 * (2.0 ** attempt))
            for _ in range(50):
                delay = transport.calculate_delay(attempt)
                self.assertGreaterEqual(delay, 0.0)
                self.assertLessEqual(delay, cap)

    def test_equal_jitter_bounds(self) -> None:
        config = RetryConfig(
            base_delay=1.0,
            max_delay=20.0,
            backoff_factor=2.0,
            jitter=JitterStrategy.EQUAL,
        )
        transport = RetryTransport(config=config)

        # Equal jitter: half <= delay <= cap
        for attempt in range(4):
            cap = 1.0 * (2.0 ** attempt)
            half = cap / 2.0
            for _ in range(25):
                delay = transport.calculate_delay(attempt)
                self.assertGreaterEqual(delay, half)
                self.assertLessEqual(delay, cap)

    def test_decorrelated_jitter(self) -> None:
        config = RetryConfig(
            base_delay=1.0,
            max_delay=20.0,
            jitter=JitterStrategy.DECORRELATED,
        )
        transport = RetryTransport(config=config)

        for attempt in range(5):
            delay = transport.calculate_delay(attempt)
            self.assertGreaterEqual(delay, 1.0)
            self.assertLessEqual(delay, 20.0)


class TestRetryAfterHeaderParsing(unittest.TestCase):
    """Test parsing of Retry-After header with seconds and HTTP-date formats."""

    def test_parse_seconds(self) -> None:
        self.assertEqual(parse_retry_after("120"), 120.0)
        self.assertEqual(parse_retry_after("0"), 0.0)
        self.assertEqual(parse_retry_after("-5"), 0.0)
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after(""))

    def test_parse_http_date(self) -> None:
        now = 1700000000.0
        dt = datetime.fromtimestamp(now + 45.0, tz=timezone.utc)
        date_str = email.utils.format_datetime(dt)

        parsed = parse_retry_after(date_str, current_time=now)
        self.assertIsNotNone(parsed)
        self.assertAlmostEqual(parsed, 45.0, places=1)


class TestRetryTransportExecution(unittest.TestCase):
    """Test retry execution flows with various simulated HTTP responses and errors."""

    def test_immediate_success(self) -> None:
        sleeper = MockSleeper()
        transport = RetryTransport(
            config=RetryConfig(max_retries=3),
            sleeper=sleeper,
        )

        mock_req = MagicMock(return_value=HTTPResponse(status_code=200, body=b"OK"))
        resp, telemetry = transport.execute(mock_req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(len(sleeper.slept_intervals), 0)
        self.assertEqual(telemetry.total_attempts, 1)
        self.assertEqual(telemetry.total_delay_seconds, 0.0)

    def test_retry_on_status_503_then_success(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            jitter=JitterStrategy.NONE,
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        mock_req = MagicMock(
            side_effect=[
                HTTPResponse(status_code=503, body=b"Unavailable"),
                HTTPResponse(status_code=503, body=b"Unavailable"),
                HTTPResponse(status_code=200, body=b"Success"),
            ]
        )

        resp, telemetry = transport.execute(mock_req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_req.call_count, 3)
        self.assertEqual(sleeper.slept_intervals, [1.0, 2.0])
        self.assertEqual(telemetry.total_attempts, 3)

    def test_non_retryable_status_code_no_retry(self) -> None:
        sleeper = MockSleeper()
        transport = RetryTransport(
            config=RetryConfig(max_retries=3),
            sleeper=sleeper,
        )

        mock_req = MagicMock(return_value=HTTPResponse(status_code=404, body=b"Not Found"))
        resp, telemetry = transport.execute(mock_req)

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(len(sleeper.slept_intervals), 0)

    def test_retry_exhaustion_returns_last_response_when_raise_on_status_false(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=2,
            base_delay=0.1,
            jitter=JitterStrategy.NONE,
            raise_on_status=False,
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        mock_req = MagicMock(return_value=HTTPResponse(status_code=500, body=b"Error"))
        resp, telemetry = transport.execute(mock_req)

        self.assertEqual(resp.status_code, 500)
        # initial try + 2 retries = 3 calls
        self.assertEqual(mock_req.call_count, 3)
        self.assertEqual(len(sleeper.slept_intervals), 2)
        self.assertEqual(telemetry.total_attempts, 3)

    def test_retry_exhaustion_raises_when_raise_on_status_true(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=2,
            base_delay=0.1,
            jitter=JitterStrategy.NONE,
            raise_on_status=True,
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        mock_req = MagicMock(return_value=HTTPResponse(status_code=502, body=b"Bad Gateway"))
        with self.assertRaises(MaxRetriesExceededError) as ctx:
            transport.execute(mock_req)

        self.assertEqual(mock_req.call_count, 3)
        self.assertIn("502", str(ctx.exception))
        self.assertEqual(ctx.exception.last_response.status_code, 502)

    def test_retry_on_network_exception_then_success(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=3,
            base_delay=0.2,
            jitter=JitterStrategy.NONE,
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        mock_req = MagicMock(
            side_effect=[
                urllib.error.URLError("Connection reset"),
                TimeoutError("Request timed out"),
                HTTPResponse(status_code=200, body=b"Recovered"),
            ]
        )

        resp, telemetry = transport.execute(mock_req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_req.call_count, 3)
        self.assertEqual(len(sleeper.slept_intervals), 2)
        self.assertEqual(telemetry.history[0].error, "URLError: <urlopen error Connection reset>")

    def test_non_retryable_exception_raises_immediately(self) -> None:
        sleeper = MockSleeper()
        transport = RetryTransport(
            config=RetryConfig(max_retries=3),
            sleeper=sleeper,
        )

        mock_req = MagicMock(side_effect=ValueError("Invalid argument"))
        with self.assertRaises(MaxRetriesExceededError) as ctx:
            transport.execute(mock_req)

        self.assertEqual(mock_req.call_count, 1)
        self.assertIsInstance(ctx.exception.last_exception, ValueError)
        self.assertEqual(len(sleeper.slept_intervals), 0)

    def test_respect_retry_after_header(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=2,
            base_delay=0.5,
            jitter=JitterStrategy.NONE,
            respect_retry_after=True,
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        mock_req = MagicMock(
            side_effect=[
                HTTPResponse(status_code=429, headers={"Retry-After": "5"}),
                HTTPResponse(status_code=200, body=b"Done"),
            ]
        )

        resp, _ = transport.execute(mock_req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_req.call_count, 2)
        self.assertEqual(sleeper.slept_intervals, [5.0])

    def test_on_retry_callback(self) -> None:
        sleeper = MockSleeper()
        events = []

        def callback(attempt: int, cause: object, delay: float) -> None:
            events.append((attempt, getattr(cause, "status_code", str(cause)), delay))

        transport = RetryTransport(
            config=RetryConfig(max_retries=2, base_delay=1.0, jitter=JitterStrategy.NONE),
            sleeper=sleeper,
            on_retry=callback,
        )

        mock_req = MagicMock(
            side_effect=[
                HTTPResponse(status_code=503),
                HTTPResponse(status_code=200),
            ]
        )

        transport.execute(mock_req)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], (0, 503, 1.0))

    def test_custom_retryable_status_codes(self) -> None:
        sleeper = MockSleeper()
        config = RetryConfig(
            max_retries=2,
            base_delay=0.1,
            jitter=JitterStrategy.NONE,
            retry_status_codes={418, 503},  # only 418 and 503
        )
        transport = RetryTransport(config=config, sleeper=sleeper)

        # 500 should NOT be retried under this custom configuration
        mock_req = MagicMock(return_value=HTTPResponse(status_code=500))
        resp, _ = transport.execute(mock_req)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(mock_req.call_count, 1)

        # 418 SHOULD be retried
        mock_req2 = MagicMock(
            side_effect=[
                HTTPResponse(status_code=418),
                HTTPResponse(status_code=200),
            ]
        )
        resp2, _ = transport.execute(mock_req2)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(mock_req2.call_count, 2)


class TestSendUrllibAdapter(unittest.TestCase):
    """Test send method with urllib mock responses."""

    @patch("urllib.request.urlopen")
    def test_send_success(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.geturl.return_value = "https://api.example.com/data"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        transport = RetryTransport()
        resp, telemetry = transport.send("https://api.example.com/data")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, b'{"status": "ok"}')
        self.assertEqual(telemetry.total_attempts, 1)

    @patch("urllib.request.urlopen")
    def test_send_http_error_retry(self, mock_urlopen: MagicMock) -> None:
        sleeper = MockSleeper()
        transport = RetryTransport(
            config=RetryConfig(max_retries=2, base_delay=0.1, jitter=JitterStrategy.NONE),
            sleeper=sleeper,
        )

        mock_http_err = urllib.error.HTTPError(
            url="https://api.example.com/fail",
            code=503,
            msg="Unavailable",
            hdrs={"Retry-After": "2"},  # type: ignore
            fp=None,
        )

        success_resp = MagicMock()
        success_resp.status = 200
        success_resp.headers = {}
        success_resp.read.return_value = b"Recovered"
        success_resp.geturl.return_value = "https://api.example.com/fail"
        success_resp.__enter__.return_value = success_resp

        mock_urlopen.side_effect = [mock_http_err, success_resp]

        resp, telemetry = transport.send("https://api.example.com/fail")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, b"Recovered")
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(sleeper.slept_intervals, [2.0])


if __name__ == "__main__":
    unittest.main()
