"""Tasks in the admin, for corrections by staff."""

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from tasks.models import Task, TaskStep


class TaskStepInline(admin.TabularInline):
    """A task's steps, by position, with the day each was done."""

    model = TaskStep
    fields = ("position", "entry", "planned_import", "done_on")
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
                    "ended", "progress_shown", "batch", "report", "qc_list",
                    "cancelled", "failed")
    list_filter = ("priority", "cancelled", "failed", "report", "qc_list")
    list_select_related = ("substance", "assignee")
    search_fields = ("number", "substance__key", "substance__name",
                     "substance__name_de", "batch")
    ordering = ("id",)
    readonly_fields = ("number", "sequence", "created_by", "created_at")
    inlines = (TaskStepInline,)

    @admin.display(description=_("Progress"))
    def progress_shown(self, task: Task) -> str:
        """Return the steps of TASK done and its steps, as ``2/5``, or
        ``–`` without steps."""
        done, total = task.step_counts
        return f"{done}/{total}" if total else "–"

    def save_model(self, request: HttpRequest, obj: Task, form: ModelForm,
                   change: bool) -> None:
        """Save OBJ, made by the signed-in user when it is new."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
