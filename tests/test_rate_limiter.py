import unittest
import time
from core.rate_limiter import RateLimiter, ProviderRateLimitManager


class TestRateLimiter(unittest.TestCase):
    def test_acquire_tokens(self):
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        # Should allow 5 requests immediately
        for _ in range(5):
            self.assertTrue(limiter.acquire(block=False))
        # 6th non-blocking request should fail
        self.assertFalse(limiter.acquire(block=False))

    def test_manager_singleton(self):
        l1 = ProviderRateLimitManager.get_limiter("TestProvider", 30)
        l2 = ProviderRateLimitManager.get_limiter("TestProvider", 30)
        self.assertIs(l1, l2)


if __name__ == "__main__":
    unittest.main()
