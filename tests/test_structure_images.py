"""Structure images in the build (compound-registry "Structure images",
site-build "Hugo configuration", sample-procedures "Test collection").

The staging of the images, ``pipeline.stage_structures``, is driven
in-process against temporary collections, a snapshot file or a local
server that serves the lab's image addresses; the builds that the
scenarios name run ``tools/orgsyndb build`` on copies of the test
collection and skip, naming the missing tool, without Hugo and the cached
Pagefind binary.
"""

import json
import os
import re
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

import pipeline_support as ps
import support
from pipeline_support import (MOLFILE, REPO, TEST_COLLECTION, SnapshotServer,
                              captured, make_sandbox, name_registry,
                              pipeline_function, serve_snapshot,
                              with_molfiles)
from support import REGISTRY, load_snapshot

ETHANOL, ETHYL_ACETATE = "ethanol", "ethyl-acetate"
DEMO_IMAGE = (REPO / "webapp" / "demo" / "substances"
              / "isopentyl-acetate" / "structure.svg")
# Bytes that a text-mode copy would change: CR LF and a multi-byte
# character.
SVG_ONE = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
           b'\r\n<title>one \xe2\x9c\x93</title></svg>\n')
SVG_TWO = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 2">'
           b'<title>two</title></svg>\n')
SVG_THREE = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 3">'
             b'<title>three</title></svg>\n')


def staged_files(collection: Path) -> dict[str, bytes]:
    """Every file below the collection's ``build/substances/``, by
    relative path."""
    root = collection / "build" / "substances"
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


class StagingCase(unittest.TestCase):
    """A temporary collection whose registry the tests name, and the
    staging of its images."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="orgsyndb images "))
        self.addCleanup(shutil.rmtree, self.root, True)
        patch = unittest.mock.patch.dict(os.environ)
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop("ORGSYNDB_REGISTRY", None)
        self.table = load_snapshot(REGISTRY)

    def settings(self, registry: str) -> None:
        """Write the collection's ``orgsyndb.toml`` naming REGISTRY."""
        (self.root / "orgsyndb.toml").write_text(
            f"format = 1\nregistry = {json.dumps(registry)}\n",
            encoding="utf-8")

    def stage(self, table: dict[str, Any] | None = None
              ) -> tuple[str, str]:
        """Stage the images of TABLE, the table the test serves or wrote
        unless given; return what the staging wrote to stdout and
        stderr."""
        _, out, err = captured(pipeline_function("stage_structures"),
                               self.root, self.table if table is None
                               else table)
        return out, err

    def staged(self) -> dict[str, bytes]:
        return staged_files(self.root)

    def warning_lines(self, err: str) -> list[str]:
        return [line for line in err.splitlines() if line.strip()]

    def count_in(self, line: str, address: str) -> set[str]:
        """The whole numbers LINE names besides ADDRESS."""
        return set(re.findall(r"\b\d+\b", line.replace(address, "")))


