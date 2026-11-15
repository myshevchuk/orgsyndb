"""The navigation that site-theme "Navigation" expects, read from the
menu ``main`` of a site's ``hugo.toml`` and its interface strings, and
the navigation a built page shows.

A navigation is a list of entries: a link is ``(url, text)``, a group
is ``(label, [link, ...])``.
"""

import tomllib
from pathlib import Path
from typing import Any

from pipeline_support import Node, Page

Link = tuple[str, str]
Group = tuple[str, list[Link]]
Entry = Link | Group


def menu(site: Path) -> list[dict[str, Any]]:
    """The entries of the menu ``main`` of ``site/hugo.toml``."""
    config = tomllib.loads((site / "hugo.toml").read_text(encoding="utf-8"))
    return config["menus"]["main"]


def strings(site: Path, language: str) -> dict[str, str]:
    """The interface strings of LANGUAGE."""
    path = site / "i18n" / f"{language}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _ordered(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: e.get("weight", 0))


def _shown(entry: dict[str, Any], lab: bool) -> bool:
    return lab or not entry["url"].startswith("/lab/")


def links(site: Path, lab: bool) -> list[dict[str, Any]]:
    """The menu's link entries that a build with or without the lab
    shows, in the navigation's order."""
    entries = menu(site)
    shown = []
    for entry in _ordered([e for e in entries if "parent" not in e]):
        if "url" in entry:
            children = [entry]
        else:
            children = _ordered([e for e in entries
                                 if e.get("parent") == entry["identifier"]])
        shown += [c for c in children if _shown(c, lab)]
    return shown


def expected(site: Path, language: str, lab: bool) -> list[Entry]:
    """The navigation of a build in LANGUAGE, with or without the lab."""
    entries = menu(site)
    text = strings(site, language)
    navigation: list[Entry] = []
    for entry in _ordered([e for e in entries if "parent" not in e]):
        if "url" in entry:
            if _shown(entry, lab):
                navigation.append((entry["url"], text[entry["identifier"]]))
            continue
        children = [(c["url"], text[c["identifier"]])
                    for c in _ordered([e for e in entries if e.get("parent")
                                       == entry["identifier"]])
                    if _shown(c, lab)]
        if children:
            navigation.append((text[entry["identifier"]], children))
    return navigation


def marks(site: Path, lab: bool, path: str) -> dict[str, str]:
    """The ``aria-current`` values the navigation of a page at PATH
    carries, by link URL."""
    shown = links(site, lab)
    for entry in shown:
        if entry["url"] == path:
            return {entry["url"]: "page"}
    for entry in shown:
        if any(path.startswith(p)
               for p in entry.get("params", {}).get("paths", [])):
            return {entry["url"]: "true"}
    return {}


def shown(page: Page, nav: Node) -> list[Entry]:
    """The navigation that NAV of PAGE shows: the items of its list,
    each a link or a label followed by a list of links."""
    lists = [e for e in nav.elements() if e.tag == "ul"]
    assert len(lists) == 1, "the nav does not hold one list"
    navigation: list[Entry] = []
    for item in lists[0].elements():
        assert item.tag == "li", item.tag
        parts = item.elements()
        if parts and parts[0].tag == "a":
            assert len(parts) == 1, "a link item holds more than its link"
            navigation.append((page.resolve(parts[0].attrs["href"]),
                               parts[0].norm()))
            continue
        assert [p.tag for p in parts][1:] == ["ul"], [p.tag for p in parts]
        navigation.append((parts[0].norm(),
                           [(link.target, link.node.norm())
                            for link in page.links(parts[1])]))
    return navigation


def texts(navigation: list[Entry]) -> list[str]:
    """Every text of a navigation, labels and links, in order."""
    found = []
    for first, second in navigation:
        if isinstance(second, list):
            found.append(first)
            found += [text for _, text in second]
        else:
            found.append(second)
    return found
