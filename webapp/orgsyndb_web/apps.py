"""The project package as an application: templates, static files,
translations and template tags of the page shell."""

from django.apps import AppConfig


class OrgsyndbWebConfig(AppConfig):
    name = "orgsyndb_web"
    verbose_name = "OrgSynDB"
