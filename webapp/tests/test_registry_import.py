"""Tests of ``manage.py registry_import`` (lab-registry: Importing a
collection's registry)."""

import io
import re
import tempfile
import tomllib
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from inventory.models import Article
from registry.models import Substance
from vocabulary.models import ChemicalClass, Group, Project, ReactionType

from . import IndexMixin, make_substance
from .registry_support import OLD_LAYOUT

VOCABULARY_FILES = {
    "chemical-classes": ChemicalClass, "inventory-groups": Group,
    "projects": Project, "reaction-types": ReactionType}
CLASSES = 'label = "Classes"\n'
SIMPLE_VOCABULARIES = {
    "chemical-classes": '[ketones]\nlabel = "Ketones"\nlabel_de = '
                        '"Ketone"\n',
    "inventory-groups": '[purchased]\nlabel = "Purchased"\n\n'
                        '[reagents]\nlabel = "Reagents"\n'
                        'parent = "purchased"\n',
    "projects": '[teaching]\nlabel = "Teaching"\n',
    "reaction-types": '[acylation]\nlabel = "Acylation"\n',
}
ACETONE = '''name = "Acetone"
name_de = "Aceton"
formula = "C3H6O"
mw = 58.08
smiles = "CC(C)=O"
cas = "67-64-1"
short_name = "Ac"
item_number = "CH-0099"
chemical_class = ["ketones"]
group = "reagents"
'''


def run(collection: Path) -> tuple[str, str]:
    """Run ``registry_import`` on ``collection``; return its output and
    its errors. A ``CommandError`` propagates."""
    out, err = io.StringIO(), io.StringIO()
    call_command("registry_import", str(collection), stdout=out,
                 stderr=err)
    return out.getvalue(), err.getvalue()


def counts() -> tuple[int, int, int]:
    return (sum(model.objects.count()
                for model in VOCABULARY_FILES.values()),
            Substance.objects.count(), Article.objects.count())


class ImportCase(IndexMixin, TestCase):

    def setUp(self) -> None:
        self.use_index(None)
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def collection(self, compounds: dict[str, str] | None = None,
                   vocabularies: dict[str, str] | None = None) -> Path:
        """A collection directory with ``vocabularies`` (by name,
        ``SIMPLE_VOCABULARIES`` by default) and ``compounds`` (by key,
        ``acetone`` by default)."""
        (self.root / "vocabularies").mkdir(exist_ok=True)
        (self.root / "compounds").mkdir(exist_ok=True)
        for name, text in (SIMPLE_VOCABULARIES if vocabularies is None
                           else vocabularies).items():
            (self.root / "vocabularies" / f"{name}.toml").write_text(
                text, encoding="utf-8")
        for key, text in ({"acetone": ACETONE} if compounds is None
                          else compounds).items():
            (self.root / "compounds" / f"{key}.toml").write_text(
                text, encoding="utf-8")
        return self.root

    def refused(self, collection: Path) -> CommandError:
        """The import fails with a message and loads nothing."""
        before = counts()
        with self.assertRaises(CommandError) as caught:
            run(collection)
        self.assertTrue(str(caught.exception).strip())
        self.assertEqual(caught.exception.returncode, 1)
        self.assertEqual(counts(), before)
        return caught.exception


class OldLayoutTests(ImportCase):
    """A collection in the layout collections had before they named a
    registry: ``tests/fixtures/old-layout/``."""

    def test_a_collection_in_the_old_layout(self) -> None:
        """Scenario: A collection in the old layout."""
        _out, err = run(OLD_LAYOUT)
        compounds = sorted(
            path.stem for path in (OLD_LAYOUT / "compounds").glob(
                "*.toml"))
        self.assertEqual(len(compounds), 20)
        self.assertEqual(
            sorted(Substance.objects.values_list("key", flat=True)),
            compounds)
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual(found.group.key, "final-products")
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"carboxylic-acids"})
        self.assertEqual(found.article.article_number, "CH-0012")
        self.assertIn("in_house", err)
        self.assertIn("stock", err)

    def test_the_numbered_compounds_get_articles(self) -> None:
        run(OLD_LAYOUT)
        self.assertEqual(
            dict(Article.objects.values_list("substance__key",
                                             "article_number")), {
                "1-4-bromophenyl-ethanol": "CH-0001",
                "1-biphenyl-4-yl-ethanol": "CH-0002",
                "acetylsalicylic-acid": "CH-0010",
                "cinnamic-acid": "CH-0012",
                "dibenzylideneacetone": "CH-0013",
                "isopentyl-acetate": "CH-0016"})

    def test_every_term_of_the_vocabulary_files(self) -> None:
        run(OLD_LAYOUT)
        for name, model in VOCABULARY_FILES.items():
            path = OLD_LAYOUT / "vocabularies" / f"{name}.toml"
            with path.open("rb") as handle:
                wanted = tomllib.load(handle)
            with self.subTest(vocabulary=name):
                self.assertEqual(
                    {term.key: (term.label, term.label_de or None,
                                term.parent.key if getattr(
                                    term, "parent", None) else None)
                     for term in model.objects.all()},
                    {key: (value["label"], value.get("label_de"),
                           value.get("parent"))
                     for key, value in wanted.items()})

    def test_a_compounds_values(self) -> None:
        run(OLD_LAYOUT)
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual(
            (found.name, found.name_de, found.formula, str(found.mw),
             found.smiles, found.cas),
            ("(E)-Cinnamic acid", "(E)-Zimtsäure", "C9H8O2", "148.160",
             "OC(=O)/C=C/c1ccccc1", "140-10-3"))

    def test_the_warning_counts_the_compounds_that_set_each_key(
            self) -> None:
        _out, err = run(OLD_LAYOUT)
        for key, count in (("in_house", 19), ("stock", 9),
                           ("structure_image", 1)):
            with self.subTest(key=key):
                self.assertRegex(err, rf"{key}\D{{0,12}}{count}(?!\d)")

    def test_the_declared_fields_are_not_warned_about(self) -> None:
        _out, err = run(OLD_LAYOUT)
        for key in ("short_name", "chemical_class", "group",
                    "item_number", "formula", "mw", "smiles"):
            with self.subTest(key=key):
                self.assertNotRegex(err, rf"(?<![\w-]){key}(?![\w-])")

    def test_the_printed_counts(self) -> None:
        out, _err = run(OLD_LAYOUT)
        terms, substances, articles = counts()
        for number in (terms, substances, articles):
            with self.subTest(number=number):
                self.assertRegex(out, rf"(?<![\d.,]){number}(?![\d.,]\d)")


