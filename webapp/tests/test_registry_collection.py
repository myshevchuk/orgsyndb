"""Tests of the collection on the registry's pages: the procedures,
sequences and route tree beside a substance, the copy button, and the
list's filters (lab-registry: Registry pages)."""

from typing import Any

from django.test import TestCase

from collection.models import Procedure

from . import Element, make_group, make_substance, page
from .collection_support import accept
from .demo_support import SeededCase
from .registry_support import REGISTRY, substance_url
from .widget_support import kv, title_of, widget, widget_grid, widgets


def titles(root: Element) -> list[str | None]:
    """The titles of the widgets of a page."""
    return [title_of(w) for w in widgets(root)]


def rows_under(root: Element, *title: str) -> list[dict[str, Element]]:
    """The body rows of the table of the widget titled TITLE, each as a
    mapping from column header to cell."""
    return widget_grid(widget(root, *title))[1]


def link(item: Element) -> tuple[str | None, str]:
    """The ``href`` and text of the first link of ITEM."""
    first = item.find("a")
    return first.get("href"), first.text()


class SectionsTests(SeededCase):
    """Scenario: Procedures beside a substance."""

    def get(self, key: str) -> Element:
        response = self.client.get(substance_url(key))
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_made_by_with_yield_and_badge(self) -> None:
        (row,) = rows_under(self.get("acetylsalicylic-acid"),
                            "Hergestellt nach")
        self.assertEqual(link(row["Vorschrift"]), (
            "/procedures/osdb-0002/",
            "OSDB-0002 Aspirin (Acetylsalicylsäure)"))
        self.assertEqual(row["Ausbeute"].text(), "75 %")
        badge = row["Status"].find("span", cls="badge")
        self.assertEqual(badge.text(), "Entwurf")
        self.assertIn("badge--draft", badge.classes)

    def test_the_sequences(self) -> None:
        (row,) = rows_under(self.get("acetylsalicylic-acid"),
                            "Synthesewege")
        cell = row["Syntheseweg"]
        self.assertEqual(link(cell)[0], "/sequences/seq-0001/")
        self.assertIn("Aspirin", link(cell)[1])

    def test_the_route_tree(self) -> None:
        tree = widget(self.get("acetylsalicylic-acid"),
                      "Herstellungswege").find("ul", cls="route-tree")
        (top,) = [li for li in tree.children
                  if isinstance(li, Element) and li.tag == "li"]
        self.assertIn("route-step", top.classes)
        self.assertEqual(link(top)[0], "/procedures/osdb-0002/")
        compounds = [li for li in top.find_all("li")
                     if "route-compound" in li.classes
                     and li.parent.parent is top]
        self.assertEqual([link(li) for li in compounds], [
            (substance_url("salicylic-acid"), "Salicylsäure"),
            (substance_url("acetic-anhydride"), "Essigsäureanhydrid")])
        inner = [li for li in compounds[0].find_all("li")
                 if "route-step" in li.classes]
        self.assertEqual([link(li)[0] for li in inner],
                         ["/procedures/osdb-0001/"])
        self.assertIn(" · 80 % · ", inner[0].text())
        self.assertFalse(top.find_all("span", cls="route-more"))

    def test_a_substance_made_and_used(self) -> None:
        root = self.get("salicylic-acid")
        self.assertEqual([link(row["Vorschrift"])[0] for row in
                          rows_under(root, "Hergestellt nach")],
                         ["/procedures/osdb-0001/"])
        used = rows_under(root, "Verwendet in")
        self.assertEqual([link(row["Vorschrift"])[0] for row in used],
                         ["/procedures/osdb-0002/"])
        self.assertEqual(used[0]["Status"].find("span", cls="badge").text(),
                         "Entwurf")
        self.assertNotIn("Herstellungswege", titles(root))

    def test_an_entry_of_a_general_procedure(self) -> None:
        made = rows_under(self.get("1-biphenyl-4-yl-ethanol"),
                          "Hergestellt nach")
        self.assertEqual([link(row["Vorschrift"])[0] for row in made],
                         ["/procedures/osdb-0005/", "/procedures/osdb-0009/"])
        self.assertEqual(made[0]["Ausbeute"].text(), "90 %")
        self.assertEqual(made[1]["Eintrag"].text(), "Eintrag 1")
        self.assertEqual(made[1]["Ausbeute"].text(), "90 %")

    def test_sections_without_items_are_left_out(self) -> None:
        make_substance("lonely-compound")
        shown = titles(self.get("lonely-compound"))
        for name in ("Hergestellt nach", "Verwendet in", "Synthesewege",
                     "Herstellungswege"):
            with self.subTest(section=name):
                self.assertNotIn(name, shown)

    def test_a_withdrawn_procedure_is_left_out(self) -> None:
        Procedure.objects.filter(key="OSDB-0002").update(withdrawn=True)
        shown = titles(self.get("acetylsalicylic-acid"))
        self.assertNotIn("Hergestellt nach", shown)
        self.assertNotIn("Herstellungswege", shown)

    def test_a_procedure_without_a_status_has_no_badge(self) -> None:
        Procedure.objects.filter(key="OSDB-0001").update(status="")
        (row,) = rows_under(self.get("salicylic-acid"), "Hergestellt nach")
        self.assertIsNone(row["Status"].find("span", cls="badge"))

    def test_the_english_texts(self) -> None:
        accept(language="en")
        root = self.get("1-biphenyl-4-yl-ethanol")
        for name in ("Made by", "Routes"):
            with self.subTest(section=name):
                self.assertIn(name, titles(root))
        made = rows_under(root, "Made by")
        self.assertEqual(made[1]["Entry"].text(), "entry 1")
        self.assertEqual(made[1]["Yield"].text(), "90 %")
        self.assertEqual(made[0]["Status"].find("span", cls="badge").text(),
                         "draft")
        self.assertIn("Used in", titles(self.get("salicylic-acid")))
        self.assertIn("Sequences",
                      titles(self.get("acetylsalicylic-acid")))

    def test_the_copy_button(self) -> None:
        cell = kv(widget(self.get("acetylsalicylic-acid"),
                         "Verbindung"))["SMILES"]
        code = cell.find("code", attrs={"data-smiles": True})
        self.assertEqual(code.text(), "CC(=O)Oc1ccccc1C(=O)O")
        (button,) = cell.find_all("button",
                                  attrs={"data-copy-smiles": True})
        self.assertEqual((button.get("type"), button.text()),
                         ("button", "Kopieren"))
        self.assertIn("hidden", button.attrs)
        self.assertEqual(button.get("data-copied"), "Kopiert")
        self.assertEqual(button.get("data-selected"),
                         "Markiert: Strg+C drücken")
        self.assertIs(code.parent, button.parent)


