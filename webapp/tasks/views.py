"""The task list, the task page, its actions and its forms."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

from collection.models import EntrySubstance
from inventory.bookings import write_off_flasks
from inventory.figures import stock_of
from inventory.models import Batch, Vessel, VesselMovement, shown
from journal.entries import entry_for
from orgsyndb_web import lock
from orgsyndb_web.lists import (Order, SortColumn, clean_choice,
                                htmx_detail_or_redirect, htmx_list_push_url,
                                list_view, pick_selected, sort_value)
from planning.plan import Plan, TaskPriority
from tasks.closing import amounts
from tasks.forms import TaskEditForm, TaskForm
from tasks.history import history_entries
from tasks.models import Priority, State, Task, TaskStep
from tasks.steps import finish

TASKS_URL = "/lab/tasks/"
TASK_COOKIE = "task-list-view"
PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
STATE_ORDER = {
    State.RUNNING: 0,
    State.PLANNED: 1,
    State.ENDED: 2,
    State.CANCELLED: 3,
}


def _progress_sort(row: tuple[Task, TaskPriority, str]) -> Any:
    done, total = row[0].step_counts
    return done / total if total else None


TASK_COLUMNS: tuple[SortColumn, ...] = (
    SortColumn("number", gettext_lazy("No."),
               lambda row: sort_value(row[0].number)),
    SortColumn("product", gettext_lazy("Product"),
               lambda row: sort_value(row[0].substance.shown_name)),
    SortColumn("priority", gettext_lazy("Priority"),
               lambda row: PRIORITY_ORDER.get(row[1].priority, 3)),
    SortColumn("assignee", gettext_lazy("Assignee"),
               lambda row: sort_value(
                   row[0].assignee.initials if row[0].assignee else "")),
    SortColumn("started", gettext_lazy("Started"),
               lambda row: sort_value(row[0].started)),
    SortColumn("ended", pgettext_lazy("date", "Ended"),
               lambda row: sort_value(row[0].ended)),
    SortColumn("progress", gettext_lazy("Progress"), _progress_sort),
    SortColumn("batch", gettext_lazy("Batch"),
               lambda row: sort_value(_first_product_number(row[0]))),
    SortColumn("report", gettext_lazy("Report"),
               lambda row: sort_value(
                   str(_("yes")) if row[0].report else str(_("no")))),
    SortColumn("qc", gettext_lazy("QC list"),
               lambda row: sort_value(
                   str(_("yes")) if row[0].qc_list else str(_("no")))),
    SortColumn("state", gettext_lazy("State"),
               lambda row: STATE_ORDER.get(row[0].state, 4)),
)
TASK_CLASSES = {"product": "col-strong col-name", "priority": "col-strong"}

STATE_FILTERS = [
    ("active", gettext_lazy("Active")),
    ("planned", gettext_lazy("Planned")),
    ("running", gettext_lazy("Running")),
    ("followup", gettext_lazy("Follow-up")),
    ("ended", pgettext_lazy("state", "Ended")),
    ("cancelled", gettext_lazy("Cancelled")),
    ("all", gettext_lazy("All")),
]
STATE_TESTS: dict[str, Callable[[Task], bool]] = {
    "active": lambda task: task.active,
    "planned": lambda task: task.state == State.PLANNED,
    "running": lambda task: task.state == State.RUNNING,
    "followup": lambda task: task.needs_follow_up,
    "ended": lambda task: task.state == State.ENDED,
    "cancelled": lambda task: task.state == State.CANCELLED,
    "all": lambda task: True,
}


@dataclass(frozen=True)
class Filters:
    """The list's filters as the query gives them, each unknown value
    replaced by its default: STATE, a key of ``STATE_TESTS``; PERSON,
    initials, ``none`` or empty; PRIORITY, a priority or empty; and Q,
    the searched text."""

    state: str = "active"
    person: str = ""
    priority: str = ""
    q: str = ""

    @classmethod
    def from_query(cls, query: Any, initials: set[str]) -> "Filters":
        """Return the filters of QUERY, a mapping of GET parameters,
        given the INITIALS of every account."""
        state = query.get("state", "")
        person = query.get("person", "").strip()
        priority = query.get("priority", "")
        return cls(
            state=clean_choice(state, STATE_TESTS, "active"),
            person=("none" if person == "none"
                    else clean_choice(person.upper(), initials)),
            priority=clean_choice(priority, Priority.values),
            q=query.get("q", "").strip())

    def filter_pairs(self) -> list[tuple[str, str]]:
        """Return the non-default active filter pairs."""
        pairs: list[tuple[str, str]] = []
        if self.state != "active":
            pairs.append(("state", self.state))
        if self.person:
            pairs.append(("person", self.person))
        if self.priority:
            pairs.append(("priority", self.priority))
        if self.q:
            pairs.append(("q", self.q))
        return pairs

    def query_string(self) -> str:
        """Return the non-default active filter parameters encoded with a
        leading ``?``, or empty when all filters are at their defaults."""
        pairs = self.filter_pairs()
        return "?" + urlencode(pairs) if pairs else ""


def searched_text(task: Task) -> str:
    """The text the list's search looks in, folded for a comparison
    regardless of case: the number, the substance's key and names, the
    numbers of its batches and the note. The task's steps and their
    batches are read as prefetched."""
    substance = task.substance
    parts = [task.number, substance.key, substance.name, substance.name_de,
             *(batch.number for batch in made_batches(task)), task.note]
    return "\n".join(parts).casefold()


def made_batches(task: Task) -> list[Batch]:
    """Return the batches the steps of TASK made, in the order of their
    IDs, as prefetched with the steps (``steps__batches``)."""
    return sorted((batch for step in task.steps.all()
                   for batch in step.batches.all()),
                  key=lambda batch: batch.pk)


def product_numbers(task: Task) -> str:
    """Return the numbers of the product batches of TASK, the made
    batches of its substance, in the order of their IDs, joined by
    ``, ``; the steps and their batches are read as prefetched."""
    return ", ".join(batch.number for batch in made_batches(task)
                     if batch.substance_id == task.substance_id)


def _first_product_number(task: Task) -> str:
    """Return the number of the first product batch of TASK, as
    ``product_numbers`` orders them, or ``""`` when it has none."""
    return next((batch.number for batch in made_batches(task)
                 if batch.substance_id == task.substance_id), "")


def selected(tasks: list[Task], filters: Filters,
             priorities: Mapping[int, TaskPriority], by_state: bool = True
             ) -> list[Task]:
    """Return the TASKS FILTERS selects, leaving out the state filter
    unless BY_STATE; PRIORITIES maps each task's ID to its priority."""
    words = filters.q.casefold()
    return [
        task for task in tasks
        if (not by_state or STATE_TESTS[filters.state](task))
        and (not filters.person
             or (task.assignee is None if filters.person == "none"
                 else task.assignee is not None
                 and task.assignee.initials == filters.person))
        and (not filters.priority
             or priorities[task.pk].priority == filters.priority)
        and (not words or words in searched_text(task))]


