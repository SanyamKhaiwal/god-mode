import json
import pytest
from src.core.events import EventBus, event_bus
from src.core.database import db
from src.core.config import settings
import hmac
import hashlib
from src.services import register_event_handlers
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.webhook_service import webhook_service


class TestEventBus:
    def test_publish_calls_subscribers_in_order(self):
        bus = EventBus()
        calls = []
        bus.subscribe('x', lambda p: calls.append(('a', p)))
        bus.subscribe('x', lambda p: calls.append(('b', p)))
        bus.publish('x', {'n': 1})
        assert calls == [('a', {'n': 1}), ('b', {'n': 1})]

    def test_publish_without_subscribers_is_noop(self):
        EventBus().publish('nobody.listens', {})

    def test_only_matching_event_delivered(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', calls.append)
        bus.publish('b', {'x': 1})
        assert calls == []

    def test_duplicate_subscribe_ignored_and_unsubscribe(self):
        bus = EventBus()
        calls = []
        bus.subscribe('a', calls.append)
        bus.subscribe('a', calls.append)
        bus.publish('a', {})
        assert len(calls) == 1
        bus.unsubscribe('a', calls.append)
        bus.publish('a', {})
        assert len(calls) == 1

    def test_handler_exception_propagates(self):
        bus = EventBus()
        def boom(p):
            raise ValueError('boom')
        bus.subscribe('a', boom)
        with pytest.raises(ValueError):
            bus.publish('a', {})


class TestAuditViaBus:
    def setup_method(self):
        db.reset()
        register_event_handlers()

    def test_billing_events_audited(self):
        sub = billing_service.create_subscription('usr_1', 'pro')
        pay = billing_service.process_payment('usr_1', 500)
        assert [(l['action'], l['actor_id'], l['target_type'], l['target_id'], l['changes'])
                for l in db.audit_logs] == [
            ('subscription.created', 'usr_1', 'subscription', sub.id, {}),
            ('payment.processed', 'usr_1', 'payment', pay.id, {'amount': 500}),
        ]

    def test_subscription_events_audited(self):
        sub = billing_service.create_subscription('usr_1', 'starter')
        subscription_service.upgrade(sub.id, 'pro')
        subscription_service.pause(sub.id)
        subscription_service.cancel(sub.id, reason='too pricey')
        assert [(l['action'], l['changes']) for l in db.audit_logs[1:]] == [
            ('subscription.upgraded', {'from': 'starter', 'to': 'pro', 'prorate': True}),
            ('subscription.paused', {}),
            ('subscription.cancelled', {'immediate': False, 'reason': 'too pricey'}),
        ]

    def test_webhook_processed_audited(self):
        body = json.dumps({'id': 'evt_9', 'type': 'invoice.payment_succeeded'}).encode()
        webhook_service.process_webhook(body, hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest())
        log = db.audit_logs[-1]
        assert (log['action'], log['actor_id'], log['target_id'], log['changes']) == \
            ('webhook.processed', 'system', 'evt_9', {'type': 'invoice.payment_succeeded'})

    def test_extra_subscriber_sees_payload(self):
        seen = []
        event_bus.subscribe('payment.processed', seen.append)
        try:
            pay = billing_service.process_payment('usr_2', 100)
        finally:
            event_bus.unsubscribe('payment.processed', seen.append)
        assert seen == [{'user_id': 'usr_2', 'payment_id': pay.id, 'amount_cents': 100}]

    def test_webhook_dispatches_to_domain_service_handlers(self):
        from src.core.telemetry import telemetry
        telemetry.reset()
        for i, t in enumerate(['invoice.payment_failed', 'customer.subscription.deleted']):
            body = json.dumps({'id': f'evt_t{i}', 'type': t}).encode()
            webhook_service.process_webhook(
                body, hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest())
        assert telemetry.counters['webhook.payment_failed'] == 1
        assert telemetry.counters['webhook.subscription_deleted'] == 1
