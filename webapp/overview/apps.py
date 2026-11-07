"""The overview of the lab application."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OverviewConfig(AppConfig):
    name = "overview"
    verbose_name = _("Overview")
