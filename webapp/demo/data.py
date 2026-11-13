"""The demo data set: the records of an invented lab, as the list of
changes that made them, dated back from the day it is seeded as of.

``changes`` is a pure function of that day and a language. Each change
is a frozen dataclass holding its MOMENT, an aware datetime in
``Europe/Berlin``, and the user name of the account that makes it;
every other date a change holds is one the record it makes names.
``demo.seed`` makes the changes, in order, through the application's
own write paths.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
PASSWORD = "demo"
# The inventory opens this many days before the seeding day.
OPENING_DAYS = 400
# Paper records of the time before are entered within this many days of
# the opening.
ENTRY_DAYS = 30
# Changes of a day lie from 08:00 to before 18:00.
DAY_START = time(8)
DAY_SECONDS = 10 * 60 * 60

type Text = tuple[str, str]


@dataclass(frozen=True)
class Account:
    """A demo account; SIGNS_IN tells whether it has the password
    ``PASSWORD``, or no usable password."""

    username: str
    first_name: str
    last_name: str
    initials: str
    superuser: bool = False
    signs_in: bool = True

    @property
    def name(self) -> str:
        """The first and last name."""
        return f"{self.first_name} {self.last_name}"


ACCOUNTS = (
    Account("klehmann", "Katrin", "Lehmann", "KL", superuser=True),
    Account("tbauer", "Tobias", "Bauer", "TB"),
    Account("aschmidt", "Anna", "Schmidt", "AS"),
    Account("jkoch", "Jonas", "Koch", "JK"),
    Account("mwolf", "Miriam", "Wolf", "MW", signs_in=False),
)


def signing_in() -> list[Account]:
    """Return the demo accounts that sign in with ``PASSWORD``."""
    return [account for account in ACCOUNTS if account.signs_in]


# The demo's lab notebooks, each its code and its owner's user name.
NOTEBOOKS = (("AE-1", "klehmann"), ("AE-2", "aschmidt"), ("CE-1", "jkoch"),
             ("CE-3", "mwolf"))


# ---------------------------------------------------------------------------
# Changes


@dataclass(frozen=True, kw_only=True)
class Change:
    """A change made at MOMENT by the account USER."""

    moment: datetime
    user: str


@dataclass(frozen=True, kw_only=True)
class CreateAccount(Change):
    account: Account


@dataclass(frozen=True, kw_only=True)
class LoadRegistry(Change):
    """Load the demo registry, ``registry.json`` of this package, into
    the empty registry."""


@dataclass(frozen=True, kw_only=True)
class RegisterNotebook(Change):
    """Register the lab notebook CODE of the account OWNER, by user
    name, with no note."""

    code: str
    owner: str


@dataclass(frozen=True, kw_only=True)
class RecordImport(Change):
    """Record the data set's own accepted import of the demo collection,
    ``manifest.json`` of this package, with its LANGUAGE."""

    language: str


@dataclass(frozen=True, kw_only=True)
class SaveParameters(Change):
    """Store the planning parameters with FIELDS, or change them."""

    fields: dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class OpenItem(Change):
    """Create the item KEY of the substance SUBSTANCE, by its key, with
    its opening count, dated the change's day; ARTICLE_NUMBER and
    CATEGORY are its article's."""

    key: str
    substance: str
    article_number: str | None
    category: str
    size: Decimal
    unit: str
    quantity: int
    compartment: str = ""
    box: str = ""


@dataclass(frozen=True, kw_only=True)
class EnterConsumption(Change):
    item: str
    year: int
    quarter: int
    count: int


@dataclass(frozen=True, kw_only=True)
class BookNote(Change):
    """Book the delivery note NUMBER dated DAY, current or HISTORICAL,
    with LINES, pairs of an item key and a count."""

    number: str
    day: date
    recipient: str
    lines: tuple[tuple[str, int], ...]
    historical: bool = False


@dataclass(frozen=True, kw_only=True)
class ReverseNote(Change):
    """Reverse the historical delivery note NUMBER with NOTE."""

    number: str
    note: str


@dataclass(frozen=True, kw_only=True)
class ReverseDelivery(Change):
    """Reverse the delivery of ITEM by the current note NUMBER."""

    number: str
    item: str
    note: str


@dataclass(frozen=True, kw_only=True)
class OpenLot(Change):
    """Create the bulk lot KEY of the substance SUBSTANCE, by its key,
    made in the lab or bought as SOURCE says, from SUPPLIER, with its
    opening amount, in UNIT, dated the change's day; STEP, when given,
    is the task step that made it, as the key of its task and its
    position."""

    key: str
    substance: str
    source: str
    supplier: str
    unit: str
    amount: Decimal
    batch: str
    location: str
    made_on: date
    step: tuple[str, int] | None = None


@dataclass(frozen=True, kw_only=True)
class Withdraw(Change):
    """Take AMOUNT, in the lot's unit, from LOT into the step at
    POSITION of the task TASK, dated the change's day."""

    lot: str
    task: str
    position: int
    amount: Decimal


