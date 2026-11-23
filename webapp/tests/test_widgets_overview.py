"""Tests of the overview and its summary as widgets: the figures strip,
the stock widget with its legend, the chart with its value labels and
legend, the tables of the year's lists, and the chart's coordinates
(lab-overview: Overview page, Summary for the home page; web-app:
Widgets)."""

import re
from datetime import date

from django.test import SimpleTestCase

from . import Element, page
from .collection_support import accept
from .overview_support import (FIGURES, FIGURES_EN, SUMMARY,
                               WIDGET_TITLES, YEAR_LISTS, YEAR_LISTS_EN,
                               OverviewCase, figure_values, figures,
                               hidden, hrefs, stock_widget)
from .planning_support import has_date
from .widget_support import (carries, count_of, tile, title_of, tiles,
                             widget, widget_grid, widgets)

CHART = ("Abgaben je Monat", "Deliveries per month")
FONT = 11


def number_in(text: str, wanted: int) -> bool:
    """Whether ``text`` holds the number ``wanted`` as a number of its
    own, not as part of a longer one."""
    return re.search(rf"(?<![\d]){wanted}(?![\d])", text) is not None


def levels_of(found: Element) -> list[str]:
    """The levels named by the ``level-<level>`` classes of ``found``
    and the elements inside it."""
    return sorted({c[len("level-"):] for node in (found, *found.walk())
                   for c in node.classes
                   if c.startswith("level-") and c != "level-label"})


def legend(found: Element) -> list[tuple[str, Element]]:
    """The entries of the legend of the stock widget ``found``, in
    page order, each as its one level and its ``li``; fail unless the
    widget holds exactly one list."""
    lists = found.find_all(("ul", "ol"))
    assert len(lists) == 1, f"the widget holds {len(lists)} lists"
    entries = []
    for entry in lists[0].find_all("li"):
        levels = levels_of(entry)
        assert len(levels) == 1, \
            f"the legend entry {entry.text()!r} carries levels {levels}"
        entries.append((levels[0], entry))
    return entries


def bar_levels(found: Element) -> list[tuple[str, str]]:
    """The level and the number of each link of the stock bar of the
    widget ``found``."""
    return [(levels_of(a)[0], a.text())
            for a in found.find("div", "stock-bar").find_all("a")]


def first_number(style: str | None) -> float:
    found = re.search(r"\d+(?:\.\d+)?", style or "")
    assert found is not None, f"the style {style!r} holds no number"
    return float(found.group())


def share_of(cell: Element) -> float:
    """The share, as a percentage, that the one ``aria-hidden`` bar in
    ``cell`` is drawn at: the first number of the style of the bar or
    of an element inside it."""
    bars = [node for node in cell.walk() if hidden(node)]
    assert len(bars) == 1, f"the cell holds {len(bars)} bars"
    styled = [node for node in (bars[0], *bars[0].walk())
              if node.get("style")]
    assert styled, "the bar of the cell has no style"
    return first_number(styled[0].get("style"))


def figure(cell: Element) -> str:
    """The text of ``cell`` without its ``aria-hidden`` bar."""
    return cell.text(hidden)


class OverviewLayoutTests(OverviewCase):

    def test_a_strip_then_a_grid_of_the_widgets(self) -> None:
        root = self.get()
        sections = root.find_all("section", "lab-overview")
        self.assertEqual(len(sections), 1)
        section = sections[0]
        strips = section.find_all(cls="figures-strip")
        grids = section.find_all(cls="overview-grid")
        self.assertEqual((len(strips), len(grids)), (1, 1))
        strip, grid = strips[0], grids[0]
        inside = list(grid.walk())
        for each in widgets(root):
            with self.subTest(title=title_of(each)):
                self.assertTrue(any(each is node for node in inside))
                self.assertEqual(each.tag, "section")
        self.assertFalse(any(strip is node for node in inside))
        walked = list(section.walk())
        self.assertLess(walked.index(strip), walked.index(grid))
        self.assertEqual([title_of(w) for w in widgets(grid)],
                         list(WIDGET_TITLES))

    def test_every_widget_has_a_title_bar_with_its_title(self) -> None:
        found = widgets(self.get())
        self.assertEqual(len(found), len(WIDGET_TITLES))
        for each in found:
            with self.subTest(title=title_of(each)):
                head = each.find(cls="widget__head")
                self.assertIsNotNone(head)
                self.assertIsNotNone(head.find("h2"))

    def test_the_next_syntheses_link_the_planning(self) -> None:
        self.planned_item("NV-1", quantity=0)
        link = widget(self.get(), "Nächste Synthesen").find(
            "a", href="/lab/planning/")
        self.assertIsNotNone(link)
        self.assertEqual(link.text(), "Zur Planung")


class StripTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def late_syntheses(self) -> None:
        for number, quantity in enumerate((0, 30, 2, 50, 8, 4, 16), 1):
            self.planned_item(f"NV-{number}", quantity=quantity)
        self.running("NV-1", 1)

    def test_four_tiles_with_label_and_value(self) -> None:
        self.scenario()
        root = self.get()
        self.assertEqual(len(root.find_all(cls="figures-strip")), 1)
        self.assertEqual(len(tiles(root)), 4)
        shown = figures(root)
        self.assertEqual(list(shown), list(FIGURES))
        for label, found in shown.items():
            with self.subTest(label=label):
                self.assertIsNotNone(found.find(cls="figure-tile__value"))

    def test_delivered_shows_the_last_year_beneath_it(self) -> None:
        self.scenario()
        found = tile(self.get(), "Abgegeben 2026")
        value = found.find(cls="figure-tile__value")
        self.assertRegex(value.text(), r"^5(?!\d)")
        sub = found.find(cls="figure-tile__sub")
        self.assertIsNotNone(sub)
        self.assertEqual(sub.text(), "Vorjahr bis 07.11.2025: 4")
        self.assertEqual(hrefs(found), [])

    def test_syntheses_due_link_the_planning_and_carry_the_late_badge(
            self) -> None:
        self.late_syntheses()
        found = tile(self.get(), "Fällige Synthesen")
        self.assertEqual(hrefs(found), ["/lab/planning/"])
        self.assertNotIn("verspätet", found.find("a").text())
        badges = [n for n in found.walk() if "badge--late" in n.classes]
        self.assertEqual([b.text() for b in badges], ["1 verspätet"])
        self.assertTrue(all(b.closest("a") is None for b in badges))

    def test_no_late_task_no_badge(self) -> None:
        self.planned_item("NV-1", quantity=0)
        found = tile(self.get(), "Fällige Synthesen")
        self.assertFalse(carries(found, "class", "badge--late"))
        self.assertNotIn("verspätet", found.text())

    def test_tasks_are_one_link_reading_running_and_planned(self) -> None:
        self.scenario()
        found = tile(self.get(), "Aufgaben")
        self.assertEqual(hrefs(found), ["/lab/tasks/"])
        self.assertEqual(found.find("a").text(), "1 laufend · 2 geplant")

    def test_open_vessels_are_a_number_linking_the_vessels(self) -> None:
        self.scenario()
        found = tile(self.get(), "Offene Gefäße")
        self.assertEqual(hrefs(found), ["/lab/inventory/vessels/"])
        self.assertEqual(figure_values(self.get())["Offene Gefäße"], "1")

    def test_an_empty_lab_reads_zeros(self) -> None:
        shown = figure_values(self.get())
        self.assertEqual(shown["Offene Gefäße"], "0")
        self.assertIn("0 laufend · 0 geplant", shown["Aufgaben"])
        self.assertRegex(shown["Abgegeben 2026"], r"^0(?!\d)")
        self.assertRegex(shown["Fällige Synthesen"], r"^0(?!\d)")

    def test_the_strip_in_english(self) -> None:
        self.scenario()
        accept(language="en")
        root = self.get()
        shown = figure_values(root)
        self.assertEqual(list(shown), list(FIGURES_EN))
        delivered = tile(root, "Delivered in 2026").find(
            cls="figure-tile__sub").text()
        self.assertIn("Last year to", delivered)
        self.assertTrue(has_date(delivered, date(2025, 11, 7)), delivered)
        self.assertTrue(delivered.endswith(": 4"), delivered)
        self.assertEqual(tile(root, "Tasks").find("a").text(),
                         "1 running · 2 planned")

    def test_the_late_badge_in_english(self) -> None:
        self.late_syntheses()
        accept(language="en")
        found = tile(self.get(), "Syntheses due")
        badges = [n for n in found.walk() if "badge--late" in n.classes]
        self.assertEqual([b.text() for b in badges], ["1 late"])


