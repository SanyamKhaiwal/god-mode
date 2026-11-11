from src.core.security import verify_api_key, hash_token, rate_limiter
from src.core.database import db
from src.core.exceptions import RateLimitExceededError, InsufficientPermissionsError
from src.services.user_service import user_service
from typing import Dict, Any, Optional

def authenticate_request(api_key: str) -> Dict[str, Any]:
    hashed = hash_token(api_key)
    for uid, user in db.users.items():
        if user.get('api_key_hash') == hashed:
            if not user.get('is_active', True):
                raise InsufficientPermissionsError(uid, 'api_access')
            if not rate_limiter.check(uid):
                raise RateLimitExceededError(uid, rate_limiter.max_per_minute)
            user_service.record_api_call(uid)
            return {'user_id': uid, 'plan_tier': user.get('plan_tier', 'free')}
    return None

def require_admin(user_data: Dict[str, Any]) -> bool:
    user = db.users.get(user_data.get('user_id', ''))
    if not user or not user.get('is_admin'):
        raise InsufficientPermissionsError(user_data.get('user_id', ''), 'admin')
    return True
