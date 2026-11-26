"""Tasks in the admin, for corrections by staff."""

from typing import Any

from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from inventory.bookings import write_off_flasks
from tasks.closing import CLOSED
from tasks.models import Task, TaskStep


class TaskStepInline(admin.TabularInline):
    """A task's steps, by position, with the day each was done."""

    model = TaskStep
    fields = ("position", "entry", "planned_import", "done_on",
              "journal_entry")
    readonly_fields = fields
    ordering = ("position",)
    extra = 0
    can_delete = False

    def has_add_permission(self, request: HttpRequest,
                           obj: Task | None = None) -> bool:
        """Refuse adding a step here: the task form keeps the steps in
        line with the task's sequence."""
        return False


@admin.register(Task)
class TaskAdmin(SimpleHistoryAdmin):
    list_display = ("number", "substance", "priority", "assignee", "started",
                    "ended", "progress_shown", "report", "qc_list",
                    "cancelled", "failed")
    list_filter = ("priority", "cancelled", "failed", "report", "qc_list")
    list_select_related = ("substance", "assignee")
    search_fields = ("number", "substance__key", "substance__name",
                     "substance__name_de", "steps__batches__number")
    ordering = ("id",)
    readonly_fields = ("number", "sequence", "start_step", "created_by",
                       "created_at")
    inlines = (TaskStepInline,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Task]:
        return super().get_queryset(request).annotate(
            _steps_total=Count("steps"),
            _steps_done=Count("steps", filter=Q(steps__done_on__isnull=False)),
        )

    @admin.display(description=_("Progress"))
    def progress_shown(self, task: Task) -> str:
        """Return the steps of TASK done and its steps, as ``2/5``, or
        ``–`` without steps."""
        total = getattr(task, "_steps_total", None)
        if total is None:
            done, total = task.step_counts
        else:
            done = task._steps_done
        return f"{done}/{total}" if total else "–"

    def revert_disabled(self, request: HttpRequest, obj: Any = None
                        ) -> bool:
        """Offer no revert: a past version would bring back its sequence
        and start step without planning the steps."""
        return True

    def history_form_view(self, request: HttpRequest, object_id: str,
                          version_id: str,
                          extra_context: dict[str, Any] | None = None
                          ) -> HttpResponse:
        """Show a past version of a task; refuse a POST, which would
        restore it, with PermissionDenied (403)."""
        if request.method == "POST":
            raise PermissionDenied
        return super().history_form_view(request, object_id, version_id,
                                         extra_context)

    def changeform_view(self, request: HttpRequest,
                        object_id: str | None = None, form_url: str = "",
                        extra_context: dict[str, Any] | None = None
                        ) -> HttpResponse:
        """Show or save the change form of a task.

        A posted change form of an existing task is validated and saved
        in one transaction that holds the task's row lock, so that its
        end, failure and substance are checked against the batches
        recorded up to that moment, and a batch recorded meanwhile
        refuses the save at the field.
        """
        with transaction.atomic():
            if request.method == "POST" and object_id is not None:
                try:
                    list(Task.objects.select_for_update().filter(
                        pk=unquote(object_id)).values_list("pk", flat=True))
                except (ValueError, TypeError):
                    pass
            return super().changeform_view(request, object_id, form_url,
                                           extra_context)

    def save_model(self, request: HttpRequest, obj: Task, form: ModelForm,
                   change: bool) -> None:
        """Save OBJ, made by the signed-in user when it is new, and write
        off what the flasks of its batches hold when it is ended, failed
        or cancelled, in the same transaction."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if obj.state in CLOSED:
            write_off_flasks(request.user, obj)
