"""The forecast of an item's demand and of how long its stock lasts.

Everything here works on plain values: quarters as pairs of year and
quarter, orders as pairs of date and count, amounts as decimals in one
unit. Days are calendar days and may be fractional; a certainty is a
probability between 0 and 1, exclusive.
"""

import math
import statistics
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal
from functools import cached_property
from typing import Protocol

from inventory.figures import quarter_of

type Quarter = tuple[int, int]
type Order = tuple[date, int]

# The mean length of a quarter in days, a quarter of 365.25.
QUARTER_DAYS = 91.3125
# The precision, in days, to which the order model finds a runway.
ORDER_PRECISION = 0.01
# The precision, in days, to which an article's runway is first bracketed
# before it is set to the runway of the containers it allots each item.
ARTICLE_PRECISION = 1e-6
# A stored probability above this is scaled down by it; see
# ``OrderModel.cdf``.
SCALE = 1e280


class Settings(Protocol):
    """The parameters that choose and estimate a demand model."""

    history_quarters: int
    min_orders: int


def z_of(certainty: float) -> float:
    """Return the quantile of the standard normal distribution at
    CERTAINTY."""
    return statistics.NormalDist().inv_cdf(certainty)


@dataclass(frozen=True)
class QuarterlyModel:
    """Demand approximated from quarterly totals.

    M is the mean consumption per quarter and V its variance, both in
    containers and V at least M; QUARTERS is the number of quarters
    they come from. Over H days the demand is taken as normal with mean
    ``μH`` and standard deviation ``σ√H``, where ``μ = M / 91.3125`` and
    ``σ² = V / 91.3125``. The figures it gives are rough.
    """

    m: float
    v: float
    quarters: int
    rough = True

    @property
    def per_year(self) -> float:
        """The demand per year in containers, four times M."""
        return 4 * self.m

    @property
    def mu(self) -> float:
        """The mean demand per day."""
        return self.m / QUARTER_DAYS

    @property
    def sigma(self) -> float:
        """The standard deviation of the demand of one day."""
        return math.sqrt(self.v / QUARTER_DAYS)

    def need(self, days: float, certainty: float) -> float:
        """Return the containers needed to last DAYS at CERTAINTY,
        ``μH + zσ√H``; zero for no days."""
        if days <= 0:
            return 0
        return (self.mu * days
                + z_of(certainty) * self.sigma * math.sqrt(days))

    def runway(self, stock: float, certainty: float) -> float:
        """Return the days STOCK containers last at CERTAINTY, the H whose
        need is STOCK; zero for no stock."""
        if stock <= 0:
            return 0
        spread = z_of(certainty) * self.sigma
        root = (-spread + math.sqrt(spread ** 2 + 4 * self.mu * stock)) \
            / (2 * self.mu)
        return root ** 2


@dataclass(frozen=True)
class OrderModel:
    """Demand as orders: a compound Poisson process.

    Orders arrive at RATE per day; each takes a number of containers
    drawn from SIZES, the counts of past orders, each as often as it
    occurred. The figures it gives are not rough.
    """

    rate: float
    sizes: tuple[int, ...]
    rough = False

    @property
    def per_year(self) -> float:
        """The demand per year in containers: 365.25 times the rate times
        the mean order size."""
        return 365.25 * self.rate * statistics.fmean(self.sizes)

    @property
    def median(self) -> float:
        """The median order size."""
        return statistics.median(self.sizes)

    @property
    def largest(self) -> int:
        """The largest order size."""
        return max(self.sizes)

    @cached_property
    def weights(self) -> tuple[tuple[int, float], ...]:
        """Each order size with its probability times the size, the terms
        of Panjer's recursion."""
        counts = Counter(self.sizes)
        total = len(self.sizes)
        return tuple((size, size * count / total)
                     for size, count in sorted(counts.items()))

    def cdf(self, days: float, until: int | None = None,
            certainty: float | None = None) -> tuple[int, float]:
        """Return the probability that the demand of DAYS is at most a
        number of containers, with that number.

        The number is UNTIL; or, given CERTAINTY instead, the smallest
        number whose probability reaches it. The probability of the
        compound Poisson demand is computed exactly by Panjer's
        recursion: with ``Λ = RATE × DAYS``, ``g(0) = e^−Λ`` and
        ``g(n) = Λ/n Σ_j j f(j) g(n − j)``, ``f`` being the distribution
        of the sizes. Stored terms are rescaled as they grow, so that a
        large ``Λ`` neither underflows nor overflows.
        """
        mean = self.rate * max(days, 0)
        terms = [1.0]
        scale = -mean
        total = 1.0
        n = 0

        def reached() -> float:
            return math.exp(math.log(total) + scale) if total else 0.0

        while (n < until) if until is not None else (
                reached() < certainty):
            n += 1
            term = mean / n * sum(weight * terms[n - size]
                                  for size, weight in self.weights
                                  if size <= n)
            terms.append(term)
            total += term
            if term > SCALE:
                terms = [stored / SCALE for stored in terms]
                total /= SCALE
                scale += math.log(SCALE)
        return n, min(reached(), 1.0)

    def need(self, days: float, certainty: float) -> int:
        """Return the smallest whole number of containers whose
        probability of covering the demand of DAYS reaches CERTAINTY."""
        return self.cdf(days, certainty=certainty)[0]

    def lasting(self, days: float, stock: int) -> float:
        """Return the probability that STOCK containers cover the demand
        of DAYS."""
        return self.cdf(days, until=stock)[1]

    def runway(self, stock: float, certainty: float) -> float:
        """Return the days STOCK containers last at CERTAINTY: the H at
        which the probability that they cover the demand of H falls to
        CERTAINTY, found by bisection to 0.01 days and never above
        it."""
        held = max(int(stock), 0)
        low = 0.0
        high = max(1.0, (held + 1) / (self.rate * max(self.sizes)))
        while self.lasting(high, held) >= certainty:
            low, high = high, high * 2
        while high - low > ORDER_PRECISION:
            middle = (low + high) / 2
            if not low < middle < high:
                break
            if self.lasting(middle, held) >= certainty:
                low = middle
            else:
                high = middle
        return low


