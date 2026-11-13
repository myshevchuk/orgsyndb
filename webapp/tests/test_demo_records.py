"""Tests of the records the demo data set holds (lab-demo: Demo accounts,
Demo inventory, Demo tasks and parameters, Recorded past, Language of
the demo texts)."""

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.test import TestCase

from . import BERLIN, DEMO_NOTEBOOKS, frozen, page, table
from .collection_support import accept
from .demo_support import (ACCOUNTS, ARTICLES, DAY, DELIVERIES,
                           DEMO_PASSWORD, ITEMS, LOGIN, NOTE_NUMBER,
                           NUMBERLESS, PLAN, TASKS, SeededCase, noon,
                           opening, run, seed)
from .registry_support import demo_registry

O = opening(DAY)
DEFAULT_PARAMETERS = {"certainty": 0.95, "buffer_days": 28,
                      "default_synthesis_days": 21, "history_quarters": 12,
                      "min_orders": 6, "high_days": 14, "medium_days": 56,
                      "target_days": 365}


def local(moment: datetime) -> datetime:
    return moment.astimezone(BERLIN)


def quarter_of(day) -> tuple[int, int]:
    return day.year, (day.month - 1) // 3 + 1


def quarters_before(quarter: tuple[int, int], count: int
                    ) -> tuple[int, int]:
    year, number = quarter
    index = year * 4 + number - 1 - count
    return index // 4, index % 4 + 1


def history_models() -> list:
    """The historical models of every record that keeps a history."""
    from django.apps import apps
    return [model for model in apps.get_models()
            if model.__name__.startswith("Historical")]


def compound_names() -> dict[str, str]:
    """The German name of each demo substance by its article number."""
    return {entry["article_number"]: entry["name_de"] or entry["name"]
            for entry in demo_registry()["substances"]
            if entry["article_number"]}


def compound_keys() -> dict[str, str]:
    return {entry["article_number"]: entry["key"]
            for entry in demo_registry()["substances"]
            if entry["article_number"]}


