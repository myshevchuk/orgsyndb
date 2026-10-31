"""Compound pages and the compound directory of a theme build (site-theme
"Compound pages" and "Compound directory", site-build "Hugo
configuration", localization "German compound names").

``CompoundSiteTests`` builds the test collection in English;
``GermanCompoundTests`` builds it in German, and ``FallbackNameTests``
builds it in German after removing one German name.
"""

import json
import re

import field_support as fs
import pipeline_support as ps
import sequence_support as ss
import test_theme_integration as tti
from pipeline_support import Content, Page

FACT_LABELS = ["Formula", "MW", "CAS", "SMILES"]
SEPARATOR = fs.PATH_SEPARATOR


class CompoundCase(tti.SiteCase):
    """Helpers for the scans of compound pages."""

    def compound_page(self, key: str) -> Page:
        path = self.public / "compounds" / key / "index.html"
        self.assertTrue(path.is_file(), f"compounds/{key}/ was not built")
        return ps.load_page(self.public, path)

    def made_by(self, key: str) -> list[Content]:
        return sorted((i for i in self.content()
                       if key in [e["compound"] for e in i.products]),
                      key=lambda i: i.id)

    def made_by_entries(self, key: str) -> list[tuple[Content, int | None,
                                                     int | float]]:
        """The ``Made by`` list of a compound: for each procedure by ID
        its yield of the compound, or for a general procedure each entry
        that makes it, in entry order, with the entry's number and
        yield."""
        found = []
        for item in self.made_by(key):
            if not item.is_general:
                found.append((item, None, next(
                    e["yield_percent"] for e in item.products
                    if e["compound"] == key)))
                continue
            for number, entry in enumerate(item.scope, 1):
                for product in entry["products"]:
                    if product["compound"] == key:
                        found.append((item, number,
                                      product["yield_percent"]))
        return found

    def used_in_by(self, key: str) -> list[Content]:
        return sorted((i for i in self.content() if key in i.substrates),
                      key=lambda i: i.id)

    def shown(self, key: str) -> str:
        return ps.shown_name(self.registry()[key], self.LOCALE)

    def fields(self) -> list[fs.Field]:
        """The fields the collection declares, in the site's language."""
        return fs.read_fields(self.sandbox.root / "orgsyndb.toml",
                              self.LOCALE)

    def declared_pairs(self, key: str) -> list[tuple[str, str]]:
        """The label and value of each declared field the compound sets
        that its page shows after the built-in facts, in order, as read
        from the page."""
        page = self.compound_page(key)
        pairs = page.definition_pairs(page.find("dl", "compound-facts"))
        built_in = 3 + bool(self.registry()[key].get("cas"))
        return [(p.label, p.definition.norm()) for p in pairs[built_in:]]


