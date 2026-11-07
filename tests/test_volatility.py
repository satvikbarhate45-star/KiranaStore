import unittest
from app.services.volatility_engine import (
    calculate_volatility_badge,
    calculate_basket_status
)

class TestVolatilityEngine(unittest.TestCase):
    def test_badge_precedence_no_baseline(self):
        badge, var = calculate_volatility_badge(45.0, None)
        self.assertEqual(badge, "नवीन नोंद")
        self.assertIsNone(var)

    def test_badge_balanced(self):
        # Baseline = 40.0, Derived = 41.0 (+2.5% -> balanced)
        badge, var = calculate_volatility_badge(41.0, 40.0)
        self.assertEqual(badge, "संतुलित")
        self.assertAlmostEqual(var, 2.5, places=1)

    def test_badge_surge(self):
        # Baseline = 40.0, Derived = 43.0 (+7.5% -> surge > 6%)
        badge, var = calculate_volatility_badge(43.0, 40.0)
        self.assertEqual(badge, "भाववाढ")
        self.assertAlmostEqual(var, 7.5, places=1)

    def test_badge_dip(self):
        # Baseline = 40.0, Derived = 38.0 (-5.0% -> dip < -2%)
        badge, var = calculate_volatility_badge(38.0, 40.0)
        self.assertEqual(badge, "स्वस्त")
        self.assertAlmostEqual(var, -5.0, places=1)

    def test_basket_status_balanced(self):
        items = [
            {"entered_total": 200.0, "baseline_rate": 40.0, "quantity_norm": 5.0}, # exp 200
            {"entered_total": 350.0, "baseline_rate": 170.0, "quantity_norm": 2.0} # exp 340
        ]
        status, var, new_c = calculate_basket_status(items)
        # Total entered: 550, Total expected: 540 -> +1.85% <= 5% -> balanced
        self.assertEqual(status, "संतुलित बजेट")
        self.assertLessEqual(var, 5.0)

    def test_basket_status_unbalanced(self):
        items = [
            {"entered_total": 250.0, "baseline_rate": 40.0, "quantity_norm": 5.0}, # exp 200 (+25%)
        ]
        status, var, new_c = calculate_basket_status(items)
        self.assertEqual(status, "असंतुलित खर्च")
        self.assertGreater(var, 5.0)

if __name__ == "__main__":
    unittest.main()
