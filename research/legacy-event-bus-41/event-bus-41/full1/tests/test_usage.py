import unittest
from src.services.usage_service import usage_service
from src.services.user_service import user_service
from src.services.billing_service import billing_service
from src.core.database import db
from src.core.telemetry import telemetry

class TestUsageService(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_record_and_get_usage(self):
        user = user_service.create_user('test@example.com', plan_tier='starter')
        sub = billing_service.create_subscription(user.id, 'starter')
        usage_service.record_usage(user.id, sub.id, 'api_calls', 50)
        total = usage_service.get_period_usage(user.id, 'api_calls')
        self.assertEqual(total, 50)

    def test_check_limit(self):
        user = user_service.create_user('test@example.com', plan_tier='free')
        result = usage_service.check_limit(user.id, 'api_calls')
        self.assertTrue(result['allowed'])
        self.assertEqual(result['limit'], 100)

if __name__ == '__main__':
    unittest.main()