class AccountTests(SeededCase):

    def test_accounts(self) -> None:
        from django.contrib.auth import get_user_model
        users = get_user_model().objects
        self.assertEqual(sorted(users.values_list("username", flat=True)),
                         sorted(ACCOUNTS))
        for username, (name, initials) in ACCOUNTS.items():
            with self.subTest(username=username):
                account = users.get(username=username)
                self.assertEqual(account.display_name, name)
                self.assertEqual(account.initials, initials)
        kl = users.get(username="klehmann")
        self.assertTrue(kl.is_superuser and kl.is_staff)
        self.assertEqual(users.filter(is_superuser=True).count(), 1)
        self.assertFalse(users.get(username="mwolf").has_usable_password())

    def test_signing_in(self) -> None:
        """Scenario: Signing in."""
        for username in ("tbauer", "klehmann"):
            with self.subTest(username=username):
                self.assertTrue(self.client.login(
                    username=username, password=DEMO_PASSWORD))
                if username == "klehmann":
                    response = self.client.get("/lab/admin/")
                    self.assertEqual(response.status_code, 200)
                self.client.logout()
        self.assertFalse(self.client.login(username="mwolf",
                                           password=DEMO_PASSWORD))
        response = self.client.post(LOGIN, {"username": "mwolf",
                                            "password": DEMO_PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_every_account_but_mwolf_has_the_password(self) -> None:
        for username in ACCOUNTS:
            with self.subTest(username=username):
                self.assertEqual(
                    self.account(username).check_password(DEMO_PASSWORD),
                    username != "mwolf")

    def test_mwolf_only_on_records_older_than_a_year(self) -> None:
        from inventory.models import (DeliveryNote, EnteredConsumption,
                                      LotMovement, Movement)
        from tasks.models import Task
        mwolf = self.account("mwolf")
        year_ago = noon(DAY) - timedelta(days=365)
        times = [
            *Movement.objects.filter(user=mwolf).values_list(
                "booked_at", flat=True),
            *LotMovement.objects.filter(user=mwolf).values_list(
                "booked_at", flat=True),
            *DeliveryNote.objects.filter(created_by=mwolf).values_list(
                "created_at", flat=True),
            *EnteredConsumption.objects.filter(entered_by=mwolf)
            .values_list("entered_at", flat=True),
            *Task.objects.filter(created_by=mwolf).values_list(
                "created_at", flat=True),
        ]
        for model in history_models():
            if any(f.name == "history_user" for f in model._meta.fields):
                times += model.objects.filter(history_user=mwolf) \
                    .values_list("history_date", flat=True)
        self.assertTrue(times, "no record names mwolf")
        self.assertLess(max(times), year_ago)
        for task in Task.objects.filter(assignee=mwolf):
            with self.subTest(task=task.number):
                self.assertIsNotNone(task.ended)
                self.assertLess(task.ended, year_ago.date())


class RegistryTests(SeededCase):
    """The demo registry, loaded before the lab records (lab-demo: Demo
    data command)."""

    def test_the_registry_is_the_demo_registry(self) -> None:
        from registry import snapshot as registry_snapshot
        from .registry_support import demo_registry, without_digest
        self.assertEqual(
            without_digest(registry_snapshot.build()),
            without_digest(demo_registry()))

    def test_the_registry_file_lists_the_demo_accounts(self) -> None:
        """Requirement: Demo accounts (the registry file lists the five
        accounts, as the snapshot does)."""
        self.assertEqual(
            demo_registry().get("accounts"),
            [{"username": user, "name": ACCOUNTS[user][0]}
             for user in sorted(ACCOUNTS)])

    def test_the_registry_file_lists_the_demo_notebooks(self) -> None:
        """Requirement: Demo notebooks (`webapp/demo/registry.json` lists
        them as the snapshot does)."""
        self.assertEqual(
            demo_registry().get("notebooks"),
            [{"code": code, "user": user}
             for code, user in sorted(DEMO_NOTEBOOKS.items())])

    def test_the_registry_holds_the_substances_of_the_collection(
            self) -> None:
        from registry.models import Substance
        keys = set(Substance.objects.values_list("key", flat=True))
        self.assertEqual(len(keys), 21)
        self.assertLessEqual({"cinnamic-acid", "new-compound-7",
                              NUMBERLESS[1]}, keys)
        self.assertEqual(
            keys, {entry["key"] for entry in demo_registry()["substances"]})

    def test_the_registry_is_klehmanns_first_change_on_the_opening_day(
            self) -> None:
        from inventory.models import Article, Item
        from registry.models import Substance
        from vocabulary.models import (ChemicalClass, Group, Project,
                                       ReactionType)
        klehmann = self.account("klehmann")
        created = []
        records = [
            *Substance.objects.all(),
            *Article.objects.exclude(article_number__isnull=True),
            *(term for model in (ChemicalClass, Group, Project,
                                 ReactionType)
              for term in model.objects.all())]
        for record in records:
            first = record.history.order_by("history_id").first()
            with self.subTest(record=str(record)):
                self.assertEqual(first.history_type, "+")
                self.assertEqual(first.history_user, klehmann)
                self.assertEqual(local(first.history_date).date(), O)
            created.append(first.history_date)
        self.assertTrue(created)
        opened = [first.history_date for first in (
            record.history.order_by("history_id").first()
            for record in Item.objects.all())]
        self.assertLess(max(created), min(opened))

    def test_the_articles_with_numbers_come_with_the_registry(self) -> None:
        from inventory.models import Article
        for article in Article.objects.exclude(article_number__isnull=True):
            first = article.history.order_by("history_id").first()
            with self.subTest(article=article.article_number):
                self.assertEqual(first.article_number,
                                 article.article_number)


class AuthorTests(SeededCase):
    """The procedures of the demo import credit the demo accounts
    (sample-procedures: Sample marking)."""

    def test_each_procedure_credits_its_demo_accounts(self) -> None:
        from .collection_support import DEMO_CREDITS, authors_of
        for key, users in DEMO_CREDITS.items():
            with self.subTest(procedure=key):
                self.assertEqual(authors_of(key), users)

    def test_the_authors_are_the_demo_accounts(self) -> None:
        from .collection_support import author_rows
        rows = author_rows()
        self.assertTrue(rows)
        self.assertEqual({user for _, user, _ in rows}, set(ACCOUNTS))


class NotebookTests(SeededCase):
    """The demo's notebooks (lab-demo: Demo notebooks)."""

    def test_notebooks_of_the_demo(self) -> None:
        """Scenario: Notebooks of the demo."""
        from journal.models import Entry
        from registry import snapshot as registry_snapshot
        listed = registry_snapshot.build()["notebooks"]
        self.assertEqual(listed, demo_registry()["notebooks"])
        self.assertEqual(
            {n["code"]: n["user"] for n in listed}, DEMO_NOTEBOOKS)
        numbers = {code: sorted(Entry.objects.filter(
            notebook__code=code).values_list("number", flat=True))
            for code in DEMO_NOTEBOOKS}
        self.assertEqual(numbers["CE-3"], [1, 2])
        entry = Entry.objects.get(notebook__code="CE-3", number=1)
        self.assertEqual([p.key for p in entry.procedures.all()],
                         ["OSDB-0009"])
        self.assertEqual(
            [(s.task.number, s.position) for s in
             Entry.objects.get(notebook__code="CE-3", number=2)
             .task_steps.select_related("task")],
            [(self.running().number, 1)])

    def running(self):
        from tasks.models import Task
        return Task.objects.get(sequence__key="SEQ-0002",
                                started__isnull=False,
                                ended__isnull=True)

    def test_the_notebooks_have_no_note(self) -> None:
        """Requirement: Demo notebooks (with no note)."""
        from journal.models import Notebook
        self.assertEqual(Notebook.objects.count(), 4)
        for notebook in Notebook.objects.all():
            with self.subTest(code=notebook.code):
                self.assertEqual(notebook.note, "")

    def test_the_notebooks_are_made_by_klehmann_on_the_opening_day(
            self) -> None:
        """Requirement: Demo notebooks (on `O` and made by
        `klehmann`)."""
        from journal.models import Notebook
        klehmann = self.account("klehmann")
        for notebook in Notebook.objects.all():
            first = notebook.history.order_by("history_id").first()
            with self.subTest(code=notebook.code):
                self.assertEqual(first.history_type, "+")
                self.assertEqual(first.history_user, klehmann)
                self.assertEqual(local(first.history_date).date(), O)

    def test_every_procedure_names_its_entry_and_its_project(self) -> None:
        """Requirement: Demo notebooks (the data set's import gives the
        procedures the entries their `notebook` names)."""
        from .collection_support import DEMO_JOURNAL, journal_of
        self.assertEqual({key: journal_of(key) for key in DEMO_JOURNAL},
                         DEMO_JOURNAL)

    def test_only_the_named_entries_exist(self) -> None:
        """Requirement: Notebooks and entries (nothing but an import or a
        task step creates an entry): nine of the procedures and one of
        the step."""
        from journal.models import Entry
        self.assertEqual(Entry.objects.count(), 10)

    def test_the_done_step_names_the_entry(self) -> None:
        """Requirement: Demo notebooks (the done first step of the
        running task of `SEQ-0002` names the entry `CE-3/2`)."""
        from tasks.models import TaskStep
        step = TaskStep.objects.get(task=self.running(), position=1)
        self.assertIsNotNone(step.done_on)
        self.assertEqual(str(step.journal_entry), "CE-3/2")
        others = TaskStep.objects.exclude(pk=step.pk).filter(
            journal_entry__isnull=False)
        self.assertEqual(others.count(), 0)


class InventoryTests(SeededCase):

    def test_item_list(self) -> None:
        """Scenario: Item list."""
        from inventory.models import Item
        header, rows = table(self.get(ITEMS))
        numbered = [row for row in rows if row[header[0]].text()]
        self.assertEqual({row[header[0]].text() for row in numbered},
                         set(ARTICLES))
        bare = [index for index, row in enumerate(rows)
                if not row[header[0]].text()]
        self.assertEqual(len(bare), 1)
        last = rows[bare[0]]
        category = [index for index, row in enumerate(rows)
                    if row["Kategorie"].text() == last["Kategorie"].text()]
        self.assertEqual(bare[0], category[-1])
        self.assertGreater(len(category), 1)
        self.assertEqual(last[header[1]].text().removesuffix("neu"),
                         NUMBERLESS[0])
        item = Item.objects.get(article__article_number__isnull=True)
        self.assertEqual(last[header[1]].find("a").get("href"),
                         f"/lab/inventory/items/{item.pk}/")
        keys = compound_keys()
        for row in numbered:
            article = row[header[0]].text()
            name = row[header[1]]
            with self.subTest(article=article):
                link = name.find("a")
                self.assertIsNotNone(link)
                self.assertEqual(link.get("href"),
                                 f"/lab/registry/substances/"
                                 f"{keys[article]}/")
                if article == "NV-0007":
                    self.assertEqual(name.text(), "Neuverbindung 7")

    def test_new_positions(self) -> None:
        """Scenario: New positions."""
        from inventory.models import Item
        header, rows = table(self.get(ITEMS))
        marked = {(row[header[1]].text().removesuffix("neu"),
                   row[header[3]].text())
                  for row in rows if row[header[1]].find("sup", "mark-new")}
        self.assertEqual(marked, {(NUMBERLESS[0], "100 mg"),
                                  ("Dibenzylidenaceton", "1 g")})
        size = next(row for row in rows
                    if row[header[0]].text() == "CH-0013"
                    and row[header[3]].text() == "1 g")
        self.assertIn("projected", size["Ø Jahr"].classes)
        self.assertTrue(Item.objects.filter(status="discontinued").exists())

    def test_sizes_set_aside(self) -> None:
        from inventory.models import Item
        aside = {(item.article.article_number, str(item.container),
                  item.status)
                 for item in Item.objects.exclude(status="active")}
        self.assertEqual(aside, {("CH-0012", "1 g", "discontinued"),
                                 ("CH-0010", "25 g", "not_needed")})
        for item in Item.objects.exclude(status="active"):
            with self.subTest(item=str(item)):
                self.assertFalse(item.delivery_lines.exists())
                changes = [record.diff_against(record.prev_record)
                           .changed_fields for record in item.history.all()
                           if record.prev_record is not None]
                self.assertIn(["status"], changes)

    def test_locations(self) -> None:
        from inventory.models import Item
        places: dict = defaultdict(set)
        for item in Item.objects.all():
            with self.subTest(item=str(item)):
                self.assertRegex(item.compartment, r"^[0-9]+$")
                self.assertRegex(item.box, r"^[0-9]+$")
            places[item.article_id].add(item.compartment)
        self.assertTrue(Item.objects.filter(
            article__article_number__isnull=True).exclude(
                compartment="").exists())
        for article, compartments in places.items():
            with self.subTest(article=article):
                self.assertEqual(len(compartments), 1)

    def test_items_are_named_as_their_substances(self) -> None:
        from inventory.models import Item
        names = compound_names()
        for item in Item.objects.exclude(
                article__article_number="NV-0007").exclude(
                    article__article_number__isnull=True):
            substance = item.article.substance
            with self.subTest(item=str(item)):
                self.assertEqual(substance.name_de,
                                 names[item.article.article_number])
        self.assertEqual(
            [item.article.substance.key for item in Item.objects.filter(
                article__article_number__isnull=True)], [NUMBERLESS[1]])
        for item in Item.objects.filter(article__article_number="NV-0007"):
            self.assertEqual(item.article.substance.key, "new-compound-7")
            self.assertEqual(item.article.substance.name, "New compound 7")
            self.assertEqual(item.article.substance.name_de,
                             "Neuverbindung 7")

    def test_every_article_is_one_substance_of_the_registry(self) -> None:
        from inventory.models import Article
        from registry.models import Substance
        numbered = Article.objects.exclude(article_number__isnull=True)
        self.assertEqual(
            {article.article_number for article in numbered},
            set(ARTICLES))
        self.assertEqual(Article.objects.count(), len(ARTICLES) + 1)
        for article in Article.objects.all():
            self.assertTrue(Substance.objects.filter(
                pk=article.pk).exists())

    def test_sizes_and_units(self) -> None:
        from inventory.models import Item
        sizes = defaultdict(int)
        for item in Item.objects.all():
            sizes[item.article_id] += 1
        self.assertGreaterEqual(max(sizes.values()), 3)
        self.assertLessEqual({"mg", "g", "umol"},
                             set(Item.objects.values_list("unit",
                                                          flat=True)))

    def test_opening_counts(self) -> None:
        from inventory.models import Item, Movement
        opened_on_o = 0
        for item in Item.objects.all():
            first = item.movements.order_by("id").first()
            with self.subTest(item=str(item)):
                self.assertEqual(first.kind, Movement.Kind.OPENING)
                self.assertGreaterEqual(first.date, O)
            opened_on_o += first.date == O
        self.assertGreater(opened_on_o, 0)

    def test_entered_consumption(self) -> None:
        from inventory.models import EnteredConsumption
        wanted = {quarters_before(quarter_of(O), count)
                  for count in range(2, 9)}
        by_item = defaultdict(set)
        for row in EnteredConsumption.objects.all():
            by_item[row.item_id].add((row.year, row.quarter))
            with self.subTest(row=str(row)):
                self.assertGreaterEqual(local(row.entered_at).date(), O)
                self.assertLessEqual(local(row.entered_at).date(),
                                     O + timedelta(days=30))
        self.assertTrue(by_item)
        from inventory.models import Item
        early = {quarters_before(quarter_of(O), count)
                 for count in range(5, 9)}
        dormant = Item.objects.get(article__article_number="CH-0001",
                                   size=250)
        for item, quarters in by_item.items():
            with self.subTest(item=item):
                self.assertEqual(quarters, early if item == dormant.pk
                                 else wanted)

    def test_historical_notes(self) -> None:
        from inventory.models import DeliveryNote
        year, quarter = quarters_before(quarter_of(O), 1)
        first = date(year, 3 * quarter - 2, 1)
        notes = DeliveryNote.objects.filter(historical=True)
        self.assertTrue(notes.exists())
        opening_quarter = date(O.year, (O.month - 1) // 3 * 3 + 1, 1)
        self.assertTrue(notes.filter(date__lt=opening_quarter).exists())
        for note in notes:
            with self.subTest(note=str(note)):
                self.assertGreaterEqual(note.date, first)
                self.assertLess(note.date, O)
                made = local(note.created_at).date()
                self.assertGreaterEqual(made, O)
                self.assertLessEqual(made, O + timedelta(days=30))
        reversed_notes = notes.filter(reversed=True)
        self.assertEqual(reversed_notes.count(), 1)
        self.assertTrue(reversed_notes.get().reversal_note.strip())

    def test_current_notes(self) -> None:
        from inventory.models import DeliveryNote
        notes = DeliveryNote.objects.filter(historical=False)
        self.assertTrue(notes.exists())
        self.assertTrue(any(note.lines.count() > 1 for note in notes))
        for note in notes:
            with self.subTest(note=str(note)):
                self.assertGreaterEqual(note.date, O)
                self.assertLessEqual(note.date, DAY)
                self.assertTrue(note.recipient.strip())

    def test_note_numbers(self) -> None:
        from inventory.models import DeliveryNote
        by_year = defaultdict(list)
        for note in DeliveryNote.objects.all():
            match = NOTE_NUMBER.match(note.number or "")
            with self.subTest(note=note.pk):
                self.assertIsNotNone(match, note.number)
                self.assertEqual(int(match.group(1)), note.date.year)
            by_year[note.date.year].append((int(match.group(2)), note.date))
        for year, numbered in by_year.items():
            numbered.sort()
            with self.subTest(year=year):
                self.assertEqual([n for n, _ in numbered],
                                 list(range(1, len(numbered) + 1)))
                dates = [day for _, day in numbered]
                self.assertEqual(dates, sorted(dates))

    def test_reversal_and_correction(self) -> None:
        from inventory.models import Movement
        reversals = Movement.objects.filter(
            kind=Movement.Kind.REVERSAL,
            reverses__kind=Movement.Kind.DELIVERY)
        self.assertEqual(reversals.count(), 1)
        self.assertTrue(reversals.get().note.strip())
        corrections = Movement.objects.filter(kind=Movement.Kind.CORRECTION)
        self.assertEqual(corrections.count(), 1)
        self.assertTrue(corrections.get().note.strip())

    def test_lots(self) -> None:
        from inventory.models import Lot, LotMovement, Movement
        lots = Lot.objects.all()
        self.assertTrue(lots.exists())
        for lot in lots:
            with self.subTest(lot=str(lot)):
                self.assertTrue(lot.batch and lot.location and lot.made_on)
        fillings = Movement.objects.filter(kind=Movement.Kind.FILLING)
        self.assertTrue(fillings.exists())
        for filling in fillings:
            with self.subTest(filling=filling.pk):
                if filling.item.article.article_number is None:
                    self.assertIsNone(filling.bulk_movement)
                    continue
                self.assertIsNotNone(filling.bulk_movement)
                self.assertEqual(filling.bulk_movement.lot.substance,
                                 filling.item.article.substance)
        self.assertTrue(fillings.filter(
            item__article__article_number__isnull=True).exists())
        self.assertGreaterEqual(lots.filter(amount=0).count(), 1)
        corrected = LotMovement.objects.filter(
            kind=LotMovement.Kind.CORRECTION)
        self.assertEqual(corrected.count(), 1)
        self.assertTrue(corrected.get().note.strip())
        self.assertTrue(lots.filter(substance__key="new-compound-7",
                                    unit="umol").exists())

    def test_bought_and_intermediate_lots(self) -> None:
        from inventory.models import Article, Lot
        bought = Lot.objects.filter(source="bought")
        self.assertTrue(bought.exists())
        self.assertTrue(all(lot.supplier.strip() for lot in bought))
        self.assertTrue(Lot.objects.filter(source="made").exists())
        intermediate = [
            lot for lot in Lot.objects.filter(source="made", amount__gt=0)
            if not Article.objects.filter(pk=lot.substance_id).exists()]
        self.assertTrue(intermediate)

    def test_notes(self) -> None:
        """Scenario: Notes."""
        root = self.get(DELIVERIES)
        header, rows = table(root)
        numbers = [row[header[0]] for row in rows]
        self.assertTrue(numbers)
        texts = [cell.text() for cell in numbers]
        self.assertTrue(all(NOTE_NUMBER.match(text.split()[0])
                            for text in texts), texts)
        historical = [text for text in texts if "nachgetragen" in text]
        self.assertTrue(historical)
        self.assertEqual(sum("storniert" in text and "teilweise" not in text
                             for text in historical), 1)
        current = [text for text in texts if "nachgetragen" not in text]
        self.assertTrue(any("storniert" in text for text in current))


class TaskTests(SeededCase):

    def counts(self) -> tuple[int, int, int]:
        line = self.get(TASKS).find("p", cls="count").text()
        found = re.fullmatch(
            r"(\d+) geplant · (\d+) in Arbeit · (\d+) Nacharbeit", line)
        self.assertIsNotNone(found, line)
        return tuple(int(group) for group in found.groups())

    def test_task_list(self) -> None:
        """Scenario: Task list."""
        planned, running, followup = self.counts()
        self.assertGreaterEqual(planned, 2)
        self.assertGreaterEqual(running, 3)
        self.assertGreaterEqual(followup, 2)
        text = self.get(TASKS + "?state=all").text()
        for state in ("Geplant", "In Arbeit", "Abgeschlossen", "Verworfen"):
            with self.subTest(state=state):
                self.assertIn(state, text)

    def test_states(self) -> None:
        from tasks.models import State, Task
        tasks = list(Task.objects.all())
        states = {task.state for task in tasks}
        self.assertEqual(states, set(State.values))
        self.assertTrue(any(task.state == State.ENDED and task.report
                            and task.qc_list for task in tasks))

    def test_every_task_is_valid(self) -> None:
        from tasks.models import Task
        for task in Task.objects.all():
            with self.subTest(task=task.number):
                task.full_clean()

    def test_synthesis_time_of_ch_0012(self) -> None:
        from tasks.models import State, Task
        ended = [task for task in Task.objects.all()
                 if task.state == State.ENDED
                 and task.substance.key == "cinnamic-acid"]
        self.assertGreaterEqual(len(ended), 3)
        header, rows = table(self.get(PLAN))
        row = next(row for row in rows if row[header[0]].text() == "CH-0012")
        self.assertIn("längste der letzten 3 Synthesen",
                      row["Synthesedauer"].text())

    def test_sequences(self) -> None:
        """Requirement: Demo tasks and parameters (tasks of `SEQ-0001`
        and `SEQ-0002` of the data set's import, one step per step of
        the sequence)."""
        from collection.models import Import, Sequence
        from tasks.models import State, Task
        own = Import.objects.get()
        products = {"SEQ-0001": "acetylsalicylic-acid",
                    "SEQ-0002": "1-biphenyl-4-yl-ethanol"}
        for key, product in products.items():
            sequence = Sequence.objects.get(key=key)
            wanted = [step.entry for step in sequence.steps.order_by(
                "position")]
            self.assertEqual(len(wanted), 2)
            tasks = Task.objects.filter(sequence=sequence)
            with self.subTest(sequence=key):
                self.assertTrue(tasks.exists())
                for task in tasks:
                    self.assertEqual(task.substance.key, product)
                    steps = list(task.steps.order_by("position"))
                    self.assertEqual([s.position for s in steps], [1, 2])
                    self.assertEqual([s.entry for s in steps], wanted)
                    self.assertEqual({s.planned_import for s in steps},
                                     {own})
        self.assertTrue(any(
            task.state == State.RUNNING and [
                step.done_on is not None
                for step in task.steps.order_by("position")]
            == [True, False]
            for task in Task.objects.exclude(sequence=None)))

    def test_the_steps_of_a_sequence_task_name_the_demo_entries(
            self) -> None:
        """Requirement: Demo tasks and parameters (entry 1 of
        `OSDB-0009` for the second step of `SEQ-0002`)."""
        from tasks.models import Task
        task = Task.objects.filter(sequence__key="SEQ-0002").first()
        self.assertEqual(
            [(step.entry.procedure.key, step.entry.position)
             for step in task.steps.order_by("position")],
            [("OSDB-0004", 1), ("OSDB-0009", 1)])

    def test_every_task_names_a_substance_of_the_registry(self) -> None:
        from registry.models import Substance
        from tasks.models import Task
        for task in Task.objects.all():
            with self.subTest(task=task.number):
                self.assertTrue(Substance.objects.filter(
                    pk=task.substance_id).exists())

    def test_a_substance_task_and_no_assignee(self) -> None:
        from tasks.models import Task
        self.assertTrue(Task.objects.filter(
            substance__key="cinnamic-acid").exists())
        self.assertTrue(Task.objects.filter(assignee=None).exists())

    def test_the_position_without_a_number_has_its_task(self) -> None:
        """Requirement: Demo tasks and parameters (an ended task of
        `1-phenylethanol` with a batch and its product lot)."""
        from planning.plan import batch_lots
        from tasks.models import State, Task
        tasks = list(Task.objects.filter(substance__key=NUMBERLESS[1]))
        self.assertTrue(tasks)
        ended = [task for task in tasks if task.state == State.ENDED]
        self.assertTrue(ended)
        for task in ended:
            with self.subTest(task=task.number):
                self.assertTrue(task.batch)
                self.assertTrue(batch_lots(task))

    def test_batches_link_tasks_and_lots(self) -> None:
        from inventory.models import Lot
        from planning.plan import batch_lots, batch_tasks
        from tasks.models import State, Task
        batched = [task for task in Task.objects.exclude(batch="")
                   if task.state == State.ENDED]
        self.assertTrue(batched)
        for task in batched:
            with self.subTest(task=task.number):
                self.assertTrue(batch_lots(task))
        for lot in Lot.objects.all():
            with self.subTest(lot=str(lot)):
                self.assertTrue(batch_tasks(lot))

    def test_ended_tasks_have_their_lots(self) -> None:
        """Scenario: Ended tasks have their lots (every ended task that
        has not failed has a batch and a product lot)."""
        from inventory.models import Lot
        from planning.plan import batch_lots
        from tasks.models import State, Task
        ended = [task for task in Task.objects.all()
                 if task.state == State.ENDED]
        self.assertTrue(ended)
        for task in ended:
            with self.subTest(task=task.number):
                self.assertTrue(task.batch)
                self.assertFalse(task.failed)
                product = Lot.objects.filter(
                    source="made", substance=task.substance,
                    batch=task.batch)
                self.assertTrue(product.exists())
                self.assertTrue(set(product) <= set(batch_lots(task)))

    def test_one_task_failed(self) -> None:
        """Scenario: Ended tasks have their lots (one task is failed and
        has no batch)."""
        from tasks.models import State, Task
        failed = Task.objects.filter(failed=True)
        self.assertEqual(failed.count(), 1)
        task = failed.get()
        self.assertEqual(task.state, State.FAILED)
        self.assertEqual(task.batch, "")
        self.assertIsNotNone(task.ended)
        self.assertFalse(task.needs_follow_up)
        self.assertIn("Fehlgeschlagen",
                      self.get(f"/lab/tasks/{task.number}/").text())

    def test_a_step_made_a_lot_withdrawn_in_part_into_the_next(
            self) -> None:
        """Scenario: Ended tasks have their lots (one lot was made by a
        task step and has a withdrawal into another step of the same
        task); Requirement: Demo tasks and parameters (a running task of
        a sequence with the first step done, which made a lot of its
        intermediate, withdrawn in part into the second)."""
        from inventory.models import Lot, LotMovement
        from tasks.models import State, Task
        made = list(Lot.objects.exclude(task_step=None))
        self.assertTrue(made)
        withdrawn = [
            lot for lot in made
            if lot.movements.filter(
                kind=LotMovement.Kind.WITHDRAWAL,
                task_step__task=lot.task_step.task).exclude(
                    task_step=lot.task_step).exists()]
        self.assertTrue(withdrawn)
        found = []
        for lot in withdrawn:
            task = lot.task_step.task
            first, second = task.steps.order_by("position")
            if (task.state == State.RUNNING and task.sequence is not None
                    and lot.task_step == first and first.done_on
                    and second.done_on is None):
                found.append((lot, task, first, second))
        self.assertTrue(found)
        for lot, task, first, second in found:
            with self.subTest(lot=str(lot)):
                self.assertEqual(lot.source, "made")
                self.assertTrue(first.entry.substances.filter(
                    role="product", substance=lot.substance).exists())
                taken = lot.movements.get(
                    kind=LotMovement.Kind.WITHDRAWAL)
                self.assertEqual(taken.task_step, second)
                self.assertGreater(lot.amount, 0)
                self.assertLess(
                    lot.amount,
                    lot.movements.get(kind=LotMovement.Kind.OPENING)
                    .amount)
                self.assertEqual(
                    lot.amount, taken.amount_after)
                text = self.get(f"/lab/inventory/bulk/{lot.pk}/").text()
                self.assertIn(task.number, text)

    def test_numbers_follow_creation(self) -> None:
        from tasks.models import Task
        tasks = sorted(Task.objects.all(), key=lambda task: task.serial)
        self.assertEqual(tasks[0].number, "T-001")
        self.assertEqual([task.serial for task in tasks],
                         list(range(1, len(tasks) + 1)))
        created = [task.created_at for task in tasks]
        self.assertEqual(created, sorted(created))

    def test_parameters_with_a_history(self) -> None:
        """Scenario: Parameters with a history."""
        from planning.models import Parameters
        stored = Parameters.objects.get()
        for name, value in DEFAULT_PARAMETERS.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(stored, name), value)
        records = list(stored.history.order_by("history_id"))
        self.assertEqual([record.target_days for record in records][:1],
                         [180])
        self.assertEqual(records[-1].target_days, 365)
        self.assertLess(local(records[0].history_date).date(),
                        DAY - timedelta(days=365))


class RecordedPastTests(SeededCase):

    def test_item_history(self) -> None:
        """Scenario: Item history."""
        from inventory.models import Item, Movement
        item = next(item for item in Item.objects.all()
                    if item.movements.order_by("id").first().date == O)
        movements = list(item.movements.order_by("-id"))
        self.assertEqual(movements[-1].kind, Movement.Kind.OPENING)
        self.assertEqual(movements[-1].date, O)
        dates = [movement.date for movement in movements]
        self.assertEqual(dates, sorted(dates, reverse=True))
        created = item.history.order_by("history_id").first()
        self.assertEqual(created.history_type, "+")
        self.assertEqual(local(created.history_date).date(), O)

    def test_item_page_shows_the_opening_first(self) -> None:
        from inventory.models import Item
        item = next(item for item in Item.objects.all()
                    if item.movements.order_by("id").first().date == O)
        text = self.get(f"/lab/inventory/items/{item.pk}/").text()
        self.assertIn(O.strftime("%d.%m.%Y"), text)

    def test_task_history(self) -> None:
        """Scenario: Task history."""
        from tasks.models import State, Task
        task = next(task for task in Task.objects.all()
                    if task.state == State.RUNNING
                    and task.substance.key == "cinnamic-acid")
        records = list(task.history.order_by("history_id"))
        self.assertEqual(records[0].history_type, "+")
        self.assertIsNone(records[0].started)
        start = next(record for record in records if record.started)
        self.assertLess(records[0].history_date, start.history_date)
        self.assertEqual(local(start.history_date).date(), task.started)

    def test_times_within_the_inventory_life(self) -> None:
        """Scenario: Times within the inventory's life."""
        from inventory.models import (DeliveryNote, EnteredConsumption,
                                      LotMovement, Movement)
        from tasks.models import Task
        first = datetime.combine(O, time(8), BERLIN)
        last = datetime.combine(DAY, time(18), BERLIN)
        stamps = [
            *Movement.objects.values_list("booked_at", flat=True),
            *LotMovement.objects.values_list("booked_at", flat=True),
            *DeliveryNote.objects.values_list("created_at", flat=True),
            *Task.objects.values_list("created_at", flat=True),
            *EnteredConsumption.objects.values_list("entered_at",
                                                    flat=True),
        ]
        for model in history_models():
            stamps += model.objects.values_list("history_date", flat=True)
        self.assertTrue(stamps)
        for stamp in stamps:
            moment = local(stamp)
            with self.subTest(moment=moment.isoformat()):
                self.assertGreaterEqual(moment, first)
                self.assertLessEqual(moment, last)
                self.assertGreaterEqual(moment.time(), time(8))
                self.assertLessEqual(moment.time(), time(18))
        for movement in Movement.objects.all():
            self.assertLessEqual(movement.date, DAY)
            self.assertEqual(movement.date, local(movement.booked_at).date())
        for task in Task.objects.all():
            for day in (task.started, task.ended):
                if day is not None:
                    self.assertLessEqual(day, DAY)

    def test_movements_were_booked_in_order(self) -> None:
        from inventory.models import LotMovement, Movement
        for model in (Movement, LotMovement):
            with self.subTest(model=model.__name__):
                booked = list(model.objects.order_by("id").values_list(
                    "booked_at", flat=True))
                self.assertEqual(booked, sorted(booked))

    def test_history_names_its_user(self) -> None:
        for model in history_models():
            if not any(f.name == "history_user" for f in model._meta.fields):
                continue
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.filter(
                    history_user=None).exists())


class LanguageTests(TestCase):

    def replace_after(self, language: str) -> None:
        """Write the data set, accept an import of ``language`` and
        write the data set again with ``--replace``."""
        seed(DAY)
        accept(language=language)
        with frozen(noon(DAY)):
            run("--replace")

    def names(self) -> dict[str, str]:
        header, rows = table(page(self.client.get(ITEMS)))
        return {row[header[0]].text(): row[header[1]].text()
                for row in rows if row[header[0]].text()}

    def test_english_collection(self) -> None:
        """Scenario: English collection."""
        self.replace_after("en")
        names = self.names()
        self.assertEqual(names["NV-0007"], "New compound 7")
        self.assertEqual(names["CH-0012"], "(E)-Cinnamic acid")

    def test_a_german_collection_names_the_items_in_german(self) -> None:
        """Requirement: Language of the demo texts (German)."""
        self.replace_after("de")
        names = self.names()
        self.assertEqual(names["NV-0007"], "Neuverbindung 7")
        self.assertEqual(names["CH-0012"], "(E)-Zimtsäure")

    def test_an_empty_database_is_written_in_german(self) -> None:
        """Requirement: Language of the demo texts (German when it
        holds no import)."""
        seed(DAY)
        self.assertEqual(self.names()["NV-0007"], "Neuverbindung 7")

    def test_the_language_is_the_latest_import_before_deleting(
            self) -> None:
        """Requirement: Language of the demo texts (the latest accepted
        import the database holds before the command deletes
        anything)."""
        seed(DAY)
        accept(language="en")
        accept(language="de")
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(self.names()["NV-0007"], "Neuverbindung 7")
        accept(language="de")
        accept(language="en")
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(self.names()["NV-0007"], "New compound 7")

    def test_the_substances_have_names_in_both_languages(self) -> None:
        from registry.models import Substance
        seed(DAY)
        for key, english, german in (
                ("new-compound-7", "New compound 7", "Neuverbindung 7"),
                ("cinnamic-acid", "(E)-Cinnamic acid", "(E)-Zimtsäure")):
            with self.subTest(key=key):
                found = Substance.objects.get(key=key)
                self.assertEqual((found.name, found.name_de),
                                 (english, german))

    def test_same_records_whatever_the_language(self) -> None:
        """Scenario: Same records whatever the language."""
        seed(DAY)
        german = snapshot()
        accept(language="en")
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(snapshot(), german)


def snapshot() -> dict:
    """The records that must not depend on the language, without their
    IDs."""
    from inventory.models import Item, Lot, Movement
    from registry.models import Substance
    from tasks.models import Task
    return {
        "substances": sorted(Substance.objects.values_list("key", "name")),
        "items": sorted(Item.objects.values_list(
            "article__article_number", "size", "unit", "quantity"),
            key=repr),
        "movements": sorted(Movement.objects.values_list(
            "item__article__article_number", "item__size", "item__unit",
            "kind", "count", "date"), key=repr),
        "lots": sorted(Lot.objects.values_list("batch", "amount")),
        "tasks": sorted(Task.objects.values_list(
            "number", "substance__key", "started", "ended")),
    }


class DemoRegistryNamesTests(TestCase):

    def test_the_demo_registry_names_the_substances(self) -> None:
        names = compound_names()
        for article in ARTICLES:
            with self.subTest(article=article):
                self.assertIn(article, names)
        self.assertEqual(names["NV-0007"], "Neuverbindung 7")
        self.assertNotIn("CH-0003", names)
