"""The figures the inventory computes: conversions between units, stock
levels, consumption per quarter with its means, and the containers bulk
would still fill."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from inventory.models import (BASE_UNIT, FACTOR, Batch, DeliveryLine,
                              EnteredConsumption, Item, Level, Movement,
                              Status, Unit, Vessel, shown)

MASS = (Unit.MG, Unit.G)
BASE_PLACES = Decimal("0.000001")

type Quarter = tuple[int, int]
type Number = Decimal | int | float


def convert(amount: Decimal, unit: str, to: str,
            molar_mass: Number | None) -> Decimal | None:
    """Return AMOUNT of UNIT in the unit TO, unrounded.

    Units of one kind, mass (``mg``, ``g``) or amount of substance
    (``umol``, ``mmol``), convert by their factors. Across the kinds,
    MOLAR_MASS in g/mol converts; return None when it is None or zero.
    """
    base = Decimal(amount) * FACTOR[unit]
    if (unit in MASS) != (to in MASS):
        if not molar_mass:
            return None
        mass = Decimal(str(molar_mass))
        base = base * 1000 / mass if unit in MASS else base * mass / 1000
    return base / FACTOR[to]


def to_base(amount: Decimal, unit: str) -> Decimal:
    """Return AMOUNT of UNIT in its base unit, mg or µmol, rounded half up
    to six places."""
    return (Decimal(amount) * FACTOR[unit]).quantize(BASE_PLACES,
                                                     ROUND_HALF_UP)


def molar_mass(item: Item) -> Decimal | None:
    """Return the molar mass in g/mol of ITEM's substance, or None when
    the substance has none."""
    return item.article.substance.mw


def proposed_amount(item: Item, count: int, vessel: Vessel
                    ) -> Decimal | None:
    """Return the amount COUNT containers of ITEM take from VESSEL, in
    the vessel's base unit, rounded half up to six places.

    Return None when the item's unit and the vessel's are of different
    kinds and the item's substance has no molar mass.
    """
    taken = convert(Decimal(count) * item.size, item.unit,
                    BASE_UNIT[vessel.unit], molar_mass(item))
    if taken is None:
        return None
    return taken.quantize(BASE_PLACES, ROUND_HALF_UP)


def level(quantity: int, mean_quarter: Number | None, *,
          status: str = Status.ACTIVE, consumed: bool = True,
          recent: bool = True) -> str:
    """Return the level of an item holding QUANTITY containers against
    its mean consumption per quarter MEAN_QUARTER.

    The level is ``dormant`` for an item whose STATUS sets it aside, or
    that has CONSUMED containers but none RECENT, in the current year or
    the one before; else ``undelivered`` for one that has consumed none;
    else ``out`` at zero; else, with a mean above zero, ``critical``
    below half the mean, ``low`` below the mean and ``watch`` below
    twice the mean; else ``ok``.
    """
    if status != Status.ACTIVE or (consumed and not recent):
        return Level.DORMANT
    if not consumed:
        return Level.UNDELIVERED
    if quantity == 0:
        return Level.OUT
    if mean_quarter:
        if quantity * 2 < mean_quarter:
            return Level.CRITICAL
        if quantity < mean_quarter:
            return Level.LOW
        if quantity < mean_quarter * 2:
            return Level.WATCH
    return Level.OK


def quarter_of(day: date) -> Quarter:
    """Return the year and the quarter, 1 to 4, of DAY."""
    return day.year, (day.month - 1) // 3 + 1


@dataclass(frozen=True)
class Consumption:
    """An item's consumption as of a day.

    ENTERED and DELIVERED map each quarter, a pair of year and quarter,
    to its entered value and to the containers its counting delivery
    lines hold; QUARTERS maps each quarter with either to their sum.
    MEAN_YEAR is the mean over the complete years before the day's,
    from the first year with data, and MEAN_QUARTER a quarter of it;
    both are None without such a year. For an item whose consumption
    above zero all lies in the day's year they are instead PROJECTED
    from that year. THIS_YEAR is the consumption of the day's year.
    COVERAGE is the quantity in quarters of the mean, None without a
    mean above zero and for a dormant or never-delivered item, and
    LEVEL is the item's level.
    """

    entered: dict[Quarter, int]
    delivered: dict[Quarter, int]
    quarters: dict[Quarter, int]
    mean_year: Decimal | None
    mean_quarter: Decimal | None
    this_year: int
    coverage: Decimal | None
    level: str
    projected: bool = False

    def total(self, quarter: Quarter) -> int:
        """Return the consumption of QUARTER, zero without data."""
        return self.quarters.get(quarter, 0)


def entered_by_item(items: Iterable[Item] | None = None
                    ) -> dict[int, dict[Quarter, int]]:
    """Return entered quarterly consumption mapped by item ID, for ITEMS
    or for every item when ITEMS is None."""
    rows = EnteredConsumption.objects.all()
    if items is not None:
        ids = [item.pk for item in items]
        if not ids:
            return {}
        rows = rows.filter(item_id__in=ids)
    found: dict[int, dict[Quarter, int]] = {}
    for item_id, year, quarter, count in rows.values_list(
            "item_id", "year", "quarter", "count"):
        found.setdefault(item_id, {})[(year, quarter)] = count
    return found


def counted_lines(item: Item | None = None,
                  items: Iterable[Item] | None = None
                  ) -> list[DeliveryLine]:
    """Return the delivery lines of ITEM, of ITEMS, or of every item when
    both are None, that count as consumption: those of current notes
    whose own delivery movement is not reversed, and those of historical
    notes that are not reversed.

    A line is matched to its delivery by note, item and batch, so that
    the reversal of one line leaves the note's other lines of the item in
    the result.
    """
    movements = Movement.objects.filter(kind=Movement.Kind.DELIVERY,
                                        reversal__isnull=False)
    lines = DeliveryLine.objects.select_related(
        "delivery_note", "item__article__substance")
    if item is not None:
        movements = movements.filter(item=item)
        lines = lines.filter(item=item)
    elif items is not None:
        ids = [each.pk for each in items]
        if not ids:
            return []
        movements = movements.filter(item_id__in=ids)
        lines = lines.filter(item_id__in=ids)
    reversed_lines = set(movements.values_list(
        "item_id", "delivery_note_id", "batch_id"))
    return [line for line in lines
            if not (line.delivery_note.historical
                    and line.delivery_note.reversed)
            and (line.item_id, line.delivery_note_id, line.batch_id)
            not in reversed_lines]


@dataclass(frozen=True)
class ConsumptionBatch:
    """Preloaded entered consumption and counted delivery lines indexed
    by item ID, so repeated consumption and rhythm lookups issue no
    further queries."""

    entered: dict[int, dict[Quarter, int]]
    lines: dict[int, list[DeliveryLine]]
    all_lines: list[DeliveryLine]

    @classmethod
    def load(cls, items: Iterable[Item] | None = None
             ) -> "ConsumptionBatch":
        """Load entered consumption and counted delivery lines for ITEMS,
        or for every item when ITEMS is None."""
        entered = entered_by_item(items)
        all_lines = counted_lines(items=items)
        by_item: dict[int, list[DeliveryLine]] = {}
        for line in all_lines:
            by_item.setdefault(line.item_id, []).append(line)
        return cls(entered=entered, lines=by_item, all_lines=all_lines)

    def consumption(self, item: Item, today: date) -> Consumption:
        """Return the consumption of ITEM as of TODAY from the preloaded
        data."""
        delivered: dict[Quarter, int] = {}
        for line in self.lines.get(item.pk, ()):
            key = quarter_of(line.delivery_note.date)
            delivered[key] = delivered.get(key, 0) + line.count
        return figures_of(item.quantity, self.entered.get(item.pk, {}),
                          delivered, today, item.status)


def vessels_by_substance(vessels: Iterable[Vessel]
                         ) -> dict[int, list[Vessel]]:
    """Group VESSELS by their batch's substance ID, preserving order."""
    grouped: dict[int, list[Vessel]] = {}
    for vessel in vessels:
        grouped.setdefault(vessel.batch.substance_id, []).append(vessel)
    return grouped


