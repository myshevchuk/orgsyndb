"""Tests of the details of a vessel in the vessel list (end-product-
inventory: Vessel details; web-app: Main lists)."""

from datetime import date
from typing import Any

from inventory.models import Vessel

from . import Element, make_task, make_vessel, make_withdrawal, page
from .inventory_support import (VESSELS, InventoryCase, batch_url,
                                vessel_url)
from .main_lists_support import (HTMX, body_of, cells, head_cells,
                                 headers_of, heading_of, link_in, must_pane,
                                 replaced, rows_of, texts_of_links,
                                 unsorted_reasons)
from .test_inventory_dialogs import current

OPEN_PAGE = "Gefäßseite öffnen"
DIALOG_LINKS = ("Entnahme", "Umfüllen", "Korrigieren", "Bearbeiten")


class VesselDetailsCase(InventoryCase):

    def listed(self, vessel: Any, signed_in: bool = False,
               query: str = "") -> Element:
        """The vessel list with ``selected`` naming VESSEL."""
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(f"{VESSELS}?selected={vessel.pk}{query}")
        self.assertEqual(response.status_code, 200)
        return page(response)

    def details(self, vessel: Any, signed_in: bool = False,
                query: str = "") -> Element:
        found = must_pane(self.listed(vessel, signed_in, query))
        self.assertIsNotNone(found, "the list has no #item-detail")
        self.assertEqual(found.get("data-item"), str(vessel.pk))
        return found

    def bought(self) -> Any:
        """A bought vessel of ``benzaldehyde`` from ``Sigma-Aldrich``
        holding 41 g in ``Kühlschrank 1``, opened on 2026-03-05, with two
        withdrawals booked into one step."""
        vessel = make_vessel(
            self.kl, unit="g", amount="50", article="benzaldehyde",
            source="bought", supplier="Sigma-Aldrich",
            location="Kühlschrank 1", date=date(2026, 2, 1))
        step = make_task(self.kl, "benzaldehyde", steps=1).steps.get()
        self.first = make_withdrawal(self.kl, vessel, step, "4",
                                     date(2026, 3, 5))
        self.second = make_withdrawal(self.kl, vessel, step, "5",
                                      date(2026, 3, 6))
        Vessel.objects.filter(pk=vessel.pk).update(
            opened_on=date(2026, 3, 5))
        vessel.refresh_from_db()
        return vessel

    def movements(self, found: Element) -> Element:
        """The table of the pane that lists the vessel's movements."""
        grids = [grid for grid in found.find_all("table")
                 if "Datum" in headers_of(grid)]
        self.assertEqual(len(grids), 1, "the pane has no movements table")
        return grids[0]