def _task_detail_context(task: Task,
                         shown_priority: TaskPriority | None = None
                         ) -> dict[str, Any]:
    """Return the details-pane context for TASK."""
    if shown_priority is None:
        shown_priority = Plan(timezone.localdate()).task_priority(task)
    steps = [
        shown_step(step)
        for step in task.steps.select_related(
            "entry__procedure").order_by("position")
    ]
    return {
        "detail_task": task,
        "detail_shown": shown_priority,
        "detail_batches": list(task.product_batches().order_by("id")),
        "detail_steps": steps,
    }


@vary_on_cookie
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def task_list(request: HttpRequest) -> HttpResponse:
    """List the tasks the query's filters select, in the requested or
    default order, each with its priority, computed or entered, and the
    counts of planned, running and follow-up tasks among those the
    filters other than the state select."""
    accounts = list(get_user_model().objects.order_by("initials"))
    filters = Filters.from_query(request.GET,
                                 {user.initials for user in accounts})
    order = Order.from_query(request.GET, TASK_COLUMNS, "priority")
    tasks = list(Task.objects.select_related("assignee", "substance")
                 .prefetch_related("steps__batches"))
    plan = Plan(timezone.localdate())
    priorities = {task.pk: plan.task_priority(task) for task in tasks}
    counted = selected(tasks, filters, priorities, by_state=False)
    shown = sorted(selected(counted, filters, priorities),
                   key=lambda task: task.sort_key(
                       priorities[task.pk].priority,
                       priorities[task.pk].slack))
    rows = order.ordered([(task, priorities[task.pk], product_numbers(task))
                          for task in shown])
    chosen, selected_key = pick_selected(
        rows, request.GET.get("selected", ""), lambda row: row[0].number)
    filter_pairs = filters.filter_pairs()
    detail = (_task_detail_context(chosen[0], chosen[1]) if chosen
              else {"detail_task": None, "detail_shown": None,
                    "detail_batches": [], "detail_steps": []})
    response = render(request, "tasks/list.html", {
        "tasks": rows,
        **detail,
        "selected": selected_key,
        "order": order,
        "headers": order.headers(TASKS_URL, filter_pairs, selected_key,
                                 TASK_CLASSES),
        "view": list_view(request, TASK_COOKIE),
        "filters": filters,
        "accounts": accounts,
        "state_filters": STATE_FILTERS,
        "priorities": Priority.choices,
        "counts": {
            "planned": sum(t.state == State.PLANNED for t in counted),
            "running": sum(t.state == State.RUNNING for t in counted),
            "followup": sum(t.needs_follow_up for t in counted),
        },
    })
    pairs = [*filter_pairs, *order.pairs()]
    if selected_key:
        pairs.append(("selected", selected_key))
    return htmx_list_push_url(
        request, response,
        f"{TASKS_URL}?{urlencode(pairs)}" if pairs else TASKS_URL)


