"""Shared query-choice, sorting, and HTMX URL helpers for list views."""

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any, TypeVar
from urllib.parse import urlencode, urlsplit

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

T = TypeVar("T")

_NUMBER_RE = re.compile(r"\A[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)\Z")
_AMOUNT_RE = re.compile(
    r"\A([+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*"
    r"(kg|g|mg|µg|ug|mol|mmol|µmol|umol)\Z"
)
_ISO_DATE_RE = re.compile(
    r"\A(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?\Z"
)
_DE_DATE_RE = re.compile(
    r"\A(\d{2})\.(\d{2})\.(\d{4})(?: (\d{2}):(\d{2})(?::(\d{2}))?)?\Z"
)
_DIGIT_RUN_RE = re.compile(r"(\d+)")

_MASS_FACTORS: dict[str, Decimal] = {
    "ug": Decimal("0.001"),
    "µg": Decimal("0.001"),
    "mg": Decimal("1"),
    "g": Decimal("1000"),
    "kg": Decimal("1000000"),
}
_MOLE_FACTORS: dict[str, Decimal] = {
    "umol": Decimal("1"),
    "µmol": Decimal("1"),
    "mmol": Decimal("1000"),
    "mol": Decimal("1000000"),
}


@dataclass(frozen=True)
class SortColumn:
    """Definition of one column of a main list.

    KEY identifies the column in ``sort`` query parameters. LABEL is the
    header text. VALUE maps a row to its sort key, or None when the row
    has no value. SORTABLE states whether the column accepts sorting.
    """

    key: str
    label: Any
    value: Callable[[Any], Any] | None = None
    sortable: bool = True


class Order:
    """Resolved sort order of a main list for one request."""

    def __init__(
        self,
        columns: Sequence[SortColumn],
        key: str,
        descending: bool,
        default_key: str,
        default_descending: bool,
    ) -> None:
        self.columns = tuple(columns)
        self._by_key = {col.key: col for col in self.columns}
        self.key = key
        self.descending = descending
        self.default_key = default_key
        self.default_descending = default_descending

    @classmethod
    def from_query(
        cls,
        query: Mapping[str, str],
        columns: Sequence[SortColumn],
        default_key: str,
        default_descending: bool = False,
    ) -> "Order":
        """Parse ``sort`` and ``dir`` from QUERY against COLUMNS.

        Unknown or unsortable keys fall back to DEFAULT_KEY and
        DEFAULT_DESCENDING. Any ``dir`` value other than ``"desc"``
        means ascending.
        """
        sortable = {col.key for col in columns if col.sortable}
        raw_sort = query.get("sort", "")
        if raw_sort in sortable:
            key = raw_sort
            descending = query.get("dir") == "desc"
        else:
            key = default_key
            descending = default_descending
        return cls(columns, key, descending, default_key, default_descending)

    @property
    def is_default(self) -> bool:
        """Return whether the order matches the list's default order."""
        return (
            self.key == self.default_key
            and self.descending == self.default_descending
        )

    @property
    def sort_field(self) -> str:
        """Return the ``sort`` hidden-field value, or empty on default."""
        return "" if self.is_default else self.key

    @property
    def dir_field(self) -> str:
        """Return the ``dir`` hidden-field value, or empty unless desc."""
        return "desc" if (not self.is_default and self.descending) else ""

    def link(
        self,
        key: str,
        filters: Sequence[tuple[str, str]] = (),
        selected: str = "",
        extra: Sequence[tuple[str, str]] = (),
    ) -> str:
        """Return the query string for KEY's column header link.

        Toggles to descending when KEY is currently active ascending,
        and ascending otherwise. Keeps FILTERS, SELECTED, and EXTRA.
        """
        pairs: list[tuple[str, str]] = list(filters)
        pairs.append(("sort", key))
        if key == self.key and not self.descending:
            pairs.append(("dir", "desc"))
        if selected:
            pairs.append(("selected", selected))
        pairs.extend(extra)
        return f"?{urlencode(pairs)}"

    def aria_sort(self, key: str) -> str:
        """Return ``"ascending"``, ``"descending"``, or ``""`` for KEY."""
        if key != self.key:
            return ""
        return "descending" if self.descending else "ascending"

    def pairs(self) -> list[tuple[str, str]]:
        """Return canonical ``sort``/``dir`` query pairs, empty on default."""
        if self.is_default:
            return []
        result = [("sort", self.key)]
        if self.descending:
            result.append(("dir", "desc"))
        return result

    def ordered(self, rows: Sequence[T]) -> list[T]:
        """Return ROWS ordered by the active column, keeping ties stable."""
        column = self._by_key.get(self.key)
        if column is None or column.value is None:
            return list(rows)
        return sort_rows(rows, column.value, descending=self.descending)

    def headers(
        self,
        base_url: str,
        filters: Sequence[tuple[str, str]] = (),
        selected: str = "",
        classes: Mapping[str, str] | None = None,
        extra: Sequence[tuple[str, str]] = (),
    ) -> list[dict[str, Any]]:
        """Build header dictionaries for rendering with ``c-sort-th``."""
        col_classes = classes or {}
        result: list[dict[str, Any]] = []
        for col in self.columns:
            href = (
                f"{base_url}{self.link(col.key, filters, selected, extra)}"
                if col.sortable
                else ""
            )
            result.append({
                "key": col.key,
                "label": col.label,
                "href": href,
                "aria_sort": self.aria_sort(col.key) if col.sortable else "",
                "classes": col_classes.get(col.key, ""),
            })
        return result


