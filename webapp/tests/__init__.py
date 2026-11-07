"""Helpers shared by the application's tests.

Nothing here imports Django at module level: this package is imported
while the settings module is still loading. The factories import the
models when they are called.
"""

import atexit
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator
from unittest import mock
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
BERLIN = ZoneInfo("Europe/Berlin")
PASSWORD = "Tr4ck-Lab-Zebra-91"
NOT_IN_COLLECTION = {"de": "nicht in der Sammlung",
                     "en": "not in the collection"}

# ---------------------------------------------------------------------------
# Collection indexes

_modified = itertools.count(1_700_000_000)
_demo: Path | None = None


def write_index(path: Path, data: Any) -> Path:
    """Write ``data`` as JSON to ``path`` and give the file a modification
    time that no earlier call gave any file, so a reader that compares
    modification times sees every write."""
    path.write_text(json.dumps(data), encoding="utf-8")
    stamp(path)
    return path


def stamp(path: Path) -> None:
    """Give ``path`` a new modification time, later than every other
    this module handed out."""
    moment = next(_modified)
    os.utime(path, (moment, moment))


def demo_index() -> Path:
    """The output of ``orgsyndb index`` for the demo collection, saved
    once per test run to a file."""
    global _demo
    if _demo is None:
        done = subprocess.run(
            [sys.executable, str(REPO / "tools" / "orgsyndb"), "-C",
             str(REPO / "examples" / "demo"), "index"],
            capture_output=True, text=True, check=True)
        directory = Path(tempfile.mkdtemp(prefix="osdb-demo-index-"))
        atexit.register(shutil.rmtree, directory, True)
        _demo = directory / "index.json"
        _demo.write_text(done.stdout, encoding="utf-8")
        stamp(_demo)
    return _demo


def demo_data() -> dict[str, Any]:
    return json.loads(demo_index().read_text(encoding="utf-8"))


def compound(key: str, **data: Any) -> dict[str, Any]:
    return {"key": key, "path": f"compounds/{key}.toml",
            "data": {"name": key, **data}}


def procedure(ident: str, language: str | None = None) -> dict[str, Any]:
    suffix = f".{language}" if language else ""
    return {"id": ident, "language": language, "format": "md",
            "path": f"md/procedures/{ident}-x{suffix}.md",
            "front_matter": {"id": ident}}


def sequence(ident: str, steps: list[str],
             language: str | None = None) -> dict[str, Any]:
    suffix = f".{language}" if language else ""
    return {"id": ident, "language": language,
            "path": f"md/sequences/{ident}-x{suffix}.md",
            "front_matter": {"id": ident,
                             "steps": [{"procedure": s} for s in steps]}}


def build_index(language: str = "de",
                compounds: list[dict[str, Any]] | None = None,
                procedures: list[dict[str, Any]] | None = None,
                sequences: list[dict[str, Any]] | None = None,
                fields: list[dict[str, Any]] | None = None
                ) -> dict[str, Any]:
    """A small index. ``fields`` are the declared compound fields; the
    default declares the unique text field ``item_number``."""
    if fields is None:
        fields = [{"key": "item_number", "type": "text", "unique": True}]
    return {"site_language": language,
            "fields": {"compound": fields, "procedure": []},
            "compounds": compounds or [],
            "procedures": procedures or [],
            "sequences": sequences or []}


def text_field(key: str, unique: bool = True) -> dict[str, Any]:
    return {"key": key, "type": "text", "unique": unique}


class IndexMixin:
    """Mixin for ``TestCase``: points ``ORGSYNDB_INDEX`` at an index for
    the length of one test."""

    def use_index(self, index: Any = None) -> Path:
        """``index`` is a dict, written to a new file, a path, used as
        it is, or None, a path where no file exists."""
        from django.test import override_settings
        if isinstance(index, Path):
            path = index
        else:
            directory = Path(tempfile.mkdtemp(prefix="osdb-index-"))
            self.addCleanup(shutil.rmtree, directory, True)  # type: ignore
            path = directory / "index.json"
            if index is not None:
                write_index(path, index)
        override = override_settings(ORGSYNDB_INDEX=str(path))
        override.enable()
        self.addCleanup(override.disable)  # type: ignore
        return path


# ---------------------------------------------------------------------------
# Time


def berlin(year: int, month: int, day: int, hour: int = 12,
           minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=BERLIN)


def frozen(moment: datetime) -> Any:
    """A context manager that makes ``django.utils.timezone.now`` return
    ``moment``."""
    return mock.patch("django.utils.timezone.now", return_value=moment)


