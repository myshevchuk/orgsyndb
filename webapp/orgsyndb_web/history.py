"""The change history the application's records keep."""

from typing import Any

from django.db import models
from simple_history.models import HistoricalRecords


class RecordedHistory(HistoricalRecords):
    """A change history whose records are ordered as they were recorded,
    newest first, whatever their times say."""

    def get_meta_options(self, model: type[models.Model]) -> dict[str, Any]:
        """Return the options of the historical model's Meta, ordered by
        the record's ID."""
        options = super().get_meta_options(model)
        options["ordering"] = ("-history_id",)
        options["get_latest_by"] = "history_id"
        return options
