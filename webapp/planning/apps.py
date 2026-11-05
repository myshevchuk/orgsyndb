"""Production planning of the lab application."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlanningConfig(AppConfig):
    name = "planning"
    verbose_name = _("Planning")