class SmallCollectionTests(ImportCase):

    def test_a_compound(self) -> None:
        run(self.collection())
        found = Substance.objects.get()
        self.assertEqual(
            (found.key, found.name, found.name_de, found.short_name,
             found.formula, str(found.mw), found.smiles, found.cas,
             found.group.key, found.article.article_number),
            ("acetone", "Acetone", "Aceton", "Ac", "C3H6O", "58.080",
             "CC(C)=O", "67-64-1", "reagents", "CH-0099"))
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"ketones"})
        self.assertEqual(Group.objects.get(key="reagents").parent,
                         Group.objects.get(key="purchased"))

    def test_without_a_warning_nothing_is_written_to_stderr(self) -> None:
        _out, err = run(self.collection())
        self.assertEqual(err.strip(), "")

    def test_the_other_keys_are_named_once_with_their_counts(self) -> None:
        compounds = {
            "acetone": ACETONE + 'in_house = true\nstock = 5\n',
            "ethanol": ACETONE.replace("CH-0099", "CH-0098").replace(
                "67-64-1", "64-17-5") + 'in_house = false\n'}
        _out, err = run(self.collection(compounds))
        self.assertRegex(err, r"in_house\D{0,12}2(?!\d)")
        self.assertRegex(err, r"stock\D{0,12}1(?!\d)")
        self.assertEqual(len(re.findall(r"in_house", err)), 1)
        self.assertEqual(len(re.findall(r"stock", err)), 1)

    def test_a_compound_without_an_item_number_has_no_article(self) -> None:
        run(self.collection({
            "acetone": ACETONE.replace('item_number = "CH-0099"\n', "")}))
        self.assertEqual(Article.objects.count(), 0)
        self.assertEqual(Substance.objects.count(), 1)

    def test_optional_values_may_be_missing(self) -> None:
        run(self.collection({"plain": '''name = "Plain"
chemical_class = ["ketones"]
group = "reagents"
'''}))
        found = Substance.objects.get()
        self.assertIsNone(found.mw)
        self.assertFalse(found.cas or found.formula or found.name_de)

    def test_a_missing_vocabulary_file_is_an_empty_vocabulary(self) -> None:
        vocabularies = dict(SIMPLE_VOCABULARIES)
        del vocabularies["projects"]
        del vocabularies["reaction-types"]
        run(self.collection(vocabularies=vocabularies))
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(ReactionType.objects.count(), 0)
        self.assertEqual(Substance.objects.count(), 1)

    def test_a_registry_that_holds_records_is_refused(self) -> None:
        make_substance("existing")
        self.refused(self.collection())
        self.assertEqual(Substance.objects.count(), 1)


class RefusalTests(ImportCase):

    def test_a_compound_without_a_group(self) -> None:
        text = ACETONE.replace('group = "reagents"\n', "")
        error = self.refused(self.collection({"acetone": text}))
        self.assertIn("acetone", str(error))

    def test_a_compound_without_a_chemical_class(self) -> None:
        text = ACETONE.replace('chemical_class = ["ketones"]\n', "")
        error = self.refused(self.collection({"acetone": text}))
        self.assertIn("acetone", str(error))

    def test_an_empty_list_of_chemical_classes(self) -> None:
        text = ACETONE.replace('["ketones"]', "[]")
        self.refused(self.collection({"acetone": text}))

    def test_a_file_that_cannot_be_read(self) -> None:
        error = self.refused(self.collection({
            "acetone": ACETONE, "broken": "name = [unclosed\n"}))
        self.assertIn("broken", str(error))

    def test_nothing_is_loaded_when_a_later_file_fails(self) -> None:
        text = ACETONE.replace('group = "reagents"\n', "")
        self.refused(self.collection({"acetone": ACETONE, "zinc": text}))
        self.assertEqual(counts(), (0, 0, 0))

    def test_an_unreadable_vocabulary_file(self) -> None:
        vocabularies = dict(SIMPLE_VOCABULARIES)
        vocabularies["projects"] = "[teaching\nlabel = \n"
        error = self.refused(self.collection(vocabularies=vocabularies))
        self.assertIn("projects", str(error))

    def test_a_group_the_vocabulary_lacks(self) -> None:
        text = ACETONE.replace('"reagents"', '"no-such-group"')
        self.refused(self.collection({"acetone": text}))
