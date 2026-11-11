from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time

class SubscriptionStatus(str, Enum):
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELED = 'canceled'
    TRIALING = 'trialing'
    PAUSED = 'paused'

@dataclass
class Subscription:
    id: str
    user_id: str
    plan_tier: str
    status: SubscriptionStatus
    current_period_start: float = field(default_factory=time.time)
    current_period_end: float = 0.0
    cancel_at_period_end: bool = False
    canceled_at: Optional[float] = None
    trial_end: Optional[float] = None
    stripe_subscription_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
