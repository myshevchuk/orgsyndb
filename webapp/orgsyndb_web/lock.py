"""The one lock that serializes imports of the collection and the writes
that change the registry snapshot's digest.

The digest covers the substances, their chemical classes, the terms of
the four vocabularies and the articles' numbers. Every write of those
rows takes the lock in the transaction that writes, and so does the
manifest view while it checks and applies an import, so that an import
is checked against the registry it is applied to.
"""

from typing import Any

from django.db import connection, models, transaction
from django.db.transaction import TransactionManagementError

# The key of the PostgreSQL advisory lock, a fixed 64-bit integer: the
# ASCII bytes of "orgsyndb".
KEY = int.from_bytes(b"orgsyndb")


def hold() -> None:
    """Take the lock inside the current transaction of the default
    database; it is released when that transaction ends.

    On PostgreSQL this waits for ``pg_advisory_xact_lock`` with the
    fixed ``KEY``; on SQLite, which lets one writer in at a time, it does
    nothing. Raise TransactionManagementError when no transaction is
    open, that is, with autocommit on.
    """
    if not connection.in_atomic_block:
        raise TransactionManagementError(
            "the lock is held only inside a transaction")
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [KEY])


class LockedWrites:
    """A mixin for a model whose rows the snapshot's digest covers: its
    ``save`` and ``delete`` open a transaction, or join the current one,
    and take the lock before they write."""

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the record, as ``Model.save`` does, under the lock."""
        with transaction.atomic():
            hold()
            super().save(*args, **kwargs)  # type: ignore[misc]

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Delete the record, as ``Model.delete`` does, under the lock;
        return what it returns."""
        with transaction.atomic():
            hold()
            return super().delete(*args, **kwargs)  # type: ignore[misc]


class LockedQuerySet(models.QuerySet):
    """The queryset of a model whose rows the snapshot's digest covers:
    its bulk writes, ``update``, ``delete`` and ``bulk_create``, take the
    lock in their transaction as ``LockedWrites`` does for one record.
    The admin's deletion of selected rows and a many-to-many ``set``
    write through these."""

    def update(self, **kwargs: Any) -> int:
        """Update the rows, as ``QuerySet.update`` does, under the lock;
        return the number of rows matched."""
        with transaction.atomic(using=self.db):
            hold()
            return super().update(**kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:
        """Delete the rows, as ``QuerySet.delete`` does, under the lock;
        return what it returns."""
        with transaction.atomic(using=self.db):
            hold()
            return super().delete()

    def bulk_create(self, objs: Any, *args: Any, **kwargs: Any) -> Any:
        """Create the records, as ``QuerySet.bulk_create`` does, under
        the lock; return what it returns."""
        with transaction.atomic(using=self.db):
            hold()
            return super().bulk_create(objs, *args, **kwargs)
