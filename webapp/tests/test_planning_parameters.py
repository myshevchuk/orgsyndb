"""Tests of the planning parameters (production-planning: Planning
parameters)."""

from statistics import NormalDist

from django.core.exceptions import ValidationError
from django.test import TestCase

from planning.models import Parameters

from . import make_user, page
from .planning_support import DEFAULTS

ADMIN = "/lab/admin/planning/parameters/"


def errors(**over) -> dict[str, list[str]]:
    """The errors ``full_clean`` finds in the defaults changed by
    ``over``, by field; empty when there are none."""
    try:
        Parameters(**{**DEFAULTS, **over}).full_clean()
    except ValidationError as error:
        return error.message_dict
    return {}


class DefaultTests(TestCase):

    def test_defaults(self) -> None:
        """Scenario: Defaults."""
        found = Parameters.current()
        self.assertEqual(
            {name: getattr(found, name) for name in DEFAULTS}, DEFAULTS)
        self.assertAlmostEqual(found.z, 1.6449, places=4)

    def test_without_a_record_the_current_one_is_not_stored(self) -> None:
        found = Parameters.current()
        self.assertIsNone(found.pk)
        self.assertEqual(Parameters.objects.count(), 0)

    def test_a_stored_record_is_the_current_one(self) -> None:
        stored = Parameters.objects.create(
            **{**DEFAULTS, "certainty": 0.9, "buffer_days": 40})
        found = Parameters.current()
        self.assertEqual(found.pk, stored.pk)
        self.assertEqual((found.certainty, found.buffer_days), (0.9, 40))
        self.assertEqual(found.target_days, 365)

    def test_z_is_the_inverse_of_the_normal_distribution(self) -> None:
        for certainty in (0.5, 0.9, 0.95, 0.975, 0.999):
            with self.subTest(certainty=certainty):
                found = Parameters(**{**DEFAULTS, "certainty": certainty})
                self.assertAlmostEqual(
                    found.z, NormalDist().inv_cdf(certainty), places=12)
        self.assertEqual(Parameters(**{**DEFAULTS, "certainty": 0.5}).z, 0)

    def test_the_defaults_pass_validation(self) -> None:
        self.assertEqual(errors(), {})


class RangeTests(TestCase):

    def test_each_range_holds_its_limits(self) -> None:
        cases = [
            ("certainty", (0.5, 0.999), (0.49, 0.9991, 1.0, 0.0)),
            ("buffer_days", (0, 365), (-1, 366)),
            ("default_synthesis_days", (1, 730), (0, 731)),
            ("history_quarters", (4, 40), (3, 41)),
            ("min_orders", (3, 100), (2, 101)),
            ("target_days", (30, 1095), (29, 1096)),
        ]
        for field, inside, outside in cases:
            for value in inside:
                with self.subTest(field=field, value=value):
                    self.assertNotIn(field, errors(**{field: value}))
            for value in outside:
                with self.subTest(field=field, value=value):
                    self.assertIn(field, errors(**{field: value}))

    def test_the_bands_are_ordered(self) -> None:
        self.assertEqual(errors(high_days=0, medium_days=1), {})
        self.assertEqual(errors(high_days=13, medium_days=14), {})
        for high, medium in ((14, 14), (60, 56), (1, 0), (56, 14)):
            with self.subTest(high=high, medium=medium):
                self.assertTrue(errors(high_days=high, medium_days=medium))

    def test_the_high_band_is_not_negative(self) -> None:
        self.assertTrue(errors(high_days=-1, medium_days=56))


class HistoryTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_creation_and_changes_are_kept(self) -> None:
        record = Parameters.objects.create(**DEFAULTS)
        self.assertEqual(record.history.count(), 1)
        record._history_user = self.kl
        record.buffer_days = 35
        record.save()
        self.assertEqual(record.history.count(), 2)
        newest = record.history.first()
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(newest.buffer_days, 35)
        self.assertEqual(record.history.last().buffer_days, 28)


class AdminTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.worker = make_user("worker", "WO")

    def setUp(self) -> None:
        self.client.force_login(self.staff)

    def data(self, **over) -> dict[str, str]:
        return {name: str(value)
                for name, value in {**DEFAULTS, **over}.items()}

    def test_staff_reach_the_parameters(self) -> None:
        self.assertEqual(self.client.get(ADMIN).status_code, 200)

    def test_others_are_kept_out(self) -> None:
        self.client.force_login(self.worker)
        done = self.client.get(ADMIN)
        self.assertIn(done.status_code, (302, 403))
        self.client.logout()
        done = self.client.get(ADMIN)
        self.assertEqual(done.status_code, 302)
        self.assertTrue(done["Location"].startswith("/lab/admin/login/"))

    def test_the_form_offers_every_parameter(self) -> None:
        record = Parameters.objects.create(**DEFAULTS)
        done = self.client.get(f"{ADMIN}{record.pk}/change/")
        self.assertEqual(done.status_code, 200)
        root = page(done)
        for name in DEFAULTS:
            with self.subTest(name=name):
                self.assertIsNotNone(root.find(("input", "select"),
                                               name=name))

    def test_a_record_can_be_added_when_none_exists(self) -> None:
        done = self.client.post(f"{ADMIN}add/", self.data(buffer_days=30))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Parameters.current().buffer_days, 30)

    def test_a_change_is_saved_and_kept_in_the_history(self) -> None:
        record = Parameters.objects.create(**DEFAULTS)
        done = self.client.post(f"{ADMIN}{record.pk}/change/",
                                self.data(certainty=0.9, high_days=10))
        self.assertEqual(done.status_code, 302)
        record.refresh_from_db()
        self.assertEqual((record.certainty, record.high_days), (0.9, 10))
        self.assertEqual(record.history.count(), 2)
        self.assertEqual(record.history.first().history_user, self.staff)

    def test_bands_out_of_order(self) -> None:
        """Scenario: Bands out of order."""
        record = Parameters.objects.create(**DEFAULTS)
        done = self.client.post(
            f"{ADMIN}{record.pk}/change/",
            self.data(high_days=60, medium_days=56))
        self.assertEqual(done.status_code, 200)
        self.assertIsNotNone(page(done).find(cls="errorlist")
                             or page(done).find(cls="errornote"))
        record.refresh_from_db()
        self.assertEqual((record.high_days, record.medium_days), (14, 56))
        self.assertEqual(record.history.count(), 1)
        self.assertEqual(Parameters.current().high_days, 14)

    def test_a_value_out_of_range_is_refused(self) -> None:
        record = Parameters.objects.create(**DEFAULTS)
        for field, value in (("certainty", 0.4), ("buffer_days", 400),
                             ("history_quarters", 3), ("min_orders", 2)):
            with self.subTest(field=field):
                done = self.client.post(f"{ADMIN}{record.pk}/change/",
                                        self.data(**{field: value}))
                self.assertEqual(done.status_code, 200)
                record.refresh_from_db()
                self.assertEqual(getattr(record, field), DEFAULTS[field])
