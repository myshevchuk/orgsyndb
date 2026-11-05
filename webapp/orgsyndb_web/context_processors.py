"""Template context shared by every page of the application."""

from typing import Any

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

SITE_TITLE = "OrgSynDB"
SITE_SECTIONS = [
    ("/procedures/", _("Procedures")),
    ("/compounds/", _("Compounds")),
    ("/sequences/", _("Sequences")),
    ("/help/", _("Help")),
]
# The application's views: each a link and the path its pages lie under.
VIEWS = [
    ("/lab/inventory/end-products/", _("Inventory"), "/lab/inventory/"),
    ("/lab/tasks/", _("Tasks"), "/lab/tasks/"),
]


def navigation(path: str) -> list[dict[str, Any]]:
    """Return the header's links for a page at PATH, in order: the
    site's sections, then the application's views.

    Each link is a dict of ``url``, ``label`` and ``current``: ``page``
    for the link to PATH itself, ``true`` for the link of the view whose
    pages PATH lies under, and the empty string otherwise.
    """
    links = [(url, label, None) for url, label in SITE_SECTIONS] + VIEWS
    shown = []
    for url, label, under in links:
        if path == url:
            current = "page"
        elif under is not None and path.startswith(under):
            current = "true"
        else:
            current = ""
        shown.append({"url": url, "label": label, "current": current})
    return shown


def shell(request: HttpRequest) -> dict[str, Any]:
    """Return the context of the page shell: the site title and the
    navigation for the requested path."""
    return {"site_title": SITE_TITLE,
            "navigation": navigation(request.path)}
