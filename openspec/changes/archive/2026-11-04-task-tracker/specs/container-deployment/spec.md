## MODIFIED Requirements

### Requirement: Releases
A successful build SHALL be copied, with its `pdf/` when PDFs are on, into a new directory `<data>/releases/<serial>-<app>-<collection>`, the serial counting up from `000001` and the commits shortened to ten characters, together with `index.json`, the output of `<app>/tools/orgsyndb -C <collection>/<path> index` run after the build; when that command fails or exceeds the build timeout, the build counts as failed. The relative symlink `<data>/current` SHALL then be replaced atomically to point to the release. Afterwards all releases but the current one and the `ORGSYNDB_KEEP_RELEASES` newest others are removed, with any partial copy. `<data>/state.json` records the published commits and release, the serial, and up to 50 failed combinations.

#### Scenario: Relative symlink
- **WHEN** a test runs `sync` once
- **THEN** `current` is a symlink with a relative target

#### Scenario: Pruning
- **WHEN** with `ORGSYNDB_KEEP_RELEASES=1` four collection commits are published
- **THEN** two releases remain and `current` points to the newest

#### Scenario: PDFs
- **WHEN** `sync` runs with `ORGSYNDB_PDF=true`
- **THEN** the build ran `pdf` and the release holds `pdf/`

#### Scenario: Index in the release
- **WHEN** `sync` publishes a build with the fake `tools/orgsyndb`, whose `index` prints `{"site_language": "de"}`
- **THEN** `current/index.json` holds that text

#### Scenario: Failing index
- **WHEN** the fake `tools/orgsyndb` builds successfully but its `index` exits 1, or runs past `ORGSYNDB_BUILD_TIMEOUT`
- **THEN** `sync` publishes nothing, the release published before stays current, and the combination is recorded as failed

#### Scenario: New application whose index fails
- **WHEN** a new application commit builds but its `index` exits 1, while the checked-out one works
- **THEN** `sync` falls back to the checked-out commit and publishes its build with its index

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, and forward `/lab/` and every path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default. It sets the header `Cache-Control: no-cache` on every response and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`;
- `db`, from `postgres:18`, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb` and starting once `db` is healthy;
- `backup`, from `postgres:18`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`.

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, and `ORGSYNDB_ALLOWED_HOSTS`. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*` and `reverse_proxy`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app` and `backup`, `builder` runs `orgsyndb-deploy run` and reads the settings, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, and `app` receives the example's `ORGSYNDB_DATABASE_URL`

## ADDED Requirements

### Requirement: Application image
`deploy/webapp/Dockerfile` SHALL build an image from `fedora:44` that installs Python 3 and uv, copies `webapp/` and `site/assets/css/` from the build context, the repository root, installs the locked dependencies without the development ones, and collects the static files. It runs as the user `orgsyndb` with UID 1000 and exposes port 8000. Its command applies pending migrations and then serves `orgsyndb_web.wsgi` with gunicorn on `0.0.0.0:8000`. `ORGSYNDB_INDEX` defaults to `/var/lib/orgsyndb/current/index.json`.

#### Scenario: Image inputs
- **WHEN** a test reads `deploy/webapp/Dockerfile`
- **THEN** it names `fedora:44`, `uv sync --frozen --no-dev`, `collectstatic`, `migrate` and `gunicorn`, and `USER orgsyndb`

### Requirement: Database backups
`deploy/backup/orgsyndb-backup` SHALL be an executable POSIX shell script with the subcommands `run`, the default, and `once`. `once` dumps the database `POSTGRES_DB` on host `db` as `POSTGRES_USER` with `POSTGRES_PASSWORD`, using `pg_dump` in custom format, into `<dir>/lab-<UTC time as YYYYMMDDTHHMMSSZ>.dump`, `<dir>` being `ORGSYNDB_BACKUP_DIR`, default `/backups`, writing a temporary file renamed when the dump is complete. It then removes all but the `ORGSYNDB_KEEP_BACKUPS` newest `lab-*.dump` files, default 14. A failed dump leaves no file and exits 1 with `orgsyndb-backup: error:` and the reason on stderr. `run` dumps as `once` does every `ORGSYNDB_BACKUP_HOURS` hours, default 24, starting at once, logs a failed dump and keeps going. A malformed number exits 1 naming the variable; an unknown subcommand exits 2 with a usage line.

#### Scenario: Dump and pruning
- **WHEN** a test runs `once` with a fake `pg_dump` on `PATH` and `ORGSYNDB_BACKUP_DIR` naming a temporary directory that holds 14 older dumps, and `ORGSYNDB_KEEP_BACKUPS` unset
- **THEN** a new `lab-*.dump` holds the fake's output, 14 dumps remain, and the oldest is gone

#### Scenario: Failed dump
- **WHEN** the fake `pg_dump` exits 1
- **THEN** `once` exits 1, stderr starts with `orgsyndb-backup: error:`, and no new file exists in the directory
