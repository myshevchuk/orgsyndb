## Context

`collection-registry` made the collection read the application's
registry. The builder (`deploy/docker/orgsyndb-deploy`) clones the
collection, polls it every `ORGSYNDB_INTERVAL` seconds, fetches the
snapshot, builds with `tools/orgsyndb build` or `pdf`, runs
`tools/orgsyndb index`, copies `public/`, `pdf/` and `index.json` into
`<data>/releases/<serial>-<app>-<commit>` and points `<data>/current`
at it. It keeps `state.json` with the published combination and up to
50 failed ones. The application reads `index.json` through
`orgsyndb_web.index` for the site language, compound keys, procedure
IDs and sequence steps, and has no rows for procedures.

Draft 07 of the schema, which the owner settled, adds a `collection`
package whose rows only an accepted import writes, a manifest the
builder sends, and one lock over registry writes and imports. This
change brings that part. Tasks, issued IDs, authors as accounts, the
journal and Forgejo follow in later changes.

## Goals / Non-Goals

**Goals:**

- The application holds procedures, scope entries, sequences and steps
  as rows, written only by an accepted import, never deleted.
- Every build reaches the application, accepted or refused, and the
  site shows only what the application accepted.
- A registry that changes while an import is checked cannot slip in:
  an import is accepted only against the registry it was built with.

**Non-Goals:**

- Tasks on imported rows, the site language from the import, and the
  removal of `index.json`: the next change.
- Issued procedure and sequence IDs, authors as accounts, steps named
  by product: a later change. Steps keep naming a procedure and an
  entry number, which the import resolves.
- Notebooks, projects as columns, lots made by a step: a later change.
- Forgejo, the push log, the gate and `pushed_by`: change 4.

## Decisions

### The manifest has two halves

`tools/orgsyndb manifest` prints the collection half after a build: the
site language and, for each procedure ID, the variant the site
publishes (localization "Choosing the variant to publish"), its title,
the `.de` variant's title, its source format, reaction type and entries;
and each sequence with its target and steps. It reads `build/export/`,
`md/procedures/` and `md/sequences/`, so it needs the export a build
leaves, and fails when Org sources exist without it. The builder adds
the build half: a UUID it chooses for the build, the commit and its
commit time, the snapshot digest, its own application commit as
`tooling`, the base import, the trigger and the staged release.

A specific procedure has one entry, made of its top-level substrates
and products; a general procedure has one per line of its `scope`, in
file order, and the manifest says which it is. A step names a
procedure ID and, for a general procedure only, an entry number
counted from 1, as the validator already requires of sequence files.

Alternatives: let the application parse the collection. It would need
the export tooling and a checkout; the builder already has both.

### One path, signed by a token

`POST /lab/collection/manifest/` takes the manifest as JSON. The
request carries `Authorization: Bearer <ORGSYNDB_BUILDER_TOKEN>`,
compared in constant time. With the setting empty the path answers
404, with a wrong token 403. The view is exempt from CSRF. Caddy
answers 404 for every path beginning with `/lab/collection/manifest`
in a `handle` block of its own, which Caddy orders before `/lab/*` as
the more specific path, so only the compose network reaches the view.

### Accepting under one lock

The view opens a transaction and takes the lock. A build UUID already
recorded is answered with that import's outcome and changes nothing.
A failed build is recorded as refused at once: it writes no rows, so
staleness does not matter. A built manifest whose `base` is not the
latest accepted import's id, or whose `snapshot` is not the current
registry's digest, is answered `409` with `stale` and recorded
nowhere. Otherwise the application
checks the manifest against its registry, records a refused import
with every error, or applies it and records an accepted one, and
answers `200` with the outcome and the import's id. A manifest that is
not JSON of the stated shape is answered `400` and recorded nowhere.

The lock is `orgsyndb_web.lock.hold()`, called inside an atomic block:
on PostgreSQL `pg_advisory_xact_lock` with a fixed key, released at the
end of the transaction; on SQLite nothing, since SQLite lets one writer
in at a time. Every write that changes a value the digest covers takes
it: a substance, its chemical classes, a term and an article, whose
number the snapshot carries. The models take it in their own `save`
and `delete`, inside an atomic block, so the forms, the admin, the
delivery booking that numbers an article and both load commands are
covered without each remembering to.

### Matching rows across imports

A procedure and a sequence are matched by their ID. A scope entry is
matched within its procedure by its signature: the substrates' keys
sorted and joined by ` + `, then ` >> `, then the products' keys sorted
and joined by ` + `. Two entries of one procedure with one signature
refuse the import. A matched entry takes its new position and its
substances' new yields and order; an entry no longer in the file is
withdrawn, and comes back when a later import has its signature again.
A procedure or sequence no longer in the manifest is withdrawn, its
entries and steps left as they were. A sequence's steps follow the file:
they are replaced on every import that changes them. A row records the
accepted import that created it or last changed one of its values, its
entries or its steps.

### The builder publishes what was accepted

The snapshot names the latest accepted import, outside the digest. A
cycle builds when the collection commit, the digest or the
application commit differs from that import's, or when that import's
release is missing, choosing the trigger in that order: `commit`,
`registry`, `tooling`, `catch-up` (also when no import was accepted
yet). It builds, runs `manifest` and `index`, stages the release under
its final name without moving `current`, and sends the manifest:

- `accepted`: point `current` at the release, prune, record it.
- `refused`: remove the staged release and record the combination as
  failed.
- `stale`: remove the staged release; the next cycle builds again with
  a fresh snapshot.
- no answer or another status: log it and keep the staged release;
  the application may have accepted it, and the next cycle publishes it
  when the snapshot names it.

A build that fails sends a manifest with the outcome `refused` and its
errors, the lines of the build's output that contain `: error: `, or the
failure itself. It counts as failed only once the application has
answered that report, so that an outage does not lose it. At the start
of every cycle the builder points `current` at the release the latest
accepted import names, when that release exists. Without
`ORGSYNDB_BUILDER_TOKEN` it builds nothing and logs why.

The latest accepted import comes only from a snapshot fetched in the
same cycle. When the snapshot cannot be fetched, the cycle builds
nothing: the application, which alone can accept a build, is then out
of reach too, and a kept copy cannot say which import it accepted
last. The builder keeps no `registry.source` any more.

### Demo replacement

`demo_data --replace` deletes every lab record. The imported rows are
lab records too and go with them; after the replacement the snapshot's
`import` is `null`, so the builder's next cycle finds no accepted
import and imports the collection again from scratch.

`index.json` stays in the release for the tasks that still read it.

## Risks / Trade-offs

- [The site waits for the application] → A build is published only
  after the application accepts it; while `app` is down the site stays
  on the last accepted release, and the next cycle tries again.
- [A new required setting] → Existing deployments need
  `ORGSYNDB_BUILDER_TOKEN` in `orgsyndb.env`; without it the builder
  says so in its log and publishes nothing.
- [SQLite has no advisory lock] → The development server relies on
  SQLite's single writer; the lock matters on PostgreSQL, where the
  deployment runs.
- [Stale loops] → A registry that changes faster than a build finishes
  keeps answering stale; each cycle builds once, so the site catches up
  when edits pause.
