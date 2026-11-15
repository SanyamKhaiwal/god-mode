from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time

class PaymentStatus(str, Enum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    REFUNDED = 'refunded'

@dataclass
class Payment:
    id: str
    user_id: str
    invoice_id: Optional[str]
    amount_cents: int
    currency: str = 'usd'
    status: PaymentStatus = PaymentStatus.PENDING
    stripe_payment_intent_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    error_message: Optional[str] = None
    refund_reason: Optional[str] = None
