## Context

The site is static: `tools/orgsyndb` builds it from a collection, and
in a container deployment `orgsyndb-deploy` rebuilds it on every new
commit and Caddy serves the current release. Nothing in the
application stores data outside Git. `orgsyndb index` prints a JSON
description of a collection: its language, declared fields,
vocabularies, compounds, procedures and sequences; a Markdown
sequence's front matter lists its steps as procedure IDs.

The lab's task tracker is an Excel file with the columns product name,
priority, assignee, date started, date ended, steps ended, steps
total, progress, batch number, report and QC list, the last two yes or
no. Its priority is estimated today from the end-product inventory's
forecast. The owner's answers on 2026-11-04: no institute login exists
(no LDAP, AD or single sign-on); reading for everyone, changes for
signed-in users; containers carry no barcodes; whether other
departments will use the application is open. The Excel import waits
for a later change.

## Goals / Non-Goals

**Goals:** a web application beside the static site, under one
address, with accounts, change history and backups; the task tracker
as its first view, with the file's columns and what the application
can add to them; a foundation the end-product inventory and later
views reuse without new deployment pieces.

**Non-Goals:** Excel import and export; links from the static site's
navigation to the application; departments and their permissions;
notifications; an API; JavaScript-driven pages; priorities computed
from the inventory, which need the inventory (`production-planning`).

## Decisions

### Django in this repository, under `webapp/`

The application reads the index that the same checkout's
`tools/orgsyndb` writes and serves the same checkout's stylesheets, so
it lives beside them. `webapp/` has its own `pyproject.toml` and
`uv.lock` (Python 3.14, like the command-line program), so the
program's standard-library rule stays untouched. Django brings
accounts, forms, migrations, an admin for corrections during the
transition, and translations. Rejected: a separate repository, which
would need a release of both for every index change; Flask or FastAPI,
which would need each of those pieces chosen and wired.

Packages: `orgsyndb_web` (settings, URLs, the index reader, the page
shell), `accounts` (the user model), `tasks`. Later views add their own
packages.

### One prefix, `/lab/`

Caddy forwards `/lab/*` to the application and serves everything else
from the release, as now. The Caddyfile is part of the image, and the
updater does not use an application commit that changes
`deploy/docker/`, so each new view must not need a new route. One
prefix also cannot collide with a collection's `static/` files except
under `static/lab/`, which the validator does not forbid; that is
accepted. Paths below the prefix are English, like the site's:
`/lab/tasks/`, later `/lab/inventory/...`. Rejected: one route per view
(`/tasks/`, `/inventory/`), which would need a new image for each.

### The index file, not tables

The updater runs `orgsyndb index` after a successful build and stores
the output as `index.json` in the release. The application reads
`ORGSYNDB_INDEX`, by default `/var/lib/orgsyndb/current/index.json`,
and reads it again when the file's modification time or the release it
resolves to changes. The brainstorm put the index into read-only
database tables marked with the commit; a file is enough while the
application only looks keys up, and tables can follow when a view
needs to search or join compounds. Without a readable index the
application still serves every page: the language is German, products
show as entered, and no sequence can be chosen.

### Language from the index

The interface uses `site_language` of the index, `de` or `en`, with
Django's translations; without an index, `de`, the language of the
shipped `site/hugo.toml`. Dates and numbers follow the language. The
time zone is `Europe/Berlin`, as for modification times. Rejected: a
setting of its own, which could disagree with the site.

### Accounts without an institute login

A custom user model from the start, because Django cannot swap it
later without rebuilding the tables. It adds `initials`, unique, which
the lists show. An administrator creates accounts in the admin. A
person who never signs in, such as a student assigned a task, gets an
account without a usable password. Users change their own password.

### Host names are required

Caddy's default address `:8080` accepts any host name, so the
application checks it: `ORGSYNDB_ALLOWED_HOSTS` is required outside
debug, like the secret key.

### Reading is open, changing needs sign-in

The owner chose this on 2026-11-04. The static site is open to
everyone who reaches the address, and so are the application's pages;
every form and action needs a signed-in user. The admin needs staff
status. Records are not deleted in the views: a task is cancelled
instead. Staff can delete in the admin.

### History with django-simple-history

Every model that holds lab records registers a history: each save
stores a copy of the row with the user and time. A record's page lists
its changes, newest first, each with the fields that changed and their
old and new values. Rejected: a hand-written audit table, which would
repeat what the package does.

### Pages without JavaScript

Lists filter and search with GET forms, edits and actions are plain
POST forms, like the site's rule that content needs no JavaScript.
Progress shows as an HTML `progress` element. A compound field offers
its choices through a `datalist`. A later view may add HTMX where a
page would otherwise reload too often.

