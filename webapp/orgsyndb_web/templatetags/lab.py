"""Template tags of the lab application's pages."""

from typing import Any

from django import template
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _

register = template.Library()


def not_in_collection(text: str) -> SafeString:
    """Return TEXT followed by the mark of a name the collection
    lacks."""
    return format_html('{} <span class="lab-mark">({})</span>', text,
                       _("not in the collection"))


@register.simple_tag
def marked(text: str) -> SafeString:
    """Return TEXT as HTML, followed by the mark of a name the
    collection lacks."""
    return not_in_collection(text)


@register.simple_tag
def substance(found: Any) -> SafeString:
    """Return the substance FOUND as HTML: its name in the active
    language, linking to its page in the registry."""
    return format_html('<a href="/lab/registry/substances/{}/">{}</a>',
                       found.key, found.shown_name)


@register.inclusion_tag("registry/substance_datalist.html")
def substance_datalist() -> dict[str, Any]:
    """Return the context of the datalist that offers every substance's
    key labelled with its name in the active language."""
    from registry.models import Substance
    return {"substances": Substance.objects.order_by("key")}


@register.simple_tag
def procedure(ident: str, known: bool) -> SafeString:
    """Return the procedure IDENT as HTML: a link to its page when KNOWN,
    else IDENT with the mark of a name the collection lacks."""
    if not known:
        return not_in_collection(ident)
    return format_html('<a href="/procedures/{}/">{}</a>', ident.lower(),
                       ident)


@register.simple_tag
def sequence(ident: str, known: bool) -> SafeString:
    """Return the sequence IDENT as HTML: a link to its page when KNOWN,
    else IDENT with the mark of a name the collection lacks."""
    if not known:
        return not_in_collection(ident)
    return format_html('<a href="/sequences/{}/">{}</a>', ident.lower(),
                       ident)


@register.simple_tag
def person(user: Any) -> SafeString:
    """Return USER's initials with the display name as title, or nothing
    for no user."""
    if user is None:
        return mark_safe("")
    return format_html('<abbr title="{}">{}</abbr>', user.display_name,
                       user.initials)


@register.filter
def yes_no(value: bool) -> str:
    """Return ``yes`` or ``no`` in the active language."""
    return _("yes") if value else _("no")
