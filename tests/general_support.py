"""Shared checks of the pages of general procedures (general-procedures
"Scope table on the page", site-theme "Structure image slot"), stated
once for both interface languages.

The functions take the test case, so that a failure reports through it.
"""

import unittest
from typing import Any

import pipeline_support as ps
from pipeline_support import Content, Node, Page

OPTIONAL_COLUMNS = ("scale", "time", "temperature", "note")

TEXTS: dict[str, dict[str, Any]] = {
    "en": {
        "heading": "Scope",
        "columns": ["Entry", "Starting materials", "Products", "Yield"],
        "optional": {"scale": "Scale", "time": "Time",
                     "temperature": "Temperature", "note": "Note"},
        "structure_of": "Structure of {name}",
        "scheme_of": "Scheme of {title}",
        "label_scale": "Scale", "label_yield": "Yield",
        "entry": "entry {n}",
    },
    "de": {
        "heading": "Anwendungsbereich",
        "columns": ["Eintrag", "Ausgangsstoffe", "Produkte", "Ausbeute"],
        "optional": {"scale": "Ansatzgröße", "time": "Zeit",
                     "temperature": "Temperatur", "note": "Anmerkung"},
        "structure_of": "Strukturformel von {name}",
        "scheme_of": "Schema von {title}",
        "label_scale": "Ansatzgröße", "label_yield": "Ausbeute",
        "entry": "Eintrag {n}",
    },
}


def scope_keys(item: Content) -> list[str]:
    """The optional keys that some entry of ``item`` sets, in the order
    of the table's columns."""
    return [key for key in OPTIONAL_COLUMNS
            if any(key in entry for entry in item.scope)]


def expected_header(item: Content, locale: str) -> list[str]:
    texts = TEXTS[locale]
    return texts["columns"] + [texts["optional"][key]
                               for key in scope_keys(item)]


def check_scope_table(case: unittest.TestCase, page: Page, item: Content,
                      registry: dict[str, dict], locale: str,
                      first_heading: str) -> Node:
    """The ``section.scope`` of the page of the general procedure
    ``item``: its place, its heading, its header cells and, for each
    entry, its cells. ``first_heading`` is the text of the body's first
    heading. Returns the table."""
    texts = TEXTS[locale]
    article = page.find("article", "procedure")
    case.assertIsNotNone(article, "no article.procedure")
    sections = article.find_all("section", "scope")
    case.assertEqual(len(sections), 1, "not one section.scope")
    section = sections[0]
    details = article.find("div", "procedure-details")
    case.assertIsNotNone(details, "no details wrapper")
    summary = page.heading(first_heading)
    case.assertIsNotNone(summary, f"no {first_heading} heading")
    order = [page.index_of(n) for n in (details, section, summary)]
    case.assertEqual(order, sorted(order),
                     "the scope lies between the details and the body")
    case.assertFalse(section.within(details))
    case.assertEqual([h.norm() for h in section.find_all("h2")],
                     [texts["heading"]])
    tables = section.find_all("table", "scope-table")
    case.assertEqual(len(tables), 1, "not one table.scope-table")
    table = tables[0]
    rows = table.find_all("tr")
    case.assertEqual(len(rows), 1 + len(item.scope))
    header = [c for c in rows[0].elements() if c.tag in ("td", "th")]
    case.assertEqual([c.norm() for c in header],
                     expected_header(item, locale))
    keys = scope_keys(item)
    for number, (row, entry) in enumerate(zip(rows[1:], item.scope), 1):
        cells = [c for c in row.elements() if c.tag in ("td", "th")]
        with case.subTest(entry=number):
            case.assertEqual(len(cells), len(header))
            check_scope_row(case, page, cells, entry, number, keys,
                            registry, locale)
    return table


