from src.core.database import db
from src.core.telemetry import telemetry
from src.core.config import PLAN_TIERS
from src.models.usage import UsageRecord
from typing import Dict, Any, List
import time

class UsageService:
    def record_usage(self, user_id: str, subscription_id: str,
                     metric: str, quantity: int) -> UsageRecord:
        rec_id = f'usage_{len(db.usage_records) + 1}'
        record = UsageRecord(
            id=rec_id, user_id=user_id, subscription_id=subscription_id,
            metric=metric, quantity=quantity
        )
        db.usage_records.append({
            'id': rec_id, 'user_id': user_id, 'subscription_id': subscription_id,
            'metric': metric, 'quantity': quantity, 'recorded_at': time.time()
        })
        telemetry.increment(f'usage.{metric}', quantity)
        return record

    def get_period_usage(self, user_id: str, metric: str,
                          period_start: float = 0) -> int:
        total = 0
        for rec in db.usage_records:
            if (rec['user_id'] == user_id and rec['metric'] == metric
                    and rec['recorded_at'] >= period_start):
                total += rec['quantity']
        return total

    def check_limit(self, user_id: str, metric: str) -> Dict[str, Any]:
        user = db.users.get(user_id)
        if not user:
            return {'allowed': False, 'reason': 'user_not_found'}
        tier = user.get('plan_tier', 'free')
        limit = PLAN_TIERS.get(tier, {}).get(metric, 0)
        if limit == -1:
            return {'allowed': True, 'remaining': float('inf')}
        used = self.get_period_usage(user_id, metric)
        return {'allowed': used < limit, 'used': used, 'limit': limit,
                'remaining': max(0, limit - used)}

usage_service = UsageService()