type Model = OrderModel | QuarterlyModel


def previous(quarter: Quarter) -> Quarter:
    """Return the quarter before QUARTER."""
    year, number = quarter
    return (year - 1, 4) if number == 1 else (year, number - 1)


def quarter_days(quarter: Quarter) -> int:
    """Return the calendar days of QUARTER."""
    year, number = quarter
    start = date(year, 3 * number - 2, 1)
    end = date(year + 1, 1, 1) if number == 4 \
        else date(year, 3 * number + 1, 1)
    return (end - start).days


def history_window(data: Iterable[Quarter], today: date,
                   count: int) -> list[Quarter]:
    """Return the history window, oldest first: the last COUNT complete
    quarters before TODAY's, leaving out those before the first of the
    quarters DATA, which have data. Without data it is empty."""
    first = min(data, default=None)
    if first is None:
        return []
    window = []
    quarter = quarter_of(today)
    for _ in range(count):
        quarter = previous(quarter)
        if quarter < first:
            break
        window.append(quarter)
    return window[::-1]


def order_rate(orders: Sequence[Order], window: Sequence[Quarter]
               ) -> float:
    """Return the rate per day of ORDERS, all of which lie in WINDOW:
    the larger of the rate over the whole window and that over its
    latest four quarters, or all of them when it has fewer."""
    latest = set(window[-4:])
    recent = sum(quarter_of(day) in latest for day, _ in orders)
    return max(len(orders) / sum(map(quarter_days, window)),
               recent / sum(map(quarter_days, latest)))


def demand(entered: Mapping[Quarter, int], orders: Iterable[Order],
           today: date, settings: Settings) -> Model | None:
    """Return the demand model of an item as of TODAY, or None when it
    has no demand.

    ENTERED maps quarters to their entered consumption and ORDERS are
    the dates and counts of the item's counted delivery lines. The
    history window holds the last ``history_quarters`` of SETTINGS
    complete quarters, from the first with data; a quarter's total is
    its entered value plus its orders. An empty window, or one whose
    totals are all zero, gives None.

    The order window runs from the latest entered quarter of the history
    window, not included, to its end, or covers it whole without one.
    With at least ``min_orders`` orders in it, the order model applies,
    estimated from those orders; otherwise the quarterly model, from
    the history window's totals.
    """
    orders = list(orders)
    window = history_window(
        [*entered, *(quarter_of(day) for day, _ in orders)], today,
        settings.history_quarters)
    shown = set(window)
    totals = {quarter: entered.get(quarter, 0) for quarter in window}
    for day, count in orders:
        if quarter_of(day) in shown:
            totals[quarter_of(day)] += count
    if not any(totals.values()):
        return None
    latest = max((quarter for quarter in window if quarter in entered),
                 default=None)
    order_window = [quarter for quarter in window
                    if latest is None or quarter > latest]
    inside = set(order_window)
    counted = [(day, count) for day, count in orders
               if quarter_of(day) in inside]
    if order_window and len(counted) >= settings.min_orders:
        return OrderModel(rate=order_rate(counted, order_window),
                          sizes=tuple(count for _, count in counted))
    values = [totals[quarter] for quarter in window]
    recent = values[-4:]
    m = max(sum(values) / len(values), sum(recent) / len(recent))
    spread = statistics.variance(values) if len(values) > 1 else 0
    return QuarterlyModel(m=m, v=max(spread, m), quarters=len(values))


