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
    ``PASSWORD`` and an email address, or no usable password and no
    address."""

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

    @property
    def email(self) -> str:
        """``<user name>@example.org`` for an account that signs in,
        which Forgejo needs; empty for one that does not."""
        return f"{self.username}@example.org" if self.signs_in else ""


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
    with LINES, triples of an item key, the key of a batch of the item's
    substance and a count."""

    number: str
    day: date
    recipient: str
    lines: tuple[tuple[str, str, int], ...]
    historical: bool = False


@dataclass(frozen=True, kw_only=True)
class ReverseNote(Change):
    """Reverse the historical delivery note NUMBER with NOTE."""

    number: str
    note: str


@dataclass(frozen=True, kw_only=True)
class ReverseDelivery(Change):
    """Reverse the deliveries of ITEM by the current note NUMBER, one
    for each batch the note's lines of the item name."""

    number: str
    item: str
    note: str


@dataclass(frozen=True, kw_only=True)
class RecordBatch(Change):
    """Record the batch KEY of the substance SUBSTANCE, by its key, made
    in the lab with the number NUMBER or bought as SOURCE says, with its
    supplier's fields, dated DATE, the day it was made or received, or
    None for a batch known by its number alone.

    The batch's first vessel holds AMOUNT, in UNIT, at LOCATION; an
    AMOUNT of None opens none. STEP, when given, is the task step that
    made the batch, as the key of its task and its position: the amount
    is then the batch's yield and waits in its flask when LOCATION is
    empty."""

    key: str
    substance: str
    source: str
    number: str
    supplier: str
    supplier_article_number: str
    supplier_batch: str
    unit: str
    amount: Decimal | None
    location: str
    date: date | None
    step: tuple[str, int] | None = None


@dataclass(frozen=True, kw_only=True)
class Withdraw(Change):
    """Take AMOUNT, in the vessel's unit, from the first vessel of the
    batch VESSEL into the step at POSITION of the task TASK, dated the
    change's day."""

    vessel: str
    task: str
    position: int
    amount: Decimal


@dataclass(frozen=True, kw_only=True)
class Fill(Change):
    """Fill COUNT containers of ITEM from the first vessel of the batch
    VESSEL, taking AMOUNT in the vessel's unit, dated the change's
    day."""

    item: str
    vessel: str
    count: int
    amount: Decimal


@dataclass(frozen=True, kw_only=True)
class Transfer(Change):
    """Pass AMOUNT, in the unit of the first vessel of the batch VESSEL,
    which is a flask, into a new stored vessel at LOCATION, dated the
    change's day."""

    vessel: str
    amount: Decimal
    location: str


@dataclass(frozen=True, kw_only=True)
class SetStatus(Change):
    """Set the state of ITEM to STATUS, as its edit form does."""

    item: str
    status: str


@dataclass(frozen=True, kw_only=True)
class Correct(Change):
    """Set the share of ITEM of the batch BATCH, by its key, or of
    unknown batch when BATCH is None, to COUNT, dated the change's
    day."""

    item: str
    batch: str | None
    count: int
    note: str


@dataclass(frozen=True, kw_only=True)
class CorrectVessel(Change):
    """Set the amount of the first vessel of the batch VESSEL to AMOUNT,
    in its unit, dated the change's day."""

    vessel: str
    amount: Decimal
    note: str


@dataclass(frozen=True, kw_only=True)
class OpenVessel(Change):
    """Record the first vessel of the batch VESSEL, a bought one, as
    opened on the change's day."""

    vessel: str


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
class _StepBatch:
    """A batch of the substance SUBSTANCE, by its key, that the step at
    POSITION of a synthesis makes on the day MADE, yielding AMOUNT in
    UNIT, and the WITHDRAWALS from its flask into the synthesis's steps,
    each a day, a step's position and an amount in UNIT. The yield waits
    in the flask unless STORED, and the batch's number ends in SUFFIX."""

    substance: str
    unit: str
    amount: str
    position: int
    made: int
    withdrawals: tuple[tuple[int, int, str], ...] = ()
    stored: bool = False
    suffix: str = ""