@dataclass(frozen=True, kw_only=True)
class Fill(Change):
    """Fill COUNT containers of ITEM from LOT, taking AMOUNT in the lot's
    unit, or from no lot when LOT is None, dated the change's day."""

    item: str
    lot: str | None
    count: int
    amount: Decimal | None


@dataclass(frozen=True, kw_only=True)
class SetStatus(Change):
    """Set the state of ITEM to STATUS, as its edit form does."""

    item: str
    status: str


@dataclass(frozen=True, kw_only=True)
class Correct(Change):
    """Set the quantity of ITEM to COUNT, dated the change's day."""

    item: str
    count: int
    note: str


@dataclass(frozen=True, kw_only=True)
class CorrectLot(Change):
    """Set the amount of LOT to AMOUNT, in its unit, dated the change's
    day."""

    lot: str
    amount: Decimal
    note: str


@dataclass(frozen=True, kw_only=True)
class NameJournalEntry(Change):
    """Make the step at POSITION of the task TASK name the lab notebook
    entry ENTRY, ``<code>/<number>``."""

    task: str
    position: int
    entry: str


@dataclass(frozen=True, kw_only=True)
class SaveTask(Change):
    """Create the task KEY with FIELDS, or change it; an assignee is
    given by user name, a substance and a sequence by their keys, and
    the steps as the task form's ``steps_total`` and ``steps_done``."""

    key: str
    fields: dict[str, Any]


# ---------------------------------------------------------------------------
# The lab


@dataclass(frozen=True)
class _Size:
    """A container size of an article.

    FINAL is the containers it holds on the seeding day. Orders come
    every GAP days, the first PHASE days after the first day of the
    history, with the counts SIZES in turn; GAP None gives none. OPENED
    is the day of its opening count, in days after the opening. RATE,
    when given, is the containers a quarter its entered consumption
    holds instead of its orders' rate, entered for the quarters ENTERED
    counts back from the opening's quarter. A size not FILLED gets its
    containers from its opening count alone. STATUS is set on the day
    SET_ASIDE, in days after the opening.
    """

    size: str
    unit: str
    final: int
    gap: int | None = None
    sizes: tuple[int, ...] = ()
    phase: int = 0
    opened: int = 0
    rate: float | None = None
    entered: tuple[int, ...] = (8, 7, 6, 5, 4, 3, 2)
    filled: bool = True
    status: str = "active"
    set_aside: int = 0

    @property
    def per_quarter(self) -> float:
        """The containers its orders take in a quarter, or its RATE."""
        if self.rate is not None:
            return self.rate
        if not self.gap:
            return 0
        return 91.3125 * sum(self.sizes) / len(self.sizes) / self.gap


@dataclass(frozen=True)
class _StepLot:
    """A lot of the substance SUBSTANCE, by its key, that the step at
    POSITION of a synthesis makes on the day MADE, holding AMOUNT in
    UNIT, and the WITHDRAWALS from it into the synthesis's steps, each
    a day, a step's position and an amount in UNIT."""

    substance: str
    unit: str
    amount: str
    position: int
    made: int
    withdrawals: tuple[tuple[int, int, str], ...] = ()


@dataclass(frozen=True)
class _Synthesis:
    """A task of a substance, its days counted from the opening.

    A synthesis follows the sequence SEQUENCE, by its key, or none when
    it is empty, from its step START_STEP on; STEPS names the procedures
    of its steps, in order, and
    STEPS_DONE the days on which a number of them is done; its steps
    make the STEP_LOTS, and the JOURNAL entries are named by its steps,
    each a day, a step's position and an entry ``<code>/<number>``. A
    synthesis that ends yields its product lot the day it ends, which
    fills its article's items on the days FILLS and keeps REST, in the
    lot's unit. A synthesis that FAILED ends that day as failed, with
    no batch and no lot.
    """

    by: str
    created: int
    assignee: str | None = None
    started: int | None = None
    ended: int | None = None
    report: int | None = None
    qc: int | None = None
    cancelled: int | None = None
    failed: int | None = None
    sequence: str = ""
    start_step: int = 1
    steps: tuple[str, ...] = ()
    steps_done: tuple[tuple[int, int], ...] = ()
    step_lots: tuple[_StepLot, ...] = ()
    journal: tuple[tuple[int, int, str], ...] = ()
    fills: tuple[int, ...] = ()
    rest: str = "0"
    location: Text = ("Chemikalienschrank 3", "Chemicals cabinet 3")
    priority: str = "medium"
    note: Text = ("", "")


@dataclass(frozen=True)
class _Article:
    # The article number, or for an article never delivered, which has
    # none, the key of its substance; NUMBERED tells which. SUBSTANCE is
    # the key of its substance in the demo registry.
    number: str
    substance: str
    category: Text
    lot_unit: str
    sizes: tuple[_Size, ...]
    syntheses: tuple[_Synthesis, ...] = ()
    # The molar mass in g/mol the fillings convert with, where the
    # lot's unit and the items' differ in kind.
    mass: str | None = None
    numbered: bool = True

    @property
    def article_number(self) -> str | None:
        """The article number its items carry, or None."""
        return self.number if self.numbered else None


