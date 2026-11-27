"""Tests of HTMX live inventory lists, canonical HX-Push-Url, history
restore, and split-view HX-Replace-Url (web-app: Live lists;
end-product-inventory: Live inventory lists).
"""

import json
import re
from datetime import date
from typing import Any
from urllib.parse import parse_qsl, unquote_plus, urlsplit

from . import Element, make_class, make_group, make_substance, page
from .inventory_support import (
    BATCHES,
    DELIVERIES,
    LIST,
    VESSELS,
    InventoryCase,
)
from . import test_shell
from .test_inventory_categories import CHEMICALS, INTERMEDIATES
from .test_inventory_dialogs import HTMX, RESTORE, current, vary_of
from .test_inventory_lists import BULK

MORPH_OOB = re.compile(r"^#[A-Za-z0-9_-]+:morph$")
ITEM_LIST_OOB = {
    "#item-count:morph",
    "#list-summary:morph",
    "#item-head:morph",
    "#item-detail:morph",
    "#stock-filter:morph",
    "#stock-entries:morph",
    "#more-filters-button:morph",
    "#filter-selected:morph",
    "#filter-hidden:morph",
}
ITEM_RESET_OOB = (ITEM_LIST_OOB - {
    "#filter-selected:morph", "#filter-hidden:morph"
}) | {"#filters:morph", "#more-filters:morph"}
CATEGORY_OOB = {
    "#category-count:morph",
    "#item-detail:morph",
    "#filter-selected:morph",
}
SPLIT_DETAIL_OOB = {"#item-detail:morph", "#filter-selected:morph"}


def triggers_of(element: Element) -> list[str]:
    """Return stripped top-level comma-separated trigger clauses from
    ``hx-trigger`` (preserving commas inside parenthesized selectors)."""
    raw = element.get("hx-trigger") or ""
    clauses: list[str] = []
    depth = 0
    start = 0
    for idx, ch in enumerate(raw):
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            part = raw[start:idx].strip()
            if part:
                clauses.append(part)
            start = idx + 1
    tail = raw[start:].strip()
    if tail:
        clauses.append(tail)
    return clauses


def oob_entries(value: str | None) -> list[str]:
    """Return stripped comma-separated entries from ``hx-select-oob``."""
    return [part.strip() for part in (value or "").split(",")
            if part.strip()]


def effective_hx(element: Element, attr: str) -> str | None:
    """Return ATTR from ELEMENT or its nearest ancestor inside ``main``."""
    node: Element | None = element
    while node is not None and node.tag != "#root":
        if attr in node.attrs:
            return node.get(attr)
        if node.tag == "main":
            break
        node = node.parent
    return None


def is_ancestor(ancestor: Element, node: Element) -> bool:
    """Return whether ANCESTOR is NODE or contains NODE."""
    cur: Element | None = node
    while cur is not None:
        if cur is ancestor:
            return True
        cur = cur.parent
    return False


