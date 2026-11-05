"""The task list, the task page, its actions and its forms."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.views.decorators.http import require_POST

from orgsyndb_web import index
from planning.plan import Plan, TaskPriority, batch_lots, bulk_link
from tasks.forms import TaskEditForm, TaskForm
from tasks.history import history_entries
from tasks.models import Priority, State, Task

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
            state=state if state in STATE_TESTS else "active",
            person=("none" if person == "none" else person.upper()
                    if person.upper() in initials else ""),
            priority=priority if priority in Priority.values else "",
            q=query.get("q", "").strip())


def searched_text(task: Task) -> str:
    """The text the list's search looks in, folded for a comparison
    regardless of case: the number, the product, the name of the
    product's compound, the batch and the note."""
    found = index.compound_for(task.product)
    parts = [task.number, task.product, found.name if found else "",
             task.batch, task.note]
    return "\n".join(parts).casefold()


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


def task_list(request: HttpRequest) -> HttpResponse:
    """List the tasks the query's filters select, in the list's order,
    each with its priority, computed or entered, and the counts of
    planned, running and follow-up tasks among those the filters other
    than the state select."""
    accounts = list(get_user_model().objects.order_by("initials"))
    filters = Filters.from_query(request.GET,
                                 {user.initials for user in accounts})
    tasks = list(Task.objects.select_related("assignee"))
    plan = Plan(timezone.localdate())
    priorities = {task.pk: plan.task_priority(task) for task in tasks}
    counted = selected(tasks, filters, priorities, by_state=False)
    shown = sorted(selected(counted, filters, priorities),
                   key=lambda task: task.sort_key(
                       priorities[task.pk].priority,
                       priorities[task.pk].slack))
    return render(request, "tasks/list.html", {
        "tasks": [(task, priorities[task.pk]) for task in shown],
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


@dataclass(frozen=True)
class Step:
    """A step of a task's sequence as its page lists it."""

    procedure: str
    known: bool
    done: bool


def task_page(request: HttpRequest, number: str) -> HttpResponse:
    """Show the task NUMBER with its priority, steps, actions, the
    forecast of each article it matches, the lots of its batch and its
    history; answer 404 for an unknown number."""
    task = get_object_or_404(Task.objects.select_related(
        "assignee", "created_by"), number=number)
    plan = Plan(timezone.localdate())
    articles = plan.articles_of(task)
    steps = [Step(procedure=ident,
                  known=index.procedure_for(ident) is not None,
                  done=position < task.steps_done)
             for position, ident in enumerate(task.sequence_steps or [])]
    return render(request, "tasks/page.html", {
        "task": task,
        "steps": steps,
        "sequence_known": bool(task.sequence)
        and index.sequence_for(task.sequence) is not None,
        "actions": [(name, action.label)
                    for name, action in ACTIONS.items()
                    if action.applies(task)]
        if request.user.is_authenticated else [],
        "history": history_entries(task),
        "shown": plan.task_priority(task),
        "articles": articles,
        "lots": batch_lots(task),
        "bulk_link": bulk_link(
            task, [line.article_number for line in articles]),
    })


def form_page(request: HttpRequest, form_class: type[TaskForm],
              task: Task, initial: dict[str, Any] | None = None
              ) -> HttpResponse:
    """Show FORM_CLASS for TASK, with the INITIAL values given, or save
    the posted form and return to the task's page with a message; a
    form with errors shows again."""
    if request.method == "POST":
        form = form_class(request.POST, instance=task)
        if form.is_valid():
            saved = form.save()
            messages.success(request, _("Task %(number)s saved.")
                             % {"number": saved.number})
            return redirect("task", number=saved.number)
    else:
        form = form_class(instance=task, initial=initial)
    found = index.current()
    return render(request, "tasks/form.html", {
        "form": form,
        "task": task,
        "compounds": found.compounds.values(),
        "sequences": found.sequences.values(),
    })


@login_required
def task_new(request: HttpRequest) -> HttpResponse:
    """Create a task, made by the signed-in user; ``product`` in the
    query fills in the product."""
    return form_page(request, TaskForm, Task(created_by=request.user),
                     {"product": request.GET.get("product", "")})


@login_required
def task_edit(request: HttpRequest, number: str) -> HttpResponse:
    """Change the task NUMBER; answer 404 for an unknown number."""
    return form_page(request, TaskEditForm,
                     get_object_or_404(Task, number=number))


def _start(task: Task) -> str:
    task.started = timezone.localdate()
    return _("Task %(number)s started.")


def _step(task: Task) -> str:
    task.steps_done += 1
    return _("Step %(done)s of %(total)s of task %(number)s done.")


def _end(task: Task) -> str:
    task.ended = timezone.localdate()
    if task.steps_total:
        task.steps_done = task.steps_total
    return _("Task %(number)s ended.")


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
    change, the REFUSAL shown when it does not apply, and the FIELDS the
    change sets, the only ones it saves."""

    label: Any
    applies: Callable[[Task], bool]
    change: Callable[[Task], str]
    refusal: Any
    fields: tuple[str, ...]


ACTIONS = {
    "start": Action(
        gettext_lazy("Start"), lambda t: t.state == State.PLANNED, _start,
        gettext_lazy("Only a planned task can be started."), ("started",)),
    "step": Action(
        gettext_lazy("Step done"),
        lambda t: (t.state == State.RUNNING and bool(t.steps_total)
                   and t.steps_done < t.steps_total), _step,
        gettext_lazy("Only a running task with steps left can finish a "
                     "step."), ("steps_done",)),
    "end": Action(
        gettext_lazy("End"), lambda t: t.state == State.RUNNING, _end,
        gettext_lazy("Only a running task can be ended."),
        ("ended", "steps_done")),
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
    each other. An action that does not apply to the task's state
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
            task.save(update_fields=chosen.fields)
    if applies:
        messages.success(request, text % {
            "number": task.number, "done": task.steps_done,
            "total": task.steps_total})
    else:
        messages.error(request, chosen.refusal)
    return redirect("task", number=task.number)
