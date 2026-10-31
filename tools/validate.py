#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Validate OrgSynDB procedure files against the procedure schema.

Content roots are directories of Markdown procedures with ``+++`` TOML
front matter, such as an ox-hugo export directory. The compound
registry is a directory of ``<key>.toml`` files, one per compound; the
validator checks each of them and resolves the compound keys that
procedures name against the compounds it defines. The sequences
directory holds synthesis sequences, Markdown files whose steps name
procedures of the content roots; the validator checks that each step
exists and that the steps chain. The collection's settings file
declares further compound fields, whose values each compound file is
checked against, and names the vocabularies of its choice fields. The
validator reads no Org source: an
Org procedure reaches it only as its export, and the export checks the
Org source itself. Each problem is printed to stdout
as ``<path>:<field>: <severity>: <message>``, followed by a summary line
on stderr. The exit status is 0 when no error was found, 1 when at
least one was, and 2 on a usage or configuration error.
"""

import argparse
import datetime as dt
import math
import os
import re
import sys
import tomllib
import zoneinfo
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

APP = Path(__file__).resolve().parent.parent
DEFAULT_VOCABULARY = APP / "site" / "data" / "reaction_types.toml"
# Structure images, compounds and sequences belong to a collection; run
# from its root.
DEFAULT_STATIC_DIR = Path("static")
DEFAULT_COMPOUNDS = Path("compounds")
DEFAULT_SEQUENCES = Path("md") / "sequences"
DEFAULT_SETTINGS = Path("orgsyndb.toml")
ZONE_NAME = "Europe/Berlin"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# A compound file is named <key>.toml, the key shaped like a slug.
COMPOUND_FILE_RE = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)\.toml$")
SCALE_RE = re.compile(r"^\d+([.,]\d+)?\s+\S+$")
TIME_RE = re.compile(r"\d+([.,]\d+)?\s+(min|h|d)")
CAS_RE = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")
# The collection settings file: the format it is written in, and its
# top-level keys.
SETTINGS_FORMAT = 1
SETTINGS_KEYS = ("format", "fields")
FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
FIELD_TYPES = ("text", "number", "boolean", "choice")
# The keys of a field declaration: those every type takes, and those
# only the named type takes.
FIELD_OPTIONS = ("key", "type", "label", "label_de", "required", "column")
TYPE_OPTIONS = {
    "text": ("pattern", "unique"),
    "number": ("min", "max", "unit", "unique"),
    "boolean": (),
    "choice": ("vocabulary", "multiple"),
}
TERM_KEYS = ("label", "label_de", "parent")
STATUSES = ("draft", "checked", "retired")
# The languages a procedure may be written in. A file name may carry one
# of them before its suffix, as in OSDB-0001-x.de.md; the files of one ID
# are variants of one procedure, and the build publishes the one that
# suits the site's language. A file without a code is in any language.
LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "en"
SECTIONS_BY_LANGUAGE = {
    "en": ("Summary", "Reagents", "Procedure", "Workup and Purification",
           "Characterization", "Notes", "Hazards and Waste Disposal",
           "References"),
    "de": ("Zusammenfassung", "Reagenzien", "Durchführung",
           "Aufarbeitung und Reinigung", "Charakterisierung", "Anmerkungen",
           "Gefahren und Entsorgung", "Literatur"),
}
SECTIONS = SECTIONS_BY_LANGUAGE[DEFAULT_LANGUAGE]
# Front-matter values that every variant of a procedure shares. Each
# entry of ``scope`` is compared without its ``note``, which a
# translation translates.
SHARED_FIELDS = ("status", "reaction_types", "tags", "products",
                 "substrates", "scope", "scheme_image")
# The front-matter values that every variant of a sequence shares.
SEQUENCE_SHARED_FIELDS = ("target", "steps")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

ERROR = "error"
WARNING = "warning"


class ConfigError(Exception):
    """A usage or configuration problem that ends the run with status 2."""


class Kind(NamedTuple):
    """The naming rules of one kind of content file.

    ``noun`` names the kind in messages, ``prefix`` is the letters
    before the four digits of an ID, ``example`` a short slug that
    file-name messages show, and ``shared`` the front-matter keys that
    every variant of one ID must agree on.
    """

    noun: str
    prefix: str
    example: str
    shared: tuple[str, ...]


PROCEDURE = Kind("procedure", "OSDB", "ethyl-acetate", SHARED_FIELDS)
SEQUENCE = Kind("sequence", "SEQ", "aspirin-from-wintergreen",
                SEQUENCE_SHARED_FIELDS)


class Problem(NamedTuple):
    """One reported problem, before a path is attached."""

    field: str
    severity: str
    message: str


def error(name: str, message: str) -> Problem:
    """Return an error problem for ``name``."""
    return Problem(name, ERROR, message)


def warning(name: str, message: str) -> Problem:
    """Return a warning problem for ``name``."""
    return Problem(name, WARNING, message)


# --------------------------------------------------------------------------
# Value predicates and small helpers


def id_number(value: object, prefix: str = "OSDB") -> int | None:
    """Return the number of the ID string VALUE, or None if malformed.

    An ID is PREFIX, a hyphen and four digits, as in ``OSDB-0001``.
    """
    if not isinstance(value, str):
        return None
    match = re.match(rf"^{prefix}-(\d{{4}})$", value)
    return int(match.group(1)) if match else None


def is_valid_id(value: object, prefix: str = "OSDB") -> bool:
    """Whether VALUE is an ID string from PREFIX-0001 to PREFIX-9999."""
    number = id_number(value, prefix)
    return number is not None and number >= 1


def is_number(value: object) -> bool:
    """Whether ``value`` is a TOML integer or float (never a boolean)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_string_list(value: object) -> bool:
    """Whether ``value`` is a list whose entries are all strings."""
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def is_offset_datetime(value: object) -> bool:
    """Whether ``value`` is a TOML offset datetime (an aware datetime)."""
    return isinstance(value, dt.datetime) and value.utcoffset() is not None


def cas_check_digit_ok(cas: str) -> bool:
    """Whether a CAS number of the form ``N-NN-N`` has a valid check digit.

    The check digit is the sum of every other digit multiplied by its
    position counted from the right, modulo 10.
    """
    digits = cas.replace("-", "")
    body, check = digits[:-1], int(digits[-1])
    total = sum(i * int(d) for i, d in enumerate(reversed(body), start=1))
    return total % 10 == check


def format_offset(offset: dt.timedelta) -> str:
    """Format a UTC offset as ``+HH:MM``."""
    minutes = int(offset.total_seconds()) // 60
    sign = "-" if minutes < 0 else "+"
    hours, minutes = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def zone_offset_mismatch(value: dt.datetime,
                         zone: dt.tzinfo) -> str | None:
    """Return the zone's offset at ``value``'s instant if it differs.

    ``value`` must be aware. Returns None when its offset is the one
    ``zone`` has in force at that instant, otherwise that offset as
    ``+HH:MM``.
    """
    expected = value.astimezone(zone).utcoffset()
    if expected is None or expected == value.utcoffset():
        return None
    return format_offset(expected)


# --------------------------------------------------------------------------
# Front matter


class FrontMatter(NamedTuple):
    """Parsed front matter and the body that follows it."""

    data: dict[str, Any]
    body: str


