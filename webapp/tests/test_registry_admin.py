"""Tests of the registry in the admin (lab-registry: Registry in the
admin)."""

from typing import Any

from registry.models import Substance
from vocabulary.models import ChemicalClass, Group

from . import make_user, page
from .registry_support import RegistryCase, vocabulary_model

ADMIN = "/lab/admin/"
SUBSTANCES = ADMIN + "registry/substance/"
MODELS = {"chemical-classes": "chemicalclass", "groups": "group",
          "projects": "project", "reaction-types": "reactiontype"}
TREES = ["chemical-classes", "groups", "projects"]


def terms(vocabulary: str) -> str:
    return f"{ADMIN}vocabulary/{MODELS[vocabulary]}/"


def editable(response: Any) -> set[str]:
    """The names of the controls a page offers for editing."""
    root = page(response)
    return {e.get("name") for e in
            root.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in (
                "submit", "hidden", "button")}


class AdminCase(RegistryCase):

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.staff)

    def change(self, base: str, record: Any) -> str:
        return f"{base}{record.pk}/change/"


class AccessTests(AdminCase):

    def paths(self) -> list[str]:
        return [SUBSTANCES, *(terms(v) for v in MODELS)]

    def test_staff_enter(self) -> None:
        for path in self.paths():
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_anonymous_users_are_sent_to_the_admin_sign_in(self) -> None:
        self.client.logout()
        for path in self.paths():
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertTrue(
                    done["Location"].startswith("/lab/admin/login/"))

    def test_users_without_staff_status_are_kept_out(self) -> None:
        self.client.force_login(self.kl)
        for path in self.paths():
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertIn(done.status_code, (302, 403))
                if done.status_code == 302:
                    self.assertTrue(
                        done["Location"].startswith("/lab/admin/login/"))


class SearchTests(AdminCase):

    def listed(self, query: str) -> str:
        return self.client.get(f"{SUBSTANCES}?q={query}").content.decode()

    def test_substances_are_listed(self) -> None:
        text = self.client.get(SUBSTANCES).content.decode()
        for key in ("cinnamic-acid", "acetophenone", "new-compound-7"):
            with self.subTest(key=key):
                self.assertIn(key, text)

    def test_search_by_key(self) -> None:
        text = self.listed("acetoph")
        self.assertIn("acetophenone", text)
        self.assertNotIn("cinnamic-acid", text)

    def test_search_by_name(self) -> None:
        text = self.listed("compound")
        self.assertIn("new-compound-7", text)
        self.assertNotIn("cinnamic-acid", text)

    def test_search_by_german_name(self) -> None:
        text = self.listed("zimts")
        self.assertIn("cinnamic-acid", text)
        self.assertNotIn("acetophenone", text)

    def test_search_a_term_by_key_and_labels(self) -> None:
        base = terms("groups")
        for query, found, other in (("starting", "starting-materials",
                                     "synthesised"),
                                    ("Reagents", "reagents", "synthesised"),
                                    ("zwischen", "intermediates",
                                     "reagents")):
            with self.subTest(query=query):
                text = self.client.get(f"{base}?q={query}").content.decode()
                self.assertIn(found, text)
                self.assertNotIn(f">{other}<", text)

    def test_the_terms_of_each_vocabulary_are_listed(self) -> None:
        for vocabulary in MODELS:
            vocabulary_model(vocabulary).objects.get_or_create(
                key="listed", defaults={"label": "Listed"})
            with self.subTest(vocabulary=vocabulary):
                self.assertIn("listed", self.client.get(
                    terms(vocabulary)).content.decode())


class HistoryTests(AdminCase):

    def test_the_change_history_of_a_substance(self) -> None:
        worker = make_user("lab-worker-xy", "XY")
        found = Substance.objects.get(key="cinnamic-acid")
        found._history_user = worker
        found.note = "geändert"
        found.save()
        done = self.client.get(f"{SUBSTANCES}{found.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-xy", done.content.decode())

    def test_the_change_history_of_each_vocabulary(self) -> None:
        for vocabulary in MODELS:
            model = vocabulary_model(vocabulary)
            term = model.objects.create(key="history", label="History")
            with self.subTest(vocabulary=vocabulary):
                done = self.client.get(
                    f"{terms(vocabulary)}{term.pk}/history/")
                self.assertEqual(done.status_code, 200)


