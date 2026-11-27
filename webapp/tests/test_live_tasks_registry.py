"""Tests of HTMX live filtering, canonical HX-Push-Url, and history restore
on /lab/tasks/ and /lab/registry/ (task-tracker: Live task list;
lab-registry: Live substance list).
"""

import json
from typing import Any

from . import field_value, make_task, page, past, test_shell
from .test_inventory_dialogs import HTMX, RESTORE, vary_of
from .test_inventory_live_lists import LiveListAssertions
from .test_registry_pages import RegistryCase
from .test_task_list import ListCase

TASKS_URL = "/lab/tasks/"
REGISTRY_URL = "/lab/registry/"
MIDDLE_DOT = "·"
TASK_OOB = ["#task-counts:morph", "#item-head:morph", "#item-detail:morph",
            "#filter-selected:morph"]
SUBSTANCE_OOB = ["#substance-count:morph", "#item-head:morph",
                 "#item-detail:morph", "#filter-selected:morph"]


class LivePageContractMixin(LiveListAssertions):
    """Shared structural, header, and CSP assertions for live list pages."""

    def assert_no_data_submit(self, root: Any) -> None:
        self.assertEqual(
            [e.tag for e in root.walk() if "data-submit" in e.attrs],
            [],
        )

    def assert_live_filter_form(
        self,
        root: Any,
        *,
        url: str,
        target: str,
        oob_entries: list[str],
    ) -> None:
        self.assert_no_data_submit(root)
        form = root.find("form", id="filters")
        self.assertIsNotNone(form)
        self.assertIn("lab-filters", form.classes)
        self.assertEqual(form.get("method"), "get")
        self.assertEqual(form.get("action"), url)
        self.assertIsNotNone(form.find("button", type="submit"))
        entries = self.assert_live_element(
            form,
            root,
            expected_get=url,
            target=target,
            required_oob=set(oob_entries),
        )
        self.assertEqual(entries, oob_entries)
        self.assert_scoped_triggers(
            form,
            has_search=True,
            has_select=True,
            has_checkbox=False,
        )
        self.assertNotRegex(form.get("hx-trigger") or "", r"\bchanged\b")

    def assert_live_header_links(
        self,
        url: str,
        count: str,
        sortable: int,
    ) -> None:
        """The header links of the list at URL update ``#item-rows``
        in place, and out of band the count COUNT, ``#item-head``,
        ``#item-detail`` and ``#filters``."""
        root = page(self.client.get(url + "?state=all", **HTMX))
        head = root.find(id="item-head")
        self.assertIsNotNone(head)
        links = head.find_all("a")
        self.assertEqual(len(links), sortable)
        wanted = [f"#{count}:morph", "#item-head:morph",
                  "#item-detail:morph", "#filters:morph"]
        for link in links:
            with self.subTest(link=link.text()):
                self.assertTrue(link.get("href"))
                entries = self.assert_live_element(
                    link, root, expected_get=link.get("href"),
                    target="#item-rows", required_oob=set(wanted))
                self.assertEqual(entries, wanted)

    def assert_complete_page_variants(
        self,
        *,
        base_url: str,
        full_url: str,
        expected_push_url: str,
        target: str,
        oob_entries: list[str],
    ) -> None:
        htmx_res = self.client.get(full_url, **HTMX)
        restore_res = self.client.get(full_url, **RESTORE)
        plain_res = self.client.get(full_url)
        self.assertIn("HX-Push-Url", htmx_res)
        self.assertEqual(htmx_res["HX-Push-Url"], expected_push_url)
        self.assertNotIn("HX-Push-Url", restore_res)
        self.assertNotIn("HX-Push-Url", plain_res)
        for label, res in (
            ("htmx", htmx_res),
            ("restore", restore_res),
            ("plain", plain_res),
        ):
            with self.subTest(kind=label):
                test_shell.ShellTests.assert_scripts(self, res)
                self.assertLessEqual(
                    {"hx-request", "hx-history-restore-request"},
                    vary_of(res),
                )
                root = page(res)
                self.assertIsNotNone(root.find("html"))
                self.assertIsNotNone(root.find("main", id="main"))
                self.assertIsNotNone(root.find("table"))
                self.assert_live_filter_form(
                    root,
                    url=base_url,
                    target=target,
                    oob_entries=oob_entries,
                )
                meta = root.find("meta", attrs={"name": "htmx-config"})
                cfg = json.loads(meta.get("content"))
                self.assertIs(cfg.get("historyCacheSize"), 0)
                self.assertIs(cfg.get("refreshOnHistoryMiss"), True)