# The days of a quarter, in ten-thousandths, so that a projection
# divides whole numbers once.
QUARTER_DAYS = 913125
SCALE = 10000


def quarter_start(quarter: Quarter) -> date:
    """Return the first day of QUARTER."""
    year, number = quarter
    return date(year, 3 * (number - 1) + 1, 1)


def figures_of(quantity: int, entered: dict[Quarter, int],
               delivered: dict[Quarter, int], today: date,
               status: str = Status.ACTIVE) -> Consumption:
    """Return the consumption of an item holding QUANTITY containers,
    given its ENTERED values and DELIVERED containers per quarter and
    its STATUS, as of TODAY.

    An item whose consumption above zero all lies in TODAY's year has
    projected means: that year's consumption times 91.3125 divided by
    the days from the first day of the quarter of its first consumption
    above zero to TODAY, TODAY included, or by 91.3125 when that is
    fewer.
    """
    quarters = {key: entered.get(key, 0) + delivered.get(key, 0)
                for key in sorted({*entered, *delivered})}
    used = [key for key, count in quarters.items() if count > 0]
    this_year = sum(count for (year, _), count in quarters.items()
                    if year == today.year)
    years = range(min((year for year, _ in quarters), default=today.year),
                  today.year)
    mean_year = mean_quarter = coverage = None
    projected = bool(used) and all(year == today.year for year, _ in used)
    # Each figure divides whole numbers once, so that one that
    # terminates, such as a coverage of 2.25, is exact and rounds as it
    # should.
    if projected:
        days = (today - quarter_start(min(used))).days + 1
        span = max(days * SCALE, QUARTER_DAYS)
        mean_quarter = Decimal(this_year * QUARTER_DAYS) / span
        mean_year = Decimal(4 * this_year * QUARTER_DAYS) / span
        coverage = Decimal(quantity * span) / (this_year * QUARTER_DAYS)
    elif years:
        total = sum(count for (year, _), count in quarters.items()
                    if year in years)
        mean_year = Decimal(total) / len(years)
        mean_quarter = Decimal(total) / (4 * len(years))
        if total:
            coverage = Decimal(quantity * 4 * len(years)) / total
    found = level(quantity, mean_quarter, status=status,
                  consumed=bool(used),
                  recent=any(year >= today.year - 1 for year, _ in used))
    if found in (Level.DORMANT, Level.UNDELIVERED):
        coverage = None
    return Consumption(
        entered=entered, delivered=delivered, quarters=quarters,
        mean_year=mean_year, mean_quarter=mean_quarter,
        this_year=this_year, coverage=coverage, level=found,
        projected=projected)


