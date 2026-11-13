## Why

Draft 07 moves the collection's home to a Forgejo instance on the
server, which clones and later the CMS push to. Each person keeps one
account, in the lab app: Forgejo signs people in through it by OpenID
Connect, creates the matching account at the first sign-in and binds
it to the lab account's id, and a deactivated lab account is blocked
in Forgejo. This change brings Forgejo into the deployment with that
sign-in; the collection moves into it in a later change.

## What Changes

- The lab app becomes an OpenID Connect provider with one client,
  Forgejo: discovery, authorization, token, user info and keys under
  `/lab/o/`. A signed-in person passes through without a consent page.
  The ID token's subject is the account's id; it also carries the
  user name, the name and the email address. The lab's cookies are
  scoped to `/lab/`.
- Accounts: an email address is unique regardless of case, and signing
  in to Forgejo needs one. A user name may not be one Forgejo
  reserves.
- Deactivating an account blocks its Forgejo account through
  Forgejo's admin API, and reactivating it lifts the block; a changed
  address or name is sent too;
  `manage.py forge_accounts` brings every account in line.
- The deployment gains `forge` (Forgejo 15 LTS, rootless image) with its own
  database `forge` on the PostgreSQL server, created by a one-shot
  `forge-db`; Caddy serves it at `/git/`; a start script supplies the
  settings derived from `orgsyndb.env`, and a setup script registers the
  lab app as the sign-in source and creates the admin account the app
  uses. New settings: `ORGSYNDB_URL`, `ORGSYNDB_OIDC_KEY`,
  `ORGSYNDB_FORGE_CLIENT_SECRET`, `ORGSYNDB_FORGE_URL`,
  `ORGSYNDB_FORGE_PASSWORD`, `FORGE_DB_PASSWORD`.
- Demo accounts get email addresses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: accounts (email, reserved names), the OpenID provider,
  Forgejo accounts.
- `container-deployment`: the `forge` and `forge-db` services, the
  `/git/` route, the setup script, the settings, the image's command.
- `lab-demo`: the demo accounts' email addresses.

## Impact

- New dependency: `django-oauth-toolkit` (OpenID Connect provider).
- Changed: `webapp/accounts/` (model rule, admin, the provider's
  claims and views, the Forgejo client, commands), `webapp/orgsyndb_web/`
  (settings, URLs), `webapp/demo/`, the tests of each;
  `deploy/compose.yaml`, `deploy/docker/Caddyfile`,
  `deploy/orgsyndb.env.example`, `deploy/webapp/Dockerfile`, new
  `deploy/forge/`; root tests of the deployment;
  `webapp/docs/database-schema.html`, regenerated.
- Docs: README (container deployment, accounts, Forgejo set-up).
- Test server: new settings and `forge-setup`; `demo_data --replace`
  for the demo's email addresses.
