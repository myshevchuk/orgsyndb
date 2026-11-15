"""The navigation that site-theme "Navigation" expects on the
application's pages, read from the menu ``main`` of ``site/hugo.toml``
and the site's interface strings, and the navigation a page shows.

A navigation is a list of entries: a link is ``(url, text)``, a group
is ``(label, [link, ...])``.
"""

import tomllib
from typing import Any

from . import REPO, Element, page

SITE = REPO / "site"
Link = tuple[str, str]
Group = tuple[str, list[Link]]
Entry = Link | Group


def strings(language: str) -> dict[str, str]:
    """The site's interface strings of LANGUAGE."""
    path = SITE / "i18n" / f"{language}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def menu() -> list[dict[str, Any]]:
    """The entries of the menu ``main``."""
    config = tomllib.loads((SITE / "hugo.toml").read_text(encoding="utf-8"))
    return config["menus"]["main"]


def _ordered(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: e.get("weight", 0))


def _children(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return _ordered([e for e in menu()
                     if e.get("parent") == entry["identifier"]])


def links() -> list[dict[str, Any]]:
    """Every link entry of the menu, in the navigation's order."""
    found = []
    for entry in _ordered([e for e in menu() if "parent" not in e]):
        found += [entry] if "url" in entry else _children(entry)
    return found


def expected(language: str) -> list[Entry]:
    """The navigation of the application's pages in LANGUAGE: every
    entry, those under /lab/ included."""
    text = strings(language)
    navigation: list[Entry] = []
    for entry in _ordered([e for e in menu() if "parent" not in e]):
        if "url" in entry:
            navigation.append((entry["url"], text[entry["identifier"]]))
        else:
            navigation.append((text[entry["identifier"]],
                               [(c["url"], text[c["identifier"]])
                                for c in _children(entry)]))
    return navigation


def expected_marks(path: str) -> dict[str, str]:
    """The ``aria-current`` values of the navigation of a page at PATH,
    by link URL."""
    for entry in links():
        if entry["url"] == path:
            return {entry["url"]: "page"}
    for entry in links():
        if any(path.startswith(p)
               for p in entry.get("params", {}).get("paths", [])):
            return {entry["url"]: "true"}
    return {}


def nav(root: Element) -> Element:
    """The navigation of a page's header."""
    header = root.find("header", cls="site-header")
    assert header is not None, "no header.site-header"
    navs = header.find_all("nav")
    assert len(navs) == 1, f"{len(navs)} nav elements in the header"
    return navs[0]


def _elements(node: Element) -> list[Element]:
    return [c for c in node.children if isinstance(c, Element)]


def shown(root: Element) -> list[Entry]:
    """The navigation a page shows: the items of its list, each a link
    or a label followed by a list of links."""
    lists = [e for e in _elements(nav(root)) if e.tag == "ul"]
    assert len(lists) == 1, "the nav does not hold one list"
    navigation: list[Entry] = []
    for item in _elements(lists[0]):
        parts = _elements(item)
        if parts and parts[0].tag == "a":
            assert len(parts) == 1, "a link item holds more than its link"
            navigation.append((parts[0].get("href"), parts[0].text()))
            continue
        assert [p.tag for p in parts][1:] == ["ul"], [p.tag for p in parts]
        navigation.append((parts[0].text(),
                           [(a.get("href"), a.text())
                            for a in parts[1].find_all("a")]))
    return navigation


def marks(response: Any) -> dict[str, str]:
    """The ``aria-current`` values of a response's navigation, by link
    URL."""
    return {a.get("href"): a.get("aria-current")
            for a in nav(page(response)).find_all("a")
            if a.get("aria-current") is not None}
