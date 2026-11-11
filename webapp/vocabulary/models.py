"""The vocabularies: chemical classes, groups and projects, each a tree of
terms, and reaction types, a flat list.

Every term has a fixed KEY and a label in English and, optionally, in
German. A term of a tree may be filed under a PARENT of its own
vocabulary, never under itself or under a term filed under it. A term
that a substance or another term refers to cannot be deleted.
"""

from collections.abc import Iterable
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from orgsyndb_web.history import RecordedHistory
from orgsyndb_web.lock import LockedQuerySet, LockedWrites

KEY_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
key_rule = RegexValidator(
    KEY_PATTERN, _("Enter lower-case letters and digits, joined by single "
                   "hyphens, such as carboxylic-acids."))


def german() -> bool:
    """Whether the active language is German."""
    return (get_language() or "").startswith("de")


class Term(LockedWrites, models.Model):
    """A term of a vocabulary: its KEY, its LABEL on an English site and
    LABEL_DE on a German one. Its saves and deletions take the lock
    (``orgsyndb_web.lock``)."""

    objects = LockedQuerySet.as_manager()

    key = models.CharField(_("Key"), max_length=50, unique=True,
                           validators=[key_rule])
    label = models.CharField(_("Label"), max_length=100)
    label_de = models.CharField(_("German label"), max_length=100,
                                blank=True)

    class Meta:
        abstract = True
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key

    @property
    def shown_label(self) -> str:
        """The label in the active language: ``label_de`` on a German
        site when the term has one, else ``label``."""
        return self.label_de if german() and self.label_de else self.label


class TreeTerm(Term):
    """A term that may be filed under a PARENT of its own vocabulary."""

    class Meta(Term.Meta):
        abstract = True

    def clean(self) -> None:
        """Refuse a parent that is the term itself or a term filed under
        it, with the error at ``parent``."""
        if self.parent_id is not None and self.pk is not None \
                and self.parent_id in {self.pk, *(
                    term.pk for term in descendants(self))}:
            raise ValidationError({"parent": _(
                "A term cannot be filed under itself or under a term "
                "filed under it.")})


def tree_parent(model: str) -> models.ForeignKey:
    """Return the optional, protected parent of a term of MODEL."""
    return models.ForeignKey(model, verbose_name=_("Parent"), null=True,
                             blank=True, on_delete=models.PROTECT,
                             related_name="children")


class ChemicalClass(TreeTerm):
    """A chemical class, such as the carboxylic acids, which a substance
    belongs to."""

    parent = tree_parent("self")

    history = RecordedHistory()

    class Meta(TreeTerm.Meta):
        verbose_name = _("chemical class")
        verbose_name_plural = _("chemical classes")


class Group(TreeTerm):
    """A group of the inventory, such as the final products, which a
    substance is filed in."""

    parent = tree_parent("self")

    history = RecordedHistory()

    class Meta(TreeTerm.Meta):
        verbose_name = _("group")
        verbose_name_plural = _("groups")


class Project(TreeTerm):
    """A project of the lab, such as a course it teaches."""

    parent = tree_parent("self")

    history = RecordedHistory()

    class Meta(TreeTerm.Meta):
        verbose_name = _("project")
        verbose_name_plural = _("projects")


class ReactionType(Term):
    """A type of reaction, such as an esterification."""

    history = RecordedHistory()

    class Meta(Term.Meta):
        verbose_name = _("reaction type")
        verbose_name_plural = _("reaction types")


def is_tree(model: type[Term]) -> bool:
    """Whether the terms of MODEL may have a parent."""
    return issubclass(model, TreeTerm)


def tree_order[T: Term](terms: Iterable[T]) -> list[tuple[T, int]]:
    """Return TERMS each with its depth, a parent before the terms filed
    under it and those before its next sibling, siblings in key order.

    A term whose parent is not among TERMS stands at the top, at depth
    zero; flat terms are all at depth zero, in key order.
    """
    every = list(terms)
    known = {term.pk for term in every}
    children: dict[Any, list[T]] = {}
    for term in every:
        parent = getattr(term, "parent_id", None)
        children.setdefault(parent if parent in known else None,
                            []).append(term)
    found: list[tuple[T, int]] = []

    def visit(parent: Any, depth: int) -> None:
        for term in sorted(children.get(parent, []),
                           key=lambda each: each.key):
            found.append((term, depth))
            visit(term.pk, depth + 1)

    visit(None, 0)
    return found


def descendants(term: TreeTerm) -> list[TreeTerm]:
    """Return the terms filed under TERM, at any depth."""
    model = type(term)
    pairs = dict(model.objects.values_list("pk", "parent_id"))
    found: list[Any] = []
    frontier = {term.pk}
    while frontier:
        below = {pk for pk, parent in pairs.items() if parent in frontier
                 and pk not in found and pk != term.pk}
        found += sorted(below)
        frontier = below
    return list(model.objects.filter(pk__in=found))
