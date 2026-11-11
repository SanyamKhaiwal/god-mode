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

    def handle_event(self, payload: Dict[str, Any]) -> None:
        self.record(payload['action'], payload['actor_id'], payload['target_type'],
                    payload['target_id'], changes=payload.get('changes'))

# Events whose payloads are recorded verbatim as audit entries.
AUDITED_EVENTS = (
    'subscription.created',
    'subscription.cancelled',
    'subscription.upgraded',
    'subscription.paused',
    'payment.processed',
    'webhook.processed',
)

audit_service = AuditService()
for _event in AUDITED_EVENTS:
    event_bus.subscribe(_event, audit_service.handle_event)
