## Context

Since `collection-registry` the four compound fields come from the
registry and a collection declares only procedure fields; the demo
declares `notebook` (text, pattern, unique) and `project` (a choice of
the projects). Draft 07 adds `journal_notebook` and `journal_entry`,
`collection_procedure.journal_entry` and `project`, and
`tasks_taskstep.journal_entry`.

## Goals / Non-Goals

**Goals:**

- One meaning of `notebook` and `project` in every collection, checked
  against the application's notebooks and projects.
- Every entry a procedure or a step names is a row, so a notebook page
  shows what each entry holds.

**Non-Goals:**

- Entries' contents: they stay on paper.
- Emacs completion of notebook codes; `project` keeps its completion
  as a choice field.
- Planning by project.

## Decisions

### Journal fields as built-in declarations

The tools already treat declared fields uniformly (validation, export,
field data, index, site). The two journal fields are prepended as
declarations, as `registry_fields` gives the compound fields, so the
site, the export and Emacs need no change. `notebook` keeps the
demo's text type, so an Org value that tomelr unquotes still draws
`must be a string`; its one extra check is the registered code.

### Notebooks in the registry, entries in the journal

A notebook is registry data: the snapshot lists it, inside the digest,
its writes take the lock, and `registry_load` ignores it as it ignores
accounts, which it names. Entries are not in the snapshot: the text
names them by number, and they are created on first use by the
import and by a task step alike with `get_or_create` on the unique
pair of notebook and number, which takes the existing row when another
transaction inserted it first. The lock plays no part in this.
Concurrency is not tested: the test database is SQLite.

### A procedure's entry

No two procedures that are not withdrawn name one entry: the constraint
is conditional, so a withdrawn procedure keeps its entry for history.
The import refuses a manifest whose procedures share an entry, before
any row is written. Applying first withdraws the procedures the
manifest lacks and clears the entries that change, and only then sets
new entries and brings procedures back, so an entry can pass from one
procedure to another, two can swap, and a withdrawn one can return
with its entry once its holder lets it go.

### A step's entry holds the step

Steps are kept by position when a task's sequence changes, so an
entry on a step would follow it to other chemistry. As with a done
step or one that made a lot, a step naming an entry keeps the sequence
from changing and is never removed.

### The pages

Notebook pages live under `/lab/journal/` and are linked from the
registry page beside the vocabularies, so the navigation stays as it
is. A step's entry is set by a small form per step on the task page,
which posts to its own path and leads back with a message.

## Risks / Trade-offs

- [The test server's collection names unregistered notebooks after
  the deploy] → `demo_data --replace` registers the demo's; a lab
  registers its notebooks before its next import.
- [Fixture renames churn many tests] → The fixture's declared fields
  become `sample_code` and `funding`, keeping their types and options,
  so each test changes its keys only.
