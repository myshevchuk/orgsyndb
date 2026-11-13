"""Helpers shared by the application's tests.

Nothing here imports Django at module level: this package is imported
while the settings module is still loading. The factories import the
models when they are called.
"""

import io
import itertools
import re
import unicodedata
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
DEMO_REGISTRY = REPO / "webapp" / "demo" / "registry.json"

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


# The demo's accounts by user name, with their first and last names and
# initials that no other account of the tests has, so that tests may add
# the accounts a collection's authors name next to their own.
DEMO_USERS = {
    "klehmann": ("Katrin", "Lehmann", "ZKL"),
    "tbauer": ("Tobias", "Bauer", "ZTB"),
    "aschmidt": ("Anna", "Schmidt", "ZAS"),
    "jkoch": ("Jonas", "Koch", "ZJK"),
    "mwolf": ("Miriam", "Wolf", "ZMW"),
}


def make_demo_accounts() -> list[Any]:
    """The five demo accounts, which the demo collection's procedures
    credit, each created when it does not exist; return them in the
    order of ``DEMO_USERS``."""
    from django.contrib.auth import get_user_model
    found = []
    for username, (first, last, initials) in DEMO_USERS.items():
        account = get_user_model().objects.filter(username=username).first()
        found.append(account or make_user(
            username, initials, first, last, password=None))
    return found


# The demo's notebooks and their owners (lab-demo "Demo notebooks"), by
# code.
DEMO_NOTEBOOKS = {"AE-1": "klehmann", "AE-2": "aschmidt",
                  "CE-1": "jkoch", "CE-3": "mwolf"}


def make_demo_notebooks() -> list[Any]:
    """The four demo notebooks, which the demo collection's procedures
    name, each created when it does not exist, with no note; return them
    in the order of ``DEMO_NOTEBOOKS``. The demo accounts must exist
    (``make_demo_accounts``). Does nothing, and returns none, while the
    application has no journal, so that a test of the import fails on its
    own assertions rather than here."""
    from django.apps import apps
    from django.contrib.auth import get_user_model
    try:
        model = apps.get_model("journal", "Notebook")
    except LookupError:
        return []
    return [model.objects.get_or_create(code=code, defaults={
        "user": get_user_model().objects.get(username=username)})[0]
        for code, username in DEMO_NOTEBOOKS.items()]


def slug(text: str) -> str:
    """``text`` as a registry key: lower case ASCII letters and digits
    joined by single hyphens, as ``Neuverbindung 9`` gives
    ``neuverbindung-9``."""
    ascii_text = unicodedata.normalize("NFKD", text).encode(
        "ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def make_group(key: str = "purchased", label: str | None = None,
               parent: Any = None, **fields: Any) -> Any:
    """The group ``key``, created when there is none; ``fields``, such
    as ``label_de``, are for a group that has to be created."""
    from vocabulary.models import Group
    return Group.objects.get_or_create(key=key, defaults={
        "label": label or key.replace("-", " ").title(),
        "parent": parent, **fields})[0]


def make_class(key: str = "alcohols", label: str | None = None,
               parent: Any = None, **fields: Any) -> Any:
    """The chemical class ``key``, created when there is none."""
    from vocabulary.models import ChemicalClass
    return ChemicalClass.objects.get_or_create(key=key, defaults={
        "label": label or key.replace("-", " ").title(),
        "parent": parent, **fields})[0]


def make_substance(key: str, name: str | None = None, group: Any = None,
                   classes: Any = (), **fields: Any) -> Any:
    """The substance ``key``, created when there is none, in ``group``
    (the group ``purchased`` by default) and the chemical classes
    ``classes``, which are keys or terms. The name of an existing
    substance stays; a field given for it replaces its value. ``mw``
    may be a string or a number."""
    from decimal import Decimal
    from registry.models import Substance, SubstanceClass
    if fields.get("mw") is not None:
        fields["mw"] = Decimal(str(fields["mw"]))
    found = Substance.objects.filter(key=key).first()
    if found is None:
        found = Substance.objects.create(
            key=key, name=name or key, group=group or make_group(),
            **fields)
    else:
        changed = dict(fields)
        if group is not None:
            changed["group"] = group
        for field, value in changed.items():
            setattr(found, field, value)
        if changed:
            found.save()
    for term in classes:
        term = make_class(term) if isinstance(term, str) else term
        SubstanceClass.objects.get_or_create(substance=found,
                                             chemical_class=term)
    return found


