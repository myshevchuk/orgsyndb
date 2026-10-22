"""Read sample procedures from their source files and check the quantity
rules of the sample-procedures spec. Pure helpers, no I/O beyond reading."""

import re
import tomllib
from pathlib import Path
from typing import Any, NamedTuple

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
WEIGHTS = {"C": 12.011, "H": 1.008, "N": 14.007, "O": 15.999, "Na": 22.990,
           "P": 30.974, "S": 32.06, "Cl": 35.45, "K": 39.098, "Br": 79.904}


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
    alist. Quoted lists become lists, dotted pairs become tuples."""
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
    product = sample.data.get("product", {})
    try:
        weight = formula_weight(product.get("formula", ""))
        if abs(float(product.get("mw", "nan")) - weight) > 0.02:
            problems.append(f"product mw {product.get('mw')} vs {weight:.2f}")
    except ValueError as exc:
        problems.append(str(exc))
    return problems
