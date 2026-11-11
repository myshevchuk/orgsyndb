"""The imports, procedures and sequences in the admin, for staff to read.

Only an accepted import writes these rows, so the admin shows them
read-only: it adds, changes and deletes none.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from collection.models import (Import, Procedure, ScopeEntry, Sequence,
                               Step)


class ReadOnly(admin.ModelAdmin):
    """An admin that shows its records and grants no permission to add,
    change or delete one."""

    def has_add_permission(self, request: HttpRequest,
                           obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False


class ReadOnlyInline(admin.TabularInline):
    """An inline that shows its rows and grants no permission to add,
    change or delete one."""

    extra = 0
    can_delete = False

    def has_add_permission(self, request: HttpRequest,
                           obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False


@admin.register(Import)
class ImportAdmin(ReadOnly):
    list_display = ("received_at", "short_commit", "trigger", "outcome",
                    "release")
    list_filter = ("outcome", "trigger")

    @admin.display(description="Commit")
    def short_commit(self, record: Import) -> str:
        """The first ten digits of RECORD's commit."""
        return record.commit[:10]


class EntryInline(ReadOnlyInline):
    model = ScopeEntry
    fields = ("position", "signature", "withdrawn")


@admin.register(Procedure)
class ProcedureAdmin(ReadOnly):
    list_display = ("key", "title", "source", "reaction_type", "withdrawn",
                    "last_import")
    list_filter = ("withdrawn", "source")
    search_fields = ("key", "title", "title_de")
    inlines = [EntryInline]


class StepInline(ReadOnlyInline):
    model = Step
    fields = ("position", "entry")


@admin.register(Sequence)
class SequenceAdmin(ReadOnly):
    list_display = ("key", "title", "target", "withdrawn", "last_import")
    list_filter = ("withdrawn",)
    search_fields = ("key", "title", "title_de")
    inlines = [StepInline]