# The substances of the demo collection that have an item number, by
# that number: key, English name, German name and molar mass. Test
# records that name one of these article numbers get the substance, so
# that ``CH-0012`` is ``cinnamic-acid`` with its molar mass 148.16.
DEMO_ARTICLES = {
    "CH-0001": ("1-4-bromophenyl-ethanol", "1-(4-Bromophenyl)ethanol",
                "1-(4-Bromphenyl)ethanol", "201.06"),
    "CH-0002": ("1-biphenyl-4-yl-ethanol", "1-(Biphenyl-4-yl)ethanol",
                "1-(Biphenyl-4-yl)ethanol", "198.26"),
    "CH-0010": ("acetylsalicylic-acid", "Acetylsalicylic acid",
                "Acetylsalicylsäure", "180.16"),
    "CH-0012": ("cinnamic-acid", "(E)-Cinnamic acid", "(E)-Zimtsäure",
                "148.16"),
    "CH-0013": ("dibenzylideneacetone", "Dibenzylideneacetone",
                "Dibenzylidenaceton", "234.3"),
    "CH-0016": ("isopentyl-acetate", "Isopentyl acetate",
                "Isopentylacetat", "130.19"),
}


def demo_article(text: str) -> tuple[str, str, str, str] | None:
    """The entry of ``DEMO_ARTICLES`` for an article number or a key."""
    if text in DEMO_ARTICLES:
        return DEMO_ARTICLES[text]
    return next((known for known in DEMO_ARTICLES.values()
                 if known[0] == text), None)


def substance_for(text: str, name: str | None = None,
                  **fields: Any) -> Any:
    """The substance a test names by ``text``, created when there is
    none: the demo substance of an article number or key in
    ``DEMO_ARTICLES``, else the substance whose key is ``slug(text)``,
    named ``name`` or ``text``. How a test names a substance by an
    article number or a plain name, ``NV-7`` giving ``nv-7``."""
    from registry.models import Substance
    known = demo_article(text)
    key = known[0] if known else slug(text)
    if Substance.objects.filter(key=key).exists():
        return make_substance(key, **fields)
    if known is None:
        return make_substance(key, name or text, **fields)
    return make_substance(key, name or known[1], **{
        "name_de": "" if name else known[2], "mw": known[3], **fields})


def make_article(substance: Any, number: str | None = None,
                 category: str = "", user: Any = None) -> Any:
    """The article of ``substance``, created when there is none. A
    number or a category given for an existing article is set when the
    article lacks it. ``user``, when given, is the history's user of
    what this call saves."""
    from inventory.models import Article
    article = Article.objects.filter(substance=substance).first()
    if article is None:
        article = Article(substance=substance,
                          article_number=number or None, category=category)
    else:
        if number and not article.article_number:
            article.article_number = number
        if category:
            article.category = category
    if user is not None:
        article._history_user = user
    article.save()
    return article


def make_task(created_by: Any, substance: Any = "Aspirin",
              steps: int = 0, done: int = 0, done_on: date | None = None,
              **fields: Any) -> Any:
    """A task of ``substance``, a substance or a text that
    ``substance_for`` turns into one, with ``steps`` plain steps, the
    first ``done`` of them done on ``done_on`` (2 March 2025 by
    default)."""
    from tasks.models import Task
    if isinstance(substance, str):
        substance = substance_for(substance)
    task = Task.objects.create(created_by=created_by, substance=substance,
                               **fields)
    add_steps(task, steps, done, done_on)
    return task


def add_steps(task: Any, count: int, done: int = 0,
              done_on: date | None = None) -> None:
    """Add ``count`` plain steps, with no entry and no import, after the
    steps ``task`` has, the first ``done`` of them done on ``done_on``
    (2 March 2025 by default)."""
    if not count:
        return
    from tasks.models import TaskStep
    first = task.steps.count()
    for number in range(1, count + 1):
        TaskStep.objects.create(
            task=task, position=first + number,
            done_on=(done_on or past(2)) if number <= done else None)


