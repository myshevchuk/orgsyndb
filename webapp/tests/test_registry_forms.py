"""Tests of the registry's forms (lab-registry: Registry forms)."""

from decimal import Decimal
from typing import Any

from registry.models import Substance, SubstanceClass
from vocabulary.models import ChemicalClass, Group

from . import (build_index, context_form, field_value, make_substance,
               page)
from .registry_support import (NEW_SUBSTANCE, REGISTRY, VOCABULARIES,
                               RegistryCase, choice_value, offered,
                               substance_url, term_url, vocabulary_model)

TREES = ["chemical-classes", "groups", "projects"]
# The groups and classes of the registry in the order of their pages.
GROUP_ORDER = ["purchased", "reagents", "starting-materials",
               "synthesised", "final-products", "intermediates"]
CLASS_ORDER = ["carbonyl-compounds", "carboxylic-acids", "ketones",
               "aryl-ketones"]


class FormCase(RegistryCase):
    """A test case whose client is signed in."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.kl)

    def refused(self, response: Any, field: str | None = None) -> None:
        """The form is shown again with errors."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        if field is not None:
            self.assertIn(field, errors)

    def keys_of(self, root: Any, field: str) -> list[str]:
        """The keys of the terms a control offers, in its order."""
        every = {}
        for model in (Group, ChemicalClass):
            for term in model.objects.all():
                every[str(term.pk)] = term.key
                every[term.key] = term.key
        return [every[e.get("value")] for e in offered(root, field)]


def control_names(form: Any) -> set[str]:
    """The names of the controls of ``form`` that submit a value."""
    return {e.get("name") for e in
            form.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in ("submit", "button")
            and e.get("name") != "csrfmiddlewaretoken"}


def substance_data(root: Any, **over: Any) -> dict[str, Any]:
    """The new-substance form's fields for ``ethyl-acetate`` in the
    group ``reagents`` and the class ``ketones``, as the page ``root``
    offers them, with ``over`` applied."""
    data = {
        "key": "ethyl-acetate", "name": "Ethyl acetate", "name_de": "",
        "short_name": "", "group": choice_value(
            root, "group", Group.objects.get(key="reagents")),
        "chemical_classes": [choice_value(
            root, "chemical_classes",
            ChemicalClass.objects.get(key="ketones"))],
        "formula": "", "mw": "", "smiles": "", "cas": "", "note": ""}
    data.update(over)
    return data


