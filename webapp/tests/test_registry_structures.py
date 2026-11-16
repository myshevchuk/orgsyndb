"""Tests of the structure images (lab-registry: Structure images) and of
the drawing's place in the change history (web-app: Change history)."""

import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

from registry import snapshot
from registry.models import Substance

from . import make_substance
from .demo_support import SeededCase
from .registry_support import (RegistryCase, load, small_snapshot,
                               substance_url, wipe_registry, without_digest,
                               write_json)
from .structure_support import (ACETONE, ACETONE_WITH_AN_ALIAS, ALIAS,
                                ETHANOL, ETHANOL_AT_THE_ORIGIN,
                                ETHANOL_IN_A_COLUMN, HEADERS, PLAIN, SVG,
                                bonds, named_colours, parsed, tag)
from .test_registry_admin import SUBSTANCES

WHITE = {"#fff", "#ffffff", "white"}
BLACK = {"#000", "#000000", "black"}


def image_path(key: str) -> str:
    """The address of the image of the substance ``key``."""
    return substance_url(key) + "structure.svg"


def drawn(*, wrapping: bool = True) -> Any:
    """A patch of ``registry.structures.draw`` that records its calls
    and, when ``wrapping``, still draws."""
    from registry import structures
    return mock.patch.object(structures, "draw",
                             wraps=structures.draw if wrapping else None)


