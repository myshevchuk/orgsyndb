"""Tests of the route trees the lab draws (synthesis-routes: Routes in
the lab, by the rules of Derived routes)."""

from typing import Any

from django.test import SimpleTestCase, TestCase

from collection import routes
from collection.models import Procedure
from vocabulary.models import ReactionType

from . import make_substance
from .collection_support import (make_entry, make_entry_substance,
                                 make_import, make_procedure)
from .demo_support import SeededCase


def leaf(key: str, more: bool = False) -> dict[str, Any]:
    """A substance of a step that is not expanded."""
    return {"compound": key, "steps": [], "more": more}


def step(procedure: str, yield_percent: Any, *substrates: dict[str, Any],
         entry: int | None = None) -> dict[str, Any]:
    """A step of a route tree, as Derived routes writes it."""
    found: dict[str, Any] = {"procedure": procedure}
    if entry is not None:
        found["entry"] = entry
    return found | {"yield_percent": yield_percent,
                    "substrates": list(substrates)}


def below(key: str, *steps: dict[str, Any]) -> dict[str, Any]:
    """A substance of a step, expanded with STEPS."""
    return {"compound": key, "steps": list(steps), "more": False}


class Collection:
    """Procedure rows of one accepted import, made one at a time."""

    def __init__(self) -> None:
        ReactionType.objects.get_or_create(key="acylation",
                                           defaults={"label": "Acylation"})
        self.received = make_import()

    def add(self, key: str, *entries: tuple[list[str], list[tuple]],
            general: bool = False, **fields: Any) -> Procedure:
        """The procedure KEY with ENTRIES, each a pair of its substrates'
        keys and its products, pairs of a key and a yield, in order."""
        procedure = make_procedure(self.received, key, general=general,
                                   **fields)
        for position, (substrates, products) in enumerate(entries, 1):
            entry = make_entry(procedure, f"{key} {position}", position)
            for index, substrate in enumerate(substrates, 1):
                make_substance(substrate)
                make_entry_substance(entry, substrate, "substrate", index)
            for index, (product, made) in enumerate(products, 1):
                make_substance(product)
                make_entry_substance(entry, product, "product", index,
                                     yield_percent=made)
        return procedure


class DemoRoutesTests(SeededCase):
    """Scenario: Routes of the demo data; Withdrawn procedures leave the
    tree."""

    def trees(self) -> dict[str, list[dict[str, Any]]]:
        from registry.models import Substance
        made = routes.steps()
        drawn = {key: routes.route_tree(key, made)
                 for key in Substance.objects.values_list("key", flat=True)}
        return {key: tree for key, tree in drawn.items() if tree}

    def test_the_substances_with_a_tree(self) -> None:
        self.assertEqual(sorted(self.trees()), [
            "1-biphenyl-4-yl-ethanol", "acetylsalicylic-acid",
            "cinnamic-acid"])

    def test_the_tree_of_aspirin(self) -> None:
        self.assertEqual(self.trees()["acetylsalicylic-acid"], [
            step("OSDB-0002", 75.0,
                 below("salicylic-acid",
                       step("OSDB-0001", 80.0, leaf("methyl-salicylate"))),
                 leaf("acetic-anhydride"))])

    def test_two_steps_to_one_substance(self) -> None:
        inner = below("4-acetylbiphenyl", step(
            "OSDB-0004", 85.0, leaf("4-bromoacetophenone"),
            leaf("phenylboronic-acid")))
        self.assertEqual(self.trees()["1-biphenyl-4-yl-ethanol"], [
            step("OSDB-0005", 90.0, inner),
            step("OSDB-0009", 90.0, inner, entry=1)])

    def test_a_withdrawn_procedure_leaves_the_tree(self) -> None:
        Procedure.objects.filter(key="OSDB-0007").update(withdrawn=True)
        self.assertNotIn("cinnamic-acid", self.trees())

    def test_a_withdrawn_entry_leaves_the_tree(self) -> None:
        from collection.models import ScopeEntry
        ScopeEntry.objects.filter(procedure__key="OSDB-0007").update(
            withdrawn=True)
        self.assertNotIn("cinnamic-acid", self.trees())