class NewSubstanceTests(FormCase):

    def data(self, **over: Any) -> dict[str, Any]:
        return substance_data(self.get(NEW_SUBSTANCE), **over)

    def test_new_substance(self) -> None:
        """Scenario: New substance."""
        done = self.client.post(NEW_SUBSTANCE, self.data(mw="88,11"))
        found = Substance.objects.get(key="ethyl-acetate")
        self.assertEqual(found.mw, Decimal("88.11"))
        self.assertEqual(found.name, "Ethyl acetate")
        self.assertEqual(found.group.key, "reagents")
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"ketones"})
        self.assertEqual(found.history.get().history_type, "+")
        self.assertEqual(found.history.get().history_user, self.kl)
        self.assertRedirects(done, substance_url("ethyl-acetate"),
                             fetch_redirect_response=False)
        self.assertEqual(
            self.client.get(substance_url("ethyl-acetate")).status_code,
            200)

    def test_every_field_is_saved(self) -> None:
        self.client.post(NEW_SUBSTANCE, self.data(
            name_de="Ethylacetat", short_name="EtOAc", formula="C4H8O2",
            mw="88.11", smiles="CCOC(C)=O", cas="141-78-6", note="Lösung"))
        found = Substance.objects.get(key="ethyl-acetate")
        self.assertEqual(
            (found.name_de, found.short_name, found.formula, found.smiles,
             found.cas, found.note),
            ("Ethylacetat", "EtOAc", "C4H8O2", "CCOC(C)=O", "141-78-6",
             "Lösung"))

    def test_several_classes(self) -> None:
        root = self.get(NEW_SUBSTANCE)
        self.client.post(NEW_SUBSTANCE, substance_data(
            root, chemical_classes=[
                choice_value(root, "chemical_classes",
                             ChemicalClass.objects.get(key=key))
                for key in ("ketones", "carboxylic-acids")]))
        found = Substance.objects.get(key="ethyl-acetate")
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"ketones", "carboxylic-acids"})
        self.assertEqual(SubstanceClass.objects.filter(
            substance=found).count(), 2)

    def test_only_the_optional_fields_may_be_empty(self) -> None:
        self.client.post(NEW_SUBSTANCE, self.data())
        found = Substance.objects.get(key="ethyl-acetate")
        self.assertIsNone(found.mw)
        self.assertFalse(found.cas)

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = self.get(NEW_SUBSTANCE)
        form = root.find("input", name="key").closest("form")
        names = control_names(form)
        self.assertEqual(names, {
            "key", "name", "name_de", "short_name", "group",
            "chemical_classes", "formula", "mw", "smiles", "cas", "note"})

    def test_the_groups_come_in_the_order_of_their_page(self) -> None:
        root = self.get(NEW_SUBSTANCE)
        self.assertEqual(self.keys_of(root, "group"), GROUP_ORDER)

    def test_the_classes_are_check_boxes_in_the_order_of_their_page(
            self) -> None:
        root = self.get(NEW_SUBSTANCE)
        boxes = root.find_all("input", name="chemical_classes")
        self.assertTrue(all(box.get("type") == "checkbox" for box in boxes))
        self.assertEqual(self.keys_of(root, "chemical_classes"),
                         CLASS_ORDER)

    def test_the_form_in_english(self) -> None:
        self.use_index(build_index("en"))
        root = self.get(NEW_SUBSTANCE)
        self.assertIn("Chemical classes", root.text())

    def test_no_chemical_class(self) -> None:
        """Scenario: No chemical class."""
        before = Substance.objects.count()
        self.refused(self.client.post(
            NEW_SUBSTANCE, self.data(chemical_classes=[])),
            "chemical_classes")
        self.assertEqual(Substance.objects.count(), before)
        self.assertFalse(Substance.objects.filter(
            key="ethyl-acetate").exists())

    def test_the_key_must_match_its_pattern(self) -> None:
        for key in ("", "Ethyl-Acetate", "ethyl acetate", "-a", "a--b",
                    "ä", "k" * 101):
            with self.subTest(key=key):
                self.refused(self.client.post(
                    NEW_SUBSTANCE, self.data(key=key)), "key")
        self.assertFalse(Substance.objects.filter(
            name="Ethyl acetate").exists())

    def test_a_taken_key_is_refused(self) -> None:
        before = Substance.objects.count()
        self.refused(self.client.post(
            NEW_SUBSTANCE, self.data(key="acetophenone")), "key")
        self.assertEqual(Substance.objects.count(), before)

    def test_the_name_is_required(self) -> None:
        self.refused(self.client.post(NEW_SUBSTANCE, self.data(name="")),
                     "name")

    def test_the_group_is_required(self) -> None:
        self.refused(self.client.post(NEW_SUBSTANCE, self.data(group="")),
                     "group")

    def test_an_unknown_group_is_refused(self) -> None:
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(group="no-such-group")),
                     "group")

    def test_a_molar_mass_must_be_a_number_above_zero(self) -> None:
        for mw in ("abc", "0", "-1", "0,0", "1,2345"):
            with self.subTest(mw=mw):
                self.refused(self.client.post(NEW_SUBSTANCE,
                                              self.data(mw=mw)), "mw")
        self.assertFalse(Substance.objects.filter(
            key="ethyl-acetate").exists())

    def test_a_molar_mass_with_a_decimal_comma(self) -> None:
        self.client.post(NEW_SUBSTANCE, self.data(mw="0,001"))
        self.assertEqual(Substance.objects.get(key="ethyl-acetate").mw,
                         Decimal("0.001"))

    def test_cas_number_checked(self) -> None:
        """Scenario: CAS number checked."""
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(cas="140-10-4")), "cas")
        self.assertFalse(Substance.objects.filter(
            key="ethyl-acetate").exists())
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(cas="140-10-3")), "cas")
        self.assertFalse(Substance.objects.filter(
            key="ethyl-acetate").exists())

    def test_a_cas_number_of_the_wrong_form(self) -> None:
        for cas in ("1-10-3", "140-1-3", "1401 03", "140-10-33", "x"):
            with self.subTest(cas=cas):
                self.refused(self.client.post(NEW_SUBSTANCE,
                                              self.data(cas=cas)), "cas")

    def test_a_cas_number_that_verifies_is_saved(self) -> None:
        self.client.post(NEW_SUBSTANCE, self.data(cas="141-78-6"))
        self.assertEqual(Substance.objects.get(key="ethyl-acetate").cas,
                         "141-78-6")

    def test_the_names_are_bounded(self) -> None:
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(name="n" * 201)), "name")
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(name_de="n" * 201)),
                     "name_de")
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(short_name="s" * 51)),
                     "short_name")
        self.refused(self.client.post(NEW_SUBSTANCE,
                                      self.data(formula="f" * 101)),
                     "formula")

    def test_a_refused_form_shows_what_was_entered(self) -> None:
        response = self.client.post(NEW_SUBSTANCE, self.data(
            name="Entered", mw="abc"))
        root = page(response)
        self.assertEqual(field_value(root, "name"), "Entered")
        self.assertEqual(field_value(root, "mw"), "abc")


class EditSubstanceTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.before_classes = list(SubstanceClass.history.values_list(
            "history_id", flat=True))

    def url(self, key: str = "cinnamic-acid") -> str:
        return substance_url(key, "edit")

    def data(self, **over: Any) -> dict[str, Any]:
        root = self.get(self.url())
        data = {
            "key": "ignored", "name": "(E)-Cinnamic acid",
            "name_de": "(E)-Zimtsäure", "short_name": "ZS",
            "group": choice_value(root, "group",
                                  Group.objects.get(key="final-products")),
            "chemical_classes": [choice_value(
                root, "chemical_classes",
                ChemicalClass.objects.get(key="carboxylic-acids"))],
            "formula": "C9H8O2", "mw": "148,16",
            "smiles": "OC(=O)/C=C/c1ccccc1", "cas": "140-10-3",
            "note": "Notiz"}
        data.update(over)
        return data

    def test_the_form_shows_the_substance(self) -> None:
        root = self.get(self.url())
        self.assertEqual(field_value(root, "name"), "(E)-Cinnamic acid")
        self.assertEqual(field_value(root, "name_de"), "(E)-Zimtsäure")
        self.assertEqual(field_value(root, "short_name"), "ZS")
        self.assertEqual(field_value(root, "formula"), "C9H8O2")
        self.assertEqual(field_value(root, "cas"), "140-10-3")
        self.assertRegex(field_value(root, "mw"), r"^148[,.]16$")
        checked = [b for b in root.find_all("input",
                                            name="chemical_classes")
                   if "checked" in b.attrs]
        self.assertEqual(len(checked), 1)

    def test_the_form_has_no_key(self) -> None:
        root = self.get(self.url())
        self.assertIsNone(root.find("input", name="key"))
        self.assertIsNone(root.find("select", name="key"))

    def test_key_fixed(self) -> None:
        """Scenario: Key fixed."""
        done = self.client.post(self.url(), self.data(key="zimtsaeure"))
        self.assertTrue(Substance.objects.filter(
            key="cinnamic-acid").exists())
        self.assertFalse(Substance.objects.filter(
            key="zimtsaeure").exists())
        self.assertRedirects(done, substance_url("cinnamic-acid"),
                             fetch_redirect_response=False)

    def test_a_change_is_saved_with_its_history(self) -> None:
        done = self.client.post(self.url(), self.data(
            note="Geändert", mw="148,2"))
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual((found.note, found.mw),
                         ("Geändert", Decimal("148.2")))
        newest = found.history.order_by("-history_id").first()
        self.assertEqual(newest.history_type, "~")
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(newest.note, "Geändert")
        self.assertRedirects(done, substance_url("cinnamic-acid"),
                             fetch_redirect_response=False)

    def test_the_classes_are_replaced(self) -> None:
        root = self.get(self.url())
        self.client.post(self.url(), self.data(chemical_classes=[
            choice_value(root, "chemical_classes",
                         ChemicalClass.objects.get(key=key))
            for key in ("ketones", "aryl-ketones")]))
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"ketones", "aryl-ketones"})

    def test_a_change_of_classes_is_in_the_history(self) -> None:
        root = self.get(self.url())
        self.client.post(self.url(), self.data(chemical_classes=[
            choice_value(root, "chemical_classes",
                         ChemicalClass.objects.get(key="ketones"))]))
        records = SubstanceClass.history.filter(
            substance__key="cinnamic-acid")
        changes = {(r.history_type, r.chemical_class.key, r.history_user)
                   for r in records.exclude(
                       history_id__in=self.before_classes)}
        self.assertEqual(changes, {("+", "ketones", self.kl),
                                   ("-", "carboxylic-acids", self.kl)})

    def test_a_substance_keeps_its_classes_without_a_change(self) -> None:
        self.client.post(self.url(), self.data())
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual({t.key for t in found.chemical_classes.all()},
                         {"carboxylic-acids"})
        self.assertEqual(SubstanceClass.objects.filter(
            substance=found).count(), 1)

    def test_no_chemical_class(self) -> None:
        self.refused(self.client.post(
            self.url(), self.data(chemical_classes=[])),
            "chemical_classes")
        self.assertEqual(Substance.objects.get(
            key="cinnamic-acid").chemical_classes.count(), 1)

    def test_a_cas_number_of_another_substance_is_refused(self) -> None:
        make_substance("other", cas="141-78-6")
        self.refused(self.client.post(self.url(),
                                      self.data(cas="141-78-6")), "cas")
        self.assertEqual(Substance.objects.get(key="cinnamic-acid").cas,
                         "140-10-3")

    def test_its_own_cas_number_is_no_conflict(self) -> None:
        done = self.client.post(self.url(), self.data(cas="140-10-3"))
        self.assertEqual(done.status_code, 302)

    def test_the_cas_number_may_be_removed(self) -> None:
        self.client.post(self.url(), self.data(cas=""))
        self.assertFalse(Substance.objects.get(key="cinnamic-acid").cas)

    def test_a_molar_mass_of_zero_is_refused(self) -> None:
        self.refused(self.client.post(self.url(), self.data(mw="0")), "mw")
        self.assertEqual(Substance.objects.get(key="cinnamic-acid").mw,
                         Decimal("148.16"))

    def test_the_name_is_required(self) -> None:
        self.refused(self.client.post(self.url(), self.data(name="")),
                     "name")

    def test_an_unknown_substance_answers_404(self) -> None:
        self.assertEqual(self.client.get(self.url("nope")).status_code, 404)
        self.assertEqual(self.client.post(self.url("nope"), {}).status_code,
                         404)



