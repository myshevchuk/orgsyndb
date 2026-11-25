"""Pure-function tests of stock age calculations and labels
(end-product-inventory: Lists by substance).
"""

from datetime import date

from django.test import SimpleTestCase
from django.utils import translation

from inventory.summaries import age_label, is_old, months_between


class MonthsBetweenTests(SimpleTestCase):

    def test_ages_scenario_months(self) -> None:
        """Scenario: Ages (whole calendar months)."""
        today = date(2026, 11, 24)
        self.assertEqual(months_between(date(2026, 11, 20), today), 0)
        self.assertEqual(months_between(date(2026, 4, 6), today), 7)
        self.assertEqual(months_between(date(2025, 5, 1), today), 18)
        self.assertEqual(months_between(date(2025, 11, 24), today), 12)

    def test_month_ends_scenario(self) -> None:
        """Scenario: Month ends."""
        self.assertEqual(
            months_between(date(2026, 1, 31), date(2026, 2, 28)), 1)
        self.assertEqual(
            months_between(date(2026, 1, 31), date(2026, 2, 27)), 0)

    def test_eleven_months_thirty_days(self) -> None:
        self.assertEqual(
            months_between(date(2025, 11, 25), date(2026, 11, 24)), 11)

    def test_leap_year_months(self) -> None:
        self.assertEqual(
            months_between(date(2028, 1, 31), date(2028, 2, 29)), 1)
        self.assertEqual(
            months_between(date(2028, 1, 31), date(2028, 2, 28)), 0)
        self.assertEqual(
            months_between(date(2028, 1, 29), date(2028, 2, 29)), 1)
        self.assertEqual(
            months_between(date(2028, 2, 29), date(2029, 2, 28)), 12)
        self.assertEqual(
            months_between(date(2028, 2, 29), date(2029, 2, 27)), 11)
        self.assertEqual(
            months_between(date(2028, 2, 29), date(2032, 2, 29)), 48)
        self.assertEqual(
            months_between(date(2027, 2, 28), date(2028, 2, 28)), 12)
        self.assertEqual(
            months_between(date(2027, 2, 28), date(2028, 2, 29)), 12)


class AgeLabelTests(SimpleTestCase):

    def test_ages_scenario_labels(self) -> None:
        """Scenario: Ages."""
        today = date(2026, 11, 24)
        with translation.override("de"):
            self.assertEqual(age_label(date(2026, 11, 20), today), "4 Tage")
            self.assertEqual(age_label(date(2026, 4, 6), today), "7 Mon.")
            self.assertEqual(age_label(date(2025, 5, 1), today), "1 J 6 Mon.")
            self.assertEqual(age_label(date(2025, 11, 24), today), "1 J")
        with translation.override("en"):
            self.assertEqual(age_label(date(2026, 11, 20), today), "4 days")
            self.assertEqual(age_label(date(2026, 4, 6), today), "7 mo.")
            self.assertEqual(age_label(date(2025, 5, 1), today), "1 y 6 mo.")
            self.assertEqual(age_label(date(2025, 11, 24), today), "1 y")

    def test_month_ends_labels(self) -> None:
        """Scenario: Month ends."""
        with translation.override("de"):
            self.assertEqual(
                age_label(date(2026, 1, 31), date(2026, 2, 28)), "1 Mon.")
            self.assertEqual(
                age_label(date(2026, 1, 31), date(2026, 2, 27)), "27 Tage")
        with translation.override("en"):
            self.assertEqual(
                age_label(date(2026, 1, 31), date(2026, 2, 28)), "1 mo.")
            self.assertEqual(
                age_label(date(2026, 1, 31), date(2026, 2, 27)), "27 days")

    def test_zero_and_one_day(self) -> None:
        today = date(2026, 11, 24)
        with translation.override("de"):
            self.assertEqual(age_label(today, today), "heute")
            self.assertEqual(age_label(date(2026, 11, 23), today), "1 Tag")
        with translation.override("en"):
            self.assertEqual(age_label(today, today), "today")
            self.assertEqual(age_label(date(2026, 11, 23), today), "1 day")

    def test_boundary_before_and_at_twelve_months(self) -> None:
        today = date(2026, 11, 24)
        with translation.override("de"):
            self.assertEqual(
                age_label(date(2025, 11, 25), today), "11 Mon.")
            self.assertEqual(age_label(date(2025, 11, 24), today), "1 J")
            self.assertEqual(
                age_label(date(2024, 11, 24), today), "2 J")
            self.assertEqual(
                age_label(date(2024, 10, 24), today), "2 J 1 Mon.")
        with translation.override("en"):
            self.assertEqual(
                age_label(date(2025, 11, 25), today), "11 mo.")
            self.assertEqual(age_label(date(2025, 11, 24), today), "1 y")
            self.assertEqual(
                age_label(date(2024, 11, 24), today), "2 y")
            self.assertEqual(
                age_label(date(2024, 10, 24), today), "2 y 1 mo.")

    def test_leap_year_labels(self) -> None:
        with translation.override("de"):
            self.assertEqual(
                age_label(date(2028, 1, 31), date(2028, 2, 28)), "28 Tage")
            self.assertEqual(
                age_label(date(2028, 1, 31), date(2028, 2, 29)), "1 Mon.")
            self.assertEqual(
                age_label(date(2028, 2, 29), date(2029, 2, 27)), "11 Mon.")
            self.assertEqual(
                age_label(date(2028, 2, 29), date(2029, 2, 28)), "1 J")
        with translation.override("en"):
            self.assertEqual(
                age_label(date(2028, 1, 31), date(2028, 2, 28)), "28 days")
            self.assertEqual(
                age_label(date(2028, 1, 31), date(2028, 2, 29)), "1 mo.")
            self.assertEqual(
                age_label(date(2028, 2, 29), date(2029, 2, 27)), "11 mo.")
            self.assertEqual(
                age_label(date(2028, 2, 29), date(2029, 2, 28)), "1 y")


class IsOldTests(SimpleTestCase):

    def test_a_year_or_more_is_old(self) -> None:
        today = date(2026, 11, 24)
        self.assertFalse(is_old(today, today))
        self.assertFalse(is_old(date(2026, 11, 23), today))
        self.assertFalse(is_old(date(2026, 4, 6), today))
        self.assertFalse(is_old(date(2025, 11, 25), today))
        self.assertTrue(is_old(date(2025, 11, 24), today))
        self.assertTrue(is_old(date(2025, 5, 1), today))

    def test_leap_year_old_threshold(self) -> None:
        self.assertFalse(is_old(date(2028, 2, 29), date(2029, 2, 27)))
        self.assertTrue(is_old(date(2028, 2, 29), date(2029, 2, 28)))
        self.assertTrue(is_old(date(2028, 2, 29), date(2032, 2, 29)))