class CompoundSiteTests(CompoundCase):
    """The test collection, built in English."""

    def test_a_page_per_compound(self) -> None:
        """Scenario: A page per compound."""
        registry = self.registry()
        self.assertGreater(len(registry), 10)
        built = sorted(p.parent.name for p in
                       (self.public / "compounds").glob("*/index.html"))
        self.assertEqual(built, sorted(registry))
        for key, compound in registry.items():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                main = page.find("main")
                self.assertEqual([h.norm() for h in main.find_all("h1")],
                                 [compound["name"]])
                self.assertEqual(page.title(),
                                 f"{compound['name']} | OrgSynDB")
                self.check_facts(page, compound)
                self.check_figure(page, compound)

    def check_facts(self, page: Page, compound: dict) -> None:
        facts = page.find("main").find("dl", "compound-facts")
        self.assertIsNotNone(facts, "no dl.compound-facts")
        pairs = page.definition_pairs(facts)
        declared = fs.shown(self.fields(), compound, self.LOCALE, page=True)
        wanted = [label for label in FACT_LABELS
                  if label != "CAS" or compound.get("cas")]
        wanted += [field.label for field, _ in declared]
        self.assertEqual([p.label for p in pairs], wanted)
        values = {p.label: p.definition for p in pairs}
        for field, text in declared:
            self.assertEqual(values[field.label].norm(), text, field.key)
        self.assertEqual(values["Formula"].norm(), compound["formula"])
        self.assertEqual(
            [s.norm() for s in values["Formula"].find_all("sub")],
            re.findall(r"[0-9]+", compound["formula"]))
        self.assertEqual(values["MW"].norm(), f"{compound['mw']} g/mol")
        if compound.get("cas"):
            self.assertEqual(values["CAS"].norm(), compound["cas"])
        code = values["SMILES"].find("code", data_smiles=True)
        self.assertIsNotNone(code, "no code[data-smiles]")
        self.assertEqual(code.norm(), compound["smiles"])
        copy = values["SMILES"].find("button", "copy-button")
        self.assertIsNotNone(copy, "no button.copy-button")
        self.assertEqual(copy.attrs.get("type"), "button")
        self.assertIn("data-copy-smiles", copy.attrs)
        self.assertIn("hidden", copy.attrs)
        self.assertEqual(copy.norm(), "Copy")
        self.assertGreater(page.index_of(copy), page.index_of(code))
        for pair in pairs:
            self.assertNotEqual(pair.gap, "", pair.label)
            self.assertEqual(pair.gap.strip(), "", pair.label)

    def check_figure(self, page: Page, compound: dict) -> None:
        main = page.find("main")
        figures = main.find_all("figure")
        image = compound.get("structure_image")
        if image is None:
            self.assertEqual(figures, [], "a figure without an image")
            return
        self.assertEqual(len(figures), 1)
        self.assertTrue(figures[0].has_class("structure"))
        self.assertFalse(figures[0].has_class("structure--placeholder"))
        images = figures[0].find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].attrs.get("alt"),
                         f"Structure of {compound['name']}")
        self.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/" + image)
        self.assertTrue(ps.target_file(self.public, "/" + image).is_file())
        self.assertLess(page.index_of(main.find("h1")),
                        page.index_of(figures[0]))
        self.assertLess(page.index_of(figures[0]),
                        page.index_of(main.find("dl", "compound-facts")))

    def test_declared_fields_follow_the_built_in_facts(self) -> None:
        """Scenario: Declared fields in English."""
        classes = {
            "carboxylic": "Carbonyl compounds" + SEPARATOR
                          + "Carboxylic acids",
            "esters": SEPARATOR.join(
                ["Carbonyl compounds", "Carboxylic acid derivatives",
                 "Esters"]),
        }
        expected = {
            "acetylsalicylic-acid": [
                ("Item no.", "CH-0010"), ("Short name", "ASA"),
                ("Chemical class",
                 f"{classes['carboxylic']}, {classes['esters']}"),
                ("Made in house", "Yes")],
            "acetic-acid": [
                ("Item no.", "CH-0006"), ("Short name", "AcOH"),
                ("Chemical class", classes["carboxylic"]),
                ("Stock", "2500 g"), ("Made in house", "No")],
            "ethyl-triphenylphosphoranylidene-acetate": [
                ("Item no.", "CH-0015"),
                ("Chemical class", f"Organophosphorus compounds, "
                                   f"{classes['esters']}"),
                ("Stock", "12.5 g"), ("Made in house", "No")],
            "methyl-salicylate": [
                ("Item no.", "CH-0018"),
                ("Chemical class", f"{classes['esters']}, Phenols")],
            "4-bromoacetophenone": [
                ("Item no.", "CH-0005"),
                ("Chemical class", SEPARATOR.join(
                    ["Carbonyl compounds", "Ketones", "Aryl ketones"])
                 + ", Aryl halides"),
                ("Stock", "100 g"), ("Made in house", "No")],
        }
        for key, pairs in expected.items():
            with self.subTest(compound=key):
                self.assertEqual(self.declared_pairs(key), pairs)

    def test_every_compound_sets_an_item_number(self) -> None:
        """Scenario: Declared fields in English (a required field)."""
        for key, compound in self.registry().items():
            with self.subTest(compound=key):
                self.assertEqual(
                    self.declared_pairs(key)[0],
                    ("Item no.", compound["item_number"]))

    def test_the_parts_come_in_order(self) -> None:
        """Scenario: A page per compound (order of the parts)."""
        for key in self.registry():
            page = self.compound_page(key)
            main = page.find("main")
            with self.subTest(compound=key):
                parts = [main.find("h1"), main.find("dl", "compound-facts")]
                for cls in ("compound-made-by", "compound-used-in",
                            "compound-sequences"):
                    wanted = {
                        "compound-made-by": self.made_by(key),
                        "compound-used-in": self.used_in_by(key),
                        "compound-sequences": ss.sequences_making(
                            key, self.sequences())}[cls]
                    section = main.find("section", cls)
                    self.assertEqual(section is not None, bool(wanted), cls)
                    if section is not None:
                        parts.append(section)
                order = [page.index_of(n) for n in parts]
                self.assertEqual(order, sorted(order))

    def test_made_by_and_used_in(self) -> None:
        """Scenario: Made by and used in."""
        salicylic = self.compound_page("salicylic-acid")
        made = salicylic.find("section", "compound-made-by")
        self.assertEqual([h.norm() for h in made.find_all("h2")],
                         ["Made by"])
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylic acid · 80 % · draft"])
        used = salicylic.find("section", "compound-used-in")
        self.assertEqual([h.norm() for h in used.find_all("h2")],
                         ["Used in"])
        self.assertEqual(
            [li.norm() for li in used.find_all("li")],
            ["OSDB-0002 Aspirin (acetylsalicylic acid) · draft"])
        methyl = self.compound_page("methyl-salicylate")
        self.assertIsNone(methyl.find("section", "compound-made-by"))
        used = methyl.find("section", "compound-used-in")
        self.assertEqual([li.norm() for li in used.find_all("li")],
                         ["OSDB-0001 Salicylic acid · draft"])

    def test_every_made_by_and_used_in_list_follows_the_content(
            self) -> None:
        """Scenario: Made by and used in (all compounds)."""
        for key in self.registry():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                for cls, items in (
                        ("compound-made-by", self.made_by_entries(key)),
                        ("compound-used-in",
                         [(i, None, None) for i in self.used_in_by(key)])):
                    section = page.find("section", cls)
                    if not items:
                        self.assertIsNone(section, cls)
                        continue
                    entries = section.find("ul").find_all("li")
                    self.assertEqual(len(entries), len(items))
                    for entry, (item, number, made) in zip(entries, items):
                        link = entry.elements()[0]
                        self.assertEqual(link.tag, "a")
                        self.assertEqual(page.resolve(link.attrs["href"]),
                                         f"/procedures/{item.slug}/")
                        self.assertEqual(link.norm(),
                                         f"{item.id} {item.title}")
                        badge = entry.find("span", "badge")
                        self.assertIsNotNone(badge, "no status badge")
                        self.assertIn(f"badge--{item.data['status']}",
                                      badge.classes)
                        self.assertEqual(badge.norm(), item.data["status"])
                        text = f"{item.id} {item.title}"
                        if number is not None:
                            text += f" · entry {number}"
                        if cls == "compound-made-by":
                            text += f" · {made} %"
                        self.assertEqual(
                            entry.norm(), f"{text} · {badge.norm()}")

    def test_the_sequences_that_make_a_compound(self) -> None:
        """Scenario: Links to the demo sequence (the compound pages)."""
        sequences = self.sequences()
        self.assertEqual([s.id for s in sequences], ["SEQ-0001", "SEQ-0002"])
        for key in self.registry():
            with self.subTest(compound=key):
                ss.check_compound_sequences(
                    self, self.compound_page(key), key, sequences, "en")
        page = self.compound_page("acetylsalicylic-acid")
        section = page.find("section", "compound-sequences")
        self.assertEqual(
            [(l.target, l.node.norm()) for l in page.links(section)],
            [("/sequences/seq-0001/", "Aspirin from oil of wintergreen")])
        self.assertLess(page.index_of(page.find("dl", "compound-facts")),
                        page.index_of(section))

    def test_made_by_an_entry_of_a_general_procedure(self) -> None:
        """Scenario: Made by an entry of a general procedure."""
        page = self.compound_page("1-biphenyl-4-yl-ethanol")
        made = page.find("section", "compound-made-by")
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · 90 % · draft",
             "OSDB-0009 Secondary benzylic alcohols by sodium borohydride "
             "reduction · entry 1 · 90 % · draft"])
        self.assertIsNone(page.find("section", "compound-used-in"))
        acetylbiphenyl = self.compound_page("4-acetylbiphenyl")
        used = acetylbiphenyl.find("section", "compound-used-in")
        self.assertEqual(
            [li.norm() for li in used.find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · draft",
             "OSDB-0009 Secondary benzylic alcohols by sodium borohydride "
             "reduction · draft"])
        for key in ("acetophenone", "1-phenylethanol",
                    "1-4-bromophenyl-ethanol"):
            self.assertTrue((self.public / "compounds" / key
                             / "index.html").is_file(), key)

    def test_compound_pages_are_not_indexed(self) -> None:
        """Scenario: Compound pages are not indexed."""
        for key in self.registry():
            page = self.compound_page(key)
            with self.subTest(compound=key):
                self.assertEqual(page.find_all(data_pagefind_body=True), [])
                sources = [page.resolve(s) for s in page.script_sources()
                           if s]
                self.assertTrue(sources)
                for source in sources:
                    self.assertRegex(source, r"^/js/site\.")
        page = self.compound_page("isopentyl-acetate")
        image = page.find("figure", "structure").find("img")
        self.assertEqual(
            ps.target_file(self.public, page.resolve(image.attrs["src"])),
            self.public / "structures" / "isopentyl-acetate.svg")
        self.assertTrue((self.public / "structures"
                         / "isopentyl-acetate.svg").is_file())

    def test_the_directory_lists_every_compound(self) -> None:
        """Scenario: Every compound is listed."""
        path = self.public / "compounds" / "index.html"
        self.assertTrue(path.is_file(), "compounds/ was not built")
        page = ps.load_page(self.public, path)
        main = page.find("main")
        self.assertEqual([h.norm() for h in main.find_all("h1")],
                         ["Compounds"])
        self.assertEqual(page.title(), "Compounds | OrgSynDB")
        self.assertEqual(main.find_all("form"), [])
        self.assertEqual(main.find_all("input"), [])
        tables = main.find_all("table", "compound-table")
        self.assertEqual(len(tables), 1)
        model = next(m for m in page.tables() if m.node is tables[0])
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Compound", "Formula", "MW", "CAS", "Item no.",
                          "Chemical class", "Made by", "Used in"])
        columns = [f for f in self.fields() if f.column]
        self.assertEqual([f.key for f in columns],
                         ["item_number", "chemical_class"])
        registry = self.registry()
        names = {self.shown(key): key for key in registry}
        self.assertEqual(len(names), len(registry), "names are not unique")
        rows = [tr for tr in tables[0].find_all("tr") if tr.find("td")]
        self.assertEqual(len(rows), len(registry))
        listed = []
        for row in rows:
            cells = [c for c in row.elements() if c.tag in ("td", "th")]
            self.assertEqual(len(cells), 8)
            link = page.links(cells[0])[0]
            key = names[link.node.norm()]
            listed.append(link.node.norm())
            compound = registry[key]
            with self.subTest(compound=key):
                self.assertEqual(link.target, f"/compounds/{key}/")
                self.assertEqual(cells[1].norm(), compound["formula"])
                self.assertEqual(
                    [s.norm() for s in cells[1].find_all("sub")],
                    re.findall(r"[0-9]+", compound["formula"]))
                self.assertEqual(cells[2].norm(),
                                 f"{compound['mw']} g/mol")
                self.assertEqual(cells[3].norm(), compound.get("cas", ""))
                texts = {f.key: text for f, text in fs.shown(
                    columns, compound, self.LOCALE, page=False)}
                for cell, field in zip(cells[4:6], columns):
                    self.assertEqual(cell.norm(), texts.get(field.key, ""),
                                     field.key)
                self.assertEqual(cells[6].norm(),
                                 str(len(self.made_by(key))))
                self.assertEqual(cells[7].norm(),
                                 str(len(self.used_in_by(key))))
        self.assertEqual(listed, sorted(names))
        self.assertEqual(len(set(listed)), len(listed))

    def test_the_directory_writes_a_choice_as_its_own_labels(self) -> None:
        """Scenario: Every compound is listed (the column fields)."""
        page = ps.load_page(self.public, self.public / "compounds"
                            / "index.html")
        model = next(m for m in page.tables()
                     if m.node.has_class("compound-table"))
        rows = {r[0].text: r for r in model.rows[1:]}
        self.assertEqual(
            [c.text for c in rows["Acetylsalicylic acid"][4:6]],
            ["CH-0010", "Carboxylic acids, Esters"])
        self.assertEqual(
            [c.text for c in rows[self.shown("4-bromoacetophenone")][4:6]],
            ["CH-0005", "Aryl ketones, Aryl halides"])
        self.assertEqual(
            [c.text for c in rows["Benzaldehyde"][4:6]],
            ["CH-0011", "Aldehydes"])


