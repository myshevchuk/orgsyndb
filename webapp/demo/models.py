"""The demo mark, which makes a database a demo database."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class DemoMark(models.Model):
    """The mark the demo data set leaves in the database it fills.

    A database holding a mark is a demo database: its records are
    invented, and its pages say so. SEEDED_ON is the day the data set
    was written as of.
    """

    seeded_on = models.DateField(_("Seeded on"))

    class Meta:
        verbose_name = _("demo mark")
        verbose_name_plural = _("demo marks")

    def __str__(self) -> str:
        return f"{_('Demo data')} {self.seeded_on.isoformat()}"


def current() -> DemoMark | None:
    """Return the demo mark of the database, or None when it holds
    none."""
    return DemoMark.objects.order_by("pk").first()
