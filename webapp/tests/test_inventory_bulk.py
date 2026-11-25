"""Tests of the end-product layers and the bulk list (end-product-inventory:
End product layers, Bulk list).
"""

from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from inventory.bookings import correct_vessel, fill

from . import (
    Element,
    field_value,
    make_batch,
    make_substance,
    make_task,
    make_vessel,
    page,
    past,
    table,
)
from .collection_support import accept
from .inventory_support import (
    DELIVERIES,
    LIST,
    InventoryCase,
    batch_url,
    count_beside,
    has_amount,
    has_number,
    item_url,
    vessel_url,
)

BULK = "/lab/inventory/end-products/bulk/"
COOKIE = "bulk-list-view"
HTMX = {"HTTP_HX_REQUEST": "true"}
VIEWS = (None, "table", "details")
COLUMNS_DE = ["Artikel", "Gefäß", "Charge", "Herkunft", "Menge", "Ort",
              "Datum", "Reicht für"]
COLUMNS_EN = ["Article", "Vessel", "Batch", "Source", "Amount", "Location",
              "Date", "Fills"]


def detail_url(vessel: Any) -> str:
    return f"{BULK}{vessel.pk}/"


def body_rows(root: Element) -> list[Element]:
    grid = root.find("table")
    return [tr for tr in grid.find("tbody").find_all("tr")
            if tr.closest("table") is grid]


def chosen_rows(root: Element) -> list[Element]:
    return [row for row in body_rows(root)
            if row.get("aria-current") == "true"]


def layer_links(root: Element) -> list[Element]:
    """The links of the end-product layer switch in document order."""
    targets = {LIST, BULK, DELIVERIES}
    found = []
    for link in root.find("main").find_all("a"):
        if link.get("href") not in targets:
            continue
        nav = link.closest("nav")
        if nav is not None and "section-tabs" in nav.classes:
            continue
        if link.closest("table") is not None \
                or link.closest("aside") is not None:
            continue
        found.append(link)
    return found