SEQ_1 = ("OSDB-0001", "OSDB-0002")
SEQ_2 = ("OSDB-0004", "OSDB-0009")
FRIDGE = ("Kühlschrank 2, Fach 1", "Fridge 2, shelf 1")
DESICCATOR = ("Exsikkator 1", "Desiccator 1")

ARTICLES = (
    _Article(
        "CH-0012", "cinnamic-acid",
        ("Carbonsäuren", "Carboxylic acids"), "mg",
        (_Size("100", "mg", final=4, gap=21, sizes=(2, 3, 2, 4), phase=3),
         _Size("500", "mg", final=3, gap=30, sizes=(1, 2, 1), phase=11),
         _Size("1", "g", final=2, filled=False, status="discontinued",
               set_aside=120)),
        (_Synthesis("mwolf", 0, "mwolf", started=-20, ended=14,
                    report=20, qc=30, fills=(15, 60, 100)),
         _Synthesis("tbauer", 115, "tbauer", started=120,
                    ended=161, report=168, qc=175, fills=(162, 210, 250),
                    note=("Umkristallisiert aus Ethanol/Wasser.",
                          "Recrystallised from ethanol/water.")),
         _Synthesis("aschmidt", 200, cancelled=206,
                    note=("Ausgangsmaterial verunreinigt, neu bestellt.",
                          "Starting material impure; reordered.")),
         _Synthesis("klehmann", 255, "aschmidt", started=260,
                    ended=298, report=305, fills=(299, 330)),
         _Synthesis("klehmann", 330, "tbauer", started=338,
                    priority="high"))),
    _Article(
        "CH-0010", "acetylsalicylic-acid",
        ("Carbonsäuren", "Carboxylic acids"), "g",
        (_Size("1", "g", final=18, gap=14, sizes=(1, 1, 2), phase=5),
         _Size("5", "g", final=8, gap=33, sizes=(1, 2, 1, 1), phase=17),
         _Size("25", "g", final=1, filled=False, status="not_needed",
               set_aside=200)),
        (_Synthesis("klehmann", 35, "jkoch", started=40,
                    ended=66, report=70, qc=74, sequence="SEQ-0001",
                    steps=SEQ_1, steps_done=((52, 1),),
                    fills=(67, 120, 180), location=DESICCATOR),
         _Synthesis("klehmann", 225, "jkoch", started=230,
                    ended=261, report=266, qc=270, sequence="SEQ-0001",
                    steps=SEQ_1, steps_done=((245, 1),),
                    step_lots=(_StepLot("salicylic-acid", "g", "5", 1,
                                        245),),
                    fills=(262, 310, 350), location=DESICCATOR),
         _Synthesis("aschmidt", 380, "aschmidt",
                    sequence="SEQ-0001", start_step=2, steps=SEQ_1[1:],
                    note=("Ölbad vorher prüfen.",
                          "Check the oil bath first.")))),
    _Article(
        "CH-0013", "dibenzylideneacetone",
        ("Ketone", "Ketones"), "mg",
        (_Size("250", "mg", final=0, gap=25, sizes=(1, 2, 1, 1),
               phase=8),
         _Size("1", "g", final=4, gap=15, sizes=(1,), opened=340,
               filled=False)),
        (_Synthesis("tbauer", 85, "tbauer", started=90,
                    ended=115, report=118, qc=122, fills=(116, 180)),
         _Synthesis("tbauer", 245, "jkoch", started=250,
                    ended=270, report=274, qc=280, fills=(271, 300)),
         _Synthesis("jkoch", 310, "jkoch", started=315, failed=327,
                    note=("Produkt zersetzt sich bei der Aufarbeitung.",
                          "The product decomposed during the work-up."))
         )),
    _Article(
        "CH-0016", "isopentyl-acetate",
        ("Ester", "Esters"), "g",
        (_Size("1", "g", final=3, gap=10, sizes=(1, 2, 1), phase=2),
         _Size("5", "g", final=5, gap=30, sizes=(1, 1, 2), phase=9),
         _Size("10", "g", final=3, gap=35, sizes=(1, 1), phase=20)),
        (_Synthesis("klehmann", 25, "tbauer", started=30,
                    ended=58, report=63, qc=66, fills=(59, 110, 150),
                    location=FRIDGE),
         _Synthesis("tbauer", 195, "jkoch", started=200,
                    ended=225, report=230, qc=233, fills=(226, 280, 330),
                    location=FRIDGE),
         _Synthesis("klehmann", 335, "tbauer", started=340,
                    ended=360, report=365, fills=(361,), rest="200",
                    location=FRIDGE))),
    _Article(
        "CH-0001", "1-4-bromophenyl-ethanol",
        ("Alkohole", "Alcohols"), "mg",
        (_Size("50", "mg", final=6, gap=200, sizes=(3,), phase=60),
         _Size("250", "mg", final=3, rate=2, entered=(8, 7, 6, 5),
               filled=False)),
        (_Synthesis("klehmann", 385, "jkoch",
                    priority="low"),)),
    _Article(
        "CH-0002", "1-biphenyl-4-yl-ethanol",
        ("Alkohole", "Alcohols"), "mg",
        (_Size("10", "umol", final=10, gap=30, sizes=(2, 3), phase=4),
         _Size("50", "umol", final=5, gap=35, sizes=(1, 1, 2), phase=15)),
        (_Synthesis("klehmann", 75, "jkoch", started=80,
                    ended=110, report=115, qc=121, sequence="SEQ-0002",
                    steps=SEQ_2, steps_done=((95, 1),),
                    fills=(111, 200, 300), rest="150"),
         _Synthesis("klehmann", 380, "jkoch", started=388,
                    sequence="SEQ-0002", steps=SEQ_2,
                    steps_done=((396, 1),), journal=((396, 1, "CE-3/2"),),
                    step_lots=(_StepLot("4-acetylbiphenyl", "g", "3", 1,
                                        396, ((398, 2, "2"),)),))),
        mass="198.26"),
    _Article(
        "1-phenylethanol", "1-phenylethanol",
        ("Alkohole", "Alcohols"), "mg",
        (_Size("100", "mg", final=8, opened=310),),
        (_Synthesis("aschmidt", 280, "aschmidt",
                    started=285, ended=305, report=308, qc=309,
                    fills=(311,), rest="150"),),
        numbered=False),
    _Article(
        "NV-0007", "new-compound-7",
        ("Neuverbindungen", "New compounds"), "umol",
        (_Size("10", "mg", final=4, gap=20, sizes=(1, 2), phase=6),),
        (_Synthesis("tbauer", 95, "aschmidt", started=100,
                    ended=140, report=146, qc=150, fills=(141, 250, 330),
                    rest="600", location=FRIDGE),
         _Synthesis("aschmidt", 365, "aschmidt", started=372,
                    note=("Ansatz verdoppelt.", "Scale doubled."))),
        mass="250"),
)



