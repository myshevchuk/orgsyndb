"""Procedure fields (procedure-fields): the fixture, the declarations of
a collection's ``orgsyndb.toml``, their configuration errors and the
checks of the values a procedure file sets, driven through
procedure-field runs (procedure-fields "Procedure field fixture")."""

import tomllib
import unittest
from pathlib import Path

from pipeline_support import make_sandbox, pipeline
from support import (BASELINE, GENERAL, PROCEDURE_FIELDS, REGISTRY,
                     FieldTestCase, add_procedure, append_text, declaration,
                     edit_procedure, edit_procedure_registry,
                     edit_procedure_settings, insert_after, insert_line,
                     load_snapshot, parse_problems, procedure_declaration,
                     procedure_field_run, replace_line, replace_text,
                     variant_run)
from test_localization import germanised

BASELINE_FILE = BASELINE.name
GENERAL_FILE = GENERAL.name
SCHEMA_KEYS = (
    "id", "slug", "title", "date", "lastmod", "authors", "status",
    "reaction_types", "tags", "products", "scale", "hazards", "substrates",
    "scope", "scheme_image", "checked_by", "references", "ai_model",
    "language", "draft", "description", "aliases", "weight", "author",
    "url")
HUGO_KEYS = (
    "build", "cascade", "expirydate", "headless", "iscjklanguage",
    "keywords", "kind", "lang", "layout", "linktitle", "markup", "menu",
    "menus", "modified", "outputs", "params", "path", "pubdate",
    "publishdate", "published", "resources", "sitemap", "sites", "summary",
    "translationkey", "type", "unpublishdate", "authors_weight",
    "reaction_types_weight", "tags_weight")
CATALOGUE_KEYS = ("tag", "created", "text", "q", "sort", "view")
VALUES = ('sample_code = "AE-1/2"', "working_time = 2.5",
          "inert_atmosphere = false", 'funding = "first-year-practical"')


# A procedure-field change that gives the registry copy the notebook
# `AE-1` (the fixture registry has none).
WITH_NOTEBOOK = edit_procedure_registry(
    lambda table: table.update(
        notebooks=[{"code": "AE-1", "user": "a.example"}]))


def set_values(*lines: str, name: str = BASELINE_FILE):
    """A procedure-field change inserting the assignment ``lines``
    among the top-level keys of ``name`` of the content root."""
    return edit_procedure(name, *(insert_line(line) for line in lines))


def add_copy(name: str, number: int, *lines: str,
             source: str = BASELINE_FILE):
    """A procedure-field change adding ``name``, a copy of ``source``
    with the ID ``OSDB-<number>``, the matching slug and the assignment
    ``lines`` added."""
    return add_procedure(
        name,
        replace_line("id", f'id = "OSDB-{number:04d}"'),
        replace_line("slug", f'slug = "osdb-{number:04d}"'),
        *(insert_line(line) for line in lines),
        source=source)


def add_german(*edits, name: str = "OSDB-0100-baseline.de.md"):
    """A procedure-field change adding the German variant of the
    baseline: a copy of the content root's baseline with German section
    headings and the text ``edits`` applied."""
    return add_procedure(name, germanised, *edits)


class ProcedureFieldTestCase(FieldTestCase):
    def assert_errors_on(self, result, field: str, text: str,
                         *names: str) -> None:
        """Exit status 1 and exactly one error per file name in
        ``names``, all with ``field`` and a message containing
        ``text``."""
        self.assert_errors(result, field, text, len(names))
        self.assertEqual(sorted(Path(p.path).name
                                for p in result.problems), sorted(names))


class ProcedureFieldFixtureTests(unittest.TestCase):
    def read(self) -> dict:
        return tomllib.loads(
            (PROCEDURE_FIELDS / "orgsyndb.toml").read_text(
                encoding="utf-8"))

    def test_the_fixture_matches_its_description(self) -> None:
        """Scenario: The fixture matches its description."""
        settings = self.read()
        self.assertEqual(list(settings), ["format", "fields"])
        self.assertEqual(settings["format"], 1)
        self.assertEqual(list(settings["fields"]), ["procedure"])
        self.assertEqual(settings["fields"]["procedure"], [
            {"key": "sample_code", "type": "text", "label": "Sample code",
             "label_de": "Probencode", "pattern": r"[A-Z]{2}-\d+/\d+",
             "unique": True},
            {"key": "working_time", "type": "number",
             "label": "Working time", "label_de": "Arbeitszeit",
             "unit": "h", "min": 0},
            {"key": "inert_atmosphere", "type": "boolean",
             "label": "Inert atmosphere"},
            {"key": "funding", "type": "choice", "label": "Funding",
             "label_de": "Förderung", "vocabulary": "projects"}])
        self.assertEqual(
            [p.name for p in PROCEDURE_FIELDS.iterdir()],
            ["orgsyndb.toml"])
        projects = load_snapshot(REGISTRY)["vocabularies"]["projects"]
        self.assertEqual(
            {entry["key"]: (entry["label"], entry["label_de"],
                            entry["parent"]) for entry in projects},
            {"teaching": ("Teaching", "Lehre", None),
             "first-year-practical": ("First-year practical",
                                      "Grundpraktikum", "teaching"),
             "research": ("Research", "Forschung", None)})
        self.assertEqual(len(projects), 3)

    def test_the_fixture_declares_no_required_unique_or_facet_option(
            self) -> None:
        """Scenario: The fixture matches its description (none of them
        `required` or a `facet`; `unique` only on `sample_code`)."""
        for entry in self.read()["fields"]["procedure"]:
            with self.subTest(key=entry["key"]):
                self.assertNotIn("required", entry)
                self.assertNotIn("facet", entry)
                self.assertEqual("unique" in entry,
                                 entry["key"] == "sample_code")