def lacking(model: Model, quantity: int, days: float,
            certainty: float) -> int:
    """Return the whole containers an item holding QUANTITY lacks for
    DAYS at CERTAINTY: its need less QUANTITY where positive, rounded
    up."""
    return max(0, math.ceil(model.need(days, certainty) - quantity))


def joint_certainty(certainty: float, count: int) -> float:
    """Return the certainty at which each of COUNT items is planned so
    that, by the union bound, all are covered together with at least
    CERTAINTY: ``1 − (1 − CERTAINTY) / COUNT``."""
    return 1 - (1 - certainty) / count


type Holding = tuple[Model | None, int, Decimal | None]


def article_runway(items: Sequence[Holding], bulk: Decimal,
                   certainty: float) -> float | None:
    """Return the runway of an article in days, or None when none of its
    ITEMS has demand.

    Each of ITEMS is its model, None without demand, its quantity, and
    its container size in the bulk unit, None when it does not convert.
    BULK is the usable bulk in that unit. Each of the ``k`` items with
    demand is planned at ``joint_certainty(CERTAINTY, k)``. The runway
    is the longest H for which the whole containers the converting
    items lack, times their sizes, fit into BULK, and which no
    unconverting item's runway on hand falls short of.
    """
    held = [(model, quantity, size) for model, quantity, size in items
            if model is not None]
    if not held:
        return None
    each = joint_certainty(certainty, len(held))
    bound = min((model.runway(quantity, each)
                 for model, quantity, size in held if size is None),
                default=math.inf)
    filled = [(model, quantity, size) for model, quantity, size in held
              if size is not None]
    if not filled:
        return bound

    def cost(days: float) -> Decimal:
        return sum((lacking(model, quantity, days, each) * size
                    for model, quantity, size in filled), Decimal(0))

    if bound < math.inf and cost(bound) <= bulk:
        return bound
    low = 0.0
    if bound < math.inf:
        high = bound
    else:
        high = 1.0
        while cost(high) <= bulk:
            low, high = high, high * 2
    while high - low > ARTICLE_PRECISION:
        middle = (low + high) / 2
        if not low < middle < high:
            break
        if cost(middle) <= bulk:
            low = middle
        else:
            high = middle
    allotted = min(model.runway(quantity + lacking(model, quantity, low,
                                                   each), each)
                   for model, quantity, size in filled)
    return min(max(allotted, low), bound)


def usable_bulk(amounts: Iterable[Decimal], largest: Decimal) -> Decimal:
    """Return the bulk that can be filled in whole containers: the sum of
    AMOUNTS, one per lot, each less LARGEST, the largest container size,
    where positive."""
    return sum((amount - largest for amount in amounts if amount > largest),
               Decimal(0))


def synthesis_time(durations: Sequence[int], default: int
                   ) -> tuple[int, int | None]:
    """Return the synthesis time in days and the number of syntheses it
    is the longest of, None when it is DEFAULT.

    DURATIONS are those of the past syntheses, oldest first. From three
    on, the time is the longest of the last three; before, it is the
    longest of them and DEFAULT.
    """
    if len(durations) >= 3:
        return max(durations[-3:]), 3
    longest = max(durations, default=0)
    if longest > default:
        return longest, len(durations)
    return default, None


def priority(slack: float, high_days: int, medium_days: int) -> str:
    """Return the priority of SLACK days: ``high`` below HIGH_DAYS,
    ``medium`` below MEDIUM_DAYS, and ``low`` otherwise."""
    if slack < high_days:
        return "high"
    if slack < medium_days:
        return "medium"
    return "low"


@dataclass(frozen=True)
class Rhythm:
    """The deliveries of an item as of a day.

    LAST is the latest delivery's date, None without one; PAST_YEAR the
    number of deliveries in the 365 days up to the day. INTERVAL is the
    median of the days between consecutive deliveries of the 730 days up
    to the day, rounded half up, and NEXT is LAST plus INTERVAL; both
    are None with fewer than three deliveries in those 730 days.
    """

    last: date | None
    past_year: int
    interval: int | None
    next: date | None


def rhythm(dates: Iterable[date], today: date) -> Rhythm:
    """Return the delivery rhythm of the deliveries on DATES, in any
    order, as of TODAY."""
    found = sorted(dates)
    recent = [day for day in found if (today - day).days < 730]
    interval = None
    if len(recent) >= 3:
        gaps = [(later - earlier).days
                for earlier, later in zip(recent, recent[1:])]
        interval = math.floor(statistics.median(gaps) + 0.5)
    last = found[-1] if found else None
    return Rhythm(
        last=last,
        past_year=sum((today - day).days < 365 for day in found),
        interval=interval,
        next=last + timedelta(days=interval) if interval is not None
        else None)


def whole(amount: Decimal) -> Decimal:
    """Return AMOUNT rounded up to a whole number."""
    return amount.to_integral_value(ROUND_CEILING)
