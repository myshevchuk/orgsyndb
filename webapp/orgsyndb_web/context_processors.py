"""Template context shared by every page of the application."""

from typing import Any

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from demo import data, models

SITE_TITLE = "OrgSynDB"
SITE_SECTIONS = [
    ("/compounds/", _("Compounds")),
    ("/sequences/", _("Sequences")),
    ("/procedures/", _("Procedures")),
    ("/help/", _("Help")),
]
# The application's views: each a link and the path its pages lie under.
VIEWS = [
    ("/lab/inventory/end-products/", _("Inventory"), "/lab/inventory/"),
    ("/lab/planning/", _("Planning"), "/lab/planning/"),
    ("/lab/tasks/", _("Tasks"), "/lab/tasks/"),
]


def navigation(path: str) -> list[dict[str, Any]]:
    """Return the header's links for a page at PATH, in order: the
    application's views, then the site's sections.

    Each link is a dict of ``url``, ``label`` and ``current``: ``page``
    for the link to PATH itself, ``true`` for the link of the view whose
    pages PATH lies under, and the empty string otherwise.
    """
    links = VIEWS + [(url, label, None) for url, label in SITE_SECTIONS]
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
    """Return the context of the page shell: the site title, the
    navigation for the requested path, and the database's demo mark,
    None outside a demo database, with the demo accounts that sign
    in and their password."""
    return {"site_title": SITE_TITLE,
            "navigation": navigation(request.path),
            "demo_mark": models.current(),
            "demo_accounts": data.signing_in(),
            "demo_password": data.PASSWORD}
