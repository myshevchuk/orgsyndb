## MODIFIED Requirements

### Requirement: Updater program
`orgsyndb-deploy` SHALL be an executable Python program using only the standard library, with the subcommands `run` (the default), `sync`, `status`, `retry` and `help`. `sync` runs one cycle; `run` runs a cycle, waits `ORGSYNDB_INTERVAL` seconds or until SIGHUP, and repeats until SIGTERM, logging errors of a cycle without stopping. `status` prints the saved state as JSON; `retry` empties its list of failed combinations. It exits 0 on success, 1 on an error, writing `orgsyndb-deploy: error:` and a message to stderr, and 2 with a usage line on an unknown subcommand.

It reads `ORGSYNDB_COLLECTION_REPO` (required), `ORGSYNDB_COLLECTION_REF` (default `main`), `ORGSYNDB_COLLECTION_PATH` (a relative path without `..`, default the repository root), `ORGSYNDB_APP_UPDATE` (default true), `ORGSYNDB_APP_REPO` and `ORGSYNDB_APP_REF` (default the image's `app_repo` and `app_ref`), `ORGSYNDB_INTERVAL` (default 300, at least 10), `ORGSYNDB_PDF` (default false), `ORGSYNDB_KEEP_RELEASES` (default 2), `ORGSYNDB_BUILD_TIMEOUT` (default 3600, at least 60), `ORGSYNDB_REGISTRY_URL` (default `http://app:8000/lab/registry/snapshot.json`), and `ORGSYNDB_ALLOWED_HOSTS`, the host names the lab application accepts, which `orgsyndb.env` gives the builder as it gives `app`, and, for its paths, `ORGSYNDB_DATA` (default `/var/lib/orgsyndb`), `ORGSYNDB_APP` (default `/opt/orgsyndb/app`) and `ORGSYNDB_IMAGE_INFO` (default `/opt/orgsyndb/image.json`). A flag takes `true`, `false`, `yes`, `no`, `on`, `off`, `1` or `0`. A missing collection repository or a malformed value is an error naming the variable.

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

Next the cycle requests the lab application's snapshot at `ORGSYNDB_REGISTRY_URL`, sending as `Host` the first entry of `ORGSYNDB_ALLOWED_HOSTS` that is not `*`, with a leading `.` dropped, or `localhost` when there is none, with a timeout of 30 seconds, and on an answer of status 200 whose body is a snapshot (lab-registry "Snapshot") writes it to `<data>/registry.json` and the address to `<data>/registry.source`. When the request fails it logs `cannot fetch the registry` and uses the copy in `<data>/registry.json` when `<data>/registry.source` holds the same address; without such a copy it builds nothing. The registry's digest is part of every combination below, so that a changed registry is built and published like a new commit.

The cycle then tries, in order, the new application commit if there is one and the checked-out one, each with the fetched collection commit and the registry. It stops at the first combination that is already published, and skips one that failed before. For any other it checks out both commits, keeping ignored files, and runs `<app>/tools/orgsyndb -C <collection>/<path> build`, or `pdf` when `ORGSYNDB_PDF` is true. Every run of `tools/orgsyndb` in the cycle, the index the release carries included, has `ORGSYNDB_REGISTRY` naming `<data>/registry.json` (compound-registry "Registry source"), so that the site and the index describe the registry the cycle fetched. When `<path>/orgsyndb.toml` is missing it logs `ORGSYNDB_COLLECTION_PATH` and builds nothing. A build that exits non-zero or exceeds the timeout fails; the cycle logs that the published site is unchanged and records the combination as failed. After the cycle the application's clone is at the commit of the published site, or at the commit it started from.

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

#### Scenario: Registry change
- **WHEN** a test serves a snapshot, runs `sync`, changes the snapshot's digest, and runs `sync` again without a new commit
- **THEN** the second run publishes a second release, built with the new snapshot, and the state names its digest

#### Scenario: Host of the request
- **WHEN** a test runs `sync` with `ORGSYNDB_ALLOWED_HOSTS=lab.example.org,localhost` against a test server that records each request
- **THEN** the snapshot was requested with the `Host` header `lab.example.org`; with `ORGSYNDB_ALLOWED_HOSTS=*` it was requested with `localhost`, and with `.example.org` with `example.org`

#### Scenario: Registry unreachable
- **WHEN** after a publish the snapshot's address stops answering and the collection gains a commit, and `sync` runs; and separately `sync` runs on a fresh data directory with an address that never answers
- **THEN** the first logs `cannot fetch the registry` and publishes the new commit built with the copy; the second logs it and builds nothing
