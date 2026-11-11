"""The table diagram: the application's tables read from its models and
drawn as a standalone HTML page."""

import html
import inspect
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from pathlib import Path

from django.apps import apps
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import F, Q
from django.db.models.fields import NOT_PROVIDED
from django.db.utils import load_backend
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.safestring import SafeString, mark_safe
from simple_history.models import HistoricalChanges

WEBAPP = Path(__file__).resolve().parents[1]
OUTPUT = WEBAPP / "docs" / "database-schema.html"

# The table every record names a person by; its links have a kind of
# their own.
HUB = "accounts_user"
# The name of the one box that stands for every history table.
HISTORY = "‹app›_historical‹model›"


class LayoutError(ValueError):
    """An arrangement the generator cannot draw."""


@dataclass(frozen=True)
class Column:
    """A column as the diagram shows it.

    KEY is ``PK``, ``1:1``, ``FK``, ``UQ`` or empty. REF names the table
    a foreign key references, REF_COLUMN its column, ON_DELETE the
    delete rule's name. CHECK is the check the column carries without
    its name, such as ``>= 0``. A column whose TYPE is empty stands for
    several columns.
    """

    name: str
    type: str
    nullable: bool = False
    key: str = ""
    ref: str | None = None
    ref_column: str = "id"
    on_delete: str | None = None
    check: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Table:
    """A table: its NAME, the package APP it belongs to and its COLUMNS.

    ABOUT is the first paragraph of its model's docstring and DOC every
    paragraph. HISTORY names its history table, if it keeps one. COUNT
    is the number of tables its box stands for.
    """

    name: str
    app: str
    columns: tuple[Column, ...]
    about: str = ""
    doc: tuple[str, ...] = ()
    history: str | None = None
    count: int = 1


@dataclass(frozen=True)
class HistoryTable:
    """A history table NAME of the table TRACKED, leaving out the
    columns OMITTED."""

    name: str
    tracked: str
    omitted: tuple[str, ...]


@dataclass(frozen=True)
class Constraint:
    """A constraint of TABLE: KIND ``unique`` over COLUMNS, or ``check``
    of CONDITION; a unique constraint may also have a CONDITION. NAME is
    None for a ``unique_together`` entry."""

    table: str
    name: str | None
    kind: str
    columns: tuple[str, ...] = ()
    condition: str | None = None


@dataclass(frozen=True)
class Link:
    """A link the models do not hold, drawn from SOURCE.COLUMN to
    TARGET.TARGET_COLUMN, labelled LABEL where it fits; NOTE tells how
    it matches."""

    source: str
    column: str
    target: str
    target_column: str
    label: str
    note: str = ""


@dataclass(frozen=True)
class Schema:
    """What the diagram shows.

    TABLES are the application's tables and HISTORY the box that stands
    for HISTORY_TABLES. POSITIVE_CHECKS name the ``table.column``
    carrying a ``>= 0`` check; NULL_NOTES are ``(constraint, table,
    column)`` for each nullable column of a unique constraint.
    FRAMEWORK names every other table. PACKAGES are ``(label, name)``
    of the packages that have tables.
    """

    tables: tuple[Table, ...]
    history: Table
    history_tables: tuple[HistoryTable, ...]
    constraints: tuple[Constraint, ...]
    positive_checks: tuple[str, ...]
    null_notes: tuple[tuple[str, str, str], ...]
    framework: tuple[str, ...]
    packages: tuple[tuple[str, str], ...]


GRID = (
    (("inventory_deliverynote",), ("inventory_movement",),
     ("inventory_lotmovement",), (HUB,), ("collection_import",)),
    (("inventory_deliveryline",), ("inventory_item",),
     ("inventory_enteredconsumption",), ("inventory_lot",),
     ("collection_procedure", "collection_scopeentry")),
    (("inventory_article",), ("registry_substance",),
     ("registry_substanceclass",), ("tasks_task",),
     ("collection_entrysubstance",)),
    (("vocabulary_group", "vocabulary_project"),
     ("vocabulary_chemicalclass", "vocabulary_reactiontype"),
     ("tasks_counter", HISTORY), ("planning_parameters", "demo_demomark"),
     ("collection_sequence", "collection_step")),
)

LINKS = (
    Link("tasks_task", "batch", "inventory_lot", "batch", "same batch",
         "A lot belongs to a task when the two share a batch and the "
         "task's substance is the lot's."),
    Link("tasks_counter", "name", "tasks_task", "number", "T-###",
         "The counter named task issues the task numbers, T- and at "
         "least three digits."),
)

# Light and dark colour of each package's boxes.
COLOURS = {
    "inventory": ("#0e7378", "#45c2c6"),
    "registry": ("#b0306a", "#ef7fb1"),
    "vocabulary": ("#7a6a12", "#cdbb52"),
    "accounts": ("#a5650c", "#e5a64c"),
    "tasks": ("#4652c4", "#929cff"),
    "planning": ("#3a7f33", "#7cc673"),
    "demo": ("#66717b", "#a2abb4"),
    "collection": ("#1d6a96", "#68b1df"),
    "history": ("#84479a", "#c98ddd"),
}

# The kinds of line, their switches' labels and whether they start on.
KINDS = (("key", "Foreign keys", True),
         ("user", "To accounts_user", False),
         ("value", "Matched by value", True))

