"""The production plan as the database gives it: which tasks belong to
which articles, each article's forecast, and the priority of each task.

Planning works on the articles that have an article number, each the
items of one substance; a task belongs to the article of its substance.
``Plan`` reads the records once and keeps each article's forecast, so a
page asks one plan for every figure it shows.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from typing import Any, NamedTuple
from urllib.parse import urlencode

from django.db.models import Q

from inventory.figures import (Consumption, bulk, consumption, convert,
                               counted_lines, figures_of, molar_mass,
                               quarter_of)
from inventory.models import (BASE_UNIT, Article, EnteredConsumption, Item,
                              Level, Lot, Unit)
from planning import forecast
from planning.forecast import Model, Rhythm
from planning.models import Parameters
from tasks.models import Priority, State, Task

ACTIVE = (State.PLANNED, State.RUNNING)
# The levels of the items planning leaves out: they have no demand.
UNPLANNED = (Level.DORMANT, Level.UNDELIVERED)


class TaskPriority(NamedTuple):
    """A task's priority as the application uses it.

    PRIORITY is a value of ``tasks.models.Priority``. COMPUTED tells
    whether it follows from the task's SLACK in days, which is None for
    a task whose priority is the one entered.
    """

    priority: str
    computed: bool
    slack: float | None

    @property
    def label(self) -> str:
        """The priority as the active language names it."""
        return str(Priority(self.priority).label)


def latest_start(today: date, slack: float) -> date | None:
    """Return TODAY plus SLACK in whole days, rounded down, or None when
    that date lies beyond the calendar's last."""
    try:
        return today + timedelta(days=math.floor(slack))
    except OverflowError:
        return None


@dataclass(frozen=True)
class ItemForecast:
    """An item of an article with its forecast.

    MODEL is its demand model, None without demand; RUNWAY_ON_HAND the
    days its quantity lasts at the certainty, None without demand; SIZE
    its container size in the article's bulk unit, None when it does not
    convert. FIGURES is its consumption, RHYTHM its delivery rhythm, and
    FILL whether filling it from bulk is due: its runway on hand is
    below the buffer and the open lots would fill at least one of its
    containers.
    """

    item: Item
    model: Model | None
    runway_on_hand: float | None
    size: Decimal | None
    figures: Consumption
    rhythm: Rhythm
    fill: bool

    @property
    def per_year(self) -> Decimal | None:
        """The demand per year in containers, rounded half up to one
        place; None without demand."""
        if self.model is None:
            return None
        return Decimal(str(self.model.per_year)).quantize(
            Decimal("0.1"), ROUND_HALF_UP)


@dataclass(frozen=True)
class ArticleForecast:
    """The forecast of an article that has demand.

    SUBSTANCE is the article's substance and NAME its name; ITEMS are
    all its items in the item list's order. BULK_UNIT is the unit its
    bulk is counted in, USABLE_BULK what its open lots that convert can fill in whole containers, and
    UNCONVERTIBLE whether an open lot does not convert. CERTAINTY is
    the one each item with demand is planned at. RUNWAY, SLACK and
    LATEST_START follow from those and from SYNTHESIS_DAYS, the longest
    of the last BASIS_COUNT syntheses or, with BASIS_COUNT None, the
    default. YIELD_AMOUNT is what a new synthesis must yield in the bulk
    unit, None when no item with demand converts, and YIELD_MG the same
    in mg when the bulk unit is µmol; LACKING maps the ID of each item
    with demand that does not convert to the containers it lacks. ROUGH
    tells whether any figure comes from the quarterly model.
    """

    article_number: str
    substance: Any
    name: str
    items: list[ItemForecast]
    parameters: Parameters
    bulk_unit: str
    usable_bulk: Decimal
    unconvertible: bool
    certainty: float
    runway: float
    synthesis_days: int
    basis_count: int | None
    slack: float
    latest_start: date | None
    priority: str
    yield_days: int
    yield_amount: Decimal | None
    yield_mg: int | None
    lacking: dict[int, int]
    rough: bool

    @property
    def priority_label(self) -> str:
        """The priority as the active language names it."""
        return str(Priority(self.priority).label)

    @property
    def bulk_unit_label(self) -> str:
        """The bulk unit as it is shown, such as ``µmol``."""
        return str(Unit(self.bulk_unit).label)

    @property
    def last_delivery(self) -> date | None:
        """The latest date of the counted deliveries of its items, or
        None."""
        return max((entry.rhythm.last for entry in self.items
                    if entry.rhythm.last), default=None)

    @property
    def demand_count(self) -> int:
        """The number of its items with demand."""
        return sum(entry.model is not None for entry in self.items)

    @property
    def lacking_items(self) -> list[tuple[Item, int]]:
        """The items of LACKING with the containers each lacks, in the
        item list's order."""
        return [(entry.item, self.lacking[entry.item.pk])
                for entry in self.items if entry.item.pk in self.lacking]

    def entry(self, item: Item) -> ItemForecast | None:
        """Return the forecast of ITEM among its items, or None."""
        return next((entry for entry in self.items
                     if entry.item.pk == item.pk), None)


