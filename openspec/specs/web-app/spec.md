# web-app Specification

## Purpose
Run the lab application beside the static site under `/lab/`: a Django project with its settings from the environment, accounts kept by the application, open reading and signed-in changes, a change history of every lab record, the interface in the site's language, the site's own page shell and stylesheets, and the language of the latest accepted import of the collection.
## Requirements
### Requirement: Application project
`webapp/` SHALL hold a Django project: `pyproject.toml`, declaring the Python it requires and naming Django, django-simple-history, psycopg, gunicorn and whitenoise as dependencies; `uv.lock`; `manage.py`; and the packages `orgsyndb_web`, which holds the settings, the URLs and the page shell, `accounts` and `tasks`. The application's tests live in `webapp/tests/` as `unittest.TestCase` classes, and `uv run pytest` in `webapp/` runs them. A `pytest` run at the repository root without arguments collects only `tests/`, so the program's suite needs no Django. Nothing under `tools/` imports from `webapp/`.

#### Scenario: Project file
- **WHEN** a test reads `webapp/pyproject.toml`
- **THEN** `requires-python` is set and the dependencies name the five packages

#### Scenario: Root suite leaves the application out
- **WHEN** `pytest --collect-only -q` runs at the repository root
- **THEN** no collected test lies under `webapp/`

### Requirement: Settings from the environment
The settings SHALL come from these environment variables:

- `ORGSYNDB_SECRET_KEY`: Django's secret key; required unless `ORGSYNDB_DEBUG` is true.
- `ORGSYNDB_DEBUG`: a flag, default false.
- `ORGSYNDB_DATABASE_URL`: `postgres://<user>:<password>@<host>[:<port>]/<name>`, the PostgreSQL database; default `postgres://lab:lab@localhost:5432/lab`, the local development database.
- `ORGSYNDB_ALLOWED_HOSTS`: the host names the site is reached by, separated by commas; required unless `ORGSYNDB_DEBUG` is true, when it defaults to `localhost,127.0.0.1`.
- `ORGSYNDB_DEMO`: a flag, default false, that permits writing the demo data (lab-demo "Demo data command").
- `ORGSYNDB_BUILDER_TOKEN`: the token the builder signs its manifests with (collection-import "Manifest"); default empty, which turns the manifest path off.
- `ORGSYNDB_WAKE_URL`: the builder's wake-up address (collection-import "Wake-up after a registry write"); default empty, which sends no wake-up.

A flag takes the words `orgsyndb-deploy` accepts. A missing secret key or host list, a malformed flag or a database URL of another scheme stops the start with a message naming the variable. A request forwarded with `X-Forwarded-Proto: https` counts as secure. The time zone is `Europe/Berlin`.

#### Scenario: Secret key required
- **WHEN** a test loads the settings without `ORGSYNDB_SECRET_KEY` and with `ORGSYNDB_DEBUG` unset
- **THEN** loading fails with a message naming `ORGSYNDB_SECRET_KEY`

#### Scenario: Requests through the proxy
- **WHEN** a test client with CSRF checks enforced posts the sign-in form to host `lab.example.org`, listed in `ORGSYNDB_ALLOWED_HOSTS`, with `X-Forwarded-Proto: https` and the origin `https://lab.example.org`, and once with the host `other.example.org`
- **THEN** the first is treated as secure and accepted, and the second answers 400

#### Scenario: Database URLs
- **WHEN** a test loads the settings with `ORGSYNDB_DATABASE_URL` set to `postgres://lab:secret@db:5432/lab`, to `sqlite:////tmp/x.sqlite3`, to `mysql://db/lab` and not at all
- **THEN** the first gives the PostgreSQL engine with name `lab`, user `lab`, password `secret`, host `db` and port `5432`, the second and the third fail naming `ORGSYNDB_DATABASE_URL`, and the fourth gives the PostgreSQL engine with name `lab` on `localhost`

#### Scenario: Demo flag
- **WHEN** a test loads the settings with `ORGSYNDB_DEMO` unset, set to `yes` and set to `maybe`
- **THEN** the first gives the flag false, the second true, and the third fails naming `ORGSYNDB_DEMO`

