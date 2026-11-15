from .models import LineItem

RATES = {"food": 0.05, "electronics": 0.18, "books": 0.0}


def line_tax(line: LineItem, taxable_amount: float) -> float:
    return round(taxable_amount * RATES[line.item.category], 2)