@dataclass(frozen=True)
class _Intermediate:
    """A substance without an article, by its KEY, that a synthesis
    yields a lot of, the day it ends, holding AMOUNT in UNIT: made in
    the lab, or, with a SUPPLIER, bought from it; a bought lot has a
    lot made in the lab beside it, holding MADE in UNIT, with the same
    batch."""

    key: str
    unit: str
    amount: str
    synthesis: _Synthesis
    supplier: str = ""
    made: str = ""


INTERMEDIATES = (
    _Intermediate(
        "4-acetylbiphenyl", "g", "12",
        _Synthesis("klehmann", 145, "jkoch", started=150, ended=168,
                   report=171, qc=173,
                   note=("Vorstufe für CH-0002.",
                         "Precursor of CH-0002."))),
    _Intermediate(
        "ethyl-cinnamate", "g", "25",
        _Synthesis("klehmann", 205, "klehmann", started=210, ended=236,
                   report=238, qc=239,
                   note=("Auftragssynthese; die Charge ist die des "
                         "Lieferanten.",
                         "Contract synthesis; the batch is the "
                         "supplier's.")),
        supplier="ChemPur GmbH", made="2"),
)

RECIPIENTS: tuple[Text, ...] = (
    ("AG Weber (Biochemie)", "Weber group (biochemistry)"),
    ("Analytiklabor", "Analytical laboratory"),
    ("Pharmakologie", "Pharmacology"),
    ("Formulierung", "Formulation"),
)
# The staff who book the daily work, and those who did in the first
# weeks.
STAFF = ("tbauer", "aschmidt", "jkoch")
FIRST_WEEKS = ("mwolf", "tbauer")
# The variation of entered quarters around a size's rate.
VARIATION = (0.9, 1.1, 1.0, 0.85, 1.15, 1.0, 1.0)
# The delivery reversed: its article, the position of its size and the
# position of the order among the size's current orders. The size
# corrected: its article, its position and the day. The lot corrected:
# its article, the position of its synthesis, the day and the amount
# found missing. The historical note entered twice, by its position.
REVERSED = ("CH-0016", 0, 14)
CORRECTED = ("CH-0016", 1, 180)
CORRECTED_LOT = ("CH-0016", 2, 370, "1.5")
DUPLICATED = 2
FACTOR = {"mg": Decimal(1), "g": Decimal(1000), "umol": Decimal(1),
          "mmol": Decimal(1000)}
MASS_UNITS = ("mg", "g")
DEFAULTS = {"certainty": 0.95, "buffer_days": 28,
            "default_synthesis_days": 21, "history_quarters": 12,
            "min_orders": 6, "high_days": 14, "medium_days": 56,
            "target_days": 365}

NOTES = {
    "reversed delivery": ("Falscher Empfänger, Gebinde zurückgenommen.",
                          "Wrong recipient; container taken back."),
    "correction": ("Inventur: ein Gebinde fehlt.",
                   "Stocktaking: one container missing."),
    "lot correction": ("Nachgewogen.", "Weighed again."),
    "duplicate": ("Doppelt erfasst, siehe {number}.",
                  "Entered twice, see {number}."),
}


def size_key(article: str, size: _Size) -> str:
    """The key of an article's item of SIZE."""
    return f"{article}/{size.size}{size.unit}"


# ---------------------------------------------------------------------------
# The timeline