class ProcedureFieldDeclarationTests(ProcedureFieldTestCase):
    def test_the_fixture_declarations_are_accepted(self) -> None:
        """Scenario: The fixture declarations are accepted."""
        self.assert_clean(procedure_field_run())

    def test_facets_on_a_boolean_and_a_choice_field(self) -> None:
        """Scenario: Facets on a boolean and a choice field."""
        self.assert_clean(procedure_field_run(edit_procedure_settings(
            insert_after('key = "inert_atmosphere"', "facet = true"),
            insert_after('key = "funding"', "facet = true"))))

    def test_a_settings_file_without_procedure_fields_declares_none(
            self) -> None:
        """Requirement: Procedure field declarations (no
        `fields.procedure`)."""
        result = procedure_field_run(
            edit_procedure_settings(lambda _: "format = 1\n"),
            set_values('sample_code = "AE-1/2"'))
        self.assert_one(result, "warning", "sample_code", "unknown field",
                        path_suffix=BASELINE_FILE)

    def test_keys_that_follow_the_pattern_are_accepted(self) -> None:
        """Requirement: Procedure field declarations (the key pattern)."""
        for key in ("a", "batch_2a", "x1_y2_z3", "de", "note_dex",
                    "statuses", "layouts", "tagline", "weight_class"):
            with self.subTest(key=key):
                self.assert_clean(procedure_field_run(
                    edit_procedure_settings(append_text(
                        procedure_declaration(key, "boolean", "Flag")))))

    def test_compound_built_in_keys_are_no_reserved_keys(self) -> None:
        """Requirement: Procedure field declarations (the reserved keys
        are those of the procedures, not the compound-registry
        keys)."""
        for key in ("name", "formula", "mw", "smiles", "cas",
                    "structure_image"):
            with self.subTest(key=key):
                self.assert_clean(procedure_field_run(
                    edit_procedure_settings(append_text(
                        procedure_declaration(key, "text", "Free")))))

    def test_defaults_may_be_written_out(self) -> None:
        """Requirement: Procedure field declarations (defaults)."""
        self.assert_clean(procedure_field_run(edit_procedure_settings(
            insert_after('key = "sample_code"', "required = false"),
            insert_after('key = "funding"', "multiple = false"),
            insert_after('key = "funding"', "facet = false"),
            insert_after('key = "inert_atmosphere"', "facet = false"),
            insert_after('key = "working_time"', "unique = false"))))

    def test_a_procedure_field_may_share_a_vocabulary(self) -> None:
        """Requirement: Procedure field declarations (the vocabularies
        are shared, one vocabulary for two fields)."""
        self.assert_clean(procedure_field_run(
            edit_procedure_settings(append_text(procedure_declaration(
                "main_project", "choice", "Main project",
                'vocabulary = "projects"', "facet = true"))),
            set_values('main_project = "research"',
                       'funding = "teaching"')))

    def test_a_choice_may_name_each_of_the_four_vocabularies(self) -> None:
        """Requirement: Procedure field declarations (`vocabulary`, one
        of the registry's four)."""
        for name in ("chemical-classes", "inventory-groups", "projects",
                     "reaction-types"):
            with self.subTest(vocabulary=name):
                self.assert_clean(procedure_field_run(
                    edit_procedure_settings(append_text(
                        procedure_declaration(
                            "category", "choice", "Category",
                            f'vocabulary = "{name}"')))))


