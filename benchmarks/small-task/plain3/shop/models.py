from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Item:
    sku: str
    name: str
    unit_price: float  # in rupees
    category: str      # "food", "electronics", "books"


@dataclass
class LineItem:
    item: Item
    qty: int


@dataclass
class Cart:
    customer_state: str           # e.g. "UP", "MH"
    lines: list = field(default_factory=list)
    coupon: Optional[str] = None

    def add(self, item: Item, qty: int = 1):
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.lines.append(LineItem(item, qty))
