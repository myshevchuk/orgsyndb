"""Template context shared by every page of the application."""

import tomllib
from functools import cache
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils import translation

from demo import data, models
from orgsyndb_web.config import WEBAPP

# The site of the same checkout, whose title, menu and interface strings
# the shell shows.
SITE = WEBAPP.parent / "site"


@cache
def site_config() -> dict[str, Any]:
    """Return the site's ``hugo.toml``, parsed.

    Raises ``OSError`` when the file cannot be read and
    ``tomllib.TOMLDecodeError`` when it is not TOML.
    """
    with (SITE / "hugo.toml").open("rb") as file:
        return tomllib.load(file)


@cache
def site_strings(language: str) -> dict[str, str]:
    """Return the site's interface strings of LANGUAGE, ``de`` or ``en``.

    Raises ``OSError`` when the language has no strings file.
    """
    with (SITE / "i18n" / f"{language}.toml").open("rb") as file:
        return tomllib.load(file)


def _ordered(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda entry: entry.get("weight", 0))


def navigation(path: str, language: str) -> list[dict[str, Any]]:
    """Return the navigation of a page at PATH in LANGUAGE: every entry
    of the menu ``main`` of the site's ``hugo.toml``, in order of
    weight.

    An item is a link, a dict of ``url``, ``label``, ``paths`` and
    ``current``, or a group, a dict of ``label`` and ``links``, a list
    of links. Labels are the interface strings the entries' identifiers
    name. ``current`` is ``page`` on the link whose URL is PATH;
    without one, ``true`` on the first link with a path in ``paths``
    that PATH begins with; and the empty string on every other link.
    """
    entries = site_config()["menus"]["main"]
    strings = site_strings(language)

    def link(entry: dict[str, Any]) -> dict[str, Any]:
        return {"url": entry["url"], "label": strings[entry["identifier"]],
                "paths": entry.get("params", {}).get("paths", []),
                "current": ""}

    items: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for entry in _ordered([e for e in entries if "parent" not in e]):
        if "url" in entry:
            items.append(link(entry))
            links.append(items[-1])
            continue
        group = [link(child) for child in _ordered(
            [e for e in entries if e.get("parent") == entry["identifier"]])]
        items.append({"label": strings[entry["identifier"]],
                      "links": group})
        links += group
    current = next((l for l in links if l["url"] == path), None)
    if current is not None:
        current["current"] = "page"
        return items
    current = next((l for l in links
                    if any(path.startswith(p) for p in l["paths"])), None)
    if current is not None:
        current["current"] = "true"
    return items


def active_language() -> str:
    """Return the active language, ``de`` or ``en``, without a
    region."""
    return (translation.get_language()
            or settings.LANGUAGE_CODE).split("-")[0]


def shell(request: HttpRequest) -> dict[str, Any]:
    """Return the context of the page shell: the site's title, the
    texts of its search form and sidebar toggle, and its navigation, in
    the active language, and the database's demo mark, None outside a
    demo database, with the demo accounts that sign in and their
    password."""
    language = active_language()
    strings = site_strings(language)
    return {"site_title": site_config()["title"],
            "site_strings": {key: strings[key] for key in (
                "nav_site", "nav_toggle", "search_label",
                "search_placeholder", "search_button")},
            "navigation": navigation(request.path, language),
            "demo_mark": models.current(),
            "demo_accounts": data.signing_in(),
            "demo_password": data.PASSWORD}
