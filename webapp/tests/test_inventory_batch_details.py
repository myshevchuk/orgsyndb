"""Tests of the details of a batch in the batch list (end-product-
inventory: Batch details; web-app: Main lists)."""

from datetime import date
from decimal import Decimal
from typing import Any

from . import Element, make_batch, make_vessel, page
from .inventory_support import BATCHES, InventoryCase, batch_url, vessel_url
from .journal_support import entry_of, make_notebook
from .main_lists_support import (HTMX, body_of, cells, headers_of, heading_of,
                                 link_in, must_pane, key_number, replaced,
                                 row_for, row_keys, texts_of_links,
                                 unsorted_reasons)
from .test_inventory_dialogs import current

OPEN_PAGE = "Chargenseite öffnen"


class BatchDetailsCase(InventoryCase):

    def listed(self, batch: Any, signed_in: bool = False,
               query: str = "") -> Element:
        """The batch list with ``selected`` naming BATCH."""
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(f"{BATCHES}?selected={batch.pk}{query}")
        self.assertEqual(response.status_code, 200)
        return page(response)

    def details(self, batch: Any, signed_in: bool = False) -> Element:
        found = must_pane(self.listed(batch, signed_in))
        self.assertIsNotNone(found, "the list has no #item-detail")
        self.assertEqual(found.get("data-item"), str(batch.pk))
        return found

    def made(self, **extra: Any) -> Any:
        """The made batch ``KL0412`` of ``cinnamic-acid`` that names the
        journal entry ``AE-1/9``, with a stored vessel of 2 g in
        ``Kühlschrank 2`` and a used-up flask."""
        make_notebook("AE-1", self.ae)
        self.item("CH-0012")
        batch = make_batch(
            self.kl, "CH-0012", number="KL0412",
            journal_entry=entry_of("AE-1/9"), date=date(2026, 10, 30),
            yield_amount="2", yield_unit="g", **extra)
        self.stored = make_vessel(self.kl, batch, unit="g", amount="2",
                                  location="Kühlschrank 2")
        self.flask = make_vessel(self.kl, batch, unit="mg", amount="0",
                                 flask=True)
        return batch


class DetailsOfABatchTests(BatchDetailsCase):

    def test_details_of_a_batch(self) -> None:
        """Scenario: Details of a batch."""
        batch = self.made()
        found = self.details(batch)
        heading = heading_of(found)
        self.assertIsNotNone(heading)
        self.assertEqual(heading.text(), "KL0412")
        self.assertEqual(link_in(heading).get("href"), batch_url(batch))
        links = texts_of_links(found)
        self.assertEqual(links["AE-1/9"], "/lab/journal/AE-1/")
        self.assertIn("CH-0012", found.text())
        self.assertEqual(links[OPEN_PAGE], batch_url(batch))
        self.assertEqual(links[f"#{self.stored.pk}"],
                         vessel_url(self.stored))
        self.assertNotIn(f"#{self.flask.pk}", links)
        rows = [cell.text() for row in body_of(found.find("table"))
                for cell in cells(row)]
        self.assertIn("Kühlschrank 2", rows)
        self.assertIn("2 g", rows)

    def test_the_substance_links_its_page_with_the_article_number(
            self) -> None:
        batch = self.made()
        found = self.details(batch)
        link = [a for a in found.find_all("a")
                if a.get("href") == "/lab/registry/substances/cinnamic-acid/"]
        self.assertEqual(len(link), 1)
        self.assertIn(link[0].text(), ("(E)-Zimtsäure",))
        self.assertIn("CH-0012", found.text())

    def test_a_made_batch_shows_its_journal_entry_yield_and_date(
            self) -> None:
        text = self.details(self.made()).text()
        self.assertIn("2 g", text)
        self.assertIn("30.10.2026", text)

    def test_the_source_is_as_the_list_shows_it(self) -> None:
        batch = self.made()
        root = self.listed(batch)
        row = row_for(root, str(batch.pk))
        shown = cells(row)[3].text()
        self.assertTrue(shown)
        self.assertIn(shown, must_pane(root).text())

    def test_a_bought_batch_names_no_journal_entry(self) -> None:
        batch = make_batch(self.kl, "CH-0012", source="bought",
                           supplier="Sigma", date=date(2026, 5, 1))
        found = self.details(batch)
        self.assertIn("Sigma", found.text())
        self.assertEqual(
            [a for a in found.find_all("a")
             if a.get("href", "").startswith("/lab/journal/")], [])

    def test_each_field_without_a_value_reads_a_dash(self) -> None:
        batch = make_batch(self.kl, "CH-0012", source="bought")
        text = self.details(batch).text()
        self.assertIn("–", text)

    def test_a_batch_without_an_article_number_still_has_details(
            self) -> None:
        batch = make_batch(self.kl, "Aspirin")
        found = self.details(batch)
        self.assertEqual(heading_of(found).find("a").get("href"),
                         batch_url(batch))
        self.assertIn(OPEN_PAGE, texts_of_links(found))


