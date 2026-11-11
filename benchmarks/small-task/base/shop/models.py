from dataclasses import dataclass, field


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

    def add(self, item: Item, qty: int = 1):
        self.lines.append(LineItem(item, qty))
