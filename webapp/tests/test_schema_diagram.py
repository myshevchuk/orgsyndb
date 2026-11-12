"""Tests of the table diagram (database-diagram)."""

import io
import re
import tempfile
import unittest
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Q
from django.utils import translation

from inventory.models import Article, Item
from orgsyndb_web import schema_diagram as sd
from orgsyndb_web.schema_diagram import Column, LayoutError, Link, Table

APP_TABLES = {
    "accounts_user", "registry_substance", "registry_substanceclass",
    "vocabulary_chemicalclass", "vocabulary_group", "vocabulary_project",
    "vocabulary_reactiontype", "inventory_article", "inventory_item",
    "inventory_movement", "inventory_deliverynote", "inventory_deliveryline",
    "inventory_lot", "inventory_lotmovement", "inventory_enteredconsumption",
    "tasks_task", "tasks_taskstep", "tasks_counter", "planning_parameters",
    "demo_demomark",
    "collection_import", "collection_procedure", "collection_scopeentry",
    "collection_entrysubstance", "collection_sequence", "collection_step"}


def by_name(items: tuple, name: str):
    """Return the item of ITEMS whose name is NAME."""
    return next(item for item in items if item.name == name)


class CollectionTests(unittest.TestCase):
    """Scenarios of "Tables and columns" read from the collected schema."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.schema = sd.collect()

    def table(self, name: str) -> Table:
        return by_name(self.schema.tables, name)

    def column(self, table: str, column: str) -> Column:
        return by_name(self.table(table).columns, column)

    def test_only_the_applications_tables(self) -> None:
        """Scenario: Only the application's tables."""
        self.assertEqual({t.name for t in self.schema.tables}, APP_TABLES)

    def test_item_columns(self) -> None:
        """Scenario: An item's columns."""
        item = self.table("inventory_item")
        self.assertEqual(
            [c.name for c in item.columns],
            ["id", "article_id", "size", "unit", "quantity", "note",
             "status", "stocked_on", "compartment", "box"])
        self.assertEqual((item.columns[0].key, item.columns[0].type),
                         ("PK", "bigint"))
        article = self.column("inventory_item", "article_id")
        self.assertEqual((article.key, article.type, article.nullable,
                          article.ref),
                         ("FK", "bigint", False, "inventory_article"))
        self.assertEqual(self.column("inventory_item", "size").type,
                         "numeric(10,3)")
        self.assertEqual(item.history, "inventory_historicalitem")
        status = " ".join(self.column("inventory_item", "status").notes)
        for value in ("active", "not_needed", "discontinued"):
            self.assertIn(value, status)
        quantity = self.column("inventory_item", "quantity").notes
        self.assertIn("not in history", quantity)
        self.assertIn("CHECK >= 0", quantity)
        self.assertFalse(any(n.startswith(("at most", "from"))
                             for n in quantity), quantity)

    def test_movement_keys(self) -> None:
        """Scenario: Keys of a movement."""
        item = self.column("inventory_movement", "item_id")
        self.assertEqual((item.key, item.type, item.nullable, item.ref),
                         ("FK", "bigint", False, "inventory_item"))
        self.assertEqual(item.on_delete, "CASCADE")
        note = self.column("inventory_movement", "delivery_note_id")
        self.assertEqual((note.key, note.nullable, note.on_delete),
                         ("FK", True, "PROTECT"))
        bulk = self.column("inventory_movement", "bulk_movement_id")
        self.assertEqual((bulk.key, bulk.ref),
                         ("1:1", "inventory_lotmovement"))
        reverses = self.column("inventory_movement", "reverses_id")
        self.assertEqual((reverses.key, reverses.ref),
                         ("1:1", "inventory_movement"))
        self.assertEqual(self.column("inventory_movement", "booked_at").type,
                         "timestamptz")

    def test_unique_columns_and_short_types(self) -> None:
        self.assertEqual(self.column("accounts_user", "initials").key, "UQ")
        self.assertEqual(self.column("tasks_task", "number").key, "UQ")
        self.assertEqual(self.column("tasks_counter", "name").key, "PK")
        self.assertEqual(self.column("planning_parameters", "certainty").type,
                         "float8")
        self.assertEqual(self.column("collection_procedure", "general").type,
                         "boolean")

    def test_notes_from_validators_defaults_and_checks(self) -> None:
        certainty = self.column("planning_parameters", "certainty").notes
        self.assertIn("from 0.5 to 0.999", certainty)
        self.assertIn("default 0.95", certainty)
        self.assertIn("from 1 to 4",
                      self.column("inventory_enteredconsumption",
                                  "quarter").notes)
        count = self.column("inventory_deliveryline", "count")
        self.assertIn("at least 1", count.notes)
        self.assertEqual(count.check, ">= 0")
        self.assertIsNone(self.column("inventory_item", "note").check)

    def test_notes_in_english(self) -> None:
        """Scenario: Notes in English."""
        with translation.override("de"):
            schema = sd.collect()
        certainty = by_name(by_name(schema.tables, "planning_parameters")
                            .columns, "certainty").notes
        self.assertIn("The probability with which a stock is to last its "
                      "runway.", certainty)
        self.assertIn("from 0.5 to 0.999", certainty)
        self.assertIn("default 0.95", certainty)

    def test_an_articles_key(self) -> None:
        """Scenario: An article's key."""
        substance = self.column("inventory_article", "substance_id")
        self.assertEqual((substance.key, substance.type,
                          substance.nullable, substance.ref),
                         ("PK", "bigint", False, "registry_substance"))
        number = self.column("inventory_article", "article_number")
        self.assertEqual((number.key, number.type, number.nullable),
                         ("UQ", "varchar(30)", True))

    def test_the_registrys_tables(self) -> None:
        group = self.column("registry_substance", "group_id")
        self.assertEqual((group.key, group.ref, group.on_delete),
                         ("FK", "vocabulary_group", "PROTECT"))
        self.assertEqual(self.column("registry_substance", "mw").type,
                         "numeric(10,3)")
        self.assertTrue(self.column("registry_substance", "mw").nullable)
        for column, ref in (("substance_id", "registry_substance"),
                            ("chemical_class_id", "vocabulary_chemicalclass")):
            with self.subTest(column=column):
                found = self.column("registry_substanceclass", column)
                self.assertEqual((found.key, found.ref), ("FK", ref))
        for name in ("vocabulary_chemicalclass", "vocabulary_group",
                     "vocabulary_project"):
            with self.subTest(table=name):
                parent = self.column(name, "parent_id")
                self.assertEqual((parent.key, parent.ref, parent.nullable),
                                 ("FK", name, True))
                self.assertEqual(
                    [c.name for c in self.table(name).columns],
                    ["id", "key", "label", "label_de", "parent_id"])
        self.assertEqual(
            [c.name for c in self.table("vocabulary_reactiontype").columns],
            ["id", "key", "label", "label_de"])

    def test_the_columns_of_a_task_and_its_steps(self) -> None:
        """Scenario: Only the application's tables (`tasks_taskstep`),
        and the task record's sequence and steps."""
        names = [c.name for c in self.table("tasks_task").columns]
        for gone in ("sequence_steps", "steps_total", "steps_done"):
            with self.subTest(column=gone):
                self.assertNotIn(gone, names)
        sequence = self.column("tasks_task", "sequence_id")
        self.assertEqual((sequence.key, sequence.ref, sequence.nullable),
                         ("FK", "collection_sequence", True))
        self.assertEqual(
            {c.name for c in self.table("tasks_taskstep").columns},
            {"id", "task_id", "position", "entry_id", "planned_import_id",
             "done_on"})
        for column, ref, nullable in (
                ("task_id", "tasks_task", False),
                ("entry_id", "collection_scopeentry", True),
                ("planned_import_id", "collection_import", True)):
            with self.subTest(column=column):
                found = self.column("tasks_taskstep", column)
                self.assertEqual((found.key, found.ref, found.nullable),
                                 ("FK", ref, nullable))
        self.assertTrue(self.column("tasks_taskstep", "done_on").nullable)

    def test_lots_and_tasks_name_substances(self) -> None:
        for name in ("inventory_lot", "tasks_task"):
            with self.subTest(table=name):
                found = self.column(name, "substance_id")
                self.assertEqual((found.key, found.ref, found.nullable),
                                 ("FK", "registry_substance", False))
        names = [c.name for c in self.table("inventory_lot").columns]
        for gone in ("inventory", "article_number"):
            self.assertNotIn(gone, names)
        self.assertNotIn("product",
                         [c.name for c in self.table("tasks_task").columns])

    def test_docstrings(self) -> None:
        item = self.table("inventory_item")
        self.assertTrue(item.about)
        self.assertGreater(len(item.doc), 1)
        self.assertEqual(item.about, item.doc[0])

    def test_history_tables(self) -> None:
        found = {(h.name, h.tracked, h.omitted)
                 for h in self.schema.history_tables}
        wanted = {
            ("inventory_historicalitem", "inventory_item", ("quantity",)),
            ("inventory_historicalarticle", "inventory_article", ()),
            ("inventory_historicaldeliverynote", "inventory_deliverynote",
             ()),
            ("inventory_historicallot", "inventory_lot", ("amount",)),
            ("registry_historicalsubstance", "registry_substance", ()),
            ("vocabulary_historicalchemicalclass",
             "vocabulary_chemicalclass", ()),
            ("vocabulary_historicalgroup", "vocabulary_group", ()),
            ("vocabulary_historicalproject", "vocabulary_project", ()),
            ("vocabulary_historicalreactiontype",
             "vocabulary_reactiontype", ()),
            ("tasks_historicaltask", "tasks_task", ()),
            ("tasks_historicaltaskstep", "tasks_taskstep", ()),
            ("planning_historicalparameters", "planning_parameters", ())}
        self.assertLessEqual(wanted, found)
        self.assertLessEqual(found - wanted, {
            ("registry_historicalsubstanceclass", "registry_substanceclass",
             ())})
        self.assertIn("not in history",
                      self.column("inventory_lot", "amount").notes)
        layout = self.schema.history
        self.assertEqual(
            [c.name for c in layout.columns],
            ["id", "… tracked columns", "history_id", "history_date",
             "history_change_reason", "history_type", "history_user_id"])
        user = by_name(layout.columns, "history_user_id")
        self.assertEqual((user.ref, user.on_delete, user.nullable),
                         ("accounts_user", "SET_NULL", True))
        self.assertEqual(by_name(layout.columns, "history_type").type,
                         "varchar(1)")

    def test_djangos_tables(self) -> None:
        for name in ("auth_group", "auth_permission", "django_session",
                     "django_content_type", "django_admin_log",
                     "accounts_user_groups",
                     "accounts_user_user_permissions"):
            self.assertIn(name, self.schema.framework)
        for name in APP_TABLES | {"inventory_historicalitem"}:
            self.assertNotIn(name, self.schema.framework)
        self.assertEqual(list(self.schema.framework),
                         sorted(self.schema.framework))