class LiveListAssertions:
    """Shared structural assertions for live HTMX inventory lists."""

    def assert_scoped_triggers(
        self,
        form: Element,
        *,
        has_search: bool,
        has_select: bool,
        has_checkbox: bool,
        extra_triggers: tuple[str, ...] = (),
    ) -> None:
        raw = form.get("hx-trigger") or ""
        self.assertNotRegex(raw, r"\bfrom:select\b")
        self.assertNotRegex(raw, r"\bfrom:input\[type=search\]")
        self.assertNotRegex(raw, r"from:[^\s,]+\s+[^\s,]")
        triggers = triggers_of(form)
        self.assertIn("submit", triggers)
        if has_search:
            search = form.find("input", name="q")
            self.assertIsNotNone(search)
            self.assertEqual(search.get("id"), "filter-q")
            self.assertIn("search from:#filter-q", triggers)
            self.assertIn("input delay:200ms from:#filter-q", triggers)
            self.assertNotIn("input changed delay:200ms from:#filter-q",
                             triggers)
        form_change = [t for t in triggers
                       if t.startswith("change") and " from:" not in t]
        self.assertLessEqual(len(form_change), 1,
                             f"multiple form change clauses collide in htmx: "
                             f"{form_change}")
        if has_select and has_checkbox:
            self.assertIn("change target:(select, input[type=checkbox])",
                          triggers)
        elif has_select:
            self.assertIn("change target:select", triggers)
        elif has_checkbox:
            self.assertIn("change target:input[type=checkbox]", triggers)
        for trigger in extra_triggers:
            self.assertIn(trigger, triggers)

    def assert_disjoint_oob(
        self,
        root: Element,
        oob_value: str | None,
        primary_selector: str,
    ) -> list[str]:
        entries = oob_entries(oob_value)
        self.assertTrue(entries, "empty hx-select-oob")
        for entry in entries:
            self.assertRegex(entry, MORPH_OOB, f"bad OOB entry {entry!r}")
        ids = [entry[1:].split(":", 1)[0] for entry in entries]
        self.assertEqual(len(ids), len(set(ids)),
                         f"duplicate OOB targets in {entries}")
        primary_id = primary_selector.removeprefix("#")
        primary = root.find(id=primary_id)
        self.assertIsNotNone(primary, f"missing primary {primary_selector}")
        nodes: list[tuple[str, Element]] = []
        for target_id in ids:
            found = root.find_all(id=target_id)
            self.assertEqual(len(found), 1, f"expected unique #{target_id}")
            node = found[0]
            self.assertFalse(
                is_ancestor(primary, node) or is_ancestor(node, primary),
                f"#{target_id} overlaps primary {primary_selector}",
            )
            nodes.append((target_id, node))
        for index, (id_a, node_a) in enumerate(nodes):
            for id_b, node_b in nodes[index + 1:]:
                self.assertFalse(
                    is_ancestor(node_a, node_b)
                    or is_ancestor(node_b, node_a),
                    f"overlapping OOB targets #{id_a} and #{id_b}",
                )
        return entries

    def assert_live_element(
        self,
        element: Element,
        root: Element,
        *,
        expected_get: str,
        target: str,
        required_oob: set[str] = (),
        forbidden_oob: set[str] = (),
    ) -> list[str]:
        self.assertEqual(element.get("hx-get"), expected_get)
        self.assertEqual(effective_hx(element, "hx-push-url"), "true")
        self.assertEqual(effective_hx(element, "hx-sync"), "#main:replace")
        self.assertEqual(effective_hx(element, "hx-target"), target)
        self.assertEqual(effective_hx(element, "hx-select"), target)
        self.assertEqual(effective_hx(element, "hx-swap"), "morph:outerHTML")
        entries = self.assert_disjoint_oob(
            root, effective_hx(element, "hx-select-oob"), target)
        entry_set = set(entries)
        self.assertLessEqual(set(required_oob), entry_set)
        self.assertEqual(entry_set & set(forbidden_oob), set())
        return entries

    def assert_push_url(
        self,
        response: Any,
        expected_path: str,
        expected_query: dict[str, str],
        *,
        exact_url: str | None = None,
    ) -> None:
        self.assertIn("HX-Push-Url", response)
        actual = response["HX-Push-Url"]
        if exact_url is not None:
            self.assertEqual(actual, exact_url)
        parts = urlsplit(actual)
        self.assertEqual((parts.scheme, parts.netloc, parts.path),
                         ("", "", expected_path))
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        self.assertEqual(len(pairs), len(dict(pairs)), actual)
        self.assertEqual(dict(pairs), expected_query, actual)

    def assert_single_detail_fragment(
        self, response: Any, expected_item: str,
    ) -> Element:
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        elements = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].get("id"), "item-detail")
        self.assertEqual(elements[0].get("data-item"), expected_item)
        return elements[0]


