"""Tests of the demo data set as plain data: the list of changes
``demo.data.changes`` gives for a seeding day (lab-demo: Recorded past).

Each change is a dataclass with a ``moment``, an aware datetime; every
other date it holds is one the record it makes names.
"""

import dataclasses
from datetime import date, datetime, time

from django.test import SimpleTestCase

from . import BERLIN
from .demo_support import SEEDING_DAYS, opening


def changes(day: date, language: str = "de") -> list:
    from demo import data
    return data.changes(day, language)


def named_dates(change) -> list[date]:
    found = []
    for field in dataclasses.fields(change):
        value = getattr(change, field.name)
        if isinstance(value, date) and not isinstance(value, datetime):
            found.append(value)
        if isinstance(value, dict):
            found += [v for v in value.values()
                      if isinstance(v, date) and not isinstance(v, datetime)]
    return found


class ChangeListTests(SimpleTestCase):

    def test_moments_lie_from_the_opening_to_the_seeding_day(self) -> None:
        for day in SEEDING_DAYS:
            found = changes(day)
            first = datetime.combine(opening(day), time(8), BERLIN)
            last = datetime.combine(day, time(18), BERLIN)
            with self.subTest(day=day):
                self.assertTrue(found)
                for change in found:
                    moment = change.moment.astimezone(BERLIN)
                    self.assertGreaterEqual(moment, first, change)
                    self.assertLessEqual(moment, last, change)
                    self.assertGreaterEqual(moment.time(), time(8), change)
                    self.assertLessEqual(moment.time(), time(18), change)

    def test_moments_rise(self) -> None:
        for day in SEEDING_DAYS:
            moments = [change.moment for change in changes(day)]
            with self.subTest(day=day):
                self.assertEqual(moments, sorted(moments))
                self.assertEqual(len(moments), len(set(moments)))

    def test_no_named_date_after_its_moment(self) -> None:
        for day in SEEDING_DAYS:
            for change in changes(day):
                made = change.moment.astimezone(BERLIN).date()
                for named in named_dates(change):
                    with self.subTest(day=day, change=type(change).__name__):
                        self.assertLessEqual(named, made)

    def test_the_list_depends_only_on_the_day(self) -> None:
        day = SEEDING_DAYS[0]
        self.assertEqual(changes(day), changes(day))

    def test_languages_share_the_moments(self) -> None:
        day = SEEDING_DAYS[-1]
        german, english = changes(day, "de"), changes(day, "en")
        self.assertEqual([type(c) for c in german],
                         [type(c) for c in english])
        self.assertEqual([c.moment for c in german],
                         [c.moment for c in english])
        self.assertNotEqual(german, english)