def parse_front_matter(text: str) -> FrontMatter | Problem:
    """Split ``text`` at its ``+++`` delimiters and parse the TOML.

    Trailing whitespace and carriage returns on the delimiter lines are
    tolerated. Returns the parsed front matter and body, or a
    ``front_matter`` error describing why the text has none.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "+++":
        return error("front_matter", "file must begin with a +++ line "
                     "(TOML front matter)")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "+++":
            break
    else:
        return error("front_matter",
                     "front matter has no closing +++ line")
    try:
        # The leading newline makes tomllib's line numbers file lines.
        data = tomllib.loads("\n" + "".join(lines[1:i]))
    except tomllib.TOMLDecodeError as exc:
        return error("front_matter", f"invalid TOML: {exc}")
    return FrontMatter(data, "".join(lines[i + 1:]))


# --------------------------------------------------------------------------
# Field checks on one content file


@dataclass
class Context:
    """Settings shared by the checks of one run."""

    vocabulary: frozenset[str]
    static_dir: Path
    zone: dt.tzinfo
    compounds: frozenset[str] = frozenset()
    fields: tuple[Declaration, ...] = ()


def check_string(name: str, value: object) -> list[Problem]:
    """Check that ``value`` is a non-empty string."""
    if not isinstance(value, str):
        return [error(name, "must be a string")]
    if not value.strip():
        return [error(name, "must not be empty")]
    return []


def check_string_list(name: str, value: object,
                      non_empty: bool) -> list[Problem]:
    """Check that ``value`` is a list of non-empty strings.

    With ``non_empty`` the list itself must also have an entry.
    """
    if not is_string_list(value):
        return [error(name, "must be a list of strings, "
                      'e.g. ["A. Example"]')]
    if non_empty and not value:
        return [error(name, "must not be empty")]
    if any(not v.strip() for v in value):
        return [error(name, "entries must not be empty strings")]
    return []


def check_lastmod(value: object, date: object,
                  zone: dt.tzinfo) -> list[Problem]:
    """Check ``lastmod`` VALUE: a datetime as for ``check_datetime``, and
    not earlier than DATE when both are offset datetimes."""
    found: list[Problem] = []
    if is_offset_datetime(value) and is_offset_datetime(date) \
            and value < date:
        found.append(error("lastmod", f"{value.isoformat()} is earlier "
                           f"than date {date.isoformat()}"))
    return found + check_datetime("lastmod", value, zone)


def check_datetime(name: str, value: object,
                   zone: dt.tzinfo) -> list[Problem]:
    """Check that ``value`` is an offset datetime with the Berlin offset.

    A wrong offset is a warning; any other type is an error.
    """
    if not is_offset_datetime(value):
        return [error(name, "must be a TOML offset datetime, unquoted, "
                      "e.g. 2026-10-19T17:42:05+02:00")]
    expected = zone_offset_mismatch(value, zone)
    if expected is not None:
        return [warning(
            name, f"offset {format_offset(value.utcoffset())} is not the "
            f"Europe/Berlin offset at that instant (expected {expected})")]
    return []


def check_id(value: object, prefix: str = "OSDB") -> list[Problem]:
    """Check the ``id`` field's format and range for IDs of PREFIX."""
    if id_number(value, prefix) is None:
        return [error("id", f"{value!r} must match {prefix}-NNNN "
                      f"({prefix}- and four digits)")]
    if not is_valid_id(value, prefix):
        return [error("id", f"must be between {prefix}-0001 and "
                      f"{prefix}-9999")]
    return []


def check_slug(value: object, ident: object,
               prefix: str = "OSDB") -> list[Problem]:
    """Check that ``slug`` VALUE is the lowercased ``id`` IDENT.

    The equality check runs only when IDENT is a valid ID of PREFIX.
    """
    if not isinstance(value, str):
        return [error("slug", "must be a string")]
    if is_valid_id(ident, prefix):
        expected = str(ident).lower()
        if value != expected:
            return [error("slug",
                          f'must be "{expected}" (the lowercased id)')]
    return []


def check_status(value: object) -> list[Problem]:
    """Check that ``status`` is one of the workflow states."""
    if value not in STATUSES:
        return [error("status", f"{value!r} must be one of "
                      f"{', '.join(STATUSES)}")]
    return []


def check_reaction_types(value: object,
                         vocabulary: frozenset[str]) -> list[Problem]:
    """Check that ``reaction_types`` holds one slug from the vocabulary."""
    name = "reaction_types"
    if not is_string_list(value):
        return [error(name, "must be a list of strings, "
                      'e.g. ["esterification"]')]
    if len(value) != 1:
        return [error(name, "must contain exactly one reaction type")]
    if value[0] not in vocabulary:
        return [error(name, f'unknown reaction type "{value[0]}"; see '
                      "site/data/reaction_types.toml for the allowed "
                      "values")]
    return []


def check_tags(value: object) -> list[Problem]:
    """Check that ``tags`` is a non-empty list of slug-shaped strings."""
    if not is_string_list(value):
        return [error("tags", 'must be a list of strings, '
                      'e.g. ["sample-data"]')]
    if not value:
        return [error("tags", "must not be empty")]
    return [error("tags", f'tag "{tag}" must be lowercase and '
                  'hyphenated, e.g. "sample-data"')
            for tag in value if not SLUG_RE.match(tag)]


def check_yield(name: str, value: object) -> list[Problem]:
    """Check that the yield ``value`` is a finite number from 0 to 100.

    Problems are reported under ``name``.
    """
    if not is_number(value):
        return [error(name, "must be a number, unquoted, e.g. 85")]
    if not math.isfinite(value) or not 0 <= value <= 100:
        return [error(name, f"{value} must be between 0 and 100")]
    return []


def check_scale(value: object, name: str = "scale") -> list[Problem]:
    """Check that the scale ``value`` is a number, whitespace and a unit.

    Problems are reported under ``name``.
    """
    if not isinstance(value, str) or not SCALE_RE.match(value):
        return [error(name, f"{value!r} must be a number followed by "
                      'a unit, e.g. "25 mmol"')]
    return []


def check_time(name: str, value: object) -> list[Problem]:
    """Check that the time ``value`` is a number, whitespace and one of
    the units ``min``, ``h`` and ``d``, reporting under ``name``."""
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        shown = f'"{value}"' if isinstance(value, str) else repr(value)
        return [error(name, f"{shown} must be a number followed by min, "
                      'h or d, e.g. "2 h"')]
    return []


def check_temperature(name: str, value: object) -> list[Problem]:
    """Check that the temperature ``value`` is a finite number, reporting
    under ``name``."""
    if not is_number(value) or not math.isfinite(value):
        return [error(name, "must be a number in °C, unquoted, e.g. 80")]
    return []


def check_products(value: object, compounds: frozenset[str],
                   name: str = "products") -> list[Problem]:
    """Check the products array of tables ``value`` against the registry.

    Problems are reported under ``name``: one inside the n-th table,
    counting from 1, under ``<name>[n].<key>``, and an entry that is not
    a table under ``<name>[n]``; such an entry gets no sub-field checks.
    A ``compound`` that is not a string is not looked up in
    ``compounds``, the registry's keys. A key named by two tables is one
    error under ``name``.
    """
    if not isinstance(value, list):
        return [error(name, "must be an array of tables, e.g. "
                      '[{ compound = "ethyl-acetate", yield_percent = 85 }]')]
    if not value:
        return [error(name, "must not be empty")]
    found: list[Problem] = []
    keys: list[str] = []
    for number, entry in enumerate(value, start=1):
        prefix = f"{name}[{number}]"
        if not isinstance(entry, dict):
            found.append(error(prefix, "must be a table, e.g. "
                               '{ compound = "ethyl-acetate", '
                               "yield_percent = 85 }"))
            continue
        if "compound" not in entry:
            found.append(error(f"{prefix}.compound",
                               "required field missing"))
        elif not isinstance(entry["compound"], str):
            found.append(error(f"{prefix}.compound", "must be a string"))
        else:
            keys.append(entry["compound"])
            found += check_compound_key(f"{prefix}.compound",
                                        entry["compound"], compounds)
        if "yield_percent" not in entry:
            found.append(error(f"{prefix}.yield_percent",
                               "required field missing"))
        else:
            found += check_yield(f"{prefix}.yield_percent",
                                 entry["yield_percent"])
        for key in entry:
            if key not in ("compound", "yield_percent"):
                found.append(warning(f"{prefix}.{key}", "unknown field"))
    found += [error(name, f"lists {key} twice") for key in repeated(keys)]
    return found


def check_substrates(value: object, products: object,
                     compounds: frozenset[str], name: str = "substrates",
                     non_empty: bool = False) -> list[Problem]:
    """Check the substrates ``value``: registry keys, none twice, none a
    product.

    ``products`` is the products value of the same procedure or scope
    entry; the compound keys of its well-formed tables are the ones a
    substrate must not repeat. ``compounds`` holds the registry's keys.
    Problems are reported under ``name``. With ``non_empty`` an empty
    list is an error.
    """
    if not is_string_list(value):
        return [error(name, "must be a list of compound keys, "
                      'e.g. ["ethanol"]')]
    if non_empty and not value:
        return [error(name, "must not be empty")]
    found: list[Problem] = []
    for key in value:
        found += check_compound_key(name, key, compounds)
    found += [error(name, f"lists {key} twice") for key in repeated(value)]
    made = product_keys(products)
    found += [error(name, f"{key} is also a product")
              for key in dict.fromkeys(value) if key in made]
    return found


def check_compound_key(name: str, key: str,
                       compounds: frozenset[str]) -> list[Problem]:
    """Check that ``key`` is a key of the registry ``compounds``."""
    if key not in compounds:
        return [error(name, f'unknown compound "{key}"; the compound '
                      f"registry has no {key}.toml")]
    return []


