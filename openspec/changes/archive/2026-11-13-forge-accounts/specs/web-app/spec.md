## MODIFIED Requirements

### Requirement: Accounts and sign-in
The user model SHALL be `accounts.User`, Django's user with a user name of at most 40 letters and digits, single `.`, `-` or `_` allowed between them, as Forgejo takes user names, unique regardless of case, as Forgejo's are, fixed once the account exists, since procedure files name their authors by it, and with an added `initials`: one to five letters or digits, unique regardless of case, stored in upper case. A user name equal, regardless of case, to one Forgejo 15 reserves for itself, one ending in `.keys`, `.gpg`, `.rss`, `.atom` or `.png`, which Forgejo refuses too, or `orgsyndb`, the name of the Forgejo account the application uses (Forgejo accounts), is refused, so that every account can have its Forgejo account. An account's email address may be empty and is otherwise unique regardless of case, since Forgejo takes each address once. A user's display name is the full name, or the user name when that is empty. There is no page for creating one's own account; staff create accounts in the admin. A person signs in with user name and password, signs out with a POST, and changes their own password at `/lab/accounts/password/`. An account without a usable password cannot sign in and can still be named on records. The session and CSRF cookies have the path `/lab/`, so that Forgejo, served from the same host, does not receive them (container-deployment "Forgejo").

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
Pages that show data SHALL need no sign-in. Every page and action that changes data needs a signed-in user: a request without one, GET or POST, redirects to the sign-in page with `next` set to the requested path and changes nothing. The exceptions are the manifest path, which the builder signs with a service token (collection-import "Manifest"); the ID path, which needs an account's access token, a signed-in session not being enough (collection-import "Issued IDs"); and the OpenID provider's token and user-info paths, which authenticate the client or the token they are given (OpenID provider); none of these redirects. The admin needs staff status. The views offer no deletion, except that a user revokes their own access tokens (Access tokens); staff delete in the admin.

#### Scenario: Form without sign-in
- **WHEN** a test client that is not signed in requests and posts `/lab/tasks/new/`
- **THEN** both redirect to `/lab/accounts/login/?next=/lab/tasks/new/` and no task exists

## ADDED Requirements

### Requirement: OpenID provider
The application SHALL be an OpenID Connect provider, under `/lab/o/`, for one client, Forgejo, when `ORGSYNDB_OIDC_KEY` holds a PEM-encoded RSA private key in base64; without it every path under `/lab/o/` answers 404. `manage.py forge_client` creates or updates the client from `ORGSYNDB_FORGE_CLIENT_SECRET`, and does nothing without it: client id `forgejo`, confidential, the authorization code flow without PKCE, which Forgejo does not send, ID tokens signed with RS256, the one redirect URI `<ORGSYNDB_URL>/git/user/oauth2/lab/callback`, and no consent page. The issuer is `<ORGSYNDB_URL>/lab/o` in every ID token, whichever host the token was requested through.

`/lab/o/.well-known/openid-configuration` names the issuer `<ORGSYNDB_URL>/lab/o` and the authorization endpoint `<ORGSYNDB_URL>/lab/o/authorize/`, which the person's browser reaches, and the token, user-info and keys endpoints under `ORGSYNDB_APP_INTERNAL_URL`, `http://app:8000` by default, at `/lab/o/token/`, `/lab/o/userinfo/` and `/lab/o/.well-known/jwks.json`, which only Forgejo's server calls; it lists the scopes `openid`, `profile` and `email`.

The authorization endpoint needs a signed-in user, as every page that changes data does (Permissions). For a signed-in account with an email address it sends the person back to the redirect URI with a code at once. For one without, it answers with the page `Kein Zugang zu Forgejo` (`No access to Forgejo`), saying that staff must give the account an email address first, and sends nobody back. The ID token and the user info carry `sub`, the account's primary key as text, `nickname` and `preferred_username`, both the user name, `name`, the display name, and `email`, the email address. An inactive account cannot sign in (Accounts and sign-in), so it authorizes nothing; and a code, a refresh token or an access token issued to an account that has since been deactivated is refused, at the token and user-info endpoints alike.

#### Scenario: Discovery
- **WHEN** the provider is on with `ORGSYNDB_URL=http://localhost:8080` and a test client requests `/lab/o/.well-known/openid-configuration`
- **THEN** the issuer is `http://localhost:8080/lab/o`, the authorization endpoint `http://localhost:8080/lab/o/authorize/`, the token endpoint `http://app:8000/lab/o/token/` and the scopes include `openid`, `profile` and `email`

#### Scenario: Signing in to Forgejo
- **WHEN** `klehmann`, with the address `kl@example.org`, is signed in and the client `forgejo` requests the authorization endpoint with the scopes `openid profile email` and its redirect URI and no code challenge, and then posts the code it received to the token endpoint with its secret, with the host `app:8000`
- **THEN** the first answer redirects to the redirect URI with a code and the given state, and the ID token, signed with RS256, has the issuer `http://localhost:8080/lab/o`, the audience `forgejo`, `sub` the account's primary key, `nickname` and `preferred_username` `klehmann`, `name` `Katrin Lehmann` and `email` `kl@example.org`, as has the user info for the access token

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