class LiveListContractTests(LiveListAssertions, InventoryCase):
    """Shared ``web-app: Live lists`` contract across all six inventory lists
    (seven URLs) and CSP ``assert_scripts`` verification."""

    def setUp(self) -> None:
        super().setUp()
        self.item_rec = self.item("CH-0012", category="Ester")
        self.bulk_vessel = self.vessel("CH-0012", number="KL-1")
        self.note_rec = self.deliver(self.item_rec, 1, number="LS-1")
        self.int_vessel = self.vessel("acetophenone", number="INT-1",
                                      location="Regal 1")
        self.chem_vessel = self.vessel("benzaldehyde", source="bought",
                                       supplier="Sigma",
                                       supplier_batch="SUP-1")

    def list_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "url": LIST,
                "active_query": "?category=Ester",
                "has_search": True,
                "has_select": True,
                "has_checkbox": False,
                "extra_triggers": (
                    "change from:#filter-container",
                    "change from:#filter-compartment",
                    "change from:#filter-box",
                ),
                "required_oob": ITEM_LIST_OOB,
                "split_view": True,
            },
            {
                "url": INTERMEDIATES,
                "active_query": "?location=Regal+1",
                "has_search": True,
                "has_select": True,
                "has_checkbox": True,
                "extra_triggers": (),
                "required_oob": CATEGORY_OOB,
                "split_view": True,
            },
            {
                "url": CHEMICALS,
                "active_query": "?sealed=1",
                "has_search": True,
                "has_select": True,
                "has_checkbox": True,
                "extra_triggers": (),
                "required_oob": CATEGORY_OOB,
                "split_view": True,
            },
            {
                "url": BULK,
                "active_query": "?q=CH",
                "has_search": True,
                "has_select": True,
                "has_checkbox": True,
                "extra_triggers": (),
                "required_oob": SPLIT_DETAIL_OOB,
                "split_view": True,
            },
            {
                "url": DELIVERIES,
                "active_query": "?q=LS",
                "has_search": True,
                "has_select": True,
                "has_checkbox": False,
                "extra_triggers": (),
                "required_oob": SPLIT_DETAIL_OOB,
                "split_view": True,
            },
            {
                "url": BATCHES,
                "active_query": "?q=KL",
                "has_search": True,
                "has_select": False,
                "has_checkbox": False,
                "extra_triggers": (),
                "required_oob": set(),
                "split_view": False,
            },
            {
                "url": VESSELS,
                "active_query": "?empty=1",
                "has_search": False,
                "has_select": True,
                "has_checkbox": True,
                "extra_triggers": (),
                "required_oob": set(),
                "split_view": False,
            },
        ]

    def test_live_filter_attributes_and_csp_across_all_lists(self) -> None:
        for spec in self.list_specs():
            url = spec["url"]
            with self.subTest(url=url):
                response = self.client.get(url, **HTMX)
                test_shell.ShellTests.assert_scripts(self, response)
                root = page(response)
                self.assertEqual(
                    [e.tag for e in root.walk()
                     if "data-submit" in e.attrs],
                    [],
                )
                form = root.find("form", cls="lab-filters")
                self.assertIsNotNone(form)
                self.assertEqual(form.get("method"), "get")
                self.assertEqual(form.get("action"), url)
                self.assertIsNotNone(form.find("button", type="submit"))
                tbody = root.find("table").find("tbody")
                tbody_id = tbody.get("id")
                self.assertTrue(tbody_id, f"{url} tbody lacks id")
                entries = self.assert_live_element(
                    form,
                    root,
                    expected_get=url,
                    target=f"#{tbody_id}",
                    required_oob=spec["required_oob"],
                )
                self.assert_scoped_triggers(
                    form,
                    has_search=spec["has_search"],
                    has_select=spec["has_select"],
                    has_checkbox=spec["has_checkbox"],
                    extra_triggers=spec["extra_triggers"],
                )
                count_el = root.find(cls="lab-count")
                self.assertIsNotNone(count_el)
                count_id = count_el.get("id")
                self.assertTrue(count_id, f"{url} .lab-count lacks id")
                self.assertIn(f"#{count_id}:morph", entries)
                if spec["split_view"]:
                    self.assertEqual(tbody.get("hx-sync"), "#main:replace")
                    selected_wrap = form.find(id="filter-selected")
                    self.assertIsNotNone(selected_wrap)
                    self.assertEqual(
                        len(selected_wrap.find_all(
                            "input", type="hidden", name="selected")),
                        1,
                    )

    def test_plain_get_htmx_get_and_history_restore_on_all_lists(self) -> None:
        """Scenario: Live list filter request and history restore."""
        for spec in self.list_specs():
            url = spec["url"]
            full_url = url + spec["active_query"]
            with self.subTest(url=url):
                htmx_res = self.client.get(full_url, **HTMX)
                restore_res = self.client.get(full_url, **RESTORE)
                plain_res = self.client.get(full_url)
                self.assertIn("HX-Push-Url", htmx_res)
                self.assertNotIn("HX-Push-Url", restore_res)
                self.assertNotIn("HX-Push-Url", plain_res)
                for label, res in (("htmx", htmx_res),
                                   ("restore", restore_res),
                                   ("plain", plain_res)):
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
                        form = root.find("form", cls="lab-filters")
                        self.assertEqual(form.get("method"), "get")
                        self.assertEqual(form.get("action"), url)
                        self.assertIsNotNone(
                            form.find("button", type="submit"))
                        meta = root.find("meta", attrs={"name": "htmx-config"})
                        cfg = json.loads(meta.get("content"))
                        self.assertIs(cfg.get("historyCacheSize"), 0)
                        self.assertIs(cfg.get("refreshOnHistoryMiss"), True)


