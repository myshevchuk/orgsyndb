"""The compound links and the field values of the metadata panel, in theme
builds of modified copies of the test collection (compound-fields "Field
display" and "Values beside compound links", localization "German compound
names").

``MarkupFieldTests`` builds the test collection in English with markup
characters in the label of a project and in the short name of a
substance; ``GermanNameTests`` builds it in German, and
``FallbackNameTests`` builds it in German after removing one German name.
"""

import field_support as fs
import pipeline_support as ps
import support
import test_theme_integration as tti
from pipeline_support import Node, Page


class MarkupFieldTests(tti.SiteCase):
    """The test collection in English, with markup characters in the
    label of the project `first-year-practical` and in the `short_name` of
    `acetone`."""

    LABEL = "First-year <b>&</b>"
    VALUE = "<i>Me</i>2CO & co"

    @classmethod
    def prepare(cls) -> None:
        def relabel(table: dict) -> None:
            (found,) = [t for t in table["vocabularies"]["projects"]
                        if t["key"] == "first-year-practical"]
            found["label"] = cls.LABEL
        ps.edit_snapshot(
            cls.sandbox, relabel,
            support.setting_substance("acetone", short_name=cls.VALUE))

    def starting_materials(self, ident: str) -> tuple[Page, Node]:
        """The page of the procedure `ident` and the value of its
        `Starting materials` pair."""
        page = self.page_of(self.by_id()[ident])
        return page, self.panel(page)["Starting materials"].definition

    def test_markup_in_a_label_is_text(self) -> None:
        """Scenario: Markup in a label is text."""
        page = self.page_of(self.by_id()["OSDB-0002"])
        panel = page.find("dl", "metadata")
        pairs = {pair.label: pair for pair in page.definition_pairs(panel)}
        self.assertEqual(pairs["Project"].definition.norm(),
                         f"Teaching › {self.LABEL}")
        self.assertEqual(panel.find_all("b"), [])
        self.assertEqual(panel.find_all("i"), [])

    def test_markup_in_a_value_beside_a_link_is_text(self) -> None:
        """Scenario: Markup in a value, and a compound without one (the
        value)."""
        page, materials = self.starting_materials("OSDB-0006")
        after = fs.after_link(fs.link_to(page, materials, "acetone"))
        self.assertGreaterEqual(len(after), 2, "no note follows the link")
        self.assertEqual(after[0], " ")
        self.assertEqual((after[1].tag, after[1].classes),
                         ("span", ["compound-beside"]))
        self.assertEqual(after[1].text(), f"({self.VALUE})")
        self.assertEqual(after[1].elements(), [])
        self.assertEqual(materials.find_all("i"), [])
        self.assertEqual(materials.find_all("b"), [])
        self.assertEqual(self.check_notes(page, materials),
                         [None, f"({self.VALUE})"])

    def test_a_compound_without_a_value_beside_has_no_note(self) -> None:
        """Scenario: Markup in a value, and a compound without one (the
        procedure without markup)."""
        page, materials = self.starting_materials("OSDB-0002")
        self.assertEqual(materials.norm(),
                         "Salicylic acid, Acetic anhydride (Ac2O)")
        after = fs.after_link(fs.link_to(page, materials, "salicylic-acid"))
        self.assertEqual(after[0], ", ")
        self.assertEqual(after[1].tag, "a")
        self.assertEqual(self.check_notes(page, materials),
                         [None, "(Ac2O)"])


class GermanNameTests(tti.SiteCase):
    """The test collection, built in German."""

    LOCALE = "de"

    def test_german_names_on_a_german_site(self) -> None:
        """Scenario: German names on a German site."""
        page = self.page_of(self.by_id()["OSDB-0001"])
        product = self.panel(page)["Produkt"].definition
        self.assertEqual(
            [(page.resolve(l.attrs["href"]), l.norm())
             for l in product.find_all("a", "compound")],
            [(fs.substance_url("salicylic-acid"), "Salicylsäure")])


class FallbackNameTests(tti.SiteCase):
    """The test collection in German, with the German name of `acetone`
    removed from its registry."""

    LOCALE = "de"

    @classmethod
    def prepare(cls) -> None:
        ps.edit_snapshot(cls.sandbox, support.setting_substance(
            "acetone", name_de=None))

    def test_a_compound_without_a_german_name(self) -> None:
        """Scenario: A compound without a German name."""
        name = self.registry()["acetone"]["name"]
        self.assertEqual(name, "Acetone")
        page = self.page_of(self.by_id()["OSDB-0006"])
        materials = self.panel(page)["Ausgangsstoffe"].definition
        link = fs.link_to(page, materials, "acetone")
        self.assertEqual(link.norm(), name)
        self.assertEqual([l.norm() for l in materials.find_all("a")],
                         ["Benzaldehyd", name])


if __name__ == "__main__":
    import unittest
    unittest.main()