class _Timeline:
    """The changes of the data set as of TODAY in LANGUAGE, collected in
    any order and given their moments by ``changes``."""

    def __init__(self, today: date, language: str) -> None:
        self.today = today
        self.opening = today - timedelta(days=OPENING_DAYS)
        self.language = language
        self.pending: list[tuple[date, int, int, type, dict[str, Any]]] = []

    def day(self, offset: int) -> date:
        """The day OFFSET days after the opening."""
        return self.opening + timedelta(days=offset)

    def text(self, pair: Text) -> str:
        """PAIR's German text, or its English one in English."""
        return pair[0] if self.language == "de" else pair[1]

    def add(self, on: date, rank: int, kind: type, **fields: Any) -> None:
        """Make a change of KIND on the day ON; on one day, changes come
        in order of RANK, then in the order they were added."""
        self.pending.append((on, rank, len(self.pending), kind, fields))

    def changes(self) -> list[Change]:
        """Return the changes in order, each day's spread evenly from
        08:00 to before 18:00."""
        ordered = sorted(self.pending, key=lambda entry: entry[:3])
        per_day: dict[date, int] = defaultdict(int)
        for on, *_rest in ordered:
            per_day[on] += 1
        seen: dict[date, int] = defaultdict(int)
        found = []
        for on, _rank, _seq, kind, fields in ordered:
            step = DAY_SECONDS // per_day[on]
            moment = datetime.combine(on, DAY_START, BERLIN) + timedelta(
                seconds=seen[on] * step)
            seen[on] += 1
            found.append(kind(moment=moment, **fields))
        return found


# Ranks of the changes of one day: a task ends after its product lot
# is recorded.
ACCOUNT, REGISTRY, PARAMETERS, ITEM, TASK, LOT, END, FILL, WITHDRAWAL, \
    NOTE, REVERSAL, CORRECTION, ENTRY, HISTORICAL, LOT_CORRECTION, \
    STATUS = range(16)


def staff(offset: int, turn: int = 0) -> str:
    """The account that books the daily work OFFSET days after the
    opening."""
    people = FIRST_WEEKS if offset < ENTRY_DAYS else STAFF
    return people[(offset + turn) % len(people)]


def quarter_of(day: date) -> tuple[int, int]:
    """Return the year and the quarter, 1 to 4, of DAY."""
    return day.year, (day.month - 1) // 3 + 1


def quarter_start(quarter: tuple[int, int]) -> date:
    """Return the first day of QUARTER, a year and a quarter."""
    year, number = quarter
    return date(year, 3 * number - 2, 1)


def back(quarter: tuple[int, int], count: int) -> tuple[int, int]:
    """The quarter COUNT quarters before QUARTER."""
    year, number = quarter
    index = year * 4 + number - 1 - count
    return index // 4, index % 4 + 1


def amount_of(article: _Article, size: _Size, count: int) -> Decimal:
    """The amount COUNT containers of SIZE take from a lot of ARTICLE, in
    the lot's unit, rounded half up to three places."""
    base = Decimal(count) * Decimal(size.size) * FACTOR[size.unit]
    if (size.unit in MASS_UNITS) != (article.lot_unit in MASS_UNITS):
        mass = Decimal(article.mass)
        base = (base * 1000 / mass if size.unit in MASS_UNITS
                else base * mass / 1000)
    return (base / FACTOR[article.lot_unit]).quantize(
        Decimal("0.001"), ROUND_HALF_UP)


def changes(today: date, language: str) -> list[Change]:
    """Return the changes of the data set as of TODAY, its free texts in
    LANGUAGE, ``de`` or ``en``, in the order they are made.

    The inventory opens ``OPENING_DAYS`` before TODAY; no change lies
    later than the day before TODAY. Raise ValueError when the lab's
    plan cannot be met, such as a size whose stock would fall below
    zero.
    """
    line = _Timeline(today, language)
    for account in ACCOUNTS:
        line.add(line.opening, ACCOUNT, CreateAccount,
                 user=account.username, account=account)
    line.add(line.opening, REGISTRY, LoadRegistry, user="klehmann")
    for code, owner in NOTEBOOKS:
        line.add(line.opening, REGISTRY, RegisterNotebook, user="klehmann",
                 code=code, owner=owner)
    line.add(line.opening, REGISTRY, RecordImport, user="klehmann",
             language=language)
    line.add(line.day(1), PARAMETERS, SaveParameters, user="klehmann",
             fields={**DEFAULTS, "target_days": 180})
    line.add(line.day(200), PARAMETERS, SaveParameters, user="klehmann",
             fields={"target_days": 365})
    orders: list[tuple[date, str, int]] = []
    batches = _batches(line)
    for article in ARTICLES:
        orders += _article(line, article, batches)
    for intermediate in INTERMEDIATES:
        _intermediate(line, intermediate, batches)
    _notes(line, orders)
    return line.changes()


