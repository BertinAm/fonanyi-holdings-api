"""Shared test setup.

The rate limiter counts requests in the default cache, and that cache lives
for the whole pytest process. Without this, how many requests a test may make
depends on how many the tests before it happened to make -- so adding a test
anywhere could push an unrelated one over the limit and fail it with a 429.
That is exactly what happened when the mail-alert tests were added.
"""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_history():
    cache.clear()
    yield
    cache.clear()
