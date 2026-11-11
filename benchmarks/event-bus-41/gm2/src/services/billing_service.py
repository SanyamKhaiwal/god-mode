from src.core.database import db
from src.core.telemetry import telemetry
from src.core.config import settings, PLAN_TIERS
from src.services.stripe_client import stripe_client
from src.core.events import event_bus
from src.models.subscription import Subscription, SubscriptionStatus
from src.models.invoice import Invoice, InvoiceStatus, LineItem
from src.models.payment import Payment, PaymentStatus
from src.core.exceptions import PaymentFailedError, IdempotencyConflictError
from typing import Optional, Dict, Any
import time

class BillingService:
    def create_subscription(self, user_id: str, plan_tier: str) -> Subscription:
        sub_id = f'sub_{len(db.subscriptions) + 1}'
        now = time.time()
        sub = Subscription(
            id=sub_id, user_id=user_id, plan_tier=plan_tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + 30 * 86400
        )
        db.subscriptions[sub_id] = {
            'id': sub.id, 'user_id': user_id, 'plan_tier': plan_tier,
            'status': sub.status.value,
            'current_period_start': sub.current_period_start,
            'current_period_end': sub.current_period_end,
            'cancel_at_period_end': False
        }
        telemetry.increment('subscription.created')
        event_bus.publish('subscription.created', {
            'actor_id': user_id, 'target_type': 'subscription', 'target_id': sub_id})
        return sub

    def create_invoice(self, user_id: str, subscription_id: str) -> Invoice:
        inv_id = f'inv_{len(db.invoices) + 1}'
        sub_data = db.subscriptions.get(subscription_id, {})
        tier = sub_data.get('plan_tier', 'free')
        price = PLAN_TIERS.get(tier, {}).get('price_cents', 0)
        invoice = Invoice(
            id=inv_id, user_id=user_id, subscription_id=subscription_id,
            line_items=[LineItem(description=f'{tier} plan', amount_cents=price)]
        )
        invoice.calculate_totals(settings.TAX_RATE_PERCENT)
        db.invoices[inv_id] = {
            'id': inv_id, 'user_id': user_id, 'subscription_id': subscription_id,
            'total_cents': invoice.total_cents, 'status': invoice.status.value
        }
        telemetry.increment('invoice.created')
        return invoice

    def process_payment(self, user_id: str, amount_cents: int,
                        idempotency_key: str = None, invoice_id: str = None) -> Payment:
        if idempotency_key:
            existing = db.get_idempotency(idempotency_key)
            if existing:
                if existing.get('user_id') != user_id or existing.get('amount_cents') != amount_cents:
                    raise IdempotencyConflictError(idempotency_key)
                telemetry.increment('payment.idempotent_cache_hit')
                return Payment(id=existing['id'], user_id=user_id, invoice_id=invoice_id,
                               amount_cents=amount_cents, status=PaymentStatus.SUCCEEDED,
                               idempotency_key=idempotency_key)

        with telemetry.timer('payment.processing_time'):
            stripe_result = stripe_client.create_payment_intent(
                amount=amount_cents, currency=settings.CURRENCY
            )

        pay_id = f'pay_{len(db.payments) + 1}'
        payment = Payment(
            id=pay_id, user_id=user_id, invoice_id=invoice_id,
            amount_cents=amount_cents, status=PaymentStatus.SUCCEEDED,
            stripe_payment_intent_id=stripe_result['id'],
            idempotency_key=idempotency_key
        )
        db.payments[pay_id] = {
            'id': pay_id, 'user_id': user_id, 'amount_cents': amount_cents,
            'status': 'succeeded', 'invoice_id': invoice_id
        }
        if idempotency_key:
            db.save_idempotency(idempotency_key, {
                'id': pay_id, 'user_id': user_id, 'amount_cents': amount_cents
            })
        telemetry.increment('payment.processed')
        event_bus.publish('payment.processed', {
            'actor_id': user_id, 'target_type': 'payment', 'target_id': pay_id,
            'changes': {'amount': amount_cents}})
        return payment

    def on_webhook_payment_succeeded(self, payload: Dict[str, Any]):
        telemetry.increment('webhook.payment_succeeded')

    def on_webhook_payment_failed(self, payload: Dict[str, Any]):
        telemetry.increment('webhook.payment_failed')

billing_service = BillingService()
event_bus.subscribe('webhook.invoice.payment_succeeded', billing_service.on_webhook_payment_succeeded)
event_bus.subscribe('webhook.invoice.payment_failed', billing_service.on_webhook_payment_failed)
