import unittest
from src.services.billing_service import billing_service
from src.core.database import db
from src.core.telemetry import telemetry

class TestBillingService(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_create_subscription(self):
        sub = billing_service.create_subscription('user_1', 'pro')
        self.assertEqual(sub.plan_tier, 'pro')
        self.assertIn(sub.id, db.subscriptions)
        self.assertEqual(telemetry.counters.get('subscription.created'), 1)

    def test_create_invoice(self):
        sub = billing_service.create_subscription('user_1', 'pro')
        inv = billing_service.create_invoice('user_1', sub.id)
        self.assertEqual(inv.total_cents, 4999)
        self.assertIn(inv.id, db.invoices)

    def test_process_payment(self):
        pay = billing_service.process_payment('user_1', 5000, idempotency_key='key_1')
        self.assertEqual(pay.amount_cents, 5000)
        self.assertEqual(pay.status.value, 'succeeded')

    def test_idempotent_payment(self):
        pay1 = billing_service.process_payment('user_1', 5000, idempotency_key='key_2')
        pay2 = billing_service.process_payment('user_1', 5000, idempotency_key='key_2')
        self.assertEqual(pay1.id, pay2.id)
        self.assertEqual(telemetry.counters.get('payment.idempotent_cache_hit'), 1)

    def test_idempotency_conflict(self):
        billing_service.process_payment('user_1', 5000, idempotency_key='key_3')
        with self.assertRaises(Exception):
            billing_service.process_payment('user_2', 9999, idempotency_key='key_3')

if __name__ == '__main__':
    unittest.main()