@dataclass(frozen=True)
class TaskLine:
    """A planned or running task of an article: when it is expected to
    end, today plus its REMAINING days, and whether it is LATE, its
    slack being below zero."""

    task: Task
    remaining: int
    end: date
    late: bool


@dataclass(frozen=True)
class Row:
    """An article of the planning list with its TASKS and the actions
    due: the items to FILL, whether to CHECK_BULK, and whether to
    PLAN_SYNTHESIS. LISTED tells whether the list shows it without
    ``all=1``."""

    forecast: ArticleForecast
    tasks: list[TaskLine]
    fill: list[Item]
    check_bulk: bool
    plan_synthesis: bool

    @property
    def listed(self) -> bool:
        """Whether its priority is high or medium or an action is due."""
        return (self.forecast.priority in (Priority.HIGH, Priority.MEDIUM)
                or bool(self.fill) or self.check_bulk)


@dataclass(frozen=True)
class ArticleLine:
    """An article a task matches, with its forecast, None without
    demand."""

    article_number: str
    forecast: ArticleForecast | None


class Plan:
    """The forecasts as of TODAY under PARAMETERS, the current ones by
    default.

    The records are read when first needed and kept, as is each
    article's forecast; a plan reflects the database as it was then.
    """

    def __init__(self, today: date,
                 parameters: Parameters | None = None) -> None:
        self.today = today
        self.parameters = parameters or Parameters.current()
        self._forecasts: dict[str, ArticleForecast | None] = {}

    @cached_property
    def items(self) -> dict[str, list[Item]]:
        """The items whose article has an article number, by article
        number, each in the item list's order."""
        found: dict[str, list[Item]] = {}
        for item in sorted(Item.objects.filter(
                article__article_number__isnull=False).select_related(
                    "article__substance"), key=Item.sort_key):
            found.setdefault(item.article_number, []).append(item)
        return found

    @cached_property
    def numbers(self) -> dict[int, str]:
        """The article numbers of the numbered articles, with items or
        without, by the ID of their substance."""
        return dict(Article.objects.filter(
            article_number__isnull=False).values_list("pk",
                                                      "article_number"))

    @cached_property
    def lots(self) -> list[Lot]:
        """The open lots."""
        return list(Lot.objects.filter(amount__gt=0))

    @cached_property
    def tasks(self) -> list[Task]:
        """Every task."""
        return list(Task.objects.select_related("substance"))

    def matches(self, task: Task, article_number: str) -> bool:
        """Whether TASK names the substance of the article
        ARTICLE_NUMBER."""
        return self.numbers.get(task.substance_id) == article_number

    def matching(self, task: Task) -> list[str]:
        """Return the article numbers TASK matches: that of its
        substance's article, when it has a number, or none."""
        number = self.numbers.get(task.substance_id)
        return [] if number is None else [number]

    def forecasts(self) -> list[ArticleForecast]:
        """Return the forecast of every article that has one, by article
        number."""
        return [found for found in map(self.forecast, sorted(self.items))
                if found is not None]

    def forecast(self, article_number: str) -> ArticleForecast | None:
        """Return the forecast of ARTICLE_NUMBER, None when none of its
        items has demand or it has none."""
        if article_number not in self._forecasts:
            self._forecasts[article_number] = self._forecast(article_number)
        return self._forecasts[article_number]

    def _forecast(self, article_number: str) -> ArticleForecast | None:
        """Return the forecast of ARTICLE_NUMBER, read afresh."""
        items = self.items.get(article_number, [])
        if not items:
            return None
        settings = self.parameters
        planned = [item for item in items if consumption(
            item, self.today).level not in UNPLANNED]
        if not planned:
            return None
        mass = molar_mass(items[0])
        unit = Unit.UMOL if mass else BASE_UNIT[planned[0].unit]
        lots = [lot for lot in self.lots
                if lot.substance_id == items[0].article_id]
        entries = [self._item(item, unit, mass) for item in items]
        held = [entry for entry in entries if entry.model is not None]
        if not held:
            return None
        largest = max((entry.size for entry in held
                       if entry.size is not None), default=Decimal(0))
        converted = [convert(lot.amount, BASE_UNIT[lot.unit], unit, mass)
                     for lot in lots]
        usable = forecast.usable_bulk(
            [amount for amount in converted if amount is not None],
            largest)
        holdings = [(entry.model, entry.item.quantity, entry.size)
                    for entry in entries]
        runway = forecast.article_runway(holdings, usable,
                                         settings.certainty)
        days, basis = forecast.synthesis_time(
            self._durations(article_number),
            settings.default_synthesis_days)
        slack = runway - settings.buffer_days - days
        each = forecast.joint_certainty(settings.certainty, len(held))
        horizon = days + settings.buffer_days + settings.target_days
        produced, mg = self._yield(held, horizon, each, usable, unit, mass)
        return ArticleForecast(
            article_number=article_number,
            substance=items[0].article.substance, name=items[0].name,
            items=entries,
            parameters=settings, bulk_unit=unit, usable_bulk=usable,
            unconvertible=any(amount is None for amount in converted),
            certainty=each, runway=runway, synthesis_days=days,
            basis_count=basis, slack=slack,
            latest_start=latest_start(self.today, slack),
            priority=forecast.priority(slack, settings.high_days,
                                       settings.medium_days),
            yield_days=horizon, yield_amount=produced, yield_mg=mg,
            lacking={entry.item.pk: forecast.lacking(
                entry.model, entry.item.quantity, horizon, each)
                for entry in held if entry.size is None},
            rough=any(entry.model.rough for entry in held))

    @staticmethod
    def _yield(held: list[ItemForecast], horizon: int, each: float,
               usable: Decimal, unit: str, mass: Decimal | None
               ) -> tuple[Decimal | None, int | None]:
        """Return what a new synthesis must yield for the items HELD, all
        with demand, to last HORIZON days at the certainty EACH, beyond
        their containers and the USABLE bulk: in UNIT, rounded up to a
        whole number, and in mg, rounded up, when UNIT is µmol and MASS,
        the molar mass, converts. Either is None when it cannot be
        given, the first when no item of HELD converts."""
        filled = [entry for entry in held if entry.size is not None]
        if not filled:
            return None, None
        exact = max(Decimal(0), sum(
            (forecast.lacking(entry.model, entry.item.quantity, horizon,
                              each) * entry.size for entry in filled),
            Decimal(0)) - usable)
        mg = None
        if unit == Unit.UMOL and mass:
            mg = int(forecast.whole(convert(exact, Unit.UMOL, Unit.MG,
                                            mass)))
        return forecast.whole(exact), mg

    def _item(self, item: Item, unit: str, mass: Decimal | None
              ) -> ItemForecast:
        """Return the forecast of ITEM with its size in UNIT, MASS being
        the molar mass of its substance; a dormant or never-delivered
        item has no demand model."""
        entered = {(row.year, row.quarter): row.count for row in
                   EnteredConsumption.objects.filter(item=item)}
        orders = [(line.delivery_note.date, line.count)
                  for line in counted_lines(item)]
        delivered: dict[tuple[int, int], int] = {}
        for day, count in orders:
            delivered[quarter_of(day)] = delivered.get(
                quarter_of(day), 0) + count
        figures = figures_of(item.quantity, entered, delivered,
                             self.today, item.status)
        model = None if figures.level in UNPLANNED else forecast.demand(
            entered, orders, self.today, self.parameters)
        on_hand = None if model is None else model.runway(
            item.quantity, self.parameters.certainty)
        return ItemForecast(
            item=item, model=model, runway_on_hand=on_hand,
            size=convert(item.size, item.unit, unit, mass),
            figures=figures,
            rhythm=forecast.rhythm([day for day, _ in orders], self.today),
            fill=(on_hand is not None
                  and on_hand < self.parameters.buffer_days
                  and bulk(item, self.lots).containers > 0))

    def _durations(self, article_number: str) -> list[int]:
        """Return the durations in days of the ended tasks that match
        ARTICLE_NUMBER and are neither cancelled nor failed, each at
        least 1, ordered by end date, then start date, then number."""
        ended = sorted(
            (task for task in self.tasks
             if task.state == State.ENDED and task.started
             and self.matches(task, article_number)),
            key=lambda task: (task.ended, task.started, task.serial))
        return [max(1, (task.ended - task.started).days)
                for task in ended]

    def remaining(self, task: Task, found: ArticleForecast) -> int:
        """Return the days TASK still needs of the synthesis time of
        FOUND: all of it while planned, less the days since its start
        while running, at least zero."""
        if task.started is None:
            return found.synthesis_days
        return max(0, found.synthesis_days
                   - (self.today - task.started).days)

    def task_slack(self, task: Task) -> float | None:
        """Return the slack of TASK in days, None unless it is planned or
        running and matches an article with a forecast: the smallest,
        over those articles, of the runway less the buffer less its
        remaining time."""
        if task.state not in ACTIVE:
            return None
        slacks = [found.runway - self.parameters.buffer_days
                  - self.remaining(task, found)
                  for found in map(self.forecast, self.matching(task))
                  if found is not None]
        return min(slacks, default=None)

    def task_priority(self, task: Task) -> TaskPriority:
        """Return the priority of TASK: computed from its slack when it
        has one, else the one entered."""
        slack = self.task_slack(task)
        if slack is None:
            return TaskPriority(task.priority, False, None)
        return TaskPriority(
            forecast.priority(slack, self.parameters.high_days,
                              self.parameters.medium_days), True, slack)

    def task_lines(self, found: ArticleForecast) -> list[TaskLine]:
        """Return the planned and running tasks that match the article of
        FOUND, running first, then by number."""
        active = sorted(
            (task for task in self.tasks if task.state in ACTIVE
             and self.matches(task, found.article_number)),
            key=lambda task: (task.state != State.RUNNING, task.serial))
        lines = []
        for task in active:
            remaining = self.remaining(task, found)
            slack = self.task_slack(task)
            lines.append(TaskLine(
                task=task, remaining=remaining,
                end=self.today + timedelta(days=remaining),
                late=slack is not None and slack < 0))
        return lines

    def row(self, found: ArticleForecast) -> Row:
        """Return the planning list's row of FOUND."""
        tasks = self.task_lines(found)
        return Row(
            forecast=found, tasks=tasks,
            fill=[entry.item for entry in found.items if entry.fill],
            check_bulk=found.unconvertible,
            plan_synthesis=(found.priority in (Priority.HIGH,
                                               Priority.MEDIUM)
                            and not tasks and not found.unconvertible))

    def articles_of(self, task: Task) -> list[ArticleLine]:
        """Return the articles TASK matches, each with its forecast."""
        return [ArticleLine(number, self.forecast(number))
                for number in self.matching(task)]


