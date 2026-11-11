from src.core.database import db
from src.models.audit_log import AuditLog
from typing import List, Dict, Any, Optional
from src.core.events import event_bus
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

audit_service = AuditService()


def _on_subscription_created(p):
    audit_service.record('subscription.created', p['user_id'], 'subscription', p['subscription_id'])

def _on_payment_processed(p):
    audit_service.record('payment.processed', p['user_id'], 'payment', p['payment_id'],
                         changes={'amount': p['amount_cents']})

def _on_subscription_cancelled(p):
    audit_service.record('subscription.cancelled', p['user_id'], 'subscription',
                         p['subscription_id'],
                         changes={'immediate': p['immediate'], 'reason': p['reason']})

def _on_subscription_upgraded(p):
    audit_service.record('subscription.upgraded', p['user_id'], 'subscription',
                         p['subscription_id'],
                         changes={'from': p['from_tier'], 'to': p['to_tier'],
                                  'prorate': p['prorate']})

def _on_subscription_paused(p):
    audit_service.record('subscription.paused', p['user_id'], 'subscription', p['subscription_id'])

def _on_webhook_processed(p):
    audit_service.record('webhook.processed', 'system', 'webhook', p['event_id'],
                         changes={'type': p['event_type']})

AUDITED_EVENTS = {
    'subscription.created': _on_subscription_created,
    'payment.processed': _on_payment_processed,
    'subscription.cancelled': _on_subscription_cancelled,
    'subscription.upgraded': _on_subscription_upgraded,
    'subscription.paused': _on_subscription_paused,
    'webhook.processed': _on_webhook_processed,
}

def register_audit_subscribers(bus=event_bus):
    for name, handler in AUDITED_EVENTS.items():
        bus.subscribe(name, handler)

register_audit_subscribers()