class TermFormTests(FormCase):

    def new(self, vocabulary: str) -> str:
        return term_url(vocabulary, "new")

    def edit(self, vocabulary: str, key: str) -> str:
        return term_url(vocabulary, key, "edit")

    def data(self, vocabulary: str, **over: Any) -> dict[str, Any]:
        data = {"key": "fresh", "label": "Fresh", "label_de": "Frisch"}
        if vocabulary in TREES:
            data["parent"] = ""
        data.update(over)
        return data

    def test_a_new_term(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                done = self.client.post(self.new(vocabulary),
                                        self.data(vocabulary))
                found = vocabulary_model(vocabulary).objects.get(
                    key="fresh")
                self.assertEqual((found.label, found.label_de),
                                 ("Fresh", "Frisch"))
                self.assertEqual(found.history.get().history_type, "+")
                self.assertEqual(found.history.get().history_user,
                                 self.kl)
                self.assertRedirects(done, term_url(vocabulary),
                                     fetch_redirect_response=False)

    def test_a_new_term_under_a_parent(self) -> None:
        root = self.get(self.new("groups"))
        parent = Group.objects.get(key="reagents")
        self.client.post(self.new("groups"), self.data(
            "groups", parent=choice_value(root, "parent", parent)))
        self.assertEqual(Group.objects.get(key="fresh").parent, parent)

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                root = self.get(self.new(vocabulary))
                form = root.find("input", name="key").closest("form")
                names = control_names(form)
                self.assertEqual(
                    names, {"key", "label", "label_de"}
                    | ({"parent"} if vocabulary in TREES else set()))

    def test_a_term_is_filed_under_a_term_of_its_vocabulary(self) -> None:
        root = self.get(self.new("groups"))
        self.assertEqual(self.keys_of(root, "parent"), GROUP_ORDER)

    def test_bad_key(self) -> None:
        """Scenario: Bad key."""
        before = vocabulary_model("projects").objects.count()
        self.refused(self.client.post(self.new("projects"), self.data(
            "projects", key="Teaching 2")), "key")
        self.assertEqual(vocabulary_model("projects").objects.count(),
                         before)

    def test_keys_that_break_the_pattern(self) -> None:
        for vocabulary in VOCABULARIES:
            for key in ("", "Upper", "two words", "-a", "a-", "a--b",
                        "k" * 51):
                with self.subTest(vocabulary=vocabulary, key=key):
                    self.refused(self.client.post(
                        self.new(vocabulary),
                        self.data(vocabulary, key=key)), "key")
            self.assertEqual(
                vocabulary_model(vocabulary).objects.filter(
                    key="fresh").count(), 0)

    def test_a_taken_key_is_refused(self) -> None:
        self.refused(self.client.post(self.new("groups"), self.data(
            "groups", key="reagents")), "key")
        self.assertEqual(Group.objects.filter(key="reagents").count(), 1)

    def test_the_label_is_required(self) -> None:
        for vocabulary in VOCABULARIES:
            with self.subTest(vocabulary=vocabulary):
                self.refused(self.client.post(
                    self.new(vocabulary), self.data(vocabulary, label="")),
                    "label")

    def test_the_labels_are_bounded(self) -> None:
        self.refused(self.client.post(self.new("groups"), self.data(
            "groups", label="l" * 101)), "label")
        self.refused(self.client.post(self.new("groups"), self.data(
            "groups", label_de="l" * 101)), "label_de")

    def test_the_german_label_may_be_empty(self) -> None:
        self.client.post(self.new("groups"), self.data("groups",
                                                       label_de=""))
        self.assertTrue(Group.objects.filter(key="fresh").exists())

    def test_edit_keeps_the_key(self) -> None:
        for vocabulary in VOCABULARIES:
            model = vocabulary_model(vocabulary)
            model.objects.create(key="old", label="Old")
            with self.subTest(vocabulary=vocabulary):
                root = self.get(self.edit(vocabulary, "old"))
                self.assertIsNone(root.find("input", name="key"))
                done = self.client.post(
                    self.edit(vocabulary, "old"),
                    self.data(vocabulary, key="changed", label="New"))
                found = model.objects.get(key="old")
                self.assertEqual(found.label, "New")
                self.assertFalse(model.objects.filter(
                    key="changed").exists())
                self.assertEqual(
                    found.history.order_by("-history_id").first()
                    .history_type, "~")
                self.assertRedirects(done, term_url(vocabulary),
                                     fetch_redirect_response=False)

    def test_the_edit_form_shows_the_term(self) -> None:
        root = self.get(self.edit("groups", "reagents"))
        self.assertEqual(field_value(root, "label"), "Reagents")
        self.assertEqual(field_value(root, "label_de"), "Reagenzien")

    def test_the_parent_choice_leaves_out_the_term_and_its_descendants(
            self) -> None:
        root = self.get(self.edit("groups", "purchased"))
        self.assertEqual(self.keys_of(root, "parent"),
                         ["synthesised", "final-products", "intermediates"])
        root = self.get(self.edit("groups", "reagents"))
        self.assertEqual(
            self.keys_of(root, "parent"),
            ["purchased", "starting-materials", "synthesised",
             "final-products", "intermediates"])

    def test_the_parent_may_be_none(self) -> None:
        self.client.post(self.edit("groups", "reagents"), self.data(
            "groups", label="Reagents", parent=""))
        self.assertIsNone(Group.objects.get(key="reagents").parent)

    def test_no_loop(self) -> None:
        """Scenario: No loop."""
        self.assertEqual(Group.objects.get(key="starting-materials")
                         .parent.key, "purchased")
        child = Group.objects.get(key="starting-materials")
        for value in (str(child.pk), child.key):
            with self.subTest(value=value):
                self.refused(self.client.post(
                    self.edit("groups", "purchased"),
                    self.data("groups", label="Purchased", parent=value)),
                    "parent")
                self.assertIsNone(Group.objects.get(key="purchased").parent)

    def test_a_term_is_not_its_own_parent(self) -> None:
        own = Group.objects.get(key="reagents")
        for value in (str(own.pk), own.key):
            with self.subTest(value=value):
                self.refused(self.client.post(
                    self.edit("groups", "reagents"),
                    self.data("groups", label="Reagents", parent=value)),
                    "parent")
        self.assertEqual(Group.objects.get(key="reagents").parent.key,
                         "purchased")

    def test_no_loop_through_a_grandchild(self) -> None:
        deep = Group.objects.create(
            key="deep", label="Deep",
            parent=Group.objects.get(key="reagents"))
        for value in (str(deep.pk), deep.key):
            with self.subTest(value=value):
                self.refused(self.client.post(
                    self.edit("groups", "purchased"),
                    self.data("groups", label="Purchased", parent=value)),
                    "parent")
        self.assertIsNone(Group.objects.get(key="purchased").parent)

    def test_unknown_terms_and_vocabularies_answer_404(self) -> None:
        for path in (self.edit("groups", "nope"),
                     self.new("nope"), self.edit("nope", "x")):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
                self.assertEqual(self.client.post(path, {}).status_code,
                                 404)

class SignInTests(RegistryCase):

    def paths(self) -> dict[str, dict[str, Any]]:
        paths: dict[str, dict[str, Any]] = {
            NEW_SUBSTANCE: {"key": "ethyl-acetate", "name": "Ethyl"},
            substance_url("cinnamic-acid", "edit"): {"name": "X"}}
        for vocabulary in VOCABULARIES:
            paths[term_url(vocabulary, "new")] = {"key": "fresh",
                                                  "label": "Fresh"}
        paths[term_url("groups", "reagents", "edit")] = {"label": "X"}
        return paths

    def test_form_without_sign_in(self) -> None:
        before = (Substance.objects.count(), Group.objects.count())
        for path, data in self.paths().items():
            login = f"/lab/accounts/login/?next={path}"
            with self.subTest(path=path, method="GET"):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertEqual(done["Location"], login)
            with self.subTest(path=path, method="POST"):
                done = self.client.post(path, data)
                self.assertEqual(done.status_code, 302)
                self.assertEqual(done["Location"], login)
        self.assertEqual(before, (Substance.objects.count(),
                                  Group.objects.count()))
        self.assertEqual(Group.objects.get(key="reagents").label,
                         "Reagents")
        self.assertEqual(Substance.objects.get(key="cinnamic-acid").name,
                         "(E)-Cinnamic acid")

    def test_the_pages_need_no_sign_in(self) -> None:
        for path in (REGISTRY, substance_url("cinnamic-acid"),
                     *(term_url(v) for v in VOCABULARIES)):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