class StockWidgetTests(OverviewCase):

    def levels(self) -> None:
        """Items at the levels low (1), ok (2), undelivered (3) and
        dormant (1)."""
        from inventory.models import Item
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        for number in range(3):
            self.item(f"UN-{number}", quantity=5)
        dormant = self.item("DO-1", quantity=4)
        Item.objects.filter(pk=dormant.pk).update(status="discontinued")

    def test_each_level_shown_is_named_with_its_number(self) -> None:
        from .inventory_support import LEVELS
        self.levels()
        found = stock_widget(self.get())
        shown = bar_levels(found)
        self.assertEqual({level for level, _ in shown},
                         {"low", "ok", "undelivered", "dormant"})
        entries = legend(found)
        self.assertEqual([level for level, _ in entries],
                         [level for level, _ in shown])
        for (level, entry), (_, count) in zip(entries, shown):
            with self.subTest(level=level):
                text = entry.text()
                self.assertIn(LEVELS[level], text)
                self.assertTrue(
                    number_in(text.replace(LEVELS[level], "", 1),
                              int(count)), text)

    def test_the_number_of_items_follows_the_legend(self) -> None:
        self.levels()
        found = stock_widget(self.get())
        self.assertIn("7 Artikel", found.text())
        self.assertTrue(all("Artikel" not in entry.text()
                            for _, entry in legend(found)))

    def test_the_legend_is_outside_the_bar(self) -> None:
        self.levels()
        found = stock_widget(self.get())
        bar = found.find("div", "stock-bar")
        for _, entry in legend(found):
            self.assertIsNone(
                next((a for a in entry.find_all("a")
                      if any(a is n for n in bar.walk())), None))
            self.assertFalse(any(entry is n for n in bar.walk()))

    def test_the_bar_is_unchanged_in_its_widget(self) -> None:
        self.levels()
        found = stock_widget(self.get())
        links = found.find("div", "stock-bar").find_all("a")
        for each in links:
            with self.subTest(level=levels_of(each)):
                (level,) = levels_of(each)
                self.assertEqual(
                    each.get("href"),
                    f"/lab/inventory/end-products/?stock={level}")
                self.assertEqual(each.get("style"),
                                 f"flex-grow: {each.text()}")
                self.assertTrue(each.get("title").endswith(
                    f": {each.text()}"))

    def test_an_empty_lab_has_no_legend_entry(self) -> None:
        found = stock_widget(self.get())
        self.assertEqual(found.find("div", "stock-bar").find_all("a"), [])
        self.assertEqual(found.find_all("li"), [])
        self.assertIn("0 Artikel", found.text())

    def test_the_stock_in_english(self) -> None:
        self.levels()
        accept(language="en")
        found = stock_widget(self.get())
        self.assertEqual(title_of(found), "Inventory")
        self.assertIn("7 items", found.text())
        self.assertEqual(len(legend(found)), 4)


class ChartWidgetTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def drawing(self, root: Element) -> tuple[Element, list, list, list]:
        svg = widget(root, *CHART).find("svg")
        rects = svg.find_all("rect")
        return (svg,
                [r for r in rects if "current" in r.classes],
                [r for r in rects if "previous" in r.classes],
                svg.find_all("text", cls="chart-value"))

    @staticmethod
    def centre(rect: Element) -> float:
        return float(rect.get("x")) + float(rect.get("width")) / 2

    def test_each_value_label_stands_centred_above_its_bar(self) -> None:
        item = self.item("CH-0012", quantity=20)
        self.deliver(item, 3, date(2026, 3, 2))
        self.deliver(item, 4, date(2025, 3, 15))
        _, current, previous, labels = self.drawing(self.get())
        shown = {t.text(): t for t in labels}
        self.assertEqual(sorted(shown), ["3", "4"])
        for text, rect in (("3", current[3]), ("4", previous[3])):
            with self.subTest(label=text):
                label = shown[text]
                self.assertEqual(label.get("text-anchor"), "middle")
                self.assertAlmostEqual(float(label.get("x")),
                                       self.centre(rect), delta=0.5)
                self.assertLessEqual(float(label.get("y")),
                                     float(rect.get("y")))

    def test_a_label_above_the_tallest_bar_is_inside_the_drawing(
            self) -> None:
        item = self.item("CH-0012", quantity=60)
        self.deliver(item, 20, date(2026, 3, 2))
        self.deliver(item, 25, date(2025, 3, 15))
        svg, current, previous, labels = self.drawing(self.get())
        self.assertEqual(sorted(t.text() for t in labels), ["20", "25"])
        for label in labels:
            with self.subTest(label=label.text()):
                self.assertGreaterEqual(float(label.get("y")) - FONT, 0)

    def test_no_label_for_a_value_of_zero(self) -> None:
        item = self.item("CH-0012", quantity=20)
        self.deliver(item, 3, date(2026, 3, 2))
        _, current, previous, labels = self.drawing(self.get())
        self.assertEqual([t.text() for t in labels], ["3"])
        self.assertTrue(all(t.text() != "0" for t in labels))

    def test_a_year_of_values_keeps_the_twelve_month_labels(self) -> None:
        item = self.item("CH-0012", quantity=90)
        for year, month in [(2025, 12)] + [(2026, m) for m in range(1, 12)]:
            self.deliver(item, month, date(year, month, 2))
        svg, current, previous, labels = self.drawing(self.get())
        self.assertEqual(len(labels), 12)
        months = [t.text() for t in svg.find_all("text")
                  if "chart-value" not in t.classes]
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0], "Dez")
        self.assertEqual(len(set(months)), 12)
        for label, rect in zip(sorted(
                labels, key=lambda t: float(t.get("x"))), current):
            self.assertAlmostEqual(float(label.get("x")),
                                   self.centre(rect), delta=0.5)

    def test_the_legend_names_the_two_colours_under_the_chart(self) -> None:
        found = widget(self.get(), *CHART)
        svg = found.find("svg")
        walked = list(found.walk())
        after = walked[walked.index(svg) + 1 + len(list(svg.walk())):]
        for name in ("Aktuelle 12 Monate", "Vorjahresmonat"):
            with self.subTest(name=name):
                self.assertFalse(any(name in n.text() for n in svg.walk()))
                named = [n for n in after if name in n.text()]
                self.assertTrue(named, f"no legend names {name!r}")
        outside = found.text(lambda node: node is svg)
        self.assertLess(outside.index("Aktuelle 12 Monate"),
                        outside.index("Vorjahresmonat"))
        self.assertIsNone(found.find("figcaption"))
        self.assertNotIn("Der graue Balken", found.text())

    def test_the_legend_in_english(self) -> None:
        accept(language="en")
        text = widget(self.get(), *CHART).text()
        self.assertIn("Last 12 months", text)
        self.assertIn("Same month a year before", text)
        self.assertNotIn("The grey bar", text)

    def test_the_chart_of_an_empty_lab_has_no_value_label(self) -> None:
        _, current, previous, labels = self.drawing(self.get())
        self.assertEqual((len(current), len(previous), labels),
                         (12, 12, []))


class YearListTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def grid(self, title: str, root: Element | None = None) -> tuple:
        return widget_grid(widget(root or self.get(), title))

    def ranked(self) -> None:
        """Articles and recipients with 4, 2 and 1 containers
        delivered in 2026."""
        for article, count, recipient in (("A-1", 4, "Eins"),
                                          ("A-2", 2, "Zwei"),
                                          ("A-3", 1, "Drei")):
            item = self.item(article, quantity=20)
            self.deliver(item, count, date(2026, 5, 1), recipient=recipient)

    def test_the_columns_in_german(self) -> None:
        self.scenario()
        root = self.get()
        self.assertEqual(self.grid("Meistgefragt 2026", root)[0],
                         ["Artikelnr.", "Substanz", "Gebinde"])
        self.assertEqual(self.grid("Empfänger 2026", root)[0],
                         ["Empfänger", "Gebinde"])
        header = self.grid("Letzte Lieferscheine", root)[0]
        self.assertEqual(header, ["Beleg", "Datum", "Empfänger", "Gebinde"])
        self.assertNotIn("Notiz", header)

    def test_the_columns_in_english(self) -> None:
        self.scenario()
        accept(language="en")
        root = self.get()
        self.assertEqual(self.grid("Most requested in 2026", root)[0],
                         ["Article no.", "Substance", "Containers"])
        self.assertEqual(self.grid("Recipients in 2026", root)[0],
                         ["Recipient", "Containers"])
        self.assertEqual(self.grid("Latest delivery notes", root)[0],
                         ["Note", "Date", "Recipient", "Containers"])

    def test_the_count_is_the_number_of_rows(self) -> None:
        self.scenario()
        root = self.get()
        for title, wanted in zip(YEAR_LISTS, (2, 1, 5)):
            with self.subTest(title=title):
                self.assertEqual(count_of(widget(root, title)), wanted)
                self.assertEqual(len(self.grid(title, root)[1]), wanted)

    def test_the_count_stops_at_five(self) -> None:
        for number in range(7):
            item = self.item(f"A-{number}", quantity=20)
            self.deliver(item, number + 1, date(2026, 5, 1),
                         recipient=f"Empfänger {number}")
        root = self.get()
        for title in YEAR_LISTS:
            with self.subTest(title=title):
                self.assertEqual(count_of(widget(root, title)), 5)

    def test_an_empty_list_has_no_count_and_reads_no_deliveries(
            self) -> None:
        root = self.get()
        for title in YEAR_LISTS:
            with self.subTest(title=title):
                found = widget(root, title)
                self.assertIsNone(count_of(found))
                self.assertIn("Keine Abgaben.", found.text())
                self.assertEqual(found.find_all("td"), [])

    def test_an_empty_list_in_english(self) -> None:
        accept(language="en")
        root = self.get()
        for title in YEAR_LISTS_EN:
            with self.subTest(title=title):
                self.assertIn("No deliveries.", widget(root, title).text())

    def test_the_most_requested_link_their_first_items(self) -> None:
        second = self.item("CH-0012", size="5", quantity=20)
        first = self.item("CH-0012", size="1", quantity=20)
        self.deliver(second, 2, date(2026, 3, 2))
        _, found = self.grid("Meistgefragt 2026")
        self.assertEqual(len(found), 1)
        link = found[0]["Artikelnr."].find("a")
        self.assertEqual(link.text(), "CH-0012")
        self.assertEqual(link.get("href"),
                         f"/lab/inventory/items/{first.pk}/")

    def test_the_two_rankings_draw_a_bar_in_proportion(self) -> None:
        self.ranked()
        root = self.get()
        for title, column in (("Meistgefragt 2026", "Gebinde"),
                              ("Empfänger 2026", "Gebinde")):
            with self.subTest(title=title):
                _, found = self.grid(title, root)
                self.assertEqual([figure(r[column]) for r in found],
                                 ["4", "2", "1"])
                shares = [share_of(r[column]) for r in found]
                for got, wanted in zip(shares, (100, 50, 25)):
                    self.assertAlmostEqual(got, wanted, delta=1)

    def test_a_tie_for_the_first_place_fills_both_bars(self) -> None:
        for article in ("A-1", "A-2"):
            self.deliver(self.item(article, quantity=20), 3,
                         date(2026, 5, 1))
        _, found = self.grid("Meistgefragt 2026")
        self.assertEqual([share_of(r["Gebinde"]) for r in found],
                         [100.0, 100.0])

    def test_the_latest_notes_draw_no_bar(self) -> None:
        self.ranked()
        widget_ = widget(self.get(), "Letzte Lieferscheine")
        self.assertEqual([n for n in widget_.walk() if hidden(n)], [])
        _, found = widget_grid(widget_)
        self.assertEqual(sorted(r["Gebinde"].text() for r in found),
                         ["1", "2", "4"])

    def test_no_other_widget_draws_a_bar_of_this_kind(self) -> None:
        self.ranked()
        root = self.get()
        for title in ("Bestand", "Nächste Synthesen"):
            with self.subTest(title=title):
                self.assertEqual(
                    [n for n in widget(root, title).walk()
                     if n.get("aria-hidden") == "true"], [])

    def test_an_empty_recipient_reads_a_dash(self) -> None:
        self.scenario()
        _, found = self.grid("Letzte Lieferscheine")
        self.assertEqual([r["Empfänger"].text() for r in found],
                         ["AK Weber", "–", "AK Weber", "–", "–"])
        self.assertEqual([r["Gebinde"].text() for r in found],
                         ["6", "2", "3", "5", "4"])

    def test_the_latest_notes_link_the_delivery_list(self) -> None:
        """Scenario: A note without a number (the link in the title
        bar)."""
        self.scenario()
        found = widget(self.get(), "Letzte Lieferscheine")
        links = found.find(cls="widget__head").find_all("a")
        self.assertEqual([(a.get("href"), a.text()) for a in links],
                         [("/lab/inventory/deliveries/", "Alle →")])

    def test_the_link_to_the_delivery_list_in_english(self) -> None:
        self.scenario()
        accept(language="en")
        found = widget(self.get(), "Latest delivery notes")
        links = found.find(cls="widget__head").find_all("a")
        self.assertEqual([(a.get("href"), a.text()) for a in links],
                         [("/lab/inventory/deliveries/", "All →")])

    def test_the_link_to_the_delivery_list_stands_without_notes(
            self) -> None:
        found = widget(self.get(), "Letzte Lieferscheine")
        self.assertEqual(
            [a.get("href") for a in found.find(
                cls="widget__head").find_all("a")],
            ["/lab/inventory/deliveries/"])

    def test_no_other_year_list_links_the_delivery_list(self) -> None:
        self.scenario()
        root = self.get()
        for title in ("Meistgefragt 2026", "Empfänger 2026"):
            with self.subTest(title=title):
                self.assertIsNone(widget(root, title).find(
                    "a", href="/lab/inventory/deliveries/"))

    def test_the_recipients_leave_out_notes_without_one(self) -> None:
        self.scenario()
        _, found = self.grid("Empfänger 2026")
        self.assertEqual([r["Empfänger"].text() for r in found],
                         ["AK Weber"])