class ProcedureDeclarationErrorTests(ProcedureFieldTestCase):
    def test_options_a_procedure_field_does_not_take(self) -> None:
        """Scenario: Options a procedure field does not take."""
        for key, option in (("sample_code", "column"),
                            ("sample_code", "search"),
                            ("funding", "tabs"),
                            ("working_time", "beside")):
            with self.subTest(key=key, option=option):
                result = procedure_field_run(edit_procedure_settings(
                    insert_after(f'key = "{key}"', f"{option} = true")))
                self.assert_configuration_error(result, key, option)

    def test_no_declaration_takes_column_search_tabs_or_beside(
            self) -> None:
        """Requirement: Procedure field declarations (it takes neither
        `column`, nor `search`, nor `tabs`, nor `beside`)."""
        for key in ("sample_code", "working_time", "inert_atmosphere",
                    "funding"):
            for option in ("column", "search", "tabs", "beside"):
                with self.subTest(key=key, option=option):
                    result = procedure_field_run(edit_procedure_settings(
                        insert_after(f'key = "{key}"',
                                     f"{option} = false")))
                    self.assert_configuration_error(result, key, option)

    def test_an_option_the_type_does_not_take(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a key that the type does not take)."""
        cases = (("working_time", "pattern = 'x'", "pattern"),
                 ("inert_atmosphere", "unique = true", "unique"),
                 ("inert_atmosphere", "unit = 'h'", "unit"),
                 ("sample_code", "facet = true", "facet"),
                 ("working_time", "facet = true", "facet"),
                 ("sample_code", "multiple = true", "multiple"),
                 ("sample_code", "vocabulary = 'projects'", "vocabulary"),
                 ("funding", "pattern = 'x'", "pattern"),
                 ("funding", "unique = true", "unique"),
                 ("sample_code", "min = 0", "min"))
        for key, line, option in cases:
            with self.subTest(key=key, option=line):
                result = procedure_field_run(edit_procedure_settings(
                    insert_after(f'key = "{key}"', line)))
                self.assert_configuration_error(result, key, option)

    def test_an_unknown_option(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a key that is unknown)."""
        for option in ("sortable = true", "help = 'x'"):
            with self.subTest(option=option):
                result = procedure_field_run(edit_procedure_settings(
                    insert_after('key = "sample_code"', option)))
                self.assert_configuration_error(
                    result, "sample_code", option.split(" =")[0])

    def test_reserved_keys(self) -> None:
        """Scenario: Reserved keys."""
        for key in ("status", "layout", "tag"):
            with self.subTest(key=key):
                result = procedure_field_run(edit_procedure_settings(
                    append_text(procedure_declaration(key, "text", "X"))))
                self.assert_configuration_error(
                    result, "fields.procedure", key)

    def test_every_reserved_key_is_refused(self) -> None:
        """Requirement: Procedure field declarations (the keys of the
        procedure schema, the front-matter keys of Hugo and the keys of
        the procedure catalogue)."""
        for key in (*SCHEMA_KEYS, *HUGO_KEYS, *CATALOGUE_KEYS):
            with self.subTest(key=key):
                result = procedure_field_run(edit_procedure_settings(
                    append_text(procedure_declaration(key, "text", "X"))))
                self.assert_configuration_error(
                    result, "fields.procedure", key)

    def test_a_reserved_key_is_refused_for_every_type(self) -> None:
        """Requirement: Procedure field declarations (a reserved key,
        whatever the type)."""
        for type_ in ("boolean", "number"):
            with self.subTest(type=type_):
                result = procedure_field_run(edit_procedure_settings(
                    append_text(procedure_declaration(
                        "scale", type_, "Scale"))))
                self.assert_configuration_error(
                    result, "fields.procedure", "scale")

    def test_a_key_ending_in_de_is_refused(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a key that ends in `_de`)."""
        for key in ("note_de", "working_time_de", "x_1_de"):
            with self.subTest(key=key):
                result = procedure_field_run(edit_procedure_settings(
                    append_text(procedure_declaration(key, "text", "N"))))
                self.assert_configuration_error(
                    result, "fields.procedure", key)

    def test_a_key_that_breaks_its_pattern(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a key that breaks its pattern)."""
        for key in ("Lab_Notebook", "1abc", "a__b", "a_", "_a",
                    "has-hyphen", "has space", "umlautä"):
            with self.subTest(key=key):
                result = procedure_field_run(edit_procedure_settings(
                    append_text(procedure_declaration(key, "text", "B"))))
                self.assert_configuration_error(
                    result, "fields.procedure", key)

    def test_a_key_declared_twice(self) -> None:
        """Scenario: A key declared twice."""
        result = procedure_field_run(edit_procedure_settings(append_text(
            procedure_declaration("sample_code", "text", "Sample code"))))
        self.assert_configuration_error(
            result, "sample_code", "fields.procedure")

    def test_a_declaration_lacks_a_required_key(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a declaration lacks `key`, `type` or `label`)."""
        cases = [("key", 'key = "working_time"\n', ["key"]),
                 ("type", 'type = "number"\n', ["working_time", "type"]),
                 ("label", 'label = "Working time"\n',
                  ["working_time", "label"]),
                 ("vocabulary", 'vocabulary = "projects"\n',
                  ["funding", "vocabulary"])]
        for name, line, needles in cases:
            with self.subTest(missing=name):
                result = procedure_field_run(edit_procedure_settings(
                    replace_text(line, "")))
                self.assert_configuration_error(result, *needles)

    def test_a_declaration_with_a_value_of_the_wrong_type(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a value of the wrong type)."""
        cases = [
            ('label = "Working time"', "label = 5", "working_time",
             "label"),
            ('label = "Working time"', 'label = ""', "working_time",
             "label"),
            ('label_de = "Arbeitszeit"', "label_de = 5", "working_time",
             "label_de"),
            ('label_de = "Arbeitszeit"', 'label_de = ""', "working_time",
             "label_de"),
            ('type = "number"', 'type = "date"', "working_time", "type"),
            ('type = "number"', "type = 5", "working_time", "type"),
            ('unit = "h"', 'unit = ""', "working_time", "unit"),
            ('unit = "h"', "unit = 5", "working_time", "unit"),
            ("min = 0", 'min = "0"', "working_time", "min"),
            ("min = 0", "min = true", "working_time", "min"),
            ("unique = true", 'unique = "yes"', "sample_code", "unique"),
            ("pattern = '[A-Z]{2}-\\d+/\\d+'", "pattern = 5", "sample_code",
             "pattern"),
            ('vocabulary = "projects"', "vocabulary = 5", "funding",
             "vocabulary"),
        ]
        for old, new, key, option in cases:
            with self.subTest(change=new):
                result = procedure_field_run(edit_procedure_settings(
                    replace_text(old, new)))
                self.assert_configuration_error(result, key, option)

    def test_required_facet_and_multiple_must_be_booleans(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a value of the wrong type)."""
        for key, option in (("sample_code", 'required = "yes"'),
                            ("sample_code", "required = 1"),
                            ("inert_atmosphere", 'facet = "yes"'),
                            ("funding", "facet = 1"),
                            ("funding", 'multiple = "yes"')):
            with self.subTest(key=key, option=option):
                result = procedure_field_run(edit_procedure_settings(
                    insert_after(f'key = "{key}"', option)))
                self.assert_configuration_error(
                    result, key, option.split(" =")[0])

    def test_a_pattern_that_does_not_compile(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a `pattern` that breaks the rules of the compound
        declarations)."""
        result = procedure_field_run(edit_procedure_settings(replace_text(
            "pattern = '[A-Z]{2}-\\d+/\\d+'", 'pattern = "AE-("')))
        self.assert_configuration_error(result, "sample_code", "pattern")

    def test_a_bound_that_is_not_usable(self) -> None:
        """Scenario: A bound that is not a number, with the other bounds
        the declaration rules refuse."""
        for old, new, option in (
                ("min = 0", "min = 5\nmax = 1", "min"),
                ("min = 0", "min = 0\nmax = nan", "max"),
                ("min = 0", "min = inf", "min")):
            with self.subTest(bound=new):
                result = procedure_field_run(edit_procedure_settings(
                    replace_text(old, new)))
                self.assert_configuration_error(
                    result, "working_time", option)

    def test_a_single_table_instead_of_an_array(self) -> None:
        """Scenario: A single table instead of an array."""
        result = procedure_field_run(edit_procedure_settings(
            lambda _: 'format = 1\n\n[fields.procedure]\n'
                      'key = "sample_code"\ntype = "text"\n'
                      'label = "Sample code"\n'))
        self.assert_configuration_error(result, "fields.procedure")

    def test_fields_procedure_must_be_an_array_of_tables(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (`fields.procedure` is not an array of tables)."""
        for name, text in {
                "a number": "format = 1\n\n[fields]\nprocedure = 5\n",
                "numbers": "format = 1\n\n[fields]\nprocedure = [1, 2]\n",
                "a string": 'format = 1\n\n[fields]\nprocedure = "x"\n'
                }.items():
            with self.subTest(case=name):
                result = procedure_field_run(
                    edit_procedure_settings(lambda _, t=text: t))
                self.assert_configuration_error(result, "fields.procedure")

    def test_a_missing_vocabulary(self) -> None:
        """Scenario: A missing vocabulary."""
        result = procedure_field_run(edit_procedure_settings(replace_text(
            'vocabulary = "projects"',
            'vocabulary = "no-such-vocabulary"')))
        self.assert_configuration_error(result, "no-such-vocabulary")

    def test_a_vocabulary_of_the_collection_is_not_one_of_the_four(
            self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (the vocabulary a `choice` field names is not one of the
        registry's four)."""
        for name in ("storage", "Projects", "projects.toml", ""):
            with self.subTest(vocabulary=name):
                result = procedure_field_run(edit_procedure_settings(
                    replace_text('vocabulary = "projects"',
                                 f'vocabulary = "{name}"')))
                self.assert_configuration_error(result, "funding")

    def test_a_compound_declaration(self) -> None:
        """Scenario: A compound declaration."""
        result = procedure_field_run(edit_procedure_settings(append_text(
            declaration("sample_code", "text", "Sample code"))))
        self.assert_configuration_error(result, "fields.compound")

    def test_a_compound_declaration_beside_procedure_declarations(
            self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (`fields` holds a key other than `procedure`, `compound`
        among them)."""
        for name, text in {
                "the fixture's own key": declaration(
                    "sample_code", "text", "Sample code"),
                "a built-in registry key": declaration(
                    "article_number", "text", "Article no."),
                "a single table": ('\n[fields.compound]\nkey = "x"\n'
                                   'type = "text"\nlabel = "X"\n')
        }.items():
            with self.subTest(case=name):
                result = procedure_field_run(
                    edit_procedure_settings(append_text(text)))
                self.assert_configuration_error(result, "fields.compound")

    def test_a_compound_declaration_alone(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a settings file that declares only compound fields)."""
        result = procedure_field_run(edit_procedure_settings(
            lambda _: "format = 1\n" + declaration("x", "text", "X")))
        self.assert_configuration_error(result, "fields.compound")

    def test_a_misspelt_top_level_key(self) -> None:
        """Scenario: A misspelt top-level key."""
        result = procedure_field_run(edit_procedure_settings(
            lambda text: text.replace("[[fields.procedure]]",
                                      "[[feilds.procedure]]")))
        self.assert_configuration_error(result, "feilds")

    def test_a_misspelt_entity_under_fields(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a settings file that declares fields of another
        entity)."""
        result = procedure_field_run(edit_procedure_settings(
            append_text('\n[[fields.reagent]]\nkey = "lot"\n'
                        'type = "text"\nlabel = "Lot"')))
        self.assert_configuration_error(result, "fields.reagent")

    def test_a_configuration_error_hides_the_procedure_checks(
            self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (nothing on stdout)."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(
                procedure_declaration("status", "text", "Status"))),
            set_values('sample_code = "AE-12"'))
        self.assert_configuration_error(result, "fields.procedure",
                                        "status")


class ProcedureFieldValueTests(ProcedureFieldTestCase):
    def check_one(self, line: str, field: str, text: str,
                  *more: str) -> None:
        """A procedure-field run that sets ``line`` in the baseline
        reports exactly one error on that file, with ``field`` and all
        of ``text`` and ``more``."""
        problem = self.assert_one(
            procedure_field_run(set_values(line)), "error", field, text,
            path_suffix=BASELINE_FILE)
        for needle in more:
            self.assertIn(needle, problem.message)

    def test_declared_values_pass(self) -> None:
        """Scenario: Declared values pass."""
        self.assert_clean(procedure_field_run(set_values(*VALUES)))

    def test_a_text_value_that_breaks_its_pattern(self) -> None:
        """Scenario: A text value that breaks its pattern."""
        self.check_one('sample_code = "AE-12"', "sample_code",
                       "must match the pattern")

    def test_the_pattern_is_matched_as_a_whole(self) -> None:
        """Requirement: Procedure field values (a text value matches its
        pattern as a whole, as a compound's does)."""
        for value in ("AE-1/2 ", "xAE-1/2", "ae-1/2", "AE-1/2/3"):
            with self.subTest(value=value):
                self.check_one(f'sample_code = "{value}"', "sample_code",
                               "must match the pattern")

    def test_an_empty_or_unquoted_text_value(self) -> None:
        """Requirement: Procedure field values (the messages of the
        compound fields: `must not be empty`, `must be a string`)."""
        self.check_one('sample_code = ""', "sample_code", "must not be empty")
        for line in ("sample_code = 5", "sample_code = true",
                     'sample_code = ["AE-1/2"]'):
            with self.subTest(line=line):
                self.check_one(line, "sample_code", "must be a string")

    def test_a_quoted_number(self) -> None:
        """Scenario: A quoted number."""
        self.check_one('working_time = "2"', "working_time",
                       "must be a number")

    def test_numbers_are_checked_against_their_bounds(self) -> None:
        """Requirement: Procedure field values (`must be at least 0`, as
        compound-fields "Field values")."""
        self.check_one("working_time = -1", "working_time",
                       "must be at least 0")
        for value in ("0", "12", "2.5", "1e1"):
            with self.subTest(working_time=value):
                self.assert_clean(procedure_field_run(
                    set_values(f"working_time = {value}")))

    def test_a_value_that_is_not_a_finite_number(self) -> None:
        """Requirement: Procedure field values (`must be a number`)."""
        for value in ("true", "inf", "nan", "[1]", "2026-01-01"):
            with self.subTest(working_time=value):
                self.check_one(f"working_time = {value}", "working_time",
                               "must be a number")

    def test_a_quoted_boolean(self) -> None:
        """Requirement: Procedure field values (`must be true or
        false`)."""
        for value in ('"yes"', '"false"', "1", "0", "[true]"):
            with self.subTest(inert_atmosphere=value):
                self.check_one(f"inert_atmosphere = {value}",
                               "inert_atmosphere", "must be true or false")
        for value in ("true", "false"):
            with self.subTest(inert_atmosphere=value):
                self.assert_clean(procedure_field_run(
                    set_values(f"inert_atmosphere = {value}")))

    def test_a_value_outside_the_vocabulary(self) -> None:
        """Scenario: A value outside the vocabulary."""
        self.check_one('funding = "outreach"', "funding",
                       'unknown value "outreach"', "projects")

    def test_a_choice_may_name_a_value_at_any_level(self) -> None:
        """Requirement: Procedure field values (`choice` at every level
        of its vocabulary)."""
        for value in ("teaching", "first-year-practical", "research"):
            with self.subTest(funding=value):
                self.assert_clean(procedure_field_run(
                    set_values(f'funding = "{value}"')))

    def test_a_single_choice_must_be_a_string(self) -> None:
        """Requirement: Procedure field values (`choice`: `must be a
        string`)."""
        for value in ("5", '["research"]', "true"):
            with self.subTest(funding=value):
                self.check_one(f"funding = {value}", "funding",
                               "must be a string")

    def test_a_multiple_choice_is_a_list(self) -> None:
        """Requirement: Procedure field values (`multiple`, as for a
        compound field)."""
        multiple = edit_procedure_settings(
            insert_after('key = "funding"', "multiple = true"))
        self.assert_clean(procedure_field_run(
            multiple, set_values(
                'funding = ["first-year-practical", "research"]')))
        result = procedure_field_run(
            multiple, set_values('funding = "research"'))
        self.assert_one(result, "error", "funding",
                        "must be a list of strings",
                        path_suffix=BASELINE_FILE)
        result = procedure_field_run(
            multiple, set_values('funding = ["research", "research"]'))
        self.assert_one(result, "error", "funding", 'repeats "research"',
                        path_suffix=BASELINE_FILE)
        result = procedure_field_run(
            multiple, set_values('funding = ["research", "nope"]'))
        self.assert_one(result, "error", "funding", 'unknown value "nope"',
                        path_suffix=BASELINE_FILE)

    def test_a_required_field_on_every_procedure(self) -> None:
        """Scenario: A required field on every procedure."""
        result = procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "funding"', "required = true")),
            add_procedure(GENERAL_FILE, source=GENERAL))
        self.assert_errors_on(result, "funding", "required field missing",
                              BASELINE_FILE, GENERAL_FILE)

    def test_a_required_field_that_is_set_passes(self) -> None:
        """Requirement: Procedure field values (`required`)."""
        self.assert_clean(procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "funding"', "required = true")),
            add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('funding = "research"'),
            set_values('funding = "teaching"', name=GENERAL_FILE)))

    def test_a_field_that_is_not_required_may_be_absent(self) -> None:
        """Requirement: Procedure field values (`required` defaults to
        false)."""
        self.assert_clean(procedure_field_run(
            add_procedure(GENERAL_FILE, source=GENERAL)))

    def test_a_value_of_the_wrong_type_is_not_also_a_missing_one(
            self) -> None:
        """Requirement: Procedure field values (the messages of the
        compound fields: a value of the wrong type draws that one
        error)."""
        result = procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "working_time"', "required = true")),
            set_values('working_time = "5"'))
        self.assert_one(result, "error", "working_time",
                        "must be a number", path_suffix=BASELINE_FILE)

    def test_a_general_procedure_sets_declared_fields(self) -> None:
        """Requirement: Procedure field values (a general procedure as
        any other)."""
        self.assert_clean(procedure_field_run(
            add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('sample_code = "AE-3/1"', "working_time = 4",
                       name=GENERAL_FILE)))
        result = procedure_field_run(
            add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('funding = "outreach"', name=GENERAL_FILE))
        self.assert_one(result, "error", "funding", "unknown value",
                        path_suffix=GENERAL_FILE)

    def test_a_value_set_by_two_procedures(self) -> None:
        """Scenario: A value set by two procedures."""
        result = procedure_field_run(
            set_values('sample_code = "AE-1/2"'),
            add_copy("OSDB-0101-copy.md", 101))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_file = {Path(p.path).name: p for p in result.problems}
        self.assertEqual(set(by_file), {BASELINE_FILE, "OSDB-0101-copy.md"})
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, "sample_code", result.stdout)
            self.assertIn("also set by", problem.message)
        self.assertIn("OSDB-0101", by_file[BASELINE_FILE].message)
        self.assertNotIn("OSDB-0100", by_file[BASELINE_FILE].message)
        self.assertIn("OSDB-0100", by_file["OSDB-0101-copy.md"].message)
        self.assertNotIn("OSDB-0101", by_file["OSDB-0101-copy.md"].message)

    def test_three_procedures_name_each_other(self) -> None:
        """Requirement: Procedure field values (the IDs of the other
        procedures)."""
        result = procedure_field_run(
            set_values('sample_code = "AE-1/2"'),
            add_copy("OSDB-0101-copy.md", 101),
            add_copy("OSDB-0102-copy.md", 102))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 3, result.stdout)
        ids = {BASELINE_FILE: "OSDB-0100", "OSDB-0101-copy.md": "OSDB-0101",
               "OSDB-0102-copy.md": "OSDB-0102"}
        for problem in result.problems:
            own = ids[Path(problem.path).name]
            self.assertEqual(problem.field, "sample_code")
            self.assertNotIn(own, problem.message)
            for other in set(ids.values()) - {own}:
                self.assertIn(other, problem.message)

    def test_different_values_under_a_unique_field_pass(self) -> None:
        """Requirement: Procedure field values (only a repeated value
        draws an error)."""
        self.assert_clean(procedure_field_run(
            add_copy("OSDB-0101-copy.md", 101, 'sample_code = "AE-1/3"'),
            set_values('sample_code = "AE-1/2"')))

    def test_a_repeated_value_of_a_field_that_is_not_unique_passes(
            self) -> None:
        """Requirement: Procedure field values (`unique` is opt-in)."""
        self.assert_clean(procedure_field_run(
            add_copy("OSDB-0101-copy.md", 101, 'funding = "research"',
                     "working_time = 2"),
            set_values('funding = "research"', "working_time = 2")))

    def test_a_unique_number_field(self) -> None:
        """Requirement: Procedure field values (`unique` for
        `number`)."""
        result = procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "working_time"', "unique = true")),
            add_copy("OSDB-0101-copy.md", 101, "working_time = 2"),
            set_values("working_time = 2"))
        self.assert_errors(result, "working_time", "also set by", 2)

    def test_variants_of_one_procedure_are_one_holder(self) -> None:
        """Scenario: Variants of one procedure are one holder."""
        self.assert_clean(procedure_field_run(
            set_values('sample_code = "AE-1/2"'), add_german()))

    def test_a_variant_is_not_compared_beside_its_reference(self) -> None:
        """Requirement: Procedure field values (the procedures compared
        are those that stand for their IDs)."""
        result = procedure_field_run(
            set_values('sample_code = "AE-1/2"'), add_german(),
            add_copy("OSDB-0101-copy.md", 101))
        self.assert_errors_on(result, "sample_code", "also set by",
                              BASELINE_FILE, "OSDB-0101-copy.md")
        by_file = {Path(p.path).name: p for p in result.problems}
        self.assertIn("OSDB-0101", by_file[BASELINE_FILE].message)
        self.assertIn("OSDB-0100", by_file["OSDB-0101-copy.md"].message)
        self.assertNotIn("de.md", result.stdout)

    def test_values_that_fail_their_checks_are_not_compared(self) -> None:
        """Requirement: Procedure field values (every value that passes
        the checks of its field)."""
        result = procedure_field_run(
            set_values('sample_code = "AE-12"'),
            add_copy("OSDB-0101-copy.md", 101))
        self.assert_errors(result, "sample_code", "must match the pattern", 2)
        self.assertNotIn("also set by", result.stdout)

    def test_a_file_that_does_not_parse_sets_no_value(self) -> None:
        """Requirement: Procedure field values (a file whose front matter
        does not parse sets no value)."""
        result = procedure_field_run(
            set_values('sample_code = "AE-1/2"'),
            add_copy("OSDB-0101-broken.md", 101, 'sample_code = "AE-1/2"'),
            edit_procedure("OSDB-0101-broken.md",
                           replace_line("scale", 'scale = "25 mmol')))
        self.assert_one(result, "error", "front_matter", "invalid TOML",
                        path_suffix="OSDB-0101-broken.md")


