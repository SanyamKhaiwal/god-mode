import unittest
import json
import hmac
import hashlib
from src.core.events import EventBus, event_bus
from src.services.audit_service import audit_service
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.webhook_service import webhook_service
from src.core.config import settings
from src.core.database import db
from src.core.telemetry import telemetry


class TestEventBus(unittest.TestCase):
    def test_publish_calls_subscribers_in_order(self):
        bus = EventBus()
        calls = []
        bus.subscribe('thing.happened', lambda p: calls.append(('a', p)))
        bus.subscribe('thing.happened', lambda p: calls.append(('b', p)))
        bus.publish('thing.happened', {'x': 1})
        self.assertEqual(calls, [('a', {'x': 1}), ('b', {'x': 1})])

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {})

    def test_subscribers_only_receive_their_event(self):
        bus = EventBus()
        calls = []
        bus.subscribe('one', calls.append)
        bus.publish('two', {'y': 2})
        self.assertEqual(calls, [])

    def test_duplicate_subscribe_is_ignored(self):
        bus = EventBus()
        calls = []
        bus.subscribe('e', calls.append)
        bus.subscribe('e', calls.append)
        bus.publish('e', {})
        self.assertEqual(len(calls), 1)

    def test_unsubscribe(self):
        bus = EventBus()
        calls = []
        bus.subscribe('e', calls.append)
        bus.unsubscribe('e', calls.append)
        bus.publish('e', {})
        self.assertEqual(calls, [])

    def test_handler_exception_propagates(self):
        bus = EventBus()
        def boom(payload):
            raise ValueError('boom')
        bus.subscribe('e', boom)
        with self.assertRaises(ValueError):
            bus.publish('e', {})


class TestAuditViaBus(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_audit_subscribed_to_service_events(self):
        for name in ('subscription.created', 'subscription.cancelled',
                     'subscription.upgraded', 'subscription.paused',
                     'payment.processed', 'webhook.processed'):
            self.assertIn(audit_service.handle_event, event_bus.handlers(name))

    def test_publish_records_audit_entry(self):
        event_bus.publish('payment.processed', {
            'action': 'payment.processed', 'actor_id': 'usr_9',
            'target_type': 'payment', 'target_id': 'pay_9',
            'changes': {'amount': 5}
        })
        logs = audit_service.get_logs_for_target('payment', 'pay_9')
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['actor_id'], 'usr_9')
        self.assertEqual(logs[0]['changes'], {'amount': 5})

    def test_billing_writes_audit_entries(self):
        sub = billing_service.create_subscription('usr_1', 'pro')
        pay = billing_service.process_payment('usr_1', 1000)
        actions = [l['action'] for l in db.audit_logs]
        self.assertEqual(actions, ['subscription.created', 'payment.processed'])
        self.assertEqual(db.audit_logs[0]['target_id'], sub.id)
        self.assertEqual(db.audit_logs[0]['changes'], {})
        self.assertEqual(db.audit_logs[1]['target_id'], pay.id)
        self.assertEqual(db.audit_logs[1]['changes'], {'amount': 1000})

    def test_subscription_writes_audit_entries(self):
        sub = billing_service.create_subscription('usr_1', 'starter')
        subscription_service.upgrade(sub.id, 'pro')
        subscription_service.pause(sub.id)
        subscription_service.cancel(sub.id, immediate=True, reason='x')
        logs = audit_service.get_logs_for_target('subscription', sub.id)
        self.assertEqual([l['action'] for l in logs], [
            'subscription.created', 'subscription.upgraded',
            'subscription.paused', 'subscription.cancelled'])
        self.assertEqual(logs[1]['changes'], {'from': 'starter', 'to': 'pro', 'prorate': True})
        self.assertEqual(logs[2]['changes'], {})
        self.assertEqual(logs[3]['changes'], {'immediate': True, 'reason': 'x'})
        self.assertTrue(all(l['actor_id'] == 'usr_1' for l in logs))

    def test_webhook_writes_audit_and_reaches_services(self):
        payload = json.dumps({'id': 'evt_bus_1',
                              'type': 'invoice.payment_succeeded'}).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), payload,
                       hashlib.sha256).hexdigest()
        result = webhook_service.process_webhook(payload, sig)
        self.assertEqual(result['status'], 'processed')
        logs = audit_service.get_logs_for_target('webhook', 'evt_bus_1')
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['actor_id'], 'system')
        self.assertEqual(logs[0]['changes'], {'type': 'invoice.payment_succeeded'})
        self.assertEqual(telemetry.counters.get('webhook.payment_succeeded'), 1)


if __name__ == '__main__':
    unittest.main()
