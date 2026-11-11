"""Fixtures and helpers shared by the registry tests.

Nothing here imports the ``registry`` or ``vocabulary`` packages at
module level, so a test that uses these helpers fails on its own
assertions while the packages are missing.
"""

import io
import json
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from . import (DEMO_REGISTRY, REPO, IndexMixin, make_article, make_class,
               make_group, make_substance, make_user, parse)

REGISTRY = "/lab/registry/"
SNAPSHOT = REGISTRY + "snapshot.json"
NEW_SUBSTANCE = REGISTRY + "substances/new/"
VOCABULARIES = {
    "chemical-classes": ("Stoffklassen", "Chemical classes"),
    "groups": ("Gruppen", "Groups"),
    "projects": ("Projekte", "Projects"),
    "reaction-types": ("Reaktionstypen", "Reaction types"),
}
DEMO_COLLECTION = REPO / "examples" / "demo"


def substance_url(key: str, action: str = "") -> str:
    return f"{REGISTRY}substances/{key}/" + (f"{action}/" if action else "")


def term_url(vocabulary: str, key: str | None = None,
             action: str = "") -> str:
    """The page of a vocabulary, or of its term ``key`` with ``action``
    (``edit``), or ``new`` for the new-term form when ``key`` is
    ``new``."""
    path = f"{REGISTRY}{vocabulary}/"
    if key is not None:
        path += f"{key}/"
    if action:
        path += f"{action}/"
    return path


def vocabulary_model(vocabulary: str) -> Any:
    """The model of the vocabulary whose URL name is ``vocabulary``."""
    from vocabulary.models import (ChemicalClass, Group, Project,
                                   ReactionType)
    return {"chemical-classes": ChemicalClass, "groups": Group,
            "projects": Project, "reaction-types": ReactionType
            }[vocabulary]


def choice_value(root: Any, field: str, term: Any) -> str:
    """The value that the control ``field`` of a page, a select or a
    group of check boxes, submits for ``term``, which it offers by
    primary key or by key."""
    wanted = {str(term.pk), term.key}
    select = root.find("select", name=field)
    candidates = (select.find_all("option") if select is not None
                  else root.find_all("input", name=field))
    for candidate in candidates:
        if candidate.get("value") in wanted:
            return candidate.get("value")
    raise AssertionError(f"the page offers {term.key} at no {field}")


def offered(root: Any, field: str) -> list[Any]:
    """The elements, options or check boxes, that offer a choice at
    ``field``, without an empty one."""
    select = root.find("select", name=field)
    found = (select.find_all("option") if select is not None
             else root.find_all("input", name=field))
    return [e for e in found if e.get("value")]


def build_registry() -> dict[str, Any]:
    """A small registry: two trees of groups and classes, and three
    substances, one of them with an article."""
    make_group("purchased", "Purchased", label_de="Zugekauft")
    make_group("reagents", "Reagents", make_group("purchased"),
               label_de="Reagenzien")
    make_group("starting-materials", "Starting materials",
               make_group("purchased"), label_de="Ausgangsstoffe")
    make_group("synthesised", "Synthesised", label_de="Selbst hergestellt")
    make_group("intermediates", "Intermediates", make_group("synthesised"),
               label_de="Zwischenprodukte")
    make_group("final-products", "Final products",
               make_group("synthesised"), label_de="Endprodukte")
    make_class("carbonyl-compounds", "Carbonyl compounds",
               label_de="Carbonylverbindungen")
    make_class("carboxylic-acids", "Carboxylic acids",
               make_class("carbonyl-compounds"), label_de="Carbonsäuren")
    make_class("ketones", "Ketones", make_class("carbonyl-compounds"),
               label_de="Ketone")
    make_class("aryl-ketones", "Aryl ketones", make_class("ketones"),
               label_de="Arylketone")
    cinnamic = make_substance(
        "cinnamic-acid", "(E)-Cinnamic acid", name_de="(E)-Zimtsäure",
        short_name="ZS", group=make_group("final-products"),
        classes=["carboxylic-acids"], formula="C9H8O2", mw="148.16",
        smiles="OC(=O)/C=C/c1ccccc1", cas="140-10-3", note="Notiz")
    make_article(cinnamic, "CH-0012")
    acetophenone = make_substance(
        "acetophenone", "Acetophenone", group=make_group("intermediates"),
        classes=["aryl-ketones"])
    bare = make_substance("new-compound-7", "New compound 7",
                          group=make_group("intermediates"))
    return {"cinnamic": cinnamic, "acetophenone": acetophenone,
            "bare": bare}