### The site's stylesheets

The application's static files include `site/assets/css/` from the
same checkout under `site/`, so pages link `tokens.css`, `base.css`,
`screen.css` and `print.css` as the site's pages do, and add `lab.css`
for forms, badges and messages. The page shell repeats the site
header's markup: the site title, the site's four sections, then the
application's views and the sign-in state. whitenoise serves the
static files under `/lab/static/`. Rejected: linking the release's
fingerprinted stylesheets, whose names change with every build.

### PostgreSQL in deployment, SQLite elsewhere

`ORGSYNDB_DATABASE_URL` names the database, `postgres://...` or
`sqlite:///...`; unset, it is `webapp/db.sqlite3`. Deployment runs
PostgreSQL 18. The suite runs on SQLite by default, and CI runs it on
PostgreSQL as well, so a difference between the two fails in CI.

### The application is updated by hand

The application's image is built from the checkout that holds
`deploy/compose.yaml`, so updating means `git pull`, a backup and
`docker compose up -d --build app`. It starts by applying pending
migrations. The updater keeps following the application's repository
for the site only: migrations against the lab's records should not run
unattended at night. Rejected: an image that clones the repository
like the builder's, which the updater would then have to restart.

### Daily dumps on the host

The `backup` service runs `deploy/backup/orgsyndb-backup` in the
PostgreSQL image, so `pg_dump` matches the server. It writes
`lab-<UTC time>.dump` in custom format to `deploy/backups/`, a host
directory that is easy to copy elsewhere, every
`ORGSYNDB_BACKUP_HOURS` hours (24), and keeps the
`ORGSYNDB_KEEP_BACKUPS` newest (14). `orgsyndb-backup once` writes one
dump, for use before an update. Restoring is `pg_restore`, described in
the README.

### Task numbers from a counter

The tracker has no number column, but a task needs a stable name for
its page and for conversation. `T-` and at least three digits,
assigned when a task is created. A counter row, incremented by one
atomic `UPDATE ... SET value = value + 1` and read back in the same
transaction, gives the next number, so two people saving at once get
different numbers and a number deleted in the admin is not reused.
Rejected: `select_for_update()`, which Django ignores on SQLite.

### State from the dates

The tracker records when a task started and ended, so the state
follows from them instead of being kept twice: no start date is
planned, a start without an end is running, an end is ended. A
cancelled flag takes a task out of the active list without deleting
it. An ended task whose report or QC-list flag is still off needs
follow-up and stays in the active list until both are set, since that
is the work the two flags track.

### Identifiers without collisions

The validator checks each unique field on its own, so a value can
repeat across fields or equal another compound's key. A key wins; a
value found in more than one compound finds none, so an ambiguous
identifier never picks a compound at random.

### Products as compounds, where the collection has them

The product is text: a compound identifier from the index, by key or a
unique text field such as an item number, or a name the collection does
not have yet. A product the index finds shows under the compound's name
and links to its page; any other shows as entered with a mark. Rejected:
requiring a compound, which would block tasks for products whose
compound file does not exist yet.

### Steps from a synthesis sequence

A task may name a synthesis sequence of the collection. The save that
sets or changes it copies the sequence's steps onto the task, and their
number becomes the steps total; later saves read nothing from the
index. A recorded task therefore keeps the steps it was planned with
when the sequence is edited or removed, and an edit of a flag never
fails on the index. The task's page lists the copied steps with their
procedures, the first `steps_done` marked done. Without a sequence the
total is entered. Progress is computed, never entered. Rejected:
reading the sequence on every save or display, which let a sequence
edit rewrite a task's history.

### Actions on the task page

Starting a task, finishing a step and ending it are single buttons on
the task's page for a signed-in user, each a POST that sets today's date
or adds one step, so the tracker's most frequent edits need no form.
Dates may not lie in the future, so ending today never precedes the
start.

### The admin keeps its own pages

The page shell and the rule against scripts cover the application's
own pages. The admin is Django's, with its own templates and scripts,
and only staff use it.

## Risks / Trade-offs

- The application and the site may run different commits, since only
  the site follows the repository. The application reads only index
  keys that exist today and treats a missing key as no data.
- The site's stylesheets were written for the site's pages; the
  application's markup must use the same classes, and a change to
  them can break application pages. The suite renders the shell and
  checks the classes it relies on.
- Open reading: if a deployment is reachable from the internet, so are
  the tasks. The owner accepts this for now.

## Open Questions

- The priority's values: the draft uses high, medium and low.