class ConstraintTests(unittest.TestCase):
    """Constraints as the page lists them."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.schema = sd.collect()

    def constraint(self, name: str) -> sd.Constraint:
        return by_name(self.schema.constraints, name)

    def test_model_constraints(self) -> None:
        identity = self.constraint("inventory_item_identity")
        self.assertEqual(
            (identity.table, identity.kind, identity.columns),
            ("inventory_item", "unique", ("article_id", "size", "unit")))
        cas = self.constraint("registry_substance_cas_once")
        self.assertEqual((cas.table, cas.kind, cas.columns),
                         ("registry_substance", "unique", ("cas",)))
        self.assertTrue(cas.condition)
        classes = self.constraint("registry_substanceclass_once")
        self.assertEqual(
            (classes.table, classes.kind, classes.columns),
            ("registry_substanceclass", "unique",
             ("substance_id", "chemical_class_id")))
        self.assertEqual(
            self.constraint("inventory_item_size_positive").condition,
            "size > 0")
        self.assertEqual(
            self.constraint("inventory_entered_quarter").condition,
            "quarter >= 1 AND quarter <= 4")
        self.assertEqual(self.constraint("inventory_line_item_once").columns,
                         ("delivery_note_id", "item_id"))
        self.assertEqual(
            self.constraint("inventory_lot_amount_not_negative").condition,
            "amount >= 0")

    def test_positive_checks(self) -> None:
        self.assertIn("inventory_item.quantity", self.schema.positive_checks)
        self.assertNotIn("tasks_task.steps_done",
                         self.schema.positive_checks)
        self.assertNotIn("inventory_item.name", self.schema.positive_checks)

    def test_the_item_identity_has_no_nullable_column(self) -> None:
        self.assertNotIn("inventory_item_identity",
                         [note[0] for note in self.schema.null_notes])

    def test_conditions(self) -> None:
        self.assertEqual(sd.condition_text(Q(size__gt=0) | Q(unit="mg"),
                                           Item),
                         "size > 0 OR unit = 'mg'")
        self.assertEqual(sd.condition_text(~Q(status="active"), Item),
                         "NOT (status = 'active')")
        self.assertEqual(
            sd.condition_text(Q(article_number__isnull=True), Article),
            "article_number IS NULL")
        self.assertEqual(
            sd.condition_text(Q(Q(size__lt=5) | Q(size__gte=10),
                                quantity__lte=3), Item),
            "(size < 5 OR size >= 10) AND quantity <= 3")

    def test_unsupported_condition(self) -> None:
        with self.assertRaises(ValueError) as caught:
            sd.condition_text(Q(name__icontains="x"), Item)
        self.assertIn("icontains", str(caught.exception))


def tbl(name: str, *refs: str, rows: int = 3) -> Table:
    """A table NAME with an id, ROWS - 1 plain columns and one foreign
    key per REFS entry, ``<target>_id`` referencing it."""
    columns = [Column("id", "bigint", key="PK")]
    columns += [Column(f"c{n}", "text") for n in range(1, rows)]
    columns += [Column(f"{ref}_id", "bigint", key="FK", ref=ref,
                       on_delete="PROTECT") for ref in refs]
    return Table(name, "inventory", tuple(columns))


def on_box(point: tuple[float, float], box: sd.Box) -> bool:
    """Whether POINT lies on the outline of BOX."""
    x, y = point
    inside_x = box.left <= x <= box.right
    inside_y = box.top <= y <= box.bottom
    return ((x in (box.left, box.right) and inside_y)
            or (y in (box.top, box.bottom) and inside_x))


class ArrangementTests(unittest.TestCase):
    """Scenarios of "Arrangement"."""

    def test_box_width_fits_the_longest_row(self) -> None:
        long = Table("t", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("a_rather_long_column_name_here", "varchar(100)")))
        wide = sd.arrange([long, tbl("u")], ((("t",), ("u",)),))
        narrow = sd.arrange([tbl("t"), tbl("u")], ((("t",), ("u",)),))
        self.assertGreater(wide.box_width, narrow.box_width)
        self.assertEqual(wide.boxes["t"].right - wide.boxes["t"].left,
                         wide.boxes["u"].right - wide.boxes["u"].left)

    def test_routing_rules(self) -> None:
        """Scenario: Routing rules."""
        tables = [tbl("a", "b", "c", "d", "a"), tbl("b"), tbl("c"),
                  tbl("d", rows=12), tbl("e")]
        drawing = sd.arrange(tables, ((("a",), ("e",), ("d",)),
                                      (("c",), ("b",), None)))
        boxes = drawing.boxes
        a = boxes["a"]
        edges = {e.target: e for e in drawing.edges}

        elbow = edges["b"].points
        self.assertEqual(elbow[0], (a.right, a.row_y("b_id")))
        self.assertEqual(elbow[-1], (boxes["b"].left,
                                     boxes["b"].row_y("id")))
        self.assertTrue(all(a.right < x < boxes["b"].left
                            for x, _ in elbow[1:-1]))

        vertical = edges["c"].points
        self.assertEqual(len(vertical), 2)
        self.assertEqual(vertical[0][0], vertical[1][0])
        self.assertEqual((vertical[0][1], vertical[1][1]),
                         (a.bottom, boxes["c"].top))

        under = edges["d"].points
        self.assertEqual(under[0][1], a.bottom)
        self.assertGreater(under[-2][1], boxes["e"].bottom)
        self.assertEqual(under[-1][0], boxes["d"].left)

        loop = edges["a"].points
        self.assertEqual(loop[0], (a.right, a.row_y("a_id")))
        self.assertEqual(loop[-1][1], a.bottom)
        self.assertTrue(a.left < loop[-1][0] < a.right)

        for edge in drawing.edges:
            self.assertTrue(on_box(edge.points[0], boxes[edge.source]))
            self.assertTrue(on_box(edge.points[-1], boxes[edge.target]))

    def test_lines_in_one_gap_are_spread(self) -> None:
        a = Table("a", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("one_id", "bigint", key="FK", ref="b"),
            Column("two_id", "bigint", key="FK", ref="b")))
        drawing = sd.arrange([a, tbl("b")], ((("a",), ("b",)),))
        xs = {e.points[1][0] for e in drawing.edges}
        self.assertEqual(len(xs), 2)

    def test_ends_labels_and_kinds(self) -> None:
        a = Table("a", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("b_id", "bigint", nullable=True, key="1:1", ref="b",
                   on_delete="CASCADE"),
            Column("u_id", "bigint", key="FK", ref="u",
                   on_delete="PROTECT")))
        drawing = sd.arrange([a, tbl("b"), tbl("u")],
                             ((("a",), ("b",), ("u",)),), hub="u",
                             links=[Link("b", "c1", "u", "c2", "x")])
        edges = {(e.target, e.kind): e for e in drawing.edges}
        self.assertEqual(set(edges), {("b", "key"), ("u", "user"),
                                      ("u", "value")})
        edge = edges["b", "key"]
        self.assertEqual((edge.source_end, edge.target_end, edge.label),
                         ("zero_one", "zero_one", "cascade"))
        self.assertEqual(edges["u", "user"].label, "")

    def test_declared_links(self) -> None:
        tables = [tbl("a"), tbl("b")]
        drawing = sd.arrange(
            tables, ((("a",), ("b",)),),
            links=[Link("a", "c1", "b", "c2", "same", "how it matches")])
        edge = drawing.edges[0]
        self.assertTrue(edge.soft)
        self.assertEqual(edge.kind, "value")
        self.assertEqual(edge.note, "how it matches")
        self.assertEqual(edge.points[0][1], drawing.boxes["a"].row_y("c1"))
        self.assertEqual(edge.points[-1][1], drawing.boxes["b"].row_y("c2"))

    def test_declared_link_to_a_missing_column(self) -> None:
        """Scenario: A declared link to a missing column."""
        with self.assertRaises(LayoutError) as caught:
            sd.arrange([tbl("a"), tbl("b")], ((("a",), ("b",)),),
                       links=[Link("a", "c1", "b", "nope", "x")])
        self.assertIn("b.nope", str(caught.exception))

    def test_refused_arrangements(self) -> None:
        """Scenario: Refused arrangements."""
        cases = [
            ([tbl("a"), tbl("b")], ((("a",), None),), "b"),
            ([tbl("a")], ((("a",), ("zz",)),), "zz"),
            ([tbl("a")], ((("a",), ("a",)),), "a"),
        ]
        for tables, grid, named in cases:
            with self.subTest(named=named, grid=grid):
                with self.assertRaises(LayoutError) as caught:
                    sd.arrange(tables, grid)
                self.assertIn(named, str(caught.exception))

    def assert_clear(self, drawing: sd.Drawing) -> None:
        """Assert that no line of DRAWING crosses a box but its own."""
        for edge in drawing.edges:
            self.assertIsNone(sd.crossing(edge, drawing.boxes),
                              f"{edge.source}.{edge.column}")
            self.assertTrue(on_box(edge.points[0],
                                   drawing.boxes[edge.source]))
            self.assertTrue(on_box(edge.points[-1],
                                   drawing.boxes[edge.target]))

    def test_channel_between_bands(self) -> None:
        """Scenario: Channel between bands."""
        drawing = sd.arrange(
            [tbl("p"), tbl("q"), tbl("r"), tbl("s"), tbl("t", "p")],
            ((("p",), ("q",)), (("r",), ("s",), ("t",))))
        b = drawing.boxes
        points = drawing.edges[0].points
        self.assertEqual(points[0], (b["t"].left, b["t"].row_y("p_id")))
        self.assertEqual(points[-1], (b["p"].right, b["p"].row_y("id")))
        xs = [x for x, _ in points[1:-1]]
        self.assertTrue(all(b["s"].right < x < b["t"].left
                            for x in xs[:2]), points)
        self.assertTrue(all(b["p"].right < x < b["q"].left
                            for x in xs[2:]), points)
        corridor = points[2][1]
        self.assertEqual(corridor, points[3][1])
        self.assertTrue(max(b[n].bottom for n in "pq") < corridor
                        < min(b[n].top for n in "rst"), points)
        self.assert_clear(drawing)

    def test_channel_within_a_column(self) -> None:
        """Scenario: Channel within a column."""
        drawing = sd.arrange(
            [tbl("a", "c"), tbl("b"), tbl("c"), tbl("d")],
            ((("a",), ("d",)), (("b",),), (("c",),)))
        b = drawing.boxes
        points = drawing.edges[0].points
        self.assertEqual(len(points), 4)
        self.assertEqual(points[0], (b["a"].right, b["a"].row_y("c_id")))
        self.assertEqual(points[-1], (b["c"].right, b["c"].row_y("id")))
        self.assertTrue(b["a"].right < points[1][0] < b["d"].left)
        self.assert_clear(drawing)

    def test_delete_rule_on_a_short_channel(self) -> None:
        a = Table("a", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("c_id", "bigint", key="FK", ref="c",
                   on_delete="CASCADE")))
        drawing = sd.arrange([a, tbl("b"), tbl("c"), tbl("d")],
                             ((("a",), ("d",)), (("b",),), (("c",),)))
        edge = drawing.edges[0]
        self.assertEqual(edge.label, "cascade")
        self.assertIsNotNone(edge.label_at)
        self.assertEqual(edge.label_at[0], edge.points[1][0])

    def test_channel_in_place_of_a_crossing_line(self) -> None:
        """Scenario: Channel in place of a crossing line."""
        drawing = sd.arrange(
            [tbl("a", "d"), tbl("s"), tbl("b", rows=12), tbl("d", rows=17)],
            ((("a", "s"), ("b",), ("d",)),))
        edge = drawing.edges[0]
        self.assertEqual(edge.points[0][0], drawing.boxes["a"].right)
        self.assert_clear(drawing)

    def test_lanes_and_room(self) -> None:
        """Scenario: Lanes and room."""
        one = Table("t", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("p_id", "bigint", key="FK", ref="p")))
        two = Table("t", "inventory", (*one.columns,
                                       Column("p2_id", "bigint", key="FK",
                                              ref="p")))
        grid = ((("p",), ("q",)), (("r",), ("s",), ("t",)))
        single = sd.arrange([tbl("p"), tbl("q"), tbl("r"), tbl("s"), one],
                            grid)
        double = sd.arrange([tbl("p"), tbl("q"), tbl("r"), tbl("s"), two],
                            grid)
        heights = sorted(e.points[2][1] for e in double.edges)
        self.assertEqual(heights[1] - heights[0], 10)
        self.assertEqual(double.boxes["r"].top - single.boxes["r"].top, 10)
        for left, right in (("p", "q"), ("s", "t")):
            with self.subTest(gap=left + right):
                self.assertEqual(
                    double.boxes[right].left - double.boxes[left].right,
                    single.boxes[right].left - single.boxes[left].right
                    + 12)

    def test_the_applications_grid(self) -> None:
        schema = sd.collect()
        drawing = sd.arrange([*schema.tables, schema.history], sd.GRID,
                             links=sd.LINKS, hub=sd.HUB)
        self.assertEqual(set(drawing.boxes),
                         APP_TABLES | {schema.history.name})
        self.assert_clear(drawing)


class PageTests(unittest.TestCase):
    """Scenarios of "Page" and "Links between tables"."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.page = sd.generate()
        cls.schema = sd.collect()

    def svg(self) -> str:
        found = re.findall(r"<svg\b.*?</svg>", self.page, re.DOTALL)
        diagrams = [s for s in found if 'class="diagram"' in s[:200]]
        self.assertEqual(len(diagrams), 1)
        return diagrams[0]

    def edges(self) -> list[dict[str, str]]:
        """The lines of the diagram, each as its attributes and body."""
        found = []
        for match in re.finditer(r'<g class="edge([^"]*)"([^>]*)>(.*?)</g>',
                                 self.svg(), re.DOTALL):
            attributes = dict(re.findall(r'data-([a-z-]+)="([^"]*)"',
                                         match.group(2)))
            attributes["class"] = match.group(1).strip()
            attributes["body"] = match.group(3)
            found.append(attributes)
        return found

    def edge(self, source: str, column: str) -> dict[str, str]:
        found = [e for e in self.edges()
                 if e["from"] == source and e["column"] == column]
        self.assertEqual(len(found), 1, f"{source}.{column}")
        return found[0]

    def test_a_standalone_page(self) -> None:
        """Scenario: A standalone page."""
        self.assertTrue(self.page.startswith("<!doctype html>"))
        self.assertIn('<html lang="en">', self.page)
        self.assertIn('<meta charset="utf-8">', self.page)
        self.assertIn("<title>OrgSynDB tables</title>", self.page)
        hosts = set(re.findall(r'(?:href|src)="https?://([^/"]+)',
                               self.page))
        self.assertEqual(hosts, {"fonts.googleapis.com",
                                 "fonts.gstatic.com"})
        self.assertNotRegex(self.page, r"<script[^>]*\bsrc=")
        svg = self.svg()
        for table in self.schema.tables:
            self.assertIn(f'data-table="{table.name}"', svg)
            for column in table.columns:
                self.assertIn(f">{column.name}<", svg)

    def test_no_machine_paths_or_dates(self) -> None:
        self.assertNotIn("/home/", self.page)
        self.assertNotRegex(self.page, r"20\d\d-\d\d-\d\d")

    def test_constraint_lists(self) -> None:
        """Scenario: Constraint lists."""
        text = re.sub(r"<[^>]+>", "", self.page)
        for part in ("inventory_item_identity",
                     "article_id, size, unit",
                     "inventory_item_size_positive", "size &gt; 0",
                     "inventory_entered_quarter",
                     "quarter &gt;= 1 AND quarter &lt;= 4",
                     "registry_substance_cas_once",
                     "registry_substanceclass_once",
                     "substance_id, chemical_class_id",
                     "inventory_historicalitem"):
            self.assertIn(part, text)
        self.assertRegex(text, r"registry_substance_cas_once\s+.*\bcas\b")
        self.assertRegex(text, r"inventory_historicalitem\s+without\s+"
                               r"quantity")

    def test_links_of_an_entered_consumption(self) -> None:
        """Scenario: Links of an entered consumption."""
        item = self.edge("inventory_enteredconsumption", "item_id")
        self.assertEqual((item["to"], item["class"]),
                         ("inventory_item", "kind-key"))
        self.assertIn(">cascade<", item["body"])
        user = self.edge("inventory_enteredconsumption", "entered_by_id")
        self.assertEqual((user["to"], user["class"]),
                         ("accounts_user", "kind-user"))
        row = re.search(r'<g class="row"[^>]*data-column='
                        r'"inventory_enteredconsumption.entered_by_id".*?'
                        r'</g>', self.svg(), re.DOTALL)
        self.assertIsNotNone(row)
        self.assertIn("app-accounts", row.group(0))

    def test_links_to_people(self) -> None:
        """Scenario: Links to people."""
        to_people = [e for e in self.edges() if e["to"] == sd.HUB]
        self.assertEqual(
            sorted((e["from"], e["column"]) for e in to_people),
            sorted([("inventory_deliverynote", "created_by_id"),
                    ("inventory_movement", "user_id"),
                    ("inventory_lotmovement", "user_id"),
                    ("inventory_enteredconsumption", "entered_by_id"),
                    ("tasks_task", "assignee_id"),
                    ("tasks_task", "created_by_id"),
                    (sd.HISTORY, "history_user_id")]))
        self.assertTrue(all(e["class"] == "kind-user" for e in to_people))
        self.assertIn(">set null<",
                      self.edge(sd.HISTORY, "history_user_id")["body"])

    def test_links_of_a_task(self) -> None:
        """Scenario: Links of a task."""
        for source, column, target, target_column in (
                ("tasks_task", "batch", "inventory_lot", "batch"),
                ("tasks_counter", "name", "tasks_task", "number")):
            with self.subTest(column=f"{source}.{column}"):
                edge = self.edge(source, column)
                self.assertEqual(
                    (edge["class"], edge["to"], edge["target-column"]),
                    ("soft kind-value", target, target_column))
                tip = re.search(r"<title>(.*?)</title>", edge["body"],
                                re.DOTALL).group(1)
                note = next(link.note for link in sd.LINKS
                            if (link.source, link.column)
                            == (source, column))
                self.assertTrue(note)
                self.assertEqual(tip.splitlines()[1],
                                 note.replace("'", "&#x27;"))
        self.assertEqual(
            sorted((e["from"], e["column"]) for e in self.edges()
                   if e["class"].endswith("kind-value")),
            [("tasks_counter", "name"), ("tasks_task", "batch")])
        self.assertEqual(
            sorted((link.source, link.column) for link in sd.LINKS),
            [("tasks_counter", "name"), ("tasks_task", "batch")])

    def test_the_declared_batch_link_names_the_substance(self) -> None:
        note = next(link.note for link in sd.LINKS
                    if (link.source, link.column) == ("tasks_task", "batch"))
        self.assertIn("substance", note)
        self.assertNotIn("product", note)

    def test_links_to_the_registry(self) -> None:
        """Scenario: Links to the registry."""
        for source, column, target in (
                ("tasks_task", "substance_id", "registry_substance"),
                ("inventory_lot", "substance_id", "registry_substance"),
                ("inventory_article", "substance_id", "registry_substance"),
                ("inventory_item", "article_id", "inventory_article"),
                ("registry_substance", "group_id", "vocabulary_group"),
                ("registry_substanceclass", "substance_id",
                 "registry_substance"),
                ("registry_substanceclass", "chemical_class_id",
                 "vocabulary_chemicalclass")):
            with self.subTest(column=f"{source}.{column}"):
                edge = self.edge(source, column)
                self.assertEqual((edge["to"], edge["class"]),
                                 (target, "kind-key"))
        row = re.search(r'<g class="row"[^>]*data-column='
                        r'"inventory_article.substance_id".*?</g>',
                        self.svg(), re.DOTALL)
        self.assertIsNotNone(row)
        self.assertIn("app-registry", row.group(0))
        self.assertNotIn("app-vocabulary", row.group(0))

    def test_links_of_the_task_steps(self) -> None:
        """Scenario: Only the application's tables (the links of the new
        table)."""
        for source, column, target in (
                ("tasks_taskstep", "task_id", "tasks_task"),
                ("tasks_taskstep", "entry_id", "collection_scopeentry"),
                ("tasks_taskstep", "planned_import_id", "collection_import"),
                ("tasks_task", "sequence_id", "collection_sequence")):
            with self.subTest(column=f"{source}.{column}"):
                edge = self.edge(source, column)
                self.assertEqual((edge["to"], edge["class"]),
                                 (target, "kind-key"))

    def test_the_new_packages_have_colours_of_their_own(self) -> None:
        colours = sd.COLOURS
        self.assertIn("registry", colours)
        self.assertIn("vocabulary", colours)
        others = [value for app, value in colours.items()
                  if app not in ("registry", "vocabulary")]
        for app in ("registry", "vocabulary"):
            with self.subTest(app=app):
                self.assertNotIn(colours[app], others)
        self.assertNotEqual(colours["registry"], colours["vocabulary"])
        svg = self.svg()
        for name, app in (("registry_substance", "registry"),
                          ("registry_substanceclass", "registry"),
                          ("vocabulary_group", "vocabulary"),
                          ("vocabulary_project", "vocabulary"),
                          ("vocabulary_reactiontype", "vocabulary"),
                          ("vocabulary_chemicalclass", "vocabulary")):
            with self.subTest(table=name):
                box = re.search(rf'<g class="tbl app-{app}[^"]*"[^>]*'
                                rf'data-table="{name}"', svg)
                self.assertIsNotNone(box)

    def test_line_ends(self) -> None:
        """Scenario: Line ends."""
        for source, column, ends in (
                ("inventory_movement", "delivery_note_id", "many zero_one"),
                ("inventory_movement", "bulk_movement_id",
                 "zero_one zero_one"),
                ("inventory_deliveryline", "item_id", "many one")):
            with self.subTest(column=column):
                self.assertEqual(self.edge(source, column)["ends"], ends)

    def test_switches(self) -> None:
        """Scenario: Switches."""
        group = re.search(r'<fieldset class="layers"[^>]*>.*?</fieldset>',
                          self.page, re.DOTALL)
        self.assertIsNotNone(group)
        self.assertIn(" hidden", group.group(0)[:60])
        kinds = [e["class"].split()[-1] for e in self.edges()]
        self.assertEqual(set(kinds), {"kind-key", "kind-user", "kind-value"})
        for kind, checked in (("key", True), ("user", False),
                              ("value", True)):
            with self.subTest(kind=kind):
                box = re.search(rf'<input type="checkbox"[^>]*data-kind='
                                rf'"{kind}"[^>]*>.*?</label>',
                                group.group(0), re.DOTALL)
                self.assertIsNotNone(box)
                self.assertEqual(" checked" in box.group(0).split(">")[0],
                                 checked)
                count = kinds.count(f"kind-{kind}")
                self.assertIn(f'<span class="count">{count}</span>',
                              box.group(0))