class SummaryWidgetTests(OverviewCase):

    def setUp(self) -> None:
        super().setUp()
        self.at_the_seventh()

    def summary(self) -> Element:
        response = self.client.get(SUMMARY)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_the_summary_shows_the_strip_and_the_stock_alone(self) -> None:
        self.scenario()
        root = self.summary()
        sections = root.find_all("section", "lab-summary")
        self.assertEqual(len(sections), 1)
        section = sections[0]
        self.assertEqual(len(section.find_all(cls="figures-strip")), 1)
        self.assertEqual([title_of(w) for w in widgets(root)], ["Bestand"])
        self.assertTrue(any(w is stock_widget(root)
                            for w in widgets(section)))
        self.assertEqual(list(figures(root)), list(FIGURES))
        self.assertEqual(root.find("base").get("target"), "_top")
        self.assertEqual(
            [a for a in root.find_all("a") if a.get("href") == "/lab/"], [])
        for title in ("Nächste Synthesen", "Abgaben je Monat"):
            self.assertNotIn(title, [title_of(w) for w in widgets(root)])
        self.assertIsNone(root.find("table"))
        self.assertIsNone(root.find("svg"))

    def test_the_summary_shows_what_the_overview_shows(self) -> None:
        self.scenario()
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        shown = self.get()
        framed = self.summary()
        self.assertEqual(figure_values(framed), figure_values(shown))
        self.assertEqual(
            [hrefs(f) for f in figures(framed).values()],
            [hrefs(f) for f in figures(shown).values()])
        self.assertEqual(
            [(level, entry.text())
             for level, entry in legend(stock_widget(framed))],
            [(level, entry.text())
             for level, entry in legend(stock_widget(shown))])
        self.assertEqual(bar_levels(stock_widget(framed)),
                         bar_levels(stock_widget(shown)))
        self.assertGreater(len(legend(stock_widget(framed))), 0)

    def test_the_summary_names_the_levels_with_their_numbers(self) -> None:
        for article in ("OK-1", "OK-2"):
            self.with_mean_quarter(self.item(article, quantity=20), 4)
        self.with_mean_quarter(self.item("LO-1", quantity=3), 4)
        found = stock_widget(self.summary())
        entries = legend(found)
        self.assertEqual([level for level, _ in entries], ["low", "ok"])
        self.assertIn("niedrig", entries[0][1].text())
        self.assertTrue(number_in(entries[0][1].text(), 1))
        self.assertIn("ausreichend", entries[1][1].text())
        self.assertTrue(number_in(entries[1][1].text(), 2))
        self.assertIn("3 Artikel", found.text())

    def test_the_summary_of_an_empty_lab(self) -> None:
        root = self.summary()
        found = stock_widget(root)
        self.assertEqual(found.find_all("li"), [])
        self.assertEqual(len(tiles(root)), 4)
        self.assertEqual(figure_values(root)["Offene Gefäße"], "0")

    def test_the_summary_late_badge(self) -> None:
        self.planned_item("NV-1", quantity=0)
        self.running("NV-1", 1)
        root = self.summary()
        self.assertTrue(carries(tile(root, "Fällige Synthesen"), "class",
                                "badge--late"))


