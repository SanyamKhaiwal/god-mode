import unittest
from shop.models import Item, Cart
from shop.invoice import build_invoice

PHONE = Item("E1", "Phone", 6000.0, "electronics"); RICE = Item("F1", "Rice", 100.0, "food"); BOOK = Item("B1", "Book", 300.0, "books")

class Hidden(unittest.TestCase):
    def test_save10_intrastate(self):
        c = Cart("UP"); c.add(RICE, 2); c.add(BOOK); c.coupon = "SAVE10"
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 50.0, "cgst": 4.5, "sgst": 4.5, "igst": 0.0, "tax": 9.0, "total": 459.0})
    def test_flat500_bulk_interstate(self):
        c = Cart("MH"); c.add(PHONE); c.coupon = "FLAT500"
        self.assertEqual(build_invoice(c), {"subtotal": 6000.0, "discount": 800.0, "cgst": 0.0, "sgst": 0.0, "igst": 936.0, "tax": 936.0, "total": 6136.0})
    def test_flat500_below_threshold(self):
        c = Cart("UP"); c.add(BOOK); c.coupon = "FLAT500"
        self.assertEqual(build_invoice(c)["discount"], 0.0)
    def test_unknown(self):
        c = Cart("UP"); c.add(BOOK); c.coupon = "BOGUS"
        with self.assertRaises(ValueError): build_invoice(c)
    def test_qty(self):
        with self.assertRaises(ValueError): Cart("UP").add(BOOK, 0)
