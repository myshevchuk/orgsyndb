"""The planning parameters in the admin, kept by staff.

The admin edits the one record, adds it while none exists, and deletes
none, so that a change of assumptions stays in the history.
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from planning.models import Parameters


@admin.register(Parameters)
class ParametersAdmin(SimpleHistoryAdmin):
    list_display = ("__str__", "certainty", "buffer_days",
                    "default_synthesis_days", "history_quarters",
                    "min_orders", "high_days", "medium_days", "target_days")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow adding a record only while none is stored."""
        return (super().has_add_permission(request)
                and not Parameters.objects.exists())

    def has_delete_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False
