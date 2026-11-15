from src.core.database import db
from src.core.telemetry import telemetry
from src.services.stripe_client import stripe_client
from src.core.events import event_bus
from src.models.subscription import SubscriptionStatus
from src.core.exceptions import SubscriptionNotFoundError
from typing import Optional, Dict, Any
import time

class SubscriptionService:
    def cancel(self, subscription_id: str, immediate: bool = False,
               reason: str = None) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        stripe_client.cancel_subscription(subscription_id, immediate=immediate)
        if immediate:
            sub['status'] = SubscriptionStatus.CANCELED.value
            sub['canceled_at'] = time.time()
        else:
            sub['cancel_at_period_end'] = True
        telemetry.increment('subscription.cancelled')
        event_bus.publish('subscription.cancelled', {
            'user_id': sub['user_id'], 'subscription_id': subscription_id,
            'immediate': immediate, 'reason': reason
        })
        return sub

    def upgrade(self, subscription_id: str, new_tier: str,
                prorate: bool = True) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        old_tier = sub['plan_tier']
        sub['plan_tier'] = new_tier
        telemetry.increment('subscription.upgraded')
        event_bus.publish('subscription.upgraded', {
            'user_id': sub['user_id'], 'subscription_id': subscription_id,
            'from': old_tier, 'to': new_tier, 'prorate': prorate
        })
        return sub

    def pause(self, subscription_id: str) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        sub['status'] = SubscriptionStatus.PAUSED.value
        telemetry.increment('subscription.paused')
        event_bus.publish('subscription.paused', {
            'user_id': sub['user_id'], 'subscription_id': subscription_id
        })
        return sub

    def resume(self, subscription_id: str) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        sub['status'] = SubscriptionStatus.ACTIVE.value
        telemetry.increment('subscription.resumed')
        return sub

    def on_webhook_subscription_deleted(self, payload: Dict[str, Any]):
        telemetry.increment('webhook.subscription_deleted')

    def on_webhook_subscription_updated(self, payload: Dict[str, Any]):
        telemetry.increment('webhook.subscription_updated')

subscription_service = SubscriptionService()
event_bus.subscribe('webhook.customer.subscription.deleted',
                    subscription_service.on_webhook_subscription_deleted)
event_bus.subscribe('webhook.customer.subscription.updated',
                    subscription_service.on_webhook_subscription_updated)
