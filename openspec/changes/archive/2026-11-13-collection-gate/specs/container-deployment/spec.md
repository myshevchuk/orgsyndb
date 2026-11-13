## MODIFIED Requirements

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, answer `404` for every path beginning with `/lab/collection/manifest` or `/lab/collection/check`, forward `/lab/` and every other path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default, and forward every path below `/git/`, with `/git` taken off, to Forgejo at `ORGSYNDB_FORGE_UPSTREAM`, `forge:3000` by default, redirecting `/git` to `/git/`. It sets the header `Cache-Control: no-cache` on every response but Forgejo's, which sets its own, and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process and `ORGSYNDB_LAB=true` in its environment, so that the site it builds links the lab application's views, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`;
- `db`, from `postgres:18`, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb` and starting once `db` is healthy;
- `backup`, from `postgres:18`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`;
- `forge-db` and `forge` (Forgejo).

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, `ORGSYNDB_ALLOWED_HOSTS`, with `app` among the hosts, `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token, and the settings of Forgejo with how to generate each secret. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*`, `reverse_proxy`, `/lab/collection/manifest*` and `/lab/collection/check*`, each answered with `404` ahead of the `/lab/*` route, and `/git/*` with `handle_path`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app`, `backup`, `forge-db` and `forge`, `builder` runs `orgsyndb-deploy run`, reads the settings and has `ORGSYNDB_LAB` set to `true`, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, and `app` receives the example's `ORGSYNDB_DATABASE_URL`

### Requirement: Forgejo
`deploy/compose.yaml` SHALL run Forgejo as `forge`, from `codeberg.org/forgejo/forgejo:15.0.11-rootless`, keeping its data in the volume `forge`, with port 2222, its SSH server, published, starting once `forge-db` has completed. Its settings come from environment variables, none from a hand-edited file and none substituted by Compose from the shell: as constants in `compose.yaml`, the PostgreSQL database `forge` on `db` as the role `forge`, the installation locked, registration only through an external source, an account created at the first sign-in through one, named by the `nickname` claim, no linking to an existing account, no password sign-in form, the built-in SSH server on port 2222, and `USER_DISABLED_FEATURES` `change_username,deletion`, so that a Forgejo account keeps the lab user name; and, from `orgsyndb.env` at start, the root URL `<ORGSYNDB_URL>/git/` and the database password `FORGE_DB_PASSWORD`, which `deploy/forge/forge-start`, mounted read-only and run as the service's entrypoint, exports before it runs the image's own entrypoint.

`forge-db`, from `postgres:18`, runs once after `db` is healthy and creates the role `forge` with `FORGE_DB_PASSWORD` and the database `forge` it owns when either is missing, so that a database volume made before gains them; it changes nothing that exists.

`deploy/forge/forge-setup`, mounted read-only into `forge` as well and run with `docker compose exec forge`, creates the admin account `orgsyndb` with `ORGSYNDB_FORGE_PASSWORD` when it is missing, adds or updates the OpenID Connect source `lab` with the discovery URL `${ORGSYNDB_APP_INTERNAL_URL}/lab/o/.well-known/openid-configuration`, the client id `forgejo`, `ORGSYNDB_FORGE_CLIENT_SECRET`, the scopes `openid profile email`, the group claim `groups` mapped to the team `authors` of the organisation `lab`, with membership removed when the claim no longer names it; creates, when missing, the public organisation `lab`, its team `authors`, and the public repository `lab/collection` with the default branch `main`, giving the team write access to that repository alone; protects `main`, so that Forgejo refuses a force push to it; and links `deploy/forge/gate` into the repository's `hooks/pre-receive.d/` as `orgsyndb-gate` (Gate). Run again it changes only what differs. `deploy/orgsyndb.env.example` names `ORGSYNDB_URL`, the address people reach the site at; `ORGSYNDB_OIDC_KEY`, with the command that generates it; `ORGSYNDB_FORGE_CLIENT_SECRET`, `ORGSYNDB_FORGE_PASSWORD` and `FORGE_DB_PASSWORD`, each with how to generate it; `ORGSYNDB_FORGE_URL`, `http://forge:3000/api/v1` by default; `ORGSYNDB_GATE_TOKEN`, with how to generate it; and, as `ORGSYNDB_COLLECTION_REPO`, `http://forge:3000/lab/collection.git`, the repository `forge-setup` creates.

#### Scenario: Forgejo's service
- **WHEN** a test runs `docker compose config` as in Compose file
- **THEN** with no `ORGSYNDB_` or `FORGE_` variable in the shell, `forge` uses the pinned image, has `forge-start` as its entrypoint, mounts the volume `forge`, publishes 2222, depends on `forge-db` completing, and its environment sets the database `forge` on `db`, `ENABLE_AUTO_REGISTRATION`, `ACCOUNT_LINKING` `disabled` and `ENABLE_INTERNAL_SIGNIN` `false`, and the output holds no unresolved or empty substitution; `forge-db` depends on `db` being healthy and does not restart

#### Scenario: The start script
- **WHEN** a test runs `deploy/forge/forge-start` with `ORGSYNDB_URL=http://localhost:8080` and `FORGE_DB_PASSWORD=x` in its environment and a stand-in for the image's entrypoint
- **THEN** the stand-in runs with `FORGEJO__server__ROOT_URL=http://localhost:8080/git/` and `FORGEJO__database__PASSWD=x` in its environment

#### Scenario: Creating the database once
- **WHEN** a test runs `forge-db`'s script against a PostgreSQL server twice, skipping without one
- **THEN** after the first run the role and the database `forge` exist, and the second run succeeds and changes nothing

#### Scenario: The set-up script
- **WHEN** a test reads `deploy/forge/forge-setup`
- **THEN** it creates the admin `orgsyndb`, the organisation `lab`, the team `authors`, the repository `lab/collection` and the protection of `main` each only when missing, adds the source `lab` when missing and updates it otherwise, with the discovery URL, the client id `forgejo`, the scopes `openid profile email` and the group claim `groups` mapped to the team `authors`, and links the gate into `hooks/pre-receive.d/`

## ADDED Requirements

### Requirement: Gate
`deploy/forge/gate` SHALL be the pre-receive hook of `lab/collection`. For each update of `refs/heads/main` that does not delete it, it sends the new commit with its history, the output of `git pack-objects --stdout --revs` given the commit, by `POST` to `ORGSYNDB_GATE_URL`, `http://builder:8091/check` by default, with the header `X-Orgsyndb-Commit: <commit>` and `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, waiting at most `ORGSYNDB_GATE_TIMEOUT` seconds, 150 by default, a time Forgejo waits for a pre-receive hook over HTTPS and SSH alike. On `200` the update passes. On any other answer, or none in time, the hook writes `Gate: <reason>` and then each line of the answer's body to its standard error, which Forgejo shows the pusher, and exits non-zero, so that Forgejo refuses the push. Updates of other refs pass unchecked. Without `ORGSYNDB_GATE_TOKEN` the hook refuses every update of `main`, saying that the gate is not configured.

`orgsyndb-deploy run` SHALL serve `POST /check` on port 8091 for the hook from a thread beside its cycles, when `ORGSYNDB_GATE_TOKEN` is set. A request without `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, compared in constant time, answers 401; another path or method answers 404 or 405; a body over 200 MB answers 413; one without a commit id of 40 hexadecimal digits in `X-Orgsyndb-Commit` answers 400. One check runs at a time: a request while one runs answers 503 at once, before its body has arrived, saying that the gate is busy and to push again; the server then discards what arrives of that body for at most 2 seconds and closes the connection.

A check shares no file with the cycle. It has its own clone of the application, `<data>/check/app/`, which it fetches from the cycle's clone and checks out, keeping ignored files, and into which it copies the cycle clone's tool caches `.emacs-batch/` and `.tools/` when they are missing, so that a check needs no network access the build does not, at the application commit of the published release the saved state names, or the cycle's checked-out commit when none is published; and its own directory, removed when the check ends, into which it fetches the snapshot as a cycle does (Update cycle), indexes the pack into a new repository, points `main` at the commit and, unless the commit's tree holds a symbolic link anywhere, checks it out. A tree with a symbolic link is refused with `422` and `symbolic links are not allowed: <path>` for each, before anything is checked out, since the tools would follow a link out of the checkout. It then runs, from its clone, `tools/orgsyndb -C <checkout>/<ORGSYNDB_COLLECTION_PATH> validate` and `manifest`, with `ORGSYNDB_REGISTRY` naming its snapshot, each in a new process group. When a step exits non-zero, or the pack does not hold the commit, the answer is `422` with the step's error lines (the lines holding `: error: `, or its last line when none does). Otherwise it posts the collection half of the manifest (`language`, `procedures`, `sequences` and `deleted`) to `ORGSYNDB_CHECK_URL`, `http://app:8000/lab/collection/check/` by default, with the `Host` and `Authorization` headers of a manifest (Manifests), and answers `422` with the errors the application returned, one per line, or `200` with an empty body when it returned none. When the snapshot cannot be fetched or the application gives no answer of status 200, the answer is `503` with the reason; an answer of any other status, even one in the 2xx range, is no verdict.

A check has one deadline, `ORGSYNDB_GATE_TIMEOUT` less 10 seconds after it starts: reading the request's body, fetching the snapshot, each step and the application's answer, each transfer as a whole, may take only the time left, and when the deadline passes the step's process group is killed and the answer is `503`, saying that the check took too long. On `SIGTERM` the main thread stops the server, kills a running check's process group and removes its directory before the program exits; signals are handled in the main thread only.

#### Scenario: A valid push
- **WHEN** a test runs the check server with a fake application that finds no errors and posts the pack of a valid collection's commit with the token
- **THEN** the answer is 200, the fake received the manifest's collection half with the builder token, and no check directory remains

#### Scenario: Files a committed .gitattributes leaves out of an archive
- **WHEN** the commit holds a `.gitattributes` marking an invalid procedure `export-ignore`
- **THEN** the answer is 422 with the validator's error for that procedure

#### Scenario: A symbolic link
- **WHEN** the commit holds `build/tmp` as a symbolic link to a directory outside the checkout
- **THEN** the answer is 422 with `symbolic links are not allowed: build/tmp`, no tool ran, and the directory the link names is untouched

#### Scenario: A collection that fails validation
- **WHEN** the commit holds a procedure with a field the vocabulary does not know
- **THEN** the answer is 422 and its body holds the validator's error line for that field, and the application received nothing

#### Scenario: A collection the import would refuse
- **WHEN** the fake application answers the check with the error `OSDB-0099: not issued`
- **THEN** the answer is 422 with that line

#### Scenario: Without the token
- **WHEN** a test posts a pack without a token, and with a wrong one
- **THEN** both answers are 401 and no check ran

#### Scenario: Busy
- **WHEN** a second check is posted while one is running
- **THEN** the second answers 503 at once, saying that the gate is busy

#### Scenario: A body that trickles
- **WHEN** `ORGSYNDB_GATE_TIMEOUT` is 12 and a client sends the body a byte a second
- **THEN** the answer is 503 within about 2 seconds, saying the check took too long

#### Scenario: Busy with a large body
- **WHEN** a second request arrives during a check and sends its large body slowly
- **THEN** its 503 busy answer arrives before its body has been sent

#### Scenario: An answer that is not 200
- **WHEN** the fake application answers the check with 202 and an empty `errors`
- **THEN** the answer is 503

#### Scenario: Tool caches
- **WHEN** the check clone is made while the cycle clone holds `.emacs-batch/` and `.tools/`
- **THEN** the check clone holds copies of both, and the export runs without fetching them

#### Scenario: Too slow
- **WHEN** `ORGSYNDB_GATE_TIMEOUT` is 12 and a step of the check hangs
- **THEN** the answer is 503 within about 2 seconds, saying the check took too long, the step's processes are gone and no check directory remains

#### Scenario: The cycle meanwhile
- **WHEN** a check runs while a cycle checks out another application commit in its own clone and rewrites its snapshot
- **THEN** the check's clone stays at its commit and its snapshot unchanged until the check ends

#### Scenario: The hook
- **WHEN** a test runs `deploy/forge/gate` with `sh`, inside a Git repository, against a fake check server, feeding it an update of `refs/heads/main`, then one of `refs/heads/draft`, and with the fake answering 200, then 422 with two lines, then nothing within a timeout of 1 second
- **THEN** the update of `main` passes on 200 and the fake received a pack holding the commit, its id in `X-Orgsyndb-Commit` and the token; the update of `refs/heads/draft` passes without a request; on 422 the hook exits non-zero and its standard error holds both lines; and without an answer it exits non-zero and says the gate gave no answer
