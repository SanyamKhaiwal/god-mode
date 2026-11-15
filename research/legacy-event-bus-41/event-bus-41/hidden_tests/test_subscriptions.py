import unittest
from src.services.subscription_service import subscription_service
from src.services.billing_service import billing_service
from src.core.database import db
from src.core.telemetry import telemetry

class TestSubscriptionService(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_cancel_subscription(self):
        sub = billing_service.create_subscription('user_2', 'enterprise')
        result = subscription_service.cancel(sub.id, immediate=True)
        self.assertEqual(result['status'], 'canceled')

    def test_upgrade_subscription(self):
        sub = billing_service.create_subscription('user_2', 'starter')
        result = subscription_service.upgrade(sub.id, 'pro')
        self.assertEqual(result['plan_tier'], 'pro')

    def test_pause_resume(self):
        sub = billing_service.create_subscription('user_2', 'pro')
        subscription_service.pause(sub.id)
        self.assertEqual(db.subscriptions[sub.id]['status'], 'paused')
        subscription_service.resume(sub.id)
        self.assertEqual(db.subscriptions[sub.id]['status'], 'active')

    def test_cancel_nonexistent(self):
        with self.assertRaises(Exception):
            subscription_service.cancel('sub_nonexistent')

if __name__ == '__main__':
    unittest.main()