class ItemListLiveTests(LiveListAssertions, InventoryCase):
    """Live filtering, sorting, stock menu, reset, and canonical push URLs
    on ``item_list``."""

    def test_live_filtering_sorting_stock_status_and_reset(self) -> None:
        """Scenario: Live filtering, sorting, stock status, and reset on the
        item list."""
        ester = self.item("CH-0012", category="Ester", compartment="2",
                          box="7")
        self.item("CH-0001", category="Säuren")
        res = self.client.get(
            f"{LIST}?category=Ester&stock=bogus&sort=stock&dir=desc&q=",
            **HTMX,
        )
        self.assert_push_url(
            res,
            LIST,
            {
                "category": "Ester",
                "sort": "stock",
                "dir": "desc",
                "selected": str(ester.pk),
            },
            exact_url=(
                f"{LIST}?category=Ester&sort=stock&dir=desc"
                f"&selected={ester.pk}"
            ),
        )
        root = page(res)
        form = root.find("form", id="filters")
        self.assert_live_element(
            form, root, expected_get=LIST, target="#item-rows",
            required_oob=ITEM_LIST_OOB,
        )
        self.assert_scoped_triggers(
            form,
            has_search=True,
            has_select=True,
            has_checkbox=False,
            extra_triggers=(
                "change from:#filter-container",
                "change from:#filter-compartment",
                "change from:#filter-box",
            ),
        )
        self.assertIsNotNone(form.find(id="filter-hidden"))
        self.assertIsNotNone(root.find(id="more-filters-button"))

        head = root.find(id="item-head")
        self.assertIsNotNone(head)
        sort_links = head.find_all("a")
        self.assertEqual(len(sort_links), 12)
        for link in sort_links:
            with self.subTest(sort_link=link.text()):
                self.assertTrue(link.get("href"))
                self.assert_live_element(
                    link, root, expected_get=link.get("href"),
                    target="#item-rows", required_oob=ITEM_RESET_OOB,
                    forbidden_oob={"#filter-selected:morph",
                                   "#filter-hidden:morph"},
                )

        entries = root.find(id="stock-entries")
        self.assertIsNotNone(entries)
        stock_links = entries.find_all("a")
        self.assertEqual(len(stock_links), 8)
        for link in stock_links:
            with self.subTest(stock_link=link.find("strong").text()):
                self.assertTrue(link.get("href"))
                self.assert_live_element(
                    link, root, expected_get=link.get("href"),
                    target="#item-rows", required_oob=ITEM_RESET_OOB,
                    forbidden_oob={"#filter-selected:morph",
                                   "#filter-hidden:morph"},
                )

        summary = root.find(id="list-summary")
        self.assertIsNotNone(summary)
        reset_links = [a for a in summary.find_all("a")
                       if a.text() == "Zurücksetzen"]
        self.assertEqual(len(reset_links), 1)
        reset = reset_links[0]
        self.assert_live_element(
            reset,
            root,
            expected_get=reset.get("href"),
            target="#item-rows",
            required_oob=ITEM_RESET_OOB,
            forbidden_oob={"#filter-selected:morph", "#filter-hidden:morph"},
        )

    def test_canonical_push_url_cleaning_and_empty_selection(self) -> None:
        item = self.item("CH-0012", category="Säuren", size="100", unit="mg",
                         compartment="2", box="7")
        res_default = self.client.get(
            f"{LIST}?sort=bogus&dir=up&q=+&selected=999999", **HTMX)
        self.assert_push_url(
            res_default,
            LIST,
            {"sort": "category", "selected": str(item.pk)},
            exact_url=f"{LIST}?sort=category&selected={item.pk}",
        )

        res_filtered = self.client.get(
            f"{LIST}?q=+Zimt+&category=S%C3%A4uren&stock=undelivered"
            "&container=100+mg&compartment=2&box=7&sort=name",
            **HTMX,
        )
        self.assert_push_url(
            res_filtered,
            LIST,
            {
                "q": "Zimt",
                "category": "Säuren",
                "stock": "undelivered",
                "container": "100 mg",
                "compartment": "2",
                "box": "7",
                "sort": "name",
                "selected": str(item.pk),
            },
        )
        self.assertIn("category=Säuren",
                      unquote_plus(res_filtered["HX-Push-Url"]))

        res_empty = self.client.get(
            f"{LIST}?category=Basen&selected={item.pk}", **HTMX)
        self.assert_push_url(
            res_empty,
            LIST,
            {"category": "Basen", "sort": "category"},
            exact_url=f"{LIST}?category=Basen&sort=category",
        )
        selected_wrap = page(res_empty).find(id="filter-selected")
        self.assertIsNotNone(selected_wrap)
        self.assertEqual(selected_wrap.find_all("input", name="selected"), [])


