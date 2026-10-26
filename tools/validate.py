#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Validate OrgSynDB procedure files against the procedure schema.

Content roots are directories of Markdown procedures with ``+++`` TOML
front matter, such as an ox-hugo export directory. The validator reads
no Org source: an Org procedure reaches it only as its export, and the
export checks the Org source itself. Each problem is printed to stdout
as ``<path>:<field>: <severity>: <message>``, followed by a summary line
on stderr. The exit status is 0 when no error
was found, 1 when at least one was, and 2 on a usage or configuration
error.
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

APP = Path(__file__).resolve().parent.parent
DEFAULT_VOCABULARY = APP / "site" / "data" / "reaction_types.toml"
# Structure images belong to a collection; run from its root.
DEFAULT_STATIC_DIR = Path("static")
ZONE_NAME = "Europe/Berlin"

ID_RE = re.compile(r"^OSDB-(\d{4})$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SCALE_RE = re.compile(r"^\d+([.,]\d+)?\s+\S+$")
CAS_RE = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")
AI_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")
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
# Front-matter values that every variant of a procedure shares; the
# dotted names are keys of the product table.
SHARED_FIELDS = ("status", "reaction_types", "tags", "yield_percent",
                 "precursors", "structure_image", "product.formula",
                 "product.mw", "product.smiles", "product.cas")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

ERROR = "error"
WARNING = "warning"


class ConfigError(Exception):
    """A usage or configuration problem that ends the run with status 2."""


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


def procedure_number(value: object) -> int | None:
    """Return the number of an ``OSDB-NNNN`` string, or None if malformed."""
    if not isinstance(value, str):
        return None
    match = ID_RE.match(value)
    return int(match.group(1)) if match else None


def is_valid_id(value: object) -> bool:
    """Whether ``value`` is an ID string from OSDB-0001 to OSDB-9999."""
    number = procedure_number(value)
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


def check_id(value: object) -> list[Problem]:
    """Check the ``id`` field's format and range."""
    if procedure_number(value) is None:
        return [error("id", f"{value!r} must match OSDB-NNNN "
                      "(OSDB- and four digits)")]
    if not is_valid_id(value):
        return [error("id", "must be between OSDB-0001 and OSDB-9999")]
    return []


def check_slug(value: object, ident: object) -> list[Problem]:
    """Check that ``slug`` is the lowercased ``id``.

    The equality check runs only when ``ident`` is a valid ID.
    """
    if not isinstance(value, str):
        return [error("slug", "must be a string")]
    if is_valid_id(ident):
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


def check_yield(value: object) -> list[Problem]:
    """Check that ``yield_percent`` is a finite number from 0 to 100."""
    name = "yield_percent"
    if not is_number(value):
        return [error(name, "must be a number, unquoted, e.g. 85")]
    if not math.isfinite(value) or not 0 <= value <= 100:
        return [error(name, f"{value} must be between 0 and 100")]
    return []


def check_scale(value: object) -> list[Problem]:
    """Check that ``scale`` is a number, whitespace and a unit."""
    if not isinstance(value, str) or not SCALE_RE.match(value):
        return [error("scale", f"{value!r} must be a number followed by "
                      'a unit, e.g. "25 mmol"')]
    return []


def check_product(value: object) -> list[Problem]:
    """Check the ``product`` table and its keys.

    Sub-field problems are reported under ``product.<key>``. When the
    value is not a table, no sub-field is checked.
    """
    if not isinstance(value, dict):
        return [error("product", "must be a table ([product])")]
    found: list[Problem] = []
    for key in ("name", "formula"):
        if key not in value:
            found.append(error(f"product.{key}", "required field missing"))
        else:
            found += check_string(f"product.{key}", value[key])
    mw = value.get("mw")
    if "mw" not in value:
        found.append(error("product.mw", "required field missing"))
    elif not is_number(mw):
        found.append(error("product.mw", "must be a number in g/mol, "
                           "unquoted, e.g. 88.11"))
    elif not math.isfinite(mw) or mw <= 0:
        found.append(error("product.mw", "must be greater than 0"))
    if "smiles" not in value:
        found.append(error("product.smiles", "required field missing"))
    else:
        found += check_string("product.smiles", value["smiles"])
    if "cas" in value:
        cas = value["cas"]
        if not isinstance(cas, str) or not CAS_RE.match(cas):
            found.append(error("product.cas", f"{cas!r} must have the "
                               'form NNNNNNN-NN-N, e.g. "64-17-5"'))
        elif not cas_check_digit_ok(cas):
            found.append(error("product.cas", f'"{cas}" has a wrong check '
                               "digit; check the number"))
    for key in value:
        if key not in ("name", "formula", "mw", "smiles", "cas"):
            found.append(warning(f"product.{key}", "unknown field"))
    return found


def check_precursors(value: object, ident: object) -> list[Problem]:
    """Check the shape of ``precursors`` and that it omits ``ident``.

    Existence is checked across files by ``check_cross_file``.
    """
    name = "precursors"
    if not is_string_list(value):
        return [error(name, 'must be a list of procedure ids, '
                      'e.g. ["OSDB-0001"]')]
    found: list[Problem] = []
    for entry in value:
        if not is_valid_id(entry):
            found.append(error(name, f'"{entry}" must match OSDB-NNNN, '
                               "from OSDB-0001 to OSDB-9999"))
        elif entry == ident:
            found.append(error(name, f"{entry} lists the procedure itself"))
    return found


def check_structure_image(value: object, static_dir: Path) -> list[Problem]:
    """Check ``structure_image``'s form, then that the file exists.

    The existence check runs only when the path has an allowed prefix
    and suffix.
    """
    name = "structure_image"
    if not isinstance(value, str):
        return [error(name, "must be a string")]
    parts = value.split("/")
    if (not value.startswith("structures/") or ".." in parts
            or "\\" in value or len(parts) < 2 or not parts[-1]):
        return [error(name, f'"{value}" must be a relative path under '
                      'structures/, e.g. "structures/osdb-0001.svg"')]
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
                 "status", "reaction_types", "tags", "product", "scale",
                 "yield_percent", "hazards")
