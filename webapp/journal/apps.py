"""The lab journal: the lab's paper notebooks and their entries."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class JournalConfig(AppConfig):
    name = "journal"
    verbose_name = _("Lab journal")
