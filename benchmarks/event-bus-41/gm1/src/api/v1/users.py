from src.services.user_service import user_service
from src.services.usage_service import usage_service
from src.schemas.user import CreateUserRequest, UserProfileResponse
from typing import Dict, Any

def handle_create_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    user = user_service.create_user(
        email=payload['email'],
        name=payload.get('name', ''),
        plan_tier=payload.get('plan_tier', 'free')
    )
    return {'user_id': user.id, 'email': user.email}

def handle_get_profile(user_id: str) -> Dict[str, Any]:
    user = user_service.get_user(user_id)
    if not user:
        return {'error': 'not_found'}
    usage = usage_service.check_limit(user_id, 'api_calls')
    return {
        'id': user['id'], 'email': user['email'], 'name': user['name'],
        'plan_tier': user['plan_tier'], 'is_active': user['is_active'],
        'api_calls_remaining': usage.get('remaining', 0)
    }