class FileStagingTests(StagingCase):
    """A registry named by a path (compound-registry "Structure
    images": images beside a snapshot file)."""

    def setUp(self) -> None:
        super().setUp()
        self.settings("registry.json")

    def write_table(self, *keys: str, path: Path | None = None) -> None:
        self.table = with_molfiles(self.table, *keys)
        (path or self.root / "registry.json").write_text(
            json.dumps(self.table), encoding="utf-8")

    def put(self, key: str, body: bytes, beside: Path | None = None
            ) -> Path:
        target = (beside or self.root) / "substances" / key / "structure.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        return target

    def test_an_image_beside_the_file_is_staged_byte_for_byte(self) -> None:
        """Scenario: Images beside a snapshot file (the build stages a
        copy of it)."""
        self.write_table(ETHANOL, ETHYL_ACETATE)
        self.put(ETHANOL, SVG_ONE)
        self.put(ETHYL_ACETATE, SVG_TWO)
        out, err = self.stage()
        self.assertEqual(self.staged(), {
            f"{ETHANOL}/structure.svg": SVG_ONE,
            f"{ETHYL_ACETATE}/structure.svg": SVG_TWO})
        self.assertEqual(err, "")

    def test_a_substance_without_the_file_has_none_and_no_warning(
            self) -> None:
        """Scenario: Images beside a snapshot file (a substance without
        that file has no structure image, and stderr holds no
        warning)."""
        self.write_table(ETHANOL, ETHYL_ACETATE)
        self.put(ETHANOL, SVG_ONE)
        out, err = self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_ONE})
        self.assertEqual(err, "")
        self.assertEqual(out, "")

    def test_a_staged_image_without_its_file_is_removed(self) -> None:
        """Requirement: Structure images (a substance without that file
        has its staged image removed)."""
        self.write_table(ETHANOL, ETHYL_ACETATE)
        self.put(ETHANOL, SVG_ONE)
        self.put(ETHYL_ACETATE, SVG_TWO)
        self.stage()
        (self.root / "substances" / ETHANOL / "structure.svg").unlink()
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})

    def test_a_new_file_replaces_the_staged_copy(self) -> None:
        """Requirement: Structure images (the build stages a copy of the
        file)."""
        self.write_table(ETHANOL)
        self.put(ETHANOL, SVG_ONE)
        self.stage()
        self.put(ETHANOL, SVG_THREE)
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_THREE})

    def test_only_a_molfile_makes_an_image(self) -> None:
        """Requirement: Structure images (a substance has a structure
        image only when its `molfile` is a string)."""
        self.write_table(ETHYL_ACETATE)
        self.put(ETHANOL, SVG_ONE)
        self.put(ETHYL_ACETATE, SVG_TWO)
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})
        # A snapshot written before substances had molfiles names none.
        self.table = load_snapshot(REGISTRY)
        self.assertNotIn("molfile", self.table["substances"][0])
        out, err = self.stage()
        self.assertEqual(self.staged(), {})
        self.assertEqual(err, "")

    def test_a_null_molfile_removes_the_image(self) -> None:
        """Scenario: A structure removed (from a snapshot file)."""
        self.write_table(ETHANOL, ETHYL_ACETATE)
        self.put(ETHANOL, SVG_ONE)
        self.put(ETHYL_ACETATE, SVG_TWO)
        self.stage()
        self.write_table(ETHYL_ACETATE)
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})

    def test_everything_that_is_no_image_of_a_molfile_is_removed(
            self) -> None:
        """Requirement: Structure images (removes from
        `build/substances/` everything that is not the image of a
        substance with a molfile)."""
        self.write_table(ETHYL_ACETATE)
        self.put(ETHYL_ACETATE, SVG_TWO)
        staged = self.root / "build" / "substances"
        for name, body in (("stray.txt", b"x"),
                           ("gone/structure.svg", SVG_ONE),
                           (f"{ETHYL_ACETATE}/extra.txt", b"x"),
                           (f"{ETHYL_ACETATE}/structure.png", b"x"),
                           (f"{ETHANOL}/structure.svg", SVG_ONE)):
            (staged / name).parent.mkdir(parents=True, exist_ok=True)
            (staged / name).write_bytes(body)
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})

    def test_the_directory_is_created_when_it_is_missing(self) -> None:
        """Requirement: Structure images (creating `build/substances/`
        when it is missing)."""
        self.write_table()
        self.assertFalse((self.root / "build").exists())
        self.stage()
        self.assertTrue((self.root / "build" / "substances").is_dir())
        self.assertEqual(self.staged(), {})

    def test_the_images_lie_beside_a_file_outside_the_collection(
            self) -> None:
        """Requirement: Structure images (the snapshot file's
        directory)."""
        outer = self.root
        collection, shared = outer / "collection", outer / "shared"
        collection.mkdir()
        shared.mkdir()
        self.root = collection
        self.settings("../shared/registry.json")
        self.write_table(ETHANOL, path=shared / "registry.json")
        self.put(ETHANOL, SVG_ONE, beside=shared)
        self.put(ETHANOL, SVG_THREE)
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_ONE})

    def test_the_environment_names_the_file_the_images_lie_beside(
            self) -> None:
        """Requirement: Structure images (the registry is the source of
        `registry_source`, `ORGSYNDB_REGISTRY` included)."""
        other = self.root / "other"
        other.mkdir()
        self.write_table(ETHANOL, path=other / "snapshot.json")
        self.put(ETHANOL, SVG_ONE, beside=other)
        self.put(ETHANOL, SVG_THREE)
        os.environ["ORGSYNDB_REGISTRY"] = str(other / "snapshot.json")
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_ONE})


