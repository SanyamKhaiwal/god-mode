from dataclasses import dataclass, field
import time

@dataclass
class UsageRecord:
    id: str
    user_id: str
    subscription_id: str
    metric: str  # 'api_calls', 'storage_mb'
    quantity: int
    recorded_at: float = field(default_factory=time.time)