class CategoryListLiveTests(LiveListAssertions, InventoryCase):
    """Live filtering and canonical ``HX-Push-Url`` on intermediate and
    commercial chemical lists."""

    def test_live_filtering_on_category_lists(self) -> None:
        """Scenario: Live filtering on category lists."""
        sub_int = make_substance("acetophenone", "Acetophenone")
        self.vessel(substance=sub_int, location="Regal 1")
        sub_chem = make_substance("benzaldehyde", "Benzaldehyde")
        self.vessel(substance=sub_chem, source="bought", supplier="Sigma")

        res_int = self.client.get(
            f"{INTERMEDIATES}?location=Regal+1&sealed=1&selected=missing",
            **HTMX,
        )
        root_int = page(res_int)
        form_int = root_int.find("form", id="filters")
        self.assert_live_element(
            form_int, root_int, expected_get=INTERMEDIATES,
            target="#item-rows", required_oob=CATEGORY_OOB,
        )
        self.assert_scoped_triggers(
            form_int, has_search=True, has_select=True, has_checkbox=True)
        self.assert_push_url(
            res_int,
            INTERMEDIATES,
            {"location": "Regal 1", "selected": "acetophenone"},
            exact_url=(
                f"{INTERMEDIATES}?location=Regal+1&selected=acetophenone"
            ),
        )

        res_empty = self.client.get(
            f"{INTERMEDIATES}?location=nowhere", **HTMX)
        self.assert_push_url(
            res_empty,
            INTERMEDIATES,
            {"location": "nowhere"},
            exact_url=f"{INTERMEDIATES}?location=nowhere",
        )
        self.assertEqual(
            page(res_empty).find(id="filter-selected").find_all(
                "input", name="selected"),
            [],
        )

        res_chem = self.client.get(
            f"{CHEMICALS}?sealed=1&flask=1", **HTMX)
        root_chem = page(res_chem)
        form_chem = root_chem.find("form", id="filters")
        self.assert_live_element(
            form_chem, root_chem, expected_get=CHEMICALS,
            target="#item-rows", required_oob=CATEGORY_OOB,
        )
        self.assert_scoped_triggers(
            form_chem, has_search=True, has_select=True, has_checkbox=True)
        self.assert_push_url(
            res_chem,
            CHEMICALS,
            {"sealed": "1", "selected": "benzaldehyde"},
            exact_url=f"{CHEMICALS}?sealed=1&selected=benzaldehyde",
        )

    def test_category_lists_canonical_push_url_rules(self) -> None:
        ketones = make_class("ketones", "Ketones")
        solvents = make_group("solvents", "Solvents")
        sub_int = make_substance("acetophenone", "Acetophenone",
                                 classes=[ketones])
        self.vessel(substance=sub_int, flask=True, date=date(2020, 1, 1))
        sub_chem = make_substance("acetone", "Acetone", group=solvents)
        self.vessel(substance=sub_chem, source="bought", supplier="Merck",
                    location="Kühlraum")

        res_int = self.client.get(
            f"{INTERMEDIATES}?q=+acet+&class=ketones&flask=1&old=1"
            "&group=solvents&supplier=Merck&sealed=1",
            **HTMX,
        )
        self.assert_push_url(
            res_int,
            INTERMEDIATES,
            {
                "q": "acet",
                "class": "ketones",
                "flask": "1",
                "old": "1",
                "selected": "acetophenone",
            },
        )

        res_chem = self.client.get(
            f"{CHEMICALS}?q=+acet+&location=+K%C3%BChlraum+&group=solvents"
            "&supplier=+Merck+&sealed=1&class=ketones&flask=1&old=1",
            **HTMX,
        )
        self.assert_push_url(
            res_chem,
            CHEMICALS,
            {
                "q": "acet",
                "location": "Kühlraum",
                "group": "solvents",
                "supplier": "Merck",
                "sealed": "1",
                "selected": "acetone",
            },
        )

        res_no_match = self.client.get(
            f"{CHEMICALS}?q=missing&selected=acetone", **HTMX)
        self.assert_push_url(
            res_no_match,
            CHEMICALS,
            {"q": "missing"},
            exact_url=f"{CHEMICALS}?q=missing",
        )