#### Scenario: Wake-up address
- **WHEN** a test loads the settings with `ORGSYNDB_WAKE_URL` unset and set to `http://builder:8091/wake`
- **THEN** the first gives an empty address and the second that address

#### Scenario: Builder token
- **WHEN** a test loads the settings with `ORGSYNDB_BUILDER_TOKEN` unset and set to `s3cret`
- **THEN** the first gives an empty token and the second `s3cret`

### Requirement: Paths under /lab/
The application SHALL serve everything under `/lab/`: its views, `/lab/accounts/login/`, `/lab/accounts/logout/` and `/lab/accounts/password/`, the admin at `/lab/admin/`, and its static files at `/lab/static/`. `/lab/` shows the lab's overview and `/lab/summary/` its summary (lab-overview "Overview page" and "Summary for the home page"). Any other path answers 404.

#### Scenario: Entry and outside paths
- **WHEN** a test client requests `/lab/` and `/procedures/`
- **THEN** the first answers 200 with a `section.lab-overview` and the second answers 404

### Requirement: Accounts and sign-in
The user model SHALL be `accounts.User`, Django's user with a user name of at most 40 letters and digits, single `.`, `-` or `_` allowed between them, as Forgejo takes user names, unique regardless of case, as Forgejo's are, fixed once the account exists, since procedure files name their authors by it, and with an added `initials`: one to five letters or digits, unique regardless of case, stored in upper case. A user name equal, regardless of case, to one Forgejo reserves for itself, one ending in `.keys`, `.gpg`, `.rss`, `.atom` or `.png`, which Forgejo refuses too, or `orgsyndb`, the name of the Forgejo account the application uses (Forgejo accounts), is refused, so that every account can have its Forgejo account. An account's email address may be empty and is otherwise unique regardless of case, since Forgejo takes each address once. A user's display name is the full name, or the user name when that is empty. There is no page for creating one's own account; staff create accounts in the admin. A person signs in with user name and password, signs out with a POST, and changes their own password at `/lab/accounts/password/`. An account without a usable password cannot sign in and can still be named on records. The session and CSRF cookies have the path `/lab/`, so that Forgejo, served from the same host, does not receive them (container-deployment "Forgejo").

#### Scenario: Initials
- **WHEN** a test creates a user with initials `kl` and then another with `KL`
- **THEN** the first is stored as `KL` and the second fails validation

#### Scenario: Account without a password
- **WHEN** a test creates an account with an unusable password and posts its user name to the sign-in page
- **THEN** sign-in fails, and the account is offered as assignee in the task form

#### Scenario: User names
- **WHEN** a staff user creates accounts in the admin named `a.example`, `a..b`, `-ab`, `ab-` and `Ä.müller`, and then changes the user name of `a.example`
- **THEN** only `a.example` is created, and its user name cannot be changed

#### Scenario: Reserved user names
- **WHEN** a staff user creates accounts in the admin named `Admin`, `explore`, `anna.rss`, `a.png` and `orgsyndb`
- **THEN** none is created, and each form names the user name as reserved

#### Scenario: User names differing in case
- **WHEN** a staff user creates the account `alice` and then `Alice`
- **THEN** the second fails validation

#### Scenario: Cookie path
- **WHEN** a test client signs in
- **THEN** the session cookie and the CSRF cookie have the path `/lab/`

#### Scenario: Email addresses
- **WHEN** a staff user gives one account the address `kl@example.org`, then another `KL@Example.org`, and leaves two more without an address
- **THEN** the second fails validation and both accounts without an address are saved

### Requirement: Permissions
Pages that show data SHALL need no sign-in. Every page and action that changes data needs a signed-in user: a request without one, GET or POST, redirects to the sign-in page with `next` set to the requested path and changes nothing; a request for a form in a dialog leads the page it was made from to the sign-in page instead, with `next` set to that page's address (Form dialogs). The exceptions are the manifest path, which the builder signs with a service token (collection-import "Manifest"); the ID path, which needs an account's access token, a signed-in session not being enough (collection-import "Issued IDs"); and the OpenID provider's token and user-info paths, which authenticate the client or the token they are given (OpenID provider); none of these redirects. The admin needs staff status. The views offer no deletion, except that a user revokes their own access tokens (Access tokens); staff delete in the admin.

