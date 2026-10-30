"""Shared checks of the pages of synthesis sequences (synthesis-sequences
"Sequence pages" and "Sequences beside procedures and compounds"), stated
once for both interface languages.

The functions take the test case, so that a failure reports through it.
What a page must show is computed from the content files, independently
of the theme.
"""

import math
import re
import unittest
from fractions import Fraction
from typing import Any, NamedTuple

import pipeline_support as ps
from pipeline_support import Content, Node, Page, Sequence

TEXTS: dict[str, dict[str, Any]] = {
    "en": {
        "steps": "Steps", "yield": "Overall yield", "step": "Step {k}",
        "entry": "entry {n}", "structure_of": "Structure of {name}",
        "heading": "Sequences", "title": "Sequences",
        "columns": ["Sequence", "Target", "Steps", "Overall yield"],
        "status": {"draft": "draft", "checked": "checked",
                   "retired": "retired"},
    },
    "de": {
        "steps": "Stufen", "yield": "Gesamtausbeute", "step": "Stufe {k}",
        "entry": "Eintrag {n}", "structure_of": "Strukturformel von {name}",
        "heading": "Synthesewege", "title": "Synthesewege",
        "columns": ["Syntheseweg", "Zielverbindung", "Stufen",
                    "Gesamtausbeute"],
        "status": {"draft": "Entwurf", "checked": "Geprüft",
                   "retired": "Zurückgezogen"},
    },
}


class StepFacts(NamedTuple):
    """One step of a sequence, read from its procedure."""

    item: Content
    entry: int | None
    substrates: list[str]
    products: list[dict[str, Any]]
    carried: str
    yield_percent: int | float


def run_of(item: Content, step: dict[str, Any]
           ) -> tuple[list[str], list[dict[str, Any]]]:
    """The substrates and products of the run a step names: those of the
    procedure, or of the entry of a general procedure."""
    if item.is_general:
        entry = item.scope[step["entry"] - 1]
        return list(entry["substrates"]), list(entry["products"])
    return item.substrates, item.products


def step_facts(sequence: Sequence, by_id: dict[str, Content]
               ) -> list[StepFacts]:
    """The steps of ``sequence`` with the compound that carries on from
    each: the first product, in order, among the next step's substrates,
    and for the last step the target."""
    runs = [run_of(by_id[step["procedure"]], step)
            for step in sequence.steps]
    found = []
    for index, step in enumerate(sequence.steps):
        substrates, products = runs[index]
        if index + 1 < len(runs):
            following = runs[index + 1][0]
            carried = next(p["compound"] for p in products
                           if p["compound"] in following)
        else:
            carried = sequence.target
        made = next(p for p in products if p["compound"] == carried)
        found.append(StepFacts(by_id[step["procedure"]], step.get("entry"),
                               substrates, products, carried,
                               made["yield_percent"]))
    return found


def overall_yield(facts: list[StepFacts]) -> int:
    """The product of the steps' yields as a whole percentage, halves
    up."""
    total = Fraction(100)
    for fact in facts:
        total *= Fraction(str(fact.yield_percent)) / 100
    return math.floor(total + Fraction(1, 2))


def sequences_of(item: Content, sequences: list[Sequence]
                 ) -> list[Sequence]:
    """The sequences that have the procedure ``item`` as a step, by
    ID."""
    return sorted((s for s in sequences
                   if item.id in [step["procedure"] for step in s.steps]),
                  key=lambda s: s.id)


def sequences_making(key: str, sequences: list[Sequence]
                     ) -> list[Sequence]:
    """The sequences whose target is the compound ``key``, by ID."""
    return sorted((s for s in sequences if s.target == key),
                  key=lambda s: s.id)