OPTIONAL_KEYS = ("precursors", "structure_image", "checked_by",
                 "references", "ai_model", "language")


def check_fields(data: dict[str, Any], ctx: Context) -> list[Problem]:
    """Check every front-matter key of one content file on its own.

    Covers required and optional fields, the ``lastmod >= date``
    ordering, and keys outside the schema. Checks that need other files
    or the file name are not included.
    """
    found: list[Problem] = []
    for key in REQUIRED_KEYS:
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
                date = data.get("date")
                if is_offset_datetime(value) and is_offset_datetime(
                        date) and value < date:
                    found.append(error(
                        key, f"{value.isoformat()} is earlier than date "
                        f"{date.isoformat()}"))
                found += check_datetime(key, value, ctx.zone)
            case "authors" | "hazards":
                found += check_string_list(key, value, non_empty=True)
            case "status":
                found += check_status(value)
            case "reaction_types":
                found += check_reaction_types(value, ctx.vocabulary)
            case "tags":
                found += check_tags(value)
            case "product":
                found += check_product(value)
            case "scale":
                found += check_scale(value)
            case "yield_percent":
                found += check_yield(value)
    for key in OPTIONAL_KEYS:
        if key not in data:
            continue
        value = data[key]
        match key:
            case "precursors":
                found += check_precursors(value, data.get("id"))
            case "structure_image":
                found += check_structure_image(value, ctx.static_dir)
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


def file_name_pattern(suffix: str) -> re.Pattern[str]:
    """Return the procedure file-name pattern for ``suffix``.

    Group 1 is the ID, group 2 the base name without the language code
    and suffix, and group 3 the language code, if any.
    """
    return re.compile(rf"^((OSDB-\d{{4}})-[a-z0-9]+(?:-[a-z0-9]+)*)"
                      rf"(?:\.([a-z]{{2}}))?{re.escape(suffix)}$")


