import unittest
from src.core.security import verify_signature, hash_token, generate_api_key, verify_api_key, RateLimiter

class TestSecurity(unittest.TestCase):
    def test_hash_token(self):
        h = hash_token('secret-api-token')
        self.assertEqual(len(h), 64)

    def test_api_key_roundtrip(self):
        raw, hashed = generate_api_key()
        self.assertTrue(verify_api_key(raw, hashed))
        self.assertFalse(verify_api_key('wrong-key', hashed))

    def test_rate_limiter(self):
        rl = RateLimiter(max_per_minute=3)
        self.assertTrue(rl.check('u1'))
        self.assertTrue(rl.check('u1'))
        self.assertTrue(rl.check('u1'))
        self.assertFalse(rl.check('u1'))
        self.assertEqual(rl.remaining('u1'), 0)

if __name__ == '__main__':
    unittest.main()
