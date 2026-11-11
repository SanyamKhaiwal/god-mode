from src.services.subscription_service import subscription_service
from src.core.exceptions import SubscriptionNotFoundError
from typing import Dict, Any

def handle_cancel_subscription(subscription_id: str, immediate: bool = False,
                                reason: str = None) -> Dict[str, Any]:
    try:
        sub = subscription_service.cancel(subscription_id, immediate=immediate, reason=reason)
        return {'success': True, 'status': sub['status']}
    except SubscriptionNotFoundError:
        return {'success': False, 'error': 'not_found'}

def handle_upgrade_subscription(subscription_id: str, new_tier: str,
                                  prorate: bool = True) -> Dict[str, Any]:
    try:
        sub = subscription_service.upgrade(subscription_id, new_tier, prorate=prorate)
        return {'success': True, 'new_tier': sub['plan_tier']}
    except SubscriptionNotFoundError:
        return {'success': False, 'error': 'not_found'}

def handle_pause_subscription(subscription_id: str) -> Dict[str, Any]:
    try:
        sub = subscription_service.pause(subscription_id)
        return {'success': True, 'status': sub['status']}
    except SubscriptionNotFoundError:
        return {'success': False, 'error': 'not_found'}