OPERATORS = {"exact": "=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
SHORT_TYPES = {"timestamp with time zone": "timestamptz",
               "double precision": "float8"}


def postgres() -> BaseDatabaseWrapper:
    """Return a PostgreSQL connection object that is never opened, to
    ask fields for their types and checks."""
    backend = load_backend("django.db.backends.postgresql")
    return backend.DatabaseWrapper({
        "ENGINE": "django.db.backends.postgresql", "NAME": "", "USER": "",
        "PASSWORD": "", "HOST": "", "PORT": "", "OPTIONS": {},
        "TIME_ZONE": None, "CONN_MAX_AGE": 0, "CONN_HEALTH_CHECKS": False,
        "AUTOCOMMIT": True, "ATOMIC_REQUESTS": False, "TEST": {}},
        alias="schema_diagram")


def short_type(db_type: str) -> str:
    """Return DB_TYPE with its long names shortened and no spaces in its
    arguments."""
    for long, short in SHORT_TYPES.items():
        db_type = db_type.replace(long, short)
    return re.sub(r",\s+", ",", db_type)


def literal(value: object, model: type[models.Model]) -> str:
    """Return VALUE written as SQL, a field reference as its column.

    Raises ValueError for a value of another kind.
    """
    if isinstance(value, F):
        return model._meta.get_field(value.name).column
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    raise ValueError(f"cannot write the value {value!r} as SQL")


def comparison(lookup: str, value: object,
               model: type[models.Model]) -> str:
    """Return the comparison LOOKUP=VALUE of MODEL written as SQL.

    Raises ValueError for a lookup across a relation or one other than
    ``exact``, ``gt``, ``gte``, ``lt``, ``lte`` and ``isnull``.
    """
    name, _, operator = lookup.partition("__")
    operator = operator or "exact"
    if operator != "isnull" and operator not in OPERATORS:
        raise ValueError(f"cannot write the lookup {operator!r} of "
                         f"{model._meta.db_table} as SQL")
    column = model._meta.get_field(name).column
    if operator == "isnull":
        return f"{column} IS {'' if value else 'NOT '}NULL"
    if value is None:
        return f"{column} IS NULL"
    return f"{column} {OPERATORS[operator]} {literal(value, model)}"


def condition_text(condition: Q, model: type[models.Model],
                   nested: bool = False) -> str:
    """Return CONDITION, a ``Q`` over the fields of MODEL, written as SQL.

    Comparisons join by the condition's connector; a nested condition of
    several parts is put in parentheses, a negated one is written
    ``NOT (…)``. Raises ValueError as ``comparison`` does.
    """
    parts = [condition_text(child, model, nested=True)
             if isinstance(child, Q) else comparison(*child, model)
             for child in condition.children]
    joined = f" {condition.connector} ".join(parts)
    if condition.negated:
        return f"NOT ({joined})"
    return f"({joined})" if nested and len(parts) > 1 else joined


def paragraphs(model: type[models.Model]) -> tuple[str, ...]:
    """Return the paragraphs of MODEL's docstring, each on one line, or
    none when the model has only the docstring Django gives it."""
    doc = inspect.getdoc(model) or ""
    if re.fullmatch(rf"{model.__name__}\(.*\)", doc, re.DOTALL):
        return ()
    return tuple(" ".join(part.split()) for part in re.split(r"\n\s*\n", doc)
                 if part.strip())


def shown(value: object) -> str:
    """Return VALUE as a note shows it."""
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def notes_of(field: models.Field, check: str | None) -> tuple[str, ...]:
    """Return the notes the model gives on FIELD, whose column carries
    CHECK.

    The bounds are those of the validators the field declares, not the
    range Django derives from the database.
    """
    notes = []
    if field.choices:
        notes.append("values " + " · ".join(
            shown(value) for value, _ in field.flatchoices))
    low = high = None
    for validator in field._validators:
        if isinstance(validator, MinValueValidator):
            low = validator.limit_value
        elif isinstance(validator, MaxValueValidator):
            high = validator.limit_value
    if low is not None and high is not None:
        notes.append(f"from {shown(low)} to {shown(high)}")
    elif low is not None:
        notes.append(f"at least {shown(low)}")
    elif high is not None:
        notes.append(f"at most {shown(high)}")
    if field.default is not NOT_PROVIDED and not callable(field.default):
        notes.append(f"default {shown(field.default)}")
    if field.db_index and not field.is_relation and not field.unique:
        notes.append("indexed")
    if check:
        notes.append(f"CHECK {check}")
    if field.help_text:
        notes.append(str(field.help_text))
    return tuple(notes)


def column_of(field: models.Field,
              connection: BaseDatabaseWrapper) -> Column:
    """Return FIELD as a column, typed as CONNECTION creates it."""
    check = field.db_check(connection)
    if check:
        check = re.sub(r'^"[^"]+"\s*', "", check)
    ref = ref_column = on_delete = None
    if field.primary_key and not field.is_relation:
        key = "PK"
    elif field.is_relation:
        key = "PK" if field.primary_key else \
            "1:1" if field.one_to_one or field.unique else "FK"
        ref = field.related_model._meta.db_table
        ref_column = field.target_field.column
        on_delete = field.remote_field.on_delete.__name__
    else:
        key = "UQ" if field.unique else ""
    return Column(field.column, short_type(field.db_type(connection)),
                  nullable=field.null, key=key, ref=ref,
                  ref_column=ref_column or "id", on_delete=on_delete,
                  check=check, notes=notes_of(field, check))


def own(model: type[models.Model]) -> bool:
    """Whether MODEL belongs to a package of the application."""
    return Path(model._meta.app_config.path).parent == WEBAPP


def history_model(model: type[models.Model]) -> type[models.Model] | None:
    """Return the historical model of MODEL, or None when it keeps no
    history."""
    attribute = getattr(model._meta, "simple_history_manager_attribute",
                        None)
    return getattr(model, attribute).model if attribute else None


def constraints_of(model: type[models.Model]) -> list[Constraint]:
    """Return the unique and check constraints of MODEL.

    Raises ValueError naming the constraint when its condition cannot be
    written as SQL, or for a constraint of another kind.
    """
    table = model._meta.db_table
    found = []
    for constraint in model._meta.constraints:
        try:
            if isinstance(constraint, models.UniqueConstraint):
                found.append(Constraint(
                    table, constraint.name, "unique",
                    tuple(model._meta.get_field(name).column
                          for name in constraint.fields),
                    condition_text(constraint.condition, model)
                    if constraint.condition else None))
            elif isinstance(constraint, models.CheckConstraint):
                found.append(Constraint(
                    table, constraint.name, "check",
                    condition=condition_text(constraint.condition, model)))
            else:
                raise ValueError(f"cannot show a {type(constraint).__name__}")
        except ValueError as error:
            raise ValueError(f"{table}, constraint {constraint.name}: "
                             f"{error}") from error
    for names in model._meta.unique_together:
        found.append(Constraint(
            table, None, "unique",
            tuple(model._meta.get_field(name).column for name in names)))
    return found


def collect() -> Schema:
    """Return the application's tables as the diagram shows them, read
    from the models in English, typed as PostgreSQL creates them.

    Raises ValueError for a constraint the page cannot show.
    """
    with translation.override("en"):
        return _collect(postgres())


def _collect(connection: BaseDatabaseWrapper) -> Schema:
    every = apps.get_models(include_auto_created=True)
    historical = [m for m in every if issubclass(m, HistoricalChanges)]
    mine = sorted((m for m in every if own(m) and m not in historical
                   and not m._meta.auto_created),
                  key=lambda m: m._meta.db_table)
    tables, history_tables, constraints = [], [], []
    for model in mine:
        name = model._meta.db_table
        columns = [column_of(f, connection)
                   for f in model._meta.concrete_fields]
        past = history_model(model)
        if past:
            kept = {f.column for f in past._meta.concrete_fields}
            omitted = tuple(c.name for c in columns if c.name not in kept)
            columns = [replace(c, notes=(*c.notes, "not in history"))
                       if c.name in omitted else c for c in columns]
            history_tables.append(
                HistoryTable(past._meta.db_table, name, omitted))
        doc = paragraphs(model)
        tables.append(Table(name, model._meta.app_label, tuple(columns),
                            about=doc[0] if doc else "", doc=doc,
                            history=past._meta.db_table if past else None))
        constraints += constraints_of(model)
    # The layout is drawn from a history table of a row with an ``id``.
    sample = min((m for m in historical if any(
        f.name == "id" for f in m._meta.concrete_fields)),
        key=lambda m: m._meta.db_table)
    fields = sample._meta.concrete_fields
    layout = [column_of(f, connection) for f in fields
              if f.name == "id" or f.name.startswith("history_")]
    layout.insert(1, Column("… tracked columns", ""))
    history = Table(
        HISTORY, "history", tuple(layout),
        about="The layout of every history table: one row per saved "
              "change of a tracked row, holding its columns then.",
        count=len(historical))
    by_name = {t.name: t for t in tables}
    null_notes = tuple(
        (c.name, c.table, column) for c in constraints
        if c.kind == "unique" and c.name for column in c.columns
        if next(x for x in by_name[c.table].columns
                if x.name == column).nullable)
    return Schema(
        tables=tuple(tables), history=history,
        history_tables=tuple(sorted(history_tables, key=lambda h: h.name)),
        constraints=tuple(sorted(constraints,
                                 key=lambda c: (c.table, c.name or ""))),
        positive_checks=tuple(f"{t.name}.{c.name}" for t in tables
                              for c in t.columns if c.check == ">= 0"),
        null_notes=null_notes,
        framework=tuple(sorted(m._meta.db_table for m in every
                               if m not in mine and m not in historical)),
        packages=tuple(sorted({(m._meta.app_label,
                                str(m._meta.app_config.verbose_name))
                               for m in mine})))


# Geometry, in SVG user units.
ROW, HEAD, PAD = 17, 30, 7
MARGIN, TOP = 24, 24
COLUMN_GAP, BAND_GAP, SLOT_GAP = 66, 70, 60
GAP_LANE, CORRIDOR_LANE, COLUMN_LANE = 12, 10, 16
MIN_WIDTH = 240
NAME_ADVANCE, TYPE_ADVANCE, TITLE_ADVANCE = 6.6, 6.0, 6.4
LABEL_ADVANCE = 5.7

Point = tuple[float, float]
Grid = Sequence[Sequence[Sequence[str] | None]]


@dataclass(frozen=True)
class Box:
    """The box of TABLE, its top left corner at LEFT, TOP."""

    table: Table
    left: float
    top: float
    width: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + HEAD + len(self.table.columns) * ROW + PAD

    @property
    def centre(self) -> float:
        return self.left + self.width / 2

    def row_y(self, column: str) -> float:
        """Return the middle height of COLUMN's row.

        Raises LayoutError when the table has no such column.
        """
        for index, found in enumerate(self.table.columns):
            if found.name == column:
                return self.top + HEAD + index * ROW + ROW / 2
        raise LayoutError(f"{self.table.name}.{column} does not exist")


@dataclass(frozen=True)
class Edge:
    """A line from SOURCE.COLUMN to TARGET.TARGET_COLUMN through POINTS.

    SOURCE_SIDE and TARGET_SIDE are the directions in which the line
    leaves each box: ``left``, ``right``, ``up`` or ``down``.
    SOURCE_END and TARGET_END are ``many``, ``zero_one``, ``one`` or
    empty for a declared link. KIND is ``key``, ``user`` or ``value``.
    LABEL is drawn at LABEL_AT, a point and a text anchor, or not at
    all when LABEL_AT is None. NOTE tells how a declared link matches.
    """

    source: str
    column: str
    target: str
    target_column: str
    points: tuple[Point, ...]
    source_side: str
    target_side: str
    source_end: str
    target_end: str
    label: str
    label_at: tuple[float, float, str] | None
    kind: str = "key"
    note: str = ""
    soft: bool = False


@dataclass(frozen=True)
class Drawing:
    """The boxes by table name and the lines of an arrangement."""

    boxes: dict[str, Box]
    edges: tuple[Edge, ...]
    width: float
    height: float
    box_width: float


@dataclass
class _Reference:
    source: str
    column: str
    target: str
    target_column: str
    kind: str
    label: str
    note: str
    source_end: str
    target_end: str
    rule: str = ""
    source_gap: int = 0
    target_gap: int = 0
    corridor: int | None = None
    corridor_lane: int = 0
    index: int = 0


@dataclass(frozen=True)
class _Placement:
    boxes: dict[str, Box]
    where: dict[str, tuple[int, int]]
    stacks: dict[int, list[str]]
    tops: tuple[float, ...]
    bottoms: tuple[float, ...]
    columns: int
    width: int
    gaps: dict[int, int]
    corridors: dict[int, int]

    def gap_centre(self, gap: int) -> float:
        """Return the middle of the gap after column GAP."""
        return MARGIN + (gap + 1) * self.width + sum(
            self.gaps.get(g, COLUMN_GAP) for g in range(gap)) + (
            self.gaps.get(gap, COLUMN_GAP) / 2)

    def corridor_y(self, corridor: int, lane: int) -> float:
        """Return the height of LANE in the corridor below band
        CORRIDOR."""
        bottom = (self.bottoms[corridor] + BAND_GAP
                  + self.corridors.get(corridor, 0))
        return bottom - 18 - lane * CORRIDOR_LANE


def box_width(tables: Iterable[Table]) -> int:
    """Return the box width that fits the longest header and row of
    TABLES, by an estimate of their text."""
    need = MIN_WIDTH
    for table in tables:
        need = max(need, 10 + TITLE_ADVANCE * len(table.name) + 64)
        for column in table.columns:
            type_text = column.type + ("?" if column.nullable else "")
            need = max(need, 32 + NAME_ADVANCE * len(column.name) + 12
                       + TYPE_ADVANCE * len(type_text) + 10)
    return math.ceil(need / 4) * 4


def _place(tables: Sequence[Table], grid: Grid, gaps: dict[int, int],
           corridors: dict[int, int]) -> _Placement:
    by_name = {t.name: t for t in tables}
    width = box_width(tables)
    count = max(len(band) for band in grid)
    lefts = [MARGIN]
    for gap in range(count - 1):
        lefts.append(lefts[-1] + width + gaps.get(gap, COLUMN_GAP))
    boxes: dict[str, Box] = {}
    where: dict[str, tuple[int, int]] = {}
    stacks: dict[int, list[str]] = {}
    tops, bottoms = [], []
    top = TOP
    for band_index, band in enumerate(grid):
        bottom = top
        for column_index, slot in enumerate(band):
            y = top
            for name in slot or ():
                if name not in by_name:
                    raise LayoutError(
                        f"the grid names {name}, which is not a table")
                if name in boxes:
                    raise LayoutError(f"the grid names {name} twice")
                box = Box(by_name[name], lefts[column_index], y, width)
                boxes[name] = box
                where[name] = (band_index, column_index)
                stacks.setdefault(column_index, []).append(name)
                y = box.bottom + SLOT_GAP
                bottom = max(bottom, box.bottom)
        tops.append(top)
        bottoms.append(bottom)
        top = bottom + BAND_GAP + corridors.get(band_index, 0)
    missing = sorted(set(by_name) - set(boxes))
    if missing:
        raise LayoutError(f"the grid misses {', '.join(missing)}")
    return _Placement(boxes, where, stacks, tuple(tops), tuple(bottoms),
                      count, width, dict(gaps), dict(corridors))


def _references(tables: Sequence[Table], links: Sequence[Link],
                boxes: dict[str, Box], hub: str | None
                ) -> list[_Reference]:
    found = []
    for table in tables:
        for column in table.columns:
            if not column.ref or column.ref not in boxes:
                continue
            found.append(_Reference(
                table.name, column.name, column.ref, column.ref_column,
                "user" if column.ref == hub else "key",
                "" if column.on_delete in (None, "PROTECT")
                else column.on_delete.lower().replace("_", " "),
                f"on delete {column.on_delete}" if column.on_delete else "",
                "zero_one" if column.key == "1:1" else "many",
                "zero_one" if column.nullable else "one"))
    for link in links:
        for table, column in ((link.source, link.column),
                              (link.target, link.target_column)):
            if table not in boxes:
                raise LayoutError(f"{table}.{column} does not exist")
            boxes[table].row_y(column)
        found.append(_Reference(link.source, link.column, link.target,
                                link.target_column, "value", link.label,
                                link.note, "", ""))
    for index, ref in enumerate(found):
        ref.index = index
    return found


def _under_points(ref: _Reference, place: _Placement) -> tuple[Point, ...]:
    source, target = place.boxes[ref.source], place.boxes[ref.target]
    (band, col), (_, target_col) = (place.where[ref.source],
                                    place.where[ref.target])
    low, high = sorted((col, target_col))
    between = [place.boxes[n].bottom for n, (b, c) in place.where.items()
               if b == band and low < c < high]
    lane = max([*between, source.bottom]) + 36
    rightward = target.left > source.left
    sx = source.right - 46 if rightward else source.left + 46
    tx = target.left if rightward else target.right
    return ((sx, source.bottom), (sx, lane), (tx, lane))


def _classify(ref: _Reference, place: _Placement) -> None:
    target = place.boxes[ref.target]
    (band, col), (target_band, target_col) = (place.where[ref.source],
                                              place.where[ref.target])
    if ref.source == ref.target:
        ref.rule = "loop"
        return
    if abs(col - target_col) == 1:
        ref.rule = "elbow"
        ref.source_gap = ref.target_gap = min(col, target_col)
        return
    stack = place.stacks[col]
    if col == target_col and abs(stack.index(ref.source)
                                 - stack.index(ref.target)) == 1:
        ref.rule = "vertical"
        return
    if band == target_band and col != target_col:
        points = _under_points(ref, place)
        lane = points[1][1]
        if (target.top + HEAD < lane < target.bottom - PAD
                and _crossing(ref.source, ref.target, points,
                              place.boxes) is None):
            ref.rule = "under"
            return
    if place.columns < 2:
        raise LayoutError(f"{ref.source}.{ref.column} fits no rule: "
                          "the grid has no gap between columns")
    ref.rule = "channel"
    if target_col > col or (target_col == col
                            and col < place.columns - 1):
        ref.source_gap = col
    else:
        ref.source_gap = col - 1
    if target_col == col:
        ref.target_gap = ref.source_gap
    else:
        ref.target_gap = target_col if col > target_col else target_col - 1
    if ref.source_gap != ref.target_gap:
        ref.corridor = band if target_band >= band else band - 1


def _lanes(spans: list[tuple[object, tuple[float, float], object]]
           ) -> tuple[dict[object, int], dict[object, int]]:
    """Give each span of SPANS, ``(group, (low, high), key)``, the lowest
    lane of its group free over its span; return the lanes by key and
    the number of lanes by group."""
    ends: dict[object, list[float]] = {}
    lanes: dict[object, int] = {}
    for group, (low, high), key in sorted(
            spans, key=lambda s: (str(s[0]), s[1][0], s[1][1], str(s[2]))):
        taken = ends.setdefault(group, [])
        lane = next((i for i, end in enumerate(taken) if end < low), None)
        if lane is None:
            lane = len(taken)
            taken.append(high)
        taken[lane] = high
        lanes[key] = lane
    return lanes, {group: len(taken) for group, taken in ends.items()}


def _ends(ref: _Reference, place: _Placement) -> tuple[float, float]:
    return (place.boxes[ref.source].row_y(ref.column),
            place.boxes[ref.target].row_y(ref.target_column))


def _vertical_spans(ref: _Reference, place: _Placement
                    ) -> list[tuple[int, tuple[float, float]]]:
    """The gaps REF runs along, each with the heights it covers there."""
    y1, y2 = _ends(ref, place)
    if ref.rule == "elbow" or (ref.rule == "channel"
                               and ref.corridor is None):
        return [(ref.source_gap, (min(y1, y2), max(y1, y2)))]
    if ref.rule != "channel":
        return []
    yc = place.corridor_y(ref.corridor, ref.corridor_lane)
    return [(ref.source_gap, (min(y1, yc), max(y1, yc))),
            (ref.target_gap, (min(yc, y2), max(yc, y2)))]


def _route(ref: _Reference, place: _Placement, offsets: dict[object, float]
           ) -> Edge:
    source, target = place.boxes[ref.source], place.boxes[ref.target]
    label_at = None
    if ref.rule == "loop":
        y = source.row_y(ref.column)
        right, below = source.right + 18, source.bottom + 22
        back = source.right - 60
        points = ((source.right, y), (right, y), (right, below),
                  (back, below), (back, source.bottom))
        sides = ("right", "down")
        label_at = ((right + back) / 2, below + 13, "middle")
    elif ref.rule == "vertical":
        x = source.centre + offsets.get((ref.index, "column"), 0)
        if source.top < target.top:
            points = ((x, source.bottom), (x, target.top))
            sides = ("down", "up")
        else:
            points = ((x, source.top), (x, target.bottom))
            sides = ("up", "down")
        label_at = (x + 8, (points[0][1] + points[1][1]) / 2 + 3, "start")
    elif ref.rule == "under":
        points = _under_points(ref, place)
        sides = ("down", "left" if points[-1][0] == target.left
                 else "right")
    else:
        y1, y2 = _ends(ref, place)
        ga = place.gap_centre(ref.source_gap) + offsets.get(
            (ref.index, ref.source_gap), 0)
        gb = place.gap_centre(ref.target_gap) + offsets.get(
            (ref.index, ref.target_gap, "target"), offsets.get(
                (ref.index, ref.target_gap), 0))
        sx = source.right if ga > source.right else source.left
        tx = target.right if gb > target.right else target.left
        if ref.rule == "elbow" or ref.corridor is None:
            points = ((sx, y1), (ga, y1), (ga, y2), (tx, y2))
        else:
            yc = place.corridor_y(ref.corridor, ref.corridor_lane)
            points = ((sx, y1), (ga, y1), (ga, yc), (gb, yc), (gb, y2),
                      (tx, y2))
        sides = ("right" if sx == source.right else "left",
                 "right" if tx == target.right else "left")
        if ref.rule == "elbow" and ref.kind != "value":
            if abs(y2 - y1) >= 60:
                label_at = (ga, (y1 + y2) / 2 + 3, "middle")
            else:
                label_at = (ga, max(y1, y2) + 16, "middle")
    if ref.label and (label_at is None or ref.kind == "value"):
        label_at = _fitting_label(ref.label, points)
        if label_at is None and ref.kind != "value":
            label_at = _vertical_label(points)
    return Edge(ref.source, ref.column, ref.target, ref.target_column,
                tuple(points), sides[0], sides[1], ref.source_end,
                ref.target_end, ref.label,
                label_at if ref.label else None, kind=ref.kind,
                note=ref.note, soft=ref.kind == "value")


def _fitting_label(label: str, points: Sequence[Point]
                   ) -> tuple[float, float, str] | None:
    """Return where LABEL goes above the longest horizontal segment of
    POINTS, or None when that segment cannot hold it."""
    segments = [(abs(b[0] - a[0]), a, b) for a, b in zip(points, points[1:])
                if a[1] == b[1]]
    if not segments:
        return None
    length, a, b = max(segments, key=lambda s: s[0])
    if length < LABEL_ADVANCE * len(label) + 16:
        return None
    return ((a[0] + b[0]) / 2, a[1] - 5, "middle")


def _vertical_label(points: Sequence[Point]) -> tuple[float, float, str]:
    """Return where a label goes on the longest vertical segment of
    POINTS, or on its first segment when none is vertical."""
    segments = [(abs(b[1] - a[1]), a, b) for a, b in zip(points, points[1:])
                if a[0] == b[0]] or [(0, points[0], points[1])]
    _, a, b = max(segments, key=lambda s: s[0])
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 3, "middle")