class RowRoutesTests(TestCase):
    """The rules of Derived routes on the lab's rows."""

    def setUp(self) -> None:
        self.collection = Collection()

    def test_a_protection_and_its_removal(self) -> None:
        """Scenario: A protection and its removal in the lab."""
        add = self.collection.add
        add("OSDB-0001", (["a"], [("b", 90)]))
        add("OSDB-0002", (["b"], [("a", 90)]))
        add("OSDB-0003", (["b"], [("c", 90)]))
        made = routes.steps()
        self.assertEqual(routes.route_tree("a", made), [])
        self.assertEqual(routes.route_tree("b", made), [])
        self.assertEqual(routes.route_tree("c", made), [
            step("OSDB-0003", 90.0,
                 below("b", step("OSDB-0001", 90.0, leaf("a"))))])

    def test_the_budget(self) -> None:
        """Scenario: The budget in the lab."""
        self.collection.add("OSDB-0001", *[
            ([f"chain-{n - 1}"], [(f"chain-{n}", 80)]) for n in range(1, 8)],
            general=True)
        tree = routes.route_tree("chain-7", routes.steps())
        entries = []
        while tree:
            (only,) = tree
            entries.append(only["entry"])
            (substrate,) = only["substrates"]
            last, tree = substrate, substrate["steps"]
        self.assertEqual(entries, [7, 6, 5, 4, 3, 2])
        self.assertEqual(last, leaf("chain-1", more=True))

    def test_order_entries_and_a_step_from_nothing(self) -> None:
        """Derived routes: steps by procedure ID, a general procedure's
        entries in entry order, and a step that starts from nothing."""
        add = self.collection.add
        add("OSDB-0003", (["m"], [("t", 70)]))
        add("OSDB-0001", (["m"], [("t", 60)]), (["n"], [("t", 50)]),
            general=True)
        add("OSDB-0002", ([], [("m", 40)]))
        made = routes.steps()
        from_m = below("m", step("OSDB-0002", 40.0))
        self.assertEqual(routes.route_tree("t", made), [
            step("OSDB-0001", 60.0, from_m, entry=1),
            step("OSDB-0001", 50.0, leaf("n"), entry=2),
            step("OSDB-0003", 70.0, from_m)])
        self.assertEqual(routes.route_tree("m", made), [])

    def test_a_withdrawn_entry_of_a_kept_procedure_is_no_step(self) -> None:
        procedure = self.collection.add("OSDB-0001", (["a"], [("b", 90)]))
        self.collection.add("OSDB-0002", (["b"], [("c", 90)]))
        procedure.entries.update(withdrawn=True)
        self.assertEqual(routes.route_tree("c", routes.steps()), [])


def chain(length: int) -> dict[str, list[routes.Step]]:
    """The steps of a chain: OSDB-000<n> makes c<n> from c<n-1>."""
    return {f"c{n}": [routes.Step(f"OSDB-{n:04d}", None, 90.0,
                                  (f"c{n - 1}",))]
            for n in range(1, length + 1)}


class LimitTests(SimpleTestCase):
    """Derived routes: the depth limit and the step budget."""

    def test_the_depth_limit(self) -> None:
        made = chain(4)
        self.assertEqual(routes.route_tree("c4", made, depth=2), [
            step("OSDB-0004", 90.0, below(
                "c3", step("OSDB-0003", 90.0, leaf("c2", more=True))))])
        self.assertEqual(routes.route_tree("c2", made, depth=2), [
            step("OSDB-0002", 90.0, below(
                "c1", step("OSDB-0001", 90.0, leaf("c0"))))])
        for key in ("c2", "c3", "c4"):
            with self.subTest(key=key):
                (only,) = routes.route_tree(key, made, depth=1)
                self.assertEqual(only["substrates"],
                                 [leaf(f"c{int(key[1]) - 1}", more=True)])
        self.assertEqual(routes.route_tree("c1", made, depth=1), [])

    def test_the_step_budget(self) -> None:
        made = {"r": [routes.Step("OSDB-0001", None, 90.0, ("a", "b"))],
                "a": [routes.Step("OSDB-0002", None, 90.0, ("x",))],
                "b": [routes.Step("OSDB-0003", None, 90.0, ("y",))],
                "x": [routes.Step("OSDB-0004", None, 90.0, ("z",))]}
        x_full = below("x", step("OSDB-0004", 90.0, leaf("z")))
        self.assertEqual(routes.route_tree("r", made, budget=4), [
            step("OSDB-0001", 90.0,
                 below("a", step("OSDB-0002", 90.0, x_full)),
                 below("b", step("OSDB-0003", 90.0, leaf("y"))))])
        self.assertEqual(routes.route_tree("r", made, budget=3), [
            step("OSDB-0001", 90.0,
                 below("a", step("OSDB-0002", 90.0, leaf("x", more=True))),
                 below("b", step("OSDB-0003", 90.0, leaf("y"))))])
        self.assertEqual(routes.route_tree("r", made, budget=0), [
            step("OSDB-0001", 90.0, leaf("a", more=True),
                 leaf("b", more=True))])
