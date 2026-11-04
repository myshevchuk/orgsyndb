"""The application's user model."""

from typing import Any

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """A person who signs in or is named on records.

    INITIALS, one to five letters or digits, name the user in lists;
    they are stored in upper case and unique regardless of case. An
    account without a usable password cannot sign in and can still be
    named on records.
    """

    initials = models.CharField(
        _("initials"), max_length=5, unique=True,
        validators=[RegexValidator(
            r"^[A-Za-z0-9]{1,5}$",
            _("Enter one to five letters or digits."))],
        help_text=_("One to five letters or digits, shown in lists."),
        error_messages={"unique": _("Another account has these initials.")})

    REQUIRED_FIELDS = ["email", "initials"]

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    @property
    def display_name(self) -> str:
        """The full name, or the user name when the full name is
        empty."""
        return self.get_full_name() or self.get_username()

    def clean(self) -> None:
        """Normalize the account as ``AbstractUser.clean`` does, and
        put the initials in upper case."""
        super().clean()
        self.initials = (self.initials or "").upper()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the account with its initials in upper case."""
        self.initials = (self.initials or "").upper()
        super().save(*args, **kwargs)
