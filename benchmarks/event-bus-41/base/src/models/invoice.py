from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import time

class InvoiceStatus(str, Enum):
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    VOID = 'void'
    UNCOLLECTIBLE = 'uncollectible'

@dataclass
class LineItem:
    description: str
    amount_cents: int
    quantity: int = 1

@dataclass
class Invoice:
    id: str
    user_id: str
    subscription_id: Optional[str]
    line_items: List[LineItem] = field(default_factory=list)
    subtotal_cents: int = 0
    tax_cents: int = 0
    total_cents: int = 0
    currency: str = 'usd'
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    paid_at: Optional[float] = None
    due_date: Optional[float] = None

    def calculate_totals(self, tax_rate: float = 0.0):
        self.subtotal_cents = sum(item.amount_cents * item.quantity for item in self.line_items)
        self.tax_cents = int(self.subtotal_cents * tax_rate / 100)
        self.total_cents = self.subtotal_cents + self.tax_cents