class GermanCompoundTests(CompoundCase):
    """The test collection, built in German."""

    LOCALE = "de"

    def test_german_names_on_a_german_site(self) -> None:
        """Scenario: German names on a German site."""
        page = self.compound_page("salicylic-acid")
        self.assertEqual(page.find("main").find("h1").norm(), "Salicylsäure")
        self.assertEqual(page.title(), "Salicylsäure | OrgSynDB")
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        registry = self.registry()
        table = directory.find("table", "compound-table")
        links = [directory.links(row)[0] for row in table.find_all("tr")
                 if directory.links(row)]
        names = [l.node.norm() for l in links]
        self.assertIn("Salicylsäure", names)
        self.assertEqual(names, sorted(
            registry[key]["name_de"] for key in registry))
        link = next(l for l in links if l.node.norm() == "Salicylsäure")
        self.assertEqual(link.target, "/compounds/salicylic-acid/")
        procedure = ps.load_page(self.public, self.public / "procedures"
                                 / "osdb-0001" / "index.html")
        product = procedure.find("dl", "metadata")
        pair = next(p for p in procedure.definition_pairs(product)
                    if p.label == "Produkt")
        self.assertEqual([l.norm() for l in pair.definition.find_all("a")],
                         ["Salicylsäure"])

    def test_german_labels_on_compound_pages(self) -> None:
        """Scenario: German page shell (compound pages)."""
        page = self.compound_page("salicylic-acid")
        facts = page.find("dl", "compound-facts")
        self.assertEqual([p.label for p in page.definition_pairs(facts)],
                         ["Summenformel", "Molmasse", "CAS", "SMILES",
                          "Artikelnr.", "Stoffklasse", "Eigene Herstellung"])
        values = {p.label: p.definition.norm()
                  for p in page.definition_pairs(facts)}
        self.assertEqual(values["Molmasse"], "138,12 g/mol")
        self.assertEqual(page.find("button", "copy-button").norm(),
                         "Kopieren")
        made = page.find("section", "compound-made-by")
        self.assertEqual([h.norm() for h in made.find_all("h2")],
                         ["Hergestellt nach"])
        used = page.find("section", "compound-used-in")
        self.assertEqual([h.norm() for h in used.find_all("h2")],
                         ["Verwendet in"])
        self.assertEqual(
            [li.norm() for li in made.find_all("li")],
            ["OSDB-0001 Salicylsäure · 80 % · Entwurf"])
        aspirin = self.compound_page("acetylsalicylic-acid")
        sequences = aspirin.find("section", "compound-sequences")
        self.assertEqual([h.norm() for h in sequences.find_all("h2")],
                         ["Synthesewege"])
        self.assertEqual(
            [(l.target, l.node.norm()) for l in aspirin.links(sequences)],
            [("/sequences/seq-0001/", "Aspirin aus Wintergrünöl")])
        general = self.compound_page("1-biphenyl-4-yl-ethanol")
        self.assertEqual(
            [li.norm() for li in general.find(
                "section", "compound-made-by").find_all("li")],
            ["OSDB-0005 1-(Biphenyl-4-yl)ethanol · 90 % · Entwurf",
             "OSDB-0009 Sekundäre Benzylalkohole durch Reduktion mit "
             "Natriumborhydrid · Eintrag 1 · 90 % · Entwurf"])
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        table = directory.find("table", "compound-table")
        model = next(m for m in directory.tables() if m.node is table)
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Verbindung", "Summenformel", "Molmasse", "CAS",
                          "Artikelnr.", "Stoffklasse", "Hergestellt nach",
                          "Verwendet in"])
        row = next(m for m in model.rows[1:]
                   if m[0].text == "Salicylsäure")
        self.assertEqual(row[2].text, "138,12 g/mol")
        self.assertEqual([c.text for c in row[4:6]],
                         ["CH-0020", "Carbonsäuren, Phenole"])

    def test_declared_fields_in_german(self) -> None:
        """Scenario: Declared fields in German."""
        carbonyl = "Carbonylverbindungen"
        expected = {
            "acetic-acid": [
                ("Artikelnr.", "CH-0006"), ("Kurzname", "AcOH"),
                ("Stoffklasse", f"{carbonyl}{SEPARATOR}Carbonsäuren"),
                ("Bestand", "2500 g"), ("Eigene Herstellung", "Nein")],
            "ethyl-triphenylphosphoranylidene-acetate": [
                ("Artikelnr.", "CH-0015"),
                ("Stoffklasse", "Organophosphorverbindungen, " + SEPARATOR
                 .join([carbonyl, "Carbonsäurederivate", "Ester"])),
                ("Bestand", "12,5 g"), ("Eigene Herstellung", "Nein")],
            "salicylic-acid": [
                ("Artikelnr.", "CH-0020"),
                ("Stoffklasse", f"{carbonyl}{SEPARATOR}Carbonsäuren, "
                                "Phenole"),
                ("Eigene Herstellung", "Ja")],
            "methyl-salicylate": [
                ("Artikelnr.", "CH-0018"),
                ("Stoffklasse", SEPARATOR.join(
                    [carbonyl, "Carbonsäurederivate", "Ester"])
                 + ", Phenole")],
        }
        for key, pairs in expected.items():
            with self.subTest(compound=key):
                self.assertEqual(self.declared_pairs(key), pairs)

    def test_every_declared_value_reads_as_the_fields_say(self) -> None:
        """Scenario: Declared fields in German (every compound)."""
        fields = self.fields()
        self.assertEqual([f.label for f in fields],
                         ["Artikelnr.", "Kurzname", "Stoffklasse",
                          "Bestand", "Eigene Herstellung"])
        for key, compound in self.registry().items():
            with self.subTest(compound=key):
                self.assertEqual(
                    self.declared_pairs(key),
                    [(f.label, text) for f, text in fs.shown(
                        fields, compound, "de", page=True)])


