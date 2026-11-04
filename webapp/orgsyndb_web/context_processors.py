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
VIEWS = [("/lab/tasks/", _("Tasks"))]


def navigation(path: str) -> list[dict[str, Any]]:
    """Return the header's links for a page at PATH, in order.

    Each link is a dict of ``url``, ``label`` and ``current``: ``page``
    for the link to PATH itself, ``true`` for the application's view
    PATH lies in, and the empty string otherwise.
    """
    links = []
    for url, label in SITE_SECTIONS + VIEWS:
        if path == url:
            current = "page"
        elif url.startswith("/lab/") and path.startswith(url):
            current = "true"
        else:
            current = ""
        links.append({"url": url, "label": label, "current": current})
    return links


def shell(request: HttpRequest) -> dict[str, Any]:
    """Return the context of the page shell: the site title and the
    navigation for the requested path."""
    return {"site_title": SITE_TITLE,
            "navigation": navigation(request.path)}
