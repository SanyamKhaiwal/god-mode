import unittest
from shop.models import Item, Cart
from shop.invoice import build_invoice

PHONE = Item("E1", "Phone", 6000.0, "electronics")
RICE = Item("F1", "Rice", 100.0, "food")
BOOK = Item("B1", "Book", 300.0, "books")


class InvoiceTests(unittest.TestCase):
    def test_small_cart(self):
        c = Cart("UP"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 0.0, "tax": 10.0, "total": 510.0})

    def test_bulk_discount(self):
        c = Cart("UP"); c.add(PHONE)
        self.assertEqual(build_invoice(c), {"subtotal": 6000.0, "discount": 300.0, "tax": 1026.0, "total": 6726.0})


if __name__ == "__main__":
    unittest.main()