#### Scenario: Form without sign-in
- **WHEN** a test client that is not signed in requests and posts `/lab/tasks/new/`
- **THEN** both redirect to `/lab/accounts/login/?next=/lab/tasks/new/` and no task exists

### Requirement: Change history
Every model holding lab records SHALL keep a history with django-simple-history: each creation and change stores a copy of the record with the signed-in user and the time. A value the application derives from the record's other values and keeps as a cache, a substance's structure drawing (lab-registry "Structure images"), is left out of the copy. A record's page shows its history, newest first, each entry with its time, the user's initials and either `Angelegt` (`Created`) or the changed fields, each with its label and old and new values.

#### Scenario: History of a change
- **WHEN** a signed-in user `KL` creates a task and then changes its priority from medium to high
- **THEN** the task's page lists two history entries, the newer naming `KL`, the field `Priorität` and the values `mittel` and `hoch`

### Requirement: Interface language
Every text the application shows SHALL come from its translations, German and English, or, for the site title, the navigation and the search form, from the site's interface strings (localization "Interface strings"), in the language of the latest accepted import of the collection (collection-import "Accepting an import"), or German while none was accepted. The German texts are those the requirements name; the English ones follow in parentheses. A page has `<html lang="<language>">`. Dates show as `03.11.2026` in German and `2026-11-03` in English.

#### Scenario: English site
- **WHEN** the latest accepted import's language is `en` and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="en">`, the navigation's texts are those of `site/i18n/en.toml`, the sign-in link reads `Sign in` and a start date of 3 November 2026 shows as `2026-11-03`

#### Scenario: Before any import
- **WHEN** no import was accepted and a test client requests `/lab/tasks/`
- **THEN** the page has `<html lang="de">`

### Requirement: Page shell
Every page but the admin's, the authorization endpoint's error page and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`, and load htmx, idiomorph, and then `/lab/static/lab.js`, all with `defer` (Scripts). Its `header.site-header` holds the site's shell, read from `site/hugo.toml` and `site/i18n/` of the same checkout: the site title linking to `/`; the site's search form as the site's pages other than the catalogues have it (site-theme "Page shell"); and the navigation, with every entry of the menu, those under `/lab/` included (site-theme "Navigation"). The header also shows the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. The admin keeps Django's own pages and scripts, and the authorization endpoint (OpenID provider) answers a request it refuses with the OAuth toolkit's own error page. The summary, `/lab/summary/`, links the same five stylesheets, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, hold the site title, the site's search form and the navigation as site-theme "Navigation" states them for a build with the lab application's views, the first shows `KL` and a sign-out form and the second a link to the sign-in page

#### Scenario: Current link on the application's pages
- **WHEN** a test client requests every page of the application that the menu links, and a page inside the section of each
- **THEN** each page's navigation marks its links as site-theme "Navigation" states

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: Scripts on every page
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** each loads `/lab/static/htmx/htmx.min.js`, `/lab/static/idiomorph/idiomorph-ext.min.js`, and then `/lab/static/lab.js`, all with `defer`

### Requirement: Substance links
Wherever the application shows a substance, the substance of an item, a batch, a vessel or a task among them, it SHALL show the substance's name (lab-registry "Substances") linking to its page, `/lab/registry/substances/<key>/`, except where a requirement links that name elsewhere, as the item list does for an item without an article number (end-product-inventory "Item list"). A form field for a substance takes its key and offers, through a `datalist`, every substance's key labelled with its name; an unknown key is an error at the field.

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

### Requirement: OpenID provider
The application SHALL be an OpenID Connect provider, under `/lab/o/`, for one client, Forgejo, when `ORGSYNDB_OIDC_KEY` holds a PEM-encoded RSA private key in base64; without it every path under `/lab/o/` answers 404. `manage.py forge_client` creates or updates the client from `ORGSYNDB_FORGE_CLIENT_SECRET`, and does nothing without it: client id `forgejo`, confidential, the authorization code flow without PKCE, which Forgejo does not send, ID tokens signed with RS256, the one redirect URI `<ORGSYNDB_URL>/git/user/oauth2/lab/callback`, and no consent page. The issuer is `<ORGSYNDB_URL>/lab/o` in every ID token, whichever host the token was requested through.

`/lab/o/.well-known/openid-configuration` names the issuer `<ORGSYNDB_URL>/lab/o` and the authorization endpoint `<ORGSYNDB_URL>/lab/o/authorize/`, which the person's browser reaches, and the token, user-info and keys endpoints under `ORGSYNDB_APP_INTERNAL_URL`, `http://app:8000` by default, at `/lab/o/token/`, `/lab/o/userinfo/` and `/lab/o/.well-known/jwks.json`, which only Forgejo's server calls; it lists the scopes `openid`, `profile` and `email`.