def _crossing(source: str, target: str, points: Sequence[Point],
              boxes: dict[str, Box]) -> str | None:
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        for name, box in boxes.items():
            if name in (source, target):
                continue
            if y1 == y2:
                hit = (box.top < y1 < box.bottom
                       and min(x1, x2) < box.right
                       and max(x1, x2) > box.left)
            else:
                hit = (box.left < x1 < box.right
                       and min(y1, y2) < box.bottom
                       and max(y1, y2) > box.top)
            if hit:
                return name
    return None


def crossing(edge: Edge, boxes: dict[str, Box]) -> str | None:
    """Return the name of a box in BOXES that EDGE crosses, other than
    its own two, or None."""
    return _crossing(edge.source, edge.target, edge.points, boxes)


def arrange(tables: Sequence[Table], grid: Grid,
            links: Sequence[Link] = (), hub: str | None = None) -> Drawing:
    """Place TABLES by GRID and route their references and LINKS.

    GRID holds bands, top to bottom, each a sequence of slots, left to
    right; a slot is None or the names of the tables it holds, top to
    bottom. A reference to HUB is of kind ``user``, any other of kind
    ``key``, a link of kind ``value``; references to tables without a
    box are not drawn. Raises LayoutError when the grid misses a table,
    names an unknown one or one twice, when a link names a missing
    column, or when a line would cross another box.
    """
    place = _place(tables, grid, {}, {})
    refs = _references(tables, links, place.boxes, hub)
    for ref in refs:
        _classify(ref, place)
    channels = [r for r in refs if r.corridor is not None]
    corridor_lanes, corridor_counts = _lanes(
        [(r.corridor, tuple(sorted((r.source_gap, r.target_gap))), r.index)
         for r in channels])
    for ref in channels:
        ref.corridor_lane = corridor_lanes[ref.index]
    corridors = {k: (n - 1) * CORRIDOR_LANE
                 for k, n in corridor_counts.items()}
    place = _place(tables, grid, {}, corridors)
    spans = []
    for ref in refs:
        for index, (gap, span) in enumerate(_vertical_spans(ref, place)):
            key = (ref.index, gap, "target") if index else (ref.index, gap)
            spans.append((gap, span, key))
        if ref.rule == "vertical":
            upper, lower = sorted((place.boxes[ref.source],
                                   place.boxes[ref.target]),
                                  key=lambda b: b.top)
            spans.append((("column", place.where[ref.source][1]),
                          (upper.bottom, lower.top), (ref.index, "column")))
    lanes, counts = _lanes(spans)
    gaps = {g: COLUMN_GAP + (n - 1) * GAP_LANE for g, n in counts.items()
            if isinstance(g, int)}
    place = _place(tables, grid, gaps, corridors)
    offsets = {}
    for group, _, key in spans:
        step = GAP_LANE if isinstance(group, int) else COLUMN_LANE
        offsets[key] = (lanes[key] - (counts[group] - 1) / 2) * step
    edges = tuple(_route(ref, place, offsets) for ref in refs)
    for edge in edges:
        crossed = crossing(edge, place.boxes)
        if crossed:
            raise LayoutError(f"the line of {edge.source}.{edge.column} "
                              f"would cross {crossed}")
    right = max(b.right for b in place.boxes.values())
    deepest = max([b.bottom for b in place.boxes.values()]
                  + [y for e in edges for _, y in e.points])
    return Drawing(place.boxes, edges, width=right + MARGIN,
                   height=deepest + 40, box_width=place.width)


