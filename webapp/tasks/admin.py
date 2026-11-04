"""Tasks in the admin, for corrections by staff."""

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(SimpleHistoryAdmin):
    list_display = ("number", "product", "priority", "assignee", "started",
                    "ended", "steps_done", "steps_total", "batch",
                    "report", "qc_list", "cancelled")
    list_filter = ("priority", "cancelled", "report", "qc_list")
    search_fields = ("number", "product", "batch")
    ordering = ("id",)
    readonly_fields = ("number", "sequence", "sequence_steps", "created_by",
                       "created_at")

    def save_model(self, request: HttpRequest, obj: Task, form: ModelForm,
                   change: bool) -> None:
        """Save OBJ, made by the signed-in user when it is new."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
