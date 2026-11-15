import hashlib
import hmac
import json

import pytest

from src.core.config import settings
from src.core.database import db
from src.core.events import EventBus, event_bus
from src.core.telemetry import telemetry
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.webhook_service import webhook_service


@pytest.fixture(autouse=True)
def reset_state():
    db.reset()
    telemetry.reset()
    yield


class TestEventBus:
    def test_publish_calls_subscribers_in_order(self):
        bus = EventBus()
        calls = []
        bus.subscribe('thing.happened', lambda p: calls.append(('a', p)))
        bus.subscribe('thing.happened', lambda p: calls.append(('b', p)))
        bus.publish('thing.happened', {'x': 1})
        assert calls == [('a', {'x': 1}), ('b', {'x': 1})]

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {'x': 1})

    def test_only_matching_event_handlers_run(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', lambda p: calls.append('a'))
        bus.subscribe('b', lambda p: calls.append('b'))
        bus.publish('b', {})
        assert calls == ['b']

    def test_duplicate_subscription_ignored_and_unsubscribe(self):
        bus = EventBus()
        calls = []
        handler = lambda p: calls.append(p)
        bus.subscribe('e', handler)
        bus.subscribe('e', handler)
        bus.publish('e', {'n': 1})
        bus.unsubscribe('e', handler)
        bus.publish('e', {'n': 2})
        assert calls == [{'n': 1}]

    def test_handler_exception_propagates(self):
        bus = EventBus()
        def boom(p):
            raise RuntimeError('boom')
        bus.subscribe('e', boom)
        with pytest.raises(RuntimeError):
            bus.publish('e', {})


class TestAuditViaBus:
    def test_published_event_writes_audit_entry(self):
        event_bus.publish('subscription.paused', {
            'actor_id': 'usr_9', 'target_type': 'subscription', 'target_id': 'sub_9'})
        assert db.audit_logs[-1]['action'] == 'subscription.paused'
        assert db.audit_logs[-1]['actor_id'] == 'usr_9'
        assert db.audit_logs[-1]['changes'] == {}

    def test_billing_and_subscription_audit_entries(self):
        sub = billing_service.create_subscription('usr_1', 'starter')
        billing_service.process_payment('usr_1', 1999)
        subscription_service.upgrade(sub.id, 'pro')
        subscription_service.pause(sub.id)
        subscription_service.cancel(sub.id, immediate=True, reason='test')
        entries = [(l['action'], l['actor_id'], l['target_type'], l['target_id'], l['changes'])
                   for l in db.audit_logs]
        assert entries == [
            ('subscription.created', 'usr_1', 'subscription', sub.id, {}),
            ('payment.processed', 'usr_1', 'payment', 'pay_1', {'amount': 1999}),
            ('subscription.upgraded', 'usr_1', 'subscription', sub.id,
             {'from': 'starter', 'to': 'pro', 'prorate': True}),
            ('subscription.paused', 'usr_1', 'subscription', sub.id, {}),
            ('subscription.cancelled', 'usr_1', 'subscription', sub.id,
             {'immediate': True, 'reason': 'test'}),
        ]

    def test_webhook_audit_and_domain_handlers(self):
        payload = json.dumps({'id': 'evt_1', 'type': 'invoice.payment_succeeded'}).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        result = webhook_service.process_webhook(payload, sig)
        assert result['status'] == 'processed'
        assert telemetry.counters['webhook.payment_succeeded'] == 1
        log = db.audit_logs[-1]
        assert (log['action'], log['actor_id'], log['target_type'], log['target_id'],
                log['changes']) == ('webhook.processed', 'system', 'webhook', 'evt_1',
                                    {'type': 'invoice.payment_succeeded'})