class DetailsOfAVesselTests(VesselDetailsCase):

    def test_details_of_a_vessel(self) -> None:
        """Scenario: Details of a vessel."""
        vessel = self.bought()
        found = self.details(vessel, signed_in=True)
        heading = heading_of(found)
        self.assertEqual(link_in(heading).get("href"), vessel_url(vessel))
        text = found.text()
        for shown in ("41 g", "Kühlschrank 1", "Angebrochen am 05.03.2026"):
            self.assertIn(shown, text)
        rows = [[cell.text() for cell in cells(row)]
                for row in body_of(self.movements(found))]
        self.assertEqual([row[1] for row in rows],
                         ["Entnahme", "Entnahme", "Anfangsmenge"])
        self.assertEqual([row[2] for row in rows], ["5 g", "4 g", "50 g"])
        links = {a.text(): a for a in found.find_all("a")}
        for name in DIALOG_LINKS:
            with self.subTest(link=name):
                self.assertIn(name, links)
                self.assertIn("data-dialog", links[name].attrs)
                self.assertTrue(links[name].get("href").startswith(
                    vessel_url(vessel)))

    def test_the_dialog_links_open_the_vessels_forms(self) -> None:
        vessel = self.bought()
        links = {a.text(): a.get("href") for a in
                 self.details(vessel, signed_in=True).find_all("a")}
        self.assertEqual(links["Entnahme"], vessel_url(vessel, "withdraw"))
        self.assertEqual(links["Umfüllen"], vessel_url(vessel, "transfer"))
        self.assertEqual(links["Korrigieren"], vessel_url(vessel, "correct"))
        self.assertEqual(links["Bearbeiten"], vessel_url(vessel, "edit"))

    def test_the_heading_batch_substance_and_page_links(self) -> None:
        vessel = self.bought()
        links = texts_of_links(self.details(vessel))
        self.assertEqual(links[OPEN_PAGE], vessel_url(vessel))
        self.assertIn(batch_url(vessel.batch), links.values())
        self.assertIn("/lab/registry/substances/benzaldehyde/",
                      links.values())

    def test_the_substance_shows_its_article_number(self) -> None:
        self.item("CH-0012")
        vessel = make_vessel(self.kl, article="CH-0012", unit="mg",
                             amount="50")
        self.assertIn("CH-0012", self.details(vessel).text())

    def test_kind_amount_location_and_note(self) -> None:
        self.item("CH-0012")
        vessel = make_vessel(self.kl, article="CH-0012", unit="mg",
                             amount="250", location="Regal 3",
                             note="Rest vom Ansatz")
        text = self.details(vessel).text()
        for shown in ("Endprodukt", "250 mg", "Regal 3", "Rest vom Ansatz"):
            self.assertIn(shown, text)

    def test_the_note_is_in_the_details_and_not_in_the_table(self) -> None:
        self.item("CH-0012")
        vessel = make_vessel(self.kl, article="CH-0012", unit="mg",
                             amount="250", note="Rest vom Ansatz")
        root = self.listed(vessel)
        self.assertIn("Rest vom Ansatz", must_pane(root).text())
        head = root.find(id="item-head")
        self.assertNotIn("Bemerkung", [th.text() for th in
                                       head.find_all("th")])
        self.assertNotIn("Rest vom Ansatz", root.find(id="item-rows").text())

    def test_the_article_number_and_the_opening_are_not_in_the_table(
            self) -> None:
        """The article number and the opening of a vessel show in its
        details, not in the table's columns."""
        self.item("CH-0012")
        opened = make_vessel(self.kl, article="CH-0012", source="bought",
                             supplier="Sigma", supplier_batch="B-OPEN")
        Vessel.objects.filter(pk=opened.pk).update(
            opened_on=date(2026, 3, 5))
        sealed = make_vessel(self.kl, article="CH-0012", source="bought",
                             supplier="Sigma", supplier_batch="B-SEALED")
        root = self.listed(opened)
        headers = [th.text() for th in head_cells(root)]
        for gone in ("Artikelnr.", "Angebrochen"):
            self.assertNotIn(gone, headers)
        rows = rows_of(root).text()
        for gone in ("CH-0012", "versiegelt", "05.03.2026"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, rows)
        details = must_pane(root).text()
        self.assertIn("CH-0012", details)
        self.assertIn("Angebrochen am 05.03.2026", details)
        self.assertIn("versiegelt", self.details(sealed).text())

    def test_the_opening_of_a_bought_vessel(self) -> None:
        opened = self.bought()
        sealed = make_vessel(self.kl, article="benzaldehyde",
                             source="bought", supplier="Sigma-Aldrich")
        made = make_vessel(self.kl, article="CH-0012")
        self.assertIn("Angebrochen am 05.03.2026",
                      self.details(opened).text())
        text = self.details(sealed).text()
        self.assertIn("versiegelt", text)
        self.assertNotIn("Angebrochen am", text)
        for vessel in (made,):
            text = self.details(vessel).text()
            self.assertNotIn("versiegelt", text)
            self.assertNotIn("Angebrochen am", text)

    def test_the_five_newest_movements(self) -> None:
        vessel = make_vessel(self.kl, unit="g", amount="100",
                             article="benzaldehyde", source="bought")
        step = make_task(self.kl, "benzaldehyde", steps=1).steps.get()
        for amount in range(1, 7):
            make_withdrawal(self.kl, vessel, step, str(amount),
                            date(2026, 3, amount))
        rows = [[cell.text() for cell in cells(row)]
                for row in body_of(self.movements(self.details(vessel)))]
        self.assertEqual([row[2] for row in rows],
                         ["6 g", "5 g", "4 g", "3 g", "2 g"])

    def test_the_movements_table_has_date_kind_amount_and_note(self) -> None:
        vessel = self.bought()
        grid = self.movements(self.details(vessel))
        self.assertEqual(headers_of(grid),
                         ["Datum", "Art", "Menge", "Bemerkung"])

    def test_a_visitor_is_offered_no_form(self) -> None:
        links = texts_of_links(self.details(self.bought()))
        for name in DIALOG_LINKS:
            self.assertNotIn(name, links)
        self.assertIn(OPEN_PAGE, links)

    def test_the_movements_table_sorts_in_the_browser(self) -> None:
        found = self.details(self.bought())
        self.assertEqual(unsorted_reasons(found), [])
        rows = body_of(self.movements(found))
        self.assertEqual([cells(row)[0].get("data-sort") for row in rows],
                         ["2026-03-06", "2026-03-05", "2026-11-04"])


