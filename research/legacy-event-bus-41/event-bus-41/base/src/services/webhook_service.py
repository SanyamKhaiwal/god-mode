import json
from src.core.database import db
from src.core.telemetry import telemetry
from src.core.security import verify_signature
from src.core.config import settings
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service
from src.services.audit_service import audit_service
from src.core.exceptions import WebhookValidationError
from typing import Dict, Any
import time

class WebhookService:
    EVENT_HANDLERS = {
        'invoice.payment_succeeded': '_handle_payment_succeeded',
        'invoice.payment_failed': '_handle_payment_failed',
        'customer.subscription.deleted': '_handle_subscription_deleted',
        'customer.subscription.updated': '_handle_subscription_updated',
    }

    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        try:
            if not verify_signature(payload, signature, settings.WEBHOOK_SECRET):
                raise WebhookValidationError('Invalid signature')

            try:
                data = json.loads(payload.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise WebhookValidationError(f'Invalid payload: {e}')

            event_id = data.get('id')
            event_type = data.get('type')

            if not event_id or not event_type:
                raise WebhookValidationError('Missing event id or type')
        except WebhookValidationError as e:
            return {'status': 'error', 'message': str(e)}

        # Idempotency check
        evt_key = f'webhook_{event_id}'
        if db.get_idempotency(evt_key):
            telemetry.increment('webhook.duplicate_ignored')
            return {'status': 'ignored_duplicate', 'event_id': event_id}

        db.save_idempotency(evt_key, {'event_id': event_id, 'processed': True})
        db.webhook_events.append({
            'event_id': event_id, 'type': event_type,
            'data': data, 'received_at': time.time()
        })

        handler_name = self.EVENT_HANDLERS.get(event_type)
        if handler_name:
            handler = getattr(self, handler_name)
            handler(data)

        telemetry.increment(f'webhook.{event_type}')
        audit_service.record('webhook.processed', 'system', 'webhook', event_id,
                              changes={'type': event_type})
        return {'status': 'processed', 'event_id': event_id}

    def _handle_payment_succeeded(self, data: Dict[str, Any]):
        telemetry.increment('webhook.payment_succeeded')

    def _handle_payment_failed(self, data: Dict[str, Any]):
        telemetry.increment('webhook.payment_failed')

    def _handle_subscription_deleted(self, data: Dict[str, Any]):
        telemetry.increment('webhook.subscription_deleted')

    def _handle_subscription_updated(self, data: Dict[str, Any]):
        telemetry.increment('webhook.subscription_updated')

webhook_service = WebhookService()
