"""Template filters of the inventory's pages."""

from decimal import Decimal
from django import template
from django.utils.formats import number_format

from inventory.models import Level, Lot, plain, shown

register = template.Library()


@register.filter
def decimal(value: Decimal | None) -> str:
    """Return VALUE as a number of the active language without trailing
    zeros, or nothing for None."""
    return "" if value is None else number_format(plain(Decimal(value)))


@register.filter
def in_lot_unit(amount: Decimal, lot: Lot) -> str:
    """Return AMOUNT, kept in the base unit of LOT, in the lot's unit,
    rounded half up to three places, with the unit."""
    return f"{number_format(shown(amount, lot.unit))} {lot.unit_label}"


@register.filter
def level_label(value: str | None) -> str:
    """Return the label of the level VALUE in the active language, or
    nothing for no level."""
    return str(Level(value).label) if value else ""

