"""Localization without a build (localization): language codes in file
names, sections and the language field in the validator, variant checks,
the choice and staging of variants, German stubs and templates, and the
site's locale, interface strings and vocabulary labels."""

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
        self.assert_clean(run({"OSDB-0100-baseline.en.md": baseline()}))
        self.assert_one(run({"OSDB-0100-baseline.fr.md": baseline()}),
                        "error", "file_name", 'unknown language code ".fr"')

    def test_an_untagged_file_may_use_either_set_of_sections(self) -> None:
        """Scenario: Sections of a file without a language code."""
        self.assert_clean(run({"OSDB-0100-baseline.md": baseline()}))
        self.assert_clean(run({"OSDB-0100-baseline.md":
                               germanised(baseline())}))
        result = run({"OSDB-0100-baseline.md": germanised(baseline()).replace(
            "## Anmerkungen\n", "## Notizen\n")})
        self.assert_one(result, "warning", "body",
                        'missing section "Anmerkungen"')

    def test_the_language_field(self) -> None:
        """Scenario: The language field."""
        self.assert_clean(run({"OSDB-0100-baseline.md": germanised(baseline(
            support.insert_line('language = "de"')))}))
        self.assert_one(run({"OSDB-0100-baseline.md": baseline(
            support.insert_line('language = "fr"'))}),
            "error", "language", "must be one of")
        self.assert_one(run({"OSDB-0100-baseline.de.md": germanised(baseline(
            support.insert_line('language = "en"')))}),
            "error", "language", 'does not match the language code ".de"')
        result = run({"OSDB-0100-baseline.md": baseline(
            support.insert_line('language = "de"'))})
        self.assertIn('missing section "Zusammenfassung"',
                      [p.message for p in result.problems])

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
        """Scenario: Variants share a base name."""
        problem = self.assert_one(
            run({"OSDB-0100-baseline.md": baseline(),
                 "OSDB-0100-other.de.md": germanised(baseline())}),
            "error", "file_name", "OSDB-0100-baseline.de.md")
        self.assertTrue(problem.path.endswith("OSDB-0100-other.de.md"))

    def test_variants_without_an_untagged_file(self) -> None:
        """Scenario: A translation shares its ID and facts (no untagged
        file)."""
        result = run({"OSDB-0100-baseline.de.md": germanised(baseline()),
                      "OSDB-0100-baseline.en.md": baseline(
                          replace("yield_percent", "yield_percent = 80"))})
        problem = self.assert_one(result, "error", "yield_percent",
                                  "OSDB-0100-baseline.de.md")
        self.assertTrue(problem.path.endswith("OSDB-0100-baseline.en.md"))

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

    def test_equal_numbers_of_either_type_agree(self) -> None:
        """Scenario: A translation shares its ID and facts (integer and
        float)."""
        self.assert_clean(run({
            "OSDB-0100-baseline.md": baseline(
                replace("yield_percent", "yield_percent = 85"),
                replace("mw", "mw = 88")),
            "OSDB-0100-baseline.de.md": germanised(baseline(
                replace("yield_percent", "yield_percent = 85.0"),
                replace("mw", "mw = 88.0"))),
        }))
        result = run({
            "OSDB-0100-baseline.md": baseline(),
            "OSDB-0100-baseline.de.md": germanised(baseline(
                replace("yield_percent", "yield_percent = true")))})
        self.assertIn(("yield_percent", "error"),
                      [(p.field, p.severity) for p in result.problems])

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
        result = new(root, "Größe Säure", lang="de")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "org/procedures/OSDB-0001-groesse-saeure.de.org")
        stub = root / result.stdout.strip()
        text = stub.read_text(encoding="utf-8")
        self.assertIn("#+TITLE: Größe Säure\n", text)
        self.assertIn("#+CREATED: [2026-10-19 Mon 17:42:05]\n", text)
        self.assertIn("* Zusammenfassung\n", text)

        result = new(root, "Ölsäure", md=True, lang="de")
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

    def test_an_english_stub_with_a_language_code(self) -> None:
        """Scenario: German stub (English with a code)."""
        root = make_repo(self, trees=True)
        result = new(root, "Ethyl acetate", lang="en")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "org/procedures/OSDB-0001-ethyl-acetate.en.org")
        text = (root / result.stdout.strip()).read_text(encoding="utf-8")
        self.assertIn("* Summary\n", text)

    def test_unknown_language_is_a_usage_error(self) -> None:
        """Scenario: German stub (unknown language)."""
        root = make_repo(self)
        result = new(root, "Test", lang="fr")
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


def pair(name: str, ident: str = "OSDB-0001") -> tuple[Path, dict]:
    return Path("md/procedures") / name, {"id": ident, "slug": ident.lower()}


