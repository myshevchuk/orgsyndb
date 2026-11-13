"""The entry a text names, such as ``AE-2/8``, made when it is first
named (lab-journal "Notebooks and entries")."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from journal.models import ENTRY_RE, Entry, Notebook


def entry_for(text: str) -> Entry:
    """Return the entry TEXT names, ``<code>/<number>``: the entry of
    that number in the notebook of that code, created when the notebook
    has none.

    Two callers that name a new entry at once get the same row, the one
    that inserts it second taking the first's. Raise ValidationError,
    creating nothing, when TEXT is not ``<code>/<number>`` with a number
    from 1 and no leading zero, or when no notebook has the code.
    """
    match = ENTRY_RE.match(text)
    if match is None:
        raise ValidationError(
            _("Enter a lab notebook entry as <code>/<number>, such as "
              "AE-2/8."), code="invalid")
    notebook = Notebook.objects.filter(code=match[1]).first()
    if notebook is None:
        raise ValidationError(
            _("No lab notebook has the code %(code)s.")
            % {"code": match[1]}, code="unknown")
    return Entry.objects.get_or_create(notebook=notebook,
                                       number=int(match[2]))[0]
