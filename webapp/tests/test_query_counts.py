"""Constant-query-count regression tests for read paths (batch-consumption-
queries)."""

from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext

from inventory.bookings import book_note, enter_consumption

from . import make_task, make_vessel
from .inventory_support import LIST, InventoryCase, delivery_line, item_url

ARTICLES = ("CH-0101", "CH-0102", "CH-0103", "CH-0104")


class ReadPathQueryCountTests(InventoryCase):

    def _add_article(self, number: str, day: date) -> object:
        item = self.item(number, quantity=4, compartment="F1", box="B1")
        enter_consumption(self.kl, item, year=2025, quarter=1, count=4)
        book_note(self.kl, number=f"LS-{number}", date=day,
                  recipient="AK Meyer",
                  lines=[delivery_line(item, 2)])
        make_vessel(self.kl, article=number)
        make_task(self.kl, substance=number)
        return item

    def _query_count(self, path: str) -> int:
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return len(queries)

    def test_constant_query_counts_between_one_and_four_articles(
            self) -> None:
        first = self._add_article(ARTICLES[0], date(2026, 2, 10))
        paths = [
            LIST,
            "/lab/planning/",
            "/lab/",
            "/lab/summary/",
            item_url(first),
        ]
        one_article = {path: self._query_count(path) for path in paths}

        for index, number in enumerate(ARTICLES[1:], start=1):
            self._add_article(number, date(2026, 2, 10 + index))

        four_articles = {path: self._query_count(path) for path in paths}
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(
                    four_articles[path], one_article[path],
                    f"{path}: {one_article[path]} queries for 1 article vs "
                    f"{four_articles[path]} for 4 articles")
