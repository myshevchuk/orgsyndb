## Context

The lab app holds every account (web-app "Accounts and sign-in"); user
names already follow Forgejo's rule and are fixed once set. The
deployment runs `builder`, `web` (Caddy), `db`, `app` and `backup`
(container-deployment). Draft 07 puts Forgejo at `/git/` on the same
origin, signs people in to it through the lab app, keeps its data in
a second database on the same PostgreSQL server, and blocks a
deactivated account there. A spike against Forgejo 15.0.11 (rootless
image), and before it 16.0.7, settled how it behaves; its findings are
cited below.

## Goals / Non-Goals

**Goals:**

- Forgejo runs in the deployment and signs people in only through the
  lab app, with an account per lab account, bound by the account's id.
- Deactivating a lab account blocks its Forgejo account as soon as
  Forgejo answers; until then staff are warned, and one command
  catches up.

**Non-Goals:**

- The collection's repository in Forgejo, the gate, the push log and
  the mirror: the next change.
- Forgejo's data in the backup: a change after that.
- The CMS, and Forgejo admin rights for lab staff.
- Isolating Forgejo from the lab app in the browser (see Risks).

## Decisions

### Forgejo 15 LTS

Forgejo 16 left support on 2026-10-29; 15 is the long-term release,
supported until 2027-07-15, and 17 only until 2027-01-28. The image is
`codeberg.org/forgejo/forgejo:15.0.11-rootless`. Every behaviour below
was checked against it.

### The provider is django-oauth-toolkit

An OpenID Connect provider is real work and easy to get subtly wrong;
django-oauth-toolkit provides one for Django 6.0 (authorization code
flow, ID tokens, user info, discovery, keys). The lab app registers
one application, Forgejo: confidential, authorization code, RS256,
redirect URI `<ORGSYNDB_URL>/git/user/oauth2/lab/callback`,
`skip_authorization` on, so a signed-in person goes straight back to
Forgejo. PKCE, which the toolkit requires by default, is not required
of this client: Forgejo 15 sends no code challenge (spike), and the
client authenticates with its secret. `manage.py forge_client` creates
or updates the application from `ORGSYNDB_FORGE_CLIENT_SECRET` and
does nothing without it; the image's command runs it after `migrate`.

The RS256 key comes from `ORGSYNDB_OIDC_KEY`, a PEM private key
encoded in base64 on one line, since an env file holds one line per
setting. Without it the provider is off: its paths answer 404.

### Claims

`sub` is the account's primary key as text: Forgejo keeps it as the
account's login name and finds the account by it at every sign-in
(spike: the same subject with another name, email and full name signs
in to the same account and changes none of them). `nickname` and
`preferred_username` are the user name; Forgejo 15 names a new account
after `nickname` (spike: it ignores `USERNAME = preferred_username`),
and lab names follow its rule, so it reshapes none. `name` is the
display name and `email` the address. Scopes: `openid profile email`.

### Email

Forgejo creates no account without an address (spike: it sends the
person to its link-account page) and takes each address once (spike: a
second account with a taken address gets a server error). So a lab
account's address is unique regardless of case when set, and the
authorization page refuses an account without one with a page saying
that staff must give it an address. Requiring an address of every
account would also bind accounts that never use Forgejo, such as
`mwolf`.

Forgejo does not update an account's address or full name at sign-in
(spike), so the app sends them: saving an account whose address or
display name changed sets both on its Forgejo account, as blocking
does (below). Otherwise an address given up in the lab would stay
taken in Forgejo.

### Reserved user names

Forgejo refuses some names (`admin`, `api`, `user`, `explore` and
others, regardless of case) and names ending in `.keys`, `.gpg`,
`.rss`, `.atom` or `.png` (spike), and the admin account the app uses
is called `orgsyndb`. A lab user name that Forgejo would refuse, or
`orgsyndb`, is refused, so that every lab account can have its Forgejo
account. The names and suffixes live in `accounts/` as constants
copied from Forgejo 15's source.

### Split discovery

The browser reaches the app at the public address, Forgejo reaches it
on the compose network, and on the test server, behind an SSH tunnel,
the public address is `http://localhost:8080`, which means something
else inside a container. So `OIDC_ISS_ENDPOINT` is `<ORGSYNDB_URL>/lab/o`,
which makes every ID token's `iss` the public issuer whichever host
the token was requested through, and the app's own discovery view
names the issuer and the authorization endpoint under `ORGSYNDB_URL`
and the token, user-info and keys endpoints under
`ORGSYNDB_APP_INTERNAL_URL` (`http://app:8000` by default), which
only servers call. Forgejo's source reads the discovery document from
the internal address, which `ORGSYNDB_ALLOWED_HOSTS` then lists
(`app`). Forgejo's OpenID client compares the token's issuer with the
discovery document's and reads each endpoint as given.

