from dataclasses import dataclass, field
import time
from typing import Optional, Dict, Any

@dataclass
class AuditLog:
    id: str
    action: str
    actor_id: str
    target_type: str
    target_id: str
    changes: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
