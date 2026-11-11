from dataclasses import dataclass
from typing import Optional

@dataclass
class UpgradeSubscriptionRequest:
    new_plan_tier: str
    prorate: bool = True

@dataclass
class CancelSubscriptionRequest:
    immediate: bool = False
    reason: Optional[str] = None

@dataclass
class PauseSubscriptionRequest:
    resume_date: Optional[str] = None
