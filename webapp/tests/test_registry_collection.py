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


def headings(root: Element) -> list[str]:
    return [h.text() for h in root.find("main").find_all("h2")]


def items_under(root: Element, heading: str) -> list[Element]:
    """The items of the list that follows the ``h2`` HEADING."""
    main = root.find("main")
    found = [h for h in main.find_all("h2") if h.text() == heading]
    assert len(found) == 1, f"{len(found)} headings {heading!r}"
    siblings = [c for c in found[0].parent.children
                if isinstance(c, Element)]
    after = siblings[siblings.index(found[0]) + 1]
    assert after.tag == "ul", after.tag
    return [li for li in after.children
            if isinstance(li, Element) and li.tag == "li"]


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
        (item,) = items_under(self.get("acetylsalicylic-acid"),
                              "Hergestellt nach")
        self.assertEqual(link(item), ("/procedures/osdb-0002/",
                                      "OSDB-0002 Aspirin (Acetylsalicylsäure)"))
        self.assertIn(" · 75 % · ", item.text())
        badge = item.find("span", cls="badge")
        self.assertEqual(badge.text(), "Entwurf")
        self.assertIn("badge--draft", badge.classes)

    def test_the_sequences(self) -> None:
        (item,) = items_under(self.get("acetylsalicylic-acid"),
                              "Synthesewege")
        self.assertEqual(link(item)[0], "/sequences/seq-0001/")
        self.assertIn("Aspirin", link(item)[1])

    def test_the_route_tree(self) -> None:
        (top,) = items_under(self.get("acetylsalicylic-acid"),
                             "Herstellungswege")
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
        self.assertEqual([link(li)[0] for li in
                          items_under(root, "Hergestellt nach")],
                         ["/procedures/osdb-0001/"])
        used = items_under(root, "Verwendet in")
        self.assertEqual([link(li)[0] for li in used],
                         ["/procedures/osdb-0002/"])
        self.assertEqual(used[0].find("span", cls="badge").text(),
                         "Entwurf")
        self.assertNotIn("Herstellungswege", headings(root))

    def test_an_entry_of_a_general_procedure(self) -> None:
        made = items_under(self.get("1-biphenyl-4-yl-ethanol"),
                           "Hergestellt nach")
        self.assertEqual([link(li)[0] for li in made],
                         ["/procedures/osdb-0005/", "/procedures/osdb-0009/"])
        self.assertIn(" · 90 % · ", made[0].text())
        self.assertIn(" · Eintrag 1 · 90 % · ", made[1].text())

    def test_sections_without_items_are_left_out(self) -> None:
        make_substance("lonely-compound")
        shown = headings(self.get("lonely-compound"))
        for name in ("Hergestellt nach", "Verwendet in", "Synthesewege",
                     "Herstellungswege"):
            with self.subTest(section=name):
                self.assertNotIn(name, shown)

    def test_a_withdrawn_procedure_is_left_out(self) -> None:
        Procedure.objects.filter(key="OSDB-0002").update(withdrawn=True)
        shown = headings(self.get("acetylsalicylic-acid"))
        self.assertNotIn("Hergestellt nach", shown)
        self.assertNotIn("Herstellungswege", shown)

    def test_a_procedure_without_a_status_has_no_badge(self) -> None:
        Procedure.objects.filter(key="OSDB-0001").update(status="")
        (item,) = items_under(self.get("salicylic-acid"), "Hergestellt nach")
        self.assertIsNone(item.find("span", cls="badge"))

    def test_the_english_texts(self) -> None:
        accept(language="en")
        root = self.get("1-biphenyl-4-yl-ethanol")
        for name in ("Made by", "Routes"):
            with self.subTest(section=name):
                self.assertIn(name, headings(root))
        made = items_under(root, "Made by")
        self.assertIn(" · entry 1 · 90 % · ", made[1].text())
        self.assertEqual(made[0].find("span", cls="badge").text(), "draft")
        shown = headings(self.get("salicylic-acid"))
        self.assertIn("Used in", shown)
        self.assertIn("Sequences", headings(self.get("acetylsalicylic-acid")))

    def test_the_copy_button(self) -> None:
        main = self.get("acetylsalicylic-acid").find("main")
        code = main.find("code", attrs={"data-smiles": True})
        self.assertEqual(code.text(), "CC(=O)Oc1ccccc1C(=O)O")
        (button,) = main.find_all("button",
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
                      for a in main.find("table").find_all("a"))

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
