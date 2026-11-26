"""Constant-query-count regression tests for read paths (batch-consumption-
queries and fix-list-detail-n-plus-one)."""

from datetime import date
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from inventory.bookings import book_note, enter_consumption, transfer, withdraw
from tasks.models import TaskStep

from . import make_batch, make_task, make_user, make_vessel, task_url
from .inventory_support import (DELIVERIES, LIST, InventoryCase, delivery_line,
                                item_url, vessel_url)

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

    def test_note_list_constant_query_count(self) -> None:
        items = [self.item(number, quantity=10) for number in ARTICLES]
        book_note(self.kl, number="LS-1", date=date(2026, 2, 1),
                  recipient="AK A", lines=[delivery_line(items[0], 1)])
        one = self._query_count(DELIVERIES)

        for index, item in enumerate(items[1:], start=2):
            book_note(self.kl, number=f"LS-{index}",
                      date=date(2026, 2, index), recipient=f"AK {index}",
                      lines=[delivery_line(item, 1)])
        four = self._query_count(DELIVERIES)
        self.assertEqual(four, one)

    def test_vessel_page_constant_query_count(self) -> None:
        source = make_vessel(self.kl, article="CH-0101", amount="100")
        transfer(self.kl, source, amount=Decimal("5"), location="S1")
        one = self._query_count(vessel_url(source))

        for index in range(2, 5):
            transfer(self.kl, source, amount=Decimal("5"),
                     location=f"S{index}")
        four = self._query_count(vessel_url(source))
        self.assertEqual(four, one)

    def test_task_page_constant_query_count(self) -> None:
        task = make_task(self.kl, substance="CH-0101")
        stock = make_vessel(self.kl, article="CH-0102", amount="100")
        self.client.force_login(self.kl)

        def add_step(position: int) -> None:
            step = TaskStep.objects.create(task=task, position=position)
            batch = make_batch(self.kl, article="CH-0101",
                               number=f"KL-{position}", task_step=step)
            make_vessel(self.kl, batch=batch, amount="10")
            withdraw(self.kl, stock, task_step=step, amount=Decimal("1"))

        add_step(1)
        one = self._query_count(task_url(task))

        for position in range(2, 5):
            add_step(position)
        four = self._query_count(task_url(task))
        self.assertEqual(four, one)

    def test_task_admin_changelist_constant_query_count(self) -> None:
        staff = make_user("admin", "AD", "Admin", "User")
        staff.is_staff = True
        staff.is_superuser = True
        staff.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(staff)

        def add_task(number: str) -> None:
            task = make_task(self.kl, substance=number)
            TaskStep.objects.create(task=task, position=1,
                                    done_on=date(2026, 2, 1))
            TaskStep.objects.create(task=task, position=2)

        add_task(ARTICLES[0])
        one = self._query_count("/lab/admin/tasks/task/")

        for number in ARTICLES[1:]:
            add_task(number)
        four = self._query_count("/lab/admin/tasks/task/")
        self.assertEqual(four, one)