def clean_choice(value: str, allowed: Container[str],
                 default: str = "") -> str:
    """Return VALUE when it belongs to ALLOWED, otherwise DEFAULT."""
    return value if value in allowed else default


def sort_rows(rows: Sequence[T], value: Callable[[T], Any],
              descending: bool = False) -> list[T]:
    """Return ROWS ordered by VALUE, reversed when DESCENDING, placing
    rows whose VALUE is None last in their original order; ties keep
    their order."""
    present = [row for row in rows if value(row) is not None]
    present.sort(key=value, reverse=descending)
    return present + [row for row in rows if value(row) is None]


def _parse_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None


def _natural_parts(text: str) -> tuple[tuple[int, Any], ...]:
    parts: list[tuple[int, Any]] = []
    for piece in _DIGIT_RUN_RE.split(text.casefold()):
        if not piece:
            continue
        if piece.isdecimal():
            parts.append((0, int(piece)))
        else:
            parts.append((1, piece))
    return tuple(parts)


def sort_value(shown: Any) -> Any:
    """Return a comparable ordering key for SHOWN, or None when empty.

    Numbers and amounts sort first (plain numbers, then masses in mg,
    then amounts of substance in µmol), then dates and datetimes, then
    case-folded text with digit runs ordered numerically. Empty strings,
    None, and ``"–"`` return None.
    """
    if shown is None:
        return None
    if isinstance(shown, datetime):
        return (1, (shown.year, shown.month, shown.day,
                    shown.hour, shown.minute, shown.second))
    if isinstance(shown, date):
        return (1, (shown.year, shown.month, shown.day, 0, 0, 0))
    if isinstance(shown, (int, float, Decimal)) and not isinstance(
        shown, bool
    ):
        return (0, 0, Decimal(str(shown)))
    text = str(shown).strip()
    if not text or text == "–":
        return None
    if _NUMBER_RE.match(text):
        number = _parse_decimal(text)
        if number is not None:
            return (0, 0, number)
    amount_match = _AMOUNT_RE.match(text)
    if amount_match:
        number = _parse_decimal(amount_match.group(1))
        unit = amount_match.group(2)
        if number is not None:
            if unit in _MASS_FACTORS:
                return (0, 1, number * _MASS_FACTORS[unit])
            if unit in _MOLE_FACTORS:
                return (0, 2, number * _MOLE_FACTORS[unit])
    iso_match = _ISO_DATE_RE.match(text)
    if iso_match:
        y, m, d, hh, mm, ss = iso_match.groups()
        return (1, (int(y), int(m), int(d),
                    int(hh or 0), int(mm or 0), int(ss or 0)))
    de_match = _DE_DATE_RE.match(text)
    if de_match:
        d, m, y, hh, mm, ss = de_match.groups()
        return (1, (int(y), int(m), int(d),
                    int(hh or 0), int(mm or 0), int(ss or 0)))
    return (2, _natural_parts(text))


def amount_sort_key(amount: Decimal | None, unit: str) -> Any:
    """Return a ``sort_value`` key for AMOUNT in UNIT, or None."""
    if amount is None:
        return None
    if unit in _MASS_FACTORS:
        return (0, 1, amount * _MASS_FACTORS[unit])
    if unit in _MOLE_FACTORS:
        return (0, 2, amount * _MOLE_FACTORS[unit])
    return (0, 0, amount)


def format_decimal_key(value: Decimal) -> str:
    """Format VALUE as a plain decimal string without scientific notation."""
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def amount_data_sort(amount: Decimal | None, unit: str) -> str:
    """Return the client ``data-sort`` key (mg or µmol) for AMOUNT in UNIT."""
    if amount is None:
        return ""
    if unit in _MASS_FACTORS:
        return format_decimal_key(amount * _MASS_FACTORS[unit])
    if unit in _MOLE_FACTORS:
        return format_decimal_key(amount * _MOLE_FACTORS[unit])
    return format_decimal_key(amount)


