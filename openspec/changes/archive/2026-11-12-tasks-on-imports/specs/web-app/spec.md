## MODIFIED Requirements

### Requirement: Application project
`webapp/` SHALL hold a Django project: `pyproject.toml`, requiring Python 3.14 or later and naming Django, django-simple-history, psycopg, gunicorn and whitenoise as dependencies and pytest and pytest-django for development; `uv.lock`; `manage.py`; and the packages `orgsyndb_web`, which holds the settings, the URLs and the page shell, `accounts` and `tasks`. The application's tests live in `webapp/tests/` as `unittest.TestCase` classes, and `uv run pytest` in `webapp/` runs them. A `pytest` run at the repository root without arguments collects only `tests/`, so the program's suite needs no Django. Nothing under `tools/` imports from `webapp/`.

#### Scenario: Project file
- **WHEN** a test reads `webapp/pyproject.toml`
- **THEN** `requires-python` is `>=3.14` and the dependencies name the five packages

#### Scenario: Root suite leaves the application out
- **WHEN** `pytest --collect-only -q` runs at the repository root
- **THEN** no collected test lies under `webapp/`

### Requirement: Settings from the environment
The settings SHALL come from these environment variables:

- `ORGSYNDB_SECRET_KEY`: Django's secret key; required unless `ORGSYNDB_DEBUG` is true.
- `ORGSYNDB_DEBUG`: a flag, default false.
- `ORGSYNDB_DATABASE_URL`: `postgres://<user>:<password>@<host>[:<port>]/<name>` for PostgreSQL or `sqlite:///<path>` for SQLite; default `sqlite:///` and the absolute path of `webapp/db.sqlite3`.
- `ORGSYNDB_ALLOWED_HOSTS`: the host names the site is reached by, separated by commas; required unless `ORGSYNDB_DEBUG` is true, when it defaults to `localhost,127.0.0.1`.
- `ORGSYNDB_DEMO`: a flag, default false, that permits writing the demo data (lab-demo "Demo data command").
- `ORGSYNDB_BUILDER_TOKEN`: the token the builder signs its manifests with (collection-import "Manifest"); default empty, which turns the manifest path off.

A flag takes the words `orgsyndb-deploy` accepts. A missing secret key or host list, a malformed flag or a database URL of another scheme stops the start with a message naming the variable. A request forwarded with `X-Forwarded-Proto: https` counts as secure. The time zone is `Europe/Berlin`. `webapp/db.sqlite3` is ignored by Git.

#### Scenario: Secret key required
- **WHEN** a test loads the settings without `ORGSYNDB_SECRET_KEY` and with `ORGSYNDB_DEBUG` unset
- **THEN** loading fails with a message naming `ORGSYNDB_SECRET_KEY`

#### Scenario: Requests through the proxy
- **WHEN** a test client with CSRF checks enforced posts the sign-in form to host `lab.example.org`, listed in `ORGSYNDB_ALLOWED_HOSTS`, with `X-Forwarded-Proto: https` and the origin `https://lab.example.org`, and once with the host `other.example.org`
- **THEN** the first is treated as secure and accepted, and the second answers 400

#### Scenario: Database URLs
- **WHEN** a test loads the settings with `ORGSYNDB_DATABASE_URL` set to `postgres://lab:secret@db:5432/lab`, to `sqlite:////tmp/x.sqlite3` and to `mysql://db/lab`
- **THEN** the first gives the PostgreSQL engine with name `lab`, user `lab`, password `secret`, host `db` and port `5432`, the second the SQLite engine with name `/tmp/x.sqlite3`, and the third fails naming `ORGSYNDB_DATABASE_URL`

#### Scenario: Demo flag
- **WHEN** a test loads the settings with `ORGSYNDB_DEMO` unset, set to `yes` and set to `maybe`
- **THEN** the first gives the flag false, the second true, and the third fails naming `ORGSYNDB_DEMO`

#### Scenario: Builder token
- **WHEN** a test loads the settings with `ORGSYNDB_BUILDER_TOKEN` unset and set to `s3cret`
- **THEN** the first gives an empty token and the second `s3cret`

### Requirement: Interface language
Every text the application shows SHALL come from its translations, German and English, in the language of the latest accepted import of the collection (collection-import "Accepting an import"), or German while none was accepted. The German texts are those the requirements name; the English ones follow in parentheses. A page has `<html lang="<language>">`. Dates show as `03.11.2026` in German and `2026-11-03` in English.

#### Scenario: English site
- **WHEN** the latest accepted import's language is `en` and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="en">`, the navigation reads `Tasks` and a start date of 3 November 2026 shows as `2026-11-03`

#### Scenario: Before any import
- **WHEN** no import was accepted and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="de">`

## REMOVED Requirements

### Requirement: Collection index
**Reason**: The application reads the collection from its imported rows (collection-import) and the language from the latest accepted import; `index.json` is no longer published.
**Migration**: None; nothing outside the application read it.
