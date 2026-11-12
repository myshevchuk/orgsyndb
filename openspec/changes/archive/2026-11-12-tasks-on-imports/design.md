## Context

`tasks.Task` holds `sequence` (ID text), `sequence_steps` (a JSON list
of procedure IDs), `steps_total` and `steps_done`. The form reads the
steps from `orgsyndb_web.index.sequence_for` when the sequence is set
or changed; the page links each step's procedure when
`procedure_for` finds it; the `step` and `end` actions move
`steps_done`. `orgsyndb_web.index` also gives the interface language
(middleware, demo data) and `has_compound` for the registry page's
link. The builder runs `orgsyndb index` into each release's
`index.json` for that module. `collection-import` added imported
procedures, scope entries, sequences and steps, and the latest
accepted import with its language.

## Goals / Non-Goals

**Goals:**

- A task's steps are rows naming the scope entry they carry out and
  the import current when they were planned, as draft 07 settled.
- Nothing in the application reads `index.json`; the builder stops
  writing it.
- The demo shows tasks that follow sequences, as before.

**Non-Goals:**

- Planning suggesting a start step from stocked intermediates, steps
  started midway through a sequence, and moving a planned step: change
  3.
- Journal entries of steps, lots made by a step, withdrawals, the
  task's `failed` flag: a later change.
- Issued IDs and authors: a later change.

## Decisions

### Steps are rows; the counters go

`tasks.TaskStep` holds `task` (cascade), `position` (from 1, unique per
task), `entry` (a scope entry, protected, or none), `import` (an
import, protected, or none) and `done_on`. A sequence set or changed
by a save replaces the steps with one per sequence step, carrying its
entry and the latest accepted import; a save that keeps the sequence
keeps the steps, so a task survives a withdrawn sequence. Without a
sequence, the form's step total adds or removes plain steps at the
end. Progress is done steps over steps.

`steps done` stays a number in the form, the first that many steps
done: a step already done keeps its date, a newly done one takes today,
the rest are cleared. `step` marks the first open step done today,
`end` every open step on the end date. Step rows keep a change history
of their own, as draft 07 has it, and the task page's history lists
the task's changes and its steps' together, newest first.

A sequence may be set, changed or cleared only while no step is done:
done work belongs to the steps it was done in, and replacing them would
either lose its date or mark other chemistry done. Manual steps cannot
shrink below the done ones.

A step names its entry, not the sequence's step, so it survives the
sequence changing in the collection. When an import withdraws that
entry, its position may pass to other chemistry, so the page shows a
withdrawn entry by its signature and marks it. `Eintrag <n>` needs to
know whether the procedure is general, which the manifest says and the
procedure row now keeps.

Alternatives: keep `steps_total` and `steps_done` beside the rows. Two
sources of one fact drift; the rows are the fact.

### The language comes from the latest accepted import

The middleware takes `language` of `collection.Import.latest_accepted()`
and German without one. The registry page links `In der Sammlung` when
the latest accepted import was received no earlier than the
substance's creation, the first record of its history: that import's
build had the substance's page. The application cannot see whether
the site serves that release yet, so the link may run ahead of the
site after a lost answer, and for the demo's own import until the
builder's first build; the spec says so.

### The demo records its own import

`demo_data` needs sequences for its tasks before any build ran. It
applies `webapp/demo/manifest.json`, the demo collection's manifest,
as an accepted import on `O`, through the same code the manifest view
uses, with a commit of forty zeros and the release `demo`. That import
names no release the builder has, so the builder's first cycle builds
the real collection with that import as its base, and the import
matches the demo's rows by ID and signature, keeping the tasks' links.
The manifest file moves from the tests' fixtures to `webapp/demo/`,
and the root suite's drift guard compares the demo's real manifest
with it.

The demo texts take the language of the latest accepted import before
the command deletes anything, and the data set's import carries that
language, so an English collection keeps an English demo.

### `orgsyndb index` stays

Emacs reads `orgsyndb index`; only the builder's use and the release's
`index.json` go.

## Risks / Trade-offs

- [The demo's import names a fake commit] → It is the demo's own, shown
  on the imports page until the builder's first accepted build follows
  it; a demo database is disposable.
- [Existing tasks lose their steps] → The migration empties the task
  tables it reshapes, as `lab-registry` did; the product has no users
  and the demo is rewritten by `demo_data --replace`.
