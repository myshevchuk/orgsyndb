"""The collection's procedures and sequences as the lab application
holds them, written by the import of an accepted collection commit."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CollectionConfig(AppConfig):
    name = "collection"
    verbose_name = _("Collection")