class NumberAndBooleanColumnTests(CompoundCase):
    """The test collection in English, with `column = true` added to the
    declarations of `stock` and `in_house`."""

    @classmethod
    def prepare(cls) -> None:
        path = cls.sandbox.root / "orgsyndb.toml"
        text = path.read_text(encoding="utf-8")
        for key in ("stock", "in_house"):
            anchor = f'key = "{key}"\n'
            assert text.count(anchor) == 1, key
            text = text.replace(anchor, anchor + "column = true\n")
        path.write_text(text, encoding="utf-8")

    def directory(self):
        page = ps.load_page(self.public, self.public / "compounds"
                            / "index.html")
        table = page.find("table", "compound-table")
        return next(m for m in page.tables() if m.node is table)

    def test_the_columns_follow_the_chemical_class(self) -> None:
        """Scenario: Number and boolean columns."""
        model = self.directory()
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Compound", "Formula", "MW", "CAS", "Item no.",
                          "Chemical class", "Stock", "Made in house",
                          "Made by", "Used in"])
        header = model.rows[0]
        self.assertIn("num", header[6].classes)
        self.assertNotIn("num", header[7].classes)
        for row in model.rows[1:]:
            with self.subTest(compound=row[0].text):
                self.assertEqual(len(row), 10)
                self.assertIn("num", row[6].classes)
                self.assertNotIn("num", row[7].classes)

    def test_the_cells_of_a_number_and_a_boolean(self) -> None:
        """Scenario: Number and boolean columns (the cells)."""
        rows = {r[0].text: r for r in self.directory().rows[1:]}
        cells = {name: [c.text for c in row[6:8]]
                 for name, row in rows.items()}
        self.assertEqual(
            cells["Ethyl (triphenylphosphoranylidene)acetate"],
            ["12.5 g", "No"])
        self.assertEqual(cells["Acetic acid"], ["2500 g", "No"])
        self.assertEqual(cells["Salicylic acid"], ["", "Yes"])
        self.assertEqual(cells["Methyl salicylate"], ["", ""])

    def test_every_cell_follows_the_registry(self) -> None:
        """Scenario: Number and boolean columns (every compound)."""
        registry = self.registry()
        names = {self.shown(key): key for key in registry}
        columns = [f for f in self.fields() if f.column]
        self.assertEqual([f.key for f in columns],
                         ["item_number", "chemical_class", "stock",
                          "in_house"])
        for row in self.directory().rows[1:]:
            compound = registry[names[row[0].text]]
            texts = {f.key: text for f, text in fs.shown(
                columns, compound, "en", page=False)}
            with self.subTest(compound=row[0].text):
                self.assertEqual([c.text for c in row[4:8]],
                                 [texts.get(f.key, "") for f in columns])


