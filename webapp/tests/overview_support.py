"""Helpers shared by the tests of the lab's overview and its summary
(lab-overview: Overview page, Summary for the home page)."""

from datetime import date
from typing import Any

from . import Element, berlin, make_task, ticking
from .planning_support import PlanningCase
from .widget_support import tile_value, tiles, widget

OVERVIEW = "/lab/"
SUMMARY = "/lab/summary/"
SEVENTH = date(2026, 11, 7)
YEAR_LISTS = ("Meistgefragt 2026", "Empfänger 2026", "Letzte Lieferscheine")
YEAR_LISTS_EN = ("Most requested in 2026", "Recipients in 2026",
                 "Latest delivery notes")
WIDGET_TITLES = ("Bestand", "Nächste Synthesen", "Abgaben je Monat",
                 *YEAR_LISTS)
WIDGET_TITLES_EN = ("Inventory", "Next syntheses", "Deliveries per month",
                    *YEAR_LISTS_EN)
FIGURES = ("Abgegeben 2026", "Fällige Synthesen", "Aufgaben",
           "Offene Gefäße")
FIGURES_EN = ("Delivered in 2026", "Syntheses due", "Tasks", "Open vessels")


def figures(root: Element) -> dict[str, Element]:
    """The tiles of the page's figures strip by the text of their
    label (``.figure-tile__label``), in page order."""
    found = {}
    for each in tiles(root):
        label = each.find(cls="figure-tile__label")
        assert label is not None, f"a tile has no label: {each.text()!r}"
        found[label.text()] = each
    return found


def figure_values(root: Element) -> dict[str, str]:
    """The text of each tile of the strip without its label, by label."""
    return {label: tile_value(each, label)
            for label, each in figures(root).items()}


def hrefs(found: Element) -> list[str | None]:
    """The targets of the links inside ``found``, in page order."""
    return [a.get("href") for a in found.find_all("a")]


def stock_widget(root: Element, *titles: str) -> Element:
    """The page's widget of the stock, ``Bestand`` unless TITLES
    name it otherwise."""
    return widget(root, *(titles or ("Bestand", "Inventory")))


def hidden(found: Element) -> bool:
    """Whether ``found`` is marked ``aria-hidden``."""
    return found.get("aria-hidden") is not None


class OverviewCase(PlanningCase):

    def get(self, path: str = OVERVIEW, signed_in: bool = False) -> Any:
        return super().get(path, signed_in)

    def at_the_seventh(self) -> None:
        """Let the clock stand at 2026-11-07."""
        self.enterContext(ticking(berlin(2026, 11, 7, 9)))

    def scenario(self) -> None:
        """The books of scenario Figures and lists, for the seventh of
        November 2026."""
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
        reverse(self.kl, Movement.objects.get(delivery_note=note,
                                              kind="delivery"),
                note="Falsch gebucht")
        make_task(self.kl, substance="CH-0012", started=SEVENTH)
        make_task(self.kl, substance="CH-0010")
        make_task(self.kl, substance="Aspirin")
        self.vessel("CH-0012", "mg", "50")