def ticking(start: datetime, step: timedelta = timedelta(seconds=1)) -> Any:
    """A context manager that makes ``django.utils.timezone.now`` return
    ``start``, then a moment ``step`` later on every further call, so
    that no two bookings share a booking time."""
    moments = (start + step * count for count in itertools.count())
    return mock.patch("django.utils.timezone.now",
                      side_effect=lambda: next(moments))


def past(day: int, month: int = 3) -> date:
    """A date in 2025, in the past on any day the suite runs."""
    return date(2025, month, day)


# ---------------------------------------------------------------------------
# Records


def make_user(username: str, initials: str, first_name: str = "",
              last_name: str = "", password: str | None = PASSWORD,
              **extra: Any) -> Any:
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username=username, password=password, initials=initials,
        first_name=first_name, last_name=last_name, **extra)


def make_task(created_by: Any, **fields: Any) -> Any:
    from tasks.models import Task
    fields.setdefault("product", "Aspirin")
    return Task.objects.create(created_by=created_by, **fields)


# The day test items entered stock unless a test says otherwise: long
# enough ago that no item is marked new.
STOCKED_LONG_AGO = date(2019, 1, 2)


def make_item(user: Any, article: str | None = "CH-0001",
              name: str = "Probe", size: str = "10", unit: str = "umol",
              quantity: int = 5, category: str = "", note: str = "",
              day: date | None = None,
              stocked_on: date | None = STOCKED_LONG_AGO) -> Any:
    """An item of the inventory ``end-products``, booked by ``user``,
    that entered stock on ``stocked_on``."""
    from decimal import Decimal
    from inventory.bookings import create_item
    return create_item(
        user, article_number=article, name=name, size=Decimal(size),
        unit=unit, quantity=quantity, category=category, note=note,
        date=day, stocked_on=stocked_on)


BASE_FACTOR = {"mg": 1, "g": 1000, "umol": 1, "mmol": 1000}


def make_lot(user: Any, article: str = "CH-0001", unit: str = "mg",
             amount: str = "50", batch: str = "", location: str = "",
             made_on: date | None = None, note: str = "") -> Any:
    """A lot holding ``amount`` of ``unit``, kept in the base unit, with
    its opening movement."""
    from decimal import Decimal
    from django.utils import timezone
    from inventory.models import END_PRODUCTS, Lot, LotMovement
    base = Decimal(amount) * BASE_FACTOR[unit]
    lot = Lot.objects.create(
        inventory=END_PRODUCTS, article_number=article, unit=unit,
        amount=base, batch=batch, location=location, made_on=made_on,
        note=note)
    LotMovement.objects.create(
        lot=lot, kind=LotMovement.Kind.OPENING, amount=base,
        amount_after=base, date=timezone.localdate(),
        booked_at=timezone.now(), user=user)
    return lot


def task_url(task: Any, action: str = "") -> str:
    return f"/lab/tasks/{task.number}/" + (f"{action}/" if action else "")


def task_form_data(**over: Any) -> dict[str, str]:
    """The fields of the task form with nothing filled in but the
    product; a flag is on when given as ``"on"``."""
    data = {"product": "Aspirin", "priority": "medium", "assignee": "",
            "started": "", "ended": "", "sequence": "", "steps_total": "",
            "steps_done": "", "batch": "", "note": ""}
    data.update(over)
    return data


def edit_data(task: Any, **over: Any) -> dict[str, str]:
    """The edit form's fields as the task stands, with ``over`` applied."""
    data = task_form_data(
        product=task.product, priority=task.priority,
        assignee=str(task.assignee_id or ""),
        started=task.started.isoformat() if task.started else "",
        ended=task.ended.isoformat() if task.ended else "",
        sequence=task.sequence or "",
        steps_total=str(task.steps_total or ""),
        steps_done=str(task.steps_done), batch=task.batch or "",
        note=task.note or "")
    for flag in ("report", "qc_list", "cancelled"):
        if getattr(task, flag):
            data[flag] = "on"
    data.update(over)
    return data


def sent_messages(response: Any) -> list[Any]:
    """The messages the request behind ``response`` queued."""
    from django.contrib.messages import get_messages
    return list(get_messages(response.wsgi_request))


def context_form(response: Any) -> Any:
    """The first form in the context of ``response``."""
    from django.forms import BaseForm
    contexts = response.context
    if not isinstance(contexts, list):
        contexts = [contexts]
    for context in contexts:
        for value in context.flatten().values():
            if isinstance(value, BaseForm):
                return value
    raise AssertionError("the response holds no form")


