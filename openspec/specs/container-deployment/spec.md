# container-deployment Specification

## Purpose
Define the container deployment under `deploy/`: the image, the updater that keeps the site built from the collection's and the application's Git repositories, its releases, the web server and the Compose file.
## Requirements
### Requirement: Container image
`deploy/docker/Dockerfile` SHALL build an image from `fedora:44` that installs Python 3, Hugo, WeasyPrint, Emacs, Git, the SSH client and Caddy, and adds the user `orgsyndb` with UID 1000. Running as that user, it clones the application from the build argument `APP_REPO` at the branch or tag `APP_REF` (by default `https://github.com/myshevchuk/orgsyndb.git` and `main`) into `/opt/orgsyndb/app`, builds the demo collection there to fill `.emacs-batch/` and `.tools/`, removes the demo's build output, and writes `/opt/orgsyndb/image.json` holding `app_repo`, `app_ref` and `deploy_tree`, the Git tree id of the clone's `deploy/docker`. It installs `orgsyndb-deploy` and the Caddyfile from the clone, trusts repositories under `/srv/git/` for Git, runs as `orgsyndb`, declares `/var/lib/orgsyndb` a volume and runs `orgsyndb-deploy run` by default. `deploy/docker/` holds only `Dockerfile`, `Caddyfile` and `orgsyndb-deploy`.

#### Scenario: Image inputs
- **WHEN** a test lists `deploy/docker/` and reads its `Dockerfile`
- **THEN** the directory holds exactly those three files, and the Dockerfile names `fedora:44`, the six tools, `HEAD:deploy/docker` and `USER orgsyndb`

### Requirement: Updater program
`orgsyndb-deploy` SHALL be an executable Python program using only the standard library, with the subcommands `run` (the default), `sync`, `status`, `retry` and `help`. `sync` runs one cycle; `run` runs a cycle, waits `ORGSYNDB_INTERVAL` seconds or until SIGHUP, and repeats until SIGTERM, logging errors of a cycle without stopping. `status` prints the saved state as JSON; `retry` empties its list of failed combinations. It exits 0 on success, 1 on an error, writing `orgsyndb-deploy: error:` and a message to stderr, and 2 with a usage line on an unknown subcommand.