def article(article_number: str, today: date) -> ArticleForecast | None:
    """Return the forecast of ARTICLE_NUMBER as of TODAY under the
    current parameters, None when none of its items has demand or it has
    no item."""
    return Plan(today).forecast(article_number)


def task_priority(task: Task, today: date) -> TaskPriority:
    """Return the priority of TASK as of TODAY under the current
    parameters: computed from its slack when it is planned or running
    and matches an article with a forecast, else the one entered."""
    return Plan(today).task_priority(task)


def batch_lots(task: Task) -> list[Lot]:
    """Return the lots that belong to TASK, each once, in the order of
    their IDs: those of its substance with its batch, when it has one,
    and those a step of TASK made, whatever their substance and
    batch."""
    belongs = Q(task_step__task=task)
    if task.batch:
        belongs |= Q(batch=task.batch, substance_id=task.substance_id)
    return list(Lot.objects.filter(belongs).select_related("substance")
                .order_by("id"))


def batch_tasks(lot: Lot) -> list[Task]:
    """Return the tasks that belong to LOT, each once, by number: those
    of its substance with its batch, when it has one, and the task of
    the step that made it."""
    belongs = Q(pk__in=[]) if lot.task_step_id is None else Q(
        steps=lot.task_step_id)
    if lot.batch:
        belongs |= Q(batch=lot.batch, substance_id=lot.substance_id)
    return sorted(Task.objects.filter(belongs).distinct(),
                  key=lambda task: task.serial)


def bulk_link(task: Task) -> str | None:
    """Return the path of the new-lot form filled in from TASK, or None.

    The form is filled in when TASK is ended, neither cancelled nor
    failed, and has a batch: with its substance's key, the batch, and
    the end date.
    """
    if task.state != State.ENDED or not task.batch:
        return None
    return "/lab/inventory/bulk/new/?" + urlencode({
        "substance": task.substance.key, "batch": task.batch,
        "made_on": task.ended.isoformat()})
