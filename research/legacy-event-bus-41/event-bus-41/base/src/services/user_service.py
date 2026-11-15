from src.core.database import db
from src.core.security import generate_api_key, hash_token
from src.core.telemetry import telemetry
from src.models.user import User
from src.core.config import PLAN_TIERS
from typing import Optional, Dict, Any

class UserService:
    def create_user(self, email: str, name: str = '', plan_tier: str = 'free') -> User:
        user_id = f'usr_{len(db.users) + 1}'
        user = User(id=user_id, email=email, name=name, plan_tier=plan_tier)
        db.users[user_id] = {
            'id': user_id, 'email': email, 'name': name,
            'plan_tier': plan_tier, 'is_active': True, 'is_admin': False,
            'stripe_customer_id': None, 'api_key_hash': None,
            'usage_this_period': 0
        }
        telemetry.increment('user.created')
        return user

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return db.users.get(user_id)

    def generate_user_api_key(self, user_id: str) -> Optional[str]:
        user = db.users.get(user_id)
        if not user:
            return None
        raw_key, hashed = generate_api_key()
        user['api_key_hash'] = hashed
        return raw_key

    def check_usage_limit(self, user_id: str) -> bool:
        user = db.users.get(user_id)
        if not user:
            return False
        tier = user.get('plan_tier', 'free')
        limit = PLAN_TIERS.get(tier, {}).get('api_calls', 100)
        if limit == -1:
            return True
        return user.get('usage_this_period', 0) < limit

    def record_api_call(self, user_id: str):
        user = db.users.get(user_id)
        if user:
            user['usage_this_period'] = user.get('usage_this_period', 0) + 1
            telemetry.increment('api.call')

user_service = UserService()
