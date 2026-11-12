# web-app Specification

## Purpose
Run the lab application beside the static site under `/lab/`: a Django project with its settings from the environment, accounts kept by the application, open reading and signed-in changes, a change history of every lab record, the interface in the site's language, the site's own page shell and stylesheets, and the language of the latest accepted import of the collection.
## Requirements
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

### Requirement: Paths under /lab/
The application SHALL serve everything under `/lab/`: its views, `/lab/accounts/login/`, `/lab/accounts/logout/` and `/lab/accounts/password/`, the admin at `/lab/admin/`, and its static files at `/lab/static/`. `/lab/` shows the lab's overview and `/lab/summary/` its summary (lab-overview "Overview page" and "Summary for the home page"). Any other path answers 404.

#### Scenario: Entry and outside paths
- **WHEN** a test client requests `/lab/` and `/procedures/`
- **THEN** the first answers 200 with a `section.lab-overview` and the second answers 404

### Requirement: Accounts and sign-in
The user model SHALL be `accounts.User`, Django's user with a user name of at most 40 letters and digits, single `.`, `-` or `_` allowed between them, as Forgejo takes user names, fixed once the account exists, since procedure files name their authors by it, and with an added `initials`: one to five letters or digits, unique regardless of case, stored in upper case. A user's display name is the full name, or the user name when that is empty. There is no page for creating one's own account; staff create accounts in the admin. A person signs in with user name and password, signs out with a POST, and changes their own password at `/lab/accounts/password/`. An account without a usable password cannot sign in and can still be named on records.

#### Scenario: Initials
- **WHEN** a test creates a user with initials `kl` and then another with `KL`
- **THEN** the first is stored as `KL` and the second fails validation

#### Scenario: Account without a password
- **WHEN** a test creates an account with an unusable password and posts its user name to the sign-in page
- **THEN** sign-in fails, and the account is offered as assignee in the task form

#### Scenario: User names
- **WHEN** a staff user creates accounts in the admin named `a.example`, `a..b`, `-ab`, `ab-` and `Ä.müller`, and then changes the user name of `a.example`
- **THEN** only `a.example` is created, and its user name cannot be changed

### Requirement: Permissions
Pages that show data SHALL need no sign-in. Every page and action that changes data needs a signed-in user: a request without one, GET or POST, redirects to the sign-in page with `next` set to the requested path and changes nothing. The exceptions are the manifest path, which the builder signs with a service token (collection-import "Manifest"), and the ID path, which needs an account's access token, a signed-in session not being enough (collection-import "Issued IDs"); neither redirects. The admin needs staff status. The views offer no deletion, except that a user revokes their own access tokens (Access tokens); staff delete in the admin.

#### Scenario: Form without sign-in
- **WHEN** a test client that is not signed in requests and posts `/lab/tasks/new/`
- **THEN** both redirect to `/lab/accounts/login/?next=/lab/tasks/new/` and no task exists

### Requirement: Change history
Every model holding lab records SHALL keep a history with django-simple-history: each creation and change stores a copy of the record with the signed-in user and the time. A record's page shows its history, newest first, each entry with its time, the user's initials and either `Angelegt` (`Created`) or the changed fields, each with its label and old and new values.

#### Scenario: History of a change
- **WHEN** a signed-in user `KL` creates a task and then changes its priority from medium to high
- **THEN** the task's page lists two history entries, the newer naming `KL`, the field `Priorität` and the values `mittel` and `hoch`

### Requirement: Interface language
Every text the application shows SHALL come from its translations, German and English, in the language of the latest accepted import of the collection (collection-import "Accepting an import"), or German while none was accepted. The German texts are those the requirements name; the English ones follow in parentheses. A page has `<html lang="<language>">`. Dates show as `03.11.2026` in German and `2026-11-03` in English.

#### Scenario: English site
- **WHEN** the latest accepted import's language is `en` and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="en">`, the navigation reads `Tasks` and a start date of 3 November 2026 shows as `2026-11-03`

