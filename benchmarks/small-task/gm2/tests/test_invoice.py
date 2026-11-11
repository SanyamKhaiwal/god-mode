import unittest
from shop.models import Item, Cart
from shop.invoice import build_invoice

PHONE = Item("E1", "Phone", 6000.0, "electronics")
RICE = Item("F1", "Rice", 100.0, "food")
BOOK = Item("B1", "Book", 300.0, "books")


def invoice(subtotal, discount, cgst, sgst, igst, tax, total):
    return {"subtotal": subtotal, "discount": discount, "cgst": cgst, "sgst": sgst,
            "igst": igst, "tax": tax, "total": total}


class InvoiceTests(unittest.TestCase):
    def test_small_cart(self):
        c = Cart("UP"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), invoice(500.0, 0.0, 5.0, 5.0, 0.0, 10.0, 510.0))

    def test_bulk_discount(self):
        c = Cart("UP"); c.add(PHONE)
        self.assertEqual(build_invoice(c), invoice(6000.0, 300.0, 513.0, 513.0, 0.0, 1026.0, 6726.0))

    def test_inter_state_uses_igst(self):
        c = Cart("MH"); c.add(PHONE)
        self.assertEqual(build_invoice(c), invoice(6000.0, 300.0, 0.0, 0.0, 1026.0, 1026.0, 6726.0))

    def test_save10_only_food_and_books(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK); c.add(PHONE)
        # bulk 5% of 6500 = 325, SAVE10 10% of 500 = 50
        inv = build_invoice(c)
        self.assertEqual(inv["discount"], 375.0)

    def test_save10_invoice(self):
        c = Cart("UP", coupon="SAVE10"); c.add(RICE, 2); c.add(BOOK)
        self.assertEqual(build_invoice(c), invoice(500.0, 50.0, 4.5, 4.5, 0.0, 9.0, 459.0))

    def test_flat500_at_threshold(self):
        c = Cart("UP", coupon="FLAT500"); c.add(RICE, 20)
        self.assertEqual(build_invoice(c), invoice(2000.0, 500.0, 37.5, 37.5, 0.0, 75.0, 1575.0))

    def test_flat500_below_threshold(self):
        c = Cart("UP", coupon="FLAT500"); c.add(RICE, 19)
        self.assertEqual(build_invoice(c)["discount"], 0.0)

    def test_unknown_coupon(self):
        c = Cart("UP", coupon="BOGUS"); c.add(RICE)
        with self.assertRaisesRegex(ValueError, "unknown coupon"):
            build_invoice(c)

    def test_qty_must_be_positive(self):
        c = Cart("UP")
        for qty in (0, -1):
            with self.assertRaises(ValueError):
                c.add(RICE, qty)
        self.assertEqual(c.lines, [])


if __name__ == "__main__":
    unittest.main()
