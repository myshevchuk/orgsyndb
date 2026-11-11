"""The vocabularies in the admin, for corrections by staff.

A term's key is read-only once the term exists; a parent that would put
a term under itself is refused by the term's own check. A term that a
substance or another term refers to is not deleted.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from vocabulary.models import ChemicalClass, Group, Project, ReactionType


class TermAdmin(SimpleHistoryAdmin):
    list_display = ("key", "label", "label_de")
    search_fields = ("key", "label", "label_de")
    ordering = ("key",)

    def get_readonly_fields(self, request: HttpRequest,
                            obj: Any = None) -> tuple[str, ...]:
        """Show the key read-only on the change page of OBJ."""
        fixed = tuple(super().get_readonly_fields(request, obj))
        return fixed if obj is None else ("key", *fixed)


class TreeTermAdmin(TermAdmin):
    list_display = ("key", "label", "label_de", "parent")


admin.site.register(ChemicalClass, TreeTermAdmin)
admin.site.register(Group, TreeTermAdmin)
admin.site.register(Project, TreeTermAdmin)
admin.site.register(ReactionType, TermAdmin)
