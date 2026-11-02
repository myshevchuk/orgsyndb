## ADDED Requirements

### Requirement: Container image
`deploy/docker/Dockerfile` SHALL build an image from `fedora:44` that installs Python 3, Hugo, WeasyPrint, Emacs, Git, the SSH client and Caddy, and adds the user `orgsyndb` with UID 1000. Running as that user, it clones the application from the build argument `APP_REPO` at the branch or tag `APP_REF` (by default `https://github.com/myshevchuk/orgsyndb.git` and `main`) into `/opt/orgsyndb/app`, builds the demo collection there to fill `.emacs-batch/` and `.tools/`, removes the demo's build output, and writes `/opt/orgsyndb/image.json` holding `app_repo`, `app_ref` and `deploy_tree`, the Git tree id of the clone's `deploy/docker`. It installs `orgsyndb-deploy` and the Caddyfile from the clone, trusts repositories under `/srv/git/` for Git, runs as `orgsyndb`, declares `/var/lib/orgsyndb` a volume and runs `orgsyndb-deploy run` by default. `deploy/docker/` holds only `Dockerfile`, `Caddyfile` and `orgsyndb-deploy`.

#### Scenario: Image inputs
- **WHEN** a test lists `deploy/docker/` and reads its `Dockerfile`
- **THEN** the directory holds exactly those three files, and the Dockerfile names `fedora:44`, the six tools, `HEAD:deploy/docker` and `USER orgsyndb`

### Requirement: Updater program
`orgsyndb-deploy` SHALL be an executable Python program using only the standard library, with the subcommands `run` (the default), `sync`, `status`, `retry` and `help`. `sync` runs one cycle; `run` runs a cycle, waits `ORGSYNDB_INTERVAL` seconds or until SIGHUP, and repeats until SIGTERM, logging errors of a cycle without stopping. `status` prints the saved state as JSON; `retry` empties its list of failed combinations. It exits 0 on success, 1 on an error, writing `orgsyndb-deploy: error:` and a message to stderr, and 2 with a usage line on an unknown subcommand.

It reads `ORGSYNDB_COLLECTION_REPO` (required), `ORGSYNDB_COLLECTION_REF` (default `main`), `ORGSYNDB_COLLECTION_PATH` (a relative path without `..`, default the repository root), `ORGSYNDB_APP_UPDATE` (default true), `ORGSYNDB_APP_REPO` and `ORGSYNDB_APP_REF` (default the image's `app_repo` and `app_ref`), `ORGSYNDB_INTERVAL` (default 300, at least 10), `ORGSYNDB_PDF` (default false), `ORGSYNDB_KEEP_RELEASES` (default 2) and `ORGSYNDB_BUILD_TIMEOUT` (default 3600, at least 60), and, for its paths, `ORGSYNDB_DATA` (default `/var/lib/orgsyndb`), `ORGSYNDB_APP` (default `/opt/orgsyndb/app`) and `ORGSYNDB_IMAGE_INFO` (default `/opt/orgsyndb/image.json`). A flag takes `true`, `false`, `yes`, `no`, `on`, `off`, `1` or `0`. A missing collection repository or a malformed value is an error naming the variable.

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

The cycle then tries, in order, the new application commit if there is one and the checked-out one, each with the fetched collection commit. It stops at the first combination that is already published, and skips one that failed before. For any other it checks out both commits, keeping ignored files, and runs `<app>/tools/orgsyndb -C <collection>/<path> build`, or `pdf` when `ORGSYNDB_PDF` is true. When `<path>/orgsyndb.toml` is missing it logs `ORGSYNDB_COLLECTION_PATH` and builds nothing. A build that exits non-zero or exceeds the timeout fails; the cycle logs that the published site is unchanged and records the combination as failed. After the cycle the application's clone is at the commit of the published site, or at the commit it started from.

A collection that cannot be fetched is built from its last fetched commit, if any; an application that cannot be fetched stays at its commit.

#### Scenario: First publish
- **WHEN** a test runs `sync` once
- **THEN** the published `index.html` comes from the application and collection commits, and the state names both

#### Scenario: Nothing new
- **WHEN** a test runs `sync` twice without a new commit
- **THEN** the build ran once and there is one release

#### Scenario: New collection commit
- **WHEN** the collection gains a commit between two runs of `sync`
- **THEN** the second run publishes it as a second release

#### Scenario: Failed collection commit
- **WHEN** the collection gains a commit that fails to build, and `sync` runs twice
- **THEN** the published site is unchanged, the output says so, and the build of that commit ran once; a later good commit is published

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

### Requirement: Releases
A successful build SHALL be copied, with its `pdf/` when PDFs are on, into a new directory `<data>/releases/<serial>-<app>-<collection>`, the serial counting up from `000001` and the commits shortened to ten characters, and the relative symlink `<data>/current` SHALL then be replaced atomically to point to it. Afterwards all releases but the current one and the `ORGSYNDB_KEEP_RELEASES` newest others are removed, with any partial copy. `<data>/state.json` records the published commits and release, the serial, and up to 50 failed combinations.

#### Scenario: Relative symlink
- **WHEN** a test runs `sync` once
- **THEN** `current` is a symlink with a relative target

#### Scenario: Pruning
- **WHEN** with `ORGSYNDB_KEEP_RELEASES=1` four collection commits are published
- **THEN** two releases remain and `current` points to the newest

#### Scenario: PDFs
- **WHEN** `sync` runs with `ORGSYNDB_PDF=true`
- **THEN** the build ran `pdf` and the release holds `pdf/`

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, the header `Cache-Control: no-cache` on every response, and Caddy's admin endpoint off. `deploy/compose.yaml` SHALL define the services `builder`, running `orgsyndb-deploy run` with an init process, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both reading `orgsyndb.env`, and both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`. `deploy/orgsyndb.env.example` lists the settings.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public` and the `Cache-Control` header, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder` and `web`, `builder` runs `orgsyndb-deploy run` and reads the settings, and `web` mounts the data volume read-only