The authorization endpoint needs a signed-in user, as every page that changes data does (Permissions). For a signed-in account with an email address it sends the person back to the redirect URI with a code at once. For one without, it answers with the page `Kein Zugang zu Forgejo` (`No access to Forgejo`), saying that staff must give the account an email address first, and sends nobody back. The ID token and the user info carry `sub`, the account's primary key as text, `nickname` and `preferred_username`, both the user name, `name`, the display name, and `email`, the email address, and `groups`, the list `["authors"]` for every account, under the scope `profile`, so that Forgejo makes the account a member of the team `authors` at each sign-in (container-deployment "Forgejo"). An inactive account cannot sign in (Accounts and sign-in), so it authorizes nothing; and a code, a refresh token or an access token issued to an account that has since been deactivated is refused, at the token and user-info endpoints alike.

#### Scenario: Discovery
- **WHEN** the provider is on with `ORGSYNDB_URL=http://localhost:8080` and a test client requests `/lab/o/.well-known/openid-configuration`
- **THEN** the issuer is `http://localhost:8080/lab/o`, the authorization endpoint `http://localhost:8080/lab/o/authorize/`, the token endpoint `http://app:8000/lab/o/token/` and the scopes include `openid`, `profile` and `email`

#### Scenario: Signing in to Forgejo
- **WHEN** `klehmann`, with the address `kl@example.org`, is signed in and the client `forgejo` requests the authorization endpoint with the scopes `openid profile email` and its redirect URI and no code challenge, and then posts the code it received to the token endpoint with its secret, with the host `app:8000`
- **THEN** the first answer redirects to the redirect URI with a code and the given state, and the ID token, signed with RS256, has the issuer `http://localhost:8080/lab/o`, the audience `forgejo`, `sub` the account's primary key, `nickname` and `preferred_username` `klehmann`, `name` `Katrin Lehmann` and `email` `kl@example.org`, as has the user info for the access token, and both carry `groups` `["authors"]`

#### Scenario: Not signed in
- **WHEN** a test client that is not signed in requests the authorization endpoint
- **THEN** it redirects to the sign-in page with `next` set to the requested path and query

#### Scenario: An account without an address
- **WHEN** a signed-in account without an email address requests the authorization endpoint for `forgejo`
- **THEN** the answer is the page `Kein Zugang zu Forgejo` and no code was issued

#### Scenario: Provider off
- **WHEN** `ORGSYNDB_OIDC_KEY` is unset and a test client requests `/lab/o/.well-known/openid-configuration` and `/lab/o/authorize/`
- **THEN** both answer 404

#### Scenario: Deactivated after the code
- **WHEN** `klehmann` receives a code, is then deactivated, and the client posts the code to the token endpoint
- **THEN** the answer is an error and carries no token, and the user info for an access token issued before the deactivation is refused too

#### Scenario: A wrong secret
- **WHEN** a client posts a valid code to the token endpoint with another secret
- **THEN** the answer is 401 and carries no token