class ChartCoordinateTests(SimpleTestCase):
    """The bars of ``overview.chart.chart`` carry the centre and the
    baseline of their value labels."""

    RISING = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    FALLING = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]

    def drawn(self, current: list[int], previous: list[int]):
        from overview.chart import chart
        from overview.figures import months_ending
        return chart(months_ending(date(2026, 11, 7)), current, previous)

    def bars(self, drawing):
        return [bar for month in drawing.months
                for bar in (month.previous, month.current)]

    def coordinate(self, bar, name: str) -> float:
        self.assertTrue(hasattr(bar, name), f"Bar has no {name}")
        return getattr(bar, name)

    def test_every_bar_has_its_label_coordinates(self) -> None:
        for bar in self.bars(self.drawn(self.RISING, self.FALLING)):
            self.coordinate(bar, "label_x")
            self.coordinate(bar, "label_y")

    def test_the_label_is_centred_on_its_bar(self) -> None:
        from overview.chart import BAR
        for bar in self.bars(self.drawn([3] * 12, [5] * 12)):
            self.assertAlmostEqual(self.coordinate(bar, "label_x"),
                                   bar.x + BAR / 2, delta=0.5)

    def test_the_label_stands_above_its_bar(self) -> None:
        for bar in self.bars(self.drawn(self.RISING, self.FALLING)):
            if bar.value == 0:
                continue
            self.assertLess(self.coordinate(bar, "label_y"), bar.y)

    def test_a_label_above_the_tallest_bar_lies_inside_the_drawing(
            self) -> None:
        for current, previous in (([0] * 11 + [9], [0] * 12),
                                  ([2] * 12, [0] * 11 + [30]),
                                  ([1] * 12, [1] * 12),
                                  ([100] * 12, [50] * 12)):
            drawing = self.drawn(current, previous)
            tallest = max(self.bars(drawing), key=lambda bar: bar.value)
            self.assertGreaterEqual(
                self.coordinate(tallest, "label_y") - FONT, 0)

    def test_wide_paired_labels_do_not_overlap(self) -> None:
        """Two labels of a month too wide to stand side by side stand
        a line apart, inside the drawing."""
        drawing = self.drawn([1001] * 12, [1000] * 12)
        for month in drawing.months:
            previous, current = month.previous, month.current
            self.assertGreaterEqual(
                abs(self.coordinate(previous, "label_y")
                    - self.coordinate(current, "label_y")), FONT)
            for bar in (previous, current):
                self.assertGreaterEqual(bar.label_y - FONT, 0)

    def test_narrow_paired_labels_keep_their_place(self) -> None:
        """Labels narrow enough to stand side by side stay above their
        own bars."""
        from overview.chart import LABEL_GAP
        for month in self.drawn([21] * 12, [22] * 12).months:
            for bar in (month.previous, month.current):
                self.assertAlmostEqual(bar.label_y, bar.y - LABEL_GAP)

    def test_every_label_lies_inside_the_drawing(self) -> None:
        drawing = self.drawn([4, 0, 7, 1, 9, 2, 8, 3, 6, 5, 10, 12],
                             [12, 11, 0, 5, 0, 1, 2, 3, 4, 5, 6, 7])
        for bar in self.bars(drawing):
            label_x = self.coordinate(bar, "label_x")
            label_y = self.coordinate(bar, "label_y")
            self.assertGreaterEqual(label_y - FONT, 0)
            self.assertLessEqual(label_y, drawing.baseline)
            self.assertGreaterEqual(label_x, 0)
            self.assertLessEqual(label_x, drawing.width)

    def test_all_zero_values_still_leave_the_labels_inside(self) -> None:
        for bar in self.bars(self.drawn([0] * 12, [0] * 12)):
            self.assertGreaterEqual(
                self.coordinate(bar, "label_y") - FONT, 0)
