import unittest
from shop.models import Item, Cart
from shop.invoice import build_invoice
from unittest.mock import patch
from shop.discounts import coupon_discount, total_discount

PHONE = Item("E1", "Phone", 6000.0, "electronics")
RICE = Item("F1", "Rice", 100.0, "food")
BOOK = Item("B1", "Book", 300.0, "books")


class InvoiceTests(unittest.TestCase):
    def test_small_cart(self):
        c = Cart("UP"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 0.0, "cgst": 5.0, "sgst": 5.0,
                                            "igst": 0.0, "tax": 10.0, "total": 510.0})

    def test_bulk_discount(self):
        c = Cart("UP"); c.add(PHONE)
        self.assertEqual(build_invoice(c), {"subtotal": 6000.0, "discount": 300.0, "cgst": 513.0, "sgst": 513.0,
                                            "igst": 0.0, "tax": 1026.0, "total": 6726.0})

    def test_save10_food_and_books_only(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK); c.add(PHONE)
        # eligible 500 -> 50, plus bulk 5% of 6500 = 325
        self.assertEqual(coupon_discount(c), 50.0)
        self.assertEqual(build_invoice(c)["discount"], 375.0)

    def test_save10_invoice(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 50.0, "cgst": 4.5, "sgst": 4.5,
                                            "igst": 0.0, "tax": 9.0, "total": 459.0})

    def test_flat500_with_bulk_inter_state(self):
        c = Cart("MH", coupon="FLAT500"); c.add(PHONE)
        self.assertEqual(build_invoice(c), {"subtotal": 6000.0, "discount": 800.0, "cgst": 0.0, "sgst": 0.0,
                                            "igst": 936.0, "tax": 936.0, "total": 6136.0})

    def test_flat500_below_threshold(self):
        c = Cart("UP", coupon="FLAT500"); c.add(RICE, 2)
        self.assertEqual(coupon_discount(c), 0.0)
        c2 = Cart("UP", coupon="FLAT500"); c2.add(BOOK, 7)  # 2100
        self.assertEqual(coupon_discount(c2), 500.0)

    def test_discount_capped_at_subtotal(self):
        c = Cart("UP", coupon="FLAT500"); c.add(RICE, 2)  # subtotal 200
        with patch("shop.discounts.coupon_discount", return_value=500.0):
            self.assertEqual(total_discount(c), 200.0)
            self.assertEqual(build_invoice(c)["total"], 0.0)

    def test_unknown_coupon(self):
        c = Cart("UP", coupon="BOGUS"); c.add(RICE)
        with self.assertRaisesRegex(ValueError, "unknown coupon"):
            build_invoice(c)

    def test_qty_validation(self):
        c = Cart("UP")
        with self.assertRaises(ValueError):
            c.add(RICE, 0)
        with self.assertRaises(ValueError):
            c.add(RICE, -1)
        self.assertEqual(c.lines, [])

    def test_inter_state_small_cart(self):
        c = Cart("MH"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 0.0, "cgst": 0.0, "sgst": 0.0,
                                            "igst": 10.0, "tax": 10.0, "total": 510.0})


if __name__ == "__main__":
    unittest.main()
