## Why

The lab keeps its inventories, QC results, product catalogue and task
list in Excel files, each in its own layout. What many people change
every day belongs in a database; procedures and compounds stay text in
Git. The task tracker follows the syntheses of end products: which
product, its priority, who works on it, when it started and ended, how
many steps are done, the batch it gave, and whether the report is
written and the batch is on the QC list. It refers to the other files
only by product and batch, so it is the first to move: it brings in the
web application that later views share, and exercises sign-in, change
history, backups and deployment on the data that would hurt least to
lose. Importing the Excel file is left to a later change; tasks are
entered in the application.

## What Changes

- `webapp/`: a Django project with its own `pyproject.toml` and
  `uv.lock`, served under `/lab/` at the site's address. Its pages need
  no JavaScript and use the site's own stylesheets.
- Accounts belong to the application: an administrator creates them,
  each with initials; there is no self-registration. Reading needs no
  sign-in, every change does.
- Every change to a record keeps its author, its time and the old and
  new values.
- The interface speaks the site's language, German or English, taken
  from the collection index of the published release, which also gives
  the compounds and synthesis sequences that tasks name.
- Tasks at `/lab/tasks/`, with the tracker's columns: product,
  priority, assignee, start and end dates, steps done of steps total,
  progress, batch number, and the report and QC-list flags. Beyond the
  file: a task number `T-NNN`; a state derived from the dates; follow-up
  for ended tasks still lacking the report or the QC list; an optional
  synthesis sequence of the collection that sets the steps and lists
  them with their procedures; buttons on the task page to start it,
  finish a step and end it.
- Deployment: `deploy/compose.yaml` gains a PostgreSQL service, the
  application's service and a backup service that dumps the database
  daily into `deploy/backups/`. Caddy forwards `/lab/` to the
  application. The updater writes the collection index into each
  release.

## Capabilities

### New Capabilities

- `web-app`: the Django project, its settings, accounts and sign-in,
  permissions, change history, language, page shell, and the reader of
  the collection index.
- `task-tracker`: tasks, their numbers, state, list, page, actions,
  forms and history.

### Modified Capabilities

- `container-deployment`: releases hold `index.json`; Caddy forwards
  `/lab/`; Compose runs the database, the application and backups.

## Impact

- New: `webapp/`, `deploy/webapp/Dockerfile`, `deploy/backup/`,
  `.github/workflows/webapp.yml`, `pytest.ini`.
- Changed: `deploy/docker/orgsyndb-deploy`, `deploy/docker/Caddyfile`,
  `deploy/compose.yaml`, `deploy/orgsyndb.env.example`,
  `tests/test_deploy.py`, `.gitignore`.
- Changing `deploy/docker/` means existing deployments rebuild their
  image.
- New dependencies, for the application only: Django,
  django-simple-history, psycopg, gunicorn, whitenoise; pytest-django
  for its tests. The command-line program stays standard-library only.
- Docs: `README.md` gains the application, its accounts, updates and
  backups.
- Not included: Excel import or export, links from the static site's
  navigation to the application, departments, priorities suggested
  from the inventory (`production-planning`).
