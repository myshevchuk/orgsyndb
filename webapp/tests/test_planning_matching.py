"""Tests of the matching of tasks and articles (production-planning:
Matching tasks and articles)."""

from planning import plan

from . import make_task, page, substance_for
from .inventory_support import TODAY
from .planning_support import (PLAN, PlanningCase, article_links,
                               rows_by_article)


class ArticleTests(PlanningCase):

    def test_planning_works_on_articles(self) -> None:
        """All items of one article belong to one article, whatever the
        sizes."""
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

    def test_match_by_substance(self) -> None:
        """Scenario: Match by substance."""
        self.item("CH-0012", size="10", unit="umol", quantity=3)
        self.item("CH-0012", size="50", unit="umol", quantity=3)
        self.item("NV-0007", size="1", unit="mg", quantity=3,
                  substance=substance_for("new-compound-7",
                                          "New compound 7"))
        first = make_task(self.kl, substance="cinnamic-acid")
        second = make_task(self.kl, substance="new-compound-7")
        for task, wanted in ((first, ["CH-0012"]), (second, ["NV-0007"])):
            with self.subTest(task=task.substance.key):
                response = self.client.get(f"/lab/tasks/{task.number}/")
                links = article_links(page(response))
                self.assertEqual([a.text() for a in links], wanted)

    def test_a_task_matches_the_items_of_its_article_in_the_plan(
            self) -> None:
        for size in ("10", "50"):
            self.planned_item("CH-0012", size=size, unit="umol",
                              quantity=3)
        task = make_task(self.kl, substance="cinnamic-acid")
        make_task(self.kl, substance="Aspirin")
        root = self.get(PLAN + "?all=1")
        row = rows_by_article(root)["CH-0012"]
        listed = [a.get("href") for a in row["Aufgaben"].find_all("a")]
        self.assertEqual(listed, [f"/lab/tasks/{task.number}/"])

    def test_another_substance_matches_nothing(self) -> None:
        self.item("NV-7", size="1", unit="mg", quantity=3)
        task = make_task(self.kl, substance="Aspirin")
        response = self.client.get(f"/lab/tasks/{task.number}/")
        self.assertEqual(article_links(page(response)), [])

    def test_text_equal_to_an_article_number_matches_nothing(self) -> None:
        """A task names a substance, not text: the substance whose
        name is the article number of another substance's article is
        no match."""
        self.item("NV-7", size="1", unit="mg", quantity=3)
        task = make_task(self.kl, substance=substance_for(
            "namesake", "NV-7"))
        response = self.client.get(f"/lab/tasks/{task.number}/")
        self.assertEqual(article_links(page(response)), [])

    def test_a_position_without_an_article_number(self) -> None:
        """Scenario: A position without an article number."""
        self.item(None, "1-Phenylethanol", size="100", unit="mg",
                  quantity=8)
        task = make_task(self.kl, substance="1-Phenylethanol",
                         priority="low")
        self.assertNotIn("1-Phenylethanol",
                         page(self.client.get(PLAN + "?all=1"))
                         .find("main").text())
        self.assertFalse(plan.task_priority(task, TODAY).computed)
        response = self.client.get(f"/lab/tasks/{task.number}/")
        self.assertEqual(article_links(page(response)), [])
        self.assertIn("niedrig", page(response).text())

    def test_a_substance_without_an_article_matches_none(self) -> None:
        make_task(self.kl, substance="acetophenone")
        found = plan.Plan(TODAY)
        self.assertEqual(found.forecasts(), [])