def language_of(name: str) -> str | None:
    """Return the language code of a procedure file name, or None.

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


def check_file_name(name: str, suffix: str,
                    ident: object) -> list[Problem]:
    """Check a procedure file name, and its prefix against ``ident``.

    The agreement check runs only when ``ident`` is a valid ID; pass
    None to skip it.
    """
    match = file_name_pattern(suffix).match(name)
    if match is None:
        return [error("file_name", f"must be named OSDB-NNNN-short-slug"
                      f"{suffix}, e.g. OSDB-0001-ethyl-acetate{suffix}, or "
                      f"OSDB-0001-ethyl-acetate.de{suffix} with a language")]
    code = match.group(3)
    if code is not None and code not in LANGUAGES:
        return [error("file_name", f'unknown language code ".{code}"; '
                      f"use {' or '.join(LANGUAGES)}, or none")]
    if is_valid_id(ident) and match.group(2) != ident:
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


def shared_value(data: dict[str, Any], name: str) -> object:
    """Return the value of a ``SHARED_FIELDS`` entry, or None if unset."""
    if name.startswith("product."):
        product = data.get("product")
        return (product.get(name.removeprefix("product."))
                if isinstance(product, dict) else None)
    return data.get(name)


def same_value(mine: object, theirs: object) -> bool:
    """Whether two shared-field values agree: numbers by value, so that
    ``85`` and ``85.0`` match, and anything else by value and type."""
    if is_number(mine) and is_number(theirs):
        return mine == theirs
    return mine == theirs and type(mine) is type(theirs)


def reference_variant(holders: Sequence[ContentFile]) -> ContentFile:
    """The variant the others of one ID are compared with: the file
    without a language code, else the first in ``LANGUAGES`` order."""
    def rank(item: ContentFile) -> tuple[int, str]:
        lang = item.language
        return (-1 if lang is None else LANGUAGES.index(lang), item.path)
    return min(holders, key=rank)


def check_variants(holders: Sequence[ContentFile]) -> None:
    """Check the variants of one ID against their reference variant.

    ``holders`` are the parsed files sharing one ID, at most one per
    language code (or none). Each must have the reference's base name
    and the same value, or absence, of every ``SHARED_FIELDS`` entry.
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
        for name in SHARED_FIELDS:
            mine = shared_value(item.data, name)
            theirs = shared_value(original.data, name)
            if not same_value(mine, theirs):
                shown = "unset" if theirs is None else repr(theirs)
                item.problems.append(error(
                    name, f"must equal the value in {original.path} "
                    f"({shown}); the variants of a procedure share it"))


def check_cross_file(files: Sequence[ContentFile]) -> None:
    """Add duplicate-ID, variant and precursor-existence problems.

    An ID may be used once per language code, and once without one; the
    files of one ID are variants, checked by ``check_variants``.
    Files whose front matter did not parse contribute no ID and are not
    checked.
    """
    by_id: dict[str, list[ContentFile]] = {}
    for item in files:
        if item.data is not None and is_valid_id(item.data.get("id")):
            by_id.setdefault(item.data["id"], []).append(item)
    for ident, holders in by_id.items():
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
            check_variants(holders)
    for item in files:
        if item.data is None:
            continue
        precursors = item.data.get("precursors")
        if not is_string_list(precursors):
            continue
        for entry in precursors:
            if (is_valid_id(entry) and entry != item.data.get("id")
                    and entry not in by_id):
                item.problems.append(error(
                    "precursors", f"{entry} not found in any content "
                    "root"))


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


def discover(root: str, suffix: str) -> list[Entry]:
    """List the top-level procedure files of ``root``, sorted by name.

    Dotfiles and ``_index.md`` are omitted. A subdirectory or a file
    without ``suffix`` is returned with the problem it raises instead of
    as a procedure.
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
                "file_name", "not a procedure file; ignored")))
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
        description="Validate OrgSynDB procedures. Prints one "
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
        "--static-dir", type=Path, default=DEFAULT_STATIC_DIR,
        metavar="DIR",
        help="directory that structure_image paths are relative to "
        "(default: static in the working directory)")
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


def run(content_roots: Sequence[str], ctx: Context) -> int:
    """Validate the content roots and report; return the exit status."""
    problems: list[tuple[str, Problem]] = []
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
    return report(problems, len(content))


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
        ctx = Context(load_vocabulary(args.vocabulary), args.static_dir,
                      load_zone())
    except ConfigError as exc:
        print(f"validate.py: error: {exc}", file=sys.stderr)
        return 2
    return run(args.content_roots, ctx)


if __name__ == "__main__":
    sys.exit(main())