class FilterTests(TestCase):
    """Scenario: Filters of the list."""

    @classmethod
    def setUpTestData(cls) -> None:
        synthesised = make_group("synthesised")
        final = make_group("final-products", parent=synthesised)
        make_substance("a", group=final)
        make_substance("b", group=synthesised)
        make_substance("c", group=make_group("purchased"))

    def listed(self, query: str) -> list[str]:
        response = self.client.get(f"{REGISTRY}?{query}")
        self.assertEqual(response.status_code, 200)
        main = page(response).find("main")
        return sorted(a.get("href").rstrip("/").rsplit("/", 1)[1]
                      for a in main.find(id="item-rows").find_all("a"))

    def test_a_group_takes_the_groups_below(self) -> None:
        self.assertEqual(self.listed("group=synthesised"), ["a", "b"])
        self.assertEqual(self.listed("group=final-products"), ["a"])
        self.assertEqual(self.listed("group=nope"), [])
        self.assertEqual(self.listed("group="), ["a", "b", "c"])

    def test_a_class_takes_the_classes_below(self) -> None:
        from . import make_class
        carbonyl = make_class("carbonyl-compounds")
        make_substance("d", classes=[make_class("ketones",
                                                parent=carbonyl)])
        make_substance("e", classes=[carbonyl])
        self.assertEqual(self.listed("class=carbonyl-compounds"),
                         ["d", "e"])
        self.assertEqual(self.listed("class=ketones"), ["d"])
        self.assertEqual(self.listed("class=nope"), [])

    def test_the_filters_and_the_search_narrow_together(self) -> None:
        self.assertEqual(self.listed("group=synthesised&q=a"), ["a"])

    def test_the_form_keeps_its_values(self) -> None:
        response = self.client.get(f"{REGISTRY}?group=final-products&q=a")
        form = page(response).find("main").find("form")
        chosen = form.find("select", name="group").find(
            "option", attrs={"selected": True})
        self.assertEqual(chosen.get("value"), "final-products")
        self.assertEqual(form.find("input", name="q").get("value"), "a")

    def test_the_choices(self) -> None:
        form = page(self.client.get(REGISTRY)).find("main").find("form")
        labels = {select.get("name"): select.parent.text().split()[0]
                  for select in form.find_all("select")}
        self.assertEqual(labels, {"group": "Bestandsgruppe",
                                  "class": "Stoffklasse"})
        values = [o.get("value") for o in
                  form.find("select", name="group").find_all("option")]
        self.assertEqual(values, ["", "purchased", "synthesised",
                                  "final-products"])
