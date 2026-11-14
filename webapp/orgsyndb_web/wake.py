"""Waking the builder after a transaction that wrote a row the registry
snapshot's digest covers (collection-import "Wake-up after a registry
write").

``after_commit`` registers one wake-up for the current transaction of the
default database. When the transaction commits, the wake-up posts to
``ORGSYNDB_WAKE_URL`` with ``Authorization: Bearer
<ORGSYNDB_BUILDER_TOKEN>`` before the committing call returns, and logs a
failure as a warning. A
transaction that is rolled back sends nothing, and a registration made
inside a savepoint that is rolled back is dropped with it.
"""

import http.client
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.db import connection, transaction

log = logging.getLogger(__name__)

# Seconds the wake-up waits for the builder's answer.
TIMEOUT = 2


def send(url: str, token: str) -> None:
    """Post an empty body to URL with TOKEN as the bearer token, waiting
    at most ``TIMEOUT`` seconds; log a warning, and never raise, when URL
    is malformed, there is no answer or its status is not 202."""
    try:
        request = urllib.request.Request(
            url, b"", {"Authorization": f"Bearer {token}"}, method="POST")
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            status = answer.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except (OSError, ValueError, http.client.HTTPException) as exc:
        log.warning("The builder was not woken at %s: %s", url, exc)
        return
    if status != 202:
        log.warning("The builder was not woken at %s: it answered %s",
                    url, status)


def _wake() -> None:
    """Wake the builder (``send``) when ``ORGSYNDB_WAKE_URL`` is set; do
    nothing otherwise."""
    url = settings.ORGSYNDB_WAKE_URL
    if url:
        send(url, settings.ORGSYNDB_BUILDER_TOKEN)


def after_commit() -> None:
    """Wake the builder once after the current transaction of the default
    database commits, however often it is called in that transaction.

    The wake-up is sent only when ``ORGSYNDB_WAKE_URL`` is set when the
    transaction commits, and never raises. Outside a transaction, with
    autocommit on, it is sent at once.
    """
    if any(entry[1] is _wake for entry in connection.run_on_commit):
        return
    transaction.on_commit(_wake)