class ImageTests(RegistryCase):
    """The answer of ``/lab/registry/substances/<key>/structure.svg``."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        make_substance("acetone", "Acetone", molfile=ACETONE)

    def test_the_answer_is_an_svg_image_with_both_headers(self) -> None:
        response = self.client.get(image_path("acetone"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0],
                         "image/svg+xml")
        for name, value in HEADERS.items():
            with self.subTest(header=name):
                self.assertEqual(response[name], value)

    def test_the_image_needs_no_sign_in(self) -> None:
        self.assertEqual(
            self.client.get(image_path("acetone")).status_code, 200)

    def test_the_body_is_an_svg_document_with_a_view_box(self) -> None:
        root = parsed(self.client.get(image_path("acetone")).content)
        self.assertEqual(root.tag, SVG + "svg")
        self.assertTrue(root.get("viewBox"))

    def test_the_drawing_is_black_on_white(self) -> None:
        root = parsed(self.client.get(image_path("acetone")).content)
        colours = set(named_colours(root))
        self.assertLessEqual(colours, PLAIN)
        self.assertTrue(colours & BLACK, "nothing is drawn in black")
        self.assertTrue(colours & WHITE, "the background is not white")

    def test_a_substance_without_a_molfile_answers_404(self) -> None:
        self.assertEqual(
            self.client.get(image_path("cinnamic-acid")).status_code, 404)
        self.assertEqual(
            self.client.get(image_path("new-compound-7")).status_code, 404)

    def test_an_unknown_key_answers_404(self) -> None:
        self.assertEqual(
            self.client.get(image_path("no-such-substance")).status_code,
            404)

    def test_the_answer_is_the_drawing_kept_with_the_substance(self) -> None:
        kept = Substance.objects.get(key="acetone").structure_svg
        self.assertTrue(kept.strip())
        self.assertEqual(
            self.client.get(image_path("acetone")).content.decode("utf-8"),
            kept)

    def test_the_drawing_keeps_the_coordinates_of_the_file(self) -> None:
        make_substance("column", "Column", molfile=ETHANOL_IN_A_COLUMN)
        found = bonds(parsed(self.client.get(
            image_path("column")).content))
        self.assertGreaterEqual(len(found), 2)
        for bond in found:
            with self.subTest(bond=bond):
                self.assertLess(abs(bond[0][0] - bond[-1][0]), 0.5)
                self.assertGreater(abs(bond[0][1] - bond[-1][1]), 1)

    def test_atoms_at_the_origin_are_drawn_apart(self) -> None:
        make_substance("origin", "Origin", molfile=ETHANOL_AT_THE_ORIGIN)
        found = bonds(parsed(self.client.get(
            image_path("origin")).content))
        self.assertGreaterEqual(len(found), 2, "the bonds are not drawn")
        for bond in found:
            with self.subTest(bond=bond):
                self.assertGreater(
                    ((bond[0][0] - bond[-1][0]) ** 2
                     + (bond[0][1] - bond[-1][1]) ** 2) ** 0.5, 1)

    def test_text_from_the_molfile_adds_no_element(self) -> None:
        make_substance("alias", "Alias", molfile=ACETONE_WITH_AN_ALIAS)
        response = self.client.get(image_path("alias"))
        self.assertEqual(response.status_code, 200)
        root = parsed(response.content)
        self.assertEqual([e for e in root.iter() if tag(e) == "script"], [])
        self.assertEqual(root.tag, SVG + "svg")
        self.assertNotIn(ALIAS, response.content.decode("utf-8"))


class DrawingTests(RegistryCase):
    """When the lab draws, and what it keeps."""

    def test_drawn_when_saved(self) -> None:
        """Scenario: Drawn when saved."""
        with drawn() as draw:
            make_substance("acetone", "Acetone", molfile=ACETONE)
            first = self.client.get(image_path("acetone")).content
            second = self.client.get(image_path("acetone")).content
            make_substance("acetone", molfile=ETHANOL)
            third = self.client.get(image_path("acetone")).content
        self.assertEqual(draw.call_count, 2)
        self.assertTrue(first.strip())
        self.assertEqual(first, second)
        self.assertNotEqual(third, first)

    def test_a_request_does_not_draw(self) -> None:
        make_substance("acetone", "Acetone", molfile=ACETONE)
        kept = Substance.objects.get(key="acetone").structure_svg
        with drawn(wrapping=False) as draw:
            draw.side_effect = AssertionError("RDKit drew on a request")
            response = self.client.get(image_path("acetone"))
            page = self.client.get(substance_url("acetone"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), kept)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(draw.call_count, 0)

    def test_a_substance_without_a_molfile_is_not_drawn(self) -> None:
        with drawn() as draw:
            made = make_substance("plain", "Plain")
            made.note = "changed"
            made.save()
        self.assertEqual(draw.call_count, 0)
        self.assertEqual(Substance.objects.get(key="plain").structure_svg,
                         "")

    def test_the_drawing_follows_the_molfile(self) -> None:
        made = make_substance("acetone", "Acetone", molfile=ACETONE)
        first = Substance.objects.get(pk=made.pk).structure_svg
        make_substance("acetone", molfile=ETHANOL)
        self.assertNotEqual(
            Substance.objects.get(pk=made.pk).structure_svg, first)

    def test_a_removed_molfile_removes_the_drawing(self) -> None:
        make_substance("acetone", "Acetone", molfile=ACETONE)
        make_substance("acetone", molfile="")
        found = Substance.objects.get(key="acetone")
        self.assertEqual((found.molfile, found.structure_svg), ("", ""))
        self.assertEqual(
            self.client.get(image_path("acetone")).status_code, 404)

    def test_the_molfile_and_the_drawing_are_fields_of_the_substance(
            self) -> None:
        from django.db import models
        molfile = Substance._meta.get_field("molfile")
        drawing = Substance._meta.get_field("structure_svg")
        for field in (molfile, drawing):
            with self.subTest(field=field.name):
                self.assertIsInstance(field, models.TextField)
                self.assertTrue(field.blank)
        self.assertTrue(molfile.editable)
        self.assertFalse(drawing.editable)
        self.assertEqual(make_substance("bare", "Bare").molfile, "")

    def test_the_drawing_is_not_in_the_history(self) -> None:
        """Requirement: Change history (the cached drawing is left out of
        the copy)."""
        names = {f.name for f in Substance.history.model._meta.get_fields()}
        self.assertIn("molfile", names)
        self.assertNotIn("structure_svg", names)
        made = make_substance("acetone", "Acetone", molfile=ACETONE)
        newest = made.history.order_by("-history_id").first()
        self.assertEqual(newest.molfile, ACETONE)
        self.assertFalse(hasattr(newest, "structure_svg"))


class AdminStructureTests(RegistryCase):
    """The admin saves a substance with a molfile as the forms do and
    does not show the drawing."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.staff)

    def data(self, **over: Any) -> dict[str, str]:
        """The admin's form for a new substance, as ``test_lock`` fills
        it."""
        from vocabulary.models import ChemicalClass, Group
        data = {
            "key": "admin-made", "name": "Admin made", "name_de": "",
            "short_name": "", "group": str(Group.objects.get(
                key="reagents").pk), "formula": "", "mw": "",
            "smiles": "", "molfile": ACETONE, "cas": "", "note": "",
            "classes-TOTAL_FORMS": "1", "classes-INITIAL_FORMS": "0",
            "classes-MIN_NUM_FORMS": "0", "classes-MAX_NUM_FORMS": "1000",
            "classes-0-id": "", "classes-0-substance": "",
            "classes-0-chemical_class": str(ChemicalClass.objects.get(
                key="ketones").pk)}
        data.update(over)
        return data

    def test_a_substance_saved_in_the_admin_is_drawn(self) -> None:
        with drawn() as draw:
            done = self.client.post(SUBSTANCES + "add/", self.data())
        self.assertEqual(done.status_code, 302)
        self.assertEqual(draw.call_count, 1)
        self.assertEqual(Substance.objects.get(key="admin-made").molfile,
                         ACETONE)
        self.assertEqual(
            self.client.get(image_path("admin-made")).status_code, 200)

    def test_the_drawing_is_not_shown(self) -> None:
        found = make_substance("acetone", "Acetone", molfile=ACETONE)
        text = self.client.get(
            f"{SUBSTANCES}{found.pk}/change/").content.decode("utf-8")
        self.assertNotIn('name="structure_svg"', text)


