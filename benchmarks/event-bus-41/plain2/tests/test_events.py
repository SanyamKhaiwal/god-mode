import unittest
import json
import hmac
import hashlib
from src.core.events import EventBus, event_bus
from src.core.config import settings
from src.core.database import db
from src.core.telemetry import telemetry
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.webhook_service import webhook_service


class TestEventBus(unittest.TestCase):
    def test_publish_calls_subscribers_in_order(self):
        bus = EventBus()
        calls = []
        bus.subscribe('x', lambda p: calls.append(('a', p)))
        bus.subscribe('x', lambda p: calls.append(('b', p)))
        bus.publish('x', {'n': 1})
        self.assertEqual(calls, [('a', {'n': 1}), ('b', {'n': 1})])

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {})

    def test_only_matching_event_delivered(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', calls.append)
        bus.publish('b', {'n': 1})
        self.assertEqual(calls, [])

    def test_duplicate_subscribe_and_unsubscribe(self):
        bus = EventBus()
        calls = []
        bus.subscribe('x', calls.append)
        bus.subscribe('x', calls.append)
        bus.publish('x', {})
        self.assertEqual(len(calls), 1)
        bus.unsubscribe('x', calls.append)
        bus.publish('x', {})
        self.assertEqual(len(calls), 1)

    def test_handler_exception_propagates(self):
        bus = EventBus()
        def boom(p):
            raise ValueError('boom')
        bus.subscribe('x', boom)
        with self.assertRaises(ValueError):
            bus.publish('x', {})


class TestAuditViaBus(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def _actions(self):
        return [l['action'] for l in db.audit_logs]

    def test_direct_publish_writes_audit(self):
        event_bus.publish('subscription.paused', {'user_id': 'usr_9', 'subscription_id': 'sub_9'})
        self.assertEqual(db.audit_logs[-1]['action'], 'subscription.paused')
        self.assertEqual(db.audit_logs[-1]['target_id'], 'sub_9')
        self.assertEqual(db.audit_logs[-1]['actor_id'], 'usr_9')

    def test_billing_and_subscription_audit_entries(self):
        sub = billing_service.create_subscription('usr_1', 'pro')
        pay = billing_service.process_payment('usr_1', 1500)
        subscription_service.upgrade(sub.id, 'enterprise', prorate=False)
        subscription_service.pause(sub.id)
        subscription_service.cancel(sub.id, immediate=True, reason='too pricey')
        self.assertEqual(self._actions(), [
            'subscription.created', 'payment.processed', 'subscription.upgraded',
            'subscription.paused', 'subscription.cancelled'])
        logs = db.audit_logs
        self.assertEqual(logs[0]['target_type'], 'subscription')
        self.assertEqual(logs[1]['target_id'], pay.id)
        self.assertEqual(logs[1]['changes'], {'amount': 1500})
        self.assertEqual(logs[2]['changes'], {'from': 'pro', 'to': 'enterprise', 'prorate': False})
        self.assertEqual(logs[3]['changes'], {})
        self.assertEqual(logs[4]['changes'], {'immediate': True, 'reason': 'too pricey'})

    def test_webhook_audit_and_domain_handlers(self):
        body = json.dumps({'id': 'evt_1', 'type': 'invoice.payment_failed'}).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        webhook_service.process_webhook(body, sig)
        self.assertEqual(db.audit_logs[-1]['action'], 'webhook.processed')
        self.assertEqual(db.audit_logs[-1]['actor_id'], 'system')
        self.assertEqual(db.audit_logs[-1]['changes'], {'type': 'invoice.payment_failed'})
        self.assertEqual(telemetry.counters.get('webhook.payment_failed'), 1)


if __name__ == '__main__':
    unittest.main()