class VariantChoiceTests(unittest.TestCase):
    def chosen(self, names: list[str], language: str) -> list[str]:
        return [path.name for path, _ in pipeline().choose_variants(
            [pair(name) for name in names], language)]

    def test_the_variant_for_the_locale_is_preferred(self) -> None:
        """Scenario: Choosing the variant to publish."""
        cases = [
            (["OSDB-0001-x.md"], "de", "OSDB-0001-x.md"),
            (["OSDB-0001-x.md", "OSDB-0001-x.de.md"], "de",
             "OSDB-0001-x.de.md"),
            (["OSDB-0001-x.md", "OSDB-0001-x.en.md"], "de",
             "OSDB-0001-x.md"),
            (["OSDB-0001-x.md", "OSDB-0001-x.de.md"], "en",
             "OSDB-0001-x.md"),
            (["OSDB-0001-x.en.md"], "de", "OSDB-0001-x.en.md"),
            (["OSDB-0001-x.en.md", "OSDB-0001-x.de.md"], "en",
             "OSDB-0001-x.en.md"),
        ]
        for names, language, expected in cases:
            with self.subTest(names=names, language=language):
                self.assertEqual(self.chosen(names, language), [expected])

    def test_every_id_is_published_once(self) -> None:
        """Scenario: Choosing the variant to publish (every ID)."""
        files = [pair("OSDB-0002-y.de.md", "OSDB-0002"),
                 pair("OSDB-0001-x.md"), pair("OSDB-0001-x.de.md"),
                 pair("OSDB-0003-z.en.md", "OSDB-0003")]
        chosen = pipeline().choose_variants(files, "de")
        self.assertEqual([p.name for p, _ in chosen],
                         ["OSDB-0001-x.de.md", "OSDB-0002-y.de.md",
                          "OSDB-0003-z.en.md"])

    def test_staged_files_lose_the_code_and_keep_the_language(self) -> None:
        """Scenario: Staging the chosen variants."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "md"
            source.mkdir()
            tagged = source / "OSDB-0001-x.de.md"
            tagged.write_text("+++\nid = \"OSDB-0001\"\n+++\nText\n",
                              encoding="utf-8")
            declared = source / "OSDB-0002-y.en.md"
            declared.write_text("+++\nlanguage = \"en\"\n+++\n",
                                encoding="utf-8")
            plain = source / "OSDB-0003-z.md"
            plain.write_text("+++\n+++\n", encoding="utf-8")
            target = Path(tmp) / "build" / "content" / "procedures"
            target.mkdir(parents=True)
            (target / "OSDB-0009-stale.md").write_text("x")
            pipeline().stage_content(
                [(tagged, {}), (declared, {"language": "en"}),
                 (plain, {})], target)
            names = sorted(p.name for p in target.iterdir())
            self.assertEqual(names, ["OSDB-0001-x.md", "OSDB-0002-y.md",
                                     "OSDB-0003-z.md"])
            self.assertEqual(
                (target / "OSDB-0001-x.md").read_text(encoding="utf-8"),
                '+++\nlanguage = "de"\nid = "OSDB-0001"\n+++\nText\n')
            self.assertEqual(
                (target / "OSDB-0002-y.md").read_text(encoding="utf-8"),
                declared.read_text(encoding="utf-8"))
            self.assertEqual(
                (target / "OSDB-0003-z.md").read_text(encoding="utf-8"),
                "+++\n+++\n")

    def test_a_translation_prints_under_its_own_name(self) -> None:
        """Scenario: PDF of a translation."""
        with tempfile.TemporaryDirectory(prefix="pdf jobs ") as tmp:
            public, out = Path(tmp) / "public", Path(tmp) / "pdf"
            page = public / "procedures" / "osdb-0002" / "index.html"
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

    def test_the_locale_is_german(self) -> None:
        """Scenario: Site locale."""
        config = self.config()
        self.assertEqual(config.get("locale"), "de")
        for key in ("languages", "defaultContentLanguage"):
            self.assertNotIn(key, config)
        self.assertEqual(pipeline().site_language(SITE), "de")

    def test_site_language_reads_the_locale(self) -> None:
        """Scenario: Site locale (reading it)."""
        for locale, expected in (("de", "de"), ("de-AT", "de"),
                                 ("en_GB", "en"), ("fr", None),
                                 (None, None)):
            with self.subTest(locale=locale), \
                    tempfile.TemporaryDirectory() as tmp:
                text = f'locale = "{locale}"\n' if locale else 'title = ""\n'
                (Path(tmp) / "hugo.toml").write_text(text, encoding="utf-8")
                if expected is None:
                    with self.assertRaises(ValueError):
                        pipeline().site_language(Path(tmp))
                else:
                    self.assertEqual(pipeline().site_language(Path(tmp)),
                                     expected)

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
        used = {tomllib.loads(page.read_text(encoding="utf-8").split(
                    "+++")[1]).get("title_key")
                for page in (SITE / "content").rglob("*.md")} - {None}
        self.assertEqual(len(used), 6)
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

    def test_site_pages_are_one_per_page(self) -> None:
        """Scenario: Site locale (content pages)."""
        content = SITE / "content"
        self.assertEqual(sorted(p.name for p in content.rglob("*.*.md")), [])
        for taxonomy in ("tags", "authors", "reaction_types"):
            self.assertTrue((content / taxonomy / "_index.md").is_file(),
                            taxonomy)


if __name__ == "__main__":
    unittest.main()