class MarkupFieldTests(CompoundCase):
    """The test collection in English, with markup characters in the
    label and in a value of `short_name`."""

    LABEL = "Name <b>&</b>"
    VALUE = "<i>Me</i>2CO & co"

    @classmethod
    def prepare(cls) -> None:
        settings = cls.sandbox.root / "orgsyndb.toml"
        text = settings.read_text(encoding="utf-8")
        assert text.count('label = "Short name"') == 1
        settings.write_text(text.replace(
            'label = "Short name"', f'label = "{cls.LABEL}"'),
            encoding="utf-8")
        acetone = cls.sandbox.root / "compounds" / "acetone.toml"
        text = acetone.read_text(encoding="utf-8")
        assert "short_name" not in text
        acetone.write_text(text + f'short_name = "{cls.VALUE}"\n',
                           encoding="utf-8")

    def test_markup_in_a_label_or_a_value_is_text(self) -> None:
        """Scenario: Markup in a label or a value is text."""
        page = self.compound_page("acetone")
        facts = page.find("main").find("dl", "compound-facts")
        pairs = {p.label: p for p in page.definition_pairs(facts)}
        self.assertIn(self.LABEL, pairs, sorted(pairs))
        self.assertEqual(pairs[self.LABEL].term.text(), self.LABEL)
        self.assertEqual(pairs[self.LABEL].definition.text().strip(),
                         self.VALUE)
        self.assertEqual(facts.find_all("b"), [])
        self.assertEqual(facts.find_all("i"), [])


