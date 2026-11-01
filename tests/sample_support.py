"""Read sample procedures from their source files and check the quantity
rules of the sample-procedures spec. Pure helpers, no I/O beyond reading."""

import datetime
import re
import tomllib
from pathlib import Path
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

HEADER = ["Reagent", "CAS", "MW (g/mol)", "Amount", "mmol", "Equiv"]
# What the rules look for in a sample of each language: the Reagents
# table header, the section names, the catalyst marker and the Summary
# phrase. German samples write decimal commas.
TERMS = {
    "en": {"header": HEADER, "summary": "Summary", "reagents": "Reagents",
           "procedure": "Procedure", "notes": "Notes", "catalyst": "cat.",
           "unverified": "not experimentally verified"},
    "de": {"header": ["Reagenz", "CAS", "M (g/mol)", "Menge", "mmol",
                      "Äquiv."],
           "summary": "Zusammenfassung", "reagents": "Reagenzien",
           "procedure": "Durchführung", "notes": "Anmerkungen",
           "catalyst": "kat.", "unverified": "nicht experimentell überprüft"},
}
WEIGHTS = {"B": 10.81, "C": 12.011, "H": 1.008, "N": 14.007, "O": 15.999,
           "Na": 22.990, "P": 30.974, "S": 32.06, "Cl": 35.45, "K": 39.098,
           "Br": 79.904}


class Sample(NamedTuple):
    path: Path
    data: dict[str, Any]       # front matter, as exported (id, tags, ...)
    ai_model: str | None       # None when absent or "none"
    summary: str
    table: list[list[str]]     # rows below the header, cells stripped

    @property
    def language(self) -> str:
        return language_of(self.path)

    @property
    def terms(self) -> dict[str, Any]:
        return TERMS[self.language]


def language_of(path: Path) -> str:
    """``de`` for ``*.de.org`` and ``*.de.md``, else ``en``."""
    suffixes = path.suffixes
    return suffixes[-2][1:] if len(suffixes) > 1 else "en"


def number(text: str) -> float:
    """A table number, with a decimal point or a German decimal comma."""
    return float(text.replace(",", "."))


# --- reading ---------------------------------------------------------------

def read_elisp(text: str, pos: int = 0) -> tuple[Any, int]:
    """Read one Elisp literal: string, number, symbol, quoted list or
    alist. Quoted lists become lists, dotted pairs become tuples, and the
    symbols ``true`` and ``false`` become booleans, as ox-hugo writes
    them."""
    while text[pos].isspace():
        pos += 1
    char = text[pos]
    if char == "'":
        return read_elisp(text, pos + 1)
    if char == '"':
        end = pos + 1
        out = []
        while text[end] != '"':
            if text[end] == "\\":
                end += 1
            out.append(text[end])
            end += 1
        return "".join(out), end + 1
    if char == "(":
        items: list[Any] = []
        pos += 1
        while True:
            while text[pos].isspace():
                pos += 1
            if text[pos] == ")":
                break
            if text[pos] == "." and text[pos + 1].isspace():
                value, pos = read_elisp(text, pos + 1)
                items = [(items[0], value)]
                continue
            value, pos = read_elisp(text, pos)
            items.append(value)
        return items, pos + 1
    match = re.compile(r"[^\s()\"']+").match(text, pos)
    token = match.group(0)
    if token in ("true", "false"):
        return token == "true", match.end()
    try:
        return (int(token) if re.fullmatch(r"-?\d+", token)
                else float(token)), match.end()
    except ValueError:
        return token, match.end()


def alist_to_dict(value: Any) -> Any:
    """Turn a list of (key . value) pairs, as read, into a dict."""
    if isinstance(value, list) and value and all(
            isinstance(item, list) and len(item) == 1
            and isinstance(item[0], tuple) for item in value):
        return {item[0][0]: item[0][1] for item in value}
    return value


