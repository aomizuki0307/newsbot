"""Retry utilities shared across network-bound modules."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

import requests
from tenacity import (
    after_log,
    before_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


def _has_retryable_status(exception: BaseException) -> bool:
    """Return True when an exception exposes an HTTP status worth retrying."""
    status_code = getattr(exception, "status_code", None)
    if status_code and (status_code >= 500 or status_code in RETRYABLE_STATUS_CODES):
        return True

    response = getattr(exception, "response", None)
    if response is not None:
        code = getattr(response, "status_code", None)
        if code and (code >= 500 or code in RETRYABLE_STATUS_CODES):
            return True

    return False


def _should_retry(exception: BaseException) -> bool:
    """Determine whether a given exception warrants a retry."""
    if isinstance(exception, (asyncio.TimeoutError, TimeoutError)):
        return True

    if isinstance(
        exception,
        (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        ),
    ):
        return True

    if isinstance(exception, requests.exceptions.RequestException):
        return _has_retryable_status(exception)

    if _has_retryable_status(exception):
        return True

    return False


def _build_retry_decorator(name: str) -> Callable:
    """Create a configured tenacity retry decorator."""
    retry_logger = logging.getLogger(f"{__name__}.{name.lower()}")
    return retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception(_should_retry),
        before=before_log(retry_logger, logging.DEBUG),
        after=after_log(retry_logger, logging.WARNING),
    )


def llm_retry() -> Callable:
    """Retry decorator for LLM API calls."""
    return _build_retry_decorator("LLM")


def wordpress_retry() -> Callable:
    """Retry decorator for WordPress REST API calls."""
    return _build_retry_decorator("WordPress")