@dataclass(frozen=True)
class _Synthesis:
    """A task of a substance, its days counted from the opening.

    A synthesis follows the sequence SEQUENCE, by its key, or none when
    it is empty, from its step START_STEP on; STEPS names the procedures
    of its steps, in order, and
    STEPS_DONE the days on which a number of them is done; its steps
    make the STEP_BATCHES, and the JOURNAL entries are named by its steps,
    each a day, a step's position and an entry ``<code>/<number>``. A
    synthesis that ends has a step to end with, a plain one when it
    follows no sequence, and records its product batch from its last
    step on the day RECORDED, the day it ends by default: its yield
    fills its article's items on the days FILLS, keeps REST, in the
    vessel's unit, and, with MOVED, a day and an amount, passes that
    amount on that day from the flask into a stored vessel. The batch
    waits in its flask when FLASK and is stored at LOCATION otherwise;
    ending the task writes off what the flask holds. A synthesis that
    FAILED ends that day as failed, with no batch.
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
    step_batches: tuple[_StepBatch, ...] = ()
    journal: tuple[tuple[int, int, str], ...] = ()
    fills: tuple[int, ...] = ()
    rest: str = "0"
    recorded: int | None = None
    flask: bool = False
    moved: tuple[int, str] | None = None
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
    vessel_unit: str
    sizes: tuple[_Size, ...]
    syntheses: tuple[_Synthesis, ...] = ()
    # The molar mass in g/mol the fillings convert with, where the
    # vessel's unit and the items' differ in kind.
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
                    step_batches=(_StepBatch("salicylic-acid", "g", "5", 1,
                                        245, stored=True),),
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
                    step_batches=(_StepBatch("4-acetylbiphenyl", "g", "3", 1,
                                        396, ((398, 2, "2"),),
                                        suffix="FA"),
                               _StepBatch("4-acetylbiphenyl", "g", "1.5", 1,
                                        396, stored=True,
                                        suffix="FB")))),
        mass="198.26"),
    _Article(
        "1-phenylethanol", "1-phenylethanol",
        ("Alkohole", "Alcohols"), "mg",
        (_Size("100", "mg", final=8, opened=310),),
        (_Synthesis("aschmidt", 280, "aschmidt",
                    started=285, ended=312, report=314, qc=315,
                    fills=(311,), rest="150", recorded=305, flask=True,
                    moved=(311, "200")),),
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


ARTICLES += (
    _Article(
        "CH-0021", "benzilic-acid",
        ('Carbonsäuren', 'Carboxylic acids'), "g",
        (_Size("250", "mg", final=3, rate=1, filled=False),
         _Size("1", "g", final=1, rate=1, filled=False)),
        (_Synthesis("jkoch", 230, "jkoch", started=235,
                    ended=250, report=253, qc=255,
                    rest="8", location=DESICCATOR),),
    ),
    _Article(
        "CH-0022", "hexaphenylbenzene",
        ('Kohlenwasserstoffe', 'Hydrocarbons'), "g",
        (_Size("250", "mg", final=4, rate=2, filled=False),
         _Size("1", "g", final=2, rate=1, filled=False)),
        (_Synthesis("jkoch", 370, "jkoch", started=375,
                    sequence="SEQ-0004",
                    steps=("OSDB-0010", "OSDB-0011", "OSDB-0013",
                           "OSDB-0014"),
                    steps_done=((384, 1), (392, 2)),
                    journal=((384, 1, "CE-3/40"),
                             (392, 2, "CE-3/41")),
                    step_batches=(
                        _StepBatch("benzoin", "g", "8", 1, 384,
                                   stored=True),
                        _StepBatch("benzil", "g", "6", 2, 392,
                                   stored=True)), location=DESICCATOR),),
    ),
    _Article(
        "CH-0023", "biphenyl-4-ylmethanol",
        ('Alkohole', 'Alcohols'), "g",
        (_Size("250", "mg", final=5, rate=3, filled=False),
         _Size("1", "g", final=3, rate=1, filled=False)),
        (_Synthesis("jkoch", 232, "jkoch", started=237,
                    ended=252, report=255, qc=257,
                    rest="10", location=DESICCATOR),),
    ),
    _Article(
        "CH-0024", "n-benzylbiphenyl-4-carboxamide",
        ('Amide', 'Amides'), "g",
        (_Size("250", "mg", final=6, rate=1, filled=False),
         _Size("1", "g", final=4, rate=1, filled=False)),
    ),
    _Article(
        "CH-0025", "4-methoxycinnamic-acid",
        ('Carbonsäuren', 'Carboxylic acids'), "g",
        (_Size("250", "mg", final=7, rate=2, filled=False),
         _Size("1", "g", final=1, rate=1, filled=False)),
        (_Synthesis("jkoch", 234, "jkoch", started=239,
                    ended=254, report=257, qc=259,
                    rest="12", location=DESICCATOR),),
    ),
    _Article(
        "CH-0026", "ethanoanthracene-dicarboxylic-anhydride",
        ('Anhydride', 'Anhydrides'), "g",
        (_Size("250", "mg", final=3, rate=3, filled=False),
         _Size("1", "g", final=2, rate=1, filled=False)),
    ),
    _Article(
        "CH-0027", "2-butoxynaphthalene",
        ('Ether', 'Ethers'), "g",
        (_Size("250", "mg", final=4, rate=1, filled=False),
         _Size("1", "g", final=3, rate=1, filled=False)),
    ),
    _Article(
        "CH-0028", "isoborneol",
        ('Alkohole', 'Alcohols'), "g",
        (_Size("250", "mg", final=5, rate=2, filled=False),
         _Size("1", "g", final=4, rate=1, filled=False)),
    ),
    _Article(
        "CH-0029", "triphenylmethanol",
        ('Alkohole', 'Alcohols'), "g",
        (_Size("250", "mg", final=6, rate=3, filled=False),
         _Size("1", "g", final=1, rate=1, filled=False)),
        (_Synthesis("jkoch", 238, "jkoch", started=243,
                    ended=258, report=261, qc=263,
                    rest="16", location=DESICCATOR),),
    ),
    _Article(
        "CH-0030", "4-bromoacetanilide",
        ('Amide', 'Amides'), "g",
        (_Size("250", "mg", final=7, rate=1, filled=False),
         _Size("1", "g", final=2, rate=1, filled=False)),
    ),
    _Article(
        "CH-0031", "chalcone",
        ('Ketone', 'Ketones'), "g",
        (_Size("250", "mg", final=3, rate=2, filled=False),
         _Size("1", "g", final=3, rate=1, filled=False)),
    ),
    _Article(
        "CH-0032", "2-5-dimethyl-1-phenylpyrrole",
        ('Heterocyclen', 'Heterocycles'), "g",
        (_Size("250", "mg", final=4, rate=3, filled=False),
         _Size("1", "g", final=4, rate=1, filled=False)),
    ),
    _Article(
        "CH-0033", "ethyl-tetrahydropyrimidinone-carboxylate",
        ('Heterocyclen', 'Heterocycles'), "g",
        (_Size("250", "mg", final=5, rate=1, filled=False),
         _Size("1", "g", final=1, rate=1, filled=False)),
    ),
)


@dataclass(frozen=True)
class _Intermediate:
    """A substance without an article, by its KEY, that a synthesis
    yields a batch of, recorded from its step the day it ends, yielding
    AMOUNT in UNIT. With a SUPPLIER, a batch bought from it, with its
    ARTICLE and BATCH numbers, is received that day beside the batch
    made in the lab, which then yields MADE in UNIT, and the bought one
    AMOUNT."""

    key: str
    unit: str
    amount: str
    synthesis: _Synthesis
    supplier: str = ""
    article: str = ""
    batch: str = ""
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
        supplier="ChemPur GmbH", article="CP-4471", batch="CP240917",
        made="2"),
)


@dataclass(frozen=True)
class _Loose:
    """A batch of the substance SUBSTANCE, by its key, made in the lab
    before the application and recorded without a step on the day
    ENTERED, in days after the opening, by BY: it was MADE that many
    days after the opening, a negative number of days before it, and its
    stored vessel holds AMOUNT in UNIT at LOCATION."""

    substance: str
    unit: str
    amount: str
    made: int
    entered: int
    by: str
    location: Text


LOOSE = (
    _Loose("ethyl-cinnamate", "g", "8", -150, 3, "mwolf",
           ("Kühlschrank 2, Fach 2", "Fridge 2, shelf 2")),
    _Loose("methyl-salicylate", "g", "12", -220, 5, "tbauer",
           ("Exsikkator 1", "Desiccator 1")),
    _Loose("tetraphenylcyclopentadienone", "g", "8", -100, 7, "jkoch",
           DESICCATOR),
    _Loose("biphenyl-4-carboxylic-acid", "g", "10", -109, 8, "jkoch",
           DESICCATOR),
    _Loose("methyl-biphenyl-4-carboxylate", "g", "12", -118, 9, "jkoch",
           DESICCATOR),
    _Loose("camphor", "g", "14", -127, 10, "jkoch",
           DESICCATOR),
    _Loose("acetanilide", "g", "16", -136, 11, "jkoch",
           DESICCATOR),
    _Loose("methyl-benzoate", "g", "18", -145, 12, "jkoch",
           DESICCATOR),
)

# Bought stock: substance, supplier, catalogue number, supplier batch,
# opening mass and storage location.
COMMERCIAL = (
    ("ethanol", "Carl Roth", "9065", "L260301", "1970",
     ("Lösungsmittelschrank", "Solvent cabinet")),
    ("ethyl-acetate", "Merck", "100868", "L260302", "2250",
     ("Lösungsmittelschrank", "Solvent cabinet")),
    ("sodium-hydroxide", "Sigma-Aldrich", "71690", "L260303", "500",
     ("Laugenschrank", "Base cabinet")),
    ("1-3-diphenylacetone", "Sigma-Aldrich", "D204609", "L260100",
     "100", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("1-bromobutane", "TCI", "B0597", "L260101",
     "250", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("2-naphthol", "abcr", "AB117486", "L260102",
     "500", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("2-propanol", "Merck", "101207", "L260103",
     "1965", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("4-bromoacetophenone", "Carl Roth", "9141.5", "L260104",
     "100", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("4-methylbenzaldehyde", "Fluorochem", "F003003", "L260105",
     "250", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("4-methylbenzoic-acid", "VWR", "20923.336", "L260106",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("acetic-acid", "Alfa Aesar", "A10854", "L260107",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("acetic-anhydride", "Sigma-Aldrich", "D207145", "L260108",
     "100", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("acetone", "TCI", "B0893", "L260109",
     "1975", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("acetophenone", "abcr", "AB118870", "L260110",
     "500", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("activated-carbon", "Merck", "102111", "L260111",
     "1000", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("adipic-acid", "Carl Roth", "9293.5", "L260112",
     "100", ('Säureschrank', 'Acid cabinet')),
    ("ammonium-nitrate", "Fluorochem", "F004099", "L260113",
     "250", ('Oxidationsmittelschrank', 'Oxidiser cabinet')),
    ("aniline", "VWR", "21059.344", "L260114",
     "250", ('Sicherheitsschrank (Gift)', 'Safety cabinet (toxic)')),
    ("anisaldehyde", "Alfa Aesar", "A11278", "L260115",
     "1000", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("anthracene", "Sigma-Aldrich", "D209681", "L260116",
     "100", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("benzaldehyde", "TCI", "B1189", "L260117",
     "100", ('Kühlschrank 1', 'Fridge 1')),
    ("benzoic-acid", "abcr", "AB120254", "L260118",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("benzophenone", "Merck", "103015", "L260119",
     "1000", ('Sicherheitsschrank (Gift)', 'Safety cabinet (toxic)')),
    ("benzylamine", "Carl Roth", "9445.5", "L260120",
     "100", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("boric-acid", "Fluorochem", "F005195", "L260121",
     "250", ('Säureschrank', 'Acid cabinet')),
    ("borneol", "VWR", "21195.352", "L260122",
     "500", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("bromobenzene", "Alfa Aesar", "A11702", "L260123",
     "250", ('Sicherheitsschrank (Gift)', 'Safety cabinet (toxic)')),
    ("celite", "Sigma-Aldrich", "D212217", "L260124",
     "100", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("copper-ii-acetate", "TCI", "B1485", "L260125",
     "250", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("cyclohexanone", "abcr", "AB121638", "L260126",
     "500", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("diethyl-ether", "Merck", "103919", "L260127",
     "1780", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("dimethyl-sulfoxide", "Carl Roth", "9597.5", "L260128",
     "100", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("diphenyl-ether", "Fluorochem", "F006291", "L260129",
     "250", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("diphenylacetylene", "VWR", "21331.360", "L260130",
     "500", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("ethyl-acetoacetate", "Alfa Aesar", "A12126", "L260131",
     "1000", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("ethyl-lactate", "Sigma-Aldrich", "D214753", "L260132",
     "100", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("ethyl-triphenylphosphoranylidene-acetate", "TCI", "B1781", "L260133",
     "250", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("ethylbenzene", "abcr", "AB123022", "L260134",
     "2165", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("heptane", "Merck", "104823", "L260135",
     "1710", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("hexane", "Carl Roth", "9749.5", "L260136",
     "1650", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("hexane-2-5-dione", "Fluorochem", "F007387", "L260137",
     "250", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("hydrogen-chloride", "VWR", "21467.368", "L260138",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("iodine", "Alfa Aesar", "A12550", "L260139",
     "1000", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("iron-iii-chloride", "Sigma-Aldrich", "D217289", "L260140",
     "100", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("isopentyl-alcohol", "TCI", "B2077", "L260141",
     "250", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("lithium-chloride", "abcr", "AB124406", "L260142",
     "250", ('Exsikkator 1', 'Desiccator 1')),
    ("magnesium", "Merck", "105727", "L260143",
     "250", ('Exsikkator 2', 'Desiccator 2')),
    ("maleic-anhydride", "Carl Roth", "9901.5", "L260144",
     "250", ('Exsikkator 2', 'Desiccator 2')),
    ("malonic-acid", "Fluorochem", "F008483", "L260145",
     "250", ('Säureschrank', 'Acid cabinet')),
    ("methanol", "VWR", "21603.376", "L260146",
     "1980", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("methyl-salicylate", "Alfa Aesar", "A12974", "L260147",
     "1000", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("palladium-acetate", "Sigma-Aldrich", "D219825", "L260148",
     "100", ('Kühlschrank 1', 'Fridge 1')),
    ("petroleum-ether", "TCI", "B2373", "L260149",
     "1600", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("phenethyl-alcohol", "abcr", "AB125790", "L260150",
     "500", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("phenylboronic-acid", "Merck", "106631", "L260151",
     "1000", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("phosphoric-acid", "Carl Roth", "10053.5", "L260152",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("piperidine", "Fluorochem", "F009579", "L260153",
     "250", ('Sicherheitsschrank (Gift)', 'Safety cabinet (toxic)')),
    ("potassium-carbonate", "VWR", "21739.334", "L260154",
     "500", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("potassium-hydroxide", "Alfa Aesar", "A13398", "L260155",
     "500", ('Laugenschrank', 'Base cabinet')),
    ("pyridine", "Sigma-Aldrich", "D222361", "L260156",
     "250", ('Sicherheitsschrank (Gift)', 'Safety cabinet (toxic)')),
    ("sodium-acetate", "TCI", "B2669", "L260157",
     "250", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("sodium-borohydride", "abcr", "AB127174", "L260158",
     "100", ('Exsikkator 1', 'Desiccator 1')),
    ("sodium-bromide", "Merck", "107535", "L260159",
     "1000", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("sodium-chloride", "Carl Roth", "10205.5", "L260160",
     "100", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("sodium-hydrogen-carbonate", "Fluorochem", "F010675", "L260161",
     "250", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("sodium-hydrogen-sulfite", "VWR", "21875.342", "L260162",
     "500", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("sodium-hypochlorite", "Alfa Aesar", "A13822", "L260163",
     "500", ('Laugenschrank', 'Base cabinet')),
    ("sodium-sulfate", "Sigma-Aldrich", "D224897", "L260164",
     "100", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("succinic-acid", "TCI", "B2965", "L260165",
     "250", ('Säureschrank', 'Acid cabinet')),
    ("sulfuric-acid", "abcr", "AB128558", "L260166",
     "500", ('Säureschrank', 'Acid cabinet')),
    ("tetrabutylammonium-bromide", "Merck", "108439", "L260167",
     "1000", ('Chemikalienschrank 2', 'Chemicals cabinet 2')),
    ("tetrahydrofuran", "Carl Roth", "10357.5", "L260168",
     "2220", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("thiamine-hydrochloride", "Fluorochem", "F011771", "L260169",
     "250", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("toluene", "VWR", "22011.350", "L260170",
     "2170", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("urea", "Alfa Aesar", "A14246", "L260171",
     "1000", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
    ("vanillin", "Sigma-Aldrich", "D227433", "L260172",
     "100", ('Chemikalienschrank 1', 'Chemicals cabinet 1')),
    ("xylene", "TCI", "B3261", "L260173",
     "2150", ('Lösungsmittelschrank', 'Solvent cabinet')),
    ("silica", "Merck", "107734", "TA2214034",
     "1000", ('Chemikalienschrank 3', 'Chemicals cabinet 3')),
)

# Where the second bottle of a chemical stands, apart from the first.
SECOND_PLACES: dict[str, Text] = {
    "benzaldehyde": ("Kühlschrank 2", "Fridge 2"),
    "methanol": ("Lösungsmittelschrank (Labor 2)", "Solvent cabinet (lab 2)"),
    "acetone": ("Lösungsmittelschrank (Labor 2)", "Solvent cabinet (lab 2)"),
    "vanillin": ("Chemikalienschrank 3", "Chemicals cabinet 3"),
}

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
# corrected: its article, its position and the day. The vessel corrected:
# its article, the position of its synthesis, the day and the amount
# found missing. The historical note entered twice, by its position.
REVERSED = ("CH-0016", 0, 14)
CORRECTED = ("CH-0016", 1, 180)
CORRECTED_VESSEL = ("CH-0016", 2, 370, "1.5")
DUPLICATED = 2
# The number of the batch of an article's old stock starts with this
# text, and ends with the article number.
LEGACY_PREFIX = "ALT-"
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
    "vessel correction": ("Nachgewogen.", "Weighed again."),
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


# Ranks of the changes of one day: a task ends after its product batch
# is recorded and its flask emptied.
ACCOUNT, REGISTRY, PARAMETERS, ITEM, TASK, BATCH, END, FILL, WITHDRAWAL, \
    TRANSFER, NOTE, REVERSAL, CORRECTION, ENTRY, HISTORICAL, \
    VESSEL_CORRECTION, STATUS = range(17)


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
    """The amount COUNT containers of SIZE take from a vessel of ARTICLE,
    in the vessel's unit, rounded half up to three places."""
    base = Decimal(count) * Decimal(size.size) * FACTOR[size.unit]
    if (size.unit in MASS_UNITS) != (article.vessel_unit in MASS_UNITS):
        mass = Decimal(article.mass)
        base = (base * 1000 / mass if size.unit in MASS_UNITS
                else base * mass / 1000)
    return (base / FACTOR[article.vessel_unit]).quantize(
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
    orders: list[tuple[date, str, str, int]] = []
    numbers = _numbers(line)
    for article in ARTICLES:
        orders += _article(line, article, numbers)
    for intermediate in INTERMEDIATES:
        _intermediate(line, intermediate, numbers)
    _loose(line, numbers)
    for key, article, batch in (
            ("ethanol", "2509.2500", "CP260101"),
            ("ethyl-acetate", "3317.2500", "CP260102"),
            ("sodium-hydroxide", "6078.0500", "CP260103")):
        line.add(line.day(1), BATCH, RecordBatch, user="mwolf",
                 key=f"purchased/{key}", substance=key, source="bought",
                 number="", supplier="ChemPur GmbH",
                 supplier_article_number=article, supplier_batch=batch,
                 unit="g", amount=Decimal("500"),
                 location=line.text(
                     ("Laugenschrank", "Base cabinet")
                     if key == "sodium-hydroxide" else
                     ("Lösungsmittelschrank", "Solvent cabinet")),
                 date=line.day(1))
    for index, (key, supplier, article, batch, amount, location) in enumerate(
            COMMERCIAL):
        vessel = f"commercial/{key}"
        line.add(line.day(2), BATCH, RecordBatch, user="mwolf",
                 key=vessel, substance=key, source="bought", number="",
                 supplier=supplier, supplier_article_number=article,
                 supplier_batch=batch, unit="g", amount=Decimal(amount) * (
                     Decimal("0.7") if index % 5 == 0 else Decimal("1")),
                 location=line.text(location), date=line.day(2))
        if index % 5 == 0 or key in SECOND_PLACES:
            line.add(line.day(12 + index), BATCH, OpenVessel,
                     user="mwolf", vessel=vessel)
    for index, key in enumerate(("benzaldehyde", "methanol", "acetone",
                                 "vanillin")):
        line.add(line.day(10), BATCH, RecordBatch, user="tbauer",
                 key=f"commercial/{key}/second", substance=key,
                 source="bought", number="", supplier="Carl Roth",
                 supplier_article_number=("4184.1", "4627.1", "9372.1",
                                          "3823.1")[index],
                 supplier_batch=f"R{260200 + index}", unit="g",
                 amount=Decimal("250"),
                 location=line.text(SECOND_PLACES[key]),
                 date=line.day(10))
    _notes(line, orders)
    return line.changes()


def _initials(user: str) -> str:
    """The initials of the demo account USER, by its user name."""
    return next(account.initials for account in ACCOUNTS
                if account.username == user)


def _last(synthesis: _Synthesis) -> int:
    """The position of the last step of SYNTHESIS, a task with one
    plain step when it follows no sequence."""
    return len(synthesis.steps) or 1


def _numbers(line: _Timeline) -> dict[tuple[str, Any], str]:
    """The number of each made batch: of each synthesis that ends, by its
    article, or its intermediate's key, and its position; of each batch
    a step makes, by its synthesis's key and its position among the
    step batches; and of each loose batch, by ``loose`` and its
    position.

    A number is the initials of the account that records the batch, the
    year of its day and a serial of three digits, numbered in the order
    of the days the batches are made, then the suffix of a step batch.
    """
    syntheses = [(article.number, position, synthesis)
                 for article in ARTICLES
                 for position, synthesis in enumerate(article.syntheses)]
    syntheses += [(intermediate.key, 0, intermediate.synthesis)
                  for intermediate in INTERMEDIATES]
    made: list[tuple[date, tuple[str, Any], str, str]] = []
    for number, position, synthesis in syntheses:
        if synthesis.ended is not None:
            day = line.day(synthesis.recorded if synthesis.recorded
                           is not None else synthesis.ended)
            made.append((day, (number, position),
                         _initials(synthesis.by), ""))
        made += [(line.day(batch.made), (f"{number}#{position}", index),
                  _initials(synthesis.by), batch.suffix)
                 for index, batch in enumerate(synthesis.step_batches)]
    made += [(line.day(loose.made), ("loose", index), _initials(loose.by),
              "") for index, loose in enumerate(LOOSE)]
    return {key: f"{initials}{day:%y}{serial:03d}{suffix}"
            for serial, (day, key, initials, suffix)
            in enumerate(sorted(made, key=lambda entry: entry[0]), 1)}


def _article(line: _Timeline, article: _Article,
             numbers: dict[tuple[str, Any], str]) -> list[
                 tuple[date, str, str, int]]:
    """Add the changes of ARTICLE but its delivery notes, and return its
    order lines, each a day, an item key, a batch key and a count.

    The article's orders from before the opening name its batch of old
    stock, recorded by its number alone on the opening day; the later
    ones name the batches the items' containers are of (``_share_out``).
    """
    history = quarter_start(back(quarter_of(line.opening), 1))
    yields = set()
    for position, synthesis in enumerate(article.syntheses):
        key = f"{article.number}#{position}"
        _task(line, key, article.substance, synthesis)
        _step_batches(line, key, synthesis, numbers)
        if synthesis.ended is not None:
            yields.add(position)
    opportunities = sorted(
        (offset, position) for position, synthesis
        in enumerate(article.syntheses) if position in yields
        for offset in synthesis.fills)
    taken: dict[int, Decimal] = defaultdict(Decimal)
    found = []
    legacy = f"{article.number}/legacy"
    for turn, size in enumerate(article.sizes):
        key = size_key(article.number, size)
        own = _orders(line, size, history)
        found += [(day, key, legacy, count) for day, count in own
                  if day < line.opening]
        found += _size(line, article, turn, size, key, own, opportunities,
                       taken, legacy)
    if found:
        line.add(line.opening, BATCH, RecordBatch, user="klehmann",
                 key=legacy, substance=article.substance, source="made",
                 number=f"{LEGACY_PREFIX}{article.number}", supplier="",
                 supplier_article_number="", supplier_batch="", unit="",
                 amount=None, location="", date=None)
    for position in sorted(yields):
        synthesis = article.syntheses[position]
        key = f"{article.number}#{position}"
        moved = Decimal(synthesis.moved[1]) if synthesis.moved else 0
        _product(line, key, article.substance, article.vessel_unit,
                 taken[position] + moved + Decimal(synthesis.rest),
                 synthesis, numbers[(article.number, position)])
        if synthesis.moved:
            offset, _amount = synthesis.moved
            line.add(line.day(offset), TRANSFER, Transfer,
                     user=staff(offset), vessel=key, amount=moved,
                     location=line.text(synthesis.location))
    if article.number == CORRECTED_VESSEL[0]:
        _, position, offset, less = CORRECTED_VESSEL
        rest = Decimal(article.syntheses[position].rest)
        line.add(line.day(offset), VESSEL_CORRECTION, CorrectVessel,
                 user=staff(offset), vessel=f"{article.number}#{position}",
                 amount=rest - Decimal(less),
                 note=line.text(NOTES["vessel correction"]))
    return found


def _product(line: _Timeline, key: str, substance: str, unit: str,
             amount: Decimal, synthesis: _Synthesis, number: str) -> None:
    """Record the product batch KEY of SYNTHESIS, of the substance
    SUBSTANCE by its key and with the number NUMBER, from the last step
    of its task, yielding AMOUNT in UNIT, on the day the synthesis
    records it: in its flask, or stored at its location."""
    recorded = line.day(synthesis.recorded if synthesis.recorded
                        is not None else synthesis.ended)
    line.add(recorded, BATCH, RecordBatch, user=synthesis.by, key=key,
             substance=substance, source="made", number=number,
             supplier="", supplier_article_number="", supplier_batch="",
             unit=unit, amount=amount,
             location="" if synthesis.flask
             else line.text(synthesis.location),
             date=recorded, step=(key, _last(synthesis)))


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
          taken: dict[int, Decimal], legacy: str
          ) -> list[tuple[date, str, str, int]]:
    """Add the opening count, entered consumption, fillings and
    corrections of the item KEY, so that its stock covers its ORDERS
    and is ``size.final`` on the seeding day, and return the lines of
    its orders from the opening on, each a day, KEY, a batch key and a
    count.

    The opening count is of unknown batch. LEGACY is the key of the
    article's batch of old stock, which a line names for containers of
    unknown batch.

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
        amount = amount_of(article, size, count)
        taken[position] += amount
        line.add(day, FILL, Fill, user=staff((day - line.opening).days,
                                             turn),
                 item=key, vessel=f"{article.number}#{position}",
                 count=count, amount=amount)
    lines, corrected = _share_out(
        opening, [(day, f"{article.number}#{position}", count)
                  for day, position, count in booked],
        current, current.index(reversal) if reversal else None,
        correction, legacy, key)
    if corrected:
        line.add(correction, CORRECTION, Correct,
                 user=staff(CORRECTED[2]), item=key, batch=corrected[0],
                 count=corrected[1], note=line.text(NOTES["correction"]))
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
    return [(order[0], key, batch, count)
            for order, split in zip(current, lines)
            for batch, count in split]


def _share_out(opening: int, fills: list[tuple[date, str, int]],
               orders: list[tuple[date, int]], reversed_order: int | None,
               corrected: date | None, legacy: str, key: str
               ) -> tuple[list[list[tuple[str, int]]],
                          tuple[str | None, int] | None]:
    """Follow the shares of the item KEY through the day's changes and
    return the batches of each of its ORDERS, and the correction.

    The item opens with OPENING containers of unknown batch. FILLS are
    a day, a batch key and a count each; ORDERS a day and a count each.
    An order takes from the batches filled last first; what they do not
    hold it takes from the item's old stock, naming the batch LEGACY,
    which the booking fills from the containers of unknown batch. An
    order that no single batch covers is several lines. The order
    REVERSED_ORDER, a position or None, is reversed two days after its
    day and returns each line's containers to its batch. On the day
    CORRECTED, or none, one container is found missing from the share
    of unknown batch, or from the largest share when that holds none.

    Return, for each order, the pairs of a batch key and a count that
    its lines hold, and the correction as the batch key, None for
    unknown batch, and the count its share is set to. Raise ValueError
    when an order is not covered.
    """
    events = [(day, FILL, n, "fill", (batch, count))
              for n, (day, batch, count) in enumerate(fills)]
    events += [(day, NOTE, n, "order", n)
               for n, (day, _count) in enumerate(orders)]
    if reversed_order is not None:
        events.append((orders[reversed_order][0] + timedelta(days=2),
                       REVERSAL, 0, "reversal", reversed_order))
    if corrected is not None:
        events.append((corrected, CORRECTION, 0, "correction", None))
    held: dict[str | None, int] = {None: opening}
    recency: dict[str, int] = {}
    lines: list[list[tuple[str, int]]] = [[] for _ in orders]
    correction = None
    for turn, (day, _rank, _n, kind, what) in enumerate(
            sorted(events, key=lambda event: event[:3])):
        if kind == "fill":
            held[what[0]] = held.get(what[0], 0) + what[1]
            recency[what[0]] = turn
        elif kind == "order":
            remaining = orders[what][1]
            known = sorted((batch for batch, count in held.items()
                            if batch not in (None, legacy) and count),
                           key=lambda batch: recency[batch], reverse=True)
            for batch in [*known, legacy]:
                own = held.get(batch, 0)
                take = min(remaining, own + (held[None]
                                             if batch == legacy else 0))
                if take == 0:
                    continue
                if batch == legacy:
                    held[None] -= max(take - own, 0)
                    own = max(own, take)
                held[batch] = own - take
                lines[what].append((batch, take))
                remaining -= take
            if remaining:
                raise ValueError(f"{key} runs out on {day}")
        elif kind == "reversal":
            for batch, count in lines[what]:
                held[batch] = held.get(batch, 0) + count
        else:
            target = None if held[None] else max(
                held, key=lambda batch: held[batch])
            held[target] -= 1
            correction = (target, held[target])
    return lines, correction


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
                  numbers: dict[tuple[str, Any], str]) -> None:
    """Add the task of INTERMEDIATE and the batch it yields the day it
    ends, recorded from its step and stored; beside it, when the
    intermediate has a supplier, the batch bought from it that day."""
    synthesis = intermediate.synthesis
    key = f"{intermediate.key}#0"
    _task(line, key, intermediate.key, synthesis)
    _product(line, key, intermediate.key, intermediate.unit,
             Decimal(intermediate.made or intermediate.amount), synthesis,
             numbers[(intermediate.key, 0)])
    if intermediate.supplier:
        made = line.day(synthesis.ended)
        line.add(made, BATCH, RecordBatch, user=synthesis.by,
                 key=f"{key}/bought", substance=intermediate.key,
                 source="bought", number="", supplier=intermediate.supplier,
                 supplier_article_number=intermediate.article,
                 supplier_batch=intermediate.batch, unit=intermediate.unit,
                 amount=Decimal(intermediate.amount),
                 location=line.text(synthesis.location), date=made)


def _loose(line: _Timeline, numbers: dict[tuple[str, Any], str]) -> None:
    """Record the LOOSE batches, each without a step, with its stored
    vessel."""
    for index, found in enumerate(LOOSE):
        line.add(line.day(found.entered), BATCH, RecordBatch, user=found.by,
                 key=f"loose#{index}", substance=found.substance,
                 source="made", number=numbers[("loose", index)],
                 supplier="", supplier_article_number="", supplier_batch="",
                 unit=found.unit, amount=Decimal(found.amount),
                 location=line.text(found.location),
                 date=line.day(found.made))


def _step_batches(line: _Timeline, key: str, synthesis: _Synthesis,
               numbers: dict[tuple[str, Any], str]) -> None:
    """Record the batches the steps of the task KEY of SYNTHESIS make,
    each the day it is made, and the withdrawals from their flasks into
    its steps."""
    for index, made in enumerate(synthesis.step_batches):
        vessel = f"{key}/{index}"
        line.add(line.day(made.made), BATCH, RecordBatch, user=synthesis.by,
                 key=vessel, substance=made.substance, source="made",
                 number=numbers[(key, index)], supplier="",
                 supplier_article_number="", supplier_batch="",
                 unit=made.unit, amount=Decimal(made.amount),
                 location=line.text(synthesis.location) if made.stored
                 else "", date=line.day(made.made),
                 step=(key, made.position))
        for offset, position, amount in made.withdrawals:
            line.add(line.day(offset), WITHDRAWAL, Withdraw,
                     user=synthesis.assignee or synthesis.by,
                     vessel=vessel, task=key, position=position,
                     amount=Decimal(amount))


def _task(line: _Timeline, key: str, substance: str,
          synthesis: _Synthesis) -> None:
    """Add the changes of the task KEY of SYNTHESIS, of the substance
    SUBSTANCE by its key: its creation, then its start, steps, end or
    failure, report, QC list and cancellation, each on its day, and the
    journal entries its steps name, each after the day's other changes
    of the task; an end comes after the day's batches. A task that ends
    without a sequence has one plain step."""
    total = len(synthesis.steps) or (1 if synthesis.ended is not None
                                     else None)
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
        ended = {"ended": line.day(synthesis.ended)}
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


def _notes(line: _Timeline, orders: list[tuple[date, str, str, int]]
           ) -> None:
    """Add the delivery notes of ORDERS, each a day, an item key, a batch
    key and a count: one note a day, numbered by year in the order of
    their dates; historical for the days before the opening, entered in
    its first weeks, one of them twice and reversed; and the reversal of
    the delivery ``REVERSED`` names."""
    by_day: dict[date, list[tuple[str, str, int]]] = defaultdict(list)
    for day, key, batch, count in orders:
        by_day[day].append((key, batch, count))
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
