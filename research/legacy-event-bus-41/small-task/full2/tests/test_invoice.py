import unittest
from shop.models import Item, Cart
from shop.invoice import build_invoice
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

    def test_inter_state_uses_igst(self):
        c = Cart("MH"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 0.0, "cgst": 0.0, "sgst": 0.0,
                                            "igst": 10.0, "tax": 10.0, "total": 510.0})

    def test_save10_only_food_and_books(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK); c.add(PHONE)
        self.assertEqual(coupon_discount(c), 50.0)
        # bulk 5% of 6500 = 325, plus 50
        self.assertEqual(total_discount(c), 375.0)

    def test_save10_invoice(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), {"subtotal": 500.0, "discount": 50.0, "cgst": 4.5, "sgst": 4.5,
                                            "igst": 0.0, "tax": 9.0, "total": 459.0})

    def test_flat500_with_bulk_inter_state(self):
        c = Cart("MH", coupon="FLAT500"); c.add(PHONE)
        self.assertEqual(build_invoice(c), {"subtotal": 6000.0, "discount": 800.0, "cgst": 0.0, "sgst": 0.0,
                                            "igst": 936.0, "tax": 936.0, "total": 6136.0})

    def test_flat500_threshold(self):
        c = Cart("UP", coupon="FLAT500"); c.add(RICE, 19)
        self.assertEqual(coupon_discount(c), 0.0)
        c.add(RICE)
        self.assertEqual(coupon_discount(c), 500.0)

    def test_no_coupon_is_zero(self):
        c = Cart("UP"); c.add(RICE)
        self.assertEqual(coupon_discount(c), 0.0)

    def test_unknown_coupon(self):
        c = Cart("UP", coupon="BOGUS"); c.add(RICE)
        with self.assertRaisesRegex(ValueError, "unknown coupon"):
            build_invoice(c)

    def test_add_rejects_non_positive_qty(self):
        c = Cart("UP")
        for qty in (0, -1):
            with self.assertRaises(ValueError):
                c.add(RICE, qty)
        self.assertEqual(c.lines, [])


if __name__ == "__main__":
    unittest.main()