def check_sequence_page(case: unittest.TestCase, page: Page,
                        sequence: Sequence, by_id: dict[str, Content],
                        registry: dict[str, dict[str, Any]],
                        labels: dict[str, str], locale: str) -> None:
    """The page of ``sequence``: its parts in order, header, key facts,
    scheme, steps and body."""
    texts = TEXTS[locale]
    facts = step_facts(sequence, by_id)
    main = page.find("main")
    case.assertEqual(page.title(), f"{sequence.title} | OrgSynDB")
    header = main.find("header", "sequence-header")
    figure = main.find("figure", "sequence-scheme")
    steps = main.find("ol", "sequence-steps")
    for name, node in (("header.sequence-header", header),
                       ("figure.sequence-scheme", figure),
                       ("ol.sequence-steps", steps)):
        case.assertIsNotNone(node, f"no {name}")
    order = [page.index_of(n) for n in (header, figure, steps)]
    case.assertEqual(order, sorted(order), "parts out of order")
    case.assertEqual(len(page.find_all("p", "sequence-id")), 1)
    identity = header.find("p", "sequence-id")
    case.assertIsNotNone(identity, "no p.sequence-id")
    case.assertEqual(identity.norm(), sequence.id)
    case.assertEqual([h.norm() for h in main.find_all("h1")],
                     [sequence.title])
    case.assertTrue(header.find("h1") is not None, "the h1 is not in "
                    "the header")
    check_key_facts(case, page, header, facts, texts)
    check_scheme(case, page, figure, facts, registry, labels, locale)
    check_steps(case, page, steps, facts, registry, labels, locale)
    check_body(case, page, sequence, steps)
    case.assertEqual(page.find_all(data_pagefind_body=True), [],
                     "a sequence page is not indexed")


def check_key_facts(case: unittest.TestCase, page: Page, header: Node,
                    facts: list[StepFacts], texts: dict[str, Any]) -> None:
    key = header.find("dl", "key-facts")
    case.assertIsNotNone(key, "no dl.key-facts")
    case.assertEqual(
        [(p.label, p.definition.norm())
         for p in page.definition_pairs(key)],
        [(texts["steps"], str(len(facts))),
         (texts["yield"], f"{overall_yield(facts)} %")])


def check_scheme(case: unittest.TestCase, page: Page, figure: Node,
                 facts: list[StepFacts],
                 registry: dict[str, dict[str, Any]],
                 labels: dict[str, str], locale: str) -> None:
    """The scheme: an ``ol`` of the first step's substrates, then for
    each step the step and the compound that carries on."""
    texts = TEXTS[locale]
    lists = figure.find_all("ol")
    case.assertEqual(len(lists), 1, "not one ol in the scheme")
    items = [n for n in lists[0].elements() if n.tag == "li"]
    wanted: list[tuple[str, Any]] = [("compound", key)
                                     for key in facts[0].substrates]
    for number, fact in enumerate(facts, 1):
        wanted += [("step", number), ("compound", fact.carried)]
    case.assertEqual(len(items), len(wanted), "the scheme's item count")
    for item, (kind, what) in zip(items, wanted):
        with case.subTest(item=what):
            case.assertTrue(item.has_class(f"sequence-{kind}"), item.classes)
            if kind == "compound":
                check_compound_item(case, page, item, what, registry,
                                    locale)
            else:
                fact = facts[what - 1]
                parts = [texts["step"].format(k=what),
                         labels[fact.item.data["reaction_types"][0]],
                         f"{ps.number_text(fact.yield_percent, locale)} %"]
                text = item.norm()
                places = [text.find(part) for part in parts]
                case.assertNotIn(-1, places, f"{parts} in {text!r}")
                case.assertEqual(places, sorted(places), text)


def check_compound_item(case: unittest.TestCase, page: Page, item: Node,
                        key: str, registry: dict[str, dict[str, Any]],
                        locale: str) -> None:
    compound = registry[key]
    name = ps.shown_name(compound, locale)
    links = item.find_all("a", "compound")
    case.assertEqual(len(links), 1, "not one a.compound")
    case.assertEqual(page.resolve(links[0].attrs.get("href", "")),
                     f"/compounds/{key}/")
    case.assertEqual(links[0].norm(), name)
    images = item.find_all("img")
    if compound.get("structure_image"):
        case.assertEqual(len(images), 1, f"no image of {key}")
        case.assertEqual(page.resolve(images[0].attrs.get("src", "")),
                         "/" + compound["structure_image"])
        case.assertEqual(images[0].attrs.get("alt"),
                         TEXTS[locale]["structure_of"].format(name=name))
        case.assertLess(page.index_of(images[0]), page.index_of(links[0]))
    else:
        case.assertEqual(images, [], f"an image of {key} without one")