def check_scope(value: object, compounds: frozenset[str]) -> list[Problem]:
    """Check ``scope``, the entries of a general procedure.

    ``value`` must be a non-empty array of tables. A problem in the n-th
    entry, counting from 1, is reported under ``scope[n].<key>``, one in
    its m-th product under ``scope[n].products[m].<key>``, and an entry
    that is not a table under ``scope[n]``. Each entry's ``substrates``
    and ``products`` are checked as the top-level fields are, against
    that entry alone and the registry keys ``compounds``; an entry key
    other than these two, ``scale``, ``time``, ``temperature`` and
    ``note`` is a warning.
    """
    if not isinstance(value, list):
        return [error("scope", "must be an array of tables, e.g. "
                      '[{ substrates = ["ethanol"], products = '
                      '[{ compound = "ethyl-acetate", yield_percent = 85 }] '
                      "}]")]
    if not value:
        return [error("scope", "must not be empty")]
    found: list[Problem] = []
    for number, entry in enumerate(value, start=1):
        prefix = f"scope[{number}]"
        if not isinstance(entry, dict):
            found.append(error(prefix, "must be a table, e.g. "
                               '{ substrates = ["ethanol"], products = '
                               '[{ compound = "ethyl-acetate", '
                               "yield_percent = 85 }] }"))
            continue
        for key in ("substrates", "products"):
            if key not in entry:
                found.append(error(f"{prefix}.{key}",
                                   "required field missing"))
        for key, item in entry.items():
            name = f"{prefix}.{key}"
            match key:
                case "substrates":
                    found += check_substrates(item, entry.get("products"),
                                              compounds, name,
                                              non_empty=True)
                case "products":
                    found += check_products(item, compounds, name)
                case "scale":
                    found += check_scale(item, name)
                case "time":
                    found += check_time(name, item)
                case "temperature":
                    found += check_temperature(name, item)
                case "note":
                    found += check_string(name, item)
                case _:
                    found.append(warning(name, "unknown field"))
    return found


def product_keys(products: object) -> list[str]:
    """Return the compound keys ``products`` names, in order.

    Only entries that are tables with a string ``compound`` count; any
    other value of ``products`` names none.
    """
    if not isinstance(products, list):
        return []
    return [entry["compound"] for entry in products
            if isinstance(entry, dict)
            and isinstance(entry.get("compound"), str)]


def repeated(keys: Iterable[str]) -> list[str]:
    """Return each entry of ``keys`` that occurs more than once, once,
    in the order of its second occurrence."""
    seen: set[str] = set()
    found: list[str] = []
    for key in keys:
        if key in seen and key not in found:
            found.append(key)
        seen.add(key)
    return found


def check_structure_image(value: object, static_dir: Path,
                          name: str = "structure_image") -> list[Problem]:
    """Check the image path ``value``'s form, then that the file exists
    under ``static_dir``.

    Problems are reported under ``name``. The existence check runs only
    when the path has an allowed prefix and suffix.
    """
    if not isinstance(value, str):
        return [error(name, "must be a string")]
    parts = value.split("/")
    if (not value.startswith("structures/") or ".." in parts
            or "\\" in value or len(parts) < 2 or not parts[-1]):
        return [error(name, f'"{value}" must be a relative path under '
                      'structures/, e.g. "structures/ethyl-acetate.svg"')]
    if not value.endswith((".svg", ".png")):
        return [error(name, f'"{value}" must end in .svg or .png')]
    if not (static_dir / value).is_file():
        return [error(name, f'"{value}" not found under the static '
                      f"directory {static_dir}")]
    return []


def check_language(value: object) -> list[Problem]:
    """Check that ``language`` is one of the procedure languages."""
    if value not in LANGUAGES:
        return [error("language", f"{value!r} must be one of "
                      f"{', '.join(LANGUAGES)}")]
    return []


def check_language_agrees(name: str, value: object) -> list[Problem]:
    """Check that ``language`` names the language code of file ``name``.

    Nothing is reported when either is missing or ``language`` is
    invalid.
    """
    code = language_of(name)
    if code is None or value not in LANGUAGES or value == code:
        return []
    return [error("language", f'"{value}" does not match the language code '
                  f'".{code}" of the file name')]


def check_ai_model(value: object) -> list[Problem]:
    """Check that ``ai_model`` is a model name and not ``none``."""
    found = check_string("ai_model", value)
    if not found and str(value).strip().lower() == "none":
        return [error("ai_model", "omit ai_model when no AI was involved "
                      'instead of writing "none"')]
    return found


def check_extra_key(key: str, value: object) -> list[Problem]:
    """Check a key outside the schema: tolerated, rejected or unknown."""
    if key == "draft":
        if value is False:
            return []
        return [error("draft", "use status, not draft; draft must be "
                      "false or absent")]
    if key == "description":
        return [] if isinstance(value, str) else [
            error(key, "must be a string")]
    if key == "aliases":
        return [] if is_string_list(value) else [
            error(key, "must be a list of strings")]
    if key == "weight":
        return [] if isinstance(value, int) and not isinstance(
            value, bool) else [error(key, "must be an integer")]
    if key == "author":
        return [error(key, "use authors, a list of names")]
    if key == "url":
        return [error(key, "remove url; the URL is derived from slug")]
    return [warning(key, "unknown field")]


REQUIRED_KEYS = ("id", "slug", "title", "date", "lastmod", "authors",
                 "status", "reaction_types", "tags", "products", "scale",
                 "hazards")
OPTIONAL_KEYS = ("substrates", "scope", "scheme_image", "checked_by",
                 "references", "ai_model", "language")
# The top-level keys that a general procedure, one with ``scope``, lists
# in its entries instead.
ENTRY_KEYS = ("products", "substrates")


def check_fields(data: dict[str, Any], ctx: Context) -> list[Problem]:
    """Check every front-matter key of one content file on its own.

    Covers required and optional fields, the ``lastmod >= date``
    ordering, and keys outside the schema. A procedure with ``scope``
    needs no ``products``, and its top-level ``products`` or
    ``substrates`` are errors. Checks that need other files or the file
    name are not included.
    """
    found: list[Problem] = []
    general = "scope" in data
    if general:
        found += [error(key, "a general procedure lists them in scope; "
                        f"move {key} into its entries")
                  for key in ENTRY_KEYS if key in data]
    for key in REQUIRED_KEYS:
        if general and key in ENTRY_KEYS:
            continue
        if key not in data:
            found.append(error(key, "required field missing"))
            continue
        value = data[key]
        match key:
            case "id":
                found += check_id(value)
            case "slug":
                found += check_slug(value, data.get("id"))
            case "title":
                found += check_string(key, value)
            case "date":
                found += check_datetime(key, value, ctx.zone)
            case "lastmod":
                found += check_lastmod(value, data.get("date"), ctx.zone)
            case "authors" | "hazards":
                found += check_string_list(key, value, non_empty=True)
            case "status":
                found += check_status(value)
            case "reaction_types":
                found += check_reaction_types(value, ctx.vocabulary)
            case "tags":
                found += check_tags(value)
            case "products":
                found += check_products(value, ctx.compounds)
            case "scale":
                found += check_scale(value)
    for key in OPTIONAL_KEYS:
        if key not in data or general and key in ENTRY_KEYS:
            continue
        value = data[key]
        match key:
            case "substrates":
                found += check_substrates(value, data.get("products"),
                                          ctx.compounds)
            case "scope":
                found += check_scope(value, ctx.compounds)
            case "scheme_image":
                found += check_structure_image(value, ctx.static_dir, key)
            case "checked_by" | "references":
                found += check_string_list(key, value, non_empty=False)
            case "ai_model":
                found += check_ai_model(value)
            case "language":
                found += check_language(value)
    for key, value in data.items():
        if key not in REQUIRED_KEYS and key not in OPTIONAL_KEYS:
            found += check_extra_key(key, value)
    return found


def file_name_pattern(suffix: str, prefix: str = "OSDB") -> re.Pattern[str]:
    """Return the file-name pattern for ``suffix`` and IDs of PREFIX.

    Group 1 is the base name without the language code and suffix,
    group 2 the ID, and group 3 the language code, if any.
    """
    return re.compile(rf"^(({prefix}-\d{{4}})-[a-z0-9]+(?:-[a-z0-9]+)*)"
                      rf"(?:\.([a-z]{{2}}))?{re.escape(suffix)}$")


def language_of(name: str) -> str | None:
    """Return the language code of a content file name, or None.

    That is the two-letter code before the suffix, as in
    ``OSDB-0001-ethyl-acetate.de.md``. The code is not checked against
    ``LANGUAGES``.
    """
    match = re.search(r"\.([a-z]{2})\.(md|org|pdf)$", name)
    return match.group(1) if match else None


def base_name(name: str) -> str:
    """Return ``name`` without its suffix and language code."""
    stem = name.rsplit(".", 1)[0]
    if language_of(name) is not None:
        stem = stem.rsplit(".", 1)[0]
    return stem


def check_file_name(name: str, suffix: str, ident: object,
                    kind: Kind = PROCEDURE) -> list[Problem]:
    """Check the file NAME of a file of KIND, and its prefix against
    the ID IDENT.

    The agreement check runs only when IDENT is a valid ID of KIND; pass
    None to skip it.
    """
    match = file_name_pattern(suffix, kind.prefix).match(name)
    if match is None:
        example = f"{kind.prefix}-0001-{kind.example}"
        return [error("file_name", f"must be named {kind.prefix}-NNNN-"
                      f"short-slug{suffix}, e.g. {example}{suffix}, or "
                      f"{example}.de{suffix} with a language")]
    code = match.group(3)
    if code is not None and code not in LANGUAGES:
        return [error("file_name", f'unknown language code ".{code}"; '
                      f"use {' or '.join(LANGUAGES)}, or none")]
    if is_valid_id(ident, kind.prefix) and match.group(2) != ident:
        return [error("file_name", f"file name prefix {match.group(2)} "
                      f"does not match id {ident}")]
    return []


