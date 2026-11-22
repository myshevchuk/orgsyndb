"""Tests of the lab's overview at /lab/ and its summary at /lab/summary/
(lab-overview: Overview page, Summary for the home page; web-app: Paths
under /lab/, Page shell, Widgets)."""

from datetime import date

from django.test import SimpleTestCase

from . import make_task, page, shell_scripts
from .collection_support import accept
from . import navigation_support as ns
from .inventory_support import historical_line
from .overview_support import (FIGURES, OVERVIEW, SEVENTH, SUMMARY,
                               WIDGET_TITLES, WIDGET_TITLES_EN,
                               OverviewCase, figure_values, figures,
                               hrefs, stock_widget)
from .widget_support import (tiles, title_of, widget, widget_grid,
                             widgets)


def bars(root) -> tuple[list, list]:
    """The chart's bars of the current months and of the year before."""
    svg = widget(root, "Abgaben je Monat", "Deliveries per month").find(
        "svg")
    current = [r for r in svg.find_all("rect") if "current" in r.classes]
    previous = [r for r in svg.find_all("rect") if "previous" in r.classes]
    return current, previous


def month_labels(root) -> list[str]:
    """The texts of the chart's month labels: its ``text`` elements
    that are not value labels."""
    svg = widget(root, "Abgaben je Monat", "Deliveries per month").find(
        "svg")
    return [t.text() for t in svg.find_all("text")
            if "chart-value" not in t.classes]


def value_labels(root) -> list:
    """The chart's value labels, ``text.chart-value``."""
    svg = widget(root, "Abgaben je Monat", "Deliveries per month").find(
        "svg")
    return svg.find_all("text", cls="chart-value")


def title_of_bar(element) -> str:
    return element.find("title").text()


def rows(root, title: str) -> list[dict]:
    """The body rows of the table of the widget titled TITLE, each
    as its cells by column header."""
    return widget_grid(widget(root, title))[1]


def texts(root, title: str, column: str) -> list[str]:
    """The text of each cell of COLUMN in the table of the widget
    titled TITLE."""
    return [row[column].text() for row in rows(root, title)]


class StockBarTests(OverviewCase):

    def test_stock_bar(self) -> None:
        """Scenario: Stock bar."""
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        root = self.get()
        sections = root.find_all("section", "lab-overview")
        self.assertEqual(len(sections), 1)
        found = stock_widget(root)
        self.assertEqual(len(root.find_all("div", "stock-bar")), 1)
        links = found.find("div", "stock-bar").find_all("a")
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
        shell_scripts(root)
        self.assertIn("3 Artikel", found.text())
        for label in ("niedrig", "ausreichend"):
            with self.subTest(label=label):
                self.assertIn(label, found.text())

    def test_the_heading_and_the_order(self) -> None:
        self.item("A-1")
        root = self.get()
        self.assertEqual(root.find("h1").text(), "Labor auf einen Blick")
        section = root.find("section", "lab-overview")
        self.assertEqual([title_of(w) for w in widgets(section)],
                         list(WIDGET_TITLES))
        order = [e for e in section.walk()
                 if "figures-strip" in e.classes or "widget" in e.classes]
        self.assertIn("figures-strip", order[0].classes)
        walked = list(root.walk())
        self.assertLess(walked.index(root.find("h1")),
                        walked.index(section))


class FigureTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def test_the_open_vessels_figure_in_english(self) -> None:
        """Requirement: Overview page (`Open vessels`)."""
        self.vessel("CH-0012", "mg", "50")
        accept(language="en")
        shown = figure_values(self.get())
        self.assertIn("Open vessels", shown)
        self.assertEqual(shown["Open vessels"], "1")
        self.assertNotIn("Open bulk lots", shown)

    def test_figures_and_lists(self) -> None:
        """Scenario: Figures and lists."""
        self.scenario()
        root = self.get()
        shown = figure_values(root)
        self.assertEqual(list(shown), list(FIGURES))
        delivered = shown["Abgegeben 2026"]
        self.assertRegex(delivered, r"^5(?!\d)")
        self.assertIn("Vorjahr bis 07.11.2025: 4", delivered)
        self.assertIn("1 laufend · 2 geplant", shown["Aufgaben"])
        self.assertEqual(shown["Offene Gefäße"], "1")
        links = {label: hrefs(each)[0]
                 for label, each in figures(root).items() if hrefs(each)}
        self.assertEqual(links, {
            "Fällige Synthesen": "/lab/planning/",
            "Aufgaben": "/lab/tasks/",
            "Offene Gefäße": "/lab/inventory/vessels/"})
        requested = rows(root, "Meistgefragt 2026")
        self.assertEqual([r["Artikelnr."].text() for r in requested],
                         ["CH-0012", "CH-0010"])
        self.assertEqual([r["Gebinde"].text() for r in requested],
                         ["3", "2"])
        self.assertEqual(
            [(r["Empfänger"].text(), r["Gebinde"].text())
             for r in rows(root, "Empfänger 2026")], [("AK Weber", "3")])
        self.assertEqual(texts(root, "Letzte Lieferscheine", "Beleg"),
                         ["LS-3", "LS-2", "LS-1", "LS-00", "LS-0"])
        self.assertEqual(
            texts(root, "Letzte Lieferscheine", "Datum"),
            ["02.10.2026", "01.10.2026", "02.03.2026", "01.12.2025",
             "01.06.2025"])

    def test_open_vessels_of_any_substance_flasks_among_them(self) -> None:
        """Requirement: Overview page (`Offene Gefäße`, the number of
        vessels of any substance holding an amount above zero)."""
        self.item("CH-0012", quantity=5)
        self.vessel("CH-0012", "mg", "50")
        self.vessel("acetophenone", "mg", "5", source="made")
        self.vessel("CH-0012", "mg", "20", source="bought", supplier="Sigma")
        self.vessel("acetophenone", "mg", "0")
        self.vessel("CH-0012", "g", "2", flask=True)
        self.assertEqual(figure_values(self.get())["Offene Gefäße"], "4")

    def test_names_come_from_the_substances_of_the_articles(self) -> None:
        zimt = self.item("CH-0012", quantity=40)
        self.deliver(zimt, 3, date(2026, 3, 2), number="LS-1")
        requested = rows(self.get(), "Meistgefragt 2026")
        self.assertEqual(len(requested), 1)
        self.assertEqual(requested[0]["Artikelnr."].text(), "CH-0012")
        self.assertEqual(requested[0]["Substanz"].text(), "(E)-Zimtsäure")
        accept(language="en")
        requested = rows(self.get(), "Most requested in 2026")
        self.assertEqual(requested[0]["Substance"].text(),
                         "(E)-Cinnamic acid")

    def test_the_latest_notes_link_their_pages(self) -> None:
        self.scenario()
        from inventory.models import DeliveryNote
        first = rows(self.get(), "Letzte Lieferscheine")[0]["Beleg"]
        self.assertEqual(first.find("a").get("href"),
                         f"/lab/inventory/deliveries/"
                         f"{DeliveryNote.objects.get(number='LS-3').pk}/")

    def test_a_note_without_number(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = self.deliver(item, 1, date(2026, 11, 2), number=None)
        cell = rows(self.get(), "Letzte Lieferscheine")[0]["Beleg"]
        self.assertEqual(cell.find("a").text(), "–")
        self.assertEqual(cell.find("a").get("href"),
                         f"/lab/inventory/deliveries/{note.pk}/")

    def test_historical_notes_count(self) -> None:
        from inventory.bookings import book_note
        item = self.item("CH-0012", quantity=5)
        book_note(self.kl, date=date(2026, 2, 1),
                  lines=[historical_line(item, 7)], historical=True)
        self.assertRegex(figure_values(self.get())["Abgegeben 2026"],
                         r"^7(?!\d)")

    def test_five_entries_at_most(self) -> None:
        for number in range(7):
            item = self.item(f"A-{number}", quantity=20)
            self.deliver(item, number + 1, date(2026, 5, 1),
                         recipient=f"Empfänger {number}")
        root = self.get()
        for title in ("Meistgefragt 2026", "Empfänger 2026",
                      "Letzte Lieferscheine"):
            with self.subTest(title=title):
                self.assertEqual(len(rows(root, title)), 5)
        self.assertEqual(texts(root, "Meistgefragt 2026", "Artikelnr.")[0],
                         "A-6")
        self.assertEqual(texts(root, "Empfänger 2026", "Empfänger")[0],
                         "Empfänger 6")
        self.assertEqual(texts(root, "Empfänger 2026", "Gebinde")[0], "7")


class LeapDayTests(OverviewCase):

    def test_the_last_years_span_ends_on_the_28th(self) -> None:
        from . import berlin, ticking
        self.enterContext(ticking(berlin(2028, 2, 29, 9)))
        item = self.item("CH-0012", quantity=20)
        self.deliver(item, 2, date(2027, 2, 28))
        self.deliver(item, 3, date(2027, 3, 1))
        text = figure_values(self.get())["Abgegeben 2028"]
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
        root = self.get()
        current, previous = bars(root)
        self.assertEqual(len(current), 12)
        self.assertEqual(len(previous), 12)
        self.assertEqual(title_of_bar(current[0]), "Dezember 2025: 0")
        self.assertEqual(title_of_bar(previous[0]), "Dezember 2024: 0")
        self.assertEqual(title_of_bar(current[3]), "März 2026: 3")
        self.assertEqual(title_of_bar(previous[3]), "März 2025: 4")
        self.assertEqual(title_of_bar(current[-1]), "November 2026: 0")
        heights = [float(r.get("height")) for r in current]
        self.assertGreater(heights[3], 0)
        self.assertEqual(heights[:3], [0.0] * 3)
        labels = value_labels(root)
        self.assertEqual(sorted(t.text() for t in labels), ["3", "4"])
        svg = root.find("svg")
        _, _, width, height = (float(n) for n in
                               svg.get("viewbox").split())
        for label in labels:
            with self.subTest(label=label.text()):
                self.assertGreaterEqual(float(label.get("y")) - 11, 0)
                self.assertLessEqual(float(label.get("y")), height)
                self.assertTrue(0 <= float(label.get("x")) <= width)

    def test_each_month_is_labelled(self) -> None:
        self.item("A-1")
        labels = month_labels(self.get())
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
        header, found = widget_grid(widget(root, "Nächste Synthesen"))
        self.assertEqual(header, ["Artikelnr.", "Name", "Priorität",
                                  "Spätester Start", "Aufgabe"])
        plan = Plan(date(2026, 11, 4))
        wanted = [found.article_number for found in sorted(
            plan.forecasts(),
            key=lambda found: (found.slack, found.article_number))][:5]
        self.assertEqual([row["Artikelnr."].text() for row in found],
                         wanted)
        self.assertEqual(wanted[0], "NV-1")
        first = found[0]["Aufgabe"]
        self.assertEqual(first.find("a").get("href"),
                         f"/lab/tasks/{task.number}/")
        self.assertIn("verspätet", first.text())
        self.assertEqual(found[1]["Aufgabe"].text(), "–")
        due = sum(each.priority in (Priority.HIGH, Priority.MEDIUM)
                  for each in plan.forecasts())
        value = figure_values(root)["Fällige Synthesen"]
        self.assertRegex(value, rf"^{due}(?!\d)")
        self.assertIn("1 verspätet", value)
        self.assertEqual(widget(root, "Nächste Synthesen").find(
            "a", href="/lab/planning/").text(), "Zur Planung")

    def test_the_name_is_the_substances(self) -> None:
        self.planned_item("NV-1", quantity=0, name="Erste")
        found = rows(self.get(), "Nächste Synthesen")
        self.assertEqual(found[0]["Name"].text(), "Erste")
        self.assertEqual([a.get("href") for a in found[0]["Name"].find_all(
            "a")], ["/lab/registry/substances/nv-1/"])

    def test_the_article_links_its_first_item(self) -> None:
        self.planned_item("NV-1", size="5", quantity=0)
        first = self.planned_item("NV-1", size="1", quantity=0)
        found = rows(self.get(), "Nächste Synthesen")
        self.assertEqual(found[0]["Artikelnr."].find("a").get("href"),
                         f"/lab/inventory/items/{first.pk}/")


class EmptyTests(OverviewCase):

    def test_an_empty_lab(self) -> None:
        """Scenario: An empty lab."""
        root = self.get()
        self.assertEqual(root.find("div", "stock-bar").find_all("a"), [])
        for label, value in figure_values(root).items():
            with self.subTest(label=label):
                self.assertTrue(value.startswith("0"), value)
        found = widget(root, "Nächste Synthesen")
        self.assertIn("Keine Prognosen.", found.text())
        self.assertIsNone(found.find("table"))
        current, previous = bars(root)
        self.assertEqual(len(current), 12)
        self.assertEqual(len(previous), 12)
        self.assertTrue(all(float(r.get("height")) == 0
                            for r in current + previous))
        self.assertEqual(value_labels(root), [])
        for title in ("Meistgefragt 2026", "Empfänger 2026",
                      "Letzte Lieferscheine"):
            with self.subTest(title=title):
                self.assertIn("Keine Abgaben.", widget(root, title).text())


class EnglishTests(OverviewCase):

    def test_overview_in_english(self) -> None:
        """Scenario: Overview in English."""
        accept(language="en")
        root = self.get()
        self.assertEqual(root.find("h1").text(), "Lab at a glance")
        titles = [title_of(w) for w in widgets(root)]
        for title in ("Inventory", "Next syntheses",
                      "Deliveries per month", "Latest delivery notes"):
            with self.subTest(title=title):
                self.assertIn(title, titles)
        self.assertEqual(titles, list(WIDGET_TITLES_EN))


class SummaryTests(OverviewCase):

    def test_summary(self) -> None:
        """Scenario: Summary."""
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        make_task(self.kl, substance="OK-1", started=date(2026, 11, 1))
        self.vessel("OK-1", "mg", "50")
        response = self.client.get(SUMMARY)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        sections = root.find_all("section", "lab-summary")
        self.assertEqual(len(sections), 1)
        links = sections[0].find("div", "stock-bar").find_all("a")
        self.assertEqual([a.text() for a in links], ["1", "2"])
        self.assertEqual(len(tiles(sections[0])), 4)
        self.assertEqual(list(figures(root)), list(FIGURES))
        self.assertEqual(
            [hrefs(each) for each in figures(root).values()],
            [[], ["/lab/planning/"], ["/lab/tasks/"],
             ["/lab/inventory/vessels/"]])
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
        self.assertEqual(
            len(page(response).find_all("section", "lab-overview")), 1)
        self.assertEqual(self.client.get("/procedures/").status_code, 404)

    def test_the_navigation_marks_the_overview_as_the_menu_says(
            self) -> None:
        self.assertEqual(ns.marks(self.client.get(OVERVIEW)),
                         ns.expected_marks(OVERVIEW))


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