def totals_sort_key(totals: Mapping[str, Decimal]) -> Any:
    """Return a ``sort_value`` key for multi-unit TOTALS.

    Sums masses in mg; when no mass is present, sums amounts of
    substance in µmol. Returns None when TOTALS is empty or zero.
    """
    mass = Decimal(0)
    has_mass = False
    moles = Decimal(0)
    has_moles = False
    for unit, amount in totals.items():
        if not amount:
            continue
        if unit in _MASS_FACTORS:
            mass += amount * _MASS_FACTORS[unit]
            has_mass = True
        elif unit in _MOLE_FACTORS:
            moles += amount * _MOLE_FACTORS[unit]
            has_moles = True
    if has_mass:
        return (0, 1, mass)
    if has_moles:
        return (0, 2, moles)
    return None


def totals_data_sort(totals: Mapping[str, Decimal]) -> str:
    """Return the client ``data-sort`` key for multi-unit TOTALS."""
    key = totals_sort_key(totals)
    if key is None:
        return ""
    return format_decimal_key(key[2])


def pairs_sort_key(pairs: Sequence[tuple[Decimal, str]]) -> Any:
    """Return a ``sort_value`` key for ``(amount, unit)`` PAIRS: as
    ``totals_sort_key`` gives it for the totals per unit, and, for pairs
    whose totals are all zero, the key of a zero mass, or of a zero
    amount of substance when no pair is a mass. Returns None for no
    pairs."""
    totals: dict[str, Decimal] = {}
    for amount, unit in pairs:
        totals[unit] = totals.get(unit, Decimal(0)) + amount
    key = totals_sort_key(totals)
    if key is not None or not totals:
        return key
    return (0, 1 if any(unit in _MASS_FACTORS for unit in totals) else 2,
            Decimal(0))


def pairs_data_sort(pairs: Sequence[tuple[Decimal, str]]) -> str:
    """Return the client ``data-sort`` key for ``(amount, unit)`` PAIRS."""
    key = pairs_sort_key(pairs)
    if key is None:
        return ""
    return format_decimal_key(key[2])


def htmx_list_push_url(request: HttpRequest, response: HttpResponse,
                       canonical_url: str) -> HttpResponse:
    """Set ``HX-Push-Url`` to CANONICAL_URL on RESPONSE for a non-restore
    htmx request, and return RESPONSE."""
    if request.htmx and not request.htmx.history_restore_request:
        response["HX-Push-Url"] = canonical_url
    return response


def list_view(request: HttpRequest, cookie: str,
              default: str = "table") -> str:
    """Return the view remembered in COOKIE (``"table"`` or ``"details"``),
    or DEFAULT when missing or invalid."""
    value = request.COOKIES.get(cookie, "")
    return value if value in ("table", "details") else default


def split_major(request: HttpRequest, cookie: str,
                default: str = "first") -> str:
    """Return the larger side of a list's split remembered in COOKIE
    (``"first"`` or ``"second"``), or DEFAULT when missing or invalid."""
    value = request.COOKIES.get(cookie, "")
    return value if value in ("first", "second") else default


def pick_selected(rows: Sequence[T], wanted: str,
                  key: Callable[[T], Any]) -> tuple[T | None, str]:
    """Select the row in ROWS whose stringified KEY equals WANTED, else
    the first row, else None; return the chosen row and its string key
    (empty when ROWS is empty)."""
    for row in rows:
        row_key = str(key(row))
        if row_key == wanted:
            return row, row_key
    if not rows:
        return None, ""
    return rows[0], str(key(rows[0]))


def detail_query(request: HttpRequest,
                 keep_query: bool = False) -> QueryDict:
    """Return a mutable query for a list detail request.

    Use the same-host HTMX current URL when available. Otherwise, copy
    the request query if KEEP_QUERY is set, or return an empty query.
    """
    current = request.htmx.current_url if request.htmx else None
    if current and url_has_allowed_host_and_scheme(
            current, {request.get_host()}, request.is_secure()):
        return QueryDict(urlsplit(current).query, mutable=True)
    return request.GET.copy() if keep_query else QueryDict(mutable=True)


def htmx_detail_or_redirect(
    request: HttpRequest,
    base_url: str,
    selected: Any,
    template: str,
    context_fn: Callable[[], dict[str, Any]],
    keep_query: bool = False,
    extra: Sequence[tuple[str, str | None]] = (),
) -> HttpResponse:
    """Answer a list detail request with a pane or redirect.

    Both responses name SELECTED at BASE_URL and apply EXTRA query
    pairs. A None value drops a parameter. KEEP_QUERY controls the
    fallback query when no same-host HTMX current URL is available.
    For HTMX, render TEMPLATE with CONTEXT_FN() and set
    ``HX-Replace-Url``. Otherwise, redirect to the list URL.
    """
    params = detail_query(request, keep_query)
    params["selected"] = str(selected)
    for name, value in extra:
        params.pop(name, None)
        if value is not None:
            params[name] = value
    address = f"{base_url}?{params.urlencode()}"
    if not request.htmx:
        return redirect(address)
    response = render(request, template, context_fn())
    response["HX-Replace-Url"] = address
    return response
