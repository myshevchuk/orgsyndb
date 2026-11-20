## MODIFIED Requirements

### Requirement: Container image
`deploy/docker/Dockerfile` SHALL build an image from a `fedora` base image that installs Python, Hugo, WeasyPrint, Emacs, Git, the SSH client and Caddy, and adds the user `orgsyndb` with UID 1000. Running as that user, it clones the application from the build argument `APP_REPO` at the branch or tag `APP_REF` (by default `https://github.com/myshevchuk/orgsyndb.git` and `main`) into `/opt/orgsyndb/app`, builds the demo collection there to fill `.emacs-batch/` and `.tools/`, removes the demo's build output, and writes `/opt/orgsyndb/image.json` holding `app_repo`, `app_ref` and `deploy_tree`, the Git tree id of the clone's `deploy/docker`. It installs `orgsyndb-deploy` and the Caddyfile from the clone, trusts repositories under `/srv/git/` for Git, runs as `orgsyndb`, declares `/var/lib/orgsyndb` a volume and runs `orgsyndb-deploy run` by default. `deploy/docker/` holds only `Dockerfile`, `Caddyfile` and `orgsyndb-deploy`.

#### Scenario: Image inputs
- **WHEN** a test lists `deploy/docker/` and reads its `Dockerfile`
- **THEN** the directory holds exactly those three files, and the Dockerfile names a `fedora` base image, the six tools, `HEAD:deploy/docker` and `USER orgsyndb`

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, answer `404` for every path beginning with `/lab/collection/manifest` or `/lab/collection/check`, forward `/lab/` and every other path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default, and forward every path below `/git/`, with `/git` taken off, to Forgejo at `ORGSYNDB_FORGE_UPSTREAM`, `forge:3000` by default, redirecting `/git` to `/git/`. It sets the header `Cache-Control: no-cache` on every response but Forgejo's, which sets its own, and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process and `ORGSYNDB_LAB=true` in its environment, so that the site it builds links the lab application's views, starting once `app` is healthy, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`, and `builder` mounting the volume `pushes` read-only at `/var/lib/orgsyndb-pushes` (Push log);
- `db`, from a `postgres` image, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb`, starting once `db` is healthy, with a health check that passes once a TCP connection to its port 8000 opens;
- `backup`, from the image of `db`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`, `orgsyndb.env` read-only at `/opt/orgsyndb/orgsyndb.env`, the volumes `forge` and `pushes` read-only at `/var/lib/gitea` and `/var/lib/orgsyndb-pushes`, and `forge-control` read-write at `/var/lib/orgsyndb-forge-control` (Backups);
- `restore`, from the image of `db` with the same script, only in the profile `restore`, running `orgsyndb-backup restore`, with `deploy/backups/` read-only and the volumes `forge`, `pushes` and `data` read-write at `/var/lib/gitea`, `/var/lib/orgsyndb-pushes` and `/var/lib/orgsyndb`, starting once `db` is healthy and `forge-db` has completed, since the restore creates `forge` owned by the role `forge`;
- `forge-db` and `forge` (Forgejo), both mounting the volume `pushes` read-write at `/var/lib/orgsyndb-pushes`.

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, `ORGSYNDB_ALLOWED_HOSTS`, with `app` among the hosts, `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token, and the settings of Forgejo with how to generate each secret. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*`, `reverse_proxy`, `/lab/collection/manifest*` and `/lab/collection/check*`, each answered with `404` ahead of the `/lab/*` route, and `/git/*` with `handle_path`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app`, `backup`, `forge-db` and `forge`, with `restore` only under the profile `restore`, `backup` mounts `forge` and `pushes` read-only and `forge-control` read-write, `restore` mounts `forge`, `pushes` and `data` read-write and depends on `forge-db` completing, `builder` runs `orgsyndb-deploy run`, reads the settings and has `ORGSYNDB_LAB` set to `true`, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, `app`'s health check connects to port 8000, `builder` depends on `app` being healthy, `app` receives the example's `ORGSYNDB_DATABASE_URL`, `builder` mounts `pushes` read-only and `forge` and `forge-db` mount it read-write

### Requirement: Application image
`deploy/webapp/Dockerfile` SHALL build an image from a `fedora` base image that installs Python and uv, copies `webapp/` and the site's `site/assets/css/`, `site/hugo.toml` and `site/i18n/` from the build context, the repository root, installs the locked dependencies without the development ones, and collects the static files. It runs as the user `orgsyndb` with UID 1000 and exposes port 8000. Its command applies pending migrations, then runs `manage.py demo_data --if-empty`, which seeds an empty database when `ORGSYNDB_DEMO` is true and otherwise changes nothing (lab-demo "Demo data command"), then `manage.py forge_client`, which registers Forgejo as the OpenID client when its secret is set (web-app "OpenID provider"), and then serves `orgsyndb_web.wsgi` with gunicorn on `0.0.0.0:8000`. `deploy/orgsyndb.env.example` names `ORGSYNDB_DEMO`, commented out, with a comment saying that it fills an empty database with invented records whose accounts share a password shown on the sign-in page, and is for test deployments only.

#### Scenario: Image inputs
- **WHEN** a test reads `deploy/webapp/Dockerfile`
- **THEN** it names a `fedora` base image, `uv sync --frozen --no-dev`, `collectstatic`, `migrate`, `demo_data --if-empty`, `forge_client` and `gunicorn`, in the command in the order `migrate`, `demo_data`, `forge_client`, `gunicorn`, and `USER orgsyndb`

#### Scenario: Demo flag in the example settings
- **WHEN** a test reads `deploy/orgsyndb.env.example`
- **THEN** it holds the line `#ORGSYNDB_DEMO=false`

### Requirement: Forgejo
`deploy/compose.yaml` SHALL run Forgejo as `forge`, from a rootless image of `codeberg.org/forgejo/forgejo`, keeping its data in the volume `forge`, with an init process, the volume `forge-control` at `/var/lib/orgsyndb-forge-control`, port 2222, its SSH server, published, starting once `forge-db` has completed. Its settings come from environment variables, none from a hand-edited file and none substituted by Compose from the shell: as constants in `compose.yaml`, the PostgreSQL database `forge` on `db` as the role `forge`, the installation locked, registration only through an external source, an account created at the first sign-in through one, named by the `nickname` claim, no linking to an existing account, no password sign-in form, the built-in SSH server on port 2222, and `USER_DISABLED_FEATURES` `change_username,deletion`, so that a Forgejo account keeps the lab user name; and, from `orgsyndb.env` at start, the root URL `<ORGSYNDB_URL>/git/` and the database password `FORGE_DB_PASSWORD`, which `deploy/forge/forge-start`, mounted read-only and run as the service's entrypoint, exports before it runs the image's own entrypoint, given as its arguments, as a child. It pauses Forgejo for a backup (Backups) through the directory `/var/lib/orgsyndb-forge-control`, or the one `ORGSYNDB_FORGE_CONTROL` names: at start it removes a `paused` there and does not start the child while a `pause` exists; every 2 seconds it checks for `pause`. When `pause` holds a request id `paused` does not, it first waits until no push is in flight, no process of the container running `git receive-pack`, since stopping Forgejo during a push loses Forgejo's own processing of it; meanwhile the gate refuses new pushes (Gate). Then it stops the child with SIGTERM and waits for it, then waits, without signalling them, until no other process of the container but its init process and itself remains, so that a hook of a push in flight finishes its work, and only then writes the id to `paused`; a process that never ends leaves the request unacknowledged, and the backup times out. Once `pause` is gone it removes `paused` and starts the child again. A pause that lasts `ORGSYNDB_FORGE_PAUSE_LIMIT` seconds, an hour by default, ends: it logs that, removes `paused` and the `pause` holding that id, and starts the child. When the child exits while no pause holds, `forge-start` exits with its status; on SIGTERM or SIGINT it stops the child, waits for it and exits 0.

`forge-db`, from the image of `db`, runs once after `db` is healthy and creates the role `forge` with `FORGE_DB_PASSWORD` and the database `forge` it owns when either is missing, so that a database volume made before gains them; it changes nothing that exists. It also makes the roots of the volumes `pushes` and `forge-control`, and the files in them, owned by UID 1000, the user of Forgejo's rootless image and of the builder's image, so that `forge` can append to the push log, `builder` read it, and `forge` answer a pause.

`deploy/forge/forge-setup`, mounted read-only into `forge` as well and run with `docker compose exec forge`, creates the admin account `orgsyndb` with `ORGSYNDB_FORGE_PASSWORD` when it is missing, adds or updates the OpenID Connect source `lab` with the discovery URL `${ORGSYNDB_APP_INTERNAL_URL}/lab/o/.well-known/openid-configuration`, the client id `forgejo`, `ORGSYNDB_FORGE_CLIENT_SECRET`, the scopes `openid profile email`, the group claim `groups` mapped to the team `authors` of the organisation `lab`, with membership removed when the claim no longer names it; creates, when missing, the public organisation `lab`, its team `authors`, and the public repository `lab/collection` with the default branch `main`, giving the team write access to that repository alone; protects `main`, so that Forgejo refuses a force push to it; links `deploy/forge/gate` into the repository's `hooks/pre-receive.d/` as `orgsyndb-gate` (Gate) and `deploy/forge/push-log` into its `hooks/post-receive.d/` as `orgsyndb-push-log` (Push log); creates the push log when missing and stops with an error naming `ORGSYNDB_PUSH_LOG` when it cannot append to it; and sets up the mirror (Mirror). Run again it changes only what differs. `deploy/orgsyndb.env.example` names `ORGSYNDB_URL`, the address people reach the site at; `ORGSYNDB_OIDC_KEY`, with the command that generates it; `ORGSYNDB_FORGE_CLIENT_SECRET`, `ORGSYNDB_FORGE_PASSWORD` and `FORGE_DB_PASSWORD`, each with how to generate it; `ORGSYNDB_FORGE_URL`, `http://forge:3000/api/v1` by default; `ORGSYNDB_GATE_TOKEN`, with how to generate it; `ORGSYNDB_WAKE_URL`, `http://builder:8091/wake`; `ORGSYNDB_MIRROR_URL`, `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN`, empty, with what a mirror overwrites; and, as `ORGSYNDB_COLLECTION_REPO`, `http://forge:3000/lab/collection.git`, the repository `forge-setup` creates.

#### Scenario: Forgejo's service
- **WHEN** a test runs `docker compose config` as in Compose file
- **THEN** with no `ORGSYNDB_` or `FORGE_` variable in the shell, `forge` uses a rootless Forgejo image, has `forge-start` as its entrypoint, mounts the volume `forge`, publishes 2222, depends on `forge-db` completing, and its environment sets the database `forge` on `db`, `ENABLE_AUTO_REGISTRATION`, `ACCOUNT_LINKING` `disabled` and `ENABLE_INTERNAL_SIGNIN` `false`, and the output holds no unresolved or empty substitution; `forge-db` depends on `db` being healthy and does not restart

#### Scenario: The start script
- **WHEN** a test runs `deploy/forge/forge-start` with `ORGSYNDB_URL=http://localhost:8080` and `FORGE_DB_PASSWORD=x` in its environment and a stand-in for the image's entrypoint
- **THEN** the stand-in runs with `FORGEJO__server__ROOT_URL=http://localhost:8080/git/` and `FORGEJO__database__PASSWD=x` in its environment

#### Scenario: Pausing Forgejo
- **WHEN** a test runs `forge-start` with a stand-in for the image's entrypoint that records its starts and exits on SIGTERM, and `ORGSYNDB_FORGE_CONTROL` naming a temporary directory, then writes `pause` holding `r1`, waits for `paused`, and removes `pause`
- **THEN** the stand-in was stopped before `paused` appeared holding `r1`, `paused` is gone after `pause` is, the stand-in has started twice, and `forge-start` still runs

#### Scenario: A push in flight
- **WHEN** a process whose command line holds `receive-pack` runs in the container when `pause` holding `r3` appears, and ends 3 seconds later
- **THEN** the stand-in was stopped only after that process had ended, and then `paused` holds `r3`

#### Scenario: A stale acknowledgement at start
- **WHEN** the directory holds a `paused` holding `old` and no `pause` when `forge-start` starts
- **THEN** `paused` is gone and the stand-in runs

#### Scenario: A pause that lasts too long
- **WHEN** `ORGSYNDB_FORGE_PAUSE_LIMIT` is 3 and `pause` holding `r2` stays
- **THEN** within about 6 seconds `paused` and `pause` are gone, the stand-in runs again, and the output says the pause ended

#### Scenario: Forgejo exits by itself
- **WHEN** the stand-in exits with status 3 while no pause was asked for
- **THEN** `forge-start` exits with status 3

#### Scenario: Stopping the container
- **WHEN** a test sends `forge-start` SIGTERM while the stand-in runs
- **THEN** the stand-in received SIGTERM and `forge-start` exited 0 within about 3 seconds

#### Scenario: Creating the database once
- **WHEN** a test runs `forge-db`'s script against a PostgreSQL server twice, skipping without one
- **THEN** after the first run the role and the database `forge` exist, and the second run succeeds and changes nothing

#### Scenario: The push log's volume
- **WHEN** a test reads `deploy/forge/forge-db`
- **THEN** it makes `/var/lib/orgsyndb-pushes` and `/var/lib/orgsyndb-forge-control` owned by UID 1000

#### Scenario: The set-up script
- **WHEN** a test reads `deploy/forge/forge-setup`
- **THEN** it creates the admin `orgsyndb`, the organisation `lab`, the team `authors`, the repository `lab/collection` and the protection of `main` each only when missing, adds the source `lab` when missing and updates it otherwise, with the discovery URL, the client id `forgejo`, the scopes `openid profile email` and the group claim `groups` mapped to the team `authors`, links the gate into `hooks/pre-receive.d/` and the push log into `hooks/post-receive.d/`, and checks that the push log can be appended to
