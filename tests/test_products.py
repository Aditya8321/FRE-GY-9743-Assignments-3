"""Independent contract and display checks for the HW3 cashflow products.

Run from the repository root with ``python -m unittest discover -s tests``.
"""

import unittest

import QuantLib as ql

from fixedincomelib import (
    qfCreateProductFixedAccruedCashflow,
    qfCreateProductOvernightIndexCashflow,
    qfDisplayProduct,
)
from fixedincomelib.date.basics import Date, TermOrDate
from fixedincomelib.market.basics import AccrualBasis, Currency
from fixedincomelib.market.data_conventions import CompoundingMethod
from fixedincomelib.product import (
    ProductDisplayVisitor,
    ProductFixedAccruedCashflow,
    ProductOvernightIndexCashflow,
)
from fixedincomelib.product.product_interfaces import ProductVisitor
from fixedincomelib.product.utilities import LongOrShort


class FixedCashflowTests(unittest.TestCase):
    def make_product(self, **changes):
        fields = dict(
            effective_date="2026-01-02",
            termination_date="2026-04-02",
            currency="USD",
            notional=1_000_000,
            accrual_basis="ACT/360",
        )
        fields.update(changes)
        return qfCreateProductFixedAccruedCashflow(**fields)

    def test_contract_dates_and_default_payment(self):
        product = self.make_product()
        self.assertEqual(product.effective_date.ISO(), "2026-01-02")
        self.assertEqual(product.termination_date.ISO(), "2026-04-02")
        self.assertEqual(product.payment_date, product.termination_date)
        self.assertEqual(product.first_date, product.effective_date)
        self.assertEqual(product.last_date, product.payment_date)
        self.assertEqual(product.business_day_convention.value, ql.Following)
        self.assertEqual(product.holiday_convention.value.name(), "US government bond market")
        self.assertEqual(product.accrued, 90 / 360)

    def test_optional_payment_representations(self):
        for payment in (None, ""):
            with self.subTest(payment=payment):
                product = self.make_product(payment_date=payment)
                self.assertEqual(product.payment_date, product.termination_date)
        product = self.make_product(payment_date="2026-04-06")
        self.assertEqual(product.payment_date.ISO(), "2026-04-06")
        self.assertEqual(product.last_date, product.payment_date)
        self.assertEqual(product.accrued, 90 / 360)

    def test_direct_constructor_convention_defaults(self):
        product = ProductFixedAccruedCashflow(
            Date("2026-01-02"), Date("2026-04-02"), Currency("USD"),
            100, AccrualBasis("ACT/360"),
        )
        self.assertEqual(product.business_day_convention.value_str, "F")
        self.assertEqual(product.holiday_convention.value_str, "USGS")
        self.assertEqual(product.payment_date, product.termination_date)

    def test_weekend_end_adjusts_accrual_only(self):
        following = self.make_product(termination_date="2026-01-31")
        modified = self.make_product(
            termination_date="2026-01-31", business_day_convention="MF",
        )
        self.assertEqual(following.termination_date.ISO(), "2026-01-31")
        self.assertEqual(following.payment_date.ISO(), "2026-01-31")
        self.assertEqual(following.accrued, 31 / 360)  # Following: February 2.
        self.assertEqual(modified.accrued, 28 / 360)  # Modified following: January 30.

    def test_holiday_calendar_and_case_insensitive_conventions(self):
        # July 3 is the observed US Independence Day holiday in 2026.
        product = self.make_product(
            effective_date="2026-07-01", termination_date="2026-07-03",
            currency="usd", accrual_basis="act/360",
            business_day_convention="f", holiday_convention="usgs",
        )
        self.assertEqual(product.currency.value_str, "USD")
        self.assertEqual(product.accrued, 5 / 360)  # Following: July 6.
        self.assertEqual(product.termination_date.ISO(), "2026-07-03")

    def test_direction_and_zero_length_accrual(self):
        for notional, direction in ((100, LongOrShort.LONG), (0, LongOrShort.LONG), (-100, LongOrShort.SHORT)):
            with self.subTest(notional=notional):
                product = self.make_product(notional=notional)
                self.assertEqual(product.notional, notional)
                self.assertEqual(product.long_or_short, direction)
        product = self.make_product(termination_date="2026-01-02")
        self.assertEqual(product.accrued, 0)

    def test_invalid_contract_fields(self):
        for changes in (
            {"effective_date": ""}, {"termination_date": ""},
            {"termination_date": "2026-01-01"}, {"currency": "XYZ"},
            {"notional": float("nan")}, {"notional": float("inf")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.make_product(**changes)

    def test_serialization_round_trip(self):
        product = self.make_product(notional=-50, payment_date="2026-04-06")
        restored = ProductFixedAccruedCashflow.deserialize(product.serialize())
        self.assertEqual(restored.serialize(), product.serialize())
        self.assertEqual(restored.accrued, product.accrued)
        self.assertEqual(restored.long_or_short, LongOrShort.SHORT)


class OvernightCashflowTests(unittest.TestCase):
    def make_product(self, **changes):
        fields = dict(
            effective_date="2026-01-02", term_or_termination_date="3M",
            overnight_index="SOFR-1B", notional=-1_000_000,
        )
        fields.update(changes)
        return qfCreateProductOvernightIndexCashflow(**fields)

    def test_tenor_and_date_match_and_default_payment(self):
        tenor = self.make_product()
        explicit = self.make_product(term_or_termination_date="2026-04-02")
        self.assertEqual(tenor.termination_date.ISO(), "2026-04-02")
        self.assertEqual(tenor.termination_date, explicit.termination_date)
        self.assertEqual(tenor.payment_date, tenor.termination_date)
        self.assertEqual(tenor.first_date, tenor.effective_date)
        self.assertEqual(tenor.last_date, tenor.payment_date)
        self.assertEqual(tenor.long_or_short, LongOrShort.SHORT)
        self.assertEqual(tenor.compounding_method, CompoundingMethod.COMPOUND)
        self.assertEqual(tenor.spread, 0)

    def test_weekend_end_adjusts_with_index_calendar(self):
        tenor = self.make_product(effective_date="2026-01-30", term_or_termination_date="1M")
        explicit = self.make_product(effective_date="2026-01-30", term_or_termination_date="2026-02-28")
        self.assertEqual(tenor.termination_date.ISO(), "2026-03-02")
        self.assertEqual(explicit.termination_date, tenor.termination_date)
        self.assertEqual(explicit.payment_date, explicit.termination_date)

    def test_index_currency_and_holiday_calendars(self):
        for key, currency in (("sofr-1b", "USD"), ("fF-1b", "USD"), ("sonia-1B", "GBP")):
            with self.subTest(index=key):
                product = self.make_product(overnight_index=key, notional=100)
                self.assertEqual(product.currency.value_str, currency)
                self.assertEqual(product.serialize()["ON_INDEX"], key.upper())
                self.assertEqual(product.long_or_short, LongOrShort.LONG)
        # The SOFR fixing calendar recognizes the observed US holiday.
        holiday = self.make_product(effective_date="2026-07-01", term_or_termination_date="2026-07-03")
        self.assertEqual(holiday.termination_date.ISO(), "2026-07-06")

    def test_compounding_labels_and_explicit_fields(self):
        for name, method in (("Simple", CompoundingMethod.SIMPLE), ("ARITHMETIC", CompoundingMethod.ARITHMETIC), ("compound", CompoundingMethod.COMPOUND)):
            with self.subTest(method=name):
                product = self.make_product(compounding_method=name, spread=0.001, payment_date="2026-04-06")
                self.assertEqual(product.compounding_method, method)
                self.assertEqual(product.spread, 0.001)
                self.assertEqual(product.payment_date.ISO(), "2026-04-06")
                self.assertEqual(product.last_date, product.payment_date)
                self.assertEqual(product.serialize()["COMPOUNDING_METHOD"], name.upper())

    def test_zero_length_dates_and_optional_payment_representations(self):
        for payment in (None, ""):
            with self.subTest(payment=payment):
                product = self.make_product(term_or_termination_date="2026-01-02", payment_date=payment, notional=0)
                self.assertEqual(product.termination_date, product.effective_date)
                self.assertEqual(product.payment_date, product.termination_date)
                self.assertEqual(product.long_or_short, LongOrShort.LONG)

    def test_invalid_contract_fields(self):
        for changes in (
            {"effective_date": ""}, {"term_or_termination_date": ""},
            {"term_or_termination_date": "2025-12-30"},
            {"overnight_index": "UNKNOWN"}, {"compounding_method": "continuous"},
            {"spread": float("nan")}, {"spread": float("inf")},
            {"notional": float("nan")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.make_product(**changes)
        with self.assertRaises(ValueError):
            ProductOvernightIndexCashflow(
                Date("2026-01-02"), TermOrDate(ql.Period(-1, ql.Months)),
                "SOFR-1B", CompoundingMethod.COMPOUND, 0, 100,
            )
        with self.assertRaises(TypeError):
            ProductOvernightIndexCashflow(
                Date("2026-01-02"), TermOrDate("1M"), "SOFR-1B", "compound", 0, 100,
            )

    def test_serialization_round_trip(self):
        product = self.make_product(overnight_index="sonia-1b", spread=-0.001, payment_date="2026-04-06")
        restored = ProductOvernightIndexCashflow.deserialize(product.serialize())
        self.assertEqual(restored.serialize(), product.serialize())
        self.assertEqual(restored.currency.value_str, "GBP")
        self.assertEqual(restored.long_or_short, LongOrShort.SHORT)


class DisplayVisitorTests(unittest.TestCase):
    def setUp(self):
        self.fixed = qfCreateProductFixedAccruedCashflow(
            "2026-01-02", "2026-04-02", "USD", 100, "ACT/360",
        )
        self.overnight = qfCreateProductOvernightIndexCashflow(
            "2026-01-02", "3M", "sofr-1b", -200, "arithmetic", 0.001,
        )

    def test_fixed_display_order_and_types(self):
        table = qfDisplayProduct(self.fixed)
        self.assertEqual(list(table.columns), ["Name", "Value"])
        self.assertEqual(table["Name"].tolist(), [
            "Product Type", "Notional", "Currency", "Long Or Short", "Effective Date",
            "Termination Date", "Accrual Basis", "Payment Date",
            "Business Day Convention", "Holiday Convention",
        ])
        self.assertEqual(table["Value"].tolist(), [
            "PRODUCT_FIXED_ACCRUED", 100, "USD", "LONG", "2026-01-02",
            "2026-04-02", "ACT/360", "2026-04-02", "F", "USGS",
        ])

    def test_overnight_display_order_and_types(self):
        table = qfDisplayProduct(self.overnight)
        self.assertEqual(table["Name"].tolist(), [
            "Product Type", "Notional", "Currency", "Long Or Short", "Effective Date",
            "Termination Date", "ON Index", "Compounding Method", "Spread", "Payment Date",
        ])
        self.assertEqual(table["Value"].tolist(), [
            "PRODUCT_OVERNIGHT_INDEX_CASHFLOW", -200, "USD", "SHORT", "2026-01-02",
            "2026-04-02", "SOFR-1B", "ARITHMETIC", 0.001, "2026-04-02",
        ])

    def test_reused_visitor_replaces_rows_without_changing_old_table(self):
        visitor = ProductDisplayVisitor()
        self.fixed.accept(visitor)
        earlier = visitor.display()
        earlier_values = earlier["Value"].tolist()
        self.overnight.accept(visitor)
        latest = visitor.display()
        self.assertEqual(len(latest), 10)
        self.assertIn("ON Index", latest["Name"].tolist())
        self.assertNotIn("Accrual Basis", latest["Name"].tolist())
        self.assertEqual(earlier["Value"].tolist(), earlier_values)

    def test_accept_returns_the_visitor_result(self):
        class RecordingVisitor(ProductVisitor):
            def visit(self, product):
                return ("visited", product)

        visitor = RecordingVisitor()
        for product in (self.fixed, self.overnight):
            with self.subTest(product=product.product_type):
                self.assertEqual(product.accept(visitor), ("visited", product))

    def test_display_rejects_nonproducts(self):
        with self.assertRaises(TypeError):
            qfDisplayProduct(object())


if __name__ == "__main__":
    unittest.main()
