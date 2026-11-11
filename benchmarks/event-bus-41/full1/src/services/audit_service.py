from src.core.database import db
from src.models.audit_log import AuditLog
from src.core.events import event_bus
from typing import List, Dict, Any, Optional
import time

class AuditService:
    def record(self, action: str, actor_id: str, target_type: str,
               target_id: str, changes: Dict[str, Any] = None,
               ip_address: str = None) -> AuditLog:
        log_id = f'log_{len(db.audit_logs) + 1}'
        log = AuditLog(
            id=log_id, action=action, actor_id=actor_id,
            target_type=target_type, target_id=target_id,
            changes=changes or {}, ip_address=ip_address
        )
        db.audit_logs.append({
            'id': log_id, 'action': action, 'actor_id': actor_id,
            'target_type': target_type, 'target_id': target_id,
            'changes': changes or {}, 'timestamp': time.time()
        })
        return log

    def get_logs_for_target(self, target_type: str, target_id: str) -> List[Dict[str, Any]]:
        return [l for l in db.audit_logs
                if l['target_type'] == target_type and l['target_id'] == target_id]

    def get_logs_for_actor(self, actor_id: str) -> List[Dict[str, Any]]:
        return [l for l in db.audit_logs if l['actor_id'] == actor_id]

    # Event handlers: each records the entry the publisher used to write directly
    def on_subscription_created(self, p: Dict[str, Any]):
        self.record('subscription.created', p['user_id'], 'subscription', p['subscription_id'])

    def on_payment_processed(self, p: Dict[str, Any]):
        self.record('payment.processed', p['user_id'], 'payment', p['payment_id'],
                    changes={'amount': p['amount_cents']})

    def on_subscription_cancelled(self, p: Dict[str, Any]):
        self.record('subscription.cancelled', p['user_id'], 'subscription', p['subscription_id'],
                    changes={'immediate': p['immediate'], 'reason': p['reason']})

    def on_subscription_upgraded(self, p: Dict[str, Any]):
        self.record('subscription.upgraded', p['user_id'], 'subscription', p['subscription_id'],
                    changes={'from': p['from'], 'to': p['to'], 'prorate': p['prorate']})

    def on_subscription_paused(self, p: Dict[str, Any]):
        self.record('subscription.paused', p['user_id'], 'subscription', p['subscription_id'])

    def on_webhook_processed(self, p: Dict[str, Any]):
        self.record('webhook.processed', 'system', 'webhook', p['event_id'],
                    changes={'type': p['type']})

    def register_event_handlers(self):
        event_bus.subscribe('subscription.created', self.on_subscription_created)
        event_bus.subscribe('payment.processed', self.on_payment_processed)
        event_bus.subscribe('subscription.cancelled', self.on_subscription_cancelled)
        event_bus.subscribe('subscription.upgraded', self.on_subscription_upgraded)
        event_bus.subscribe('subscription.paused', self.on_subscription_paused)
        event_bus.subscribe('webhook.processed', self.on_webhook_processed)

audit_service = AuditService()