It reads `ORGSYNDB_COLLECTION_REPO` (required), `ORGSYNDB_COLLECTION_REF` (default `main`), `ORGSYNDB_COLLECTION_PATH` (a relative path without `..`, default the repository root), `ORGSYNDB_APP_UPDATE` (default true), `ORGSYNDB_APP_REPO` and `ORGSYNDB_APP_REF` (default the image's `app_repo` and `app_ref`), `ORGSYNDB_INTERVAL` (default 300, at least 10), `ORGSYNDB_PDF` (default false), `ORGSYNDB_KEEP_RELEASES` (default 2), `ORGSYNDB_BUILD_TIMEOUT` (default 3600, at least 60), `ORGSYNDB_REGISTRY_URL` (default `http://app:8000/lab/registry/snapshot.json`), `ORGSYNDB_MANIFEST_URL` (default `http://app:8000/lab/collection/manifest/`), `ORGSYNDB_BUILDER_TOKEN`, the token the application expects on a manifest (web-app "Settings from the environment"), and `ORGSYNDB_ALLOWED_HOSTS`, the host names the lab application accepts, which `orgsyndb.env` gives the builder as it gives `app`, and, for its paths, `ORGSYNDB_DATA` (default `/var/lib/orgsyndb`), `ORGSYNDB_APP` (default `/opt/orgsyndb/app`) and `ORGSYNDB_IMAGE_INFO` (default `/opt/orgsyndb/image.json`). A flag takes `true`, `false`, `yes`, `no`, `on`, `off`, `1` or `0`. A missing collection repository or a malformed value is an error naming the variable.

#### Scenario: Collection repository required
- **WHEN** a test runs `sync` without `ORGSYNDB_COLLECTION_REPO`
- **THEN** it exits 1 and stderr names `ORGSYNDB_COLLECTION_REPO`

#### Scenario: Malformed settings
- **WHEN** a test runs `sync` with `ORGSYNDB_INTERVAL=soon`, `ORGSYNDB_PDF=maybe` or `ORGSYNDB_COLLECTION_PATH=../x`
- **THEN** it exits 1 and stderr names the variable

#### Scenario: Standard library only
- **WHEN** a test compiles the program and collects its imports
- **THEN** it compiles, is executable, starts with `#!/usr/bin/env python3`, and imports only standard-library modules

### Requirement: Update cycle
A cycle SHALL fetch the branch or tag `ORGSYNDB_APP_REF` from `ORGSYNDB_APP_REPO` into the application's clone when application updates are on, and `ORGSYNDB_COLLECTION_REF` from `ORGSYNDB_COLLECTION_REPO` into `<data>/collection/`, creating that repository on first use. Each repository may be any URL or path Git fetches from. When the fetched application commit differs from the checked-out one and its `deploy/docker` tree differs from the image's `deploy_tree`, the cycle logs that it needs a new image and keeps the checked-out commit.

Next the cycle requests the lab application's snapshot at `ORGSYNDB_REGISTRY_URL`, sending as `Host` the first entry of `ORGSYNDB_ALLOWED_HOSTS` that is not `*`, with a leading `.` dropped, or `localhost` when there is none, with a timeout of 30 seconds, and on an answer of status 200 whose body is a snapshot (lab-registry "Snapshot") writes it to `<data>/registry.json`. When the request fails, or the answer is not a snapshot, it logs `cannot fetch the registry` and builds nothing: only the application can accept a build, and a kept copy cannot say which import it accepted last. The snapshot's `import` names the latest accepted import of the collection (lab-registry "Snapshot"); when its release is in `<data>/releases/` and `<data>/current` points elsewhere, the cycle points `current` at it. The registry's digest is part of every combination below, so that a changed registry is built and published like a new commit. Without `ORGSYNDB_BUILDER_TOKEN` the cycle logs that `ORGSYNDB_BUILDER_TOKEN` is not set and builds nothing.

The cycle then tries, in order, the new application commit if there is one and the checked-out one, each with the fetched collection commit and the registry. It stops at the first combination whose application commit, collection commit and digest are the latest accepted import's `tooling`, `commit` and `snapshot` and whose release is in `<data>/releases/`, and skips one that failed before. For any other it checks out both commits, keeping ignored files, and runs `<app>/tools/orgsyndb -C <collection>/<path> build`, or `pdf` when `ORGSYNDB_PDF` is true. It then runs `manifest` (Releases). Every run of `tools/orgsyndb` in the cycle, has `ORGSYNDB_REGISTRY` naming `<data>/registry.json` (compound-registry "Registry source"), so that the site and the manifest describe the registry the cycle fetched. When `<path>/orgsyndb.toml` is missing it logs `ORGSYNDB_COLLECTION_PATH` and builds nothing. A build or `manifest` that exits non-zero or exceeds the timeout fails; the cycle reports the failure to the application (Manifests), logs that the published site is unchanged and records the combination as failed. After the cycle the application's clone is at the commit of the published site, or at the commit it started from.

A collection that cannot be fetched is built from its last fetched commit, if any; an application that cannot be fetched stays at its commit.

#### Scenario: First publish
- **WHEN** a test runs `sync` once against a fake application that accepts every manifest
- **THEN** the published `index.html` comes from the application and collection commits, the state names both, and the application received one manifest with the trigger `catch-up`

#### Scenario: Nothing new
- **WHEN** a test runs `sync` twice without a new commit
- **THEN** the build ran once, there is one release, and the application received one manifest

#### Scenario: New collection commit
- **WHEN** the collection gains a commit between two runs of `sync`
- **THEN** the second run publishes it as a second release, sending a manifest with the trigger `commit` and the first import as its `base`

#### Scenario: Failed collection commit
- **WHEN** the collection gains a commit that fails to build, and `sync` runs twice
- **THEN** the published site is unchanged, the output says so, the build of that commit ran once and the application received it as a refused build with the build's error lines; a later good commit is published

#### Scenario: Application update
- **WHEN** the application gains a commit between two runs of `sync`
- **THEN** the second run publishes the site built with it, the clone is at that commit, and the ignored `.tools/` survives

#### Scenario: Broken application
- **WHEN** the application gains a commit that fails to build and the collection gains a good commit, and `sync` runs twice
- **THEN** the site of the new collection commit built with the previous application commit is published, the clone stays at the previous application commit, and the broken commit was built once; a later good application commit is published

#### Scenario: Application needing a new image
- **WHEN** the application gains a commit that changes `deploy/docker/`
- **THEN** `sync` logs `needs a new image`, builds nothing and keeps the application's commit

#### Scenario: Updates off
- **WHEN** `ORGSYNDB_APP_UPDATE=false` and both repositories gained a commit
- **THEN** the new collection commit is published with the old application commit

#### Scenario: Refs and collection path
- **WHEN** `ORGSYNDB_APP_REF` names a branch other than `main`, or `ORGSYNDB_COLLECTION_REF` and `ORGSYNDB_COLLECTION_PATH` name a branch and a subdirectory holding `orgsyndb.toml`
- **THEN** the published site comes from that branch and directory

#### Scenario: Missing settings file
- **WHEN** `ORGSYNDB_COLLECTION_PATH` names a directory without `orgsyndb.toml`
- **THEN** the output names `ORGSYNDB_COLLECTION_PATH`, and nothing is built or published

#### Scenario: Unreachable collection
- **WHEN** after a publish `ORGSYNDB_COLLECTION_REPO` names a missing repository
- **THEN** `sync` exits 0, logs `cannot fetch the collection`, builds nothing and keeps the site

#### Scenario: Retry
- **WHEN** a combination failed and `retry` runs
- **THEN** the state holds no failed combination and the next `sync` builds it again

#### Scenario: Registry change
- **WHEN** a test serves a snapshot, runs `sync`, changes the snapshot's digest, and runs `sync` again without a new commit
- **THEN** the second run publishes a second release, built with the new snapshot, sends a manifest with the trigger `registry`, and the state names its digest

#### Scenario: Host of the request
- **WHEN** a test runs `sync` with `ORGSYNDB_ALLOWED_HOSTS=lab.example.org,localhost` against a test server that records each request
- **THEN** the snapshot was requested with the `Host` header `lab.example.org`; with `ORGSYNDB_ALLOWED_HOSTS=*` it was requested with `localhost`, and with `.example.org` with `example.org`

#### Scenario: Registry unreachable
- **WHEN** after a publish the snapshot's address stops answering and the collection gains a commit, and `sync` runs; and separately `sync` runs on a fresh data directory with an address that never answers
- **THEN** both exit 0, log `cannot fetch the registry` and build nothing, and the first keeps the published site

#### Scenario: No token
- **WHEN** a test runs `sync` without `ORGSYNDB_BUILDER_TOKEN`
- **THEN** it exits 0, logs `ORGSYNDB_BUILDER_TOKEN`, and nothing is built or published

#### Scenario: The accepted release comes back
- **WHEN** after two publishes a test points `current` at the first release and runs `sync` without a new commit
- **THEN** `current` points at the second release, the one the latest accepted import names, and nothing is built

#### Scenario: Application update triggers a build
- **WHEN** the application gains a commit and nothing else changes
- **THEN** the next `sync` sends a manifest with the trigger `tooling`

### Requirement: Releases
A successful build SHALL be staged, with its `pdf/` when PDFs are on, in a new directory `<data>/releases/<serial>-<app>-<collection>`, the serial counting up from `000001` and the commits shortened to ten characters; when `<app>/tools/orgsyndb -C <collection>/<path> manifest`, run after the build, fails or exceeds the build timeout, the build counts as failed. Only once the application accepts the build's manifest (Manifests) SHALL the relative symlink `<data>/current` be replaced atomically to point to the release; a staged release it refuses or calls stale is removed, and one whose answer is lost is kept, so that a later cycle publishes it when the latest accepted import names it. After a publish and at the end of every cycle all releases are removed, with any partial copy, but the current one, the newest staged release whose answer was lost, and the `ORGSYNDB_KEEP_RELEASES` newest others. `<data>/state.json` records the published commits and release, the serial, and up to 50 failed combinations.

#### Scenario: Relative symlink
- **WHEN** a test runs `sync` once
- **THEN** `current` is a symlink with a relative target

#### Scenario: Pruning
- **WHEN** with `ORGSYNDB_KEEP_RELEASES=1` four collection commits are published
- **THEN** two releases remain and `current` points to the newest

#### Scenario: PDFs
- **WHEN** `sync` runs with `ORGSYNDB_PDF=true`
- **THEN** the build ran `pdf` and the release holds `pdf/`

#### Scenario: Failing manifest
- **WHEN** the fake `tools/orgsyndb` builds successfully but its `manifest` exits 1, or runs past `ORGSYNDB_BUILD_TIMEOUT`
- **THEN** `sync` publishes nothing, the release published before stays current, the application received a refused build, and the combination is recorded as failed

#### Scenario: Refused by the application
- **WHEN** the fake application answers a manifest `refused`
- **THEN** `sync` publishes nothing, removes the staged release, keeps the release published before, and records the combination as failed

#### Scenario: Stale
- **WHEN** the fake application answers a manifest `stale` once and then accepts
- **THEN** the first `sync` publishes nothing, removes the staged release and records no failed combination, and the next `sync` builds again and publishes

#### Scenario: Application unreachable
- **WHEN** the manifest address does not answer
- **THEN** `sync` exits 0, logs `cannot send the manifest`, publishes nothing and records no failed combination

#### Scenario: Accepted, answer lost
- **WHEN** the fake application accepts a manifest but closes the connection without answering, and `sync` runs twice
- **THEN** the first logs `cannot send the manifest` and keeps the published site; the second points `current` at the staged release, which the snapshot's `import` now names, and builds nothing

#### Scenario: A failed build reported late
- **WHEN** a commit fails to build while the manifest address does not answer, then the address answers again and `sync` runs once more
- **THEN** the first `sync` records no failed combination, and the second builds the commit again, reports it as refused and records it as failed

#### Scenario: New application whose manifest fails
- **WHEN** a new application commit builds but its `manifest` exits 1, while the checked-out one works
- **THEN** `sync` falls back to the checked-out commit and publishes its build

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

### Requirement: Application image
`deploy/webapp/Dockerfile` SHALL build an image from `fedora:44` that installs Python 3 and uv, copies `webapp/` and `site/assets/css/` from the build context, the repository root, installs the locked dependencies without the development ones, and collects the static files. It runs as the user `orgsyndb` with UID 1000 and exposes port 8000. Its command applies pending migrations, then runs `manage.py demo_data --if-empty`, which seeds an empty database when `ORGSYNDB_DEMO` is true and otherwise changes nothing (lab-demo "Demo data command"), then `manage.py forge_client`, which registers Forgejo as the OpenID client when its secret is set (web-app "OpenID provider"), and then serves `orgsyndb_web.wsgi` with gunicorn on `0.0.0.0:8000`. `deploy/orgsyndb.env.example` names `ORGSYNDB_DEMO`, commented out, with a comment saying that it fills an empty database with invented records whose accounts share a password shown on the sign-in page, and is for test deployments only.

#### Scenario: Image inputs
- **WHEN** a test reads `deploy/webapp/Dockerfile`
- **THEN** it names `fedora:44`, `uv sync --frozen --no-dev`, `collectstatic`, `migrate`, `demo_data --if-empty`, `forge_client` and `gunicorn`, in the command in the order `migrate`, `demo_data`, `forge_client`, `gunicorn`, and `USER orgsyndb`

#### Scenario: Demo flag in the example settings
- **WHEN** a test reads `deploy/orgsyndb.env.example`
- **THEN** it holds the line `#ORGSYNDB_DEMO=false`

### Requirement: Database backups
`deploy/backup/orgsyndb-backup` SHALL be an executable POSIX shell script with the subcommands `run`, the default, and `once`. `once` dumps the database `POSTGRES_DB` on host `db` as `POSTGRES_USER` with `POSTGRES_PASSWORD`, using `pg_dump` in custom format, into `<dir>/lab-<UTC time as YYYYMMDDTHHMMSSZ>.dump`, `<dir>` being `ORGSYNDB_BACKUP_DIR`, default `/backups`, writing a temporary file renamed when the dump is complete. It then removes all but the `ORGSYNDB_KEEP_BACKUPS` newest `lab-*.dump` files, default 14. A failed dump leaves no file and exits 1 with `orgsyndb-backup: error:` and the reason on stderr. `run` dumps as `once` does every `ORGSYNDB_BACKUP_HOURS` hours, default 24, starting at once, logs a failed dump and keeps going. A malformed number exits 1 naming the variable; an unknown subcommand exits 2 with a usage line.

#### Scenario: Dump and pruning
- **WHEN** a test runs `once` with a fake `pg_dump` on `PATH` and `ORGSYNDB_BACKUP_DIR` naming a temporary directory that holds 14 older dumps, and `ORGSYNDB_KEEP_BACKUPS` unset
- **THEN** a new `lab-*.dump` holds the fake's output, 14 dumps remain, and the oldest is gone

#### Scenario: Failed dump
- **WHEN** the fake `pg_dump` exits 1
- **THEN** `once` exits 1, stderr starts with `orgsyndb-backup: error:`, and no new file exists in the directory

### Requirement: Manifests
For every build it tries, the cycle SHALL send the application a manifest (collection-import "Manifest") by `POST` to `ORGSYNDB_MANIFEST_URL`, with the `Host` header of the snapshot request, `Authorization: Bearer <ORGSYNDB_BUILDER_TOKEN>`, `Content-Type: application/json` and a timeout of 30 seconds. It holds a new UUID as `build`; the collection commit and its committer date as `commit` and `committed_at`; the `id` of the snapshot's `import`, or `null` when that is `null`, as `base`; the snapshot's digest as `snapshot`; the application commit as `tooling`; as `trigger`, `commit` when the latest accepted import has another collection commit, else `registry` when it has another snapshot, else `tooling` when it has another application commit, else `catch-up`, which is also the trigger when no import was accepted; and, for a build that succeeded, the outcome `built`, the staged release's name as `release` and the keys of the output of `manifest`, or, for one that failed, the outcome `refused` and as `errors` the lines of the failed command's output that contain `: error: `, or its failure message when there are none.

For a build that succeeded: on `200` with `accepted` the cycle publishes the release (Releases); on `200` with `refused` it records the combination as failed; on `409` with `stale` it records nothing, so that the next cycle builds again with a fresh snapshot; on any other answer, or none, it logs `cannot send the manifest` with the reason and records nothing. A build that failed is recorded as failed once the application has answered its report with `200`; without that answer the cycle logs `cannot send the manifest` and records nothing, so that the next cycle builds it again and reports it then.

#### Scenario: What a manifest holds
- **WHEN** a test runs `sync` once against a fake application that records each manifest
- **THEN** the recorded manifest has `format` 1, a UUID `build`, the collection commit, the snapshot's digest, the application commit as `tooling`, `base` `null`, the outcome `built`, the published release's name, and the `language`, `procedures`, `sequences` and `deleted` the fake `manifest` printed, and was sent with the token and the `Host` of the snapshot request

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