class LoadedStructureTests(RegistryCase):
    """``registry_load`` draws the structures it loads."""

    def test_a_loaded_molfile_is_drawn(self) -> None:
        wipe_registry()
        data = small_snapshot()
        data["substances"][0]["molfile"] = ACETONE
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(Path(directory), data)
            with drawn() as draw:
                load(path)
        self.assertEqual(draw.call_count, 1)
        self.assertEqual(Substance.objects.get(key="acetone").molfile,
                         ACETONE)
        self.assertEqual(
            self.client.get(image_path("acetone")).status_code, 200)
        self.assertEqual(
            self.client.get(image_path("mystery")).status_code, 404)


    def test_a_loaded_molfile_is_in_the_snapshot_again(self) -> None:
        wipe_registry()
        data = small_snapshot()
        data["substances"][0]["molfile"] = ACETONE
        with tempfile.TemporaryDirectory() as directory:
            load(write_json(Path(directory), data))
        self.assertEqual(
            without_digest(snapshot.build(), "accounts", "notebooks"),
            data)


class DemoStructureTests(SeededCase):
    """Scenario: The demo's structure."""

    def test_the_demos_image(self) -> None:
        response = self.client.get(image_path("isopentyl-acetate"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0],
                         "image/svg+xml")
        for name, value in HEADERS.items():
            with self.subTest(header=name):
                self.assertEqual(response[name], value)
        root = parsed(response.content)
        self.assertEqual(root.tag, SVG + "svg")
        self.assertTrue(root.get("viewBox"))
        self.assertLessEqual(set(named_colours(root)), PLAIN)

    def test_no_image_without_a_molfile_and_for_an_unknown_key(self) -> None:
        for key in ("new-compound-7", "no-such-substance"):
            with self.subTest(key=key):
                self.assertEqual(
                    self.client.get(image_path(key)).status_code, 404)

    def test_the_image_needs_no_sign_in(self) -> None:
        self.assertEqual(
            self.client.get(image_path("isopentyl-acetate")).status_code,
            200)

    def test_every_substance_with_a_smiles_has_a_molfile(self) -> None:
        with_smiles = Substance.objects.exclude(smiles="")
        self.assertGreater(with_smiles.count(), 1)
        for found in with_smiles:
            with self.subTest(key=found.key):
                self.assertTrue(found.molfile.strip())
                self.assertEqual(
                    self.client.get(image_path(found.key)).status_code, 200)

    def test_the_substance_without_a_smiles_has_no_molfile(self) -> None:
        found = Substance.objects.get(key="new-compound-7")
        self.assertEqual((found.smiles, found.molfile), ("", ""))

    def test_rdkit_reads_each_molfile_as_the_substances_formula(self) -> None:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
        for found in Substance.objects.exclude(smiles=""):
            with self.subTest(key=found.key):
                molecule = Chem.MolFromMolBlock(found.molfile)
                self.assertIsNotNone(molecule)
                self.assertEqual(
                    rdMolDescriptors.CalcMolFormula(molecule),
                    found.formula)