### Requirement: Forgejo accounts
When `ORGSYNDB_FORGE_URL` names Forgejo's API and `ORGSYNDB_FORGE_PASSWORD` the password of its admin account `orgsyndb`, saving an account whose `is_active`, email address or display name changed SHALL set, once the save has committed and from the account as stored, on its Forgejo account `prohibit_login` to the opposite of `is_active`, the email to the address, or to `<user name>@noreply.localhost` when the address is empty, so that an address the lab gave up is free in Forgejo too, and the full name to the display name, through Forgejo's admin API with basic authentication as `orgsyndb`. The Forgejo account is the one of the source `lab` whose login name is the account's primary key; an account without one has nothing to change. The block keeps the Forgejo account's access tokens and SSH keys, which work again once the account is reactivated. When Forgejo cannot be reached or refuses, the account is saved all the same and the admin shows the warning `Forgejo wurde nicht aktualisiert; manage.py forge_accounts gleicht es ab.` (`Forgejo was not updated; manage.py forge_accounts brings it in line.`); until then the Forgejo account keeps its previous state. `manage.py forge_accounts` sets every Forgejo account of the source `lab` to its lab account in the same way, freeing an address another of them still holds before giving it out, blocks one whose login name names no lab account, prints each account it changed and exits non-zero when Forgejo cannot be reached. Without the two settings neither calls Forgejo.

#### Scenario: Deactivating an account
- **WHEN** staff deactivate `tbauer` in the admin and a fake Forgejo API knows a source-`lab` account with `tbauer`'s primary key as its login name
- **THEN** the fake received one request setting that account's `prohibit_login` to true, authenticated as `orgsyndb`, and none deleting a token or a key

#### Scenario: Reactivating an account
- **WHEN** staff reactivate `tbauer`
- **THEN** the fake received one request setting `prohibit_login` to false

#### Scenario: A new address
- **WHEN** staff change `tbauer`'s address to `tb@example.org`
- **THEN** the fake received one request setting that account's email to `tb@example.org` and its full name to `Tobias Bauer`

#### Scenario: A cleared address
- **WHEN** staff clear `tbauer`'s address
- **THEN** the fake received one request setting that account's email to `tbauer@noreply.localhost`

#### Scenario: A save rolled back
- **WHEN** a save that deactivates `tbauer` runs in a transaction that is then rolled back
- **THEN** the fake received no request

#### Scenario: Forgejo unreachable
- **WHEN** staff deactivate `tbauer` while Forgejo's address answers nothing
- **THEN** `tbauer` is inactive and the admin page shows the warning naming `forge_accounts`

#### Scenario: Bringing Forgejo in line
- **WHEN** `forge_accounts` runs against a fake that knows an unblocked account of the inactive `mwolf`, a blocked account of the active `jkoch`, an account of `aschmidt` with an old address and an account whose login name names no lab account
- **THEN** the first and the last are blocked, `jkoch`'s is unblocked, `aschmidt`'s gets the lab account's address, the output names all four, and it exits 0

#### Scenario: An address passed on during an outage
- **WHEN** while Forgejo was unreachable `aschmidt` changed from `as@example.org` to `anna@example.org` and `jkoch` then took `as@example.org`, and `forge_accounts` runs with `jkoch`'s Forgejo account listed first
- **THEN** both Forgejo accounts end with their lab addresses and it exits 0

#### Scenario: No Forgejo configured
- **WHEN** `ORGSYNDB_FORGE_URL` is unset and staff deactivate `tbauer`
- **THEN** no request is made and no warning shows

### Requirement: Scripts
Every page of the application but the admin's SHALL take its scripts from the application's own static files, served under `/lab/static/`. A library is kept in the repository at a fixed version, beside its licence; the application includes htmx and idiomorph so. No `script` element holds code, and no element carries an attribute that holds code: no attribute name begins with `on`, `hx-on` or `data-hx-on`, a page that loads htmx configures it, through the `meta` element `htmx-config`, with `allowEval` false, so that it evaluates no code it finds in the page, and any `hx-swap` or `data-hx-swap` attribute whose swap style begins with `morph` uses only `morph`, `morph:outerHTML` or `morph:innerHTML`. A page may load parts of other pages into itself; whatever it loads, the server also shows in a complete page at a URL of its own, so that a link or a reload shows it.