class TaskListLiveTests(LivePageContractMixin, ListCase):
    """Live filtering, canonical HX-Push-Url, and history restore on
    ``/lab/tasks/`` (task-tracker: Live task list).
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.planned = make_task(
            cls.kl, substance="Alpha", assignee=cls.kl, priority="low",
        )
        cls.running = make_task(
            cls.kl, substance="Beta", assignee=cls.ae, priority="high",
            started=past(1),
        )
        cls.followup = make_task(
            cls.kl, substance="Delta", assignee=None, priority="low",
            started=past(1), ended=past(2), qc_list=True,
        )
        cls.done = make_task(
            cls.kl, substance="Gamma", assignee=None, started=past(1),
            ended=past(2), report=True, qc_list=True,
        )
        cls.cancelled = make_task(
            cls.kl, substance="Epsilon", assignee=cls.kl, cancelled=True,
        )

    def row_ids(self, root: Any) -> list[str]:
        tbody = root.find("tbody", id="item-rows")
        self.assertIsNotNone(tbody)
        return [tr.get("id") for tr in tbody.find_all("tr")]

    def row_keys(self, root: Any) -> list[str]:
        return [tr.get("data-item") for tr in
                root.find("tbody", id="item-rows").find_all("tr")]

    def test_live_filtering_and_canonical_push_url(self) -> None:
        """Scenario: Live filtering and canonical URL on the task list."""
        cases = [
            (
                f"{TASKS_URL}?state=active&person=kl&priority=bogus&q=+Alpha+",
                {"person": "KL", "q": "Alpha"},
                f"{TASKS_URL}?person=KL&q=Alpha",
                [self.planned],
                f"1 geplant {MIDDLE_DOT} 0 in Arbeit "
                f"{MIDDLE_DOT} 0 Nacharbeit",
            ),
            (
                f"{TASKS_URL}?state=all&person=none",
                {"state": "all", "person": "none"},
                f"{TASKS_URL}?state=all&person=none",
                [self.done, self.followup],
                f"0 geplant {MIDDLE_DOT} 0 in Arbeit "
                f"{MIDDLE_DOT} 1 Nacharbeit",
            ),
            (
                f"{TASKS_URL}?state=running&sort=number",
                {"state": "running", "sort": "number"},
                f"{TASKS_URL}?state=running&sort=number",
                [self.running],
                f"1 geplant {MIDDLE_DOT} 1 in Arbeit "
                f"{MIDDLE_DOT} 1 Nacharbeit",
            ),
            (
                f"{TASKS_URL}?priority=high",
                {"priority": "high"},
                f"{TASKS_URL}?priority=high",
                [self.running],
                f"0 geplant {MIDDLE_DOT} 1 in Arbeit "
                f"{MIDDLE_DOT} 0 Nacharbeit",
            ),
            (
                f"{TASKS_URL}?state=bogus",
                {},
                TASKS_URL,
                [self.running, self.planned, self.followup],
                f"1 geplant {MIDDLE_DOT} 1 in Arbeit "
                f"{MIDDLE_DOT} 1 Nacharbeit",
            ),
            (
                f"{TASKS_URL}?q=no-match",
                {"q": "no-match"},
                f"{TASKS_URL}?q=no-match",
                [],
                f"0 geplant {MIDDLE_DOT} 0 in Arbeit "
                f"{MIDDLE_DOT} 0 Nacharbeit",
            ),
        ]
        for query, expected_q, exact_url, expected_tasks, counts_text in cases:
            with self.subTest(query=query):
                if expected_tasks:
                    chosen = expected_tasks[0].number
                    expected_q = {**expected_q, "selected": chosen}
                    exact_url += ("&" if "?" in exact_url else "?") \
                        + f"selected={chosen}"
                res = self.client.get(query, **HTMX)
                test_shell.ShellTests.assert_scripts(self, res)
                self.assertLessEqual(
                    {"hx-request", "hx-history-restore-request"},
                    vary_of(res),
                )
                self.assert_push_url(
                    res, TASKS_URL, expected_q, exact_url=exact_url,
                )
                root = page(res)
                self.assert_live_filter_form(
                    root,
                    url=TASKS_URL,
                    target="#item-rows",
                    oob_entries=TASK_OOB,
                )
                self.assertEqual(
                    self.row_ids(root),
                    [f"task-row-{t.pk}" for t in expected_tasks],
                )
                self.assertEqual(self.row_keys(root),
                                 [t.number for t in expected_tasks])
                counts = root.find(id="task-counts")
                self.assertIsNotNone(counts)
                self.assertEqual(counts.text(), counts_text)

    def test_the_header_links_update_the_list_in_place(self) -> None:
        self.assert_live_header_links(TASKS_URL, "task-counts", 11)

    def test_the_filter_form_hides_nothing_in_the_default_order(self) -> None:
        root = page(self.client.get(TASKS_URL, **HTMX))
        form = root.find("form", id="filters")
        names = {i.get("name") for i in form.find_all("input", type="hidden")}
        self.assertNotIn("sort", names)
        root = page(self.client.get(f"{TASKS_URL}?sort=number&dir=desc"))
        found = {i.get("name"): i.get("value") for i in
                 root.find("form", id="filters").find_all(
                     "input", type="hidden")}
        self.assertEqual((found.get("sort"), found.get("dir")),
                         ("number", "desc"))

    def test_htmx_get_history_restore_and_plain_get(self) -> None:
        self.assert_complete_page_variants(
            base_url=TASKS_URL,
            full_url=f"{TASKS_URL}?state=running",
            expected_push_url=(f"{TASKS_URL}?state=running"
                               f"&selected={self.running.number}"),
            target="#item-rows",
            oob_entries=TASK_OOB,
        )


class RegistryListLiveTests(LivePageContractMixin, RegistryCase):
    """Live filtering, unknown filter preservation, canonical HX-Push-Url,
    and history restore on ``/lab/registry/`` (lab-registry: Live substance
    list).
    """

    def row_ids(self, root: Any) -> list[str]:
        tbody = root.find("tbody", id="item-rows")
        self.assertIsNotNone(tbody)
        return [tr.get("id") for tr in tbody.find_all("tr")]

    def row_keys(self, root: Any) -> list[str]:
        return [tr.get("data-item") for tr in
                root.find("tbody", id="item-rows").find_all("tr")]

    def assert_selected_option(
        self, root: Any, field: str, expected: str,
    ) -> None:
        select = root.find("select", name=field)
        self.assertIsNotNone(select)
        selected = [
            opt.get("value") for opt in select.find_all("option")
            if "selected" in opt.attrs
        ]
        self.assertEqual(selected, [expected])
        self.assertEqual(field_value(root, field), expected)

    def test_live_filtering_and_canonical_push_url(self) -> None:
        """Scenario: Live filtering and canonical URL on the substance list."""
        cinnamic = self.records["cinnamic"]
        acetophenone = self.records["acetophenone"]
        bare = self.records["bare"]
        all_rows = sorted(
            [cinnamic, acetophenone, bare],
            key=lambda s: (s.shown_name.casefold(), s.key),
        )
        cases = [
            (
                f"{REGISTRY_URL}?q=+zimt+&group=+final-products+&class=",
                {"q": "zimt", "group": "final-products"},
                f"{REGISTRY_URL}?q=zimt&group=final-products",
                [cinnamic],
                "1",
                ("group", "final-products"),
            ),
            (
                f"{REGISTRY_URL}?group=nope",
                {"group": "nope"},
                f"{REGISTRY_URL}?group=nope",
                [],
                "0",
                ("group", "nope"),
            ),
            (
                f"{REGISTRY_URL}?group=nope&q=zimt",
                {"q": "zimt", "group": "nope"},
                f"{REGISTRY_URL}?q=zimt&group=nope",
                [],
                "0",
                ("group", "nope"),
            ),
            (
                f"{REGISTRY_URL}?group=&q=zimt",
                {"q": "zimt"},
                f"{REGISTRY_URL}?q=zimt",
                [cinnamic],
                "1",
                ("group", None),
            ),
            (
                f"{REGISTRY_URL}?q=+",
                {},
                REGISTRY_URL,
                all_rows,
                "3",
                ("group", None),
            ),
            (
                f"{REGISTRY_URL}?class=nope",
                {"class": "nope"},
                f"{REGISTRY_URL}?class=nope",
                [],
                "0",
                ("class", "nope"),
            ),
            (
                f"{REGISTRY_URL}?class=nope&q=zimt",
                {"q": "zimt", "class": "nope"},
                f"{REGISTRY_URL}?q=zimt&class=nope",
                [],
                "0",
                ("class", "nope"),
            ),
            (
                f"{REGISTRY_URL}?class=&q=zimt",
                {"q": "zimt"},
                f"{REGISTRY_URL}?q=zimt",
                [cinnamic],
                "1",
                ("class", None),
            ),
            (
                f"{REGISTRY_URL}?group=&q=zimt&sort=formula&dir=desc",
                {"q": "zimt", "sort": "formula", "dir": "desc"},
                f"{REGISTRY_URL}?q=zimt&sort=formula&dir=desc",
                [cinnamic],
                "1",
                ("group", None),
            ),
        ]
        for (
            query,
            expected_q,
            exact_url,
            expected_subs,
            count_text,
            (select_name, selected_value),
        ) in cases:
            with self.subTest(query=query):
                if expected_subs:
                    chosen = expected_subs[0].key
                    expected_q = {**expected_q, "selected": chosen}
                    exact_url += ("&" if "?" in exact_url else "?") \
                        + f"selected={chosen}"
                res = self.client.get(query, **HTMX)
                test_shell.ShellTests.assert_scripts(self, res)
                self.assertLessEqual(
                    {"hx-request", "hx-history-restore-request"},
                    vary_of(res),
                )
                self.assert_push_url(
                    res, REGISTRY_URL, expected_q, exact_url=exact_url,
                )
                root = page(res)
                self.assert_live_filter_form(
                    root,
                    url=REGISTRY_URL,
                    target="#item-rows",
                    oob_entries=SUBSTANCE_OOB,
                )
                self.assertEqual(
                    self.row_ids(root),
                    [f"substance-row-{s.pk}" for s in expected_subs],
                )
                self.assertEqual(self.row_keys(root),
                                 [s.key for s in expected_subs])
                count_el = root.find(id="substance-count")
                self.assertIsNotNone(count_el)
                self.assertEqual(count_el.text(), count_text)
                if selected_value is not None:
                    self.assert_selected_option(
                        root, select_name, selected_value,
                    )
                else:
                    self.assertIn(
                        field_value(root, select_name), ("", None),
                    )

    def test_the_header_links_update_the_list_in_place(self) -> None:
        self.assert_live_header_links(REGISTRY_URL, "substance-count", 8)

    def test_htmx_get_history_restore_and_plain_get(self) -> None:
        self.assert_complete_page_variants(
            base_url=REGISTRY_URL,
            full_url=f"{REGISTRY_URL}?q=zimt",
            expected_push_url=(f"{REGISTRY_URL}?q=zimt"
                               "&selected=cinnamic-acid"),
            target="#item-rows",
            oob_entries=SUBSTANCE_OOB,
        )