def _n(value: float) -> str:
    return f"{round(value, 2):g}"


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _marker(point: Point, side: str, kind: str) -> str:
    vx, vy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1),
              "down": (0, 1)}[side]
    nx, ny = -vy, vx

    def at(d: float, s: float) -> str:
        x = point[0] + vx * d + nx * s
        y = point[1] + vy * d + ny * s
        return f"{_n(x)},{_n(y)}"

    def ring(d: float) -> str:
        return (f'<circle class="mk o" cx="{_n(point[0] + vx * d)}" '
                f'cy="{_n(point[1] + vy * d)}" r="3.6"/>')

    if kind == "many":
        return (f'<path class="mk" d="M{at(12, 0)}L{at(0, -7)}M{at(12, 0)}'
                f'L{at(0, 7)}"/>' + ring(17))
    if kind == "one":
        return (f'<path class="mk" d="M{at(6, -6)}L{at(6, 6)}M{at(11, -6)}'
                f'L{at(11, 6)}"/>')
    return f'<path class="mk" d="M{at(6, -6)}L{at(6, 6)}"/>' + ring(14)


def _tip(column: Column) -> str:
    head = column.name
    if column.type:
        head += f" {column.type}" + (", nullable" if column.nullable else "")
    lines = [head]
    if column.ref:
        lines.append(f"→ {column.ref}.{column.ref_column}"
                     + (f", on delete {column.on_delete}"
                        if column.on_delete else ""))
    lines += column.notes
    return "\n".join(lines)