class NoFieldsTests(CompoundCase):
    """The test collection in English, with an `orgsyndb.toml` that
    declares no field. Its compounds keep the keys, which the validator
    reports as warnings and the build tolerates."""

    @classmethod
    def prepare(cls) -> None:
        (cls.sandbox.root / "orgsyndb.toml").write_text(
            "format = 1\n", encoding="utf-8")

    def test_the_field_data_is_empty(self) -> None:
        """Scenario: No settings file (the staged data)."""
        path = self.sandbox.root / "build" / "data" / "fields.json"
        self.assertTrue(path.is_file(), "build/data/fields.json is missing")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                         {"compound": []})

    def test_the_pages_show_the_built_in_facts_only(self) -> None:
        """Requirement: Compound pages (one pair for each field the
        collection declares)."""
        for key, compound in self.registry().items():
            page = self.compound_page(key)
            facts = page.find("main").find("dl", "compound-facts")
            with self.subTest(compound=key):
                self.assertEqual(
                    [p.label for p in page.definition_pairs(facts)],
                    [label for label in FACT_LABELS
                     if label != "CAS" or compound.get("cas")])

    def test_the_directory_has_no_declared_column(self) -> None:
        """Requirement: Compound directory (a column for each column
        field)."""
        page = ps.load_page(self.public, self.public / "compounds"
                            / "index.html")
        table = page.find("table", "compound-table")
        model = next(m for m in page.tables() if m.node is table)
        self.assertEqual([c.text for c in model.rows[0]],
                         ["Compound", "Formula", "MW", "CAS", "Made by",
                          "Used in"])
        for row in model.rows[1:]:
            self.assertEqual(len(row), 6)


