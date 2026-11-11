import unittest
from src.services.user_service import user_service
from src.core.database import db
from src.core.telemetry import telemetry

class TestUserService(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_create_user(self):
        user = user_service.create_user('test@example.com', 'Test')
        self.assertEqual(user.email, 'test@example.com')
        self.assertIn(user.id, db.users)

    def test_generate_api_key(self):
        user = user_service.create_user('test@example.com')
        key = user_service.generate_user_api_key(user.id)
        self.assertIsNotNone(key)
        self.assertIsNotNone(db.users[user.id]['api_key_hash'])

    def test_check_usage_limit(self):
        user = user_service.create_user('test@example.com', plan_tier='free')
        self.assertTrue(user_service.check_usage_limit(user.id))

if __name__ == '__main__':
    unittest.main()
