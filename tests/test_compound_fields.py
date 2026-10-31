"""Compound fields (compound-fields): the declarations of a collection's
``orgsyndb.toml``, its vocabularies, their configuration errors and the
checks of the values a compound file sets, driven through field-declaration
runs (procedure-validation "Fixture suite")."""

import unittest
from pathlib import Path

from support import (COMPOUNDS, FIELDS, FIXTURES, STATIC_DIR, Result,
                     ValidatorTestCase, append_text, declaration,
                     edit_field_compound, edit_settings, edit_vocabulary,
                     field_variant_run, fields_copy, fixture_run,
                     insert_after, replace_text, run_validator,
                     write_vocabulary)
from support import VOCABULARY as VOCABULARY_FILE

COMPOUND_FILES = len(list(COMPOUNDS.glob("*.toml")))
EDITED = "ethyl-acetate.toml"
VOCABULARY = "chemical-classes"
BUILT_IN_KEYS = ("name", "name_de", "formula", "mw", "smiles", "cas",
                 "structure_image")
RESERVED_KEYS = ("id", "title", "created", "modified", "text", "q", "sort",
                 "view")


def set_value(line: str, compound: str = "ethyl-acetate"):
    """A field change appending the assignment ``line`` to a compound
    file of the registry copy."""
    return edit_field_compound(compound, append_text(line))


def replace_settings(text: str):
    """A field change replacing the whole ``orgsyndb.toml``."""
    return edit_settings(lambda _: text)


class FieldTestCase(ValidatorTestCase):
    def assert_configuration_error(self, result: Result,
                                   *needles: str) -> None:
        """Exit status 2, nothing on stdout, and a message on stderr that
        begins ``validate.py: error:`` and contains every needle."""
        self.assertEqual(result.returncode, 2,
                         f"stdout={result.stdout!r} "
                         f"stderr={result.stderr!r}")
        self.assertEqual(result.stdout, "")
        self.assertIn("validate.py: error:", result.stderr)
        self.assertNotIn("unrecognized arguments", result.stderr)
        for needle in needles:
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stderr)

    def assert_errors(self, result: Result, field: str, text: str,
                      count: int) -> None:
        """Exit status 1 and exactly ``count`` lines, all errors with
        ``field`` and a message containing ``text``."""
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), count,
                         result.stdout)
        self.assertEqual(len(result.problems), count, result.stdout)
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, field, result.stdout)
            self.assertIn(text, problem.message, result.stdout)


