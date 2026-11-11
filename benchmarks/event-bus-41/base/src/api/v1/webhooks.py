from src.services.webhook_service import webhook_service
from src.core.exceptions import WebhookValidationError
from typing import Dict, Any

def handle_stripe_webhook(payload: bytes, signature: str) -> Dict[str, Any]:
    try:
        return webhook_service.process_webhook(payload, signature)
    except WebhookValidationError as e:
        return {'status': 'error', 'message': e.message}
