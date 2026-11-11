"""The substances in the admin, for corrections by staff.

A substance's key is read-only once it exists; its chemical classes are
edited as rows beside it. A substance that a record refers to is not
deleted.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from registry.models import Substance, SubstanceClass


class SubstanceClassInline(admin.TabularInline):
    model = SubstanceClass
    extra = 0


@admin.register(Substance)
class SubstanceAdmin(SimpleHistoryAdmin):
    list_display = ("key", "name", "name_de", "short_name", "group")
    list_filter = ("group",)
    search_fields = ("key", "name", "name_de", "short_name", "cas")
    ordering = ("key",)
    inlines = [SubstanceClassInline]

    def get_readonly_fields(self, request: HttpRequest,
                            obj: Any = None) -> tuple[str, ...]:
        """Show the key read-only on the change page of OBJ."""
        fixed = tuple(super().get_readonly_fields(request, obj))
        return fixed if obj is None else ("key", *fixed)