#### Scenario: Scripts from the application's files
- **WHEN** a test client requests every page of the application that the menu links, a task's page and its edit form, signed in as `KL`, and the sign-in page, not signed in
- **THEN** every `script` element of each page has a `src` beginning with `/lab/static/` and no text, no element carries an attribute whose name begins with `on`, `hx-on` or `data-hx-on`, any `hx-swap` or `data-hx-swap` morph style is one of `morph`, `morph:outerHTML` or `morph:innerHTML`, and the page's `meta` `htmx-config` holds JSON with `allowEval` false

#### Scenario: htmx kept with its licence
- **WHEN** a test looks up htmx among the application's static files
- **THEN** it finds `htmx/htmx.min.js` and the licence beside it

#### Scenario: idiomorph kept with its licence
- **WHEN** a test looks up idiomorph among the application's static files
- **THEN** it finds `idiomorph/idiomorph-ext.min.js` and the licence beside it

### Requirement: Form dialogs
Where a page opens a form in a dialog, as the specs of its pages say, the application SHALL show the form in a modal dialog over the page, which stays as it is behind it; the address does not change. The dialog is headed by the form's title and holds the form's fields and buttons. `Abbrechen` (`Cancel`), the Escape key and the dialog's close button close it and save nothing. Invalid input, and a booking the application refuses, show the form again in the dialog with the errors beside their fields and save nothing; a button that only fills in the form, such as `Menge vorschlagen` (`Propose amount`), fills it in the dialog. Once the form is saved, the page shows what a reload would show, without being loaded anew, and then the dialog closes: the message naming the record shows as it does above a page, and every part of the page that the save changed, such as the record's heading and links, the rows and their order, colours and counts of a list, shows its new state. Its scroll position and the selections and view controls a user set in it stay as they were, and so does the item selected in it while that item is still listed; otherwise the item a reload would select is selected, and the address names it. A user who is no longer signed in when the form is requested or saved is led to the sign-in page, which leads back to the page with its address unchanged, and nothing is saved (Permissions). A form opened so keeps its URL: requested as a page, by a reload or a link opened in a new tab, it shows as a complete page that posts as a page and leads where it led before (Scripts).

#### Scenario: The form alone for a dialog
- **WHEN** a signed-in user's page requests the filling form of an item for a dialog, and requests the same URL as a page
- **THEN** the first answer holds the form headed by its title and no page header or navigation, and the second is the complete form page

#### Scenario: Errors stay in the dialog
- **WHEN** a signed-in user's page posts the count correction of an item for a dialog with a count that is not a number
- **THEN** the answer is the form alone with the error at the count, and the item's count is unchanged

#### Scenario: Saved in a dialog
- **WHEN** a signed-in user's page posts a valid count correction of an item for a dialog
- **THEN** the count is corrected, the answer shows nothing in the dialog and tells the page that the item was saved, and the next page the user requests shows the message `Bestand von <item> korrigiert.`

#### Scenario: Signed out meanwhile
- **WHEN** the page `/lab/inventory/end-products/?q=CH&selected=3`, without a signed-in user, requests an item's filling form for a dialog, and posts it
- **THEN** each answer leads the page to `/lab/accounts/login/` with `next` the page's whole address, and nothing is booked

#### Scenario: The form page posts as a page
- **WHEN** a signed-in user requests the filling form of an item as a page
- **THEN** its form posts to its URL without htmx, and a valid post redirects to the item's page

#### Scenario: Refreshed parts come from the page
- **WHEN** a signed-in user requests the item list and an item's page
- **THEN** the list marks as refreshed parts its count, its summary, its stock filter, its table body and its details, and the item page everything below the page's header

