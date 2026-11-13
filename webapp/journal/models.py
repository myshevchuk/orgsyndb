"""The lab journal: the lab's paper notebooks and the numbered entries
in them that procedures and task steps name.

The entries themselves stay on paper; a row records only that an entry
exists, named ``<code>/<number>``. A notebook's CODE is fixed once it
exists. A notebook that an entry belongs to, an entry that a procedure
or a task step names, and an account that a notebook belongs to cannot
be deleted.
"""

import re
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from orgsyndb_web.history import RecordedHistory
from orgsyndb_web.lock import LockedQuerySet, LockedWrites

CODE_LENGTH = 20
CODE_PATTERN = r"[A-Z0-9]+(?:-[A-Z0-9]+)*"
# An entry as text: a notebook's code, a slash and a number from 1 to
# 9999 without a leading zero, such as AE-2/8.
ENTRY_RE = re.compile(rf"\A({CODE_PATTERN})/([1-9][0-9]{{0,3}})\Z")

code_rule = RegexValidator(
    rf"\A{CODE_PATTERN}\Z",
    _("Enter upper-case letters and digits, joined by single hyphens, "
      "such as AE-2."))


class Notebook(LockedWrites, models.Model):
    """A paper notebook of the lab: its CODE, as written on its cover;
    USER, the account whose notebook it is; and a NOTE.

    The registry snapshot lists the notebooks, so their saves and
    deletions take the lock (``orgsyndb_web.lock``).
    """

    objects = LockedQuerySet.as_manager()

    code = models.CharField(
        _("Code"), max_length=CODE_LENGTH, unique=True,
        validators=[code_rule],
        help_text=_("As written on the cover, such as AE-2. It cannot be "
                    "changed later."),
        error_messages={"unique": _("Another lab notebook has this "
                                    "code.")})
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("Owner"),
                             on_delete=models.PROTECT,
                             related_name="notebooks")
    note = models.TextField(_("Note"), blank=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["code"]
        verbose_name = _("lab notebook")
        verbose_name_plural = _("lab notebooks")

    def __str__(self) -> str:
        return self.code

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the notebook, as ``Model.save`` does, under the lock.

        Raise ValidationError, at ``code``, when the notebook exists and
        its code differs from the stored one; nothing is written then.
        """
        if self.pk is not None:
            stored = type(self).objects.filter(pk=self.pk).values_list(
                "code", flat=True).first()
            if stored is not None and stored != self.code:
                raise ValidationError({"code": _(
                    "The code of a lab notebook cannot be changed.")})
        super().save(*args, **kwargs)


class Entry(models.Model):
    """An entry of a notebook, by its NUMBER from 1, unique within the
    notebook; written ``<code>/<number>``, such as ``AE-2/8``."""

    notebook = models.ForeignKey(Notebook, verbose_name=_("lab notebook"),
                                 on_delete=models.PROTECT,
                                 related_name="entries")
    number = models.PositiveIntegerField(
        _("Number"), validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["notebook__code", "number"]
        verbose_name = _("lab notebook entry")
        verbose_name_plural = _("lab notebook entries")
        constraints = [
            models.UniqueConstraint(fields=["notebook", "number"],
                                    name="journal_entry_once"),
            models.CheckConstraint(condition=Q(number__gte=1),
                                   name="journal_entry_number"),
        ]

    def __str__(self) -> str:
        return f"{self.notebook.code}/{self.number}"