def _batches(line: _Timeline) -> dict[tuple[str, Any], str]:
    """The batch of each synthesis that ends, by its article, or its
    intermediate's key, and its position, and of each lot a step makes,
    by its synthesis's key and the lot's position among its step lots:
    ``B<yy>-<nnn>``, numbered in the order of the days of the ends and
    the step lots."""
    syntheses = [(article.number, position, synthesis)
                 for article in ARTICLES
                 for position, synthesis in enumerate(article.syntheses)]
    syntheses += [(intermediate.key, 0, intermediate.synthesis)
                  for intermediate in INTERMEDIATES]
    made: list[tuple[date, str, Any]] = [
        (line.day(synthesis.ended), number, position)
        for number, position, synthesis in syntheses
        if synthesis.ended is not None]
    made += [(line.day(lot.made), f"{number}#{position}", index)
             for number, position, synthesis in syntheses
             for index, lot in enumerate(synthesis.step_lots)]
    return {(number, position): f"B{day:%y}-{index:03d}"
            for index, (day, number, position)
            in enumerate(sorted(made, key=lambda entry: entry[0]), 1)}


def _article(line: _Timeline, article: _Article,
             batches: dict[tuple[str, int], str]) -> list[
                 tuple[date, str, int]]:
    """Add the changes of ARTICLE but its delivery notes, and return its
    orders, each a day, an item key and a count."""
    history = quarter_start(back(quarter_of(line.opening), 1))
    yields = {}
    for position, synthesis in enumerate(article.syntheses):
        key = f"{article.number}#{position}"
        batch = batches.get((article.number, position), "")
        _task(line, key, article.substance, synthesis, batch)
        _step_lots(line, key, synthesis, batches)
        if synthesis.ended is not None:
            yields[position] = batch
    opportunities = sorted(
        (offset, position) for position, synthesis
        in enumerate(article.syntheses) if position in yields
        for offset in synthesis.fills)
    # The syntheses of an article without an article number fill its
    # containers directly, not from their lots.
    taken: dict[int, Decimal] = defaultdict(Decimal)
    found = []
    for turn, size in enumerate(article.sizes):
        key = size_key(article.number, size)
        own = _orders(line, size, history)
        found += [(day, key, count) for day, count in own]
        _size(line, article, turn, size, key, own, opportunities, taken)
    for position, batch in yields.items():
        synthesis = article.syntheses[position]
        made = line.day(synthesis.ended)
        line.add(made, LOT, OpenLot, user=synthesis.by,
                 key=f"{article.number}#{position}",
                 substance=article.substance, source="made", supplier="",
                 unit=article.lot_unit,
                 amount=taken[position] + Decimal(synthesis.rest),
                 batch=batch, location=line.text(synthesis.location),
                 made_on=made)
    if article.number == CORRECTED_LOT[0]:
        _, position, offset, less = CORRECTED_LOT
        rest = Decimal(article.syntheses[position].rest)
        line.add(line.day(offset), LOT_CORRECTION, CorrectLot,
                 user=staff(offset), lot=f"{article.number}#{position}",
                 amount=rest - Decimal(less),
                 note=line.text(NOTES["lot correction"]))
    return found


def _orders(line: _Timeline, size: _Size, history: date
            ) -> list[tuple[date, int]]:
    """The orders of SIZE from the day HISTORY to the day before the
    seeding day, from its opening count on."""
    if not size.gap:
        return []
    found = []
    day = history + timedelta(days=size.phase)
    turn = 0
    while day < line.today:
        if size.opened == 0 or day >= line.day(size.opened):
            found.append((day, size.sizes[turn % len(size.sizes)]))
            turn += 1
        day += timedelta(days=size.gap)
    return found