@require_GET
@vary_on_headers("HX-Request", "HX-Current-URL")
def task_detail(request: HttpRequest, number: str) -> HttpResponse:
    """Answer a GET htmx request with the details pane of task NUMBER,
    or redirect non-htmx GET requests to the task list with ``selected``
    naming the task. Answer 404 for an unknown number and 405 for
    methods other than GET."""
    task = get_object_or_404(
        Task.objects.select_related("assignee", "substance"), number=number)
    return htmx_detail_or_redirect(
        request, TASKS_URL, task.number, "tasks/list.html#detail",
        lambda: _task_detail_context(task))


@dataclass(frozen=True)
class MadeBatch:
    """A batch a step made as the task page lists it: the BATCH, the
    amount its FLASK holds, a pair of the amount and its unit, or None
    when it has no flask or the flask holds nothing, and the amounts
    STORED in its stored vessels, such pairs by unit."""

    batch: Batch
    flask: tuple[Decimal, str] | None = None
    stored: list[tuple[Decimal, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Step:
    """A step of a task as its page lists it: its ID and POSITION; its
    PROCEDURE's ID, empty for a step without an entry, and whether the
    procedure is KNOWN, not withdrawn; the NUMBER of its entry, its
    position, for an entry of a general procedure that is not
    withdrawn, else None; the SIGNATURE of its entry when the entry is
    withdrawn, else empty; the day it was DONE_ON, or None; the BATCHES
    it made and the WITHDRAWALS booked into it, in the order of their
    IDs; the open vessels OFFERED for a withdrawal into it, empty unless
    the page offers one; and the JOURNAL_ENTRY it is written down in, or
    None."""

    id: int
    position: int
    procedure: str
    known: bool
    number: int | None
    signature: str
    done_on: Any
    batches: list[MadeBatch] = field(default_factory=list)
    withdrawals: list[VesselMovement] = field(default_factory=list)
    offered: list[Vessel] = field(default_factory=list)
    journal_entry: Any = None


def made_by(step: TaskStep) -> list[MadeBatch]:
    """Return the batches STEP made, in the order of their IDs, each
    with the amount of its flask while that holds one and the amounts of
    its stored vessels."""
    batches = getattr(step, "prefetched_batches", None)
    if batches is None:
        batches = list(step.batches.select_related(
            "substance", "journal_entry__notebook").prefetch_related(
                Prefetch("vessels", queryset=Vessel.objects.order_by("id"))
            ).order_by("id"))
    found = []
    for batch in batches:
        vessels = list(batch.vessels.all())
        flask = next((vessel for vessel in vessels
                      if vessel.flask and vessel.amount > 0), None)
        found.append(MadeBatch(
            batch=batch,
            flask=None if flask is None else (
                shown(flask.amount, flask.unit), flask.unit_label),
            stored=stock_of([vessel for vessel in vessels
                             if not vessel.flask])))
    return found


def shown_step(step: TaskStep, offer: bool = False,
               offered: list[Vessel] | None = None) -> Step:
    """Return STEP, its entry and procedure read, as its task's page
    lists it, with the batches it made and the withdrawals into it; when
    OFFER, with the open vessels of its substrates, or of any substance
    for a step without an entry, as those offered for a withdrawal."""
    withdrawals = getattr(step, "prefetched_withdrawals", None)
    if withdrawals is None:
        withdrawals = list(step.vessel_movements.filter(
            kind=VesselMovement.Kind.WITHDRAWAL).select_related(
                "vessel__batch", "reversal").order_by("id"))
    records = {
        "id": step.pk, "position": step.position, "done_on": step.done_on,
        "batches": made_by(step),
        "withdrawals": withdrawals,
        "offered": (offered if offered is not None
                    else offered_vessels(step)) if offer else [],
        "journal_entry": step.journal_entry}
    entry = step.entry
    if entry is None:
        return Step(procedure="", known=False, number=None, signature="",
                    **records)
    procedure = entry.procedure
    return Step(
        procedure=procedure.key, known=not procedure.withdrawn,
        number=entry.position if procedure.general and not entry.withdrawn
        else None,
        signature=entry.signature if entry.withdrawn else "", **records)


def offered_vessels(step: TaskStep) -> list[Vessel]:
    """Return the open vessels a withdrawal into STEP may come from:
    those of its substrates, or of any substance for a step without an
    entry, by substance key and then by ID."""
    vessels = Vessel.objects.filter(amount__gt=0).select_related(
        "batch__substance")
    substrates = step.substrates()
    if substrates is not None:
        vessels = vessels.filter(batch__substance__in=substrates)
    return list(vessels.order_by("batch__substance__key", "id"))


def _offered_by_step(steps: list[TaskStep]) -> dict[int, list[Vessel]]:
    """Return the open vessels offered for withdrawal for each step in
    STEPS, loading open vessels and entry substrates once."""
    all_open = list(Vessel.objects.filter(amount__gt=0).select_related(
        "batch__substance").order_by("batch__substance__key", "id"))
    entry_ids = {step.entry_id for step in steps if step.entry_id is not None}
    substrates: dict[int, set[int]] = {}
    if entry_ids:
        for entry_id, substance_id in EntrySubstance.objects.filter(
                entry_id__in=entry_ids, role="substrate").values_list(
                    "entry_id", "substance_id"):
            substrates.setdefault(entry_id, set()).add(substance_id)
    offered: dict[int, list[Vessel]] = {}
    for step in steps:
        if step.entry_id is None:
            offered[step.pk] = all_open
        else:
            needed = substrates.get(step.entry_id, set())
            offered[step.pk] = [vessel for vessel in all_open
                                if vessel.batch.substance_id in needed]
    return offered


def task_page(request: HttpRequest, number: str) -> HttpResponse:
    """Show the task NUMBER with its priority, sequence, steps, actions,
    the forecast of each article it matches, its product batches and its
    history; answer 404 for an unknown number.

    Each step lists the batches it made and the withdrawals into it, and
    the journal entry it names. For a signed-in user each step offers
    the form that sets its journal entry, and, while the task is planned
    or running, to record a batch it made and a withdrawal from the open
    vessels ``offered_vessels`` gives.
    """
    task = get_object_or_404(Task.objects.select_related(
        "assignee", "created_by", "substance", "sequence"), number=number)
    plan = Plan(timezone.localdate())
    steps = list(task.steps.select_related(
        "entry__procedure", "journal_entry__notebook").prefetch_related(
        Prefetch(
            "batches",
            queryset=Batch.objects.select_related(
                "substance", "journal_entry__notebook").prefetch_related(
                Prefetch("vessels", queryset=Vessel.objects.order_by("id"))
            ).order_by("id"),
            to_attr="prefetched_batches",
        ),
        Prefetch(
            "vessel_movements",
            queryset=VesselMovement.objects.filter(
                kind=VesselMovement.Kind.WITHDRAWAL).select_related(
                "vessel__batch", "reversal").order_by("id"),
            to_attr="prefetched_withdrawals",
        ),
    ).order_by("position"))
    recording = request.user.is_authenticated and task.state in (
        State.PLANNED, State.RUNNING)
    offered = _offered_by_step(steps) if recording else {}
    return render(request, "tasks/page.html", {
        "task": task,
        "steps": [shown_step(step, recording, offered.get(step.pk))
                  for step in steps],
        "recording": recording,
        "sequence_known": task.sequence is not None
        and not task.sequence.withdrawn,
        "actions": [(name, action.label)
                    for name, action in ACTIONS.items()
                    if action.applies(task)]
        if request.user.is_authenticated else [],
        "history": history_entries(task),
        "shown": plan.task_priority(task),
        "articles": plan.articles_of(task),
        "product_batches": task.product_batches().order_by("id"),
    })


def form_page(request: HttpRequest, form_class: type[TaskForm],
              task: Task, initial: dict[str, Any] | None = None
              ) -> HttpResponse:
    """Show FORM_CLASS for TASK, with the INITIAL values given, or save
    the posted form and return to the task's page with a message; a
    form with errors shows again.

    A posted form is checked and saved in one transaction that holds
    the import lock and, for an existing task, its row, so that the
    steps it checks are the steps it changes and a sequence's steps
    and the latest accepted import are read as one import left them.
    """
    if request.method == "POST":
        with transaction.atomic():
            lock.hold()
            if task.pk is not None:
                task = Task.objects.select_for_update().get(pk=task.pk)
            form = form_class(request.POST, instance=task,
                              user=request.user)
            if form.is_valid():
                saved = form.save()
                messages.success(request, _("Task %(number)s saved.")
                                 % {"number": saved.number})
                return redirect("task", number=saved.number)
    else:
        form = form_class(instance=task, initial=initial, user=request.user)
    return render(request, "tasks/form.html", {"form": form, "task": task})


@login_required
def task_new(request: HttpRequest) -> HttpResponse:
    """Create a task, made by the signed-in user; ``substance``,
    ``sequence`` and ``start_step`` in the query fill in the substance's
    key, the sequence's ID and the start step."""
    return form_page(request, TaskForm, Task(created_by=request.user), {
        name: request.GET[name]
        for name in ("substance", "sequence", "start_step")
        if name in request.GET})


@login_required
def task_edit(request: HttpRequest, number: str) -> HttpResponse:
    """Change the task NUMBER; answer 404 for an unknown number."""
    return form_page(request, TaskEditForm,
                     get_object_or_404(Task, number=number))


def _start(task: Task) -> str:
    task.started = timezone.localdate()
    return _("Task %(number)s started.")


def _step(task: Task) -> str:
    finish(task, timezone.localdate(), first_only=True)
    return _("Step %(done)s of %(total)s of task %(number)s done.")


def _end(task: Task) -> str:
    task.ended = timezone.localdate()
    finish(task, task.ended, first_only=False)
    return _("Task %(number)s ended.")


def _fail(task: Task) -> str:
    task.failed = True
    task.ended = timezone.localdate()
    return _("Task %(number)s failed.")


def _report(task: Task) -> str:
    task.report = True
    return _("The report of task %(number)s is done.")


def _qc_list(task: Task) -> str:
    task.qc_list = True
    return _("Task %(number)s is on the QC list.")


@dataclass(frozen=True)
class Action:
    """A button of the task page: its LABEL, whether it APPLIES to a
    task, the CHANGE it makes to one, which returns the message of the
    change and saves the steps it marks done, the REFUSAL shown when it
    does not apply, and the FIELDS of the task the change sets, the
    only ones it saves; a change that sets none saves no task record.
    CLOSES tells whether the change closes the task, so that the flasks
    of its batches are written off in the same transaction."""

    label: Any
    applies: Callable[[Task], bool]
    change: Callable[[Task], str]
    refusal: Any
    fields: tuple[str, ...]
    closes: bool = False


ACTIONS = {
    "start": Action(
        gettext_lazy("Start"), lambda t: t.state == State.PLANNED, _start,
        gettext_lazy("Only a planned task can be started."), ("started",)),
    "step": Action(
        gettext_lazy("Step done"),
        lambda t: (t.state == State.RUNNING
                   and t.steps.filter(done_on=None).exists()), _step,
        gettext_lazy("Only a running task with steps left can finish a "
                     "step."), ()),
    "end": Action(
        gettext_lazy("End"),
        lambda t: t.state == State.RUNNING and t.has_product_batch, _end,
        gettext_lazy("Only a running task with a product batch, a batch "
                     "of its substance made by one of its steps, can be "
                     "ended."), ("ended",), closes=True),
    "fail": Action(
        gettext_lazy("Failed"),
        lambda t: t.state == State.RUNNING and not t.has_product_batch,
        _fail,
        gettext_lazy("Only a running task without a product batch can "
                     "fail."), ("failed", "ended"), closes=True),
    "report": Action(
        gettext_lazy("Report done"),
        lambda t: t.state == State.ENDED and not t.report, _report,
        gettext_lazy("Only an ended task whose report is not done can "
                     "have it marked done."), ("report",)),
    "qc-list": Action(
        gettext_lazy("On QC list"),
        lambda t: t.state == State.ENDED and not t.qc_list, _qc_list,
        gettext_lazy("Only an ended task not yet on the QC list can be "
                     "put on it."), ("qc_list",)),
}


@login_required
@require_POST
def task_action(request: HttpRequest, number: str, action: str
                ) -> HttpResponse:
    """Apply ACTION to the task NUMBER and return to its page with a
    message.

    The task is read, checked and saved in one transaction, locked on
    PostgreSQL, and only the fields the action sets are written, so
    actions on one task at once neither act on a stale state nor undo
    each other. An action that closes the task, ``end`` and ``fail``,
    writes off what its flasks hold in that transaction, and its message
    names the amounts. An action that does not apply to the task's state
    changes nothing and leaves an error message. Answer 404 for an
    unknown task or action, and 405 for a request other than POST.
    """
    if action not in ACTIONS:
        raise Http404
    chosen = ACTIONS[action]
    with transaction.atomic():
        task = get_object_or_404(Task.objects.select_for_update(),
                                 number=number)
        applies = chosen.applies(task)
        if applies:
            text = chosen.change(task)
            if chosen.fields:
                task.save(update_fields=chosen.fields)
            written = write_off_flasks(request.user, task) \
                if chosen.closes else []
            done, total = task.step_counts
    if applies:
        text = text % {"number": task.number, "done": done, "total": total}
        if written:
            text += " " + _("Written off: %(amounts)s.") % {
                "amounts": amounts(written)}
        messages.success(request, text)
    else:
        messages.error(request, chosen.refusal)
    return redirect("task", number=task.number)


@login_required
@require_POST
def step_journal(request: HttpRequest, step: int) -> HttpResponse:
    """Make the task step STEP name the journal entry the posted
    ``journal_entry`` gives, ``<code>/<number>``, created when it is
    new, or none for an empty value, and return to its task's page with
    a message; the change is recorded in the step's history.

    A value that ``journal.entries.entry_for`` refuses changes nothing
    and leaves its error as the message. The step's task is locked for
    the change, as a task edit locks it, so the edit's rules on steps
    that name an entry hold. Answer 404 for an unknown step, or one
    removed meanwhile, and 405 for a request other than POST.
    """
    found = get_object_or_404(TaskStep.objects.select_related("task"),
                              pk=step)
    value = request.POST.get("journal_entry", "").strip()
    try:
        with transaction.atomic():
            Task.objects.select_for_update().get(pk=found.task_id)
            found = get_object_or_404(
                TaskStep.objects.select_related("task"), pk=step)
            entry = entry_for(value) if value else None
            if found.journal_entry_id != (None if entry is None
                                          else entry.pk):
                found.journal_entry = entry
                found.save(update_fields=["journal_entry"])
    except ValidationError as refused:
        messages.error(request, " ".join(refused.messages))
    else:
        messages.success(request, _("Lab notebook of step %(position)s "
                                    "saved.") % {"position": found.position})
    return redirect("task", number=found.task.number)