### Requirement: Widgets
The item page (end-product-inventory "Item page"), the change history of every record page (Change history), and every page whose spec says it shows its data in widgets SHALL show each widget as a `section.widget`, or, when it is collapsible, a `details.widget`, headed by a title bar holding the widget's title and, where the page gives them, a count and a short note; the title bar of a collapsible widget is its `summary`. The history widget is collapsible and closed when the page loads, and its count is the number of its entries. The same kind of data shows in the same kind of widget on every such page. A collapsible widget's content is part of the page whether it is open or closed. Printing the page from a browser prints every collapsible widget open and every sortable table with its column headers, with or without the script.

A table marked `data-sortable` sorts in the browser when a user activates one of its column headers: by that column ascending, then descending on each further activation, alternating. The header of the sorted column carries `aria-sort`, and no other header does. A cell's sort key is its `data-sort` attribute when it has one, otherwise its text; a template gives `data-sort` to every cell whose text is not its value: amounts in different units, and dates and times, whose key is ISO 8601 in every language. A key reads as a number when it is one, with a sign and a decimal comma or point; as a date when it reads `YYYY-MM-DD` or `DD.MM.YYYY`, either with an optional time `HH:MM`; and otherwise as text. Ascending, numbers come first by value, then dates by their order, then text by the language's collation; descending reverses that whole order. Empty keys and keys reading `–` come last in either direction, and rows of equal key keep their order. Without the script, and until a user sorts it, the table shows the order its page's spec states.

A collapsible widget's open or closed state and a sortable table's sorting are view controls (Form dialogs): when a part of the page is refreshed after a form saved in a dialog, each widget and table that the new part holds under the same `id` keeps them, its rows sorted anew, and its headers sort as before.

#### Scenario: Change history as a collapsible widget
- **WHEN** a test client requests the page of an item created with compartment `1` and box `A`, which a signed-in user `KL` then changed, in one save, to compartment `2` and box `B`
- **THEN** the page holds one `details.widget` without `open`, titled `Änderungen` with the count 2, holding a table of three rows, newest first: two of the save naming `KL`, one the field `Fach` with `1` and `2`, the other `Box` with `A` and `B`, and the creation's reading `Angelegt`

#### Scenario: Removed step in a task's history
- **WHEN** a test client requests the page of a task one of whose steps was removed
- **THEN** its history widget holds a row with the subject `Stufe <n> entfernt` and an empty change cell

#### Scenario: Numbers, dates and text
- **WHEN** the sorting function of `lab.js` orders the keys `Abgabe`, `10`, `2026-01-02T09:15`, `–`, `-3,5`, `01.01.2026`, an empty key and `2` ascending, and then descending
- **THEN** the order is `-3,5`, `2`, `10`, `01.01.2026`, `2026-01-02T09:15`, `Abgabe`, `–`, the empty key, and then `Abgabe`, `2026-01-02T09:15`, `01.01.2026`, `10`, `2`, `-3,5`, `–`, the empty key

#### Scenario: Equal keys keep their order
- **WHEN** the sorting function orders the keys `b`, `a`, `b` and `a` ascending
- **THEN** the order is the second, the fourth, the first and the third

#### Scenario: Server order without the script
- **WHEN** a test client requests the page of an item with three movements booked in the order of the dates 2026-03-01, 2026-01-15 and 2026-02-10
- **THEN** its movements table carries `data-sortable` and an `id`, no header carries `aria-sort`, its rows run newest booking first, 2026-02-10, 2026-01-15, 2026-03-01, and each date cell's `data-sort` is its ISO date

### Requirement: Back links
Each of these record pages SHALL begin its own content with a `p.lab-back`, after the notices of the page shell (the demo note and the messages, Page shell) and before its `h1`, holding one link to the list the record belongs to, whose text is that list's heading, preceded by an arrow `←` hidden from assistive technology:

| Page | Link | Text |
|---|---|---|
| an item, `/lab/inventory/items/<id>/` | `/lab/inventory/end-products/` | `Endprodukte` (`End products`) |
| a batch, `/lab/inventory/batches/<id>/` | `/lab/inventory/batches/` | its list's heading |
| a vessel, `/lab/inventory/vessels/<id>/` | `/lab/inventory/vessels/` | its list's heading |
| a delivery note, `/lab/inventory/deliveries/<id>/` | `/lab/inventory/deliveries/` | its list's heading |
| a task, `/lab/tasks/<number>/` | `/lab/tasks/` | its list's heading |
| a substance, `/lab/registry/substances/<key>/` | `/lab/registry/` | `Substanzen` (`Substances`) |
| a notebook, `/lab/journal/<code>/` | `/lab/journal/` | `Laborjournale` (`Lab notebooks`) |