def _size(line: _Timeline, article: _Article, turn: int, size: _Size,
          key: str, orders: list[tuple[date, int]],
          opportunities: list[tuple[int, int]],
          taken: dict[int, Decimal]) -> None:
    """Add the opening count, entered consumption, fillings and
    corrections of the item KEY, so that its stock covers its ORDERS
    and is ``size.final`` on the seeding day.

    Each filling but the last fills what the orders until the next take
    and a cushion of the largest order; the last fills what leaves the
    final stock. Raise ValueError when the stock would fall below zero
    or end above its final value.
    """
    opened = line.day(size.opened)
    current = [(day, count) for day, count in orders if day >= opened]
    reversal = (current[REVERSED[2]]
                if (article.number, turn) == REVERSED[:2] else None)
    correction = (line.day(CORRECTED[2])
                  if (article.number, turn) == CORRECTED[:2] else None)
    # Net demand by day: orders, a reversal two days after its order
    # giving its containers back, and a correction finding one missing.
    demand: dict[date, int] = defaultdict(int)
    for day, count in current:
        demand[day] += count
    if reversal:
        demand[reversal[0] + timedelta(days=2)] -= reversal[1]
    if correction:
        demand[correction] += 1
    fills = [(line.day(offset), position) for offset, position
             in opportunities if line.day(offset) >= opened] \
        if size.filled else []
    ends = [day for day, _ in fills[1:]] + [line.today]
    cushion = max(size.sizes, default=0)

    def between(start: date, end: date) -> int:
        return sum(count for day, count in demand.items()
                   if start <= day < end)

    first = fills[0][0] if fills else line.today
    opening = between(opened, first) + (cushion if fills else size.final)
    stock = opening - between(opened, first)
    booked: list[tuple[date, int, int]] = []
    for (day, position), end in zip(fills, ends):
        count = between(day, end) - stock + (
            size.final if end == line.today else cushion)
        if count < 0 and end == line.today:
            raise ValueError(f"{key} ends above its final stock")
        if count > 0:
            booked.append((day, position, count))
            stock += count
        stock -= between(day, end)
    _check(key, opening, booked, demand)
    compartment, box = place(article, turn)
    line.add(opened, ITEM, OpenItem, user=staff(size.opened, turn),
             key=key, substance=article.substance,
             article_number=article.article_number,
             compartment=compartment, box=box,
             category=line.text(article.category),
             size=Decimal(size.size), unit=size.unit, quantity=opening)
    for day, position, count in booked:
        amount = amount_of(article, size, count) if article.numbered \
            else None
        if amount is not None:
            taken[position] += amount
        line.add(day, FILL, Fill, user=staff((day - line.opening).days,
                                             turn),
                 item=key, lot=f"{article.number}#{position}"
                 if article.numbered else None, count=count,
                 amount=amount)
    if correction:
        counted = opening + sum(count for day, _, count in booked
                                if day <= correction) - sum(
            count for day, count in demand.items() if day <= correction)
        line.add(correction, CORRECTION, Correct,
                 user=staff(CORRECTED[2]), item=key, count=counted,
                 note=line.text(NOTES["correction"]))
    if size.opened == 0 and (size.gap or size.rate):
        _entered(line, key, size, turn)
    if size.status != "active":
        line.add(line.day(size.set_aside), STATUS, SetStatus,
                 user="klehmann", item=key, status=size.status)
    if reversal:
        day = reversal[0] + timedelta(days=2)
        line.add(day, REVERSAL, ReverseDelivery,
                 user=staff((day - line.opening).days),
                 number=reversal[0].isoformat(), item=key,
                 note=line.text(NOTES["reversed delivery"]))


def place(article: _Article, turn: int) -> tuple[str, str]:
    """The compartment and box of the size at TURN of ARTICLE: one of
    five compartments per article, and a box of its own per size."""
    position = ARTICLES.index(article)
    return str(1 + position % 5), str(3 * position + turn + 1)


def _check(key: str, opening: int, booked: list[tuple[date, int, int]],
           demand: dict[date, int]) -> None:
    """Raise ValueError when the stock of KEY, starting at OPENING, with
    the fillings BOOKED made before each day's deliveries and the net
    DEMAND of each day, falls below zero on some day."""
    filled: dict[date, int] = defaultdict(int)
    for day, _position, count in booked:
        filled[day] += count
    stock = opening
    for day in sorted({*filled, *demand}):
        stock += filled[day] - demand.get(day, 0)
        if stock < 0:
            raise ValueError(f"{key} runs out on {day}")


def _entered(line: _Timeline, key: str, size: _Size, turn: int) -> None:
    """Add the entered consumption of KEY for the quarters
    ``size.entered`` counts back from the opening's quarter, by default
    the seven from the eighth before it to the second."""
    opening = quarter_of(line.opening)
    for index, count in enumerate(size.entered):
        year, quarter = back(opening, count)
        value = max(0, round(size.per_quarter * VARIATION[index]))
        offset = 1 + (turn * 3 + index) % (ENTRY_DAYS - 2)
        line.add(line.day(offset), ENTRY, EnterConsumption,
                 user=FIRST_WEEKS[index % 2] if index % 3 else "klehmann",
                 item=key, year=year, quarter=quarter, count=value)


def _intermediate(line: _Timeline, intermediate: _Intermediate,
                  batches: dict[tuple[str, Any], str]) -> None:
    """Add the task of INTERMEDIATE and the lot it yields the day it
    ends, made in the lab or bought from the intermediate's supplier,
    and beside a bought lot the lot made in the lab with its batch."""
    synthesis = intermediate.synthesis
    batch = batches[(intermediate.key, 0)]
    key = f"{intermediate.key}#0"
    _task(line, key, intermediate.key, synthesis, batch)
    made = line.day(synthesis.ended)
    lot = {"user": synthesis.by, "substance": intermediate.key,
           "unit": intermediate.unit, "batch": batch,
           "location": line.text(synthesis.location), "made_on": made}
    line.add(made, LOT, OpenLot, key=key,
             source="bought" if intermediate.supplier else "made",
             supplier=intermediate.supplier,
             amount=Decimal(intermediate.amount), **lot)
    if intermediate.made:
        line.add(made, LOT, OpenLot, key=f"{key}/made", source="made",
                 supplier="", amount=Decimal(intermediate.made), **lot)


def _step_lots(line: _Timeline, key: str, synthesis: _Synthesis,
               batches: dict[tuple[str, Any], str]) -> None:
    """Add the lots the steps of the task KEY of SYNTHESIS make, each
    the day it is made, and the withdrawals from them into its
    steps."""
    for index, made in enumerate(synthesis.step_lots):
        lot = f"{key}/{index}"
        line.add(line.day(made.made), LOT, OpenLot, user=synthesis.by,
                 key=lot, substance=made.substance, source="made",
                 supplier="", unit=made.unit, amount=Decimal(made.amount),
                 batch=batches[(key, index)],
                 location=line.text(synthesis.location),
                 made_on=line.day(made.made), step=(key, made.position))
        for offset, position, amount in made.withdrawals:
            line.add(line.day(offset), WITHDRAWAL, Withdraw,
                     user=synthesis.assignee or synthesis.by, lot=lot,
                     task=key, position=position, amount=Decimal(amount))