def task_steps(task: Any) -> list[tuple[Any, Any, Any]]:
    """The entry, the planned import and the day done of each step of
    ``task``, in order; the entry is the pair of its procedure's key and
    its position, or None for a step without one."""
    return [(None if step.entry is None else
             (step.entry.procedure.key, step.entry.position),
             step.planned_import, step.done_on)
            for step in task.steps.select_related(
                "entry__procedure", "planned_import").order_by("position")]


def done_days(task: Any) -> list[Any]:
    """The ``done_on`` of each step of ``task``, in order."""
    return [step.done_on for step in task.steps.order_by("position")]


# The day test items entered stock unless a test says otherwise: long
# enough ago that no item is marked new.
STOCKED_LONG_AGO = date(2019, 1, 2)


def make_item(user: Any, article: str | None = "CH-0001",
              name: str | None = None, size: str = "10", unit: str = "umol",
              quantity: int = 5, category: str = "", note: str = "",
              day: date | None = None,
              stocked_on: date | None = STOCKED_LONG_AGO,
              substance: Any = None, mw: Any = None, name_de: str = "",
              compartment: str = "", box: str = "",
              status: str | None = None) -> Any:
    """An item of the inventory ``end-products``, booked by ``user``,
    that entered stock on ``stocked_on``.

    The item is a size of the article of ``substance``; without one, of
    the substance ``substance_for(article)``, named ``name`` (``Probe``
    for an article number that is not a demo article's) when it has to
    be created, or ``substance_for(name)`` for an item without an
    article number. The article is created with the number ``article``
    when it has none.
    """
    from decimal import Decimal
    from django.utils import timezone
    from inventory.models import Item, Movement
    fields = {**({"name_de": name_de} if name_de else {}),
              **({"mw": mw} if mw is not None else {})}
    if substance is None:
        text = article or name or "Probe"
        substance = substance_for(
            text, name or (None if demo_article(text) else "Probe"),
            **fields)
    elif mw is not None:
        substance = make_substance(substance.key, mw=mw)
    owned = make_article(substance, article or None, category, user)
    moved = day or timezone.localdate()
    item = Item(article=owned, size=Decimal(size), unit=unit,
                quantity=quantity, note=note, compartment=compartment,
                box=box, stocked_on=stocked_on or (
                    moved if quantity > 0 else None),
                **({"status": status} if status else {}))
    item._history_user = user
    item.save()
    Movement.objects.create(
        item=item, kind=Movement.Kind.OPENING, count=quantity,
        quantity_after=quantity, date=moved, booked_at=timezone.now(),
        user=user)
    return item


BASE_FACTOR = {"mg": 1, "g": 1000, "umol": 1, "mmol": 1000}


def make_lot(user: Any, article: str = "CH-0001", unit: str = "mg",
             amount: str = "50", batch: str = "", location: str = "",
             made_on: date | None = None, note: str = "",
             substance: Any = None, source: str = "made",
             supplier: str = "", mw: Any = None,
             task_step: Any = None) -> Any:
    """A lot holding ``amount`` of ``unit``, kept in the base unit, with
    its opening movement. It is of ``substance``, or of the substance
    ``substance_for(article)``, which ``make_item`` gives to the item of
    that article number; ``task_step`` is the step that made it."""
    from decimal import Decimal
    from django.utils import timezone
    from inventory.models import Lot, LotMovement
    if substance is None:
        substance = substance_for(
            article, **({"mw": mw} if mw is not None else {}))
    elif mw is not None:
        substance = make_substance(substance.key, mw=mw)
    base = Decimal(amount) * BASE_FACTOR[unit]
    lot = Lot(substance=substance, source=source, supplier=supplier,
              unit=unit, amount=base, batch=batch, location=location,
              made_on=made_on, note=note,
              **({"task_step": task_step} if task_step else {}))
    lot._history_user = user
    lot.save()
    LotMovement.objects.create(
        lot=lot, kind=LotMovement.Kind.OPENING, amount=base,
        amount_after=base, date=timezone.localdate(),
        booked_at=timezone.now(), user=user)
    return lot