def consumption(item: Item, today: date) -> Consumption:
    """Return the consumption of ITEM as of TODAY, with its quantity as
    the item holds it."""
    entered = dict(((row.year, row.quarter), row.count) for row in
                   EnteredConsumption.objects.filter(item=item))
    delivered: dict[Quarter, int] = {}
    for line in counted_lines(item):
        key = quarter_of(line.delivery_note.date)
        delivered[key] = delivered.get(key, 0) + line.count
    return figures_of(item.quantity, entered, delivered, today,
                      item.status)


@dataclass(frozen=True)
class Bulk:
    """The open vessels an item can be filled from.

    AMOUNTS pairs each unit the vessels are kept in with their summed
    amount in it, rounded half up to three places. CONTAINERS is the
    number of the item's containers the vessels that convert would
    still fill, counted vessel by vessel; UNCONVERTIBLE counts the
    vessels that do not convert into the item's unit. VESSELS are the
    vessels.
    """

    vessels: list[Vessel] = field(default_factory=list)
    amounts: list[tuple[Decimal, str]] = field(default_factory=list)
    containers: int = 0
    unconvertible: int = 0


def containers_from(vessel: Vessel, item: Item, mass: Number | None
                    ) -> int | None:
    """Return the number of ITEM's containers VESSEL would still fill,
    with MASS the molar mass of the item's substance; None when the
    vessel does not convert into the item's unit."""
    converted = convert(vessel.amount, BASE_UNIT[vessel.unit], item.unit,
                        mass)
    if converted is None:
        return None
    return int((converted / item.size).to_integral_value(ROUND_FLOOR))


def bulk(item: Item, vessels: Iterable[Vessel]) -> Bulk:
    """Return the bulk of ITEM among VESSELS: the open vessels of its
    substance, flasks among them. Each vessel's batch is read."""
    mine = [vessel for vessel in vessels
            if vessel.amount > 0
            and vessel.batch.substance_id == item.article_id]
    if not mine:
        return Bulk()
    mass = molar_mass(item)
    totals: dict[str, Decimal] = {}
    containers = unconvertible = 0
    for vessel in mine:
        totals[vessel.unit] = totals.get(vessel.unit, Decimal(0)) \
            + vessel.amount
        filled = containers_from(vessel, item, mass)
        if filled is None:
            unconvertible += 1
        else:
            containers += filled
    return Bulk(vessels=mine,
                amounts=[(shown(amount, unit), str(Unit(unit).label))
                         for unit, amount in totals.items()],
                containers=containers, unconvertible=unconvertible)


def stock_of(vessels: Iterable[Vessel]) -> list[tuple[Decimal, str]]:
    """Return the amount in the open VESSELS, those holding an amount
    above zero, each unit they are kept in with the summed amount in it,
    rounded half up to three places, and the unit as it is shown."""
    totals: dict[str, Decimal] = {}
    for vessel in vessels:
        if vessel.amount > 0:
            totals[vessel.unit] = totals.get(vessel.unit, Decimal(0)) \
                + vessel.amount
    return [(shown(amount, unit), str(Unit(unit).label))
            for unit, amount in totals.items()]


def newest_first(batches: Iterable[Batch]) -> list[Batch]:
    """Return BATCHES ordered by date, newest first and undated ones
    last, then by ID, newest first."""
    return sorted(batches, key=lambda batch: (
        batch.date is None,
        -(batch.date.toordinal() if batch.date else 0), -batch.pk))


def open_amounts(batches: Iterable[Batch]
                 ) -> dict[int, list[tuple[Decimal, str]]]:
    """Return, for each batch of BATCHES by its ID, the amount in its
    open vessels by unit as ``stock_of`` gives it; a batch without an
    open vessel maps to an empty list."""
    held: dict[int, list[Vessel]] = {batch.pk: [] for batch in batches}
    for vessel in Vessel.objects.filter(batch_id__in=held, amount__gt=0
                                        ).order_by("id"):
        held[vessel.batch_id].append(vessel)
    return {pk: stock_of(vessels) for pk, vessels in held.items()}
