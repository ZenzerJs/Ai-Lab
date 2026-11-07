"""Retry Policy & Exponential Backoff."""
import math
import random
from typing import Optional
from queue_engine.schema import Job, JobState


class RetryPolicy:
    """Handles job retry scheduling and dead-letter routing."""

    def __init__(self, max_attempts: int = 3, base_seconds: float = 1.0, jitter: bool = True) -> None:
        self.max_attempts = max_attempts
        self.base_seconds = base_seconds
        self.jitter = jitter

    def compute_delay(self, attempt: int, jitter: Optional[bool] = None) -> float:
        """Compute backoff delay with randomized jitter to prevent thundering herds."""
        use_jitter = self.jitter if jitter is None else jitter
        backoff = self.base_seconds * math.pow(2.0, max(0, attempt - 1))
        if use_jitter:
            return random.uniform(0.5 * backoff, 1.5 * backoff)
        return backoff

    def evaluate_failure(self, job: Job, error: str) -> JobState:
        """Route job to RETRYING or DEAD_LETTER based on attempt threshold."""
        job.last_error = error
        if job.attempts >= job.max_attempts:
            job.state = JobState.DEAD_LETTER
        else:
            job.state = JobState.RETRYING
        return job.state