class FieldDeclarationTests(FieldTestCase):
    def test_the_fixture_declarations_are_accepted(self) -> None:
        """Scenario: The fixture declarations are accepted."""
        self.assert_clean(field_variant_run())

    def test_a_settings_file_without_fields_declares_none(self) -> None:
        """Requirement: Field declarations (no `fields`)."""
        result = field_variant_run(
            replace_settings("format = 1\n"),
            set_value('item_number = "CH-0001"'))
        self.assert_one(result, "warning", "item_number", "unknown field",
                        path_suffix=EDITED)

    def test_an_undeclared_key_is_still_unknown(self) -> None:
        """Requirement: Compound fields (any other key is a warning)."""
        result = field_variant_run(
            set_value('item_nr = "CH-0001"'))
        self.assert_one(result, "warning", "item_nr", "unknown field",
                        path_suffix=EDITED)

    def test_keys_that_follow_the_pattern_are_accepted(self) -> None:
        """Requirement: Field declarations (the key pattern)."""
        for key in ("a", "batch_2a", "x1_y2_z3", "de", "note_dex"):
            with self.subTest(key=key):
                self.assert_clean(field_variant_run(
                    edit_settings(append_text(
                        declaration(key, "boolean", "Flag")))))

    def test_defaults_may_be_written_out(self) -> None:
        """Requirement: Field declarations (defaults)."""
        result = field_variant_run(edit_settings(
            insert_after('key = "short_name"', "required = false"),
            insert_after('key = "storage"', "multiple = false"),
            insert_after('key = "in_house"', "column = false"),
            insert_after('key = "stock"', "unique = false")))
        self.assert_clean(result)

    def test_equal_bounds_and_float_bounds_are_accepted(self) -> None:
        """Requirement: Field declarations (min not greater than max)."""
        for old, new in (("min = 0", "min = 5\nmax = 5"),
                         ("min = 0", "min = 0.5\nmax = 2.5"),
                         ("min = 0", "max = 100")):
            with self.subTest(bounds=new):
                self.assert_clean(field_variant_run(
                    edit_settings(replace_text(old, new))))

    def test_a_vocabulary_that_no_declaration_names_is_not_read(
            self) -> None:
        """Requirement: Vocabularies (an unused vocabulary)."""
        result = field_variant_run(
            write_vocabulary("unused", "this is [not toml\n"),
            write_vocabulary("Bad_Name", b"\xff\xfe"))
        self.assert_clean(result)

    def test_facets_and_search_where_the_types_take_them(self) -> None:
        """Scenario: Facets and search where the types take them."""
        result = field_variant_run(edit_settings(
            insert_after('key = "chemical_class"', "facet = true"),
            insert_after('key = "storage"', "facet = true"),
            insert_after('key = "in_house"', "facet = true"),
            insert_after('key = "item_number"', "search = true"),
            insert_after('key = "short_name"', "search = true")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_facet_and_search_may_be_written_as_false(self) -> None:
        """Requirement: Field declarations (facet and search default to
        false)."""
        result = field_variant_run(edit_settings(
            insert_after('key = "chemical_class"', "facet = false"),
            insert_after('key = "in_house"', "facet = false"),
            insert_after('key = "short_name"', "search = false")))
        self.assert_clean(result)

    def test_a_facet_choice_may_hold_one_value_or_many(self) -> None:
        """Requirement: Field declarations (facet on a single and on a
        multiple choice)."""
        for key in ("chemical_class", "storage"):
            with self.subTest(key=key):
                self.assert_clean(field_variant_run(edit_settings(
                    insert_after(f'key = "{key}"', "facet = true"))))

    def test_two_fields_may_share_a_vocabulary(self) -> None:
        """Requirement: Vocabularies (one vocabulary, two fields)."""
        result = field_variant_run(
            edit_settings(append_text(declaration(
                "main_class", "choice", "Main class",
                f'vocabulary = "{VOCABULARY}"'))),
            set_value('main_class = "ketones"'))
        self.assert_clean(result)


class DeclarationErrorTests(FieldTestCase):
    def test_an_option_the_type_does_not_take(self) -> None:
        """Scenario: An option the type does not take."""
        result = field_variant_run(edit_settings(
            insert_after('key = "stock"', 'pattern = "x"')))
        self.assert_configuration_error(result, "stock", "pattern")

    def test_every_type_refuses_the_options_it_does_not_take(self) -> None:
        """Requirement: Declaration errors are configuration errors (a key
        that its type does not take)."""
        cases = {
            "item_number": ["min = 0", "max = 1", 'unit = "g"',
                            'vocabulary = "storage"', "multiple = true",
                            "facet = true"],
            "short_name": ["min = 0", 'unit = "g"', "multiple = true",
                           "facet = true"],
            "stock": ["pattern = '.'", 'vocabulary = "storage"',
                      "multiple = true", "facet = true", "search = true"],
            "in_house": ["unique = true", "pattern = '.'", 'unit = "g"',
                         "min = 0", "max = 1", "multiple = true",
                         'vocabulary = "storage"', "search = true"],
            "storage": ["unique = true", "pattern = '.'", 'unit = "g"',
                        "min = 0", "max = 1", "search = true"],
            "chemical_class": ["search = true"],
        }
        for key, lines in cases.items():
            for line in lines:
                option = line.split(" =")[0]
                with self.subTest(key=key, option=option):
                    result = field_variant_run(edit_settings(
                        insert_after(f'key = "{key}"', line)))
                    self.assert_configuration_error(
                        result, "orgsyndb.toml", key, option)

    def test_an_unknown_option(self) -> None:
        """Scenario: An unknown option."""
        result = field_variant_run(edit_settings(
            insert_after('key = "chemical_class"', "tabs = true")))
        self.assert_configuration_error(result, "chemical_class", "tabs")

    def test_a_facet_or_a_search_where_the_type_does_not_take_it(
            self) -> None:
        """Scenario: A facet or a search where the type does not take it."""
        for key, option in (("short_name", "facet"), ("stock", "search")):
            with self.subTest(key=key, option=option):
                result = field_variant_run(edit_settings(
                    insert_after(f'key = "{key}"', f"{option} = true")))
                self.assert_configuration_error(result, key, option)

    def test_facet_and_search_must_be_booleans(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        value of the wrong type)."""
        for key, option in (("chemical_class", 'facet = "yes"'),
                            ("in_house", "facet = 1"),
                            ("item_number", 'search = "yes"'),
                            ("short_name", "search = 1")):
            with self.subTest(key=key, option=option):
                result = field_variant_run(edit_settings(
                    insert_after(f'key = "{key}"', option)))
                self.assert_configuration_error(
                    result, key, option.split(" =")[0])

    def test_a_key_the_catalogue_reserves(self) -> None:
        """Scenario: A key the catalogue reserves."""
        result = field_variant_run(edit_settings(append_text(
            declaration("title", "text", "Title"))))
        self.assert_configuration_error(result, "title")

    def test_every_reserved_key_is_refused(self) -> None:
        """Requirement: Field declarations (the keys the compound
        catalogue reserves)."""
        for key in RESERVED_KEYS:
            for type_ in ("text", "boolean"):
                with self.subTest(key=key, type=type_):
                    result = field_variant_run(edit_settings(append_text(
                        declaration(key, type_, "Reserved"))))
                    self.assert_configuration_error(
                        result, "orgsyndb.toml", key)

    def test_options_of_later_changes_are_unknown(self) -> None:
        """Requirement: Field declarations (no other key)."""
        for option in ("tabs = true", "help = 'x'"):
            with self.subTest(option=option):
                result = field_variant_run(edit_settings(
                    insert_after('key = "stock"', option)))
                self.assert_configuration_error(
                    result, "stock", option.split(" =")[0])

    def test_a_built_in_key(self) -> None:
        """Scenario: A built-in key."""
        result = field_variant_run(edit_settings(append_text(
            declaration("cas", "text", "CAS"))))
        self.assert_configuration_error(result, "cas")

    def test_every_built_in_key_is_refused(self) -> None:
        """Requirement: Field declarations (the compound-registry keys)."""
        for key in BUILT_IN_KEYS:
            with self.subTest(key=key):
                result = field_variant_run(edit_settings(append_text(
                    declaration(key, "text", "Built in"))))
                self.assert_configuration_error(
                    result, "orgsyndb.toml", key)

    def test_a_key_ending_in_de_is_reserved(self) -> None:
        """Requirement: Field declarations (keys ending in _de)."""
        for key in ("note_de", "short_name_de", "x_1_de"):
            with self.subTest(key=key):
                result = field_variant_run(edit_settings(append_text(
                    declaration(key, "text", "Note"))))
                self.assert_configuration_error(result, key)

    def test_a_key_that_breaks_its_pattern(self) -> None:
        """Requirement: Field declarations (the key pattern)."""
        for key in ("Item_Number", "1abc", "a__b", "a_", "_a", "has-hyphen",
                    "has space", "umlautä"):
            with self.subTest(key=key):
                result = field_variant_run(edit_settings(append_text(
                    declaration(key, "text", "Bad key"))))
                self.assert_configuration_error(result, key)

    def test_a_key_declared_twice(self) -> None:
        """Requirement: Field declarations (no other declaration has the
        key)."""
        result = field_variant_run(edit_settings(append_text(
            declaration("stock", "text", "Stock again"))))
        self.assert_configuration_error(result, "orgsyndb.toml", "stock")

    def test_a_declaration_lacks_a_required_key(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        declaration lacks key, type or label)."""
        cases = [("key", 'key = "stock"\n', ["key"]),
                 ("type", 'type = "number"\n', ["stock", "type"]),
                 ("label", 'label = "Stock"\n', ["stock", "label"]),
                 ("vocabulary", 'vocabulary = "storage"\n',
                  ["storage", "vocabulary"])]
        for name, line, needles in cases:
            with self.subTest(missing=name):
                result = field_variant_run(edit_settings(
                    replace_text(line, "")))
                self.assert_configuration_error(result, *needles)

    def test_a_declaration_with_a_value_of_the_wrong_type(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        value of the wrong type)."""
        cases = [
            ('label = "Stock"', "label = 5", "stock", "label"),
            ('label = "Stock"', 'label = ""', "stock", "label"),
            ('label_de = "Bestand"', "label_de = 5", "stock", "label_de"),
            ('label_de = "Bestand"', 'label_de = ""', "stock", "label_de"),
            ('type = "number"', 'type = "date"', "stock", "type"),
            ('type = "number"', "type = 5", "stock", "type"),
            ('unit = "g"', 'unit = ""', "stock", "unit"),
            ('unit = "g"', "unit = 5", "stock", "unit"),
            ("min = 0", 'min = "0"', "stock", "min"),
            ("min = 0", "min = true", "stock", "min"),
            ("min = 0", "max = false", "stock", "max"),
            ("unique = true", 'unique = "yes"', "item_number", "unique"),
            ("multiple = true", 'multiple = "yes"', "chemical_class",
             "multiple"),
            ("pattern = 'CH-\\d{4}'", "pattern = 5", "item_number",
             "pattern"),
            ('vocabulary = "storage"', "vocabulary = 5", "storage",
             "vocabulary"),
        ]
        for old, new, key, option in cases:
            with self.subTest(change=new):
                result = field_variant_run(edit_settings(
                    replace_text(old, new)))
                self.assert_configuration_error(result, key, option)

    def test_required_and_column_must_be_booleans(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        value of the wrong type)."""
        for option in ('required = "yes"', "required = 1", 'column = "no"',
                       "column = 1"):
            with self.subTest(option=option):
                result = field_variant_run(edit_settings(
                    insert_after('key = "stock"', option)))
                self.assert_configuration_error(
                    result, "stock", option.split(" =")[0])

    def test_a_missing_vocabulary(self) -> None:
        """Scenario: A missing vocabulary."""
        result = field_variant_run(edit_settings(replace_text(
            'vocabulary = "storage"',
            'vocabulary = "no-such-vocabulary"')))
        self.assert_configuration_error(result, "no-such-vocabulary")

    def test_a_vocabulary_name_that_is_not_a_slug(self) -> None:
        """Requirement: Vocabularies (the name pattern)."""
        for name in ("Bad_Name", "../vocabularies/storage", "storage.toml"):
            with self.subTest(name=name):
                result = field_variant_run(edit_settings(replace_text(
                    'vocabulary = "storage"', f'vocabulary = "{name}"')))
                self.assert_configuration_error(result, "vocabulary")

    def test_a_pattern_that_does_not_compile(self) -> None:
        """Scenario: A pattern that does not compile."""
        result = field_variant_run(edit_settings(replace_text(
            "pattern = 'CH-\\d{4}'", 'pattern = "CH-("')))
        self.assert_configuration_error(result, "item_number", "pattern")

    def test_a_pattern_too_large_to_compile(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        pattern that Python cannot compile for its size)."""
        for pattern in ("CH-\\d{4294967296}", "(" * 100000 + ")" * 100000):
            with self.subTest(pattern=pattern[:20]):
                result = field_variant_run(edit_settings(replace_text(
                    "pattern = 'CH-\\d{4}'", f"pattern = '{pattern}'")))
                self.assert_configuration_error(result, "item_number",
                                                "pattern")

    def test_a_bound_that_is_not_a_number(self) -> None:
        """Scenario: A bound that is not a number."""
        result = field_variant_run(edit_settings(
            insert_after('key = "stock"', "max = nan")))
        self.assert_configuration_error(result, "stock", "max")

    def test_infinite_bounds_are_refused(self) -> None:
        """Requirement: Declaration errors are configuration errors (min
        or max is not finite)."""
        for old, new, option in (("min = 0", "min = inf", "min"),
                                 ("min = 0", "min = -inf", "min"),
                                 ("min = 0", "min = 0\nmax = inf", "max"),
                                 ("min = 0", "min = 0\nmax = -inf", "max")):
            with self.subTest(bound=new):
                result = field_variant_run(edit_settings(
                    replace_text(old, new)))
                self.assert_configuration_error(result, "stock", option)

    def test_a_minimum_above_the_maximum(self) -> None:
        """Requirement: Declaration errors are configuration errors (min
        is greater than max)."""
        result = field_variant_run(edit_settings(
            replace_text("min = 0", "min = 5\nmax = 1")))
        self.assert_configuration_error(result, "stock", "min")

    def test_a_misspelt_top_level_key(self) -> None:
        """Scenario: A misspelt top-level key."""
        result = field_variant_run(edit_settings(
            lambda text: text.replace("[[fields.compound]]",
                                      "[[feilds.compound]]")))
        self.assert_configuration_error(result, "feilds")

    def test_a_single_table_instead_of_an_array(self) -> None:
        """Scenario: A single table instead of an array."""
        result = field_variant_run(replace_settings(
            'format = 1\n\n[fields.compound]\nkey = "item_number"\n'
            'type = "text"\nlabel = "Item no."\n'))
        self.assert_configuration_error(result, "fields.compound")

    def test_fields_must_be_a_table_of_compound_declarations(self) -> None:
        """Requirement: Declaration errors are configuration errors
        (`fields`)."""
        cases = {
            "fields is a number": ("format = 1\nfields = 5\n", "fields"),
            "fields is a list": ("format = 1\nfields = []\n", "fields"),
            "another entity": (
                'format = 1\n\n[fields.procedure]\nkey = "x"\n',
                "procedure"),
            "next to compound": (
                'format = 1\n\n[fields]\ncompound = []\nother = 1\n',
                "other"),
            "compound is a number": (
                "format = 1\n\n[fields]\ncompound = 5\n",
                "fields.compound"),
            "compound holds numbers": (
                "format = 1\n\n[fields]\ncompound = [1, 2]\n",
                "fields.compound"),
        }
        for name, (text, needle) in cases.items():
            with self.subTest(case=name):
                result = field_variant_run(replace_settings(text))
                self.assert_configuration_error(result, needle)

    def test_a_named_settings_file_that_does_not_exist(self) -> None:
        """Scenario: A named settings file that does not exist."""
        result = fixture_run(
            "baseline",
            extra=["--settings", FIXTURES / "no-such-settings.toml"])
        self.assert_configuration_error(result, "no-such-settings.toml")

    def test_settings_that_break_the_collection_rules(self) -> None:
        """Requirement: Declaration errors are configuration errors (the
        rules of collection "Collection layout")."""
        cases = {
            "unknown format": ("format = 2\n", "format"),
            "format as a string": ('format = "1"\n', "format"),
            "format missing": ("", "format"),
            "another key": ('format = 1\ntitle = "X"\n', "title"),
            "not TOML": ("format = \n", "orgsyndb.toml"),
        }
        for name, (text, needle) in cases.items():
            with self.subTest(case=name):
                result = field_variant_run(replace_settings(text))
                self.assert_configuration_error(
                    result, "orgsyndb.toml", needle)

    def test_settings_that_are_not_utf8(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        file that cannot be read as UTF-8 TOML)."""
        def change(copy) -> None:
            copy.settings.write_bytes(b'format = 1\n# Caf\xe9\n')
        self.assert_configuration_error(field_variant_run(change),
                                        "orgsyndb.toml")

    def test_a_configuration_error_hides_the_compound_checks(self) -> None:
        """Requirement: Declaration errors are configuration errors (no
        stdout)."""
        result = field_variant_run(
            edit_settings(insert_after('key = "stock"', 'pattern = "x"')),
            set_value("stock = -1"))
        self.assert_configuration_error(result, "stock", "pattern")


class VocabularyErrorTests(FieldTestCase):
    def test_a_value_filed_under_itself(self) -> None:
        """Scenario: A value filed under itself."""
        result = field_variant_run(edit_vocabulary(
            VOCABULARY, insert_after("[carbonyl-compounds]",
                                     'parent = "ketones"')))
        self.assert_configuration_error(result, VOCABULARY, "parent")

    def test_a_value_that_is_its_own_parent(self) -> None:
        """Requirement: Vocabularies (no value is its own ancestor)."""
        result = field_variant_run(edit_vocabulary(
            VOCABULARY, insert_after("[alcohols]", 'parent = "alcohols"')))
        self.assert_configuration_error(result, VOCABULARY, "alcohols")

    def test_a_longer_cycle_of_parents(self) -> None:
        """Requirement: Vocabularies (no value is its own ancestor)."""
        result = field_variant_run(write_vocabulary(
            VOCABULARY,
            '[a]\nlabel = "A"\nparent = "c"\n[b]\nlabel = "B"\n'
            'parent = "a"\n[c]\nlabel = "C"\nparent = "b"\n'
            '[d]\nlabel = "D"\n'))
        self.assert_configuration_error(result, VOCABULARY, "parent")

    def test_a_parent_that_is_not_a_value(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        parent that is not one of its values)."""
        for line in ('parent = "no-such-value"', "parent = 5",
                     'parent = ""'):
            with self.subTest(parent=line):
                result = field_variant_run(edit_vocabulary(
                    VOCABULARY, insert_after("[alcohols]", line)))
                self.assert_configuration_error(
                    result, VOCABULARY, "alcohols", "parent")

    def test_the_parent_may_come_later_in_the_file(self) -> None:
        """Requirement: Vocabularies (a value filed under a parent)."""
        result = field_variant_run(write_vocabulary(
            VOCABULARY,
            '[ketones]\nlabel = "Ketones"\nparent = "carbonyl-compounds"\n'
            '[carbonyl-compounds]\nlabel = "Carbonyl compounds"\n'
            '[esters]\nlabel = "Esters"\n[alcohols]\nlabel = "Alcohols"\n'))
        self.assert_clean(result)

    def test_a_value_key_that_is_not_a_slug(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        vocabulary key that is not a slug)."""
        for key in ("Bad_Key", "-ketones", "ketones-", "two--hyphens",
                    "has space"):
            with self.subTest(key=key):
                result = field_variant_run(edit_vocabulary(
                    VOCABULARY, append_text(f'\n["{key}"]\nlabel = "Bad"')))
                self.assert_configuration_error(result, VOCABULARY, key)

    def test_an_entry_that_is_not_a_table(self) -> None:
        """Requirement: Declaration errors are configuration errors (an
        entry that is not a table)."""
        result = field_variant_run(write_vocabulary(
            VOCABULARY, 'ketones = "Ketones"\n'))
        self.assert_configuration_error(result, VOCABULARY, "ketones")

    def test_an_entry_without_a_proper_label(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        non-empty string `label`)."""
        for old, new in (('label = "Ketones"\n', ""),
                         ('label = "Ketones"', 'label = ""'),
                         ('label = "Ketones"', "label = 5")):
            with self.subTest(change=new):
                result = field_variant_run(edit_vocabulary(
                    VOCABULARY, replace_text(old, new)))
                self.assert_configuration_error(
                    result, VOCABULARY, "ketones", "label")

    def test_a_german_label_must_be_a_non_empty_string(self) -> None:
        """Requirement: Declaration errors are configuration errors (an
        empty or non-string `label_de`)."""
        for new in ('label_de = ""', "label_de = 5"):
            with self.subTest(label_de=new):
                result = field_variant_run(edit_vocabulary(
                    VOCABULARY, replace_text('label_de = "Ketone"', new)))
                self.assert_configuration_error(
                    result, VOCABULARY, "ketones", "label_de")

    def test_a_german_label_may_be_absent(self) -> None:
        """Requirement: Vocabularies (`label_de` is optional)."""
        result = field_variant_run(edit_vocabulary(
            VOCABULARY, replace_text('label_de = "Ketone"\n', "")))
        self.assert_clean(result)

    def test_an_entry_key_that_is_not_allowed(self) -> None:
        """Requirement: Declaration errors are configuration errors (an
        entry key other than label, label_de and parent)."""
        result = field_variant_run(edit_vocabulary(
            VOCABULARY, insert_after("[alcohols]", 'colour = "red"')))
        self.assert_configuration_error(
            result, VOCABULARY, "alcohols", "colour")

    def test_a_vocabulary_without_a_value(self) -> None:
        """Requirement: Vocabularies (at least one value)."""
        for content in ("", "# Nothing here yet.\n"):
            with self.subTest(content=content):
                result = field_variant_run(
                    write_vocabulary(VOCABULARY, content))
                self.assert_configuration_error(result, VOCABULARY)

    def test_a_vocabulary_that_is_not_toml(self) -> None:
        """Requirement: Declaration errors are configuration errors (a
        vocabulary that cannot be read as UTF-8 TOML)."""
        for content in ("[ketones\nlabel = 1\n",
                        b'[a]\nlabel = "Caf\xe9"\n'):
            with self.subTest(content=content):
                result = field_variant_run(
                    write_vocabulary("storage", content))
                self.assert_configuration_error(result, "storage")

    def test_vocabularies_are_read_beside_the_settings_file(self) -> None:
        """Requirement: Command-line interface (--settings resolves its
        vocabularies beside the settings file)."""
        with fields_copy() as copy:
            collection = copy.settings.parent
            elsewhere = collection.parent / "elsewhere"
            elsewhere.mkdir()
            settings = elsewhere / "orgsyndb.toml"
            settings.write_bytes(copy.settings.read_bytes())
            result = run_validator(
                ["--vocabulary", VOCABULARY_FILE, "--static-dir",
                 STATIC_DIR, "--compounds", copy.registry, "--settings",
                 settings, FIXTURES / "baseline"], cwd=collection)
        self.assert_configuration_error(result, "chemical-classes")


class FieldValueTests(FieldTestCase):
    def check_one(self, line: str, field: str, text: str,
                  *more: str) -> None:
        """A field-declaration run that sets ``line`` in
        ``ethyl-acetate.toml`` reports exactly one error on that file,
        with ``field`` and all of ``text`` and ``more``."""
        result = field_variant_run(set_value(line))
        problem = self.assert_one(result, "error", field, text,
                                  path_suffix=EDITED)
        for needle in more:
            self.assertIn(needle, problem.message)

    def test_a_text_value_that_breaks_its_pattern(self) -> None:
        """Scenario: A text value that breaks its pattern."""
        self.check_one('item_number = "CH-12"', "item_number",
                       "must match the pattern")

    def test_the_pattern_is_matched_as_a_whole(self) -> None:
        """Requirement: Field values (a text value matches its pattern as
        a whole)."""
        for value in ("CH-12345", "xCH-1234", "CH-1234 ", "ch-1234"):
            with self.subTest(value=value):
                self.check_one(f'item_number = "{value}"', "item_number",
                               "must match the pattern")

    def test_the_message_names_the_pattern(self) -> None:
        """Requirement: Field values (`must match the pattern <pattern>`)."""
        self.check_one('item_number = "CH-12"', "item_number",
                       "must match the pattern", "CH-\\d{4}")

    def test_a_text_value_that_matches_passes(self) -> None:
        """Requirement: Field values (a text value)."""
        for line in ('item_number = "CH-0001"', 'short_name = "EtOAc"',
                     'short_name = "x"'):
            with self.subTest(line=line):
                self.assert_clean(field_variant_run(
                    set_value(line)))

    def test_an_empty_or_unquoted_text_value(self) -> None:
        """Requirement: Field values (`must be a string`, `must not be
        empty`)."""
        self.check_one('short_name = ""', "short_name", "must not be empty")
        for line in ("short_name = 5", "short_name = true",
                     'short_name = ["a"]'):
            with self.subTest(line=line):
                self.check_one(line, "short_name", "must be a string")

    def test_a_value_set_twice_under_a_unique_field(self) -> None:
        """Scenario: A value set twice under a unique field."""
        result = field_variant_run(
            set_value('item_number = "CH-0001"'),
            set_value('item_number = "CH-0001"',
                      compound="ethanol"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_file = {Path(p.path).name: p for p in result.problems}
        self.assertEqual(set(by_file), {"ethyl-acetate.toml",
                                        "ethanol.toml"})
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, "item_number", result.stdout)
            self.assertIn("also set by", problem.message)
        self.assertIn("ethyl-acetate", by_file["ethanol.toml"].message)
        self.assertIn("ethanol", by_file["ethyl-acetate.toml"].message)
        self.assertNotIn("ethanol", by_file["ethanol.toml"].message)
        self.assertNotIn("ethyl-acetate",
                         by_file["ethyl-acetate.toml"].message)

    def test_three_compounds_name_each_other(self) -> None:
        """Requirement: Field values (the keys of the other compounds)."""
        keys = ("ethyl-acetate", "ethanol", "acetic-acid")
        result = field_variant_run(*(
            set_value('item_number = "CH-0001"', key)
            for key in keys))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 3, result.stdout)
        for problem in result.problems:
            name = Path(problem.path).name.removesuffix(".toml")
            self.assertEqual(problem.field, "item_number")
            for other in keys:
                if other != name:
                    self.assertIn(other, problem.message)

    def test_different_values_under_a_unique_field_pass(self) -> None:
        """Requirement: Field values (only a repeated value draws an
        error)."""
        result = field_variant_run(
            set_value('item_number = "CH-0001"'),
            set_value('item_number = "CH-0002"',
                      compound="ethanol"))
        self.assert_clean(result)

    def test_a_repeated_value_of_a_field_that_is_not_unique_passes(
            self) -> None:
        """Requirement: Field values (`unique` is opt-in)."""
        result = field_variant_run(
            set_value('short_name = "same"'),
            set_value('short_name = "same"',
                      compound="ethanol"))
        self.assert_clean(result)

    def test_a_unique_number_field(self) -> None:
        """Requirement: Field declarations (`unique` for `number`)."""
        result = field_variant_run(
            edit_settings(insert_after('key = "stock"', "unique = true")),
            set_value("stock = 5"),
            set_value("stock = 5", compound="ethanol"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 2, result.stdout)
        for problem in result.problems:
            self.assertEqual(problem.field, "stock")
            self.assertIn("also set by", problem.message)

    def test_values_that_fail_their_checks_are_not_compared(self) -> None:
        """Requirement: Field values (every value that passes these
        checks)."""
        result = field_variant_run(
            set_value('item_number = "CH-12"'),
            set_value('item_number = "CH-12"',
                      compound="ethanol"))
        self.assert_errors(result, "item_number", "must match the pattern",
                           2)
        self.assertNotIn("also set by", result.stdout)

    def test_a_compound_file_that_does_not_parse_sets_no_value(
            self) -> None:
        """Requirement: Field values (a compound file that does not
        parse)."""
        result = field_variant_run(
            set_value('item_number = "CH-0001"'),
            edit_field_compound(
                "ethanol", lambda text: 'item_number = "CH-0001"\nname = "'))
        self.assert_one(result, "error", "toml", "invalid TOML",
                        path_suffix="ethanol.toml")

    def test_a_number_below_its_minimum(self) -> None:
        """Scenario: A number below its minimum."""
        self.check_one("stock = -1", "stock", "must be at least 0")

    def test_a_number_above_its_maximum(self) -> None:
        """Requirement: Field values (`must be at most <max>`)."""
        result = field_variant_run(
            edit_settings(insert_after('key = "stock"', "max = 100")),
            set_value("stock = 101"))
        self.assert_one(result, "error", "stock", "must be at most 100",
                        path_suffix=EDITED)

    def test_bounds_are_inclusive(self) -> None:
        """Requirement: Field values (bounding the value inclusively)."""
        for value in ("0", "100", "0.0", "99.5"):
            with self.subTest(stock=value):
                self.assert_clean(field_variant_run(
                    edit_settings(insert_after('key = "stock"',
                                               "max = 100")),
                    set_value(f"stock = {value}")))

    def test_integers_and_floats_are_numbers(self) -> None:
        """Requirement: Field values (a TOML integer or float)."""
        for value in ("12", "12.5", "1e3", "0"):
            with self.subTest(stock=value):
                self.assert_clean(field_variant_run(
                    set_value(f"stock = {value}")))

    def test_a_quoted_number(self) -> None:
        """Scenario: A quoted number."""
        self.check_one('stock = "5"', "stock", "must be a number")

    def test_a_value_that_is_not_a_finite_number(self) -> None:
        """Requirement: Field values (`must be a number, unquoted`)."""
        for value in ("true", "inf", "-inf", "nan", "[1]",
                      "2026-01-01"):
            with self.subTest(stock=value):
                self.check_one(f"stock = {value}", "stock",
                               "must be a number")

    def test_a_number_without_bounds(self) -> None:
        """Requirement: Field declarations (`min` and `max` are
        optional)."""
        result = field_variant_run(
            edit_settings(replace_text("min = 0\n", "")),
            set_value("stock = -1000000"))
        self.assert_clean(result)

    def test_a_quoted_boolean(self) -> None:
        """Scenario: A quoted boolean."""
        self.check_one('in_house = "yes"', "in_house",
                       "must be true or false")

    def test_booleans_are_true_or_false(self) -> None:
        """Requirement: Field values (`boolean`)."""
        for value in ("true", "false"):
            with self.subTest(in_house=value):
                self.assert_clean(field_variant_run(
                    set_value(f"in_house = {value}")))
        for value in ("1", "0", '"true"', "[true]"):
            with self.subTest(in_house=value):
                self.check_one(f"in_house = {value}", "in_house",
                               "must be true or false")

    def test_a_value_outside_the_vocabulary(self) -> None:
        """Scenario: A value outside the vocabulary."""
        self.check_one('storage = "freezer"', "storage",
                       'unknown value "freezer"', "vocabularies/storage.toml")

    def test_a_choice_may_name_a_value_at_any_level(self) -> None:
        """Scenario: Values at every level."""
        result = field_variant_run(
            set_value('chemical_class = ["carbonyl-compounds", "ketones"]'),
            set_value('storage = "fridge"'))
        self.assert_clean(result)

    def test_a_single_choice_must_be_a_string(self) -> None:
        """Requirement: Field values (`choice`: `must be a string`)."""
        for value in ("5", '["fridge"]', "true"):
            with self.subTest(storage=value):
                self.check_one(f"storage = {value}", "storage",
                               "must be a string")

    def test_one_value_where_a_list_is_declared(self) -> None:
        """Scenario: One value where a list is declared."""
        self.check_one('chemical_class = "esters"', "chemical_class",
                       "must be a list of strings")

    def test_a_list_of_something_else_than_strings(self) -> None:
        """Requirement: Field values (`must be a list of strings`)."""
        for value in ("5", "[5]", '["esters", 5]', "[[]]"):
            with self.subTest(chemical_class=value):
                self.check_one(f"chemical_class = {value}",
                               "chemical_class",
                               "must be a list of strings")

    def test_an_empty_list(self) -> None:
        """Requirement: Field values (`must not be empty`)."""
        self.check_one("chemical_class = []", "chemical_class",
                       "must not be empty")

    def test_a_repeated_value(self) -> None:
        """Scenario: A repeated value."""
        self.check_one('chemical_class = ["esters", "esters"]',
                       "chemical_class", 'repeats "esters"')

    def test_one_unknown_value_error_per_string(self) -> None:
        """Requirement: Field values (one `unknown value` error per
        string)."""
        self.check_one('chemical_class = ["esters", "nope"]',
                       "chemical_class", 'unknown value "nope"',
                       "vocabularies/chemical-classes.toml")
        result = field_variant_run(set_value(
            'chemical_class = ["nope", "esters", "nada"]'))
        self.assert_errors(result, "chemical_class", "unknown value", 2)
        messages = " ".join(p.message for p in result.problems)
        self.assertIn('unknown value "nope"', messages)
        self.assertIn('unknown value "nada"', messages)

    def test_a_required_field(self) -> None:
        """Scenario: A required field."""
        result = field_variant_run(edit_settings(
            insert_after('key = "storage"', "required = true")))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), COMPOUND_FILES, result.stdout)
        self.assertEqual(
            sorted(Path(p.path).name for p in result.problems),
            sorted(path.name for path in COMPOUNDS.glob("*.toml")))
        for problem in result.problems:
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertEqual(problem.field, "storage", result.stdout)
            self.assertIn("required field missing", problem.message)

    def test_a_required_field_that_is_set_passes(self) -> None:
        """Requirement: Field values (`required`)."""
        steps = [edit_settings(insert_after('key = "storage"',
                                            "required = true"))]
        steps += [edit_field_compound(path.stem,
                                      append_text('storage = "fridge"'))
                  for path in sorted(COMPOUNDS.glob("*.toml"))]
        self.assert_clean(field_variant_run(*steps))

    def test_a_field_that_is_not_required_may_be_absent(self) -> None:
        """Requirement: Field values (`required` defaults to false)."""
        self.assert_clean(field_variant_run())

    def test_a_value_of_the_wrong_type_is_not_also_a_missing_one(
            self) -> None:
        """Requirement: Field values (a value of the wrong type draws that
        one error)."""
        result = field_variant_run(
            edit_settings(insert_after('key = "stock"', "required = true")),
            *(edit_field_compound(path.stem, append_text("stock = 1"))
              for path in sorted(COMPOUNDS.glob("*.toml"))
              if path.stem != "ethyl-acetate"),
            set_value('stock = "5"'))
        self.assert_one(result, "error", "stock", "must be a number",
                        path_suffix=EDITED)


class DeclaredKeyTests(FieldTestCase):
    def test_every_declared_key_is_known(self) -> None:
        """Requirement: Compound fields (declared keys are not unknown)."""
        result = field_variant_run(edit_field_compound(
            "ethyl-acetate", append_text(
                'item_number = "CH-0001"\nshort_name = "EtOAc"\n'
                'stock = 12.5\nin_house = true\n'
                'chemical_class = ["esters"]\nstorage = "cabinet"')))
        self.assert_clean(result)

    def test_the_fixture_registry_sets_no_declared_field(self) -> None:
        """Requirement: Fixture suite (no fixture compound sets a declared
        field)."""
        declared = {"item_number", "short_name", "stock", "in_house",
                    "chemical_class", "storage"}
        for path in sorted(COMPOUNDS.glob("*.toml")):
            with self.subTest(compound=path.stem):
                text = path.read_text(encoding="utf-8")
                found = {key for key in declared
                         if any(line.startswith(f"{key} ")
                                for line in text.splitlines())}
                self.assertEqual(found, set())

    def test_the_fixture_settings_are_where_the_suite_says(self) -> None:
        """Requirement: Fixture suite (the `fields/` fixtures)."""
        self.assertTrue((FIELDS / "orgsyndb.toml").is_file())
        self.assertEqual(
            sorted(p.name for p in (FIELDS / "vocabularies").iterdir()),
            ["chemical-classes.toml", "storage.toml"])


if __name__ == "__main__":
    unittest.main()
