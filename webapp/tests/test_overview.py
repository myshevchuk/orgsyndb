"""Tests of the lab's overview at /lab/ and its summary at /lab/summary/
(lab-overview: Overview page, Summary for the home page; web-app: Paths
under /lab/, Page shell)."""

from datetime import date

from django.test import SimpleTestCase

from . import berlin, build_index, make_task, page, table, ticking
from .planning_support import PlanningCase

OVERVIEW = "/lab/"
SUMMARY = "/lab/summary/"
SEVENTH = date(2026, 11, 7)


def figures(root) -> dict:
    """The overview's figures, each ``dd`` by the text of its ``dt``;
    each pair sits in a ``div`` of the ``dl``."""
    return {pair.find("dt").text(): pair.find("dd")
            for pair in root.find("dl", "lab-figures").find_all("div")}


def section_of(root, heading: str):
    """The element that holds the ``h2`` HEADING and what follows it."""
    for h2 in root.find_all("h2"):
        if h2.text() == heading:
            return h2.parent
    raise AssertionError(f"no heading {heading!r}")


def entries(root, heading: str) -> list[str]:
    """The texts of the list under HEADING."""
    found = section_of(root, heading).find("ol")
    return [] if found is None else [li.text() for li in found.find_all("li")]


def bars(root) -> tuple[list, list]:
    """The chart's bars of the current months and of the year before."""
    svg = root.find("svg")
    current = [r for r in svg.find_all("rect") if "current" in r.classes]
    previous = [r for r in svg.find_all("rect") if "previous" in r.classes]
    return current, previous


def title_of(element) -> str:
    return element.find("title").text()


class OverviewCase(PlanningCase):

    def get(self, path: str = OVERVIEW, signed_in: bool = False):
        return super().get(path, signed_in)

    def at_the_seventh(self) -> None:
        """Let the clock stand at 2026-11-07."""
        self.enterContext(ticking(berlin(2026, 11, 7, 9)))


class StockBarTests(OverviewCase):

    def test_stock_bar(self) -> None:
        """Scenario: Stock bar."""
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        root = self.get()
        sections = root.find_all("section", "lab-overview")
        self.assertEqual(len(sections), 1)
        links = sections[0].find("div", "stock-bar").find_all("a")
        self.assertEqual([(sorted(c for c in a.classes
                                  if c.startswith("level-")), a.text())
                          for a in links],
                         [(["level-low"], "1"), (["level-ok"], "2")])
        self.assertEqual([a.get("href") for a in links], [
            "/lab/inventory/end-products/?stock=low",
            "/lab/inventory/end-products/?stock=ok"])
        self.assertEqual([a.get("title") for a in links],
                         ["niedrig: 1", "ausreichend: 2"])
        self.assertEqual([a.get("style") for a in links],
                         ["flex-grow: 1", "flex-grow: 2"])
        self.assertIsNone(root.find("script"))
        self.assertIn("3 Artikel", sections[0].text())

    def test_the_heading_and_the_order(self) -> None:
        self.item("A-1")
        root = self.get()
        self.assertEqual(root.find("h1").text(), "Labor auf einen Blick")
        section = root.find("section", "lab-overview")
        headings = [h.text() for h in section.find_all("h2")]
        self.assertEqual(headings, [
            "Bestand", "Nächste Synthesen", "Abgaben je Monat",
            "Meistgefragt 2026", "Empfänger 2026", "Letzte Lieferscheine"])
        order = [e for e in section.walk()
                 if e.tag in ("dl", "table", "svg")
                 or "stock-bar" in e.classes]
        self.assertTrue("stock-bar" in order[0].classes)
        self.assertEqual(order[1].tag, "dl")


class FigureTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def scenario(self) -> None:
        from inventory.bookings import reverse
        from inventory.models import Movement
        zimt = self.item("CH-0012", "(E)-Zimtsäure", quantity=40)
        aspirin = self.item("CH-0010", "Aspirin", quantity=40)
        self.deliver(zimt, 3, date(2026, 3, 2), recipient="AK Weber",
                     number="LS-1")
        self.deliver(aspirin, 2, date(2026, 10, 1), number="LS-2")
        self.deliver(zimt, 4, date(2025, 6, 1), number="LS-0")
        self.deliver(zimt, 5, date(2025, 12, 1), number="LS-00")
        note = self.deliver(aspirin, 6, date(2026, 10, 2), number="LS-3",
                            recipient="AK Weber")
        reverse(self.kl, Movement.objects.get(delivery_note=note),
                note="Falsch gebucht")
        make_task(self.kl, substance="CH-0012", started=SEVENTH)
        make_task(self.kl, substance="CH-0010")
        make_task(self.kl, substance="Aspirin")
        self.lot("CH-0012", "mg", "50")

    def test_figures_and_lists(self) -> None:
        """Scenario: Figures and lists."""
        self.scenario()
        root = self.get()
        shown = figures(root)
        self.assertEqual(list(shown), [
            "Abgegeben 2026", "Fällige Synthesen", "Aufgaben",
            "Offene Bulk-Lose"])
        delivered = shown["Abgegeben 2026"].text()
        self.assertTrue(delivered.startswith("5 "), delivered)
        self.assertIn("Vorjahr bis 07.11.2025: 4", delivered)
        self.assertIn("1 laufend · 2 geplant", shown["Aufgaben"].text())
        self.assertEqual(shown["Offene Bulk-Lose"].text(), "1")
        links = {term: value.find("a").get("href")
                 for term, value in shown.items() if value.find("a")}
        self.assertEqual(links, {
            "Fällige Synthesen": "/lab/planning/",
            "Aufgaben": "/lab/tasks/",
            "Offene Bulk-Lose": "/lab/inventory/end-products/bulk/"})
        requested = entries(root, "Meistgefragt 2026")
        self.assertEqual(len(requested), 2)
        self.assertTrue(requested[0].startswith("CH-0012"), requested)
        self.assertTrue(requested[0].endswith(" 3"), requested[0])
        self.assertTrue(requested[1].startswith("CH-0010"))
        self.assertTrue(requested[1].endswith(" 2"), requested[1])
        self.assertEqual(entries(root, "Empfänger 2026"), ["AK Weber 3"])
        latest = entries(root, "Letzte Lieferscheine")
        self.assertEqual([text.split()[0] for text in latest],
                         ["LS-3", "LS-2", "LS-1", "LS-00", "LS-0"])
        self.assertIn("02.10.2026", latest[0])

    def test_open_lots_of_any_substance(self) -> None:
        self.item("CH-0012", quantity=5)
        self.lot("CH-0012", "mg", "50")
        self.lot("acetophenone", "mg", "5", source="made")
        self.lot("CH-0012", "mg", "20", source="bought", supplier="Sigma")
        self.lot("acetophenone", "mg", "0")
        shown = figures(self.get())
        self.assertEqual(shown["Offene Bulk-Lose"].text(), "3")

    def test_names_come_from_the_substances_of_the_articles(self) -> None:
        zimt = self.item("CH-0012", quantity=40)
        self.deliver(zimt, 3, date(2026, 3, 2), number="LS-1")
        requested = entries(self.get(), "Meistgefragt 2026")
        self.assertEqual(len(requested), 1)
        self.assertIn("CH-0012", requested[0])
        self.assertIn("(E)-Zimtsäure", requested[0])
        self.use_index(build_index("en"))
        requested = entries(self.get(), "Most requested in 2026")
        self.assertIn("(E)-Cinnamic acid", requested[0])

    def test_the_latest_notes_link_their_pages(self) -> None:
        self.scenario()
        from inventory.models import DeliveryNote
        links = section_of(self.get(), "Letzte Lieferscheine").find(
            "ol").find_all("a")
        self.assertEqual(links[0].get("href"),
                         f"/lab/inventory/deliveries/"
                         f"{DeliveryNote.objects.get(number='LS-3').pk}/")

    def test_a_note_without_number(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = self.deliver(item, 1, date(2026, 11, 2), number=None)
        link = section_of(self.get(), "Letzte Lieferscheine").find(
            "ol").find("a")
        self.assertEqual(link.text(), "–")
        self.assertEqual(link.get("href"),
                         f"/lab/inventory/deliveries/{note.pk}/")

    def test_historical_notes_count(self) -> None:
        from inventory.bookings import book_note
        item = self.item("CH-0012", quantity=5)
        book_note(self.kl, date=date(2026, 2, 1), lines=[(item, 7)],
                  historical=True)
        self.assertTrue(figures(self.get())["Abgegeben 2026"].text()
                        .startswith("7 "))

    def test_five_entries_at_most(self) -> None:
        for number in range(7):
            item = self.item(f"A-{number}", quantity=20)
            self.deliver(item, number + 1, date(2026, 5, 1),
                         recipient=f"Empfänger {number}")
        root = self.get()
        for heading in ("Meistgefragt 2026", "Empfänger 2026",
                        "Letzte Lieferscheine"):
            with self.subTest(heading=heading):
                self.assertEqual(len(entries(root, heading)), 5)
        self.assertTrue(entries(root, "Meistgefragt 2026")[0]
                        .startswith("A-6"),
                        entries(root, "Meistgefragt 2026"))
        self.assertEqual(entries(root, "Empfänger 2026")[0],
                         "Empfänger 6 7")


class LeapDayTests(OverviewCase):

    def test_the_last_years_span_ends_on_the_28th(self) -> None:
        self.enterContext(ticking(berlin(2028, 2, 29, 9)))
        item = self.item("CH-0012", quantity=20)
        self.deliver(item, 2, date(2027, 2, 28))
        self.deliver(item, 3, date(2027, 3, 1))
        text = figures(self.get())["Abgegeben 2028"].text()
        self.assertIn("Vorjahr bis 28.02.2027: 2", text)


class ChartTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def test_deliveries_per_month(self) -> None:
        """Scenario: Deliveries per month."""
        item = self.item("CH-0012", quantity=20)
        self.deliver(item, 3, date(2026, 3, 2))
        self.deliver(item, 4, date(2025, 3, 15))
        current, previous = bars(self.get())
        self.assertEqual(len(current), 12)
        self.assertEqual(len(previous), 12)
        self.assertEqual(title_of(current[0]), "Dezember 2025: 0")
        self.assertEqual(title_of(previous[0]), "Dezember 2024: 0")
        self.assertEqual(title_of(current[3]), "März 2026: 3")
        self.assertEqual(title_of(previous[3]), "März 2025: 4")
        self.assertEqual(title_of(current[-1]), "November 2026: 0")
        heights = [float(r.get("height")) for r in current]
        self.assertGreater(heights[3], 0)
        self.assertEqual(heights[:3], [0.0] * 3)

    def test_each_month_is_labelled(self) -> None:
        self.item("A-1")
        svg = self.get().find("svg")
        labels = [t.text() for t in svg.find_all("text")]
        self.assertEqual(len(labels), 12)
        self.assertEqual(labels[0], "Dez")


class NextSynthesesTests(OverviewCase):

    def test_next_syntheses(self) -> None:
        """Scenario: Next syntheses."""
        from planning.plan import Plan
        from tasks.models import Priority
        for number, quantity in enumerate((0, 30, 2, 50, 8, 4, 16), 1):
            self.planned_item(f"NV-{number}", quantity=quantity)
        task = self.running("NV-1", 1)
        root = self.get()
        header, rows = table(section_of(root, "Nächste Synthesen"))
        self.assertEqual(header, ["Artikelnr.", "Name", "Priorität",
                                  "Spätester Start", "Aufgabe"])
        plan = Plan(date(2026, 11, 4))
        wanted = [found.article_number for found in sorted(
            plan.forecasts(),
            key=lambda found: (found.slack, found.article_number))][:5]
        self.assertEqual([row["Artikelnr."].text() for row in rows],
                         wanted)
        self.assertEqual(wanted[0], "NV-1")
        first = rows[0]["Aufgabe"]
        self.assertEqual(first.find("a").get("href"),
                         f"/lab/tasks/{task.number}/")
        self.assertIn("verspätet", first.text())
        self.assertEqual(rows[1]["Aufgabe"].text(), "–")
        due = sum(found.priority in (Priority.HIGH, Priority.MEDIUM)
                  for found in plan.forecasts())
        value = figures(root)["Fällige Synthesen"].text()
        self.assertTrue(value.startswith(f"{due} "), value)
        self.assertIn("1 verspätet", value)
        self.assertEqual(section_of(root, "Nächste Synthesen").find(
            "a", href="/lab/planning/").text(), "Zur Planung")

    def test_the_name_is_the_substances(self) -> None:
        self.planned_item("NV-1", quantity=0, name="Erste")
        _, rows = table(section_of(self.get(), "Nächste Synthesen"))
        self.assertEqual(rows[0]["Name"].text(), "Erste")
        self.assertEqual([a.get("href") for a in rows[0]["Name"].find_all(
            "a")], ["/lab/registry/substances/nv-1/"])

    def test_the_article_links_its_first_item(self) -> None:
        self.planned_item("NV-1", size="5", quantity=0)
        first = self.planned_item("NV-1", size="1", quantity=0)
        _, rows = table(section_of(self.get(), "Nächste Synthesen"))
        self.assertEqual(rows[0]["Artikelnr."].find("a").get("href"),
                         f"/lab/inventory/items/{first.pk}/")


class EmptyTests(OverviewCase):

    def test_an_empty_lab(self) -> None:
        """Scenario: An empty lab."""
        root = self.get()
        self.assertEqual(root.find("div", "stock-bar").find_all("a"), [])
        for term, value in figures(root).items():
            with self.subTest(term=term):
                self.assertTrue(value.text().startswith("0"), value.text())
        self.assertIn("Keine Prognosen.",
                      section_of(root, "Nächste Synthesen").text())
        self.assertIsNone(section_of(root, "Nächste Synthesen")
                          .find("table"))
        current, previous = bars(root)
        self.assertEqual(len(current), 12)
        self.assertEqual(len(previous), 12)
        self.assertTrue(all(float(r.get("height")) == 0
                            for r in current + previous))
        for heading in ("Meistgefragt 2026", "Empfänger 2026",
                        "Letzte Lieferscheine"):
            with self.subTest(heading=heading):
                self.assertIn("Keine Abgaben.",
                              section_of(root, heading).text())


class EnglishTests(OverviewCase):

    def test_overview_in_english(self) -> None:
        """Scenario: Overview in English."""
        self.use_index(build_index("en"))
        root = self.get()
        self.assertEqual(root.find("h1").text(), "Lab at a glance")
        headings = [h.text() for h in root.find_all("h2")]
        for heading in ("Inventory", "Next syntheses",
                        "Deliveries per month", "Latest delivery notes"):
            with self.subTest(heading=heading):
                self.assertIn(heading, headings)


class SummaryTests(OverviewCase):

    def test_summary(self) -> None:
        """Scenario: Summary."""
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        make_task(self.kl, substance="OK-1", started=date(2026, 11, 1))
        self.lot("OK-1", "mg", "50")
        response = self.client.get(SUMMARY)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        sections = root.find_all("section", "lab-summary")
        self.assertEqual(len(sections), 1)
        links = sections[0].find("div", "stock-bar").find_all("a")
        self.assertEqual([a.text() for a in links], ["1", "2"])
        self.assertEqual(len(figures(root)), 4)
        self.assertEqual(sections[0].find("a", href="/lab/").text(),
                         "Zur Übersicht")
        self.assertIsNone(root.find("section", "lab-overview"))
        self.assertIsNone(root.find("table"))
        self.assertIsNone(root.find("svg"))
        heading = root.find("h1")
        self.assertEqual(heading.text(), "Labor auf einen Blick")
        self.assertIn("visually-hidden", heading.classes)

    def test_a_summary_to_frame(self) -> None:
        """Scenario: A summary to frame."""
        summary = self.client.get(SUMMARY)
        tasks = self.client.get("/lab/tasks/")
        self.assertEqual(summary["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(tasks["X-Frame-Options"], "DENY")
        root, shell = page(summary), page(tasks)

        def sheets(found):
            return [e.get("href") for e in found.find_all("link")
                    if e.get("rel") == "stylesheet"]

        self.assertEqual(sheets(root), sheets(shell))
        self.assertEqual(len(sheets(root)), 5)
        self.assertEqual(root.find("base").get("target"), "_top")
        self.assertIsNone(root.find("header"))
        self.assertIsNone(root.find("nav"))
        self.assertIsNone(root.find("script"))
        self.assertNotIn("<script", summary.content.decode().lower())

    def test_the_demo_note(self) -> None:
        from demo.models import DemoMark
        DemoMark.objects.create(seeded_on=date(2026, 11, 1))
        root = page(self.client.get(SUMMARY))
        self.assertIsNotNone(root.find("p", "lab-demo"))


class StylesheetTests(SimpleTestCase):

    def test_the_stock_bar_wraps(self) -> None:
        import re
        from .test_inventory_colours import CSS
        text = CSS.read_text(encoding="utf-8")
        rule = re.search(r"\.stock-bar \{([^}]*)\}", text)
        self.assertIsNotNone(rule)
        self.assertIn("flex-wrap: wrap", rule.group(1))


class PathTests(OverviewCase):

    def test_the_overview_is_the_entry(self) -> None:
        """Scenario: Entry and outside paths."""
        response = self.client.get(OVERVIEW)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(page(response).find("section", "lab-overview"))
        self.assertEqual(self.client.get("/procedures/").status_code, 404)

    def test_no_view_is_marked(self) -> None:
        nav = page(self.client.get(OVERVIEW)).find("header").find("nav")
        self.assertFalse([a for a in nav.find_all("a")
                          if a.get("aria-current")])


class SpanTests(SimpleTestCase):

    def test_the_same_day_a_year_before(self) -> None:
        from overview.figures import a_year_before
        self.assertEqual(a_year_before(date(2026, 11, 7)),
                         date(2025, 11, 7))
        self.assertEqual(a_year_before(date(2028, 2, 29)),
                         date(2027, 2, 28))

    def test_the_twelve_months(self) -> None:
        from overview.figures import months_ending
        months = months_ending(date(2026, 11, 7))
        self.assertEqual(months[0], (2025, 12))
        self.assertEqual(months[-1], (2026, 11))
        self.assertEqual(len(months), 12)
        self.assertEqual(months_ending(date(2026, 1, 31))[0], (2025, 2))
