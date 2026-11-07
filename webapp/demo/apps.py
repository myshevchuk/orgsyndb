"""The demo data of the lab application."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DemoConfig(AppConfig):
    name = "demo"
    verbose_name = _("Demo data")
