import unittest
import json
import hmac
import hashlib
import inspect
from src.core.events import EventBus
from src.core.config import settings
from src.core.database import db
from src.core.telemetry import telemetry
from src.services import billing_service as billing_mod
from src.services import subscription_service as subscription_mod
from src.services import webhook_service as webhook_mod
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.webhook_service import webhook_service


class TestEventBus(unittest.TestCase):
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe('thing.happened', received.append)
        bus.publish('thing.happened', {'x': 1})
        self.assertEqual(received, [{'x': 1}])

    def test_multiple_handlers_called_in_order(self):
        bus = EventBus()
        calls = []
        bus.subscribe('e', lambda p: calls.append('a'))
        bus.subscribe('e', lambda p: calls.append('b'))
        bus.publish('e', {})
        self.assertEqual(calls, ['a', 'b'])

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {})

    def test_handlers_only_receive_their_event(self):
        bus = EventBus()
        received = []
        bus.subscribe('a', received.append)
        bus.publish('b', {'y': 2})
        self.assertEqual(received, [])

    def test_duplicate_subscription_ignored_and_unsubscribe(self):
        bus = EventBus()
        received = []
        bus.subscribe('e', received.append)
        bus.subscribe('e', received.append)
        bus.publish('e', {})
        self.assertEqual(len(received), 1)
        bus.unsubscribe('e', received.append)
        bus.publish('e', {})
        self.assertEqual(len(received), 1)

    def test_handler_exception_propagates(self):
        bus = EventBus()
        def boom(payload):
            raise RuntimeError('boom')
        bus.subscribe('e', boom)
        with self.assertRaises(RuntimeError):
            bus.publish('e', {})


class TestAuditViaBus(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def _logs(self):
        return [{k: v for k, v in l.items() if k != 'timestamp'} for l in db.audit_logs]

    def _webhook(self, data):
        body = json.dumps(data).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return webhook_service.process_webhook(body, sig)

    def test_subscription_created(self):
        sub = billing_service.create_subscription('usr_1', 'pro')
        self.assertEqual(self._logs(), [{
            'id': 'log_1', 'action': 'subscription.created', 'actor_id': 'usr_1',
            'target_type': 'subscription', 'target_id': sub.id, 'changes': {}}])

    def test_payment_processed(self):
        pay = billing_service.process_payment('usr_1', 4999)
        self.assertEqual(self._logs(), [{
            'id': 'log_1', 'action': 'payment.processed', 'actor_id': 'usr_1',
            'target_type': 'payment', 'target_id': pay.id, 'changes': {'amount': 4999}}])

    def test_subscription_lifecycle(self):
        sub = billing_service.create_subscription('usr_1', 'starter')
        subscription_service.upgrade(sub.id, 'pro', prorate=False)
        subscription_service.pause(sub.id)
        subscription_service.resume(sub.id)  # resume never audited
        subscription_service.cancel(sub.id, immediate=True, reason='too pricey')
        logs = self._logs()
        self.assertEqual([l['action'] for l in logs], [
            'subscription.created', 'subscription.upgraded',
            'subscription.paused', 'subscription.cancelled'])
        self.assertEqual(logs[1]['changes'], {'from': 'starter', 'to': 'pro', 'prorate': False})
        self.assertEqual(logs[2]['changes'], {})
        self.assertEqual(logs[3]['changes'], {'immediate': True, 'reason': 'too pricey'})
        for l in logs:
            self.assertEqual((l['actor_id'], l['target_type'], l['target_id']),
                             ('usr_1', 'subscription', sub.id))

    def test_webhook_audited_and_forwarded(self):
        self._webhook({'id': 'evt_1', 'type': 'invoice.payment_succeeded'})
        self._webhook({'id': 'evt_2', 'type': 'customer.subscription.deleted'})
        self._webhook({'id': 'evt_3', 'type': 'unknown.type'})
        self._webhook({'id': 'evt_1', 'type': 'invoice.payment_succeeded'})  # duplicate
        self.assertEqual(
            [(l['action'], l['actor_id'], l['target_type'], l['target_id'], l['changes'])
             for l in self._logs()],
            [('webhook.processed', 'system', 'webhook', 'evt_1', {'type': 'invoice.payment_succeeded'}),
             ('webhook.processed', 'system', 'webhook', 'evt_2', {'type': 'customer.subscription.deleted'}),
             ('webhook.processed', 'system', 'webhook', 'evt_3', {'type': 'unknown.type'})])
        self.assertEqual(telemetry.counters.get('webhook.payment_succeeded'), 1)
        self.assertEqual(telemetry.counters.get('webhook.subscription_deleted'), 1)

    def test_services_are_decoupled(self):
        for mod in (billing_mod, subscription_mod, webhook_mod):
            self.assertNotIn('audit_service', inspect.getsource(mod))
        src = inspect.getsource(webhook_mod)
        self.assertNotIn('billing_service', src)
        self.assertNotIn('subscription_service', src)


if __name__ == '__main__':
    unittest.main()