### Forgejo's configuration

Settings that are constants are environment variables in
`compose.yaml` (`FORGEJO__section__KEY`): PostgreSQL database `forge`
at `db` as role `forge`, `INSTALL_LOCK`, `DISABLE_REGISTRATION` and
`ALLOW_ONLY_EXTERNAL_REGISTRATION` (spike: auto-registration still
works), `ENABLE_AUTO_REGISTRATION`, `ACCOUNT_LINKING = disabled`
(spike: a new subject whose name is taken gets no account and binds
to none), `ENABLE_INTERNAL_SIGNIN = false` (spike: no password form),
the built-in SSH server on port 2222. Compose substitutes `${...}`
only from the shell and the project's `.env`, not from a service's
`env_file`, so settings derived from `orgsyndb.env` are made at start
by `deploy/forge/forge-start`, the service's entrypoint: it exports
`FORGEJO__server__ROOT_URL` as `<ORGSYNDB_URL>/git/` and
`FORGEJO__database__PASSWD` as `FORGE_DB_PASSWORD`, then runs the
image's own entrypoint. Caddy strips `/git` and forwards to
`forge:3000`.

`forge-db` (from `postgres:18`, run once before `forge`) creates the
role and the database `forge` when they are missing, reading its
passwords from `orgsyndb.env` at run time, so an existing database
volume gains them too. `deploy/forge/forge-setup`, run with
`docker compose exec forge`, creates the admin account `orgsyndb` with
`ORGSYNDB_FORGE_PASSWORD` and registers or updates the source `lab`
with the internal discovery URL, the client id `forgejo` and the
secret; it may run again. Forgejo fetches the discovery document when
the source is added or updated, so the app must be up with its key
set first.

### Keeping Forgejo's accounts in line

Saving an account whose `is_active`, address or display name changed
sets, on its Forgejo account (found through the admin API by its
login name among the accounts that are not local: the API names no
source by name, and a failed attempt to add `lab` uses up an id, so
`lab` need not be 1), `prohibit_login` to the opposite of `is_active`, the
email and the full name, using `ORGSYNDB_FORGE_URL` (the internal
address of Forgejo's API) and basic authentication as `orgsyndb`
(spike: basic authentication works with the sign-in form off). The
spike showed that the block refuses pushes with access tokens and SSH
keys made before it, and that repository pages answer "Account is
suspended" even to a session made before; so the block keeps tokens
and keys, and reactivating makes them work again (spike). Draft 07
removed them; blocking alone is reversible and enough. An account that
never signed in to Forgejo has nothing to change. When Forgejo cannot
be reached the save still happens, since the lab account is the
authority, and the admin shows a warning naming `forge_accounts`,
which sets every Forgejo account of the source to its lab account and
may run any time. Until it runs, a deactivated account's tokens and
keys still push. Without `ORGSYNDB_FORGE_URL` nothing is called.

A deactivated account cannot sign in to the lab app, and Django drops
its existing session, so it cannot authorize Forgejo either; the spike
found that Forgejo's own block does not stop a sign-in through the
source, so this refusal is the lab app's to make.

### After the commit, from the stored row

The call to Forgejo runs once the save's transaction has committed
(`transaction.on_commit`), so a save that is rolled back changes
nothing there, and it sends the account as stored then, so a partial
save never sends attributes it did not write. The admin's warning
follows from that call's outcome. An emptied address is replaced in
Forgejo by `<user name>@noreply.localhost`, which frees the old one,
since Forgejo refuses an empty address. `forge_accounts` gives out an
address only once no other Forgejo account holds it, parking an
account on its placeholder address to break a swap.

### Cookies

The lab app's session and CSRF cookies are scoped to `/lab/`, so that
Forgejo's server, on the same host, does not receive them.

## Risks / Trade-offs

- [Same origin] Forgejo shares the lab app's browser trust boundary: a
  script injected into a Forgejo page could request lab pages with the
  person's session, read their CSRF tokens and post changes. Cookie
  paths do not isolate pages of one origin. Draft 07 chose one origin
  for the CMS and Ketcher, and the authors are the lab's own people. →
  Forgejo sanitizes rendered content and serves raw files with a
  sandboxing policy; a separate origin remains possible later at the
  cost of a second host name and a second TLS certificate.
- [Untested end to end] The split discovery, Caddy's sub-path and the
  PostgreSQL database were not part of the spike. → The test server
  runs the checks in task 3.2 before the change is archived.
- [The gate's API answer] Forgejo 15 answers a commit refused by a
  pre-receive hook through its API with 500 and an empty message
  (spike); this matters to the CMS, not here.
- [Pinned version] → The image tag is one line to raise; the next LTS
  is 19, in April 2027.
