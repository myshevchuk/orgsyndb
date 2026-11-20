## MODIFIED Requirements

### Requirement: Application project
`webapp/` SHALL hold a Django project: `pyproject.toml`, declaring the Python it requires and naming Django, django-simple-history, psycopg, gunicorn and whitenoise as dependencies; `uv.lock`; `manage.py`; and the packages `orgsyndb_web`, which holds the settings, the URLs and the page shell, `accounts` and `tasks`. The application's tests live in `webapp/tests/` as `unittest.TestCase` classes, and `uv run pytest` in `webapp/` runs them. A `pytest` run at the repository root without arguments collects only `tests/`, so the program's suite needs no Django. Nothing under `tools/` imports from `webapp/`.

#### Scenario: Project file
- **WHEN** a test reads `webapp/pyproject.toml`
- **THEN** `requires-python` is set and the dependencies name the five packages

#### Scenario: Root suite leaves the application out
- **WHEN** `pytest --collect-only -q` runs at the repository root
- **THEN** no collected test lies under `webapp/`

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