class UsedUpVesselTests(VesselDetailsCase):

    def test_a_used_up_vessel(self) -> None:
        """Scenario: A used-up vessel."""
        vessel = make_vessel(self.kl, article="CH-0012", unit="mg",
                             amount="0")
        found = self.details(vessel, signed_in=True, query="&empty=1")
        self.assertIn("aufgebraucht", found.text())
        links = texts_of_links(found)
        self.assertIn("Korrigieren", links)
        self.assertIn("Bearbeiten", links)
        self.assertNotIn("Entnahme", links)
        self.assertNotIn("Umfüllen", links)

    def test_an_open_vessel_is_not_marked(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012", unit="mg",
                             amount="5")
        self.assertNotIn("aufgebraucht", self.details(vessel).text())


class EndpointTests(VesselDetailsCase):
    """``/lab/inventory/vessels/<id>/detail/``."""

    def test_htmx_gets_the_pane_alone(self) -> None:
        vessel = self.bought()
        response = self.client.get(f"{VESSELS}{vessel.pk}/detail/", **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual([(e.get("id"), e.get("data-item")) for e in found],
                         [("item-detail", str(vessel.pk))])

    def test_the_address_keeps_the_filters_of_the_page(self) -> None:
        vessel = self.bought()
        response = self.client.get(
            f"{VESSELS}{vessel.pk}/detail/",
            **current(f"{VESSELS}?kind=commercial&sort=amount&selected=1"))
        self.assertEqual(
            replaced(self, response),
            f"{VESSELS}?kind=commercial&sort=amount&selected={vessel.pk}")

    def test_a_used_up_vessel_has_details_too(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012", amount="0")
        response = self.client.get(f"{VESSELS}{vessel.pk}/detail/", **HTMX)
        self.assertEqual(response.status_code, 200)

    def test_without_htmx_the_list_is_the_answer(self) -> None:
        vessel = self.bought()
        response = self.client.get(f"{VESSELS}{vessel.pk}/detail/")
        self.assertRedirects(
            response, f"{VESSELS}?selected={vessel.pk}",
            fetch_redirect_response=False)

    def test_an_unknown_vessel_is_not_found(self) -> None:
        vessel = self.bought()
        self.assertEqual(self.client.get(
            f"{VESSELS}{vessel.pk}/detail/", **HTMX).status_code, 200)
        for extra in ({}, HTMX):
            self.assertEqual(
                self.client.get(f"{VESSELS}999999/detail/",
                                **extra).status_code, 404)

    def test_the_answer_varies_on_the_headers_it_reads(self) -> None:
        vessel = self.bought()
        response = self.client.get(f"{VESSELS}{vessel.pk}/detail/", **HTMX)
        found = {name.strip().lower()
                 for name in response.get("Vary", "").split(",")}
        self.assertLessEqual({"hx-request", "hx-current-url"}, found)

    def test_a_dialog_of_the_pane_refreshes_the_lists_parts(self) -> None:
        """The parts a saved dialog refreshes are marked in the page the
        details sit in (the refresh itself runs in the browser)."""
        vessel = self.bought()
        root = self.listed(vessel, signed_in=True)
        for name in ("vessel-count", "item-rows", "item-detail"):
            with self.subTest(part=name):
                found = root.find(id=name)
                self.assertIsNotNone(found)
                self.assertIn("data-refresh", found.attrs)