def check_steps(case: unittest.TestCase, page: Page, steps: Node,
                facts: list[StepFacts],
                registry: dict[str, dict[str, Any]],
                labels: dict[str, str], locale: str) -> None:
    """``ol.sequence-steps``: one item per step."""
    texts = TEXTS[locale]
    items = [n for n in steps.elements() if n.tag == "li"]
    case.assertEqual(len(items), len(facts))
    for number, (item, fact) in enumerate(zip(items, facts), 1):
        with case.subTest(step=number):
            link = item.elements()[0]
            case.assertEqual(link.tag, "a")
            case.assertEqual(page.resolve(link.attrs.get("href", "")),
                             f"/procedures/{fact.item.slug}/")
            title = f"{fact.item.id} {fact.item.title}"
            case.assertEqual(link.norm(), title)
            badge = item.find("span", "badge")
            case.assertIsNotNone(badge, "no status badge")
            status = fact.item.data["status"]
            case.assertIn(f"badge--{status}", badge.classes)
            case.assertEqual(badge.norm(), texts["status"][status])
            text = title
            if fact.item.is_general:
                text += " · " + texts["entry"].format(n=fact.entry)
            text += (f" · {labels[fact.item.data['reaction_types'][0]]}"
                     f" · {ps.number_text(fact.yield_percent, locale)} %"
                     f" · {badge.norm()}")
            case.assertEqual(item.norm(), text)


def check_body(case: unittest.TestCase, page: Page, sequence: Sequence,
               steps: Node) -> None:
    """The rendered body follows the steps: its headings and its text."""
    main = page.find("main")
    headings = re.findall(r"(?m)^## (.+)$", sequence.body)
    case.assertTrue(headings, "the sequence has no body heading")
    for heading in headings:
        node = page.heading(heading.strip())
        case.assertIsNotNone(node, f"no h2 {heading!r}")
        case.assertGreater(page.index_of(node), page.index_of(steps))
    words = " ".join(line for line in sequence.body.splitlines()
                     if line.strip() and not line.startswith("#"))
    text = main.norm()
    for word in words.split()[:4]:
        case.assertIn(word, text)


def check_panel_sequences(case: unittest.TestCase, page: Page,
                          item: Content, sequences: list[Sequence],
                          locale: str) -> None:
    """The ``Sequences`` pair of a procedure's panel: one ``a.sequence``
    per sequence that has the procedure as a step, by ID."""
    label = TEXTS[locale]["heading"]
    panel = page.find("dl", "metadata")
    pairs = {p.label: p for p in page.definition_pairs(panel)}
    wanted = sequences_of(item, sequences)
    if not wanted:
        case.assertNotIn(label, pairs)
        return
    case.assertIn(label, pairs)
    labels = list(pairs)
    case.assertEqual(labels[-1], label, "Sequences comes last")
    for earlier in ("Precursors", "Vorstufen", "Used in", "Verwendet in"):
        if earlier in labels:
            case.assertLess(labels.index(earlier), labels.index(label))
    links = pairs[label].definition.find_all("a", "sequence")
    case.assertEqual([(page.resolve(l.attrs.get("href", "")), l.norm())
                      for l in links],
                     [(f"/sequences/{s.slug}/", s.title) for s in wanted])
    case.assertEqual(len(page.links(pairs[label].definition)), len(links))
    case.assertNotEqual(pairs[label].gap, "")
    case.assertEqual(pairs[label].gap.strip(), "")


def check_compound_sequences(case: unittest.TestCase, page: Page,
                             key: str, sequences: list[Sequence],
                             locale: str) -> None:
    """``section.compound-sequences`` of a compound page, after its
    ``Used in`` section: only when some sequence makes the compound."""
    section = page.find("section", "compound-sequences")
    wanted = sequences_making(key, sequences)
    if not wanted:
        case.assertIsNone(section, f"a sequence section on {key}")
        return
    case.assertIsNotNone(section, f"no section.compound-sequences, {key}")
    case.assertEqual([h.norm() for h in section.find_all("h2")],
                     [TEXTS[locale]["heading"]])
    for other in ("compound-made-by", "compound-used-in"):
        before = page.find("section", other)
        if before is not None:
            case.assertLess(page.index_of(before), page.index_of(section))
    entries = section.find("ul").find_all("li")
    case.assertEqual(len(entries), len(wanted))
    for entry, sequence in zip(entries, wanted):
        links = page.links(entry)
        case.assertEqual([(l.target, l.node.norm()) for l in links],
                         [(f"/sequences/{sequence.slug}/", sequence.title)])