A list's heading is the `h1` of its page in the same language. The back link is the page's only link to that list outside the navigation and the section tabs; the notebook page's former plain link to `/lab/journal/` is gone.

#### Scenario: Back links match their lists
- **WHEN** the demo data set is written and a test client requests one page of each kind in the table, and each list page the links lead to
- **THEN** each record page has exactly one `p.lab-back`, after the demo note and before its `h1`, whose link leads to the stated list and whose text, without the arrow, equals that list page's `h1`, and the arrow carries `aria-hidden="true"`
- **AND** outside the navigation and the section tabs, each record page has exactly one link to its list, the back link

#### Scenario: English back links
- **WHEN** a test client with the interface language English requests one page of each kind in the table, and each list page
- **THEN** each back link's text, without the arrow, equals the English list page's `h1`, `End products` and `Substances` among them

### Requirement: Live lists
A list page whose spec opts into live updates SHALL keep its filter form as a complete GET form with a submit button so it works without scripts, and wire that form with HTMX (`hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers bound only to the list's own controls with at most one `change` clause per form, `hx-target`, `hx-select`, `hx-swap="morph:outerHTML"`, and disjoint `hx-select-oob` entries using `:morph` for dependent counts, details, and hidden filter state) so changing filters or typing in a search field updates the list in place without a full-page reload. All live controls and split-view row detail requests on the page SHALL share `hx-sync="#main:replace"` so the latest user action aborts any in-flight request, any pending debounced search trigger older than a newer `#main:replace` action SHALL be cancelled before aborting that newer action, and modified or non-primary clicks on live `a[href][hx-get]` links SHALL fall through to native browser navigation. The page shell's `meta` `htmx-config` SHALL set `historyCacheSize` to `0` and `refreshOnHistoryMiss` to `true` so browser Back and Forward reload the full page cleanly. Every live list view SHALL return the complete page for plain GET requests and for HTMX history restores (`HX-History-Restore-Request: true`), vary on `HX-Request` and `HX-History-Restore-Request`, and answer non-restore HTMX requests with `HX-Push-Url` set to the canonical list URL reflecting the cleaned active filters and, on a split-view list, the resolved `selected` parameter (omitted when the list is empty). A split-view detail endpoint SHALL continue returning only its `#item-detail` fragment for HTMX requests and redirecting non-HTMX requests, and SHALL set `HX-Replace-Url` on HTMX responses to the list URL carrying the active filter query from a same-host `HX-Current-URL` (falling back to the request query where the endpoint carries filters, else none) with `selected` naming the requested record, varying on `HX-Request` and `HX-Current-URL`.

#### Scenario: Live list filter request and history restore
- **WHEN** a test client requests a live list with `HX-Request: true` and active filter parameters, once again with `HX-History-Restore-Request: true`, and once without HTMX headers
- **THEN** all three answer 200 with the complete list markup and carry `HX-Request` and `HX-History-Restore-Request` in `Vary`, only the first carries `HX-Push-Url` set to the canonical URL, the form keeps `method="get"`, its `action`, and a submit button, and `meta` `htmx-config` sets `historyCacheSize` to `0` and `refreshOnHistoryMiss` to `true`

#### Scenario: Split-view detail response sets HX-Replace-Url
- **WHEN** a test client requests a split-view detail endpoint with `HX-Request: true` and a same-host `HX-Current-URL` carrying active filters, and once with a foreign-host `HX-Current-URL`
- **THEN** both answer 200 with only the single `#item-detail` element and vary on `HX-Request` and `HX-Current-URL`, the first sets `HX-Replace-Url` to the list URL keeping the active filters with `selected` updated to the requested record, and the second ignores the foreign host's query

