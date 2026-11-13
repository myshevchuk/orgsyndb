## Why

Since `forge-accounts` Forgejo runs beside the lab app and signs
people in through it, but the collection still lives on an outside
remote that the builder polls, and nothing stops a commit that fails
the collection's rules from reaching `main`: the build merely fails
afterwards. Draft 07 makes Forgejo the collection's home, every lab
account an author, and puts a gate in front of `main` that refuses a
commit the import would refuse, with every error, back to whoever
pushed.

## What Changes

- `forge-setup` also creates the organisation `lab`, its team
  `authors` with write access to the public repository
  `lab/collection`, with `main` protected, and installs the gate as the
  repository's pre-receive hook; the source `lab` maps the `groups`
  claim to the team. People cannot rename themselves in Forgejo.
- The lab app's ID token carries `groups: ["authors"]` for every
  account, so the first sign-in makes it an author.
- The gate: a push to `main` sends the new tip with its history to the
  builder's check, which checks it out as a build would, validates it
  and builds its manifest against a fresh snapshot, with tooling and
  files of its own, and asks the app to check it as an import, without
  recording one. Any error, or no answer in time,
  refuses the push with the errors.
- The app: `POST /lab/collection/check/`, with the builder token, runs
  the import checks on the collection half of a manifest.
- The builder serves the check on the compose network, and fetches the
  collection from Forgejo (`ORGSYNDB_COLLECTION_REPO`).
- New settings: `ORGSYNDB_GATE_TOKEN`, `ORGSYNDB_GATE_URL`,
  `ORGSYNDB_CHECK_URL`, `ORGSYNDB_GATE_TIMEOUT`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `collection-import`: the check path.
- `container-deployment`: Forgejo's repository, team and gate; the
  builder's check server; the collection fetched from Forgejo; Caddy
  hiding the check path.
- `web-app`: the `groups` claim.

## Impact

- Changed: `deploy/docker/orgsyndb-deploy` (check server),
  `deploy/docker/Caddyfile`, `deploy/compose.yaml`,
  `deploy/orgsyndb.env.example`, `deploy/forge/forge-setup`, new
  `deploy/forge/gate`; `webapp/collection/` (check view),
  `webapp/accounts/oidc.py` (claim); the tests of each.
- Docs: README (container deployment, Forgejo set-up, moving the
  collection into Forgejo, what a refused push shows).
- Test server: rebuild, new settings, `forge-setup` again, then push
  the collection to `lab/collection` once.