class ReadOnlyKeyTests(AdminCase):

    def test_key_read_only(self) -> None:
        """Scenario: Key read-only."""
        found = Substance.objects.get(key="cinnamic-acid")
        done = self.client.get(self.change(SUBSTANCES, found))
        self.assertEqual(done.status_code, 200)
        names = editable(done)
        self.assertIn("name", names)
        self.assertNotIn("key", names)
        self.assertIn("cinnamic-acid", done.content.decode())

    def test_the_key_is_entered_when_a_substance_is_added(self) -> None:
        self.assertIn("key", editable(self.client.get(
            SUBSTANCES + "add/")))

    def test_the_key_of_a_term_is_read_only(self) -> None:
        for vocabulary in MODELS:
            model = vocabulary_model(vocabulary)
            term = model.objects.create(key="fixed", label="Fixed")
            with self.subTest(vocabulary=vocabulary):
                done = self.client.get(self.change(terms(vocabulary), term))
                names = editable(done)
                self.assertIn("label", names)
                self.assertNotIn("key", names)
                self.assertIn("fixed", done.content.decode())
                self.assertIn("key", editable(self.client.get(
                    terms(vocabulary) + "add/")))

    def test_a_posted_key_is_ignored(self) -> None:
        found = Substance.objects.get(key="acetophenone")
        self.client.post(self.change(SUBSTANCES, found), {
            "key": "changed", "name": "Acetophenone",
            "group": str(found.group.pk)})
        self.assertTrue(Substance.objects.filter(
            key="acetophenone").exists())
        self.assertFalse(Substance.objects.filter(key="changed").exists())

    def test_a_term_is_added(self) -> None:
        for vocabulary in MODELS:
            data = {"key": "added", "label": "Added", "label_de": ""}
            if vocabulary in TREES:
                data["parent"] = ""
            with self.subTest(vocabulary=vocabulary):
                done = self.client.post(terms(vocabulary) + "add/", data)
                self.assertEqual(done.status_code, 302)
                self.assertTrue(vocabulary_model(vocabulary).objects.filter(
                    key="added").exists())


class ParentTests(AdminCase):

    def post(self, vocabulary: str, term: Any, **over: str) -> Any:
        data = {"label": term.label, "label_de": term.label_de or "",
                "parent": ""}
        data.update(over)
        return self.client.post(self.change(terms(vocabulary), term), data)

    def test_a_loop_is_refused(self) -> None:
        top = Group.objects.get(key="purchased")
        child = Group.objects.get(key="starting-materials")
        done = self.post("groups", top, parent=str(child.pk))
        self.assertEqual(done.status_code, 200)
        self.assertIn("errors", page(done).find(cls="field-parent").classes)
        self.assertIsNone(Group.objects.get(key="purchased").parent)

    def test_a_term_is_not_its_own_parent(self) -> None:
        own = ChemicalClass.objects.get(key="ketones")
        done = self.post("chemical-classes", own, parent=str(own.pk))
        self.assertEqual(done.status_code, 200)
        self.assertEqual(ChemicalClass.objects.get(key="ketones")
                         .parent.key, "carbonyl-compounds")

    def test_a_loop_through_a_grandchild_is_refused(self) -> None:
        top = ChemicalClass.objects.get(key="carbonyl-compounds")
        deep = ChemicalClass.objects.get(key="aryl-ketones")
        done = self.post("chemical-classes", top, parent=str(deep.pk))
        self.assertEqual(done.status_code, 200)
        self.assertIsNone(ChemicalClass.objects.get(
            key="carbonyl-compounds").parent)

    def test_a_valid_parent_is_saved(self) -> None:
        top = Group.objects.get(key="synthesised")
        child = Group.objects.get(key="reagents")
        done = self.post("groups", child, parent=str(top.pk))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Group.objects.get(key="reagents").parent, top)



class DeletionTests(AdminCase):

    def delete(self, base: str, record: Any) -> Any:
        return self.client.post(f"{base}{record.pk}/delete/",
                                {"post": "yes"})

    def test_term_in_use(self) -> None:
        """Scenario: Term in use."""
        term = ChemicalClass.objects.get(key="carboxylic-acids")
        done = self.delete(terms("chemical-classes"), term)
        self.assertEqual(done.status_code, 200)
        text = done.content.decode()
        self.assertTrue("cinnamic-acid" in text
                        or "(E)-Cinnamic acid" in text, text)
        self.assertTrue(ChemicalClass.objects.filter(
            key="carboxylic-acids").exists())

    def test_a_group_in_use_is_refused(self) -> None:
        term = Group.objects.get(key="final-products")
        done = self.delete(terms("groups"), term)
        self.assertEqual(done.status_code, 200)
        self.assertTrue(Group.objects.filter(key="final-products").exists())
        text = done.content.decode()
        self.assertTrue("cinnamic-acid" in text
                        or "(E)-Cinnamic acid" in text, text)

    def test_a_term_with_children_is_refused(self) -> None:
        term = Group.objects.get(key="purchased")
        done = self.delete(terms("groups"), term)
        self.assertEqual(done.status_code, 200)
        self.assertTrue(Group.objects.filter(key="purchased").exists())

    def test_a_term_in_no_use_is_deleted(self) -> None:
        for vocabulary in MODELS:
            term = vocabulary_model(vocabulary).objects.create(
                key="spare", label="Spare")
            with self.subTest(vocabulary=vocabulary):
                self.assertEqual(
                    self.delete(terms(vocabulary), term).status_code, 302)
                self.assertFalse(vocabulary_model(vocabulary).objects
                                 .filter(key="spare").exists())

    def test_a_substance_nothing_refers_to_is_deleted(self) -> None:
        found = Substance.objects.get(key="new-compound-7")
        self.assertEqual(self.delete(SUBSTANCES, found).status_code, 302)
        self.assertFalse(Substance.objects.filter(
            key="new-compound-7").exists())

    def test_a_substance_with_an_article_is_refused(self) -> None:
        found = Substance.objects.get(key="cinnamic-acid")
        done = self.delete(SUBSTANCES, found)
        self.assertEqual(done.status_code, 200)
        self.assertTrue(Substance.objects.filter(
            key="cinnamic-acid").exists())