def read_plist(line: str) -> dict[str, Any]:
    """Parse ``:key value :key value`` from a custom-front-matter line."""
    out: dict[str, Any] = {}
    pos = 0
    while pos < len(line):
        if line[pos].isspace():
            pos += 1
            continue
        key, pos = read_elisp(line, pos)
        value, pos = read_elisp(line, pos)
        out[key.removeprefix(":")] = value
    return out


def org_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    name = None
    for line in text.splitlines():
        match = re.match(r"^\* (.+?)\s*$", line)
        if match:
            name = match.group(1)
            sections[name] = ""
        elif name is not None:
            sections[name] += line + "\n"
    return sections


def md_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    name = None
    for line in body.splitlines():
        match = re.match(r"^## (.+?)\s*$", line)
        if match:
            name = match.group(1)
            sections[name] = ""
        elif name is not None:
            sections[name] += line + "\n"
    return sections


def table_rows(section: str) -> list[list[str]]:
    """Cell lists of every table row, skipping separator lines."""
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.fullmatch(r"\|[-+|:\s]+\|?", line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def read_org(path: Path) -> Sample:
    text = path.read_text(encoding="utf-8")
    data: dict[str, Any] = {}
    keywords: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^#\+([A-Za-z_]+):\s*(.*?)\s*$", line)
        if not match:
            continue
        name, value = match.group(1).upper(), match.group(2)
        if name == "HUGO_CUSTOM_FRONT_MATTER":
            data |= {k: alist_to_dict(v) for k, v in
                     read_plist(value).items()}
        else:
            keywords.setdefault(name, value)
    data["tags"] = keywords.get("HUGO_TAGS", "").split()
    if "products" in data:
        data["products"] = [alist_to_dict(entry) for entry in data["products"]]
    model = keywords.get("AI_MODEL")
    sections = org_sections(text)
    terms = TERMS[language_of(path)]
    rows = table_rows(sections.get(terms["reagents"], ""))
    return Sample(path, data, None if model in (None, "none") else model,
                  sections.get(terms["summary"], ""), rows)


def read_markdown(path: Path) -> Sample:
    lines = path.read_text(encoding="utf-8").split("\n")
    end = lines.index("+++", 1)
    data = tomllib.loads("\n".join(lines[1:end]))
    sections = md_sections("\n".join(lines[end + 1:]))
    terms = TERMS[language_of(path)]
    return Sample(path, data, data.get("ai_model"),
                  sections.get(terms["summary"], ""),
                  table_rows(sections.get(terms["reagents"], "")))


def sample_procedures(repo: Path) -> list[Sample]:
    """Every procedure in org/procedures/ and md/procedures/, in any
    language, whose tags include ``sample-data``."""
    found = []
    for path in sorted((repo / "org" / "procedures").glob("OSDB-*.org")):
        found.append(read_org(path))
    for path in sorted((repo / "md" / "procedures").glob("OSDB-*.md")):
        found.append(read_markdown(path))
    return [s for s in found if "sample-data" in s.data.get("tags", [])]


def product_keys(data: dict[str, Any]) -> list[str]:
    """The compound keys of a procedure's products: its own, or for a
    general procedure those of all the entries of its scope, each once,
    in order of first appearance."""
    entries = [e for entry in data.get("scope", [])
               for e in entry["products"]]
    entries += data.get("products", [])
    return list(dict.fromkeys(e["compound"] for e in entries))


def substrate_keys(data: dict[str, Any]) -> list[str]:
    """The compound keys of a procedure's substrates, over its scope for
    a general procedure."""
    keys = [key for entry in data.get("scope", [])
            for key in entry["substrates"]]
    return list(dict.fromkeys(keys + list(data.get("substrates", []))))


def scope_without_notes(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The entries of a procedure's scope without their ``note``, or
    None for a specific procedure."""
    if "scope" not in data:
        return None
    return [{k: v for k, v in entry.items() if k != "note"}
            for entry in data["scope"]]


def named_compounds(sample: Sample) -> list[str]:
    """The keys a sample names, products first, then substrates."""
    return product_keys(sample.data) + substrate_keys(sample.data)


def read_registry(registry: Path) -> dict[str, dict[str, Any]]:
    """Each compound file of a registry directory, by key."""
    return {path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
            for path in sorted(registry.glob("*.toml"))}


# --- rules -----------------------------------------------------------------

def cas_ok(cas: str) -> bool:
    if not re.fullmatch(r"\d{2,7}-\d{2}-\d", cas):
        return False
    digits = cas.replace("-", "")
    total = sum(i * int(d) for i, d in enumerate(reversed(digits[:-1]), 1))
    return total % 10 == int(digits[-1])


def formula_weight(formula: str) -> float:
    parts = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    if "".join(e + n for e, n in parts) != formula:
        raise ValueError(f"cannot read formula {formula!r}")
    return sum(WEIGHTS[e] * int(n or 1) for e, n in parts)


def compound_violations(key: str, compound: dict[str, Any]) -> list[str]:
    """Return the sample-procedures rules a demo registry compound
    breaks: its ``mw`` against its formula, and its CAS number."""
    problems = []
    try:
        weight = formula_weight(compound.get("formula", ""))
        if abs(float(compound.get("mw", "nan")) - weight) > 0.02:
            problems.append(f"{key}: mw {compound.get('mw')} vs {weight:.2f}")
    except ValueError as exc:
        problems.append(f"{key}: {exc}")
    if not cas_ok(compound.get("cas", "")):
        problems.append(f"{key}: CAS {compound.get('cas')!r} fails the "
                        "check digit")
    return problems


def quantity_violations(sample: Sample) -> list[str]:
    """Return the quantity rules the sample's Reagents table breaks."""
    problems = []
    header = sample.terms["header"]
    if not sample.table or sample.table[0] != header:
        return [f"columns are {sample.table[:1]}, not {header}"]
    rows = sample.table[1:]
    if not rows:
        return ["Reagents table has no rows"]
    for cells in rows:
        if len(cells) != len(header):
            problems.append(f"row {cells} has {len(cells)} cells")
    rows = [r for r in rows if len(r) == len(header)]
    for name, cas, _mw, _amount, _mmol, _equiv in rows:
        if not cas_ok(cas):
            problems.append(f"{name}: CAS {cas} fails the check digit")
    full = [r for r in rows if sample.terms["catalyst"] not in (r[4], r[5])]
    for name, _cas, mw, amount, mmol, _equiv in full:
        mass = re.match(r"^(\d+(?:[.,]\d+)?) g(?:\s|$)", amount)
        if mass:
            expected = 1000 * number(mass.group(1)) / number(mw)
            if abs(number(mmol) - expected) > 0.01 * expected:
                problems.append(
                    f"{name}: {mmol} mmol, expected {expected:.2f}")
    limiting = [r for r in full if number(r[5]) == 1.0]
    if len(limiting) != 1:
        problems.append(f"{len(limiting)} rows have Equiv 1.0, not one")
        return problems
    base = number(limiting[0][4])
    for name, _c, _m, _a, mmol, equiv in full:
        if abs(number(equiv) - number(mmol) / base) > 0.05:
            problems.append(f"{name}: Equiv {equiv} vs {mmol}/{base:g}")
    scale = re.fullmatch(r"(\d+(?:[.,]\d+)?) mmol", str(
        sample.data.get("scale", "")))
    if scale and abs(number(scale.group(1)) - base) > 0.01 * base:
        problems.append(f"scale {scale.group(1)} mmol vs limiting {base:g}")
    return problems


# --- agreement of a converted sample with its Org source -------------------

_SPAN = r"\S(?:.*?\S)?"
# Org's emphasis syntax: the opening marker follows the start of the text,
# whitespace or one of -('"{ and the closing marker precedes the end,
# whitespace or one of -.,:!?;'")}\[.
ORG_EMPHASIS = re.compile(
    rf"""(?<![^\s\-('"{{])([/*=~+_])({_SPAN})\1(?![^\s\-.,:!?;'")}}\[])""")
MD_EMPHASIS = re.compile(
    rf"\*\*({_SPAN})\*\*|\*({_SPAN})\*|`({_SPAN})`"
    rf"|(?<!\w)_({_SPAN})_(?!\w)")
TIMESTAMP = re.compile(r"\[(\d{4}-\d\d-\d\d)(?: [^\W\d_]+)?"
                       r"(?: (\d\d:\d\d)(?::(\d\d))?)?\]")
BERLIN = ZoneInfo("Europe/Berlin")


def read_org_keywords(path: Path) -> dict[str, str]:
    """The first value of each Org keyword in the file, keyed by its
    upper-cased name. ``#+HUGO_CUSTOM_FRONT_MATTER`` is left out."""
    keywords: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#\+([A-Za-z_]+):\s*(.*?)\s*$", line)
        if match and match.group(1).upper() != "HUGO_CUSTOM_FRONT_MATTER":
            keywords.setdefault(match.group(1).upper(), match.group(2))
    return keywords


def berlin_instants(stamp: str) -> list[datetime.datetime]:
    """The Europe/Berlin instants an Org timestamp names, earliest first:
    two in the autumn fall-back hour, otherwise one. Empty when ``stamp``
    is not a timestamp."""
    match = TIMESTAMP.fullmatch(stamp)
    if match is None:
        return []
    date, clock, seconds = match.groups()
    naive = datetime.datetime.fromisoformat(
        f"{date}T{clock or '00:00'}:{seconds or '00'}")
    found = {naive.replace(tzinfo=BERLIN, fold=fold).utcoffset(): fold
             for fold in (0, 1)}
    return sorted((naive.replace(tzinfo=BERLIN, fold=fold)
                   for fold in found.values()),
                  key=lambda moment: moment.astimezone(datetime.UTC))


def exported_instants(created: list[datetime.datetime],
                      modified: list[datetime.datetime]
                      ) -> tuple[datetime.datetime, datetime.datetime]:
    """The ``date`` and ``lastmod`` instants the export writes: the
    earliest of ``created``, and the earliest of ``modified`` not before
    it, else the latest of ``modified``. Both lists are non-empty and
    sorted earliest first."""
    date = created[0]
    later = [m for m in modified if m.astimezone(datetime.UTC)
             >= date.astimezone(datetime.UTC)]
    return date, later[0] if later else modified[-1]


def normalise_text(text: str, emphasis: re.Pattern[str]) -> str:
    """Section text without table lines, whitespace collapsed to single
    spaces and each emphasis span replaced by its inner text, the last
    group of the pattern that matched."""
    text = "\n".join(line for line in text.splitlines()
                     if not line.strip().startswith("|"))
    return emphasis.sub(
        lambda m: [g for g in m.groups() if g is not None][-1],
        " ".join(text.split()))


def agreement_differences(org: Path, markdown: Path) -> list[str]:
    """Where the Markdown procedure disagrees with the Org source it was
    converted from; empty when they agree. Compared are the front matter,
    the ``date`` and ``lastmod`` wall-clock time and Berlin offset, the
    top-level headings, the Reagents rows and each section's text."""
    out: list[str] = []
    source = read_org(org)
    keywords = read_org_keywords(org)
    lines = markdown.read_text(encoding="utf-8").split("\n")
    end = lines.index("+++", 1)
    data = tomllib.loads("\n".join(lines[1:end]))
    body = lines[end + 1:]

    expected = {k: v for k, v in source.data.items() if k != "tags"} | {
        "title": keywords.get("TITLE"), "slug": keywords.get("HUGO_SLUG"),
        "tags": source.data["tags"]} | (
            {"ai_model": source.ai_model} if source.ai_model else {})
    for key in sorted(expected.keys() | data.keys() | {"date", "lastmod"}):
        if key in ("date", "lastmod"):
            if key not in data:
                out.append(f"front matter lacks {key}")
        elif key not in data:
            out.append(f"front matter lacks {key}")
        elif key not in expected:
            out.append(f"front matter has extra key {key}")
        elif data[key] != expected[key]:
            out.append(f"{key} is {data[key]!r}, not {expected[key]!r}")
    created = berlin_instants(keywords.get("CREATED", ""))
    modified = berlin_instants(keywords.get("LAST_MODIFIED", ""))
    chosen = (exported_instants(created, modified) if created and modified
              else (None, None))
    for key, name, want in (("date", "CREATED", chosen[0]),
                            ("lastmod", "LAST_MODIFIED", chosen[1])):
        got = data.get(key)
        if want is None:
            out.append(f"#+{name} is not a timestamp, or #+CREATED and "
                       "#+LAST_MODIFIED are not both timestamps")
        elif not isinstance(got, datetime.datetime) or got.tzinfo is None:
            out.append(f"{key} is not an offset datetime")
        elif (got.replace(tzinfo=None) != want.replace(tzinfo=None)
              or got.utcoffset() != want.utcoffset()):
            out.append(f"{key} is {got.isoformat()}, not "
                       f"{want.isoformat()}")

    before = "".join(body[:next((i for i, line in enumerate(body)
                                 if line.startswith("## ")), len(body))])
    if before.strip():
        out.append("text before the first heading")
    org_text = org.read_text(encoding="utf-8")
    org_heads = re.findall(r"(?m)^\* (.+?)\s*$", org_text)
    md_heads = re.findall(r"(?m)^## (.+?)\s*$", "\n".join(body))
    if md_heads != org_heads:
        out.append(f"headings are {md_heads}, not {org_heads}")

    terms = TERMS[language_of(org)]
    sections = md_sections("\n".join(body))
    org_sects = org_sections(org_text)
    rows = table_rows(sections.get(terms["reagents"], ""))
    if rows != source.table:
        out.append(f"Reagents rows are {rows}, not {source.table}")
    for name, text in org_sects.items():
        if name not in sections:
            continue
        want = normalise_text(text, ORG_EMPHASIS)
        got = normalise_text(sections[name], MD_EMPHASIS)
        if got != want:
            out.append(f"section {name} reads {got!r}, not {want!r}")
    return out


# --- the demo's compound fields ---------------------------------------------

DEMO_DECLARATIONS = [
    {"key": "item_number", "type": "text", "required": True,
     "unique": True, "pattern": r"CH-\d{4}", "column": True,
     "search": True},
    {"key": "short_name", "type": "text", "search": True},
    {"key": "chemical_class", "type": "choice", "required": True,
     "multiple": True, "column": True, "facet": True,
     "vocabulary": "chemical-classes"},
    {"key": "stock", "type": "number", "unit": "g", "min": 0},
    {"key": "in_house", "type": "boolean", "facet": True},
    {"key": "group", "type": "choice", "required": True, "facet": True,
     "tabs": True, "vocabulary": "inventory-groups"},
]
DEMO_LABELS = {"group": ("Group", "Gruppe")}
DEMO_PROCEDURE_DECLARATIONS = [
    {"key": "notebook", "type": "text", "unique": True,
     "pattern": r"[A-Z]{2}-\d+/\d+"},
    {"key": "project", "type": "choice", "facet": True,
     "vocabulary": "projects"},
    {"key": "working_time", "type": "number", "unit": "h", "min": 0},
    {"key": "inert_atmosphere", "type": "boolean", "facet": True},
]
DEMO_PROCEDURE_LABELS = {
    "notebook": ("Lab notebook", "Laborjournal"),
    "project": ("Project", "Projekt"),
    "working_time": ("Working time", "Arbeitszeit"),
    "inert_atmosphere": ("Inert atmosphere", "Schutzgas")}
# The values of projects.toml in file order, each with its parent and its
# English and German labels.
PROJECTS = [
    ("teaching", None, "Teaching", "Lehre"),
    ("first-year-practical", "teaching", "First-year practical",
     "Grundpraktikum"),
    ("advanced-practical", "teaching", "Advanced practical",
     "Fortgeschrittenenpraktikum"),
    ("research", None, "Research", "Forschung"),
    ("biaryls", "research", "Biaryls", "Biaryle"),
    ("cinnamates", "research", "Cinnamates", "Zimts\u00e4urederivate"),
]
PROJECT_VALUES = ("first-year-practical", "advanced-practical", "biaryls",
                  "cinnamates")
PROCEDURE_KEYS = ("notebook", "project", "working_time", "inert_atmosphere")
# The values of inventory-groups.toml in file order, each with its parent
# and its English and German labels.
INVENTORY_GROUPS = [
    ("purchased", None, "Purchased", "Zugekauft"),
    ("starting-materials", "purchased", "Starting materials",
     "Ausgangsstoffe"),
    ("reagents", "purchased", "Reagents", "Reagenzien"),
    ("synthesised", None, "Synthesised", "Selbst hergestellt"),
    ("intermediates", "synthesised", "Intermediates", "Zwischenprodukte"),
    ("final-products", "synthesised", "Final products", "Endprodukte"),
]
PURCHASED_GROUPS = ("starting-materials", "reagents")
GROUP_VALUES = ("starting-materials", "reagents", "intermediates",
                "final-products")


def vocabulary_depth(vocabulary: dict[str, dict[str, Any]],
                     value: str) -> int:
    """The number of ancestors of ``value`` in ``vocabulary``."""
    depth = 0
    while "parent" in vocabulary[value]:
        value = vocabulary[value]["parent"]
        depth += 1
    return depth


def field_violations(collection: Path) -> list[str]:
    """Return the rules of sample-procedures "Demo collection" that the
    declarations, the vocabulary and the compounds' values of
    ``collection`` break."""
    problems: list[str] = []
    try:
        settings = tomllib.loads(
            (collection / "orgsyndb.toml").read_text(encoding="utf-8"))
        declared = settings["fields"]["compound"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        return [f"orgsyndb.toml declares no compound field: {exc!r}"]
    labels = [(d.get("label"), d.get("label_de")) for d in declared]
    bare = [{k: v for k, v in d.items() if k not in ("label", "label_de")}
            for d in declared]
    if bare != DEMO_DECLARATIONS:
        problems.append(f"declarations are {bare}")
    for key, pair in zip((d.get("key") for d in declared), labels):
        for label in pair:
            if not isinstance(label, str) or not label.strip():
                problems.append(f"{key}: missing label or label_de")
        if key in DEMO_LABELS and pair != DEMO_LABELS[key]:
            problems.append(f"{key}: labels are {pair}")
    names = sorted(p.name for p in (collection / "vocabularies").glob("*"))
    if names != ["chemical-classes.toml", "inventory-groups.toml",
                 "projects.toml", "reaction-types.toml"]:
        problems.append(f"vocabularies/ holds {names}")
    problems += reaction_type_violations(collection)
    vocabularies = {}
    try:
        for name in ("chemical-classes", "inventory-groups", "projects"):
            vocabularies[name] = tomllib.loads(
                (collection / "vocabularies" / f"{name}.toml"
                 ).read_text(encoding="utf-8"))
            for value, entry in vocabularies[name].items():
                if not str(entry.get("label_de", "")).strip():
                    problems.append(f"{name}/{value}: no label_de")
                if entry.get("parent", value) not in vocabularies[name]:
                    problems.append(f"{name}/{value}: parent is not a "
                                    "value")
        vocabulary = vocabularies["chemical-classes"]
        depths = [vocabulary_depth(vocabulary, v) for v in vocabulary]
    except (OSError, KeyError, RecursionError, tomllib.TOMLDecodeError) as exc:
        return problems + [f"vocabularies: {exc!r}"]
    groups = [(value, entry.get("parent"), entry.get("label"),
               entry.get("label_de"))
              for value, entry in vocabularies["inventory-groups"].items()]
    if groups != INVENTORY_GROUPS:
        problems.append(f"inventory-groups holds {groups}")
    if max(depths, default=0) < 2:
        problems.append("no value has two ancestors")
    registry = read_registry(collection / "compounds")
    classes = [c.get("chemical_class") for c in registry.values()]
    for key, compound in registry.items():
        for field in ("item_number", "chemical_class", "group"):
            if field not in compound:
                problems.append(f"{key}: sets no {field}")
        value = compound.get("chemical_class")
        if not isinstance(value, list) or not set(value) <= set(vocabulary):
            problems.append(f"{key}: chemical_class is {value!r}")
    held = [c.get("group") for c in registry.values()]
    for value in GROUP_VALUES:
        if value not in held:
            problems.append(f"no compound has group {value!r}")
    if not set(held) <= set(GROUP_VALUES):
        problems.append(f"groups are {held}")
    purchased = sum(g in PURCHASED_GROUPS for g in held)
    if (purchased, len(held) - purchased) != (10, 10):
        problems.append(f"{purchased} purchased of {len(held)} compounds")
    numbers = [c.get("item_number") for c in registry.values()]
    if len(set(numbers)) != len(numbers) or not all(
            isinstance(n, str) and re.fullmatch(r"CH-\d{4}", n)
            for n in numbers):
        problems.append(f"item numbers are {numbers}")
    if not any(isinstance(c, list) and len(c) == 2 for c in classes):
        problems.append("no compound sets two chemical classes")
    if not any(isinstance(c, list) and any(
            vocabulary_depth(vocabulary, v) == 2 for v in c if v in vocabulary)
            for c in classes):
        problems.append("no compound sets a class with two ancestors")
    for field in ("short_name", "stock"):
        count = sum(field in c for c in registry.values())
        if count == 0 or count == len(registry):
            problems.append(f"{count} compounds set {field}")
    stocks = [c["stock"] for c in registry.values() if "stock" in c]
    if all(float(s).is_integer() for s in stocks):
        problems.append("every stock is a whole number")
    flags = [c.get("in_house") for c in registry.values()]
    for wanted in (True, False, None):
        if wanted not in flags:
            problems.append(f"no compound has in_house {wanted!r}")
    return problems + procedure_field_violations(
        collection, settings, vocabularies["projects"])


STARTER_REACTION_TYPES = (Path(__file__).resolve().parent.parent
                          / "templates" / "reaction-types.toml")


def reaction_type_violations(collection: Path) -> list[str]:
    """Return the rules of sample-procedures "Demo collection" that
    ``collection``'s ``vocabularies/reaction-types.toml`` breaks: it is
    byte-identical to the starter vocabulary ``templates/reaction-types.toml``,
    every value has a ``label_de``, and every reaction type that a sample
    procedure names is one of its values."""
    path = collection / "vocabularies" / "reaction-types.toml"
    try:
        data = path.read_bytes()
        values = tomllib.loads(data.decode("utf-8"))
        starter = STARTER_REACTION_TYPES.read_bytes()
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return [f"reaction-types.toml: {exc!r}"]
    problems = []
    if data != starter:
        problems.append("reaction-types.toml is not the starter vocabulary")
    for value, entry in values.items():
        if not str(entry.get("label_de", "")).strip():
            problems.append(f"reaction-types/{value}: no label_de")
    paths = [*sorted((collection / "org" / "procedures").glob("OSDB-*.org")),
             *sorted((collection / "md" / "procedures").glob("OSDB-*.md"))]
    for procedure in paths:
        sample = read_org(procedure) if procedure.suffix == ".org" \
            else read_markdown(procedure)
        for named in sample.data.get("reaction_types", []):
            if named not in values:
                problems.append(f"{procedure.name}: reaction type {named!r} "
                                "is not a value")
    return problems


def procedure_values(collection: Path) -> dict[str, list[dict[str, Any]]]:
    """The declared procedure fields that each procedure file of
    ``collection`` sets, in either format and language, by ID: one table
    per file, holding only the keys that the file sets."""
    found: dict[str, list[dict[str, Any]]] = {}
    paths = [*sorted((collection / "org" / "procedures").glob("OSDB-*.org")),
             *sorted((collection / "md" / "procedures").glob("OSDB-*.md"))]
    for path in paths:
        sample = read_org(path) if path.suffix == ".org" \
            else read_markdown(path)
        found.setdefault(sample.data["id"], []).append(
            {key: sample.data[key] for key in PROCEDURE_KEYS
             if key in sample.data})
    return found


def procedure_field_violations(collection: Path, settings: dict[str, Any],
                               projects: dict[str, dict[str, Any]]
                               ) -> list[str]:
    """Return the rules of sample-procedures "Demo collection" for the
    procedure fields that ``settings``, the vocabulary ``projects`` and
    the procedures of ``collection`` break."""
    problems: list[str] = []
    declared = settings.get("fields", {}).get("procedure", [])
    if not declared:
        return ["orgsyndb.toml declares no procedure field"]
    bare = [{k: v for k, v in d.items() if k not in ("label", "label_de")}
            for d in declared]
    if bare != DEMO_PROCEDURE_DECLARATIONS:
        problems.append(f"procedure declarations are {bare}")
    labels = {d.get("key"): (d.get("label"), d.get("label_de"))
              for d in declared}
    if labels != DEMO_PROCEDURE_LABELS:
        problems.append(f"procedure labels are {labels}")
    held = [(value, entry.get("parent"), entry.get("label"),
             entry.get("label_de")) for value, entry in projects.items()]
    if held != PROJECTS:
        problems.append(f"projects holds {held}")
    by_id = procedure_values(collection)
    if not by_id:
        return problems + ["no procedure"]
    values: dict[str, dict[str, Any]] = {}
    for number, variants in by_id.items():
        if any(variant != variants[0] for variant in variants):
            problems.append(f"{number}: variants set {variants}")
        values[number] = variants[0]
        for key in ("notebook", "project"):
            if key not in variants[0]:
                problems.append(f"{number}: sets no {key}")
        notebook = variants[0].get("notebook")
        if "notebook" in variants[0] and not (
                isinstance(notebook, str)
                and re.fullmatch(r"[A-Z]{2}-\d+/\d+", notebook)):
            problems.append(f"{number}: notebook is {notebook!r}")
        if variants[0].get("project", PROJECT_VALUES[0]) \
                not in PROJECT_VALUES:
            problems.append(f"{number}: project is "
                            f"{variants[0]['project']!r}")
        time = variants[0].get("working_time", 0)
        if isinstance(time, bool) or not isinstance(time, (int, float)) \
                or time < 0:
            problems.append(f"{number}: working_time is {time!r}")
        flag = variants[0].get("inert_atmosphere", False)
        if not isinstance(flag, bool):
            problems.append(f"{number}: inert_atmosphere is {flag!r}")
    notebooks = [v["notebook"] for v in values.values() if "notebook" in v]
    if len(set(notebooks)) != len(notebooks):
        problems.append(f"notebooks are {notebooks}")
    chosen = {v.get("project") for v in values.values()}
    for value in PROJECT_VALUES:
        if value not in chosen:
            problems.append(f"no procedure has project {value!r}")
    times = [v["working_time"] for v in values.values()
             if "working_time" in v]
    if not times or len(times) == len(values):
        problems.append(f"{len(times)} procedures set working_time")
    if times and all(float(t).is_integer() for t in times):
        problems.append("every working_time is a whole number")
    flags = [v.get("inert_atmosphere") for v in values.values()]
    for wanted in (False, None):
        if wanted not in flags:
            problems.append(f"no procedure has inert_atmosphere {wanted!r}")
    if not any(v.get("inert_atmosphere") is True and v.get("project") in (
            "biaryls", "cinnamates") for v in values.values()):
        problems.append("no procedure of a research project needs an "
                        "inert atmosphere")
    if "OSDB-0002" in values and values["OSDB-0002"] != {
            "notebook": "AE-1/2", "project": "first-year-practical",
            "working_time": 2.5, "inert_atmosphere": False}:
        problems.append(f"OSDB-0002 sets {values['OSDB-0002']}")
    elif "OSDB-0002" not in values:
        problems.append("OSDB-0002 is missing")
    return problems
