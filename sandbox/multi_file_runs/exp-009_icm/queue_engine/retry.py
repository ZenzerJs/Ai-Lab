"""Retry Policy & Exponential Backoff."""
import math
import random
from queue_engine.schema import Job, JobState


class RetryPolicy:
    """Handles job retry scheduling with randomized jitter and dead-letter routing."""

    def __init__(self, max_attempts: int = 3, base_seconds: float = 1.0) -> None:
        self.max_attempts = max_attempts
        self.base_seconds = base_seconds

    def compute_delay(self, attempt: int, jitter: bool = True) -> float:
        """
        Compute backoff delay with randomized jitter to prevent thundering herd.
        """
        raw_delay = self.base_seconds * math.pow(2.0, max(0, attempt - 1))
        if not jitter:
            return raw_delay
        # Full jitter between 0.5x and 1.5x of raw delay
        return raw_delay * (0.5 + random.random())

    def evaluate_failure(self, job: Job, error: str) -> JobState:
        """Route job to RETRYING or DEAD_LETTER based on attempt threshold."""
        job.last_error = error
        if job.attempts >= job.max_attempts:
            job.state = JobState.DEAD_LETTER
        else:
            job.state = JobState.RETRYING
        return job.state
