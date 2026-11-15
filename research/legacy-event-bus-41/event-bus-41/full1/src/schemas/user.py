from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    email: str
    name: str = ''
    plan_tier: str = 'free'

@dataclass
class UserProfileResponse:
    id: str
    email: str
    name: str
    subscription_tier: Optional[str]
    is_active: bool
    api_calls_remaining: int = 0