def make_withdrawal(user: Any, lot: Any, step: Any, amount: str,
                    day: date | None = None) -> Any:
    """A withdrawal of ``amount`` in the lot's unit from ``lot`` into
    the task step ``step``, booked as the booking would: the lot's
    amount falls and the movement names the step."""
    from decimal import Decimal
    from django.utils import timezone
    from inventory.models import Lot, LotMovement
    base = Decimal(amount) * BASE_FACTOR[lot.unit]
    left = lot.amount - base
    Lot.objects.filter(pk=lot.pk).update(amount=left)
    lot.amount = left
    return LotMovement.objects.create(
        lot=lot, kind=LotMovement.Kind.WITHDRAWAL, amount=base,
        amount_after=left, date=day or timezone.localdate(),
        booked_at=timezone.now(), user=user, task_step=step)


def load_demo_registry() -> None:
    """Load the demo registry into an empty database with
    ``registry_load``."""
    from django.core.management import call_command
    call_command("registry_load", str(DEMO_REGISTRY),
                 stdout=io.StringIO())


def task_url(task: Any, action: str = "") -> str:
    return f"/lab/tasks/{task.number}/" + (f"{action}/" if action else "")


def sequence_target(sequence: str, default: str) -> str:
    """The key of the target of the sequence ``sequence``, a sequence's
    key, which is the substance a task of that sequence makes
    (task-tracker "Task record"); ``default`` when there is no such
    sequence."""
    from collection.models import Sequence
    return Sequence.objects.filter(key=sequence).values_list(
        "target__key", flat=True).first() or default


def task_form_data(**over: Any) -> dict[str, str]:
    """The fields of the task form with nothing filled in but the
    substance key ``aspirin``, which a test creates with
    ``substance_for("Aspirin")``; a flag is on when given as
    ``"on"``. ``sequence`` is a sequence's key, and a form that names
    one without a substance names the sequence's target, since a task
    makes its sequence's target; ``start_step`` is a number."""
    data = {"substance": "aspirin", "priority": "medium", "assignee": "",
            "started": "", "ended": "", "sequence": "", "start_step": "",
            "steps_total": "", "steps_done": "", "batch": "", "note": ""}
    data.update(over)
    if over.get("sequence") and "substance" not in over:
        data["substance"] = sequence_target(over["sequence"],
                                            data["substance"])
    return data


def edit_data(task: Any, **over: Any) -> dict[str, str]:
    """The edit form's fields as the task stands, with ``over`` applied;
    a sequence given without a substance brings its target."""
    data = task_form_data(
        substance=task.substance.key, priority=task.priority,
        assignee=str(task.assignee_id or ""),
        started=task.started.isoformat() if task.started else "",
        ended=task.ended.isoformat() if task.ended else "",
        sequence=task.sequence.key if task.sequence_id else "",
        # The attribute exists once the task records where it starts.
        start_step=str(getattr(task, "start_step", 1)),
        steps_total=str(task.steps.count() or ""),
        steps_done=str(task.steps.filter(done_on__isnull=False).count()),
        batch=task.batch or "", note=task.note or "")
    for flag in ("report", "qc_list", "cancelled", "failed"):
        if getattr(task, flag, False):
            data[flag] = "on"
    data.update(over)
    if over.get("sequence") and "substance" not in over:
        data["substance"] = sequence_target(over["sequence"],
                                            data["substance"])
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


def datalist(root: Element, field: str) -> dict[str, str]:
    """The options of the ``datalist`` that the control named ``field``
    names in its ``list`` attribute, each value with its label."""
    control = root.find(("input", "select", "textarea"), name=field)
    assert control is not None, f"the page has no control {field}"
    listed = control.get("list")
    assert listed, f"the control {field} names no datalist"
    found = root.find("datalist", id=listed)
    assert found is not None, f"the page has no datalist {listed}"
    return {o.get("value"): o.get("label") or o.text()
            for o in found.find_all("option")}


def numbers(root: Element) -> list[str]:
    """The task numbers in the first column of the list's table."""
    header, rows = table(root)
    return [row[header[0]].text() for row in rows]