class DeclaredKeyTests(ProcedureFieldTestCase):
    def test_every_declared_key_is_known(self) -> None:
        """Requirement: Procedure field values (a key of a declared
        procedure field is no key outside the schema)."""
        result = procedure_field_run(set_values(*VALUES))
        self.assert_clean(result)

    def test_an_undeclared_key_is_still_unknown(self) -> None:
        """Requirement: Procedure field values (a key that no
        declaration names is outside the schema)."""
        result = procedure_field_run(set_values("working_tme = 2.5"))
        self.assert_one(result, "warning", "working_tme", "unknown field",
                        path_suffix=BASELINE_FILE)


class JournalFieldTests(ProcedureFieldTestCase):
    """Requirement: Journal fields."""

    def test_the_journal_keys_are_notebook_and_project(self) -> None:
        """Requirement: Journal fields (the keys of the two built-in
        fields, in their order)."""
        self.assertEqual(pipeline().validate.JOURNAL_KEYS,
                         ("notebook", "project"))

    def test_a_registered_notebook(self) -> None:
        """Scenario: A registered notebook (the test collection, whose
        registry lists `AE-1`; the German variant of `OSDB-0002`, which
        must share the value, is left out)."""
        sandbox = make_sandbox(self)
        (sandbox.root / "md" / "procedures"
         / "OSDB-0002-aspirin.de.md").unlink()
        path = sandbox.root / "md" / "procedures" / "OSDB-0002-aspirin.md"
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count('notebook = "AE-1/2"'), 1)
        path.write_text(text.replace('notebook = "AE-1/2"',
                                     'notebook = "AE-1/14"'),
                        encoding="utf-8")
        result = sandbox.validator("md/procedures")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_an_unknown_notebook(self) -> None:
        """Scenario: An unknown notebook (the test collection, as above)."""
        sandbox = make_sandbox(self)
        (sandbox.root / "md" / "procedures"
         / "OSDB-0002-aspirin.de.md").unlink()
        path = sandbox.root / "md" / "procedures" / "OSDB-0002-aspirin.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('notebook = "AE-1/2"',
                                     'notebook = "ZZ-9/1"'),
                        encoding="utf-8")
        result = sandbox.validator("md/procedures")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        problems = parse_problems(result.stdout)
        self.assertEqual(len(problems), 1, result.stdout)
        self.assertEqual(problems[0].field, "notebook")
        self.assertEqual(problems[0].severity, "error")
        self.assertTrue(problems[0].path.endswith("OSDB-0002-aspirin.md"))
        self.assertIn('unknown notebook "ZZ-9"', problems[0].message)

    def test_the_message_names_the_registry(self) -> None:
        """Requirement: Journal fields (`unknown notebook "<code>"; the
        registry has no notebook of this code`)."""
        result = procedure_field_run(
            WITH_NOTEBOOK, set_values('notebook = "ZZ-9/1"'))
        problem = self.assert_one(result, "error", "notebook",
                                  'unknown notebook "ZZ-9"',
                                  path_suffix=BASELINE_FILE)
        self.assertIn("the registry has no notebook of this code",
                      problem.message)

    def test_the_fixture_registry_has_no_notebook(self) -> None:
        """Requirement: Journal fields (a value whose code is no `code`
        of the registry's `notebooks`)."""
        result = procedure_field_run(set_values('notebook = "AE-1/2"'))
        self.assert_one(result, "error", "notebook",
                        'unknown notebook "AE-1"',
                        path_suffix=BASELINE_FILE)

    def test_the_code_is_the_part_before_the_slash(self) -> None:
        """Requirement: Journal fields (the code, the part before `/`)."""
        for value in ("AE-1/1", "AE-1/14", "AE-1/100"):
            with self.subTest(value=value):
                self.assert_clean(procedure_field_run(
                    WITH_NOTEBOOK, set_values(f'notebook = "{value}"')))
        result = procedure_field_run(
            WITH_NOTEBOOK, set_values('notebook = "AE-2/1"'))
        self.assert_one(result, "error", "notebook",
                        'unknown notebook "AE-2"')

    def test_a_notebook_value_breaks_its_pattern(self) -> None:
        """Requirement: Journal fields (the pattern `[A-Z0-9]+(-[A-Z0-9]+)
        */[1-9][0-9]{0,3}`: an entry number from 1 to 9999, with no
        leading zero)."""
        for value in ("AE-1/0", "AE-1/02", "AE-1/2/3", "AE-1/ 2",
                      "AE-1/-2", "AE-1/", "AE-1/10000",
                      "AE-1/9223372036854775808"):
            with self.subTest(value=value):
                result = procedure_field_run(
                    WITH_NOTEBOOK, set_values(f'notebook = "{value}"'))
                self.assert_one(result, "error", "notebook",
                                "must match the pattern",
                                path_suffix=BASELINE_FILE)

    def test_a_code_may_hold_digits_and_several_words(self) -> None:
        """Requirement: Journal fields (the pattern's code, such as
        `AE-2`)."""
        registry = edit_procedure_registry(lambda table: table.update(
            notebooks=[{"code": "A1-B2-C3", "user": "a.example"},
                       {"code": "7", "user": "a.example"}]))
        for value in ("A1-B2-C3/5", "7/1"):
            with self.subTest(value=value):
                self.assert_clean(procedure_field_run(
                    registry, set_values(f'notebook = "{value}"')))

    def test_an_empty_or_mistyped_notebook(self) -> None:
        """Requirement: Journal fields (besides the checks of a `text`
        field; a value of the wrong type draws that one error)."""
        cases = (('notebook = ""', "must not be empty"),
                 ("notebook = 5", "must be a string"),
                 ("notebook = true", "must be a string"),
                 ('notebook = ["AE-1/1"]', "must be a string"))
        for line, text in cases:
            with self.subTest(line=line):
                result = procedure_field_run(WITH_NOTEBOOK,
                                             set_values(line))
                self.assert_one(result, "error", "notebook", text,
                                path_suffix=BASELINE_FILE)

    def test_a_notebook_is_unique(self) -> None:
        """Requirement: Journal fields (`unique`: no two procedures name
        one entry)."""
        result = procedure_field_run(
            WITH_NOTEBOOK,
            add_copy("OSDB-0101-copy.md", 101, 'notebook = "AE-1/2"'),
            set_values('notebook = "AE-1/2"'))
        self.assert_errors_on(result, "notebook", "also set by",
                              BASELINE_FILE, "OSDB-0101-copy.md")
        self.assert_clean(procedure_field_run(
            WITH_NOTEBOOK,
            add_copy("OSDB-0101-copy.md", 101, 'notebook = "AE-1/3"'),
            set_values('notebook = "AE-1/2"')))

    def test_variants_of_one_procedure_hold_one_notebook(self) -> None:
        """Requirement: Journal fields (a journal field is treated as a
        declared field: variants of one procedure are one holder)."""
        self.assert_clean(procedure_field_run(
            WITH_NOTEBOOK, set_values('notebook = "AE-1/2"'),
            add_german()))

    def test_a_project_is_a_term_of_the_projects(self) -> None:
        """Requirement: Journal fields (`project` names a term of the
        registry's projects, one filed under another too)."""
        for value in ("research", "teaching", "first-year-practical"):
            with self.subTest(value=value):
                self.assert_clean(procedure_field_run(
                    set_values(f'project = "{value}"')))
        result = procedure_field_run(set_values('project = "outreach"'))
        self.assert_one(result, "error", "project",
                        'unknown value "outreach"',
                        path_suffix=BASELINE_FILE)
        self.assertIn("projects", result.problems[0].message)

    def test_a_project_is_one_string(self) -> None:
        """Requirement: Journal fields (`project` is a `choice` that is
        not `multiple`)."""
        for line, text in (("project = 5", "must be a string"),
                           ('project = ["research"]', "must be a string")):
            with self.subTest(line=line):
                result = procedure_field_run(set_values(line))
                self.assert_one(result, "error", "project", text,
                                path_suffix=BASELINE_FILE)

    def test_a_project_is_not_unique(self) -> None:
        """Requirement: Journal fields (only `notebook` is `unique`)."""
        self.assert_clean(procedure_field_run(
            add_copy("OSDB-0101-copy.md", 101, 'project = "research"'),
            set_values('project = "research"')))

    def test_neither_journal_field_is_required(self) -> None:
        """Requirement: Journal fields (a procedure may set either, and
        neither is required)."""
        self.assert_clean(procedure_field_run())
        self.assert_clean(procedure_field_run(
            add_procedure(GENERAL_FILE, source=GENERAL)))

    def test_a_journal_key_is_no_unknown_field(self) -> None:
        """Requirement: Journal fields (the tools treat them as declared
        fields, so a collection without declarations knows them)."""
        result = variant_run("OSDB-0100-journal.md",
                             insert_line('project = "research"'))
        self.assert_clean(result)

    def test_a_general_procedure_sets_journal_fields(self) -> None:
        """Requirement: Journal fields (every procedure has them, a
        general one too)."""
        self.assert_clean(procedure_field_run(
            WITH_NOTEBOOK, add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('notebook = "AE-1/3"', 'project = "research"',
                       name=GENERAL_FILE)))

    def test_a_journal_field_declared(self) -> None:
        """Scenario: A journal field declared."""
        result = procedure_field_run(edit_procedure_settings(append_text(
            procedure_declaration("project", "text", "Project"))))
        self.assert_configuration_error(result, "fields.procedure",
                                        "project")

    def test_neither_journal_key_may_be_declared(self) -> None:
        """Requirement: Procedure field declarations (the keys of the
        journal fields are reserved), for every type."""
        for key in ("notebook", "project"):
            for type_ in ("text", "number", "boolean", "choice"):
                lines = ('vocabulary = "projects"',) \
                    if type_ == "choice" else ()
                with self.subTest(key=key, type=type_):
                    result = procedure_field_run(edit_procedure_settings(
                        append_text(procedure_declaration(
                            key, type_, "X", *lines))))
                    self.assert_configuration_error(
                        result, "fields.procedure", key)

    def test_a_journal_declaration_hides_the_procedure_checks(
            self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (nothing on stdout)."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(
                procedure_declaration("notebook", "text", "Notebook"))),
            set_values('notebook = "ZZ-9/1"'))
        self.assert_configuration_error(result, "fields.procedure",
                                        "notebook")

    def test_the_sample_fixture_declarations_are_no_journal_fields(
            self) -> None:
        """Requirement: Procedure field fixture (the fixture declares
        `sample_code` and `funding` where it declared `notebook` and
        `project`)."""
        keys = [d["key"] for d in tomllib.loads(
            (PROCEDURE_FIELDS / "orgsyndb.toml").read_text(
                encoding="utf-8"))["fields"]["procedure"]]
        self.assertEqual(keys, ["sample_code", "working_time",
                                "inert_atmosphere", "funding"])
        self.assertNotIn("notebook", keys)
        self.assertNotIn("project", keys)


if __name__ == "__main__":
    unittest.main()