def svg(drawing: Drawing, near: dict[str, list[str]]) -> str:
    """Return DRAWING as an inline ``svg``; NEAR lists, by table, the
    tables linked to it."""
    tables = {name: box.table for name, box in drawing.boxes.items()}
    out = [(f'<svg class="diagram" viewBox="0 0 {_n(drawing.width)} '
            f'{_n(drawing.height)}" role="img" aria-label="Entity-'
            f'relationship diagram of the OrgSynDB tables">'), '<g>']
    for edge in drawing.edges:
        ends = f"{edge.source_end} {edge.target_end}".strip()
        arrow = "⇢" if edge.soft else "→"
        tip = (f"{edge.source}.{edge.column} {arrow} "
               f"{edge.target}.{edge.target_column}"
               + (f"\n{edge.note}" if edge.note else ""))
        out.append(
            f'<g class="edge{" soft" if edge.soft else ""} '
            f'kind-{edge.kind}" '
            f'data-from="{_e(edge.source)}" data-to="{_e(edge.target)}" '
            f'data-column="{_e(edge.column)}" '
            f'data-target-column="{_e(edge.target_column)}" '
            f'data-ends="{ends}"><title>{_e(tip)}</title>'
            f'<path class="ln" d="M'
            + "L".join(f"{_n(x)},{_n(y)}" for x, y in edge.points) + '"/>')
        if edge.soft:
            for x, y in (edge.points[0], edge.points[-1]):
                out.append(f'<circle class="dot" cx="{_n(x)}" cy="{_n(y)}" '
                           'r="2.6"/>')
        else:
            out.append(_marker(edge.points[0], edge.source_side,
                               edge.source_end))
            out.append(_marker(edge.points[-1], edge.target_side,
                               edge.target_end))
        if edge.label_at:
            x, y, anchor = edge.label_at
            out.append(f'<text x="{_n(x)}" y="{_n(y)}" text-anchor="{anchor}"'
                       f'>{_e(edge.label)}</text>')
        out.append("</g>")
    out.append("</g><g>")
    width = drawing.box_width
    for name, box in drawing.boxes.items():
        table = box.table
        prefix, _, rest = name.partition("_")
        ghost = " ghost" if table.count > 1 else ""
        out.append(
            f'<g class="tbl app-{table.app}{ghost}" tabindex="0" '
            f'data-table="{_e(name)}" data-near="{_e(" ".join(near[name]))}" '
            f'transform="translate({_n(box.left)},{_n(box.top)})">'
            f'<title>{_e(table.about)}</title>'
            f'<rect class="box" width="{_n(width)}" '
            f'height="{_n(box.bottom - box.top)}" rx="4"/>'
            f'<path class="head" d="M0,4a4,4 0 0 1 4,-4H{_n(width - 4)}'
            f'a4,4 0 0 1 4,4V{HEAD}H0Z"/>'
            f'<text class="tname" x="10" y="20"><tspan class="pre">'
            f'{_e(prefix)}_</tspan>{_e(rest)}</text>')
        if table.history:
            out.append(f'<text class="pill" x="{_n(width - 10)}" y="19" '
                       'text-anchor="end">HISTORY</text>')
        if table.count > 1:
            out.append(f'<text class="pill" x="{_n(width - 10)}" y="19" '
                       f'text-anchor="end">×{table.count}</text>')
        for index, column in enumerate(table.columns):
            y = HEAD + index * ROW
            base = _n(y + ROW / 2 + 3.6)
            ref = f' data-ref="{_e(column.ref)}"' if column.ref else ""
            extra = "" if column.type else " extra"
            out.append(
                f'<g class="row{extra}" data-column="{_e(name)}.'
                f'{_e(column.name)}"{ref}><title>'
                f'{_e(_tip(column))}</title>'
                f'<rect class="bg" x="1" y="{y}" width="{_n(width - 2)}" '
                f'height="{ROW}"/>')
            if index:
                out.append(f'<line class="sep" x1="8" x2="{_n(width - 8)}" '
                           f'y1="{_n(y + 0.5)}" y2="{_n(y + 0.5)}"/>')
            if column.key:
                app = (tables[column.ref].app if column.ref in tables
                       else table.app)
                out.append(f'<text class="gk app-{app}" x="9" y="{base}">'
                           f'{column.key}</text>')
            out.append(f'<text class="cn" x="32" y="{base}">'
                       f'{_e(column.name)}</text>')
            if column.type:
                out.append(
                    f'<text class="ct" x="{_n(width - 10)}" y="{base}" '
                    f'text-anchor="end">{_e(column.type)}'
                    f'{"?" if column.nullable else ""}</text>')
            out.append("</g>")
        out.append("</g>")
    out.append("</g></svg>")
    return "".join(out)