def check_scope_row(case: unittest.TestCase, page: Page, cells: list[Node],
                    entry: dict[str, Any], number: int, keys: list[str],
                    registry: dict[str, dict], locale: str) -> None:
    texts = TEXTS[locale]
    case.assertEqual(cells[0].norm(), str(number))
    names = [ps.shown_name(registry[key], locale)
             for key in entry["substrates"]]
    links = page.links(cells[1])
    case.assertEqual([(l.target, l.node.norm()) for l in links],
                     [(f"/compounds/{key}/", name)
                      for key, name in zip(entry["substrates"], names)])
    for link in links:
        case.assertTrue(link.node.has_class("compound"))
    case.assertEqual(cells[1].norm(), ", ".join(names))
    expected: list[tuple[str, str]] = []
    product_names = []
    for product in entry["products"]:
        compound = registry[product["compound"]]
        name = ps.shown_name(compound, locale)
        product_names.append(name)
        if compound.get("structure_image"):
            expected.append(("img", "/" + compound["structure_image"]))
        expected.append(("a", f"/compounds/{product['compound']}/"))
    shown = []
    for node in cells[2].iter():
        if node.tag == "img":
            shown.append(("img", page.resolve(node.attrs.get("src", ""))))
            case.assertTrue(node.has_class("scope-structure"))
        elif node.tag == "a":
            shown.append(("a", page.resolve(node.attrs.get("href", ""))))
            case.assertTrue(node.has_class("compound"))
    case.assertEqual(shown, expected)
    for image in cells[2].find_all("img"):
        case.assertEqual((image.attrs.get("loading"),
                          image.attrs.get("decoding")), ("lazy", "async"))
    alts = [texts["structure_of"].format(name=name)
            for name, product in zip(product_names, entry["products"])
            if registry[product["compound"]].get("structure_image")]
    case.assertEqual([i.attrs.get("alt") for i in cells[2].find_all("img")],
                     alts)
    case.assertEqual([l.node.norm() for l in page.links(cells[2])],
                     product_names)
    case.assertEqual(cells[2].norm(), ", ".join(product_names))
    case.assertEqual(
        cells[3].norm(),
        ", ".join(f"{ps.number_text(p['yield_percent'], locale)} %"
                  for p in entry["products"]))
    for cell, key in zip(cells[4:], keys):
        value = entry.get(key)
        if key == "temperature" and value is not None:
            value = f"{ps.number_text(value, locale)} °C"
        case.assertEqual(cell.norm(), "" if value is None else value, key)


def check_scheme_figure(case: unittest.TestCase, page: Page, item: Content,
                        image: str, locale: str) -> None:
    """The header of ``item`` ends with one ``figure.structure`` holding
    the scheme image ``image``, with the alt text ``Scheme of <title>``."""
    header = page.find("header", "procedure-header")
    figures = header.find_all("figure", "structure")
    case.assertEqual(len(figures), 1)
    case.assertIs(header.elements()[-1], figures[0])
    case.assertFalse(figures[0].has_class("structure--placeholder"))
    images = figures[0].find_all("img")
    case.assertEqual(len(images), 1)
    case.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                     "/" + image)
    case.assertEqual(
        images[0].attrs.get("alt"),
        TEXTS[locale]["scheme_of"].format(title=item.title))
    case.assertEqual(page.find_all("figure", "structure--placeholder"), [])


def check_key_facts(case: unittest.TestCase, page: Page, item: Content,
                    registry: dict[str, dict], locale: str) -> None:
    """The key facts of a general procedure: its scale and the range of
    the yields of all its entries' products."""
    texts = TEXTS[locale]
    header = page.find("header", "procedure-header")
    facts = header.find("dl", "key-facts")
    case.assertIsNotNone(facts, "no dl.key-facts")
    case.assertEqual(
        [(p.label, p.definition.norm())
         for p in page.definition_pairs(facts)],
        [(texts["label_scale"], item.data["scale"]),
         (texts["label_yield"], ps.yield_text(item, registry, locale))])