def _task(line: _Timeline, key: str, substance: str,
          synthesis: _Synthesis, batch: str) -> None:
    """Add the changes of the task KEY of SYNTHESIS, of the substance
    SUBSTANCE by its key: its creation, then its start, steps, end or
    failure, report, QC list and cancellation, each on its day, and the
    journal entries its steps name, each after the day's other changes
    of the task; an end comes after the day's lots."""
    total = len(synthesis.steps) or None
    fields: dict[str, Any] = {
        "substance": substance, "assignee": synthesis.assignee,
        "priority": synthesis.priority, "note": line.text(synthesis.note),
        "sequence": synthesis.sequence,
        "start_step": synthesis.start_step, "steps_total": total}
    if synthesis.started is not None and \
            synthesis.started <= synthesis.created:
        fields["started"] = line.day(synthesis.started)
    line.add(line.day(synthesis.created), TASK, SaveTask,
             user=synthesis.by, key=key, fields=fields)
    later: list[tuple[int, dict[str, Any]]] = []
    if synthesis.started is not None and \
            synthesis.started > synthesis.created:
        later.append((synthesis.started,
                      {"started": line.day(synthesis.started)}))
    later += [(offset, {"steps_done": done})
              for offset, done in synthesis.steps_done]
    if synthesis.ended is not None:
        ended = {"ended": line.day(synthesis.ended), "batch": batch}
        if total:
            ended["steps_done"] = total
        later.append((synthesis.ended, ended))
    if synthesis.failed is not None:
        later.append((synthesis.failed, {
            "ended": line.day(synthesis.failed), "failed": True}))
    for offset, name in ((synthesis.report, "report"),
                         (synthesis.qc, "qc_list"),
                         (synthesis.cancelled, "cancelled")):
        if offset is not None:
            later.append((offset, {name: True}))
    for offset, change in sorted(later, key=lambda entry: entry[0]):
        line.add(line.day(offset), END if "ended" in change else TASK,
                 SaveTask, user=synthesis.assignee or synthesis.by,
                 key=key, fields=change)
    for offset, position, entry in synthesis.journal:
        line.add(line.day(offset), TASK, NameJournalEntry,
                 user=synthesis.assignee or synthesis.by, task=key,
                 position=position, entry=entry)


def _notes(line: _Timeline, orders: list[tuple[date, str, int]]) -> None:
    """Add the delivery notes of ORDERS: one note a day, numbered by
    year in the order of their dates; historical for the days before
    the opening, entered in its first weeks, one of them twice and
    reversed; and the reversal of the delivery ``REVERSED`` names."""
    by_day: dict[date, list[tuple[str, int]]] = defaultdict(list)
    for day, key, count in orders:
        by_day[day].append((key, count))
    days = sorted(by_day)
    historical = [day for day in days if day < line.opening]
    duplicate = historical[DUPLICATED] if len(historical) > DUPLICATED \
        else None
    numbered: list[tuple[date, bool]] = []
    for day in days:
        numbered.append((day, False))
        if day == duplicate:
            numbered.append((day, True))
    counters: dict[int, int] = defaultdict(int)
    numbers: dict[date, str] = {}
    for position, (day, copy) in enumerate(numbered):
        counters[day.year] += 1
        number = f"LS-{day.year}-{counters[day.year]:03d}"
        if not copy:
            numbers[day] = number
        recipient = line.text(RECIPIENTS[day.toordinal() % len(RECIPIENTS)])
        lines = tuple(sorted(by_day[day]))
        if day < line.opening:
            offset = 2 + position % (ENTRY_DAYS - 4)
            line.add(line.day(offset), HISTORICAL, BookNote,
                     user=FIRST_WEEKS[position % 2], number=number, day=day,
                     recipient=recipient, lines=lines, historical=True)
            if copy:
                line.add(line.day(ENTRY_DAYS - 1), REVERSAL, ReverseNote,
                         user="klehmann", number=number,
                         note=line.text(NOTES["duplicate"]).format(
                             number=numbers[day]))
        else:
            offset = (day - line.opening).days
            line.add(day, NOTE, BookNote, user=staff(offset), number=number,
                     day=day, recipient=recipient, lines=lines)
    _renumber_reversal(line, numbers)


def _renumber_reversal(line: _Timeline, numbers: dict[date, str]) -> None:
    """Point the reversed delivery at the number of its note, which the
    reversal names by its date until the notes are numbered."""
    for index, entry in enumerate(line.pending):
        on, rank, seq, kind, fields = entry
        if kind is ReverseDelivery:
            fields = {**fields,
                      "number": numbers[date.fromisoformat(fields["number"])]}
            line.pending[index] = (on, rank, seq, kind, fields)
