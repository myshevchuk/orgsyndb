"""Issuing and adopting procedure and sequence IDs (collection-import
"Issued IDs").

Both take the one lock (``orgsyndb_web.lock``) in their transaction, so
that two requests never get one ID and an import never adopts an ID at
the moment one is issued.
"""

import re
from collections.abc import Iterable
from typing import Any

from django.db import transaction

from collection.models import ISSUED_ID, IssuedId, latest_accepted
from orgsyndb_web import lock

# The prefix of the IDs of each kind.
PREFIXES = {"procedure": "OSDB", "sequence": "SEQ"}
ID_RE = re.compile(ISSUED_ID)
HIGHEST = 9999


class Unavailable(Exception):
    """No ID can be issued now; the message says why."""


def is_id(text: Any, kind: str | None = None) -> bool:
    """Whether TEXT is a procedure or sequence ID, ``OSDB-NNNN`` or
    ``SEQ-NNNN``; with KIND, ``procedure`` or ``sequence``, an ID of
    that kind only."""
    if not isinstance(text, str) or ID_RE.match(text) is None:
        return False
    return kind is None or text.startswith(f"{PREFIXES[kind]}-")


def issue(kind: str, user: Any) -> str:
    """Issue to the account USER the ID of KIND, ``procedure`` or
    ``sequence``, one above the highest issued ID of that kind,
    adopted ones included, and return it; the first is ``0001``.

    Raise Unavailable, issuing nothing, before the application has
    accepted an import, and when the ID ``9999`` of KIND is issued.
    """
    prefix = PREFIXES[kind]
    with transaction.atomic():
        lock.hold()
        if latest_accepted() is None:
            raise Unavailable(
                "no import of the collection has been accepted yet, so "
                "its IDs are not known")
        highest = IssuedId.objects.filter(
            key__startswith=f"{prefix}-").order_by("-key").values_list(
                "key", flat=True).first()
        number = 0 if highest is None else int(highest[-4:])
        if number >= HIGHEST:
            raise Unavailable(f"no {kind} ID is left above "
                              f"{prefix}-{HIGHEST}")
        key = f"{prefix}-{number + 1:04d}"
        IssuedId.objects.create(key=key, user=user)
        return key


def adopt(keys: Iterable[str]) -> list[tuple[str, bool]]:
    """Adopt each ID of KEYS that is not issued, recording it with no
    account; return each key in order with whether it was adopted, an
    ID named twice being adopted the first time. Each key must be an
    ID (``is_id``)."""
    found = []
    with transaction.atomic():
        lock.hold()
        for key in keys:
            _row, made = IssuedId.objects.get_or_create(key=key)
            found.append((key, made))
    return found


def issued(keys: Iterable[str]) -> set[str]:
    """Return those of KEYS that are issued."""
    return set(IssuedId.objects.filter(key__in=set(keys)).values_list(
        "key", flat=True))
