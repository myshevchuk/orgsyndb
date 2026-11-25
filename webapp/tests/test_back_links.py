"""Tests of the back links on the lab's record pages (web-app: Back
links), on the pages of the demo data set."""

from typing import Iterator

from . import Element, page
from .collection_support import accept
from .demo_support import SeededCase

ARROW = "←"


def position(order: list[Element], found: Element) -> int:
    """The place of ``found`` in the document ORDER of elements."""
    return next(index for index, each in enumerate(order)
                if each is found)


def in_navigation(link: Element) -> bool:
    """Whether ``link`` stands in a ``nav``: the page's navigation or
    its section tabs."""
    return link.closest("nav") is not None


def hidden(found: Element) -> bool:
    return found.get("aria-hidden") == "true"


class BackLinkTests(SeededCase):

    def records(self) -> list[tuple[str, str, str]]:
        """One page of each kind of record: its name, its URL and the
        URL of the list it belongs to."""
        from inventory.models import Batch, DeliveryNote, Item, Vessel
        from journal.models import Notebook
        from registry.models import Substance
        from tasks.models import Task
        return [
            ("item", f"/lab/inventory/items/{Item.objects.first().pk}/",
             "/lab/inventory/end-products/"),
            ("batch",
             f"/lab/inventory/batches/{Batch.objects.first().pk}/",
             "/lab/inventory/batches/"),
            ("vessel",
             f"/lab/inventory/vessels/{Vessel.objects.first().pk}/",
             "/lab/inventory/vessels/"),
            ("delivery note",
             f"/lab/inventory/deliveries/{DeliveryNote.objects.first().pk}/",
             "/lab/inventory/deliveries/"),
            ("task", f"/lab/tasks/{Task.objects.first().number}/",
             "/lab/tasks/"),
            ("substance",
             f"/lab/registry/substances/{Substance.objects.first().key}/",
             "/lab/registry/"),
            ("notebook", f"/lab/journal/{Notebook.objects.first().code}/",
             "/lab/journal/"),
        ]

    def pages(self) -> Iterator[tuple[str, Element, str, Element]]:
        """Each record page, with its kind, the URL of its list and the
        list's page."""
        for kind, url, list_url in self.records():
            yield kind, self.get(url), list_url, self.get(list_url)

    def back_link(self, root: Element) -> Element:
        found = root.find_all("p", "lab-back")
        self.assertEqual(len(found), 1)
        return found[0]

    def check_links(self) -> None:
        """Assert the contract of the back links on every kind of
        record page in the language the site has now."""
        for kind, root, list_url, listing in self.pages():
            with self.subTest(kind=kind):
                back = self.back_link(root)
                links = back.find_all("a")
                self.assertEqual([a.get("href") for a in links],
                                 [list_url])
                self.assertEqual(links[0].text(hidden),
                                 listing.find("h1").text())
                self.assertNotEqual(listing.find("h1").text(), "")
                self.assertEqual(back.text(hidden),
                                 listing.find("h1").text())
                arrows = [e for e in back.walk() if hidden(e)]
                self.assertEqual([e.text() for e in arrows], [ARROW])
                self.assertTrue(back.text().startswith(ARROW))
                self.assertEqual(
                    [a for a in root.find_all("a")
                     if a.get("href") == list_url
                     and not in_navigation(a)],
                    [links[0]])

    def test_back_links_match_their_lists(self) -> None:
        """Scenario: Back links match their lists."""
        self.check_links()

    def test_english_back_links(self) -> None:
        """Scenario: English back links."""
        accept(language="en")
        self.check_links()
        root = self.get(self.records()[0][1])
        self.assertEqual(self.back_link(root).find("a").text(hidden),
                         "End products")
        root = self.get(self.records()[5][1])
        self.assertEqual(self.back_link(root).find("a").text(hidden),
                         "Substances")

    def test_the_text_is_the_lists_german_heading(self) -> None:
        """Scenario: Back links match their lists (the table's German
        headings)."""
        found = {kind: self.back_link(root).find("a").text(hidden)
                 for kind, root, _, _ in self.pages()}
        self.assertEqual(found["item"], "Endprodukte")
        self.assertEqual(found["substance"], "Substanzen")
        self.assertEqual(found["notebook"], "Laborjournale")

    def test_the_back_link_stands_after_the_demo_note(self) -> None:
        """Requirement: Back links (after the notices of the page
        shell, before the heading)."""
        for kind, root, _, _ in self.pages():
            with self.subTest(kind=kind):
                note = root.find("p", "lab-demo")
                self.assertIsNotNone(note)
                order = list(root.walk())
                back = self.back_link(root)
                self.assertLess(position(order, note),
                                position(order, back))
                self.assertLess(position(order, back),
                                position(order, root.find("h1")))

    def test_the_back_link_stands_after_the_messages(self) -> None:
        """Requirement: Back links (after the notices of the page
        shell: the demo note and the messages)."""
        self.client.force_login(self.account("tbauer"))
        response = self.client.post("/lab/tasks/T-001/start/", follow=True)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        note = root.find("p", "lab-demo")
        self.assertIsNotNone(note)
        messages = root.find(cls="lab-messages")
        self.assertIsNotNone(messages)
        order = list(root.walk())
        back = self.back_link(root)
        self.assertLess(position(order, note), position(order, messages))
        self.assertLess(position(order, messages), position(order, back))
        self.assertLess(position(order, back),
                        position(order, root.find("h1")))

    def test_the_notebook_page_keeps_no_plain_link(self) -> None:
        """Requirement: Back links (the notebook page's former plain
        link to ``/lab/journal/`` is gone)."""
        from journal.models import Notebook
        root = self.get(f"/lab/journal/{Notebook.objects.first().code}/")
        links = [a for a in root.find_all("a")
                 if a.get("href") == "/lab/journal/"
                 and not in_navigation(a)]
        self.assertEqual(len(links), 1)
        self.assertIsNotNone(links[0].closest("p"))
        self.assertIn("lab-back", links[0].closest("p").classes)
