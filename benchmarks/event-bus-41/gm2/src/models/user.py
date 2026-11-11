from dataclasses import dataclass, field
from typing import Optional, List
import time

@dataclass
class User:
    id: str
    email: str
    name: str = ''
    stripe_customer_id: Optional[str] = None
    api_key_hash: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: float = field(default_factory=time.time)
    plan_tier: str = 'free'
    usage_this_period: int = 0
