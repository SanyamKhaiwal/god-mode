from src.services.billing_service import billing_service
from src.services.user_service import user_service
from src.schemas.billing import CreateCheckoutSessionRequest, PaymentRequest
from src.core.exceptions import BillingError
from typing import Dict, Any

def handle_create_checkout(payload: Dict[str, Any]) -> Dict[str, Any]:
    user = user_service.get_user(payload['user_id'])
    if not user:
        return {'error': 'user_not_found'}
    sub = billing_service.create_subscription(payload['user_id'], payload['plan_tier'])
    return {'subscription_id': sub.id, 'status': 'created'}

def handle_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payment = billing_service.process_payment(
            user_id=payload['user_id'],
            amount_cents=payload['amount_cents'],
            idempotency_key=payload.get('idempotency_key'),
            invoice_id=payload.get('invoice_id')
        )
        return {'payment_id': payment.id, 'status': payment.status.value}
    except BillingError as e:
        return {'error': e.code, 'message': e.message}
