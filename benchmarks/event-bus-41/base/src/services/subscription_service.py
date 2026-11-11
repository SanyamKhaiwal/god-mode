from src.core.database import db
from src.core.telemetry import telemetry
from src.services.stripe_client import stripe_client
from src.services.audit_service import audit_service
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
        audit_service.record('subscription.cancelled', sub['user_id'],
                              'subscription', subscription_id,
                              changes={'immediate': immediate, 'reason': reason})
        return sub

    def upgrade(self, subscription_id: str, new_tier: str,
                prorate: bool = True) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        old_tier = sub['plan_tier']
        sub['plan_tier'] = new_tier
        telemetry.increment('subscription.upgraded')
        audit_service.record('subscription.upgraded', sub['user_id'],
                              'subscription', subscription_id,
                              changes={'from': old_tier, 'to': new_tier, 'prorate': prorate})
        return sub

    def pause(self, subscription_id: str) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        sub['status'] = SubscriptionStatus.PAUSED.value
        telemetry.increment('subscription.paused')
        audit_service.record('subscription.paused', sub['user_id'],
                              'subscription', subscription_id)
        return sub

    def resume(self, subscription_id: str) -> Dict[str, Any]:
        if subscription_id not in db.subscriptions:
            raise SubscriptionNotFoundError(subscription_id)
        sub = db.subscriptions[subscription_id]
        sub['status'] = SubscriptionStatus.ACTIVE.value
        telemetry.increment('subscription.resumed')
        return sub

subscription_service = SubscriptionService()