class BulkCase(InventoryCase):

    def remember(self, view: str | None) -> None:
        if view is None:
            self.client.cookies.pop(COOKIE, None)
        else:
            self.client.cookies[COOKIE] = view

    def listing(self, query: str = "", view: str | None = None) -> Element:
        if view is not None:
            self.remember(view)
        response = self.client.get(BULK + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def rows(self, query: str = "") -> list[dict[str, Element]]:
        return table(self.listing(query))[1]

    def vessel_ids(self, query: str = "") -> list[str]:
        root = self.listing(query)
        if root.find("table") is None:
            return []
        return [row["Gefäß"].text() for row in table(root)[1]]


class LayerTests(BulkCase):

    def test_three_layers(self) -> None:
        """Scenario: Three layers."""
        first = self.item("CH-0012", size="100", unit="mg", quantity=4)
        self.item("CH-0012", size="1", unit="g", quantity=2)
        self.vessel("CH-0012", "g", "2")
        for n in range(1, 4):
            self.deliver(first, 1, number=f"LS-{n}")
        root = self.listing()
        self.assertEqual(root.find("main").find("h1").text(), "Endprodukte")
        links = layer_links(root)
        self.assertEqual([(a.get("href"), "Gebinde" in a.text(),
                           "Bulk" in a.text(), "Lieferungen" in a.text())
                          for a in links],
                         [(LIST, True, False, False),
                          (BULK, False, True, False),
                          (DELIVERIES, False, False, True)])
        labels = ["Gebinde", "Bulk", "Lieferungen"]
        self.assertEqual(
            [count_beside(link, label, labels)
             for link, label in zip(links, labels)],
            [2, 1, 3])
        self.assertIn(links[1].get("aria-current"), ("page", "true"))
        self.assertIsNone(links[0].get("aria-current"))
        self.assertIsNone(links[2].get("aria-current"))
        tabs = root.find("nav", cls="section-tabs").find_all("a")
        self.assertEqual(
            [(a.text(), a.get("aria-current")) for a in tabs],
            [("Endprodukte", "page"), ("Chargen", None),
             ("Alle Gefäße", None)])

    def test_all_three_lists_offer_the_layers(self) -> None:
        """Requirement: End product layers ("each has the heading
        `Endprodukte` (`End products`) and offers the three layers as links,
        to `/lab/inventory/end-products/`, `/lab/inventory/end-products/bulk/`
        and `/lab/inventory/deliveries/`, each with its count, the number of
        all items, of the vessels the bulk list lists without filters and of
        all delivery notes, and marks its own as current.")."""
        item = self.item("CH-0012", quantity=5)
        self.vessel("CH-0012", "g", "2", flask=True)
        self.vessel("CH-0012", "g", "1", location="Regal")
        self.vessel("acetophenone", "g", "1")
        self.deliver(item, 1, number="LS-1")
        labels = ["Gebinde", "Bulk", "Lieferungen"]
        for path, active in ((LIST, 0), (BULK, 1), (BULK + "?flask=1", 1),
                             (DELIVERIES, 2)):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                self.assertEqual(root.find("main").find("h1").text(),
                                 "Endprodukte")
                links = layer_links(root)
                self.assertEqual([a.get("href") for a in links],
                                 [LIST, BULK, DELIVERIES])
                self.assertEqual(
                    [count_beside(a, label, labels)
                     for a, label in zip(links, labels)],
                    [1, 2, 1])
                for index, link in enumerate(links):
                    if index == active:
                        self.assertIn(link.get("aria-current"),
                                      ("page", "true"))
                    else:
                        self.assertIsNone(link.get("aria-current"))
        accept(language="en")
        root = self.listing()
        self.assertEqual(root.find("main").find("h1").text(), "End products")
        en_labels = ["Containers", "Bulk", "Deliveries"]
        for link, label in zip(layer_links(root), en_labels):
            self.assertIn(label, link.text())


class BulkListTests(BulkCase):

    def test_columns_in_order(self) -> None:
        """Requirement: Bulk list ("with the columns `Artikel`, `Gefäß`,
        `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum` and `Reicht für`")."""
        self.item("CH-0012")
        self.vessel("CH-0012")
        self.assertEqual(table(self.listing())[0], COLUMNS_DE)
        accept(language="en")
        self.assertEqual(table(self.listing())[0], COLUMNS_EN)

    def test_vessels_of_end_products(self) -> None:
        """Scenario: Vessels of end products."""
        self.item("CH-0012", size="100", unit="mg")
        self.item("CH-0012", size="1", unit="g")
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        made = make_batch(self.kl, "CH-0012", number="KL0412",
                          task_step=task.steps.get())
        stored = make_vessel(self.kl, made, unit="g", amount="2.5",
                             location="Regal 1")
        flask = make_vessel(self.kl, made, unit="g", amount="4", flask=True)
        bought_batch = make_batch(
            self.kl, "CH-0012", source="bought", supplier="Sigma",
            supplier_batch="MKCK1234")
        bought = make_vessel(self.kl, bought_batch, unit="g", amount="50",
                             location="Regal 2")
        other = self.vessel("acetophenone", "g", "10", number="AC-1")
        by_id = {row["Gefäß"].text(): row for row in self.rows()}
        self.assertEqual(set(by_id),
                         {f"#{stored.pk}", f"#{flask.pk}", f"#{bought.pk}"})
        self.assertNotIn(f"#{other.pk}", by_id)
        self.assertEqual(by_id[f"#{flask.pk}"]["Ort"].text(), "Kolben")
        self.assertIn("gekauft", by_id[f"#{bought.pk}"]["Herkunft"].text())
        self.assertIn("25 × 100 mg oder 2 × 1 g",
                      by_id[f"#{stored.pk}"]["Reicht für"].text())

    def test_a_row_and_article_without_number(self) -> None:
        self.item("CH-0012", size="100", unit="mg")
        self.item(None, "Neuverbindung 9", size="10", unit="mg")
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = make_batch(
            self.kl, "CH-0012", number="KL0412", date=date(2026, 10, 30),
            task_step=task.steps.get())
        vessel = make_vessel(self.kl, batch, unit="g", amount="2.5",
                             location="Regal 1")
        unnumbered = self.vessel("Neuverbindung 9", "mg", "50",
                                 number="NV-1")
        self.vessel("CH-0012", "mg", "0", number="USED")
        by_id = {row["Gefäß"].text(): row for row in self.rows()}
        self.assertEqual(len(by_id), 2)
        row = by_id[f"#{vessel.pk}"]
        self.assertIn("CH-0012", row["Artikel"].text())
        self.assertIn("(E)-Zimtsäure", row["Artikel"].text())
        self.assertEqual([a.get("href") for a in row["Artikel"].find_all("a")],
                         ["/lab/registry/substances/cinnamic-acid/"])
        self.assertEqual([a.get("href") for a in row["Gefäß"].find_all("a")],
                         [vessel_url(vessel)])
        self.assertEqual(row["Charge"].text(), "KL0412")
        self.assertEqual([a.get("href") for a in row["Charge"].find_all("a")],
                         [batch_url(batch)])
        self.assertEqual(row["Herkunft"].text(),
                         f"hergestellt · {task.number}")
        self.assertEqual(
            [a.get("href") for a in row["Herkunft"].find_all("a")],
            [f"/lab/tasks/{task.number}/"])
        self.assertTrue(has_amount(row["Menge"].text(), "2,5", "g"))
        self.assertEqual(row["Ort"].text(), "Regal 1")
        self.assertEqual(row["Datum"].text(), "30.10.2026")
        self.assertEqual(row["Reicht für"].find_all("a"), [])
        plain = by_id[f"#{unnumbered.pk}"]
        self.assertIn("ohne Nr.", plain["Artikel"].text())
        self.assertIn("Neuverbindung 9", plain["Artikel"].text())
        self.assertEqual(
            [a.get("href") for a in plain["Artikel"].find_all("a")],
            ["/lab/registry/substances/neuverbindung-9/"])
        self.assertEqual(plain["Ort"].text(), "")
        self.assertEqual(plain["Datum"].text(), "")

    def test_a_vessel_that_does_not_convert(self) -> None:
        """Scenario: A vessel that does not convert."""
        self.item("X-1", size="10", unit="umol")
        self.vessel("X-1", "mg", "600", number="B-1")
        row = self.rows()[0]
        self.assertIn("Molmasse fehlt", row["Reicht für"].text())

    def test_filling_from_the_bulk_list(self) -> None:
        """Scenario: Filling from the bulk list."""
        small = self.item("CH-0012", size="100", unit="mg")
        self.item("CH-0012", size="1", unit="g")
        vessel = self.vessel("CH-0012", "g", "2.5")
        self.client.force_login(self.kl)
        row = self.rows()[0]
        links = [a for a in row["Reicht für"].find_all("a")
                 if "100 mg" in a.text()]
        self.assertEqual(len(links), 1)
        href = links[0].get("href")
        parts = urlsplit(href)
        self.assertEqual(parts.path, item_url(small, "fill"))
        self.assertEqual(parse_qs(parts.query), {"vessel": [str(vessel.pk)]})
        done = self.client.get(href)
        self.assertEqual(done.status_code, 200)
        self.assertEqual(field_value(page(done), "vessel"), str(vessel.pk))

    def test_ordering(self) -> None:
        """Requirement: Bulk list ("The vessels are ordered by article number,
        articles without one last and by name regardless of case, then by their
        batch's date, oldest first and vessels without one last, then by
        id.")."""
        self.item("CH-0002", name="Beta")
        self.item("CH-0001", name="Gamma")
        self.item(None, "zeta")
        self.item(None, "Alpha")
        v_ch2 = self.vessel("CH-0002", date=date(2024, 1, 1))
        v_ch1_none = self.vessel("CH-0001")
        v_ch1_mid1 = self.vessel("CH-0001", date=date(2025, 5, 1))
        v_ch1_mid2 = self.vessel("CH-0001", date=date(2025, 5, 1))
        v_ch1_old = self.vessel("CH-0001", date=date(2024, 1, 1))
        v_zeta = self.vessel("zeta", date=date(2024, 1, 1))
        v_alpha = self.vessel("Alpha", date=date(2026, 1, 1))
        self.assertEqual(
            self.vessel_ids(),
            [f"#{v.pk}" for v in (v_ch1_old, v_ch1_mid1, v_ch1_mid2,
                                   v_ch1_none, v_ch2, v_alpha, v_zeta)])

    def test_flasks_alone(self) -> None:
        """Scenario: Flasks alone."""
        self.item("CH-0012")
        flask = self.vessel("CH-0012", "g", "2", flask=True)
        self.vessel("CH-0012", "g", "2", location="Regal")
        self.assertEqual(self.vessel_ids("?flask=1"), [f"#{flask.pk}"])

    def test_text_filter_q(self) -> None:
        """Requirement: Bulk list ("`q` those in whose article number, or in
        whose substance's key, name or German name, or batch number or
        supplier's batch, the text is found regardless of case")."""
        self.item("CH-0012")
        self.item("X-1", name="Beta Compound", name_de="Beta-Stoff")
        v1 = self.vessel("CH-0012", number="KL0412")
        v2 = self.vessel("X-1", source="bought", supplier_batch="SUP-99")
        cases = {
            "ch-0012": [v1],
            "cinnamic-acid": [v1],
            "zimtsäure": [v1],
            "kl04": [v1],
            "beta compound": [v2],
            "beta-stoff": [v2],
            "sup-99": [v2],
            "nichts": [],
        }
        for query, expected in cases.items():
            with self.subTest(q=query):
                self.assertEqual(
                    self.vessel_ids(f"?q={quote(query)}"),
                    [f"#{v.pk}" for v in expected])

    def test_location_filter_and_offered_locations(self) -> None:
        """Requirement: Bulk list ("`location` those at that location" and
        "The page offers each location in use.")."""
        self.item("CH-0012")
        v1 = self.vessel("CH-0012", location="Kühlraum")
        self.vessel("CH-0012", location="Abzug 2")
        self.vessel("CH-0012", location="Alt", amount="0")
        self.vessel("acetophenone", location="Zwischenlager")
        self.assertEqual(self.vessel_ids(f"?location={quote('Kühlraum')}"),
                         [f"#{v1.pk}"])
        root = self.listing()
        offered = {o.get("value") for o in
                   root.find("select", name="location").find_all("option")
                   if o.get("value")}
        self.assertLessEqual({"Kühlraum", "Abzug 2"}, offered)
        self.assertNotIn("Alt", offered)

    def test_source_filter(self) -> None:
        """Requirement: Bulk list ("`source`, `made` or `bought`, those of
        batches of that source")."""
        self.item("CH-0012")
        made = self.vessel("CH-0012", source="made", number="B-M")
        bought = self.vessel("CH-0012", source="bought",
                             supplier_batch="B-B")
        self.assertEqual(self.vessel_ids("?source=made"), [f"#{made.pk}"])
        self.assertEqual(self.vessel_ids("?source=bought"), [f"#{bought.pk}"])
        self.assertEqual(set(self.vessel_ids("?source=other")),
                         {f"#{made.pk}", f"#{bought.pk}"})

    def test_filters_keep_their_values(self) -> None:
        """Requirement: Bulk list ("GET parameters select the vessels listed
        and keep their values")."""
        self.item("CH-0012")
        self.vessel("CH-0012", location="Regal", flask=True)
        root = self.listing("?q=ch&location=Regal&source=made&flask=1")
        self.assertEqual(field_value(root, "q"), "ch")
        self.assertEqual(field_value(root, "location"), "Regal")
        self.assertEqual(field_value(root, "source"), "made")
        self.assertEqual(field_value(root, "flask"), "on")

    def test_new_batch_link_for_signed_in_user(self) -> None:
        """Requirement: Bulk list ("A signed-in user sees a link `Neue
        Charge` (`New batch`).")."""
        self.item("CH-0012")
        self.vessel("CH-0012")
        self.assertIsNone(self.listing().find("a", href=NEW_BATCH))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["Neue Charge"])
        accept(language="en")
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["New batch"])