#### Scenario: Before any import
- **WHEN** no import was accepted and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="de">`

### Requirement: Page shell
Every page but the admin's and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`. Its `header.site-header` holds the site title linking to `/`, a `nav` labelled as the site's navigation with the application's views, each a link and the path its pages lie under, followed by the site's sections `/compounds/`, `/sequences/`, `/procedures/` and `/help/` under the site's labels. The views are `Bestand` (`Inventory`), linking to `/lab/inventory/end-products/`, its pages under `/lab/inventory/`; `Planung` (`Planning`), linking to `/lab/planning/`, its pages under `/lab/planning/`; `Aufgaben` (`Tasks`), linking to `/lab/tasks/`, its pages under `/lab/tasks/`; and `Substanzen` (`Substances`), linking to `/lab/registry/`, its pages under `/lab/registry/`. A view's link carries `aria-current="page"` on the page it links to and `aria-current="true"` on every other page under its view's path. The header ends with the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. These pages carry no `script` element but the item list, whose one `script` element loads `/lab/static/lab.js` with `defer` (end-product-inventory "Item list"); the admin keeps Django's own pages and scripts. The summary, `/lab/summary/`, links the same five stylesheets and carries no `script` element, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, the navigation lists `Bestand` and `Planung` without `aria-current`, `Aufgaben` with `aria-current="page"`, `Substanzen` without it, and then the four site sections in that order, the first shows `KL` and a sign-out form and the second a link to the sign-in page, and neither has a `script` element

#### Scenario: Navigation in the inventory
- **WHEN** a test client requests the item list and an item's page
- **THEN** the navigation's `Bestand` link carries `aria-current="page"` on the list and `aria-current="true"` on the item's page, and `Planung` and `Aufgaben` carry neither

#### Scenario: Navigation in the planning list
- **WHEN** a test client requests `/lab/planning/` and `/lab/planning/?all=1`
- **THEN** the navigation's `Planung` link carries `aria-current="page"` on both, and `Bestand` and `Aufgaben` carry neither

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` or `script` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: One script for the item list
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** the item list has one `script` element, with `src` `/lab/static/lab.js` and `defer`, and the other two have none

### Requirement: Substance links
Wherever the application shows a substance, the substance of an item, a lot or a task among them, it SHALL show the substance's name (lab-registry "Substances") linking to its page, `/lab/registry/substances/<key>/`, except where a requirement links that name elsewhere, as the item list does for an item without an article number (end-product-inventory "Item list"). A form field for a substance takes its key and offers, through a `datalist`, every substance's key labelled with its name; an unknown key is an error at the field.

#### Scenario: A task's substance
- **WHEN** the demo data set is written and a test client requests `/lab/tasks/?state=all`
- **THEN** each task of `cinnamic-acid` shows `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`

### Requirement: Access tokens
A signed-in user SHALL manage their own access tokens at `/lab/accounts/tokens/`, headed `Zugangsschlüssel` (`Access tokens`): a table of their tokens with the columns `Name`, `Angelegt` (`Created`) and `Zuletzt benutzt` (`Last used`) and, beside each, a button `Widerrufen` (`Revoke`) that deletes it; and a form with a `Name` of at most 100 characters that creates a token and shows it once, with the note `Kopieren Sie den Schlüssel jetzt; er wird nicht wieder angezeigt.` (`Copy the token now; it is not shown again.`). A token is `osdb_` followed by 43 URL-safe characters from a secure random source; the application keeps only its SHA-256 digest, its account, its name, when it was created and when it was last used. A request carrying `Authorization: Bearer <token>` is made by the token's account when the digest matches a token of an active account, and the request records the time as its last use; an unknown token, one of an inactive account or a revoked one is refused with 401. Staff see and delete tokens in the admin. The page needs a signed-in user, as every page that changes data does (Permissions).

#### Scenario: A token shown once
- **WHEN** user `klehmann` posts the name `Laptop` to `/lab/accounts/tokens/`
- **THEN** the answer shows a token beginning `osdb_`, the table lists `Laptop`, a second request of the page shows no token, and no stored value equals the token

#### Scenario: A revoked token
- **WHEN** user `klehmann` revokes the token `Laptop` and a client then requests the issuing of an ID with it
- **THEN** the request is refused with 401

#### Scenario: An inactive account
- **WHEN** an account holding a token is deactivated and a client requests the issuing of an ID with that token
- **THEN** the request is refused with 401

