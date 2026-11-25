"""Pure summaries and age calculations for the stock lists by substance."""

import calendar
import itertools
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from inventory.models import Unit, Vessel, shown

# Units in the order the substance rows display summed amounts.
UNIT_ORDER = (Unit.MG, Unit.G, Unit.UMOL, Unit.MMOL)


def natural(text: str) -> tuple[Any, ...]:
    """Return the sort key of TEXT among locations: runs of ASCII digits
    by numeric value, the rest casefolded."""
    return tuple(int(part) if odd else part.casefold()
                 for odd, part in zip(itertools.cycle((False, True)),
                                      re.split(r"([0-9]+)", text)))


def months_between(start: date, today: date) -> int:
    """Return the whole calendar months from START to TODAY.

    A month is complete on the same day of the month, or on the last day
    of a shorter month. Return 0 when TODAY is before START.
    """
    if today < start:
        return 0
    months = (today.year - start.year) * 12 + (today.month - start.month)
    last_day = calendar.monthrange(today.year, today.month)[1]
    if today.day < min(start.day, last_day):
        months -= 1
    return max(0, months)


def is_old(start: date, today: date) -> bool:
    """Return whether START is at least twelve whole calendar months
    before TODAY."""
    return months_between(start, today) >= 12


def age_label(start: date, today: date) -> str:
    """Return the age from START to TODAY in the active language:
    ``today``, ``1 day`` / ``<n> days`` below one month, ``<n> mo.``
    below twelve months, and ``<y> y`` or ``<y> y <m> mo.`` from twelve
    months."""
    months = months_between(start, today)
    if months == 0:
        days = max(0, (today - start).days)
        if days == 0:
            return _("today")
        return ngettext("%(count)s day", "%(count)s days", days) % {
            "count": days}
    if months < 12:
        return _("%(months)s mo.") % {"months": months}
    years, rest = divmod(months, 12)
    if rest == 0:
        return _("%(years)s y") % {"years": years}
    return _("%(years)s y %(months)s mo.") % {"years": years, "months": rest}


def amounts_by_unit(vessels: Iterable[Vessel]) -> list[tuple[Decimal, str]]:
    """Return the amounts of VESSELS summed per unit, in the order
    ``mg``, ``g``, ``µmol``, ``mmol``, each rounded half up to three
    places with its unit label."""
    totals: dict[str, Decimal] = {}
    for vessel in vessels:
        totals[vessel.unit] = totals.get(vessel.unit, Decimal(0)) \
            + vessel.amount
    return [(shown(totals[unit], unit), str(Unit(unit).label))
            for unit in UNIT_ORDER if unit in totals]


@dataclass(frozen=True)
class LocationSummary:
    """Summary of the locations of a substance's vessels: FIRST is the
    first stored location in natural order (``not recorded`` placed last),
    MORE is the count of other stored locations, and IN_FLASK tells
    whether flasks are among the vessels."""

    first: str
    more: int
    in_flask: bool


def location_summary(vessels: Iterable[Vessel], *, show_flask: bool = False
                     ) -> LocationSummary:
    """Return the location summary of VESSELS.

    Stored vessels' distinct locations are ordered naturally with
    unrecorded locations last as ``not recorded``. Flasks' own locations
    are ignored; IN_FLASK is set when SHOW_FLASK is true and any vessel
    is a flask.
    """
    listed = list(vessels)
    stored = [vessel for vessel in listed if not vessel.flask]
    named = sorted({vessel.location for vessel in stored if vessel.location},
                   key=natural)
    unrecorded = any(not vessel.location for vessel in stored)
    all_locations = [*named, *([str(_("not recorded"))] if unrecorded else [])]
    return LocationSummary(
        first=all_locations[0] if all_locations else "",
        more=max(0, len(all_locations) - 1),
        in_flask=show_flask and any(vessel.flask for vessel in listed))


@dataclass(frozen=True)
class SourceSummary:
    """Summary of the task origins of an intermediate's vessels: up to
    two TASK_NUMBERS ordered by task serial, MORE other tasks, and
    NO_TASK when any vessel's batch was made without a task step."""

    task_numbers: list[str]
    more: int
    no_task: bool


def source_summary(vessels: Iterable[Vessel]) -> SourceSummary:
    """Return the task-origin summary of VESSELS."""
    tasks: dict[str, Any] = {}
    no_task = False
    for vessel in vessels:
        step = vessel.batch.task_step
        if step is None:
            no_task = True
        else:
            tasks[step.task.number] = step.task
    ordered = sorted(tasks.values(), key=lambda task: task.serial)
    return SourceSummary(
        task_numbers=[task.number for task in ordered[:2]],
        more=max(0, len(ordered) - 2),
        no_task=no_task)


@dataclass(frozen=True)
class AgeSummary:
    """Age cell of an intermediate row: TEXT is the newest-to-oldest age
    range or ``–`` when no batch has a date; OLD is true when the oldest
    batch is a year or more old."""

    text: str
    old: bool


def age_summary(vessels: Iterable[Vessel], today: date) -> AgeSummary:
    """Return the age summary of VESSELS as of TODAY."""
    dates = [vessel.batch.date for vessel in vessels
             if vessel.batch.date is not None]
    if not dates:
        return AgeSummary(text="–", old=False)
    newest = age_label(max(dates), today)
    oldest_date = min(dates)
    oldest = age_label(oldest_date, today)
    text = newest if newest == oldest else f"{newest} – {oldest}"
    return AgeSummary(text=text, old=is_old(oldest_date, today))


@dataclass(frozen=True)
class SupplierSummary:
    """Summary of the suppliers of a commercial chemical's vessels:
    FIRST is the first supplier case-insensitively (``unknown`` placed
    last), MORE is the count of other suppliers."""

    first: str
    more: int


def supplier_summary(vessels: Iterable[Vessel]) -> SupplierSummary:
    """Return the supplier summary of VESSELS."""
    listed = list(vessels)
    named = sorted({vessel.batch.supplier for vessel in listed
                    if vessel.batch.supplier}, key=str.casefold)
    unknown = any(not vessel.batch.supplier for vessel in listed)
    all_suppliers = [*named, *([str(_("unknown"))] if unknown else [])]
    return SupplierSummary(
        first=all_suppliers[0] if all_suppliers else "",
        more=max(0, len(all_suppliers) - 1))


def earliest_opened(vessels: Iterable[Vessel]) -> date | None:
    """Return the earliest ``opened_on`` date among VESSELS, or None
    when all are sealed."""
    dates = [vessel.opened_on for vessel in vessels
             if vessel.opened_on is not None]
    return min(dates) if dates else None