class AddressStagingTests(StagingCase):
    """A registry named by an address (compound-registry "Structure
    images": images from the lab)."""

    def serve(self, *keys: str, path: str | None = None
              ) -> SnapshotServer:
        """Serve a snapshot in which KEYS have a molfile, with an image
        for each; the collection names its address."""
        self.table = with_molfiles(self.table, *keys)
        server = SnapshotServer(self.table, path)
        self.addCleanup(server.stop)
        for number, key in enumerate(keys):
            server.images[key] = (SVG_ONE, SVG_TWO, SVG_THREE)[number % 3]
        self.settings(server.url)
        return server

    def only_warning(self, err: str) -> str:
        lines = self.warning_lines(err)
        self.assertEqual(len(lines), 1, err)
        self.assertIn("warning", lines[0].lower())
        return lines[0]

    def test_images_are_requested_beside_the_snapshot_and_staged(
            self) -> None:
        """Scenario: Images from the lab (the body of an answer of
        status 200 is staged)."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        out, err = self.stage()
        self.assertEqual(self.staged(), {
            f"{ETHANOL}/structure.svg": SVG_ONE,
            f"{ETHYL_ACETATE}/structure.svg": SVG_TWO})
        self.assertEqual([key for key, _ in server.image_requests],
                         [ETHANOL, ETHYL_ACETATE])
        self.assertEqual(err, "")
        self.assertEqual(out, "")

    def test_the_address_is_resolved_against_the_snapshots(self) -> None:
        """Requirement: Structure images (`substances/<key>/
        structure.svg` resolved against that address)."""
        server = self.serve(ETHANOL, path="/some/where/snapshot.json")
        self.assertTrue(server.url.endswith("/some/where/snapshot.json"))
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_ONE})
        self.assertEqual([key for key, _ in server.image_requests],
                         [ETHANOL])

    def test_a_substance_without_a_molfile_is_not_requested(self) -> None:
        """Requirement: Structure images (a substance with a molfile has
        the image that answers a GET)."""
        server = self.serve(ETHYL_ACETATE)
        server.images[ETHANOL] = SVG_ONE
        self.stage()
        self.assertEqual([key for key, _ in server.image_requests],
                         [ETHYL_ACETATE])
        self.assertEqual(list(self.staged()),
                         [f"{ETHYL_ACETATE}/structure.svg"])

    def test_everything_that_is_no_image_of_a_molfile_is_removed(
            self) -> None:
        """Requirement: Structure images (it removes everything else
        from `build/substances/`)."""
        self.serve(ETHYL_ACETATE)
        staged = self.root / "build" / "substances"
        for name in ("stray.txt", "gone/structure.svg",
                     f"{ETHANOL}/structure.svg"):
            (staged / name).parent.mkdir(parents=True, exist_ok=True)
            (staged / name).write_bytes(b"old")
        self.stage()
        self.assertEqual(list(self.staged()),
                         [f"{ETHYL_ACETATE}/structure.svg"])

    def test_an_answer_other_than_200_keeps_the_earlier_image(self) -> None:
        """Requirement: Structure images (keeps the image an earlier
        build staged; one warning names how many were not staged and the
        first one's address with the reason)."""
        server = self.serve(ETHANOL)
        self.stage()
        for status in (404, 500, 403):
            with self.subTest(status=status):
                server.image_status = status
                out, err = self.stage()
                self.assertEqual(self.staged(), {
                    f"{ETHANOL}/structure.svg": SVG_ONE})
                line = self.only_warning(err)
                address = server.image_url(ETHANOL)
                self.assertIn(address, line)
                self.assertIn(str(status), line.replace(address, ""))
                self.assertIn("1", self.count_in(line, address))
                self.assertEqual(out, "")

    def test_an_answer_other_than_200_does_not_stop_the_requests(
            self) -> None:
        """Requirement: Structure images (only a request that gets no
        answer ends the requests of that run)."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        server.image_statuses[ETHANOL] = 404
        out, err = self.stage()
        self.assertEqual([key for key, _ in server.image_requests],
                         [ETHANOL, ETHYL_ACETATE])
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})
        line = self.only_warning(err)
        self.assertIn(server.image_url(ETHANOL), line)
        self.assertNotIn(server.image_url(ETHYL_ACETATE), line)
        self.assertIn("1", self.count_in(line, server.image_url(ETHANOL)))

    def test_the_warning_names_the_first_image_of_several(self) -> None:
        """Requirement: Structure images (how many were not staged and
        the first one's address)."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        server.image_status = 500
        out, err = self.stage()
        self.assertEqual(self.staged(), {})
        line = self.only_warning(err)
        self.assertIn(server.image_url(ETHANOL), line)
        self.assertNotIn(server.image_url(ETHYL_ACETATE), line)
        self.assertIn("2", self.count_in(
            line, server.image_url(ETHANOL)) - {"500"})

    def test_a_lab_that_stops_answering(self) -> None:
        """Scenario: A lab that stops answering."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        server.image_drop = True
        out, err = self.stage()
        self.assertEqual(len(server.image_requests), 1)
        self.assertEqual(self.staged(), {})
        line = self.only_warning(err)
        address = server.image_url(ETHANOL)
        self.assertIn(address, line)
        self.assertIn("2", self.count_in(line, address))

    def test_a_lab_that_stops_answering_leaves_the_earlier_images(
            self) -> None:
        """Requirement: Structure images (a substance that gets no
        answer keeps the image an earlier build staged)."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        self.stage()
        server.image_drop = True
        server.image_requests.clear()
        out, err = self.stage()
        self.assertEqual(len(server.image_requests), 1)
        self.assertEqual(self.staged(), {
            f"{ETHANOL}/structure.svg": SVG_ONE,
            f"{ETHYL_ACETATE}/structure.svg": SVG_TWO})
        self.assertIn("2", self.count_in(self.only_warning(err),
                                         server.image_url(ETHANOL)))

    def test_a_lab_that_is_down_leaves_the_earlier_images(self) -> None:
        """Scenario: The lab is down (the staging keeps the images)."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        self.stage()
        server.stop()
        out, err = self.stage()
        self.assertEqual(self.staged(), {
            f"{ETHANOL}/structure.svg": SVG_ONE,
            f"{ETHYL_ACETATE}/structure.svg": SVG_TWO})
        line = self.only_warning(err)
        self.assertIn(server.image_url(ETHANOL), line)
        self.assertNotIn(server.image_url(ETHYL_ACETATE), line)

    def test_a_lab_that_is_down_without_images_stages_none(self) -> None:
        """Requirement: Structure images (no earlier image, no staged
        image)."""
        server = self.serve(ETHANOL)
        server.stop()
        out, err = self.stage()
        self.assertEqual(self.staged(), {})
        self.assertIn(server.image_url(ETHANOL), self.only_warning(err))

    def test_a_structure_removed_loses_its_image(self) -> None:
        """Scenario: A structure removed."""
        server = self.serve(ETHANOL, ETHYL_ACETATE)
        self.stage()
        server.table = self.table = with_molfiles(self.table, ETHYL_ACETATE)
        server.image_requests.clear()
        out, err = self.stage()
        self.assertEqual(self.staged(), {f"{ETHYL_ACETATE}/structure.svg":
                                         SVG_TWO})
        self.assertEqual([key for key, _ in server.image_requests],
                         [ETHYL_ACETATE])
        self.assertEqual(err, "")

    def test_a_new_answer_replaces_the_staged_image(self) -> None:
        """Requirement: Structure images (stages the body of an answer of
        status 200)."""
        server = self.serve(ETHANOL)
        self.stage()
        server.images[ETHANOL] = SVG_THREE
        self.stage()
        self.assertEqual(self.staged(), {f"{ETHANOL}/structure.svg":
                                         SVG_THREE})

    def test_the_images_are_requested_with_the_snapshots_host(self) -> None:
        """Requirement: Structure images (a GET of the image beside the
        snapshot's address)."""
        server = self.serve(ETHANOL)
        self.stage()
        ((_, host),) = server.image_requests
        self.assertEqual(host, f"127.0.0.1:{server.port}")


class CompoundDataTests(unittest.TestCase):
    """``pipeline.compound_data(substance, staged)``."""

    def setUp(self) -> None:
        self.staged = Path(tempfile.mkdtemp(prefix="orgsyndb staged "))
        self.addCleanup(shutil.rmtree, self.staged, True)
        self.table = load_snapshot(REGISTRY)
        self.substances = {s["key"]: s for s in self.table["substances"]}

    def data(self, key: str) -> dict[str, Any]:
        return pipeline_function("compound_data")(self.substances[key],
                                                  self.staged)

    def stage(self, key: str, name: str = "structure.svg") -> None:
        (self.staged / key).mkdir(parents=True, exist_ok=True)
        (self.staged / key / name).write_bytes(SVG_ONE)

    def test_the_image_is_set_when_it_is_staged(self) -> None:
        """Requirement: Structure images (`structure_image` is
        `substances/<key>/structure.svg`)."""
        self.stage(ETHYL_ACETATE)
        self.assertEqual(self.data(ETHYL_ACETATE).get("structure_image"),
                         "substances/ethyl-acetate/structure.svg")

    def test_the_image_is_not_set_when_it_is_not_staged(self) -> None:
        """Requirement: Structure images (exactly when the staged image
        exists)."""
        self.stage(ETHYL_ACETATE)
        self.assertNotIn("structure_image", self.data(ETHANOL))
        (self.staged / ETHANOL).mkdir()
        self.assertNotIn("structure_image", self.data(ETHANOL))
        self.stage(ETHANOL, "structure.png")
        self.assertNotIn("structure_image", self.data(ETHANOL))

    def test_a_missing_directory_sets_no_image(self) -> None:
        """Requirement: Structure images (the staged directory may not
        exist before a build)."""
        shutil.rmtree(self.staged)
        self.assertNotIn("structure_image", self.data(ETHANOL))

    def test_the_staged_file_decides_not_the_molfile(self) -> None:
        """Requirement: Hugo configuration (`structure_image` when the
        build staged that image)."""
        self.substances[ETHANOL]["molfile"] = None
        self.stage(ETHANOL)
        self.assertEqual(self.data(ETHANOL).get("structure_image"),
                         "substances/ethanol/structure.svg")
        self.substances[ETHYL_ACETATE]["molfile"] = MOLFILE
        self.assertNotIn("structure_image", self.data(ETHYL_ACETATE))

    def test_the_other_values_stay_and_the_molfile_is_not_among_them(
            self) -> None:
        """Requirement: Hugo configuration (the values staged for a
        substance)."""
        every = with_molfiles(self.table, *self.substances)
        for entry in every["substances"]:
            with self.subTest(compound=entry["key"]):
                self.assertEqual(
                    pipeline_function("compound_data")(entry, self.staged),
                    ps.compounds_of(every, None)[entry["key"]])


class HelperTests(unittest.TestCase):
    """The harness helpers that keep a registry's images beside it."""

    def test_a_copy_keeps_the_images_beside_the_demo_registry(self) -> None:
        """Requirement: Test collection (images beside the registry);
        `keep_registry_inside` copies `substances/` along with the JSON."""
        base = Path(tempfile.mkdtemp(prefix="orgsyndb keep "))
        self.addCleanup(shutil.rmtree, base, True)
        copy = base / "collection copy"
        shutil.copytree(ps.DEMO, copy,
                        ignore=shutil.ignore_patterns("build", "public",
                                                      "pdf"))
        ps.keep_registry_inside(ps.DEMO, copy)
        image = copy / "substances" / "isopentyl-acetate" / "structure.svg"
        self.assertTrue(image.is_file(), "no image beside the registry")
        self.assertEqual(image.read_bytes(), DEMO_IMAGE.read_bytes())
        self.assertEqual(ps.collection_registry(copy), copy / "registry.json")
        self.assertTrue((copy / "registry.json").is_file())

    def test_put_compounds_places_the_image_beside_the_registry(
            self) -> None:
        """Harness: fixture images go beside the sandbox's registry, and
        their substances get a molfile."""
        sandbox = make_sandbox(self)
        ps.edit_snapshot(sandbox, support.without_substance(ETHYL_ACETATE),
                         support.without_substance(ETHANOL))
        added = ps.put_compounds(sandbox, ETHYL_ACETATE, "trans-stilbene",
                                 ETHANOL)
        self.assertIn(ETHYL_ACETATE, added)
        table = ps.read_snapshot(sandbox)
        held = {s["key"]: s for s in table["substances"]}
        for key in (ETHYL_ACETATE, "trans-stilbene"):
            with self.subTest(compound=key):
                self.assertEqual(
                    (sandbox.root / "substances" / key
                     / "structure.svg").read_bytes(),
                    (ps.FIXTURE_STATIC / "structures" / f"{key}.svg"
                     ).read_bytes())
                self.assertIsInstance(held[key]["molfile"], str)
                self.assertFalse((sandbox.root / "static" / "structures"
                                  / f"{key}.svg").exists())
        self.assertNotIsInstance(held[ETHANOL].get("molfile"), str)
        self.assertFalse(
            (sandbox.root / "substances" / ETHANOL).exists())
        self.assertEqual(table["digest"], ps.snapshot_digest(table))


LAB_SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 9 9" '
           b'role="img"><title>from the lab</title></svg>\n')


class LabBuildCase(unittest.TestCase):
    """A build of a copy of the test collection that names the address
    of a local server, which serves a snapshot of its registry in which
    ``KEYS`` have a molfile and every other substance the ``molfile``
    ``null``, and an image for each of ``KEYS``."""

    KEYS = ("isopentyl-acetate",)

    @classmethod
    def setUpClass(cls) -> None:
        ps.require_builder()

    def setUp(self) -> None:
        self.sandbox = make_sandbox(self)
        self.table = with_molfiles(
            load_snapshot(TEST_COLLECTION / "registry.json"), *self.KEYS)
        self.server = serve_snapshot(self, self.table)
        for key in self.KEYS:
            self.server.images[key] = LAB_SVG
        name_registry(self.sandbox.root, self.server.url)

    def build(self) -> ps.Run:
        env = self.sandbox.env()
        env.pop("ORGSYNDB_REGISTRY", None)
        result = self.sandbox.build("build", env=env)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        return result

    def public(self, *parts: str) -> Path:
        return self.sandbox.root / "public" / Path(*parts)

    def published(self, key: str) -> bytes:
        """The bytes of the published image of the substance ``key``."""
        path = self.public("substances", key, "structure.svg")
        self.assertTrue(path.is_file(), f"{path} was not published")
        return path.read_bytes()

    def compound(self, key: str) -> dict[str, Any]:
        return json.loads((self.sandbox.root / "build" / "data"
                           / "compounds" / f"{key}.json").read_text(
                               encoding="utf-8"))

    def staged(self) -> dict[str, bytes]:
        return staged_files(self.sandbox.root)

    def lines_naming(self, text: str, needle: str) -> list[str]:
        return [line for line in text.splitlines() if needle in line]


class ImagesFromTheLabTests(LabBuildCase):
    def test_the_served_image_is_published(self) -> None:
        """Scenario: Images from the lab."""
        result = self.build()
        key = "isopentyl-acetate"
        self.assertEqual(self.published(key), LAB_SVG)
        self.assertNotEqual(
            (self.sandbox.root / "substances" / key / "structure.svg"
             ).read_bytes(), LAB_SVG, "the image beside the file is served")
        self.assertEqual(self.compound(key)["structure_image"],
                         f"substances/{key}/structure.svg")
        self.assertEqual(self.staged(), {f"{key}/structure.svg": LAB_SVG})
        self.assertEqual([k for k, _ in self.server.image_requests], [key])
        self.assertEqual(self.lines_naming(result.stderr, "structure"), [])
        others = sorted((self.sandbox.root / "build" / "data"
                         / "compounds").glob("*.json"))
        self.assertGreater(len(others), 1)
        for path in others:
            if path.stem != key:
                with self.subTest(compound=path.stem):
                    self.assertNotIn("structure_image", json.loads(
                        path.read_text(encoding="utf-8")))

    def test_the_published_page_shows_the_served_image(self) -> None:
        """Requirement: Structure image slot (the staged image is the
        procedure's)."""
        self.build()
        page = (self.public("procedures", "osdb-0003", "index.html")
                .read_text(encoding="utf-8"))
        self.assertTrue(
            "substances/isopentyl-acetate/structure.svg" in page,
            "the page does not name the staged image")


class TheLabIsDownTests(LabBuildCase):
    def test_the_last_images_stay(self) -> None:
        """Scenario: The lab is down."""
        key = "isopentyl-acetate"
        self.build()
        self.server.stop()
        result = self.build()
        self.assertEqual(self.published(key), LAB_SVG)
        self.assertEqual(self.compound(key)["structure_image"],
                         f"substances/{key}/structure.svg")
        self.assertIn("cannot read the registry", result.stderr)
        self.assertEqual(
            len(self.lines_naming(result.stderr,
                                  self.server.image_url(key))), 1,
            result.stderr)


class StoppedAnsweringTests(LabBuildCase):
    KEYS = ("acetone", "isopentyl-acetate")

    def test_one_request_and_a_warning_for_both(self) -> None:
        """Scenario: A lab that stops answering."""
        self.server.image_drop = True
        result = self.build()
        self.assertEqual(len(self.server.image_requests), 1)
        lines = self.lines_naming(result.stderr,
                                  self.server.image_url("acetone"))
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertIn("2", re.findall(
            r"\b\d+\b", lines[0].replace(
                self.server.image_url("acetone"), "")))
        self.assertEqual(self.lines_naming(
            result.stderr, self.server.image_url("isopentyl-acetate")), [])
        self.assertEqual(self.staged(), {})


class StructureRemovedTests(LabBuildCase):
    def test_the_image_goes_with_the_molfile(self) -> None:
        """Scenario: A structure removed."""
        key = "isopentyl-acetate"
        self.build()
        self.assertEqual(self.published(key), LAB_SVG)
        self.server.table = with_molfiles(self.table)
        before = len(self.server.image_requests)
        self.build()
        self.assertTrue((self.sandbox.root / "build" / "substances"
                         ).is_dir())
        self.assertEqual(self.staged(), {})
        self.assertFalse(self.public("substances", key,
                                     "structure.svg").exists())
        self.assertNotIn("structure_image", self.compound(key))
        self.assertEqual(len(self.server.image_requests), before)


class BesideTheFileBuildTests(unittest.TestCase):
    """Scenario: Images beside a snapshot file."""

    @classmethod
    def setUpClass(cls) -> None:
        ps.require_builder()

    def test_the_image_beside_the_file_is_published(self) -> None:
        sandbox = make_sandbox(self)
        root = sandbox.root
        ps.edit_snapshot(sandbox,
                         support.setting_substance(
                             "isopentyl-acetate", molfile=MOLFILE),
                         support.setting_substance("acetone",
                                                   molfile=MOLFILE))
        self.assertFalse((root / "substances" / "acetone").exists())
        (root / "static" / "structures" / "acetone.svg").write_bytes(SVG_ONE)
        env = sandbox.env()
        env.pop("ORGSYNDB_REGISTRY", None)
        result = sandbox.build("build", env=env)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        beside = root / "substances" / "isopentyl-acetate" / "structure.svg"
        published = root / "public" / "substances" / "isopentyl-acetate"
        self.assertTrue(beside.is_file(), "no image beside the registry")
        self.assertTrue((published / "structure.svg").is_file(),
                        "the image was not published")
        self.assertEqual((published / "structure.svg").read_bytes(),
                         beside.read_bytes())
        staged = root / "build" / "data" / "compounds"
        self.assertEqual(
            json.loads((staged / "isopentyl-acetate.json").read_text(
                encoding="utf-8"))["structure_image"],
            "substances/isopentyl-acetate/structure.svg")
        self.assertNotIn("structure_image", json.loads(
            (staged / "acetone.json").read_text(encoding="utf-8")))
        self.assertEqual(
            (root / "public" / "structures" / "acetone.svg").read_bytes(),
            SVG_ONE)
        self.assertFalse((root / "public" / "substances" / "acetone"
                          ).exists())
        warnings = [line for line in result.stderr.splitlines()
                    if re.search(r"image|structure", line, re.I)]
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