class OtherInventoryListsLiveTests(LiveListAssertions, InventoryCase):
    """Live filtering and canonical ``HX-Push-Url`` on bulk, delivery, batch,
    and vessel lists."""

    def test_live_filtering_on_bulk_delivery_batch_and_vessel_lists(
        self,
    ) -> None:
        """Scenario: Live filtering on bulk, delivery, batch, and vessel
        lists."""
        item = self.item("CH-0012")
        flask = self.vessel("CH-0012", number="B-1", flask=True)
        note = self.deliver(item, 1, number="LS-1")
        self.vessel("CH-0012", amount="0", number="USED-1")

        res_bulk = self.client.get(
            f"{BULK}?flask=1&source=bogus&q=+CH+", **HTMX)
        root_bulk = page(res_bulk)
        self.assert_live_element(
            root_bulk.find("form", id="filters"),
            root_bulk,
            expected_get=BULK,
            target="#item-rows",
            required_oob=SPLIT_DETAIL_OOB,
        )
        self.assert_scoped_triggers(
            root_bulk.find("form", id="filters"),
            has_search=True, has_select=True, has_checkbox=True,
        )
        self.assert_push_url(
            res_bulk,
            BULK,
            {"q": "CH", "flask": "1", "selected": str(flask.pk)},
        )

        res_note = self.client.get(
            f"{DELIVERIES}?q=+LS+&item=abc", **HTMX)
        root_note = page(res_note)
        self.assert_live_element(
            root_note.find("form", id="filters"),
            root_note,
            expected_get=DELIVERIES,
            target="#item-rows",
            required_oob=SPLIT_DETAIL_OOB,
        )
        self.assert_scoped_triggers(
            root_note.find("form", id="filters"),
            has_search=True, has_select=True, has_checkbox=False,
        )
        self.assert_push_url(
            res_note,
            DELIVERIES,
            {"q": "LS", "selected": str(note.pk)},
        )

        res_batch = self.client.get(f"{BATCHES}?q=+B-1+", **HTMX)
        root_batch = page(res_batch)
        batch_tbody = root_batch.find("table").find("tbody").get("id")
        self.assertTrue(batch_tbody)
        batch_count = root_batch.find(cls="lab-count").get("id")
        self.assertTrue(batch_count)
        self.assert_live_element(
            root_batch.find("form", cls="lab-filters"),
            root_batch,
            expected_get=BATCHES,
            target=f"#{batch_tbody}",
            required_oob={f"#{batch_count}:morph"},
        )
        self.assert_scoped_triggers(
            root_batch.find("form", cls="lab-filters"),
            has_search=True, has_select=False, has_checkbox=False,
        )
        self.assert_push_url(
            res_batch,
            BATCHES,
            {"q": "B-1"},
            exact_url=f"{BATCHES}?q=B-1",
        )

        res_vessel = self.client.get(
            f"{VESSELS}?kind=bogus&empty=1", **HTMX)
        root_vessel = page(res_vessel)
        vessel_tbody = root_vessel.find("table").find("tbody").get("id")
        self.assertTrue(vessel_tbody)
        vessel_count = root_vessel.find(cls="lab-count").get("id")
        self.assertTrue(vessel_count)
        self.assert_live_element(
            root_vessel.find("form", cls="lab-filters"),
            root_vessel,
            expected_get=VESSELS,
            target=f"#{vessel_tbody}",
            required_oob={f"#{vessel_count}:morph"},
        )
        self.assert_scoped_triggers(
            root_vessel.find("form", cls="lab-filters"),
            has_search=False, has_select=True, has_checkbox=True,
        )
        self.assert_push_url(
            res_vessel,
            VESSELS,
            {"empty": "1"},
            exact_url=f"{VESSELS}?empty=1",
        )

    def test_canonical_push_url_edge_cases_on_other_lists(self) -> None:
        item = self.item("CH-0012")
        vessel = self.vessel("CH-0012", source="made", location="Regal 1")
        note = self.deliver(item, 1, number="LS-1")

        self.assert_push_url(
            self.client.get(
                f"{BULK}?location=+Regal+1+&source=made&flask=0", **HTMX),
            BULK,
            {
                "location": "Regal 1",
                "source": "made",
                "selected": str(vessel.pk),
            },
        )
        self.assert_push_url(
            self.client.get(f"{BULK}?q=nothing&selected={vessel.pk}", **HTMX),
            BULK,
            {"q": "nothing"},
        )
        self.assert_push_url(
            self.client.get(
                f"{DELIVERIES}?item={item.pk}&q=+LS+", **HTMX),
            DELIVERIES,
            {"q": "LS", "item": str(item.pk), "selected": str(note.pk)},
        )
        self.assert_push_url(
            self.client.get(
                f"{DELIVERIES}?q=nothing&selected={note.pk}", **HTMX),
            DELIVERIES,
            {"q": "nothing"},
        )
        self.assert_push_url(
            self.client.get(f"{BATCHES}?q=+&foo=bar", **HTMX),
            BATCHES,
            {},
            exact_url=BATCHES,
        )
        self.assert_push_url(
            self.client.get(f"{VESSELS}?kind=intermediate&empty=0", **HTMX),
            VESSELS,
            {"kind": "intermediate"},
            exact_url=f"{VESSELS}?kind=intermediate",
        )
        self.assert_push_url(
            self.client.get(VESSELS, **HTMX),
            VESSELS,
            {},
            exact_url=VESSELS,
        )


