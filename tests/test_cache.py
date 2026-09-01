import unittest
import time
from core.cache import TTLCache


class TestTTLCache(unittest.TestCase):
    def test_cache_set_get(self):
        cache = TTLCache(default_ttl_seconds=1.0)
        cache.set("k1", {"price": 10.5})
        self.assertEqual(cache.get("k1"), {"price": 10.5})

    def test_cache_expiry(self):
        cache = TTLCache(default_ttl_seconds=0.1)
        cache.set("k2", "val", ttl_seconds=0.1)
        time.sleep(0.15)
        self.assertIsNone(cache.get("k2"))


if __name__ == "__main__":
    unittest.main()