# --------------------------------------------------------------------------
# Body sections

HEADING_RE = re.compile(r"^##[ \t]+(.+)$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def section_headings(body: str) -> list[str]:
    """Return the normalised text of each level-2 ATX heading in ``body``.

    Headings inside fenced code blocks are skipped. A trailing ``{...}``
    attribute block and closing ``#`` sequence are removed, and runs of
    whitespace collapse to one space.
    """
    found: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        opening = FENCE_RE.match(line)
        if fence is not None:
            if opening and opening.group(1)[0] == fence[0] and len(
                    opening.group(1)) >= len(fence) and not line.strip(
                    ).lstrip(fence[0]):
                fence = None
            continue
        if opening:
            fence = opening.group(1)
            continue
        match = HEADING_RE.match(line)
        if match is None:
            continue
        text = re.sub(r"\s*\{[^{}]*\}\s*$", "", match.group(1))
        text = re.sub(r"(^|\s+)#+\s*$", "", text)
        text = " ".join(text.split())
        if text:
            found.append(text)
    return found


def check_body(body: str, language: str | None = DEFAULT_LANGUAGE
               ) -> list[Problem]:
    """Check that ``body`` has the eight sections in canonical order.

    The section names are those of ``language``; with None, those of the
    language that gives the fewest problems. Each missing section is a
    warning, and any canonical section out of order gives one further
    warning.
    """
    if language is None:
        return min((check_body(body, lang) for lang in LANGUAGES), key=len)
    sections = SECTIONS_BY_LANGUAGE.get(language, SECTIONS)
    folded = [h.casefold() for h in section_headings(body)]
    found: list[Problem] = []
    order: list[int] = []
    for index, name in enumerate(sections):
        if name.casefold() in folded:
            order.append(index)
        else:
            found.append(warning("body", f'missing section "{name}"'))
    order.sort(key=lambda i: folded.index(sections[i].casefold()))
    if order != sorted(order):
        found.append(warning("body", "sections out of order; expected "
                             f"{', '.join(sections)}"))
    return found


# --------------------------------------------------------------------------
# Cross-file checks


@dataclass
class ContentFile:
    """A content file examined in this run."""

    path: str
    name: str
    data: dict[str, Any] | None = None
    problems: list[Problem] = field(default_factory=list)

    @property
    def language(self) -> str | None:
        """The language code of the file name, or None."""
        return language_of(self.name)


def without_notes(scope: object) -> object:
    """Return ``scope`` with the ``note`` of each table entry left out.

    Any other value, and any entry that is not a table, is returned as
    it is.
    """
    if not isinstance(scope, list):
        return scope
    return [{k: v for k, v in entry.items() if k != "note"}
            if isinstance(entry, dict) else entry for entry in scope]


def same_value(mine: object, theirs: object) -> bool:
    """Whether two shared-field values agree.

    Numbers compare by value, so that ``85`` and ``85.0`` match; lists
    compare entry by entry in order, and tables key by key, by the same
    rule; anything else compares by value and type.
    """
    if is_number(mine) and is_number(theirs):
        return mine == theirs
    if isinstance(mine, list) and isinstance(theirs, list):
        return len(mine) == len(theirs) and all(
            same_value(a, b) for a, b in zip(mine, theirs))
    if isinstance(mine, dict) and isinstance(theirs, dict):
        return mine.keys() == theirs.keys() and all(
            same_value(mine[key], theirs[key]) for key in mine)
    return mine == theirs and type(mine) is type(theirs)


def reference_variant(holders: Sequence[ContentFile]) -> ContentFile:
    """The variant the others of one ID are compared with: the file
    without a language code, else the first in ``LANGUAGES`` order, and
    a file with an unknown code last."""
    def rank(item: ContentFile) -> tuple[int, str]:
        lang = item.language
        if lang is None:
            return (-1, item.path)
        known = LANGUAGES.index(lang) if lang in LANGUAGES else None
        return (len(LANGUAGES) if known is None else known, item.path)
    return min(holders, key=rank)


def check_variants(holders: Sequence[ContentFile],
                   kind: Kind = PROCEDURE) -> None:
    """Check the variants of one ID against their reference variant.

    HOLDERS are the parsed files of KIND sharing one ID, at most one per
    language code (or none). Each must have the reference's base name
    and the same value, or absence, of every key of ``kind.shared``,
    ``scope`` compared without the entries' notes.
    """
    original = reference_variant(holders)
    assert original.data is not None
    for item in holders:
        if item is original:
            continue
        assert item.data is not None
        if base_name(item.name) != base_name(original.name):
            item.problems.append(error(
                "file_name", f"a variant must be named after "
                f"{original.path}: {base_name(original.name)}."
                f"{item.language}{Path(item.name).suffix}"))
        for name in kind.shared:
            mine = item.data.get(name)
            theirs = original.data.get(name)
            if name == "scope":
                mine, theirs = without_notes(mine), without_notes(theirs)
            if not same_value(mine, theirs):
                shown = "unset" if theirs is None else repr(theirs)
                item.problems.append(error(
                    name, f"must equal the value in {original.path} "
                    f"({shown}); the variants of a {kind.noun} share it"))


def group_by_id(files: Iterable[ContentFile],
                prefix: str = "OSDB") -> dict[str, list[ContentFile]]:
    """Group the parsed FILES by their ``id``, a valid ID of PREFIX.

    Files whose front matter did not parse, or whose ``id`` is not
    valid, are left out. Each group keeps the order of FILES.
    """
    by_id: dict[str, list[ContentFile]] = {}
    for item in files:
        if item.data is not None and is_valid_id(item.data.get("id"),
                                                 prefix):
            by_id.setdefault(item.data["id"], []).append(item)
    return by_id


def check_cross_file(files: Sequence[ContentFile],
                     kind: Kind = PROCEDURE) -> list[ContentFile]:
    """Add duplicate-ID and variant problems to FILES, of KIND.

    An ID may be used once per language code, and once without one; the
    files of one ID are variants, checked by ``check_variants``.
    Files whose front matter did not parse contribute no ID and are not
    checked.

    Return the files that stand for themselves: every file except the
    variants compared with a reference variant, in the order of FILES.
    """
    compared: list[ContentFile] = []
    for ident, holders in group_by_id(files, kind.prefix).items():
        by_language: dict[str | None, list[ContentFile]] = {}
        for item in holders:
            by_language.setdefault(item.language, []).append(item)
        duplicated = False
        for same in by_language.values():
            if len(same) < 2:
                continue
            duplicated = True
            for item in same:
                others = ", ".join(o.path for o in same if o is not item)
                item.problems.append(error(
                    "id", f"duplicate id {ident}, also used by {others}"))
        if not duplicated and len(holders) > 1:
            check_variants(holders, kind)
            original = reference_variant(holders)
            compared += [item for item in holders if item is not original]
    return [item for item in files
            if not any(item is other for other in compared)]


# --------------------------------------------------------------------------
# Compound registry

COMPOUND_REQUIRED_KEYS = ("name", "formula", "mw", "smiles")
COMPOUND_OPTIONAL_KEYS = ("name_de", "cas", "structure_image")


def check_mw(value: object) -> list[Problem]:
    """Check that ``mw`` is a finite number greater than 0."""
    if not is_number(value):
        return [error("mw", "must be a number in g/mol, unquoted, "
                      "e.g. 88.11")]
    if not math.isfinite(value) or value <= 0:
        return [error("mw", "must be greater than 0")]
    return []


def check_cas(value: object) -> list[Problem]:
    """Check that ``cas`` has the CAS form and a valid check digit."""
    if not isinstance(value, str) or not CAS_RE.match(value):
        return [error("cas", f"{value!r} must have the form NNNNNNN-NN-N, "
                      'e.g. "64-17-5"')]
    if not cas_check_digit_ok(value):
        return [error("cas", f'"{value}" has a wrong check digit; check '
                      "the number")]
    return []


class Term(NamedTuple):
    """One value of a collection vocabulary.

    ``label`` is the value's name on an English site and ``label_de``
    its name on a German site, or None when the vocabulary gives none.
    ``parent`` is the value it is filed under, or None for a top-level
    value.
    """

    label: str
    label_de: str | None
    parent: str | None


class Declaration(NamedTuple):
    """A compound field that a collection declares, its defaults applied.

    ``type`` is one of FIELD_TYPES. An option the type does not take
    holds None, or False for a boolean option: ``pattern`` and
    ``unique`` belong to a text field, ``minimum``, ``maximum``,
    ``unit`` and ``unique`` to a number field, and ``vocabulary``,
    ``multiple`` and ``terms`` to a choice field. ``pattern`` is
    compiled; ``terms`` maps every value of the field's vocabulary, in
    file order, to its entry.
    """

    key: str
    type: str
    label: str
    label_de: str | None
    required: bool
    column: bool
    unique: bool
    pattern: re.Pattern[str] | None
    minimum: int | float | None
    maximum: int | float | None
    unit: str | None
    vocabulary: str | None
    multiple: bool
    terms: dict[str, Term]


def check_choice(field: Declaration, value: object) -> list[Problem]:
    """Check VALUE of the choice FIELD against the field's vocabulary.

    A field declared ``multiple`` takes a non-empty list of strings,
    any other a string. Each distinct string outside the vocabulary
    draws one ``unknown value`` error, in list order, and each value
    the list repeats one ``repeats`` error.
    """
    name = field.key
    source = f"vocabularies/{field.vocabulary}.toml"

    def unknown(entry: str) -> Problem:
        return error(name, f'unknown value "{entry}"; see {source} for '
                     "the allowed values")

    if not field.multiple:
        if not isinstance(value, str):
            return [error(name, "must be a string")]
        return [] if value in field.terms else [unknown(value)]
    if not is_string_list(value):
        return [error(name, "must be a list of strings, e.g. "
                      f'["{next(iter(field.terms))}"]')]
    if not value:
        return [error(name, "must not be empty")]
    found = [unknown(entry) for entry in dict.fromkeys(value)
             if entry not in field.terms]
    return found + [error(name, f'repeats "{entry}"')
                    for entry in repeated(value)]


def check_field_value(field: Declaration, value: object) -> list[Problem]:
    """Check VALUE, set by a compound file, against the declared FIELD.

    Problems are reported under the field's key. A value of the wrong
    type draws that one error and no other.
    """
    name = field.key
    match field.type:
        case "text":
            found = check_string(name, value)
            if (not found and field.pattern is not None
                    and not field.pattern.fullmatch(value)):
                found.append(error(name, "must match the pattern "
                                   f"{field.pattern.pattern}"))
            return found
        case "number":
            if not is_number(value) or not math.isfinite(value):
                return [error(name, "must be a number, unquoted")]
            if field.minimum is not None and value < field.minimum:
                return [error(name, f"must be at least {field.minimum}")]
            if field.maximum is not None and value > field.maximum:
                return [error(name, f"must be at most {field.maximum}")]
            return []
        case "boolean":
            if not isinstance(value, bool):
                return [error(name, "must be true or false, unquoted")]
            return []
        case _:
            return check_choice(field, value)


def check_declared(data: dict[str, Any],
                   fields: Iterable[Declaration]) -> list[Problem]:
    """Check the values that the parsed compound file DATA sets for the
    declared FIELDS; a missing value is an error only for a field
    declared ``required``."""
    found: list[Problem] = []
    for field in fields:
        if field.key in data:
            found += check_field_value(field, data[field.key])
        elif field.required:
            found.append(error(field.key, "required field missing"))
    return found


def check_unique(fields: Iterable[Declaration],
                 parsed: Sequence[tuple[str, str, dict[str, Any]]]
                 ) -> list[tuple[str, Problem]]:
    """Compare the values of the FIELDS declared ``unique`` across the
    compound files PARSED, each given as its path, its key and its
    table.

    Only a value that passes the checks of its field is compared. Each
    file that sets a value some other file also sets gets an error,
    with its path, that names the keys of the other compounds.
    """
    problems: list[tuple[str, Problem]] = []
    for field in fields:
        if not field.unique:
            continue
        holders: dict[object, list[tuple[str, str]]] = {}
        for path, key, data in parsed:
            if (field.key in data
                    and not check_field_value(field, data[field.key])):
                holders.setdefault(data[field.key], []).append((path, key))
        for value, owners in holders.items():
            shown = f'"{value}"' if isinstance(value, str) else str(value)
            for path, key in owners if len(owners) > 1 else ():
                others = ", ".join(k for _, k in owners if k != key)
                problems.append((path, error(
                    field.key, f"{shown} is also set by {others}")))
    return problems


def check_compound(data: dict[str, Any], static_dir: Path,
                   fields: Sequence[Declaration] = ()) -> list[Problem]:
    """Check the keys of one parsed compound file.

    Problems are reported under the key's name. ``structure_image`` is
    resolved against ``static_dir``. The keys of the declared FIELDS are
    checked against their declarations; any other key outside the
    compound schema is a warning.
    """
    found: list[Problem] = []
    for key in COMPOUND_REQUIRED_KEYS:
        if key not in data:
            found.append(error(key, "required field missing"))
        elif key == "mw":
            found += check_mw(data[key])
        else:
            found += check_string(key, data[key])
    for key in COMPOUND_OPTIONAL_KEYS:
        if key not in data:
            continue
        match key:
            case "name_de":
                found += check_string(key, data[key])
            case "cas":
                found += check_cas(data[key])
            case "structure_image":
                found += check_structure_image(data[key], static_dir)
    found += check_declared(data, fields)
    declared = {field.key for field in fields}
    for key in data:
        if (key not in COMPOUND_REQUIRED_KEYS + COMPOUND_OPTIONAL_KEYS
                and key not in declared):
            found.append(warning(key, "unknown field"))
    return found


def read_compound(path: str) -> dict[str, Any] | Problem:
    """Read and parse the compound file ``path`` as UTF-8 TOML.

    Returns the parsed table, or a ``toml`` error when the file cannot
    be read, is not UTF-8 or is not valid TOML.
    """
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return tomllib.loads(handle.read())
    except UnicodeDecodeError:
        return error("toml", "file is not valid UTF-8")
    except OSError as exc:
        return error("toml", f"cannot read file: {exc.strerror}")
    except tomllib.TOMLDecodeError as exc:
        return error("toml", f"invalid TOML: {exc}")


class Registry(NamedTuple):
    """The outcome of examining a compound registry."""

    compounds: frozenset[str]
    problems: list[tuple[str, Problem]]
    files: int


def examine_registry(registry: str, static_dir: Path,
                     fields: Sequence[Declaration] = ()) -> Registry:
    """Check every compound file of the directory ``registry``.

    Each file is checked against the compound schema and the declared
    FIELDS, and the values of the fields declared ``unique`` are
    compared across the files. Returns the keys of the compounds the
    registry defines, the problems found, each with the path
    ``registry`` joined with the entry name, and the number of compound
    files examined. A file whose name begins with ``.`` is skipped; a
    subdirectory, or any other file not named ``<key>.toml``, is a
    ``file_name`` error and defines no compound, and so does a file that
    does not parse. A ``registry`` that does not exist defines no
    compound and draws no problem.
    """
    if not os.path.isdir(registry):
        return Registry(frozenset(), [], 0)
    parsed: list[tuple[str, str, dict[str, Any]]] = []
    problems: list[tuple[str, Problem]] = []
    files = 0
    for name in sorted(os.listdir(registry)):
        path = os.path.join(registry, name)
        match = COMPOUND_FILE_RE.match(name)
        if os.path.isdir(path):
            problems.append((path, error(
                "file_name", "subdirectories are not supported; move "
                "its files to the top level")))
        elif name.startswith("."):
            continue
        elif match is None:
            problems.append((path, error(
                "file_name", "must be named <key>.toml, the key lowercase "
                "and hyphenated, e.g. ethyl-acetate.toml")))
        else:
            files += 1
            data = read_compound(path)
            if isinstance(data, Problem):
                problems.append((path, data))
                continue
            parsed.append((path, match.group(1), data))
            problems += [(path, p)
                         for p in check_compound(data, static_dir, fields)]
    problems += check_unique(fields, parsed)
    return Registry(frozenset(key for _, key, _ in parsed), problems, files)


# --------------------------------------------------------------------------
# Synthesis sequences

SEQUENCE_KEYS = ("id", "slug", "title", "date", "lastmod", "target",
                 "steps")
# Hugo would file a sequence carrying one of these under the procedures'
# taxonomies, beside the procedures.
TAXONOMY_KEYS = ("authors", "tags", "reaction_types")
STEP_KEYS = ("procedure", "entry")


class Run(NamedTuple):
    """The compounds of one run of a procedure: of the procedure itself,
    or of one entry of a general procedure."""

    substrates: list[str]
    products: list[str]


def entry_count(data: dict[str, Any]) -> int:
    """Return the number of scope entries of the procedure front matter
    DATA, 0 when its ``scope`` is not an array."""
    scope = data.get("scope")
    return len(scope) if isinstance(scope, list) else 0


def is_entry_number(value: object, count: int) -> bool:
    """Whether VALUE is an integer from 1 to COUNT."""
    return (isinstance(value, int) and not isinstance(value, bool)
            and 1 <= value <= count)


def step_run(step: object,
             procedures: dict[str, dict[str, Any]]) -> Run | None:
    """Return the run that the sequence step STEP names, or None.

    PROCEDURES maps each procedure ID of the content roots to its front
    matter. The run is that of the step's entry for a general procedure,
    one with ``scope``, and that of the procedure otherwise. None means
    the step names no run: it is not a table, its procedure is not
    found, or its entry is missing, out of range or refused.
    """
    if not isinstance(step, dict) or not isinstance(step.get("procedure"),
                                                    str):
        return None
    data = procedures.get(step["procedure"])
    if data is None:
        return None
    source: object = data
    if "scope" in data:
        if not is_entry_number(step.get("entry"), entry_count(data)):
            return None
        source = data["scope"][step["entry"] - 1]
    elif "entry" in step:
        return None
    if not isinstance(source, dict):
        return None
    substrates = source.get("substrates")
    return Run(substrates if is_string_list(substrates) else [],
               product_keys(source.get("products")))


def check_step(prefix: str, step: object,
               procedures: dict[str, dict[str, Any]]) -> list[Problem]:
    """Check one sequence step, reporting under PREFIX, ``steps[n]``.

    STEP must be a table whose ``procedure`` is a key of PROCEDURES,
    which maps procedure IDs to front matter. ``entry`` is required for a
    general procedure and must count one of its scope entries from 1; a
    specific procedure refuses it. Other keys are warnings.
    """
    if not isinstance(step, dict):
        return [error(prefix, 'must be a table, e.g. '
                      '{ procedure = "OSDB-0001" }')]
    found: list[Problem] = []
    name = f"{prefix}.procedure"
    ident = step.get("procedure")
    data = None
    if "procedure" not in step:
        found.append(error(name, "required field missing"))
    elif not isinstance(ident, str):
        found.append(error(name, 'must be a string, e.g. "OSDB-0001"'))
    elif ident not in procedures:
        found.append(error(name, f"{ident} not found in any content root"))
    else:
        data = procedures[ident]
    if data is not None:
        name = f"{prefix}.entry"
        count = entry_count(data)
        if "scope" not in data:
            if "entry" in step:
                found.append(error(name, f"{ident} has no scope entries; "
                                   "remove entry"))
        elif "entry" not in step:
            found.append(error(name, f"{ident} is a general procedure; "
                               f"name one of its entries 1 to {count}"))
        elif not is_entry_number(step["entry"], count):
            found.append(error(name, f"must be between 1 and {count}, "
                               "the number of an entry of "
                               f"{ident}'s scope"))
    found += [warning(f"{prefix}.{key}", "unknown field")
              for key in step if key not in STEP_KEYS]
    return found


def check_steps(value: object,
                procedures: dict[str, dict[str, Any]]) -> list[Problem]:
    """Check ``steps``, an array of at least two step tables.

    A problem in the n-th step, counting from 1, is reported under
    ``steps[n]`` or ``steps[n].<key>`` (``check_step``); PROCEDURES maps
    procedure IDs to front matter.
    """
    if not isinstance(value, list):
        return [error("steps", "must be an array of tables, e.g. "
                      '[{ procedure = "OSDB-0001" }, '
                      '{ procedure = "OSDB-0002" }]')]
    found: list[Problem] = []
    if len(value) < 2:
        found.append(error("steps", "must list at least two steps"))
    for number, step in enumerate(value, start=1):
        found += check_step(f"steps[{number}]", step, procedures)
    return found


def check_sequence_fields(data: dict[str, Any], ctx: Context,
                          procedures: dict[str, dict[str, Any]]
                          ) -> list[Problem]:
    """Check every front-matter key of one sequence on its own.

    DATA is the sequence's front matter; its ``target`` resolves against
    the registry keys of CTX and its steps against PROCEDURES, which maps
    procedure IDs to front matter. A missing key is an error and a key
    outside the sequence schema a warning, except a procedure taxonomy
    key (``TAXONOMY_KEYS``), which is an error. Continuity is not checked.
    """
    found: list[Problem] = []
    for key in SEQUENCE_KEYS:
        if key not in data:
            found.append(error(key, "required field missing"))
            continue
        value = data[key]
        match key:
            case "id":
                found += check_id(value, SEQUENCE.prefix)
            case "slug":
                found += check_slug(value, data.get("id"), SEQUENCE.prefix)
            case "title":
                found += check_string(key, value)
            case "date":
                found += check_datetime(key, value, ctx.zone)
            case "lastmod":
                found += check_lastmod(value, data.get("date"), ctx.zone)
            case "target":
                found += check_string(key, value) or check_compound_key(
                    key, value, ctx.compounds)
            case "steps":
                found += check_steps(value, procedures)
    found += [error(key, "must not be set; a sequence joins no procedure "
                     "taxonomy") if key in TAXONOMY_KEYS
              else warning(key, "unknown field")
              for key in data if key not in SEQUENCE_KEYS]
    return found


def check_continuity(data: dict[str, Any],
                     procedures: dict[str, dict[str, Any]],
                     compounds: frozenset[str]) -> list[Problem]:
    """Check that the steps of the sequence front matter DATA chain.

    Each step after the first must take a product of the step before
    it among its substrates, an error under ``steps[k+1]``, and a
    ``target`` that is a key of the registry COMPOUNDS must be a product
    of the last step. A step that names no run (``step_run``) is left
    out of both checks. Nothing is checked unless ``steps`` holds at
    least two tables.
    """
    steps = data.get("steps")
    if not isinstance(steps, list) or sum(
            isinstance(step, dict) for step in steps) < 2:
        return []
    runs = [step_run(step, procedures) for step in steps]
    found: list[Problem] = []
    for number in range(1, len(runs)):
        before, this = runs[number - 1], runs[number]
        if before is not None and this is not None and not any(
                key in this.substrates for key in before.products):
            found.append(error(
                f"steps[{number + 1}]", "starts from none of the products "
                f"of step {number} ({', '.join(before.products)})"))
    target = data.get("target")
    if isinstance(target, str) and target in compounds \
            and runs[-1] is not None and target not in runs[-1].products:
        found.append(error("target", f"{target} is not a product of the "
                           f"last step, step {len(runs)}"))
    return found


def procedure_index(files: Iterable[ContentFile]
                    ) -> dict[str, dict[str, Any]]:
    """Map each valid procedure ID of FILES to the front matter of its
    reference variant (``reference_variant``)."""
    return {ident: reference_variant(holders).data
            for ident, holders in group_by_id(files).items()}


def examine_sequence(entry: Entry, ctx: Context,
                     procedures: dict[str, dict[str, Any]]) -> ContentFile:
    """Read and check one sequence file on its own.

    The steps resolve against PROCEDURES, which maps procedure IDs to
    front matter; continuity is checked separately.
    """
    item = ContentFile(entry.path, entry.name)
    text = read_text(entry.path)
    parsed = parse_front_matter(text) if isinstance(text, str) else text
    if isinstance(parsed, Problem):
        item.problems.append(parsed)
        return item
    item.data = parsed.data
    item.problems += check_file_name(entry.name, ".md",
                                     parsed.data.get("id"), SEQUENCE)
    item.problems += check_sequence_fields(parsed.data, ctx, procedures)
    return item


def examine_sequences(directory: str, ctx: Context,
                      procedures: dict[str, dict[str, Any]]
                      ) -> tuple[list[tuple[str, Problem]], int]:
    """Check every sequence file of DIRECTORY.

    Returns the problems found, each with the path DIRECTORY joined with
    the entry name, and the number of sequence files examined. Steps
    resolve against PROCEDURES, which maps procedure IDs to front
    matter, and targets against the registry keys of CTX. Continuity is
    checked on the reference variant of each sequence only. A DIRECTORY
    that does not exist holds no sequence.
    """
    if not os.path.isdir(directory):
        return [], 0
    problems: list[tuple[str, Problem]] = []
    files: list[ContentFile] = []
    for entry in discover(directory, ".md", SEQUENCE.noun):
        if entry.problem is not None:
            problems.append((entry.path, entry.problem))
        else:
            files.append(examine_sequence(entry, ctx, procedures))
    for item in check_cross_file(files, SEQUENCE):
        if item.data is not None:
            item.problems += check_continuity(item.data, procedures,
                                              ctx.compounds)
    for item in files:
        problems += [(item.path, p) for p in item.problems]
    return problems, len(files)


# --------------------------------------------------------------------------
# I/O: configuration, discovery and reporting


def load_vocabulary(path: Path) -> frozenset[str]:
    """Load the reaction-type vocabulary and return its slugs.

    Raises ConfigError when the file is missing, is not TOML, has a key
    that is not a slug, or has an entry without a non-empty ``label``.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"vocabulary file {path} not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read vocabulary file {path}: "
                          f"{exc}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"vocabulary file {path} is not valid TOML: "
                          f"{exc}") from None
    for key, entry in data.items():
        if not SLUG_RE.match(key):
            raise ConfigError(f"vocabulary file {path}: key {key!r} is "
                              "not a lowercase hyphenated slug")
        label = entry.get("label") if isinstance(entry, dict) else None
        if not isinstance(label, str) or not label.strip():
            raise ConfigError(f"vocabulary file {path}: entry {key!r} "
                              "must be a table with a non-empty label")
        for lang in LANGUAGES:
            name = f"label_{lang}"
            if name in entry and (not isinstance(entry[name], str)
                                  or not entry[name].strip()):
                raise ConfigError(f"vocabulary file {path}: entry "
                                  f"{key!r} has an empty {name}")
    return frozenset(data)


def read_config(path: Path) -> dict[str, Any]:
    """Read and parse the configuration file PATH as UTF-8 TOML.

    Raises ConfigError, its message beginning with PATH, when the file
    does not exist, cannot be read, is not UTF-8 or is not valid TOML.
    """
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{path}: file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path}: cannot read it: {exc}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: not valid TOML: {exc}") from None


def read_settings(path: Path) -> dict[str, Any]:
    """Read the collection settings file PATH and return its table.

    The file must parse as TOML to a table holding ``format``, the
    integer SETTINGS_FORMAT, and no top-level key outside SETTINGS_KEYS.
    Nothing inside ``fields`` is checked. Raises ConfigError, its
    message beginning with PATH, when the file breaks any of this or
    cannot be read as UTF-8 TOML.
    """
    data = read_config(path)
    unknown = sorted(set(data) - set(SETTINGS_KEYS))
    if unknown:
        raise ConfigError(f"{path}: unknown key {', '.join(unknown)}; only "
                          f"{' and '.join(SETTINGS_KEYS)} are allowed")
    value = data.get("format")
    if type(value) is not int or value != SETTINGS_FORMAT:
        shown = "missing" if value is None else repr(value)
        raise ConfigError(f"{path}: format is {shown}; this OrgSynDB reads "
                          f"format = {SETTINGS_FORMAT}")
    return data


def load_terms(path: Path) -> dict[str, Term]:
    """Load the collection vocabulary PATH and return its values, in file
    order, each with its entry.

    Raises ConfigError, its message beginning with PATH, when the file
    cannot be read as UTF-8 TOML, holds no value, or breaks a rule of a
    vocabulary: every value a lowercase hyphenated slug whose entry is a
    table with a non-empty string ``label``, an optional non-empty
    string ``label_de`` and an optional ``parent`` that is another value
    of the file, no other key, and no value its own ancestor.
    """
    data = read_config(path)
    if not data:
        raise ConfigError(f"{path}: the vocabulary has no value")
    terms: dict[str, Term] = {}
    for value, entry in data.items():
        where = f"{path}: value {value!r}"
        if not SLUG_RE.match(value):
            raise ConfigError(f"{where} is not a lowercase hyphenated "
                              "slug")
        label = entry.get("label") if isinstance(entry, dict) else None
        if not isinstance(label, str) or not label.strip():
            raise ConfigError(f"{where} must be a table with a non-empty "
                              "label")
        unknown = sorted(set(entry) - set(TERM_KEYS))
        if unknown:
            raise ConfigError(f"{where} holds the unknown key "
                              f"{', '.join(unknown)}; only "
                              f"{', '.join(TERM_KEYS)} are allowed")
        label_de = entry.get("label_de")
        if "label_de" in entry and (not isinstance(label_de, str)
                                    or not label_de.strip()):
            raise ConfigError(f"{where}: label_de must be a non-empty "
                              "string")
        parent = entry.get("parent")
        if "parent" in entry and (not isinstance(parent, str)
                                  or parent not in data):
            raise ConfigError(f"{where}: parent {parent!r} is not a value "
                              "of this vocabulary")
        terms[value] = Term(label, label_de, parent)
    for value in terms:
        current = terms[value].parent
        for _ in terms:
            if current is None:
                break
            if current == value:
                raise ConfigError(f"{path}: value {value!r} is its own "
                                  "ancestor; its parent entries form a "
                                  "loop")
            current = terms[current].parent
    return terms


def declared_string(entry: dict[str, Any], option: str, where: str,
                    required: bool = False) -> str | None:
    """Return the non-empty string that the declaration ENTRY sets for
    OPTION, or None when it sets none and REQUIRED is false.

    Raises ConfigError, its message beginning with WHERE, when the value
    is missing but REQUIRED, or is not a non-empty string.
    """
    if option not in entry:
        if required:
            raise ConfigError(f"{where}: {option} missing")
        return None
    value = entry[option]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where}: {option} must be a non-empty string")
    return value


def declared_flag(entry: dict[str, Any], option: str, where: str) -> bool:
    """Return the boolean that the declaration ENTRY sets for OPTION,
    False when it sets none; raise ConfigError, its message beginning
    with WHERE, when the value is not a boolean."""
    value = entry.get(option, False)
    if not isinstance(value, bool):
        raise ConfigError(f"{where}: {option} must be true or false, "
                          "unquoted")
    return value


def declared_bound(entry: dict[str, Any], option: str,
                   where: str) -> int | float | None:
    """Return the finite number that the declaration ENTRY sets for
    OPTION, None when it sets none; raise ConfigError, its message
    beginning with WHERE, when the value is not a finite number."""
    value = entry.get(option)
    if value is not None and (not is_number(value)
                              or not math.isfinite(value)):
        raise ConfigError(f"{where}: {option} must be a finite number, "
                          "unquoted")
    return value


def read_declaration(entry: dict[str, Any], number: int, settings: Path,
                     taken: Iterable[str],
                     vocabularies: dict[str, dict[str, Term]]
                     ) -> Declaration:
    """Check the declaration ENTRY, the NUMBERth table of
    ``fields.compound`` in the settings file SETTINGS, and return it.

    TAKEN holds the keys of the declarations before it. A vocabulary
    the declaration names is read from ``vocabularies/`` beside
    SETTINGS, unless VOCABULARIES, a cache from vocabulary name to its
    values that this call extends, already holds it. Raises ConfigError
    when the declaration breaks a rule of a field declaration or its
    vocabulary breaks one of a vocabulary; the message names SETTINGS or
    the vocabulary file, the field's key once it is valid, and the
    offending key or value.
    """
    where = f"{settings}: declaration {number} of fields.compound"
    if "key" not in entry:
        raise ConfigError(f"{where}: key missing")
    key = entry["key"]
    if not isinstance(key, str) or not FIELD_KEY_RE.match(key):
        raise ConfigError(f"{where}: key {key!r} must be lowercase letters "
                          "and digits, words joined by single underscores, "
                          "starting with a letter, e.g. item_number")
    if key in COMPOUND_REQUIRED_KEYS + COMPOUND_OPTIONAL_KEYS:
        raise ConfigError(f"{where}: key {key!r} is a built-in compound "
                          "key")
    if key.endswith("_de"):
        raise ConfigError(f"{where}: key {key!r} ends in _de, which is "
                          "reserved")
    if key in taken:
        raise ConfigError(f"{where}: key {key!r} is declared twice")
    where = f"{settings}: field {key}"
    if "type" not in entry:
        raise ConfigError(f"{where}: type missing; it is one of "
                          f"{', '.join(FIELD_TYPES)}")
    kind = entry["type"]
    if kind not in FIELD_TYPES:
        raise ConfigError(f"{where}: type {kind!r} is not one of "
                          f"{', '.join(FIELD_TYPES)}")
    for option in entry:
        if option in FIELD_OPTIONS + TYPE_OPTIONS[kind]:
            continue
        if any(option in options for options in TYPE_OPTIONS.values()):
            raise ConfigError(f"{where}: a {kind} field does not take "
                              f"{option}")
        raise ConfigError(f"{where}: unknown key {option}")
    pattern = entry.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise ConfigError(f"{where}: pattern must be a string")
        try:
            pattern = re.compile(pattern)
        except (re.error, OverflowError, RecursionError) as exc:
            raise ConfigError(f"{where}: pattern {entry['pattern'][:60]!r} "
                              "is not a valid Python regular expression: "
                              f"{exc}") from None
    minimum = declared_bound(entry, "min", where)
    maximum = declared_bound(entry, "max", where)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ConfigError(f"{where}: min {minimum} is greater than max "
                          f"{maximum}")
    name = entry.get("vocabulary")
    terms: dict[str, Term] = {}
    if kind == "choice":
        if name is None:
            raise ConfigError(f"{where}: vocabulary missing; a choice "
                              "field names a file vocabularies/<name>.toml")
        if not isinstance(name, str) or not SLUG_RE.match(name):
            raise ConfigError(f"{where}: vocabulary {name!r} must be the "
                              "lowercase hyphenated name of a file "
                              "vocabularies/<name>.toml, without .toml")
        if name not in vocabularies:
            path = settings.parent / "vocabularies" / f"{name}.toml"
            if not path.is_file():
                raise ConfigError(f"{where}: vocabulary file {path} not "
                                  "found")
            vocabularies[name] = load_terms(path)
        terms = vocabularies[name]
    return Declaration(
        key=key, type=kind,
        label=declared_string(entry, "label", where, required=True),
        label_de=declared_string(entry, "label_de", where),
        required=declared_flag(entry, "required", where),
        column=declared_flag(entry, "column", where),
        unique=declared_flag(entry, "unique", where), pattern=pattern,
        minimum=minimum, maximum=maximum,
        unit=declared_string(entry, "unit", where), vocabulary=name,
        multiple=declared_flag(entry, "multiple", where), terms=terms)


def load_fields(path: Path,
                must_exist: bool = True) -> tuple[Declaration, ...]:
    """Load the compound fields that the collection settings file PATH
    declares, in declared order.

    A settings file without ``fields`` declares no field, and so does a
    PATH that does not exist when MUST_EXIST is false. Vocabularies
    resolve against ``vocabularies/`` beside PATH, and only those a
    declaration names are read. Raises ConfigError when PATH is missing
    though MUST_EXIST, when it breaks a rule of read_settings, or when
    ``fields`` is not a table whose only key, ``compound``, holds an
    array of tables that read_declaration accepts.
    """
    if not must_exist and not path.exists():
        return ()
    fields = read_settings(path).get("fields", {})
    if not isinstance(fields, dict):
        raise ConfigError(f"{path}: fields must be a table holding the "
                          "declarations [[fields.compound]]")
    unknown = sorted(set(fields) - {"compound"})
    if unknown:
        raise ConfigError(f"{path}: unknown key "
                          f"{', '.join(f'fields.{k}' for k in unknown)}; "
                          "only fields.compound is allowed")
    entries = fields.get("compound", [])
    if not isinstance(entries, list) or not all(
            isinstance(entry, dict) for entry in entries):
        raise ConfigError(f"{path}: fields.compound must be an array of "
                          "tables, each written [[fields.compound]]")
    declared: list[Declaration] = []
    vocabularies: dict[str, dict[str, Term]] = {}
    for number, entry in enumerate(entries, start=1):
        declared.append(read_declaration(
            entry, number, path, [d.key for d in declared], vocabularies))
    return tuple(declared)


def load_zone() -> dt.tzinfo:
    """Return the Europe/Berlin zone, or raise ConfigError."""
    try:
        return zoneinfo.ZoneInfo(ZONE_NAME)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
        raise ConfigError(f"time zone {ZONE_NAME} is not available; "
                          "install the tz database (tzdata)") from None


class Entry(NamedTuple):
    """A top-level entry of a root, classified."""

    path: str
    name: str
    problem: Problem | None


def discover(root: str, suffix: str,
             noun: str = PROCEDURE.noun) -> list[Entry]:
    """List the top-level content files of ROOT, sorted by name.

    Dotfiles and ``_index.md`` are omitted. A subdirectory, an error, or
    a file without SUFFIX, a warning that calls it not a NOUN file, is
    returned with the problem it raises instead of as a content file.
    """
    found: list[Entry] = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path):
            found.append(Entry(path, name, error(
                "file_name", "subdirectories are not supported; move "
                "its files to the top level")))
        elif name.startswith(".") or name == "_index.md":
            continue
        elif not name.endswith(suffix):
            found.append(Entry(path, name, warning(
                "file_name", f"not a {noun} file; ignored")))
        else:
            found.append(Entry(path, name, None))
    return found


def read_text(path: str) -> str | Problem:
    """Read ``path`` as UTF-8 with an optional BOM.

    Returns the text, or a ``front_matter`` error when it cannot be
    decoded or read.
    """
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read()
    except UnicodeDecodeError:
        return error("front_matter", "file is not valid UTF-8")
    except OSError as exc:
        return error("front_matter", f"cannot read file: {exc.strerror}")


def examine_content(entry: Entry, ctx: Context) -> ContentFile:
    """Read and check one content file on its own."""
    item = ContentFile(entry.path, entry.name)
    text = read_text(entry.path)
    parsed = parse_front_matter(text) if isinstance(text, str) else text
    if isinstance(parsed, Problem):
        item.problems.append(parsed)
        return item
    item.data = parsed.data
    ident = parsed.data.get("id")
    item.problems += check_file_name(entry.name, ".md", ident)
    item.problems += check_fields(parsed.data, ctx)
    lang = parsed.data.get("language")
    item.problems += check_language_agrees(entry.name, lang)
    item.problems += check_body(parsed.body, item.language or (
        lang if lang in LANGUAGES else None))
    return item


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="Validate OrgSynDB procedures, compounds and "
        "synthesis sequences. Prints one "
        "'<path>:<field>: <severity>: <message>' line per problem and "
        "exits 0 (no errors), 1 (errors found) or 2 (usage or "
        "configuration error).")
    parser.add_argument(
        "content_roots", nargs="+", metavar="CONTENT_ROOT",
        help="directory of procedure Markdown files with +++ TOML front "
        "matter, such as an export directory (at least one)")
    parser.add_argument(
        "--vocabulary", type=Path, default=DEFAULT_VOCABULARY,
        metavar="FILE",
        help="reaction-type vocabulary (default: "
        "<app>/site/data/reaction_types.toml)")
    parser.add_argument(
        "--settings", type=Path, default=None, metavar="FILE",
        help="collection settings file, whose field declarations the "
        "compound files are checked against; its vocabularies are read "
        "from vocabularies/ beside it (default: orgsyndb.toml in the "
        "working directory; a missing default file declares no field)")
    parser.add_argument(
        "--static-dir", type=Path, default=DEFAULT_STATIC_DIR,
        metavar="DIR",
        help="directory that structure_image paths are relative to "
        "(default: static in the working directory)")
    parser.add_argument(
        "--compounds", default=str(DEFAULT_COMPOUNDS),
        metavar="DIR",
        help="compound registry, one <key>.toml file per compound "
        "(default: compounds in the working directory; a missing "
        "directory defines no compound)")
    parser.add_argument(
        "--sequences", default=str(DEFAULT_SEQUENCES), metavar="DIR",
        help="directory of synthesis sequences, SEQ-NNNN-short-slug.md "
        "files whose steps name procedures of the content roots "
        "(default: md/sequences in the working directory; a missing "
        "directory holds no sequence)")
    return parser


def report(problems: Iterable[tuple[str, Problem]], files: int) -> int:
    """Print ``problems`` sorted by path and the summary; return status."""
    ordered = sorted(problems, key=lambda p: p[0])
    for path, problem in ordered:
        print(f"{path}:{problem.field}: {problem.severity}: "
              f"{problem.message}")
    errors = sum(p.severity == ERROR for _, p in ordered)
    warnings = len(ordered) - errors
    sys.stdout.flush()
    print(f"validated {files} files: {errors} errors, {warnings} warnings",
          file=sys.stderr)
    return 1 if errors else 0


def run(content_roots: Sequence[str], registry: str, sequences: str,
        ctx: Context) -> int:
    """Validate the compound REGISTRY, the CONTENT_ROOTS and the
    SEQUENCES directory, report, and return the exit status.

    The compound keys of procedures and sequences resolve against the
    compounds the registry defines, which replace those of CTX, and the
    steps of the sequences against the procedures of the content roots.
    """
    examined = examine_registry(registry, ctx.static_dir, ctx.fields)
    ctx = replace(ctx, compounds=examined.compounds)
    problems = list(examined.problems)
    content: list[ContentFile] = []
    for root in content_roots:
        for entry in discover(root, ".md"):
            if entry.problem is not None:
                problems.append((entry.path, entry.problem))
            else:
                content.append(examine_content(entry, ctx))
    check_cross_file(content)
    for item in content:
        problems += [(item.path, p) for p in item.problems]
    found, count = examine_sequences(sequences, ctx,
                                     procedure_index(content))
    return report(problems + found, examined.files + len(content) + count)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validator on ``argv`` (default: ``sys.argv[1:]``).

    Returns 0 when no error was found, 1 when at least one was, and 2 on
    a configuration error. Usage errors exit 2 through argparse.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        for root in args.content_roots:
            if not os.path.isdir(root):
                raise ConfigError(f"{root} is not a directory")
        if (os.path.exists(args.compounds)
                and not os.path.isdir(args.compounds)):
            raise ConfigError(f"compound registry {args.compounds} is not "
                              "a directory")
        if (os.path.exists(args.sequences)
                and not os.path.isdir(args.sequences)):
            raise ConfigError(f"sequences directory {args.sequences} is "
                              "not a directory")
        fields = load_fields(args.settings or DEFAULT_SETTINGS,
                             must_exist=args.settings is not None)
        ctx = Context(load_vocabulary(args.vocabulary), args.static_dir,
                      load_zone(), fields=fields)
    except ConfigError as exc:
        print(f"validate.py: error: {exc}", file=sys.stderr)
        return 2
    return run(args.content_roots, args.compounds, args.sequences, ctx)


if __name__ == "__main__":
    sys.exit(main())