# ---------------------------------------------------------------------------
# HTML

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}
AUTOCLOSE = {"li": {"li"}, "option": {"option"}, "td": {"td", "th"},
             "th": {"td", "th"}, "tr": {"tr", "td", "th"}}


class Element:
    """A node of a parsed page. An attribute given without a value has
    the value ``""``."""

    def __init__(self, tag: str, attrs: dict[str, str],
                 parent: "Element | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Element | str] = []

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def walk(self) -> Iterator["Element"]:
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.walk()

    def matches(self, tag: Any, cls: str | None,
                attrs: dict[str, Any]) -> bool:
        if tag is not None and self.tag not in (
                (tag,) if isinstance(tag, str) else tag):
            return False
        if cls is not None and cls not in self.classes:
            return False
        for name, want in attrs.items():
            if name not in self.attrs:
                return False
            if want is not True and self.attrs[name] != want:
                return False
        return True

    def find_all(self, tag: Any = None, cls: str | None = None,
                 attrs: dict[str, Any] | None = None,
                 **kw: Any) -> list["Element"]:
        """Descendants with the tag (a name or a tuple of names), the
        class and the attributes; an attribute given as True need only
        be present. Attributes with a hyphen go in ``attrs``."""
        want = {**(attrs or {}), **kw}
        return [e for e in self.walk() if e.matches(tag, cls, want)]

    def find(self, tag: Any = None, cls: str | None = None,
             attrs: dict[str, Any] | None = None,
             **kw: Any) -> "Element | None":
        found = self.find_all(tag, cls, attrs, **kw)
        return found[0] if found else None

    def closest(self, tag: str) -> "Element | None":
        node = self.parent
        while node is not None and node.tag != tag:
            node = node.parent
        return node

    def text(self, skip: Any = None) -> str:
        """The text inside, with runs of white space made one space,
        leaving out the descendants for which SKIP, a predicate on
        elements, holds."""
        parts: list[str] = []

        def collect(node: "Element") -> None:
            for child in node.children:
                if isinstance(child, str):
                    parts.append(child)
                elif skip is None or not skip(child):
                    collect(child)

        collect(self)
        return " ".join("".join(parts).split())


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str,
                        attrs: list[tuple[str, str | None]]) -> None:
        while self.stack[-1].tag in AUTOCLOSE.get(tag, ()):
            self.stack.pop()
        element = Element(
            tag, {k: ("" if v is None else v) for k, v in attrs},
            self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in VOID:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse(html: str) -> Element:
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root


def page(response: Any) -> Element:
    """The parsed body of ``response``."""
    return parse(response.content.decode("utf-8"))


def page_text(response: Any) -> str:
    return page(response).text()


def field_value(root: Element, name: str) -> str | None:
    """The value a form control named ``name`` shows: an input's value,
    a select's selected option (its first without a selection), a
    textarea's text, or whether a checkbox is checked."""
    controls = root.find_all(("input", "select", "textarea"), name=name)
    if not controls:
        return None
    control = controls[0]
    if control.tag == "select":
        options = control.find_all("option")
        chosen = [o for o in options if "selected" in o.attrs] or options[:1]
        return chosen[0].get("value", chosen[0].text()) if chosen else None
    if control.tag == "textarea":
        return control.text()
    if control.get("type") in ("checkbox", "radio"):
        return "on" if "checked" in control.attrs else ""
    return control.get("value", "")


def table(root: Element) -> tuple[list[str], list[dict[str, Element]]]:
    """The header texts of the first table, from its first row and
    without the notes in ``small`` beneath them, and its rows outside
    ``thead`` as mappings from header text to cell; the rows of tables
    inside its cells are left out."""
    grid = root.find("table")
    if grid is None:
        raise AssertionError("the page holds no table")
    rows = [tr for tr in grid.find_all("tr") if tr.closest("table") is grid]

    def cells(tr: Element) -> list[Element]:
        return [c for c in tr.children
                if isinstance(c, Element) and c.tag in ("th", "td")]

    header = [cell.text(lambda node: node.tag == "small")
              for cell in cells(rows[0])]
    return header, [dict(zip(header, cells(tr))) for tr in rows[1:]
                    if tr.closest("thead") is None]


def numbers(root: Element) -> list[str]:
    """The task numbers in the first column of the list's table."""
    header, rows = table(root)
    return [row[header[0]].text() for row in rows]
