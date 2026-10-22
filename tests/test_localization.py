"""German localization without a build (localization): translated file
names and sections in the validator, translation checks, German stubs and
templates, PDF jobs of translations, and the site's language settings,
interface strings and vocabulary labels."""

import contextlib
import datetime as dt
import re
import tempfile
import tomllib
import unittest
from collections.abc import Iterator
from pathlib import Path

import support
from pipeline_support import REPO, front_matter, pipeline
from support import BASELINE, ValidatorTestCase, fixture_run
from test_pipeline_logic import NOW, make_repo, new

GERMAN_SECTIONS = ["Zusammenfassung", "Reagenzien", "Durchführung",
                   "Aufarbeitung und Reinigung", "Charakterisierung",
                   "Anmerkungen", "Gefahren und Entsorgung", "Literatur"]
ENGLISH_SECTIONS = ["Summary", "Reagents", "Procedure",
                    "Workup and Purification", "Characterization", "Notes",
                    "Hazards and Waste Disposal", "References"]
SITE = REPO / "site"
I18N = SITE / "i18n"
LAYOUTS = SITE / "layouts"
GERMAN_MD_TEMPLATE = REPO / "templates" / "procedure.de.md"
GERMAN_ORG_TEMPLATE = REPO / "templates" / "procedure.de.org"


def baseline(*edits) -> str:
    return support.apply_edits(BASELINE.read_text(encoding="utf-8"), edits)


def germanised(text: str) -> str:
    """``text`` with its English section headings put into German."""
    for english, german in zip(ENGLISH_SECTIONS, GERMAN_SECTIONS):
        text = text.replace(f"## {english}\n", f"## {german}\n")
    return text


def replace(key: str, line: str):
    return support.replace_line(key, line)


