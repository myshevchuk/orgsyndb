"""Procedure fields (procedure-fields): the fixture, the declarations of
a collection's ``orgsyndb.toml``, their configuration errors and the
checks of the values a procedure file sets, driven through
procedure-field runs (procedure-fields "Procedure field fixture")."""

import tomllib
import unittest
from pathlib import Path

from support import (BASELINE, GENERAL, PROCEDURE_FIELDS, REGISTRY,
                     FieldTestCase, add_procedure, append_text, declaration,
                     edit_procedure, edit_procedure_settings, insert_after,
                     insert_line, load_snapshot, procedure_declaration,
                     procedure_field_run, replace_line, replace_text)
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
VALUES = ('notebook = "AE-1/2"', "working_time = 2.5",
          "inert_atmosphere = false", 'project = "first-year-practical"')


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
            {"key": "notebook", "type": "text", "label": "Lab notebook",
             "label_de": "Laborjournal", "pattern": r"[A-Z]{2}-\d+/\d+",
             "unique": True},
            {"key": "working_time", "type": "number",
             "label": "Working time", "label_de": "Arbeitszeit",
             "unit": "h", "min": 0},
            {"key": "inert_atmosphere", "type": "boolean",
             "label": "Inert atmosphere"},
            {"key": "project", "type": "choice", "label": "Project",
             "label_de": "Projekt", "vocabulary": "projects"}])
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
        `required` or a `facet`; `unique` only on `notebook`)."""
        for entry in self.read()["fields"]["procedure"]:
            with self.subTest(key=entry["key"]):
                self.assertNotIn("required", entry)
                self.assertNotIn("facet", entry)
                self.assertEqual("unique" in entry,
                                 entry["key"] == "notebook")


class ProcedureFieldDeclarationTests(ProcedureFieldTestCase):
    def test_the_fixture_declarations_are_accepted(self) -> None:
        """Scenario: The fixture declarations are accepted."""
        self.assert_clean(procedure_field_run())

    def test_facets_on_a_boolean_and_a_choice_field(self) -> None:
        """Scenario: Facets on a boolean and a choice field."""
        self.assert_clean(procedure_field_run(edit_procedure_settings(
            insert_after('key = "inert_atmosphere"', "facet = true"),
            insert_after('key = "project"', "facet = true"))))

    def test_a_settings_file_without_procedure_fields_declares_none(
            self) -> None:
        """Requirement: Procedure field declarations (no
        `fields.procedure`)."""
        result = procedure_field_run(
            edit_procedure_settings(lambda _: "format = 1\n"),
            set_values('notebook = "AE-1/2"'))
        self.assert_one(result, "warning", "notebook", "unknown field",
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
            insert_after('key = "notebook"', "required = false"),
            insert_after('key = "project"', "multiple = false"),
            insert_after('key = "project"', "facet = false"),
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
                       'project = "teaching"')))

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
        for key, option in (("notebook", "column"), ("notebook", "search"),
                            ("project", "tabs"),
                            ("working_time", "beside")):
            with self.subTest(key=key, option=option):
                result = procedure_field_run(edit_procedure_settings(
                    insert_after(f'key = "{key}"', f"{option} = true")))
                self.assert_configuration_error(result, key, option)

    def test_no_declaration_takes_column_search_tabs_or_beside(
            self) -> None:
        """Requirement: Procedure field declarations (it takes neither
        `column`, nor `search`, nor `tabs`, nor `beside`)."""
        for key in ("notebook", "working_time", "inert_atmosphere",
                    "project"):
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
                 ("notebook", "facet = true", "facet"),
                 ("working_time", "facet = true", "facet"),
                 ("notebook", "multiple = true", "multiple"),
                 ("notebook", "vocabulary = 'projects'", "vocabulary"),
                 ("project", "pattern = 'x'", "pattern"),
                 ("project", "unique = true", "unique"),
                 ("notebook", "min = 0", "min"))
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
                    insert_after('key = "notebook"', option)))
                self.assert_configuration_error(
                    result, "notebook", option.split(" =")[0])

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
            procedure_declaration("notebook", "text", "Notebook"))))
        self.assert_configuration_error(
            result, "notebook", "fields.procedure")

    def test_a_declaration_lacks_a_required_key(self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (a declaration lacks `key`, `type` or `label`)."""
        cases = [("key", 'key = "working_time"\n', ["key"]),
                 ("type", 'type = "number"\n', ["working_time", "type"]),
                 ("label", 'label = "Working time"\n',
                  ["working_time", "label"]),
                 ("vocabulary", 'vocabulary = "projects"\n',
                  ["project", "vocabulary"])]
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
            ("unique = true", 'unique = "yes"', "notebook", "unique"),
            ("pattern = '[A-Z]{2}-\\d+/\\d+'", "pattern = 5", "notebook",
             "pattern"),
            ('vocabulary = "projects"', "vocabulary = 5", "project",
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
        for key, option in (("notebook", 'required = "yes"'),
                            ("notebook", "required = 1"),
                            ("inert_atmosphere", 'facet = "yes"'),
                            ("project", "facet = 1"),
                            ("project", 'multiple = "yes"')):
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
        self.assert_configuration_error(result, "notebook", "pattern")

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
                      'key = "notebook"\ntype = "text"\n'
                      'label = "Lab notebook"\n'))
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
                self.assert_configuration_error(result, "project")

    def test_a_compound_declaration(self) -> None:
        """Scenario: A compound declaration."""
        result = procedure_field_run(edit_procedure_settings(append_text(
            declaration("notebook", "text", "Notebook"))))
        self.assert_configuration_error(result, "fields.compound")

    def test_a_compound_declaration_beside_procedure_declarations(
            self) -> None:
        """Requirement: Procedure declaration errors are configuration
        errors (`fields` holds a key other than `procedure`, `compound`
        among them)."""
        for name, text in {
                "the fixture's own key": declaration(
                    "notebook", "text", "Notebook"),
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
            set_values('notebook = "AE-12"'))
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
        self.check_one('notebook = "AE-12"', "notebook",
                       "must match the pattern")

    def test_the_pattern_is_matched_as_a_whole(self) -> None:
        """Requirement: Procedure field values (a text value matches its
        pattern as a whole, as a compound's does)."""
        for value in ("AE-1/2 ", "xAE-1/2", "ae-1/2", "AE-1/2/3"):
            with self.subTest(value=value):
                self.check_one(f'notebook = "{value}"', "notebook",
                               "must match the pattern")

    def test_an_empty_or_unquoted_text_value(self) -> None:
        """Requirement: Procedure field values (the messages of the
        compound fields: `must not be empty`, `must be a string`)."""
        self.check_one('notebook = ""', "notebook", "must not be empty")
        for line in ("notebook = 5", "notebook = true",
                     'notebook = ["AE-1/2"]'):
            with self.subTest(line=line):
                self.check_one(line, "notebook", "must be a string")

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
        self.check_one('project = "outreach"', "project",
                       'unknown value "outreach"', "projects")

    def test_a_choice_may_name_a_value_at_any_level(self) -> None:
        """Requirement: Procedure field values (`choice` at every level
        of its vocabulary)."""
        for value in ("teaching", "first-year-practical", "research"):
            with self.subTest(project=value):
                self.assert_clean(procedure_field_run(
                    set_values(f'project = "{value}"')))

    def test_a_single_choice_must_be_a_string(self) -> None:
        """Requirement: Procedure field values (`choice`: `must be a
        string`)."""
        for value in ("5", '["research"]', "true"):
            with self.subTest(project=value):
                self.check_one(f"project = {value}", "project",
                               "must be a string")

    def test_a_multiple_choice_is_a_list(self) -> None:
        """Requirement: Procedure field values (`multiple`, as for a
        compound field)."""
        multiple = edit_procedure_settings(
            insert_after('key = "project"', "multiple = true"))
        self.assert_clean(procedure_field_run(
            multiple, set_values(
                'project = ["first-year-practical", "research"]')))
        result = procedure_field_run(
            multiple, set_values('project = "research"'))
        self.assert_one(result, "error", "project",
                        "must be a list of strings",
                        path_suffix=BASELINE_FILE)
        result = procedure_field_run(
            multiple, set_values('project = ["research", "research"]'))
        self.assert_one(result, "error", "project", 'repeats "research"',
                        path_suffix=BASELINE_FILE)
        result = procedure_field_run(
            multiple, set_values('project = ["research", "nope"]'))
        self.assert_one(result, "error", "project", 'unknown value "nope"',
                        path_suffix=BASELINE_FILE)

    def test_a_required_field_on_every_procedure(self) -> None:
        """Scenario: A required field on every procedure."""
        result = procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "project"', "required = true")),
            add_procedure(GENERAL_FILE, source=GENERAL))
        self.assert_errors_on(result, "project", "required field missing",
                              BASELINE_FILE, GENERAL_FILE)

    def test_a_required_field_that_is_set_passes(self) -> None:
        """Requirement: Procedure field values (`required`)."""
        self.assert_clean(procedure_field_run(
            edit_procedure_settings(
                insert_after('key = "project"', "required = true")),
            add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('project = "research"'),
            set_values('project = "teaching"', name=GENERAL_FILE)))

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
            set_values('notebook = "AE-3/1"', "working_time = 4",
                       name=GENERAL_FILE)))
        result = procedure_field_run(
            add_procedure(GENERAL_FILE, source=GENERAL),
            set_values('project = "outreach"', name=GENERAL_FILE))
        self.assert_one(result, "error", "project", "unknown value",
                        path_suffix=GENERAL_FILE)

    def test_a_value_set_by_two_procedures(self) -> None:
        """Scenario: A value set by two procedures."""
        result = procedure_field_run(
            set_values('notebook = "AE-1/2"'),
            add_copy("OSDB-0101-copy.md", 101))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_file = {Path(p.path).name: p for p in result.problems}
        self.assertEqual(set(by_file), {BASELINE_FILE, "OSDB-0101-copy.md"})
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, "notebook", result.stdout)
            self.assertIn("also set by", problem.message)
        self.assertIn("OSDB-0101", by_file[BASELINE_FILE].message)
        self.assertNotIn("OSDB-0100", by_file[BASELINE_FILE].message)
        self.assertIn("OSDB-0100", by_file["OSDB-0101-copy.md"].message)
        self.assertNotIn("OSDB-0101", by_file["OSDB-0101-copy.md"].message)

    def test_three_procedures_name_each_other(self) -> None:
        """Requirement: Procedure field values (the IDs of the other
        procedures)."""
        result = procedure_field_run(
            set_values('notebook = "AE-1/2"'),
            add_copy("OSDB-0101-copy.md", 101),
            add_copy("OSDB-0102-copy.md", 102))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 3, result.stdout)
        ids = {BASELINE_FILE: "OSDB-0100", "OSDB-0101-copy.md": "OSDB-0101",
               "OSDB-0102-copy.md": "OSDB-0102"}
        for problem in result.problems:
            own = ids[Path(problem.path).name]
            self.assertEqual(problem.field, "notebook")
            self.assertNotIn(own, problem.message)
            for other in set(ids.values()) - {own}:
                self.assertIn(other, problem.message)

    def test_different_values_under_a_unique_field_pass(self) -> None:
        """Requirement: Procedure field values (only a repeated value
        draws an error)."""
        self.assert_clean(procedure_field_run(
            add_copy("OSDB-0101-copy.md", 101, 'notebook = "AE-1/3"'),
            set_values('notebook = "AE-1/2"')))

    def test_a_repeated_value_of_a_field_that_is_not_unique_passes(
            self) -> None:
        """Requirement: Procedure field values (`unique` is opt-in)."""
        self.assert_clean(procedure_field_run(
            add_copy("OSDB-0101-copy.md", 101, 'project = "research"',
                     "working_time = 2"),
            set_values('project = "research"', "working_time = 2")))

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
            set_values('notebook = "AE-1/2"'), add_german()))

    def test_a_variant_is_not_compared_beside_its_reference(self) -> None:
        """Requirement: Procedure field values (the procedures compared
        are those that stand for their IDs)."""
        result = procedure_field_run(
            set_values('notebook = "AE-1/2"'), add_german(),
            add_copy("OSDB-0101-copy.md", 101))
        self.assert_errors_on(result, "notebook", "also set by",
                              BASELINE_FILE, "OSDB-0101-copy.md")
        by_file = {Path(p.path).name: p for p in result.problems}
        self.assertIn("OSDB-0101", by_file[BASELINE_FILE].message)
        self.assertIn("OSDB-0100", by_file["OSDB-0101-copy.md"].message)
        self.assertNotIn("de.md", result.stdout)

    def test_values_that_fail_their_checks_are_not_compared(self) -> None:
        """Requirement: Procedure field values (every value that passes
        the checks of its field)."""
        result = procedure_field_run(
            set_values('notebook = "AE-12"'),
            add_copy("OSDB-0101-copy.md", 101))
        self.assert_errors(result, "notebook", "must match the pattern", 2)
        self.assertNotIn("also set by", result.stdout)

    def test_a_file_that_does_not_parse_sets_no_value(self) -> None:
        """Requirement: Procedure field values (a file whose front matter
        does not parse sets no value)."""
        result = procedure_field_run(
            set_values('notebook = "AE-1/2"'),
            add_copy("OSDB-0101-broken.md", 101, 'notebook = "AE-1/2"'),
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


if __name__ == "__main__":
    unittest.main()
