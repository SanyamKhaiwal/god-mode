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
        bus.subscribe('thing.happened', lambda p: calls.append(('a', p)))
        bus.subscribe('thing.happened', lambda p: calls.append(('b', p)))
        bus.publish('thing.happened', {'x': 1})
        self.assertEqual(calls, [('a', {'x': 1}), ('b', {'x': 1})])

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {'x': 1})

    def test_only_matching_event_handlers_run(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', calls.append)
        bus.publish('b', {'x': 1})
        self.assertEqual(calls, [])

    def test_unsubscribe(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', calls.append)
        bus.unsubscribe('a', calls.append)
        bus.publish('a', {})
        self.assertEqual(calls, [])

class TestAuditViaBus(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def test_bus_event_writes_audit_entry(self):
        event_bus.publish('payment.processed', {
            'actor_id': 'usr_9', 'target_type': 'payment', 'target_id': 'pay_9',
            'changes': {'amount': 5}
        })
        self.assertEqual(len(db.audit_logs), 1)
        log = db.audit_logs[0]
        self.assertEqual((log['action'], log['actor_id'], log['target_id'], log['changes']),
                         ('payment.processed', 'usr_9', 'pay_9', {'amount': 5}))

    def test_service_flows_write_same_audit_entries(self):
        sub = billing_service.create_subscription('usr_1', 'pro')
        billing_service.process_payment('usr_1', 4999)
        subscription_service.upgrade(sub.id, 'enterprise')
        subscription_service.pause(sub.id)
        subscription_service.cancel(sub.id, immediate=True, reason='x')
        entries = [(l['action'], l['actor_id'], l['target_type'], l['target_id'], l['changes'])
                   for l in db.audit_logs]
        self.assertEqual(entries, [
            ('subscription.created', 'usr_1', 'subscription', sub.id, {}),
            ('payment.processed', 'usr_1', 'payment', 'pay_1', {'amount': 4999}),
            ('subscription.upgraded', 'usr_1', 'subscription', sub.id,
             {'from': 'pro', 'to': 'enterprise', 'prorate': True}),
            ('subscription.paused', 'usr_1', 'subscription', sub.id, {}),
            ('subscription.cancelled', 'usr_1', 'subscription', sub.id,
             {'immediate': True, 'reason': 'x'}),
        ])

    def test_webhook_forwards_to_services_and_audits(self):
        body = json.dumps({'id': 'evt_9', 'type': 'customer.subscription.deleted'}).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        webhook_service.process_webhook(body, sig)
        self.assertEqual(telemetry.counters.get('webhook.subscription_deleted'), 1)
        self.assertEqual(db.audit_logs[-1]['action'], 'webhook.processed')
        self.assertEqual(db.audit_logs[-1]['changes'], {'type': 'customer.subscription.deleted'})

if __name__ == '__main__':
    unittest.main()
