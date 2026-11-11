from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CreateCheckoutSessionRequest:
    user_id: str
    plan_tier: str
    success_url: str = 'https://app.example.com/success'
    cancel_url: str = 'https://app.example.com/cancel'

@dataclass
class CheckoutSessionResponse:
    session_id: str
    checkout_url: str

@dataclass
class InvoiceSummary:
    id: str
    amount_dollars: float
    status: str
    due_date: Optional[str] = None

@dataclass
class PaymentRequest:
    user_id: str
    amount_cents: int
    idempotency_key: str
    currency: str = 'usd'
    description: str = ''
