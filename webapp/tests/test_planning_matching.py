"""Tests of the matching of tasks and articles (production-planning:
Matching tasks and articles)."""

from planning import plan

from . import build_index, make_task, page
from .inventory_support import TODAY
from .planning_support import PlanningCase, article_links


class MatchesTests(PlanningCase):
    """The demo collection names ``CH-0012`` and its key
    ``cinnamic-acid`` the same compound."""

    def test_equal_text_matches(self) -> None:
        self.assertTrue(plan.matches("NV-7", "NV-7"))
        self.assertFalse(plan.matches("NV-8", "NV-7"))

    def test_text_matches_regardless_of_case(self) -> None:
        self.assertTrue(plan.matches("nv-7", "NV-7"))
        self.assertTrue(plan.matches("NV-7", "nv-7"))
        self.assertTrue(plan.matches("Nv-7", "nV-7"))

    def test_the_same_compound_matches(self) -> None:
        """Scenario: Match by compound and by text."""
        self.assertTrue(plan.matches("cinnamic-acid", "CH-0012"))
        self.assertTrue(plan.matches("CH-0012", "cinnamic-acid"))
        self.assertTrue(plan.matches("CH-0012", "CH-0012"))

    def test_another_compound_does_not_match(self) -> None:
        self.assertFalse(plan.matches("CH-0011", "CH-0012"))
        self.assertFalse(plan.matches("benzaldehyde", "CH-0012"))

    def test_a_compound_does_not_match_a_text_that_names_none(self) -> None:
        self.assertFalse(plan.matches("CH-0012", "NV-7"))
        self.assertFalse(plan.matches("NV-7", "CH-0012"))
        self.assertFalse(plan.matches("cinnamic-acid", "NV-7"))

    def test_the_compound_is_found_as_the_index_finds_it(self) -> None:
        """Only equal text is compared regardless of case; a compound is
        found by ``compound_for``, which takes keys and values as they
        are."""
        self.assertFalse(plan.matches("CINNAMIC-ACID", "CH-0012"))

    def test_an_unknown_text_matches_nothing_else(self) -> None:
        self.assertFalse(plan.matches("Aspirin", "CH-0012"))
        self.assertFalse(plan.matches("Aspirin", "NV-7"))

    def test_the_index_decides(self) -> None:
        self.use_index(build_index("de"))
        self.assertFalse(plan.matches("cinnamic-acid", "CH-0012"))
        self.assertTrue(plan.matches("CH-0012", "ch-0012"))


class ArticleTests(PlanningCase):

    def test_planning_works_on_articles(self) -> None:
        """All items with one article number belong to one article."""
        large = self.item("CH-0012", size="50", unit="umol", quantity=3)
        small = self.item("CH-0012", size="10", unit="umol", quantity=3)
        other = self.item("NV-7", size="1", unit="mg", quantity=3)
        for item in (small, large, other):
            self.enter(item, 2026, 1, 9)
        found = plan.article("CH-0012", TODAY)
        self.assertEqual([entry.item.pk for entry in found.items],
                         [small.pk, large.pk])
        self.assertEqual(
            [entry.item.pk for entry in plan.article("NV-7", TODAY).items],
            [other.pk])

    def test_the_task_of_a_compound_matches_the_article_and_its_items(
            self) -> None:
        """Scenario: Match by compound and by text."""
        self.item("CH-0012", size="10", unit="umol", quantity=3)
        self.item("CH-0012", size="50", unit="umol", quantity=3)
        self.item("NV-7", size="1", unit="mg", quantity=3)
        first = make_task(self.kl, product="cinnamic-acid")
        second = make_task(self.kl, product="nv-7")
        for task, wanted in ((first, ["CH-0012"]), (second, ["NV-7"])):
            with self.subTest(task=task.product):
                response = self.client.get(f"/lab/tasks/{task.number}/")
                links = article_links(page(response))
                self.assertEqual([a.text() for a in links], wanted)