class CommandTests(unittest.TestCase):
    """Scenarios of "Diagram command"."""

    def test_writing_and_checking(self) -> None:
        """Scenario: Writing and checking."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docs" / "database-schema.html"
            out = io.StringIO()
            call_command("schema_diagram", "--output", str(path),
                         stdout=out)
            self.assertTrue(path.is_file())
            self.assertIn(str(path), out.getvalue())
            call_command("schema_diagram", "--check", "--output", str(path),
                         stdout=io.StringIO())
            data = bytearray(path.read_bytes())
            data[-2] = ord("x") if data[-2] != ord("x") else ord("y")
            path.write_bytes(bytes(data))
            for _ in range(2):
                with self.assertRaises(CommandError) as caught:
                    call_command("schema_diagram", "--check", "--output",
                                 str(path), stdout=io.StringIO())
                self.assertIn(str(path), str(caught.exception))
                self.assertIn("schema_diagram", str(caught.exception))
                self.assertIn(f"--output {path}", str(caught.exception))
                self.assertEqual(caught.exception.returncode, 1)
                path.unlink(missing_ok=True)

    def test_the_committed_diagram_is_current(self) -> None:
        """Scenario: The committed diagram is current."""
        self.assertEqual(sd.OUTPUT.name, "database-schema.html")
        self.assertEqual(sd.OUTPUT.parent.name, "docs")
        call_command("schema_diagram", "--check", stdout=io.StringIO())