class RegistryCase(IndexMixin, TestCase):
    """A test case with two accounts and ``build_registry``'s records
    in its database; the index is none unless a test sets one."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.records = build_registry()

    def setUp(self) -> None:
        self.use_index(None)

    def get(self, path: str, signed_in: bool = False) -> Any:
        """The parsed page ``path``, which answers 200."""
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return parse(response.content.decode("utf-8"))


def load(path: Path | str, *args: str) -> tuple[str, str]:
    """Run ``registry_load`` on ``path``; return its output and its
    errors. A ``CommandError`` propagates."""
    out, err = io.StringIO(), io.StringIO()
    call_command("registry_load", str(path), *args, stdout=out,
                 stderr=err)
    return out.getvalue(), err.getvalue()


def load_refused(path: Path | str) -> CommandError:
    """The ``CommandError`` ``registry_load`` raises for ``path``."""
    try:
        load(path)
    except CommandError as error:
        return error
    raise AssertionError("registry_load did not refuse the file")


def write_json(directory: Path, data: Any, name: str = "registry.json"
               ) -> Path:
    """Write ``data`` as JSON to ``name`` in ``directory``."""
    path = directory / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def demo_registry() -> dict[str, Any]:
    """The demo registry file as data."""
    return json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))


def without_digest(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in snapshot.items()
            if key != "digest"}


def small_snapshot() -> dict[str, Any]:
    """A snapshot of a few terms and substances, valid for
    ``registry_load``."""
    return {
        "format": 1,
        "vocabularies": {
            "chemical-classes": [
                {"key": "carbonyl-compounds", "label": "Carbonyl compounds",
                 "label_de": "Carbonylverbindungen", "parent": None},
                {"key": "ketones", "label": "Ketones", "label_de": None,
                 "parent": "carbonyl-compounds"}],
            "inventory-groups": [
                {"key": "reagents", "label": "Reagents",
                 "label_de": "Reagenzien", "parent": None}],
            "projects": [
                {"key": "teaching", "label": "Teaching", "label_de": None,
                 "parent": None}],
            "reaction-types": [
                {"key": "acylation", "label": "Acylation",
                 "label_de": "Acylierung"}]},
        "substances": [
            {"key": "acetone", "name": "Acetone", "name_de": "Aceton",
             "short_name": None, "group": "reagents",
             "chemical_classes": ["ketones"], "formula": "C3H6O",
             "mw": 58.08, "smiles": "CC(C)=O", "cas": "67-64-1",
             "note": None, "article_number": "CH-0099"},
            {"key": "mystery", "name": "Mystery", "name_de": None,
             "short_name": None, "group": "reagents",
             "chemical_classes": ["carbonyl-compounds", "ketones"],
             "formula": None, "mw": None, "smiles": None, "cas": None,
             "note": None, "article_number": None}]}


def wipe_registry() -> None:
    """Delete every substance, article and term, the terms leaves
    first."""
    from django.db.models import ProtectedError
    from inventory.models import Article
    from registry.models import Substance, SubstanceClass
    from vocabulary.models import (ChemicalClass, Group, Project,
                                   ReactionType)
    SubstanceClass.objects.all().delete()
    Article.objects.all().delete()
    Substance.objects.all().delete()
    for model in (ChemicalClass, Group, Project, ReactionType):
        while model.objects.exists():
            for term in model.objects.all():
                try:
                    term.delete()
                except ProtectedError:
                    continue