class SplitViewDetailReplaceUrlTests(LiveListAssertions, InventoryCase):
    """``HX-Replace-Url``, single ``#item-detail`` body, and ``Vary`` across
    all five split-view detail endpoints."""

    def test_inventory_detail_endpoints_replace_the_list_url(self) -> None:
        """Scenario: Inventory detail endpoints replace the list URL."""
        item = self.item("CH-0012", category="Ester")
        self.vessel("acetophenone", location="Regal 1")

        res_same = self.client.get(
            f"/lab/inventory/items/{item.pk}/detail/",
            **current(f"{LIST}?category=Ester&selected=999"),
        )
        self.assert_single_detail_fragment(res_same, str(item.pk))
        self.assertEqual(
            res_same["HX-Replace-Url"],
            f"{LIST}?category=Ester&selected={item.pk}",
        )

        res_keep = self.client.get(
            f"{INTERMEDIATES}acetophenone/?location=Regal+1",
            **HTMX,
        )
        self.assert_single_detail_fragment(res_keep, "acetophenone")
        self.assertEqual(
            res_keep["HX-Replace-Url"],
            f"{INTERMEDIATES}?"
            f"location=Regal+1&selected=acetophenone",
        )

        res_foreign = self.client.get(
            f"/lab/inventory/items/{item.pk}/detail/",
            **current(
                f"{LIST}?category=Ester&selected=999",
                host="evil.example",
            ),
        )
        self.assert_single_detail_fragment(res_foreign, str(item.pk))
        self.assertEqual(
            res_foreign["HX-Replace-Url"],
            f"{LIST}?selected={item.pk}",
        )

    def test_all_five_detail_endpoints_vary_and_replace_url(self) -> None:
        """Scenario: Split-view detail response sets HX-Replace-Url."""
        item = self.item("CH-0012", category="Ester")
        bulk_v = self.vessel("CH-0012", flask=True)
        note = self.deliver(item, 1, number="LS-1")
        self.vessel("acetophenone", location="Regal 1")
        self.vessel("benzaldehyde", source="bought", supplier="Sigma")

        endpoints = [
            (f"/lab/inventory/items/{item.pk}/detail/", LIST,
             "category=Ester", str(item.pk), False),
            (f"{INTERMEDIATES}acetophenone/", INTERMEDIATES,
             "location=Regal+1", "acetophenone", True),
            (f"{CHEMICALS}benzaldehyde/", CHEMICALS,
             "supplier=Sigma", "benzaldehyde", True),
            (f"{BULK}{bulk_v.pk}/", BULK,
             "flask=1", str(bulk_v.pk), False),
            (f"{DELIVERIES}{note.pk}/detail/", DELIVERIES,
             "q=LS", str(note.pk), False),
        ]
        for detail_url, base_url, flt, rec_id, keep_query in endpoints:
            with self.subTest(detail_url=detail_url):
                same = self.client.get(
                    detail_url,
                    **current(f"{base_url}?{flt}&selected=stale"),
                )
                self.assert_single_detail_fragment(same, rec_id)
                self.assertLessEqual(
                    {"hx-request", "hx-current-url"}, vary_of(same))
                self.assertEqual(
                    same["HX-Replace-Url"],
                    f"{base_url}?{flt}&selected={rec_id}",
                )

                foreign = self.client.get(
                    detail_url,
                    **current(
                        f"{base_url}?{flt}&selected=stale",
                        host="foreign.example",
                    ),
                )
                self.assert_single_detail_fragment(foreign, rec_id)
                self.assertLessEqual(
                    {"hx-request", "hx-current-url"}, vary_of(foreign))
                self.assertEqual(
                    foreign["HX-Replace-Url"],
                    f"{base_url}?selected={rec_id}",
                )

                absent = self.client.get(detail_url, **HTMX)
                self.assert_single_detail_fragment(absent, rec_id)
                self.assertLessEqual(
                    {"hx-request", "hx-current-url"}, vary_of(absent))
                self.assertEqual(
                    absent["HX-Replace-Url"],
                    f"{base_url}?selected={rec_id}",
                )

                if keep_query:
                    fallback = self.client.get(
                        f"{detail_url}?{flt}",
                        **current(
                            f"{base_url}?supplier=Evil&selected=stale",
                            host="foreign.example",
                        ),
                    )
                    self.assert_single_detail_fragment(fallback, rec_id)
                    self.assertEqual(
                        fallback["HX-Replace-Url"],
                        f"{base_url}?{flt}&selected={rec_id}",
                    )
