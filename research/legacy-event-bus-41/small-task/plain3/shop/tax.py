from .models import LineItem

RATES = {"food": 0.05, "electronics": 0.18, "books": 0.0}


def line_tax(line: LineItem, taxable_amount: float) -> float:
    return round(taxable_amount * RATES[line.item.category], 2)

SELLER_STATE = "UP"


def split_tax(tax: float, customer_state: str) -> dict:
    """Split tax into CGST/SGST (intra-state) or IGST (inter-state)."""
    if customer_state == SELLER_STATE:
        half = round(tax / 2, 2)
        return {"cgst": half, "sgst": half, "igst": 0.0}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax}