def _neighbours(tables: Sequence[Table], links: Sequence[Link],
                boxes: dict[str, Box]) -> dict[str, list[str]]:
    near: dict[str, set[str]] = {name: set() for name in boxes}
    pairs = [(t.name, c.ref) for t in tables for c in t.columns if c.ref]
    pairs += [(link.source, link.target) for link in links]
    for a, b in pairs:
        if a in near and b in near and a != b:
            near[a].add(b)
            near[b].add(a)
    return {name: sorted(found) for name, found in near.items()}


def _prose(text: str) -> SafeString:
    """Return docstring TEXT as HTML, ````code```` as ``code``."""
    return mark_safe(re.sub(r"``(.+?)``", r"<code>\1</code>", _e(text)))


def render(schema: Schema, drawing: Drawing,
           links: Sequence[Link] = LINKS) -> str:
    """Return the page of SCHEMA drawn as DRAWING.

    Raises LayoutError for a package without a colour.
    """
    apps_shown = sorted({b.table.app for b in drawing.boxes.values()})
    for app in apps_shown:
        if app not in COLOURS:
            raise LayoutError(f"the package {app} has no colour")
    every = [*schema.tables, schema.history]
    near = _neighbours(every, links, drawing.boxes)
    rules: dict[str, list[str]] = {}
    for table in every:
        for column in table.columns:
            if column.on_delete:
                rules.setdefault(column.on_delete, []).append(
                    f"{table.name}.{column.name} → {column.ref}")
    order = ["CASCADE", "SET_NULL", "SET_DEFAULT", "DO_NOTHING", "RESTRICT",
             "PROTECT"]
    on_delete = [(rule.replace("_", " "), sorted(rules[rule]))
                 for rule in sorted(rules, key=lambda r: (
                     order.index(r) if r in order else len(order), r))]
    text = render_to_string("orgsyndb_web/database_schema.html", {
        "colours": [(app, *COLOURS[app]) for app in COLOURS],
        "packages": schema.packages,
        "table_count": len(schema.tables),
        "package_count": len(schema.packages),
        "history_count": len(schema.history_tables),
        "svg": mark_safe(svg(drawing, near)),
        "constraints": schema.constraints,
        "positive_checks": schema.positive_checks,
        "null_notes": schema.null_notes,
        "on_delete": on_delete,
        "history_tables": schema.history_tables,
        "tables": [(t, [_prose(p) for p in t.doc]) for t in schema.tables],
        "framework": schema.framework,
        "kinds": [(kind, label, sum(e.kind == kind for e in drawing.edges),
                   checked)
                  for kind, label, checked in KINDS],
    })
    return text.strip() + "\n"


def generate() -> str:
    """Return the page of the application's tables.

    Raises ValueError, LayoutError among them, when the models or the
    grid cannot be drawn.
    """
    schema = collect()
    drawing = arrange([*schema.tables, schema.history], GRID, LINKS, HUB)
    with translation.override("en"):
        return render(schema, drawing)
