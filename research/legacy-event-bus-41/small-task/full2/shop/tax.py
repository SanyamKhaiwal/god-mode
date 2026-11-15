from .models import LineItem

RATES = {"food": 0.05, "electronics": 0.18, "books": 0.0}
SELLER_STATE = "UP"


def line_tax(line: LineItem, taxable_amount: float) -> float:
    return round(taxable_amount * RATES[line.item.category], 2)


def gst_split(tax: float, customer_state: str) -> dict:
    """Intra-state sales split tax into CGST and SGST; inter-state sales pay IGST."""
    if customer_state == SELLER_STATE:
        half = round(tax / 2, 2)
        return {"cgst": half, "sgst": half, "igst": 0.0}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax}
