"""The lab's notebooks and their entries in the admin.

Staff add and change notebooks there, the code read-only once a
notebook exists, and see each notebook's change history; a notebook
with entries is not deleted. The entries are shown read-only: only an
import or a task step that names one creates it.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from collection.admin import ReadOnly
from journal.models import Entry, Notebook


@admin.register(Notebook)
class NotebookAdmin(SimpleHistoryAdmin):
    list_display = ("code", "user", "note")
    list_select_related = ("user",)
    search_fields = ("code",)
    ordering = ("code",)

    def get_readonly_fields(self, request: HttpRequest,
                            obj: Any = None) -> tuple[str, ...]:
        """Show the code read-only on the change page of OBJ."""
        fixed = tuple(super().get_readonly_fields(request, obj))
        return fixed if obj is None else ("code", *fixed)


@admin.register(Entry)
class EntryAdmin(ReadOnly):
    list_display = ("__str__", "notebook", "number")
    list_select_related = ("notebook",)
    list_filter = ("notebook",)
    search_fields = ("notebook__code",)
    ordering = ("notebook__code", "number")
