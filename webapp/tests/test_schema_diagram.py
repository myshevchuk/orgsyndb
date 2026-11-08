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

from inventory.models import Item
from orgsyndb_web import schema_diagram as sd
from orgsyndb_web.schema_diagram import Column, LayoutError, Link, Table

APP_TABLES = {
    "accounts_user", "inventory_item", "inventory_movement",
    "inventory_deliverynote", "inventory_deliveryline", "inventory_lot",
    "inventory_lotmovement", "inventory_enteredconsumption", "tasks_task",
    "tasks_counter", "planning_parameters", "demo_demomark"}


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
            ["id", "inventory", "article_number", "name", "category",
             "size", "unit", "quantity", "note", "status", "stocked_on",
             "compartment", "box"])
        self.assertEqual((item.columns[0].key, item.columns[0].type),
                         ("PK", "bigint"))
        number = self.column("inventory_item", "article_number")
        self.assertEqual((number.type, number.nullable), ("varchar(30)", True))
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
        self.assertEqual(self.column("tasks_task", "sequence_steps").type,
                         "jsonb")

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
        self.assertIsNone(self.column("inventory_item", "name").check)

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

    def test_docstrings(self) -> None:
        item = self.table("inventory_item")
        self.assertTrue(item.about.startswith(
            "An article in one container size"))
        self.assertGreater(len(item.doc), 1)
        self.assertEqual(item.about, item.doc[0])

    def test_history_tables(self) -> None:
        self.assertEqual(
            {(h.name, h.tracked, h.omitted)
             for h in self.schema.history_tables},
            {("inventory_historicalitem", "inventory_item", ("quantity",)),
             ("inventory_historicaldeliverynote", "inventory_deliverynote",
              ()),
             ("inventory_historicallot", "inventory_lot", ("amount",)),
             ("tasks_historicaltask", "tasks_task", ()),
             ("planning_historicalparameters", "planning_parameters", ())})
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
            ("inventory_item", "unique",
             ("inventory", "article_number", "size", "unit")))
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
        self.assertIn("tasks_task.steps_done", self.schema.positive_checks)
        self.assertNotIn("inventory_item.name", self.schema.positive_checks)

    def test_nullable_columns_in_unique_constraints(self) -> None:
        self.assertEqual(
            self.schema.null_notes,
            (("inventory_item_identity", "inventory_item",
              "article_number"),))

    def test_conditions(self) -> None:
        self.assertEqual(sd.condition_text(Q(size__gt=0) | Q(unit="mg"),
                                           Item),
                         "size > 0 OR unit = 'mg'")
        self.assertEqual(sd.condition_text(~Q(status="active"), Item),
                         "NOT (status = 'active')")
        self.assertEqual(
            sd.condition_text(Q(article_number__isnull=True), Item),
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

    def test_ends_and_labels(self) -> None:
        a = Table("a", "inventory", (
            Column("id", "bigint", key="PK"),
            Column("b_id", "bigint", nullable=True, key="1:1", ref="b",
                   on_delete="CASCADE"),
            Column("u_id", "bigint", key="FK", ref="u",
                   on_delete="PROTECT")))
        drawing = sd.arrange([a, tbl("b"), tbl("u")],
                             ((("a",), ("b",), ("u",)),), hub="u")
        self.assertEqual(len(drawing.edges), 1)
        edge = drawing.edges[0]
        self.assertEqual((edge.source_end, edge.target_end, edge.label),
                         ("zero_one", "zero_one", "cascade"))

    def test_declared_links(self) -> None:
        tables = [tbl("a"), tbl("b")]
        drawing = sd.arrange(tables, ((("a",), ("b",)),),
                             links=[Link("a", "c1", "b", "c2", "same")])
        edge = drawing.edges[0]
        self.assertTrue(edge.soft)
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
            ([tbl("a", "c"), tbl("b"), tbl("c")],
             ((("a",),), (("b",),), (("c",),)), "a.c_id"),
            ([tbl("a", "c"), tbl("b"), tbl("c")],
             ((("a",), ("b",), None), (None, None, ("c",))), "a.c_id"),
        ]
        for tables, grid, named in cases:
            with self.subTest(named=named, grid=grid):
                with self.assertRaises(LayoutError) as caught:
                    sd.arrange(tables, grid)
                self.assertIn(named, str(caught.exception))

    def test_a_line_through_a_box_is_refused(self) -> None:
        tables = [tbl("a", "d"), tbl("s"), tbl("b", rows=12),
                  tbl("d", rows=17)]
        with self.assertRaises(LayoutError) as caught:
            sd.arrange(tables, ((("a", "s"), ("b",), ("d",)),))
        self.assertIn("a.d_id", str(caught.exception))
        self.assertTrue(str(caught.exception).endswith(" s"),
                        str(caught.exception))

    def test_the_applications_grid(self) -> None:
        schema = sd.collect()
        drawing = sd.arrange([*schema.tables, schema.history], sd.GRID,
                             links=sd.LINKS, hub=sd.HUB)
        self.assertEqual(set(drawing.boxes),
                         APP_TABLES | {schema.history.name})
        self.assertFalse(any(e.target == sd.HUB for e in drawing.edges))


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
                     "inventory, article_number, size, unit",
                     "inventory_item_size_positive", "size &gt; 0",
                     "inventory_entered_quarter",
                     "quarter &gt;= 1 AND quarter &lt;= 4",
                     "inventory_historicalitem"):
            self.assertIn(part, text)
        self.assertRegex(text, r"article_number\s+is null")
        self.assertRegex(text, r"inventory_historicalitem\s+without\s+"
                               r"quantity")

    def test_links_of_an_entered_consumption(self) -> None:
        """Scenario: Links of an entered consumption."""
        svg = self.svg()
        edge = re.search(
            r'<g class="edge[^"]*" data-from="inventory_enteredconsumption"'
            r' data-to="inventory_item".*?</g>', svg, re.DOTALL)
        self.assertIsNotNone(edge)
        self.assertIn(">cascade<", edge.group(0))
        self.assertNotIn('data-to="accounts_user"', svg)
        row = re.search(r'<g class="row"[^>]*data-column='
                        r'"inventory_enteredconsumption.entered_by_id".*?'
                        r'</g>', svg, re.DOTALL)
        self.assertIsNotNone(row)
        self.assertIn("app-accounts", row.group(0))

    def test_line_ends(self) -> None:
        """Scenario: Line ends."""
        svg = self.svg()
        for source, column, ends in (
                ("inventory_movement", "delivery_note_id", "many zero_one"),
                ("inventory_movement", "bulk_movement_id",
                 "zero_one zero_one"),
                ("inventory_deliveryline", "item_id", "many one")):
            with self.subTest(column=column):
                self.assertRegex(
                    svg, rf'<g class="edge" data-from="{source}" '
                         rf'data-to="[a-z_]+" data-column="{column}" '
                         rf'data-ends="{ends}"')

    def test_declared_links_are_dashed(self) -> None:
        svg = self.svg()
        self.assertRegex(svg, r'<g class="edge soft" data-from='
                              r'"inventory_lot" data-to="inventory_item"')
        self.assertRegex(svg, r'<g class="edge soft" data-from='
                              r'"tasks_counter" data-to="tasks_task"')


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
