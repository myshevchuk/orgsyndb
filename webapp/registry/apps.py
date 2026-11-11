"""The registry of substances of the lab application."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RegistryConfig(AppConfig):
    name = "registry"
    verbose_name = _("Registry")
