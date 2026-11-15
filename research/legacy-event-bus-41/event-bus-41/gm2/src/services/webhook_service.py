import json
from src.core.database import db
from src.core.telemetry import telemetry
from src.core.security import verify_signature
from src.core.config import settings
from src.core.events import event_bus
from src.core.exceptions import WebhookValidationError
from typing import Dict, Any
import time

class WebhookService:
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

        # Domain services subscribe to 'webhook.<stripe event type>'
        event_bus.publish(f'webhook.{event_type}', data)

        telemetry.increment(f'webhook.{event_type}')
        event_bus.publish('webhook.processed', {
            'actor_id': 'system', 'target_type': 'webhook', 'target_id': event_id,
            'changes': {'type': event_type}})
        return {'status': 'processed', 'event_id': event_id}


webhook_service = WebhookService()