class BulkDetailTests(BulkCase):

    def test_view_cookie_and_selected(self) -> None:
        """Requirement: Bulk list ("The list shows its vessels in the views
        `Tabelle` and `Details`, remembered in the cookie `bulk-list-view`,
        with one vessel selected by `selected=<id>`, as the item list does
        with its items.")."""
        self.item("CH-0001")
        self.item("CH-0002")
        first = self.vessel("CH-0001", number="B-1")
        second = self.vessel("CH-0002", number="B-2")
        for cookie, want in ((None, "table"), ("table", "table"),
                             ("details", "details"), ("other", "table"),
                             ("", "table")):
            with self.subTest(cookie=cookie):
                root = self.listing(view=cookie)
                layout = root.find(attrs={"data-view": True})
                self.assertIsNotNone(layout)
                self.assertEqual(layout.get("data-view"), want)
                radios = {r.get("id"): r for r in root.find_all(
                    "input", type="radio", name="view")}
                self.assertEqual(sorted(radios),
                                 ["view-details", "view-table"])
                self.assertEqual(
                    [name for name, r in radios.items()
                     if "checked" in r.attrs],
                    [f"view-{want}"])
        for view in VIEWS:
            for query, target in (
                    ("", first),
                    (f"?selected={second.pk}", second),
                    ("?selected=999999", first),
                    (f"?q=CH-0002&selected={first.pk}", second)):
                with self.subTest(view=view, query=query):
                    root = self.listing(query, view)
                    marked = chosen_rows(root)
                    self.assertEqual(len(marked), 1)
                    self.assertEqual(marked[0].get("hx-get"),
                                     detail_url(target))
                    self.assertIsNotNone(
                        marked[0].find("a", href=vessel_url(target)))
                    aside = root.find("main").find("aside")
                    self.assertIsNotNone(aside)
                    self.assertIsNotNone(
                        aside.find("a", href=vessel_url(target)))
            with self.subTest(view=view, empty=True):
                root = self.listing(f"?q=nothing&selected={first.pk}", view)
                self.assertEqual(chosen_rows(root), [])
                aside = root.find("main").find("aside")
                if aside is not None:
                    self.assertEqual(
                        [a for a in aside.find_all("a")
                         if "/vessels/" in a.get("href", "")], [])

    def test_bulk_details_fragment_and_movements(self) -> None:
        """Requirement: Bulk list ("The details view shows beside the table
        the selected vessel: its batch, source, amount, location, the
        containers it would fill, and its five newest movements as the vessel
        page shows them, with a link to the vessel's page.")."""
        small = self.item("CH-0012", size="100", unit="mg")
        self.item("CH-0012", size="1", unit="g")
        batch = make_batch(self.kl, "CH-0012", number="KL0412")
        vessel = make_vessel(self.kl, batch, unit="g", amount="10",
                             location="Kühlschrank 2")
        fill(self.kl, small, count=1, vessel=vessel, note="Bew-1")
        for n, left in ((2, "8"), (3, "7"), (4, "6"), (5, "2.5")):
            correct_vessel(self.kl, vessel, amount=Decimal(left),
                           note=f"Bew-{n}")
        response = self.client.get(detail_url(vessel), **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        text = root.text()
        for expected in ("KL0412", "hergestellt", "Kühlschrank 2",
                         "25 × 100 mg", "2 × 1 g", "Abfüllung"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "2,5", "g"), text)
        self.assertIsNotNone(root.find("a", href=vessel_url(vessel)))
        for n in range(1, 6):
            self.assertIn(f"Bew-{n}", text)
        for older, newer in zip(("Bew-5", "Bew-4", "Bew-3", "Bew-2"),
                                ("Bew-4", "Bew-3", "Bew-2", "Bew-1")):
            self.assertLess(text.index(older), text.index(newer))
        self.assertNotIn("Anfangsmenge", text)
        varied = {name.strip().lower() for name in
                  response.get("Vary", "").split(",")}
        self.assertIn("hx-request", varied)

    def test_bulk_details_non_htmx_redirects_and_missing_is_404(
            self) -> None:
        """Requirement: Bulk list (non-htmx detail request redirects to the
        list with selected; unknown vessel answers 404)."""
        self.item("CH-0012")
        vessel = self.vessel("CH-0012")
        plain = self.client.get(detail_url(vessel))
        self.assertIn(plain.status_code, (302, 303))
        target = urlsplit(plain["Location"])
        self.assertEqual(target.path, BULK)
        self.assertEqual(
            parse_qs(target.query), {"selected": [str(vessel.pk)]})
        self.assertEqual(
            self.client.get(f"{BULK}{vessel.pk + 999}/", **HTMX).status_code,
            404)