class VesselsOfABatchTests(BatchDetailsCase):

    def test_the_open_vessels_in_a_table(self) -> None:
        batch = self.made()
        found = self.details(batch)
        grid = found.find("table")
        self.assertEqual(headers_of(grid), ["Gefäß", "Art", "Ort", "Menge"])
        rows = body_of(grid)
        self.assertEqual(len(rows), 1)
        shown = [cell.text() for cell in cells(rows[0])]
        self.assertEqual(shown[0], f"#{self.stored.pk}")
        self.assertEqual(shown[2:], ["Kühlschrank 2", "2 g"])

    def test_the_vessels_run_in_the_order_of_the_batch_page(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        first = make_vessel(self.kl, batch, unit="mg", amount="5")
        make_vessel(self.kl, batch, unit="mg", amount="0")
        second = make_vessel(self.kl, batch, unit="g", amount="3")
        rows = body_of(self.details(batch).find("table"))
        self.assertEqual([cells(row)[0].text() for row in rows],
                         [f"#{first.pk}", f"#{second.pk}"])

    def test_a_batch_without_an_open_vessel_reads_none(self) -> None:
        for vessels in (0, 1):
            with self.subTest(vessels=vessels):
                batch = make_batch(self.kl, "CH-0012")
                for _ in range(vessels):
                    make_vessel(self.kl, batch, unit="mg", amount="0")
                found = self.details(batch)
                self.assertEqual(found.find_all("table"), [])
                self.assertIn("Keine", found.text())

    def test_the_vessel_table_sorts_in_the_browser(self) -> None:
        batch = self.made()
        make_vessel(self.kl, batch, unit="mg", amount="500")
        found = self.details(batch)
        self.assertEqual(unsorted_reasons(found), [])
        rows = body_of(found.find("table"))
        keys = {cells(row)[3].text(): cells(row)[3].get("data-sort")
                for row in rows}
        self.assertEqual({name: key_number(key) for name, key in keys.items()},
                         {"2 g": Decimal(2000), "500 mg": Decimal(500)})


class SignedInLinksTests(BatchDetailsCase):

    def test_a_signed_in_user_may_edit_and_add_a_vessel(self) -> None:
        batch = self.made()
        links = texts_of_links(self.details(batch, signed_in=True))
        self.assertEqual(links["Bearbeiten"],
                         f"/lab/inventory/batches/{batch.pk}/edit/")
        self.assertEqual(links["Neues Gefäß"],
                         f"/lab/inventory/batches/{batch.pk}/vessels/new/")

    def test_a_visitor_may_not(self) -> None:
        links = texts_of_links(self.details(self.made()))
        self.assertNotIn("Bearbeiten", links)
        self.assertNotIn("Neues Gefäß", links)


class EndpointTests(BatchDetailsCase):
    """``/lab/inventory/batches/<id>/detail/``."""

    def test_htmx_gets_the_pane_alone(self) -> None:
        batch = self.made()
        response = self.client.get(f"{BATCHES}{batch.pk}/detail/", **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual([(e.get("id"), e.get("data-item")) for e in found],
                         [("item-detail", str(batch.pk))])

    def test_the_address_keeps_the_filters_of_the_page(self) -> None:
        """Scenario: Inventory details endpoints replace the list URL."""
        batch = self.made()
        response = self.client.get(
            f"{BATCHES}{batch.pk}/detail/",
            **current(f"{BATCHES}?q=KL&sort=yield"))
        self.assertEqual(
            replaced(self, response),
            f"{BATCHES}?q=KL&sort=yield&selected={batch.pk}")

    def test_another_host_is_not_trusted(self) -> None:
        batch = self.made()
        response = self.client.get(
            f"{BATCHES}{batch.pk}/detail/",
            **current(f"{BATCHES}?q=KL", host="evil.example"))
        self.assertEqual(replaced(self, response),
                         f"{BATCHES}?selected={batch.pk}")

    def test_without_htmx_the_list_is_the_answer(self) -> None:
        batch = self.made()
        response = self.client.get(f"{BATCHES}{batch.pk}/detail/")
        self.assertRedirects(
            response, f"{BATCHES}?selected={batch.pk}",
            fetch_redirect_response=False)

    def test_an_unknown_batch_is_not_found(self) -> None:
        batch = self.made()
        self.assertEqual(self.client.get(
            f"{BATCHES}{batch.pk}/detail/", **HTMX).status_code, 200)
        for extra in ({}, HTMX):
            self.assertEqual(
                self.client.get(f"{BATCHES}999999/detail/",
                                **extra).status_code, 404)

    def test_the_answer_varies_on_the_headers_it_reads(self) -> None:
        batch = self.made()
        response = self.client.get(f"{BATCHES}{batch.pk}/detail/", **HTMX)
        found = {name.strip().lower()
                 for name in response.get("Vary", "").split(",")}
        self.assertLessEqual({"hx-request", "hx-current-url"}, found)


class SelectionInTheListTests(BatchDetailsCase):

    def test_the_list_selects_the_batch_it_is_asked_for(self) -> None:
        batch = self.made()
        other = make_batch(self.kl, "CH-0013", number="KL0413",
                           date=date(2026, 11, 1))
        root = self.listed(batch)
        self.assertEqual(row_keys(root), [str(other.pk), str(batch.pk)])
        marked = [tr.get("data-item") for tr in root.find("tbody")
                  .find_all("tr") if tr.get("aria-current") == "true"]
        self.assertEqual(marked, [str(batch.pk)])
        self.assertEqual(must_pane(root).get("data-item"), str(batch.pk))

    def test_the_list_without_a_selection_selects_its_first_batch(
            self) -> None:
        self.made()
        other = make_batch(self.kl, "CH-0013", number="KL0413",
                           date=date(2026, 11, 1))
        root = page(self.client.get(BATCHES))
        self.assertEqual(must_pane(root).get("data-item"), str(other.pk))

    def test_an_empty_list_has_an_empty_pane(self) -> None:
        root = page(self.client.get(BATCHES))
        found = must_pane(root)
        self.assertIsNotNone(found)
        self.assertNotIn("data-item", found.attrs)
