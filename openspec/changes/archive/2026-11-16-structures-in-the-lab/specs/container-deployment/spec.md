## MODIFIED Requirements

### Requirement: Update cycle
A cycle SHALL fetch the branch or tag `ORGSYNDB_APP_REF` from `ORGSYNDB_APP_REPO` into the application's clone when application updates are on, and `ORGSYNDB_COLLECTION_REF` from `ORGSYNDB_COLLECTION_REPO` into `<data>/collection/`, creating that repository on first use. Each repository may be any URL or path Git fetches from. When the fetched application commit differs from the checked-out one and its `deploy/docker` tree differs from the image's `deploy_tree`, the cycle logs that it needs a new image and keeps the checked-out commit.

Next the cycle requests the lab application's snapshot at `ORGSYNDB_REGISTRY_URL`, sending as `Host` the first entry of `ORGSYNDB_ALLOWED_HOSTS` that is not `*`, with a leading `.` dropped, or `localhost` when there is none, with a timeout of 30 seconds, and on an answer of status 200 whose body is a snapshot (lab-registry "Snapshot") writes it to `<data>/registry.json`. Before the cycle's first build, it requests the image of every substance of that snapshot with a molfile, `substances/<key>/structure.svg` resolved against `ORGSYNDB_REGISTRY_URL`, sending the same `Host`, with a timeout of 30 seconds, keeps the body of each answer of status 200 as `<data>/substances/<key>/structure.svg`, beside the snapshot, where the build finds it (compound-registry "Structure images"), and removes everything else from `<data>/substances/`. When an image request fails or is answered with another status, the cycle logs `cannot fetch the structure images` with the image's address and builds nothing in that cycle. When the request fails, or the answer is not a snapshot, it logs `cannot fetch the registry` and builds nothing: only the application can accept a build, and a kept copy cannot say which import it accepted last. The snapshot's `import` names the latest accepted import of the collection (lab-registry "Snapshot"); when its release is in `<data>/releases/` and `<data>/current` points elsewhere, the cycle points `current` at it. The registry's digest is part of every combination below, so that a changed registry is built and published like a new commit. Without `ORGSYNDB_BUILDER_TOKEN` the cycle logs that `ORGSYNDB_BUILDER_TOKEN` is not set and builds nothing.

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

#### Scenario: Structure images beside the kept snapshot
- **WHEN** a test runs `sync` once against a fake application whose snapshot gives one substance a molfile and that serves an SVG at `/lab/registry/substances/<key>/structure.svg`
- **THEN** the fake application received that request with the `Host` it received the snapshot's request with, and `<data>/substances/<key>/structure.svg` holds the SVG

#### Scenario: An image that cannot be fetched
- **WHEN** the fake application of the previous scenario answers the image's request with status 500 and a test runs `sync` once
- **THEN** the cycle logs `cannot fetch the structure images` and runs no build
