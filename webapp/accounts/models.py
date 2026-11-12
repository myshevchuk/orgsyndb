"""The application's user model."""

from typing import Any

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from orgsyndb_web import lock
from orgsyndb_web.lock import LockedQuerySet


USER_NAME = r"\A[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*\Z"


# The fields of an account the registry snapshot carries, as its user
# name and its name.
SNAPSHOT_FIELDS = frozenset({"username", "first_name", "last_name"})


class AccountManager(UserManager.from_queryset(LockedQuerySet)):
    """Django's manager of users, whose bulk writes take the import
    lock as ``LockedQuerySet`` states."""


class User(AbstractUser):
    """A person who signs in or is named on records.

    USERNAME is at most 40 ASCII letters and digits, with single ``.``,
    ``-`` or ``_`` between them, the user names Forgejo accepts.
    Procedure files name their authors by it, so the admin offers no way
    to change it once the account exists. INITIALS, one to five letters
    or digits, name the user in lists; they are stored in upper case and
    unique regardless of case. An account without a usable password
    cannot sign in and can still be named on records.
    """

    username = models.CharField(
        _("username"), max_length=40, unique=True,
        validators=[RegexValidator(
            USER_NAME,
            _("Enter at most 40 letters or digits, with single dots, "
              "hyphens or underscores between them."))],
        help_text=_("At most 40 letters or digits, with single dots, "
                    "hyphens or underscores between them. It cannot be "
                    "changed later."),
        error_messages={
            "unique": _("A user with that username already exists.")})
    initials = models.CharField(
        _("initials"), max_length=5, unique=True,
        validators=[RegexValidator(
            r"^[A-Za-z0-9]{1,5}$",
            _("Enter one to five letters or digits."))],
        help_text=_("One to five letters or digits, shown in lists."),
        error_messages={"unique": _("Another account has these initials.")})

    REQUIRED_FIELDS = ["email", "initials"]

    objects = AccountManager()

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    @property
    def display_name(self) -> str:
        """The full name, or the user name when the full name is
        empty."""
        return self.get_full_name() or self.get_username()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the account with its initials in upper case, under the
        import lock (``orgsyndb_web.lock``), since the registry
        snapshot's digest covers its user name and name; a save of only
        other fields, such as a sign-in's ``last_login``, takes no
        lock."""
        self.initials = (self.initials or "").upper()
        fields = kwargs.get("update_fields")
        if fields is not None and not SNAPSHOT_FIELDS & set(fields):
            super().save(*args, **kwargs)
            return
        with transaction.atomic():
            lock.hold()
            super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Delete the account, as ``Model.delete`` does, under the
        import lock; return what it returns."""
        with transaction.atomic():
            lock.hold()
            return super().delete(*args, **kwargs)

    def clean(self) -> None:
        """Normalize the account as ``AbstractUser.clean`` does, and
        put the initials in upper case."""
        super().clean()
        self.initials = (self.initials or "").upper()
