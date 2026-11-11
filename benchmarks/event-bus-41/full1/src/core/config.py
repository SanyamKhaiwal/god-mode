import os
from dataclasses import dataclass, field
from typing import Dict, Any

PLAN_TIERS = {
    'free': {'price_cents': 0, 'api_calls': 100, 'storage_mb': 50},
    'starter': {'price_cents': 1999, 'api_calls': 10000, 'storage_mb': 5000},
    'pro': {'price_cents': 4999, 'api_calls': 100000, 'storage_mb': 50000},
    'enterprise': {'price_cents': 14999, 'api_calls': -1, 'storage_mb': -1},
}

@dataclass
class Settings:
    PROJECT_NAME: str = 'EnterpriseBilling'
    API_V1_STR: str = '/api/v1'
    DATABASE_URL: str = 'sqlite:///./billing.db'
    STRIPE_SECRET_KEY: str = 'sk_test_fake_12345'
    STRIPE_PUBLISHABLE_KEY: str = 'pk_test_fake_12345'
    WEBHOOK_SECRET: str = 'whsec_fake_67890'
    TOKEN_EXPIRY_MINUTES: int = 60
    RATE_LIMIT_PER_MINUTE: int = 120
    IDEMPOTENCY_CACHE_TTL: int = 86400
    MAX_RETRY_ATTEMPTS: int = 3
    PRORATION_METHOD: str = 'day'  # 'day' or 'second'
    TAX_RATE_PERCENT: float = 0.0
    CURRENCY: str = 'usd'
    GRACE_PERIOD_DAYS: int = 7

settings = Settings()
