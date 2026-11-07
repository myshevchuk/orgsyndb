"""Tests of forecasts at the limits of the arithmetic (production-
planning: Runway, Slack and priority)."""

import signal
from decimal import Decimal
from typing import Any

from planning import forecast

from .planning_support import PLAN, WINDOW, PlanningCase


class LimitTests(PlanningCase):
    """A runway of millions or billions of days still gives a forecast,
    in time."""

    def setUp(self) -> None:
        super().setUp()
        signal.signal(signal.SIGALRM, self.too_long)
        signal.alarm(20)
        self.addCleanup(signal.alarm, 0)

    @staticmethod
    def too_long(signum: int, frame: Any) -> None:
        raise TimeoutError("the forecast did not finish")

    def test_a_runway_of_billions_of_days_ends(self) -> None:
        model = forecast.QuarterlyModel(m=1 / 12, v=1 / 12, quarters=12)
        runway = forecast.article_runway(
            [(model, 10, Decimal("0.001"))], Decimal("20000"), 0.95)
        self.assertGreater(runway, 1e9)

    def test_a_latest_start_beyond_the_calendar(self) -> None:
        item = self.item("NV-9", "NV-9", "1", "mg", 10)
        # One container in a quarter of last year, outside the latest
        # four: recent enough to be planned, and m stays at 1/12.
        for year, quarter in WINDOW:
            self.enter(item, year, quarter,
                       1 if (year, quarter) == WINDOW[-5] else 0)
        self.lot("NV-9", "mg", "3000")
        found = self.forecast("NV-9")
        self.assertGreater(found.runway, 1e6)
        self.assertIsNone(found.latest_start)
        for path in (PLAN, PLAN + "?all=1",
                     f"/lab/inventory/items/{item.pk}/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