class FallbackNameTests(CompoundCase):
    """The test collection in German, with one German name removed."""

    LOCALE = "de"

    @classmethod
    def prepare(cls) -> None:
        path = cls.sandbox.root / "compounds" / "acetone.toml"
        text = path.read_text(encoding="utf-8")
        kept = [ln for ln in text.splitlines()
                if not ln.startswith("name_de")]
        assert len(kept) == len(text.splitlines()) - 1, "no name_de line"
        path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    def test_a_compound_without_a_german_name(self) -> None:
        """Scenario: A compound without a German name."""
        page = self.compound_page("acetone")
        name = self.registry()["acetone"]["name"]
        self.assertEqual(name, "Acetone")
        self.assertEqual(page.find("main").find("h1").norm(), name)
        self.assertEqual(page.title(), f"{name} | OrgSynDB")
        procedure = ps.load_page(self.public, self.public / "procedures"
                                 / "osdb-0006" / "index.html")
        materials = next(p for p in procedure.definition_pairs(
            procedure.find("dl", "metadata")) if p.label == "Ausgangsstoffe")
        self.assertEqual([l.norm() for l in materials.definition.find_all(
            "a")], ["Benzaldehyd", "Acetone"])


class MarkupNameTests(CompoundCase):
    """The test collection in English, with a compound whose name holds
    an apostrophe and an ampersand."""

    NAME = "N,N'-Dimethylurea & co"

    @classmethod
    def prepare(cls) -> None:
        (cls.sandbox.root / "compounds" / "dimethylurea.toml").write_text(
            f'name = "{cls.NAME}"\nformula = "C3H8N2O"\nmw = 88.11\n'
            'smiles = "CNC(=O)NC"\nitem_number = "CH-0099"\n'
            'chemical_class = ["ketones"]\n', encoding="utf-8")

    def test_a_name_is_escaped_once(self) -> None:
        """Scenario: A page per compound (a name with markup characters)."""
        page = self.compound_page("dimethylurea")
        self.assertEqual(page.find("main").find("h1").norm(), self.NAME)
        self.assertEqual(page.title(), f"{self.NAME} | OrgSynDB")
        directory = ps.load_page(self.public, self.public / "compounds"
                                 / "index.html")
        self.assertIn(self.NAME, [l.node.norm() for l in directory.links()
                                  if l.target == "/compounds/dimethylurea/"])


if __name__ == "__main__":
    import unittest
    unittest.main()
