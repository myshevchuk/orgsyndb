"""The overview's figures, computed from the delivery lines that count as
consumption, the items, the forecasts and the tasks."""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from inventory.figures import consumption, counted_lines
from inventory.models import DeliveryNote, Item, Level, Lot
from planning.plan import ArticleForecast, Plan, TaskLine
from tasks.models import Priority, State

type Month = tuple[int, int]

# How many entries each list of the overview shows.
SHOWN = 5


@dataclass(frozen=True)
class Delivered:
    """Containers that went out: COUNT of ITEM on DAY to RECIPIENT, from
    a delivery line that counts as consumption."""

    day: date
    item: Item
    recipient: str
    count: int


def delivered() -> list[Delivered]:
    """Return every delivery that counts as consumption, dated by its
    note."""
    return [Delivered(day=line.delivery_note.date, item=line.item,
                      recipient=line.delivery_note.recipient.strip(),
                      count=line.count)
            for line in counted_lines()]


def a_year_before(day: date) -> date:
    """Return the same day a year before DAY, 28 February for 29
    February."""
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return day.replace(year=day.year - 1, day=28)


def total(deliveries: list[Delivered], start: date, end: date) -> int:
    """Return the containers of DELIVERIES from START through END."""
    return sum(each.count for each in deliveries if start <= each.day <= end)


def months_ending(today: date, count: int = 12) -> list[Month]:
    """Return the COUNT months ending with the month of TODAY, oldest
    first, each as its year and month."""
    index = today.year * 12 + today.month - 1
    return [(number // 12, number % 12 + 1)
            for number in range(index - count + 1, index + 1)]


def per_month(deliveries: list[Delivered], months: list[Month]
              ) -> list[int]:
    """Return the containers of DELIVERIES in each of MONTHS."""
    counts: Counter[Month] = Counter()
    for each in deliveries:
        counts[each.day.year, each.day.month] += each.count
    return [counts[month] for month in months]


@dataclass(frozen=True)
class Requested:
    """An article with the first of its items in the item list's order
    and the containers delivered of it."""

    article_number: str
    item: Item
    count: int


def most_requested(deliveries: list[Delivered], year: int,
                   items: list[Item]) -> list[Requested]:
    """Return the articles with the most containers delivered in YEAR,
    most first, then by article number, at most ``SHOWN``; ITEMS are
    all items in the item list's order."""
    counts: Counter[str] = Counter()
    for each in deliveries:
        if each.day.year == year and each.item.article_number:
            counts[each.item.article_number] += each.count
    first: dict[str, Item] = {}
    for item in items:
        if item.article_number:
            first.setdefault(item.article_number, item)
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [Requested(number, first[number], count)
            for number, count in ranked[:SHOWN]]


def recipients(deliveries: list[Delivered], year: int
               ) -> list[tuple[str, int]]:
    """Return the recipients of the most containers delivered in YEAR,
    most first, then by recipient regardless of case, at most ``SHOWN``;
    deliveries without a recipient are left out."""
    counts: Counter[str] = Counter()
    for each in deliveries:
        if each.day.year == year and each.recipient:
            counts[each.recipient] += each.count
    return sorted(counts.items(),
                  key=lambda pair: (-pair[1], pair[0].casefold()))[:SHOWN]


@dataclass(frozen=True)
class LatestNote:
    """A delivery note with the containers of its lines."""

    note: DeliveryNote
    count: int


def latest_notes() -> list[LatestNote]:
    """Return the first ``SHOWN`` notes of the delivery list, each with
    the containers of its lines."""
    notes = DeliveryNote.objects.prefetch_related("lines").order_by(
        *DeliveryNote._meta.ordering)[:SHOWN]
    return [LatestNote(note, sum(line.count for line in note.lines.all()))
            for note in notes]


@dataclass(frozen=True)
class StockPart:
    """A level at which COUNT items stand, with its LABEL."""

    level: str
    label: str
    count: int


def stock_parts(items: list[Item], today: date) -> list[StockPart]:
    """Return the levels at which ITEMS stand on TODAY, in urgency order,
    each with the number of items at it; levels without items are left
    out."""
    counts = Counter(consumption(item, today).level for item in items)
    return [StockPart(level, str(level.label), counts[level])
            for level in Level if counts[level]]


@dataclass(frozen=True)
class NextSynthesis:
    """An article with a forecast, the first of its items, and its first
    planned or running task, None without one."""

    forecast: ArticleForecast
    item: Item
    task: TaskLine | None

    @property
    def state(self) -> str:
        """The state of its task as the active language names it, empty
        without a task."""
        return str(State(self.task.task.state).label) if self.task else ""


@dataclass(frozen=True)
class Summary:
    """The overview's summary on TODAY: the stock's PARTS and the number
    of ITEMS; the containers delivered this year and last year through
    the same day, LAST_YEAR_END; the articles whose priority is high or
    medium, the planned and running tasks that are LATE; the RUNNING and
    PLANNED tasks; and the open LOTS."""

    today: date
    parts: list[StockPart]
    items: int
    this_year: int
    last_year: int
    last_year_end: date
    due: int
    late: int
    running: int
    planned: int
    lots: int


def summary(today: date, plan: Plan, items: list[Item],
            deliveries: list[Delivered]) -> Summary:
    """Return the summary on TODAY of ITEMS, every item, of DELIVERIES
    and of what PLAN holds; the open lots counted are those of any
    substance."""
    end = a_year_before(today)
    states = Counter(task.state for task in plan.tasks)
    late = [task for task in plan.tasks
            if (slack := plan.task_slack(task)) is not None and slack < 0]
    return Summary(
        today=today, parts=stock_parts(items, today), items=len(items),
        this_year=total(deliveries, date(today.year, 1, 1), today),
        last_year=total(deliveries, date(end.year, 1, 1), end),
        last_year_end=end,
        due=sum(found.priority in (Priority.HIGH, Priority.MEDIUM)
                for found in plan.forecasts()),
        late=len(late), running=states[State.RUNNING],
        planned=states[State.PLANNED],
        lots=Lot.objects.filter(amount__gt=0).count())


def next_syntheses(plan: Plan) -> list[NextSynthesis]:
    """Return the ``SHOWN`` articles with a forecast of the smallest
    slack, in the planning list's order."""
    ranked = sorted(plan.forecasts(),
                    key=lambda found: (found.slack, found.article_number))
    found = []
    for forecast in ranked[:SHOWN]:
        tasks = plan.task_lines(forecast)
        found.append(NextSynthesis(forecast, forecast.items[0].item,
                                   tasks[0] if tasks else None))
    return found


def end_products() -> list[Item]:
    """Return every item in the item list's order."""
    return sorted(Item.objects.select_related("article__substance"),
                  key=Item.sort_key)