@contextlib.contextmanager
def root_of(files: dict[str, str]) -> Iterator[Path]:
    """A fresh content root holding ``files`` (name to text)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "content"
        root.mkdir()
        for name, text in files.items():
            (root / name).write_text(text, encoding="utf-8")
        yield root


def run(files: dict[str, str]) -> support.Result:
    with root_of(files) as root:
        return fixture_run(root)


class TranslatedFileTests(ValidatorTestCase):
    def test_german_file_with_german_sections_is_clean(self) -> None:
        """Scenario: A German procedure has German sections."""
        self.assert_clean(run({"OSDB-0100-baseline.de.md":
                               germanised(baseline())}))

    def test_german_file_with_english_sections_is_warned(self) -> None:
        """Scenario: A German procedure has German sections (English
        headings)."""
        result = run({"OSDB-0100-baseline.de.md": baseline()})
        self.assertEqual(result.returncode, 0, result.stdout)
        missing = sorted(p.message for p in result.problems
                         if p.field == "body")
        self.assertEqual(missing, sorted(
            f'missing section "{name}"' for name in GERMAN_SECTIONS))

    def test_language_codes_in_file_names(self) -> None:
        """Scenario: Language code in a file name."""
        for name, text in (("OSDB-0100-baseline.en.md", "drop the language"),
                           ("OSDB-0100-baseline.fr.md",
                            'unknown language code ".fr"')):
            with self.subTest(name=name):
                self.assert_one(run({name: baseline()}), "error",
                                "file_name", text)

    def test_a_translation_shares_its_id(self) -> None:
        """Scenario: A translation shares its ID and facts."""
        self.assert_clean(run({
            "OSDB-0100-baseline.md": baseline(),
            "OSDB-0100-baseline.de.md": germanised(baseline(
                replace("title", 'title = "Essigsäureethylester"'),
                replace("name", 'name = "Essigsäureethylester"'),
                replace("hazards", 'hazards = ["Entzündbare Flüssigkeit"]'),
                replace("scale", 'scale = "25,0 mmol"'),
                replace("authors", 'authors = ["Ü. Example"]'))),
        }))

    def test_two_files_of_one_language_with_one_id(self) -> None:
        """Scenario: Duplicate ID within one language."""
        result = run({"OSDB-0100-baseline.de.md": germanised(baseline()),
                      "OSDB-0100-copy.de.md": germanised(baseline())})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sorted(p.field for p in result.problems),
                         ["id", "id"], result.stdout)
        self.assertIn("duplicate id OSDB-0100", result.problems[0].message)

    def test_a_translation_must_have_the_original_base_name(self) -> None:
        """Scenario: A translation is named after its original."""
        problem = self.assert_one(
            run({"OSDB-0100-baseline.md": baseline(),
                 "OSDB-0100-other.de.md": germanised(baseline())}),
            "error", "file_name", "OSDB-0100-baseline.de.md")
        self.assertTrue(problem.path.endswith("OSDB-0100-other.de.md"))

    def test_shared_fields_must_agree(self) -> None:
        """Scenario: A translation shares its ID and facts (a differing
        fact)."""
        for field, edit in (
                ("yield_percent", replace("yield_percent",
                                          "yield_percent = 80")),
                ("status", replace("status", 'status = "checked"')),
                ("tags", replace("tags", 'tags = ["beispiel"]')),
                ("product.mw", replace("mw", "mw = 88.1")),
                ("precursors", support.insert_line(
                    'precursors = ["OSDB-0100"]'))):
            with self.subTest(field=field):
                result = run({"OSDB-0100-baseline.md": baseline(),
                              "OSDB-0100-baseline.de.md":
                              germanised(baseline(edit))})
                errors = [p for p in result.problems if p.field == field]
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertTrue(errors, result.stdout)
                self.assertTrue(all(p.path.endswith(".de.md")
                                    for p in errors), result.stdout)
                if field != "precursors":
                    self.assertIn("OSDB-0100-baseline.md",
                                  errors[0].message)

    def test_a_german_only_procedure_is_a_valid_precursor(self) -> None:
        """Scenario: Precursors in any language."""
        self.assert_clean(run({
            "OSDB-0100-baseline.de.md": germanised(baseline()),
            "OSDB-0101-next.md": baseline(
                replace("id", 'id = "OSDB-0101"'),
                replace("slug", 'slug = "osdb-0101"'),
                support.insert_line('precursors = ["OSDB-0100"]')),
        }))

    def test_scale_with_a_decimal_comma(self) -> None:
        """Scenario: Scale with a decimal comma."""
        self.assert_clean(run({"OSDB-0100-baseline.md": baseline(
            replace("scale", 'scale = "2,5 mmol"'))}))

    def test_german_org_source_and_its_export(self) -> None:
        """Scenario: A German Org source is exported under its own name."""
        with tempfile.TemporaryDirectory() as tmp:
            org = Path(tmp) / "org"
            org.mkdir()
            text = (REPO / "templates" / "procedure.de.org").read_text(
                encoding="utf-8").replace("OSDB-0000", "OSDB-0001")
            (org / "OSDB-0001-produkt.de.org").write_text(
                text, encoding="utf-8")
            self.assert_clean(fixture_run(org_roots=[org]))
            export = Path(tmp) / "export"
            export.mkdir()
            result = fixture_run(export, org_roots=[org])
        self.assert_one(result, "error", "file_name",
                        "no exported content file OSDB-0001-produkt.de.md")

    def test_empty_german_label_is_a_configuration_error(self) -> None:
        """Scenario: Vocabulary with German labels."""
        with tempfile.TemporaryDirectory() as tmp:
            vocabulary = Path(tmp) / "reaction_types.toml"
            vocabulary.write_text('[esterification]\nlabel = "E"\n'
                                  'label_de = " "\n', encoding="utf-8")
            with root_of({"OSDB-0100-baseline.md": baseline()}) as root:
                result = support.run_validator(
                    ["--vocabulary", vocabulary, root])
        self.assertEqual(result.returncode, 2)
        self.assertIn("label_de", result.stderr)


class GermanStubTests(unittest.TestCase):
    def test_german_stubs_are_filled_and_valid(self) -> None:
        """Scenario: German stub."""
        root = make_repo(self, trees=True)
        result = new(root, "--lang", "de", "--now", NOW, "Größe Säure")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "org/procedures/OSDB-0001-groesse-saeure.de.org")
        stub = root / result.stdout.strip()
        text = stub.read_text(encoding="utf-8")
        self.assertIn("#+TITLE: Größe Säure\n", text)
        self.assertIn("#+CREATED: [2026-10-19 Mon 17:42:05]\n", text)
        self.assertIn("* Zusammenfassung\n", text)
        checked = support.run_validator(["--org-root", stub.parent])
        self.assertEqual((checked.returncode, checked.stdout), (0, ""),
                         checked.stderr)

        result = new(root, "--md", "--lang", "de", "--now", NOW, "Ölsäure")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "md/procedures/OSDB-0002-oelsaeure.de.md")
        stub = root / result.stdout.strip()
        data = front_matter(stub.read_text(encoding="utf-8"))
        self.assertEqual(data["title"], "Ölsäure")
        self.assertEqual(data["date"], dt.datetime.fromisoformat(NOW))
        checked = support.run_validator([stub.parent])
        self.assertEqual((checked.returncode, checked.stdout), (0, ""),
                         checked.stderr)

    def test_unknown_language_is_a_usage_error(self) -> None:
        """Scenario: German stub (unknown language)."""
        root = make_repo(self)
        result = new(root, "--lang", "fr", "Test")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--lang", result.stderr)

    def test_german_slugs_write_out_umlauts(self) -> None:
        """Scenario: German stub (slug)."""
        self.assertEqual(pipeline().slugify("Größe Äpfel", "de"),
                         "groesse-aepfel")
        self.assertEqual(pipeline().slugify("Ethyl acetate", "de"),
                         "ethyl-acetate")


class GermanTemplateTests(ValidatorTestCase):
    def test_german_markdown_template_is_clean(self) -> None:
        """Scenario: German templates."""
        text = GERMAN_MD_TEMPLATE.read_text(encoding="utf-8").replace(
            "OSDB-0000", "OSDB-0001").replace("osdb-0000", "osdb-0001")
        self.assert_clean(run({"OSDB-0001-vorlage.de.md": text}))
        headings = re.findall(r"(?m)^## (.+)$", text)
        self.assertEqual(headings, GERMAN_SECTIONS)

    def test_german_org_template_mirrors_the_english_one(self) -> None:
        """Scenario: German templates (Org)."""
        german = GERMAN_ORG_TEMPLATE.read_text(encoding="utf-8")
        english = (REPO / "templates" / "procedure.org").read_text(
            encoding="utf-8")
        self.assertEqual(re.findall(r"(?m)^\* (.+)$", german),
                         GERMAN_SECTIONS)

        def keys(text: str) -> list[str]:
            return re.findall(r"(?m)^#\+([A-Z_]+):", text)

        self.assertEqual(keys(german), keys(english))
        model = re.search(r"(?m)^#\+AI_MODEL: (.+)$", german).group(1)
        self.assertNotEqual(model, "none")


class TranslationPdfJobTests(unittest.TestCase):
    def test_a_translation_prints_its_own_page(self) -> None:
        """Scenario: PDF of a translation."""
        with tempfile.TemporaryDirectory(prefix="pdf jobs ") as tmp:
            public, out = Path(tmp) / "public", Path(tmp) / "pdf"
            page = public / "de" / "procedures" / "osdb-0002" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text("<html></html>")
            jobs = pipeline().pdf_jobs(
                [(Path("md/procedures/OSDB-0002-aspirin.de.md"),
                  {"slug": "osdb-0002"})], public, out)
        self.assertEqual([(Path(j.html), Path(j.pdf)) for j in jobs],
                         [(page, out / "OSDB-0002-aspirin.de.pdf")])


class SiteLanguageTests(unittest.TestCase):
    def config(self) -> dict:
        return tomllib.loads((SITE / "hugo.toml").read_text(encoding="utf-8"))

    def test_languages_are_configured(self) -> None:
        """Scenario: Site languages."""
        config = self.config()
        self.assertEqual(config.get("defaultContentLanguage"), "en")
        self.assertIs(config.get("defaultContentLanguageInSubdir"), False)
        self.assertIs(config.get("disableDefaultLanguageRedirect"), True)
        self.assertEqual(config.get("languages"), {
            "en": {"label": "English", "locale": "en", "weight": 1},
            "de": {"label": "Deutsch", "locale": "de", "weight": 2}})

    def strings(self, language: str) -> dict[str, str]:
        return tomllib.loads((I18N / f"{language}.toml")
                             .read_text(encoding="utf-8"))

    def test_both_languages_have_every_interface_string(self) -> None:
        """Scenario: Interface strings."""
        english, german = self.strings("en"), self.strings("de")
        self.assertEqual(sorted(english), sorted(german))
        for language, table in (("en", english), ("de", german)):
            for key, value in table.items():
                with self.subTest(language=language, key=key):
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip())
        used = set()
        for path in LAYOUTS.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            used |= set(re.findall(r'\bT "([a-z_]+)"', text))
            used |= {f"status_{s}" for s in ("draft", "checked", "retired")
                     if "status-label.html" in text}
        self.assertTrue(used)
        self.assertEqual(sorted(used - set(english)), [])

    def test_every_reaction_type_has_a_german_label(self) -> None:
        """Scenario: Vocabulary with German labels."""
        data = tomllib.loads((SITE / "data" / "reaction_types.toml")
                             .read_text(encoding="utf-8"))
        for slug, entry in data.items():
            with self.subTest(slug=slug):
                self.assertTrue(entry.get("label_de", "").strip())

    def test_every_site_page_has_a_german_twin(self) -> None:
        """Scenario: Site languages (content pages)."""
        content = SITE / "content"
        for page in content.rglob("*.md"):
            if page.name.endswith(".de.md"):
                continue
            twin = page.with_name(page.stem + ".de.md")
            with self.subTest(page=str(page.relative_to(content))):
                self.assertTrue(twin.is_file())
        for taxonomy in ("tags", "authors", "reaction_types"):
            self.assertTrue((content / taxonomy / "_index.de.md").is_file(),
                            taxonomy)


if __name__ == "__main__":
    unittest.main()
