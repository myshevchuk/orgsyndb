## ADDED Requirements

### Requirement: Push log
`deploy/forge/push-log` SHALL be the post-receive hook of `lab/collection`, run with `sh`. For each update of `refs/heads/main` that does not delete it, it appends to the file `ORGSYNDB_PUSH_LOG`, `/var/lib/orgsyndb-pushes/pushes.log` by default, one line `<time> <commit> <id> <name>`: the time in UTC as `YYYY-MM-DDTHH:MM:SSZ`, the new commit, and `GITEA_PUSHER_ID` and `GITEA_PUSHER_NAME` as Forgejo sets them, each `-` when unset or empty, written by a single write to the file opened for appending. Updates of other refs and deletions append nothing. After the lines it wakes the builder once (Waking the builder), by `POST` to `ORGSYNDB_WAKE_URL`, `http://builder:8091/wake` by default, with `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, waiting at most 5 seconds; it sends no wake-up when it appended nothing. When it cannot append, it writes `Push log: cannot record this push:` and the reason to standard error, and when the builder does not answer `202`, `Push log: the builder was not woken; it builds this push at its next check`; Forgejo shows both to the pusher. It exits 0, since the push is already accepted.

The builder reads the push log, mounted read-only, when it makes a manifest (Manifests), after the build's commands have run: the pusher of commit C is the name of the last line whose commit is C, or none when no line names C, that line's name is `-`, or the file is missing. A line it cannot read is skipped. A line appended after the manifest was made is not used.

#### Scenario: A push to main
- **WHEN** a test runs `deploy/forge/push-log` with `sh` against a fake wake-up server, with `GITEA_PUSHER_ID=7` and `GITEA_PUSHER_NAME=jkoch`, feeding it an update of `refs/heads/main`
- **THEN** the log gains one line with the time, the new commit, `7` and `jkoch`, and the fake received one `POST` with the gate token

#### Scenario: Other refs and deletions
- **WHEN** the hook is fed an update of `refs/heads/draft` and a deletion of `refs/heads/main`
- **THEN** the log gains nothing and no wake-up is sent

#### Scenario: No pusher
- **WHEN** the hook runs without `GITEA_PUSHER_ID` and `GITEA_PUSHER_NAME`
- **THEN** the line holds `-` for both

#### Scenario: Concurrent pushes
- **WHEN** a test runs 20 instances of the hook at once, each with another commit
- **THEN** the log holds 20 whole lines, one per commit

#### Scenario: The builder does not answer
- **WHEN** the wake-up address does not answer
- **THEN** the hook exits 0 within about 5 seconds, the line was appended, and standard error says the builder builds the push at its next check

#### Scenario: An unwritable log
- **WHEN** `ORGSYNDB_PUSH_LOG` names a file in a directory the hook cannot write
- **THEN** the hook exits 0 and standard error says it cannot record the push

#### Scenario: The pusher of a build
- **WHEN** the push log names the collection commit twice, first with `jkoch` and then with `abauer`, and `sync` runs
- **THEN** the manifest's `pusher` is `abauer`; with no line naming the commit, or no log, it is `null`

#### Scenario: A line appended during the build
- **WHEN** the log names no line for the collection commit when `sync` fetches it, and the fake build appends one naming `jkoch`
- **THEN** the manifest's `pusher` is `jkoch`

#### Scenario: The pusher of a registry build
- **WHEN** after a publish whose manifest named `jkoch` the snapshot's digest changes and `sync` runs
- **THEN** the manifest has the trigger `registry` and the pusher `jkoch`

### Requirement: Waking the builder
The builder's server (Gate) SHALL answer `POST /wake` with `202` and an empty body when the request carries `Authorization: Bearer` with `ORGSYNDB_GATE_TOKEN` or `ORGSYNDB_BUILDER_TOKEN`, either compared in constant time and an empty setting matching no token, and with `401` otherwise; another method on `/wake` answers `405`. A wake-up does what SIGHUP does: when no cycle runs, one starts at once; when one runs, one more starts after it, however many wake-ups arrived meanwhile. The wait of `ORGSYNDB_INTERVAL` seconds between cycles stays, so that a lost wake-up delays a build until the next cycle.

#### Scenario: A wake-up
- **WHEN** `run` waits with `ORGSYNDB_INTERVAL` at 300 and a test posts to `/wake` with the gate token, then with the builder token
- **THEN** both answer 202, and a cycle starts within about a second of each

#### Scenario: Wrong token
- **WHEN** a test posts to `/wake` without a token and with a wrong one
- **THEN** both answer 401 and no cycle starts

#### Scenario: During a cycle
- **WHEN** three wake-ups arrive while a cycle runs
- **THEN** exactly one more cycle runs after it

#### Scenario: Only the builder token
- **WHEN** `run` starts with `ORGSYNDB_BUILDER_TOKEN` set and `ORGSYNDB_GATE_TOKEN` empty
- **THEN** `/wake` answers 202 to the builder token

### Requirement: Mirror
`deploy/forge/forge-setup` SHALL, when `ORGSYNDB_MIRROR_URL` is set, remove every push mirror of `lab/collection` whose address is that URL and add one with that address, `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN` as its credentials, an interval of 8 hours and syncing on every push, through Forgejo's API as the admin `orgsyndb`; it stops with an error naming the variable when `ORGSYNDB_MIRROR_URL` does not begin with `https://` or either credential is empty. Without `ORGSYNDB_MIRROR_URL` it changes no mirror and says that no mirror is configured. The mirror makes the address a copy of `lab/collection`, so the example settings say that it must name a repository used for nothing else.

#### Scenario: The mirror in the set-up script
- **WHEN** a test reads `deploy/forge/forge-setup`
- **THEN** it reads `ORGSYNDB_MIRROR_URL`, `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN`, deletes the mirrors to that address and posts a new one to `push_mirrors` with `sync_on_commit` true, and changes no mirror without the URL

## MODIFIED Requirements

### Requirement: Updater program
`orgsyndb-deploy` SHALL be an executable Python program using only the standard library, with the subcommands `run` (the default), `sync`, `status`, `retry` and `help`. `sync` runs one cycle; `run` runs a cycle, waits `ORGSYNDB_INTERVAL` seconds, or until SIGHUP or a wake-up (Waking the builder), and repeats until SIGTERM, logging errors of a cycle without stopping. `status` prints the saved state as JSON; `retry` empties its list of failed combinations. It exits 0 on success, 1 on an error, writing `orgsyndb-deploy: error:` and a message to stderr, and 2 with a usage line on an unknown subcommand.

It reads `ORGSYNDB_COLLECTION_REPO` (required), `ORGSYNDB_COLLECTION_REF` (default `main`), `ORGSYNDB_COLLECTION_PATH` (a relative path without `..`, default the repository root), `ORGSYNDB_APP_UPDATE` (default true), `ORGSYNDB_APP_REPO` and `ORGSYNDB_APP_REF` (default the image's `app_repo` and `app_ref`), `ORGSYNDB_INTERVAL` (default 300, at least 10), `ORGSYNDB_PDF` (default false), `ORGSYNDB_KEEP_RELEASES` (default 2), `ORGSYNDB_BUILD_TIMEOUT` (default 3600, at least 60), `ORGSYNDB_REGISTRY_URL` (default `http://app:8000/lab/registry/snapshot.json`), `ORGSYNDB_MANIFEST_URL` (default `http://app:8000/lab/collection/manifest/`), `ORGSYNDB_BUILDER_TOKEN`, the token the application expects on a manifest (web-app "Settings from the environment"), and `ORGSYNDB_ALLOWED_HOSTS`, the host names the lab application accepts, which `orgsyndb.env` gives the builder as it gives `app`, and, for its paths, `ORGSYNDB_DATA` (default `/var/lib/orgsyndb`), `ORGSYNDB_APP` (default `/opt/orgsyndb/app`) `ORGSYNDB_IMAGE_INFO` (default `/opt/orgsyndb/image.json`) and `ORGSYNDB_PUSH_LOG` (default `/var/lib/orgsyndb-pushes/pushes.log`, Push log). A flag takes `true`, `false`, `yes`, `no`, `on`, `off`, `1` or `0`. A missing collection repository or a malformed value is an error naming the variable.

#### Scenario: Collection repository required
- **WHEN** a test runs `sync` without `ORGSYNDB_COLLECTION_REPO`
- **THEN** it exits 1 and stderr names `ORGSYNDB_COLLECTION_REPO`

#### Scenario: Malformed settings
- **WHEN** a test runs `sync` with `ORGSYNDB_INTERVAL=soon`, `ORGSYNDB_PDF=maybe` or `ORGSYNDB_COLLECTION_PATH=../x`
- **THEN** it exits 1 and stderr names the variable

#### Scenario: Standard library only
- **WHEN** a test compiles the program and collects its imports
- **THEN** it compiles, is executable, starts with `#!/usr/bin/env python3`, and imports only standard-library modules

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, answer `404` for every path beginning with `/lab/collection/manifest` or `/lab/collection/check`, forward `/lab/` and every other path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default, and forward every path below `/git/`, with `/git` taken off, to Forgejo at `ORGSYNDB_FORGE_UPSTREAM`, `forge:3000` by default, redirecting `/git` to `/git/`. It sets the header `Cache-Control: no-cache` on every response but Forgejo's, which sets its own, and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process and `ORGSYNDB_LAB=true` in its environment, so that the site it builds links the lab application's views, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`, and `builder` mounting the volume `pushes` read-only at `/var/lib/orgsyndb-pushes` (Push log);
- `db`, from `postgres:18`, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb` and starting once `db` is healthy;
- `backup`, from `postgres:18`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`;
- `forge-db` and `forge` (Forgejo), both mounting the volume `pushes` read-write at `/var/lib/orgsyndb-pushes`.

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, `ORGSYNDB_ALLOWED_HOSTS`, with `app` among the hosts, `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token, and the settings of Forgejo with how to generate each secret. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*`, `reverse_proxy`, `/lab/collection/manifest*` and `/lab/collection/check*`, each answered with `404` ahead of the `/lab/*` route, and `/git/*` with `handle_path`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app`, `backup`, `forge-db` and `forge`, `builder` runs `orgsyndb-deploy run`, reads the settings and has `ORGSYNDB_LAB` set to `true`, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, `app` receives the example's `ORGSYNDB_DATABASE_URL`, `builder` mounts `pushes` read-only and `forge` and `forge-db` mount it read-write

### Requirement: Manifests
For every build it tries, the cycle SHALL send the application a manifest (collection-import "Manifest") by `POST` to `ORGSYNDB_MANIFEST_URL`, with the `Host` header of the snapshot request, `Authorization: Bearer <ORGSYNDB_BUILDER_TOKEN>`, `Content-Type: application/json` and a timeout of 30 seconds. It holds a new UUID as `build`; the collection commit and its committer date as `commit` and `committed_at`; the `id` of the snapshot's `import`, or `null` when that is `null`, as `base`; the snapshot's digest as `snapshot`; the application commit as `tooling`; as `pusher`, the user name of the push log's last line naming the collection commit, or `null` when no line names it, the line names no pusher or the log is missing (Push log); as `trigger`, `commit` when the latest accepted import has another collection commit, else `registry` when it has another snapshot, else `tooling` when it has another application commit, else `catch-up`, which is also the trigger when no import was accepted; and, for a build that succeeded, the outcome `built`, the staged release's name as `release` and the keys of the output of `manifest`, or, for one that failed, the outcome `refused` and as `errors` the lines of the failed command's output that contain `: error: `, or its failure message when there are none.

For a build that succeeded: on `200` with `accepted` the cycle publishes the release (Releases); on `200` with `refused` it records the combination as failed; on `409` with `stale` it records nothing, so that the next cycle builds again with a fresh snapshot; on any other answer, or none, it logs `cannot send the manifest` with the reason and records nothing. A build that failed is recorded as failed once the application has answered its report with `200`; without that answer the cycle logs `cannot send the manifest` and records nothing, so that the next cycle builds it again and reports it then.

#### Scenario: What a manifest holds
- **WHEN** a test runs `sync` once against a fake application that records each manifest
- **THEN** the recorded manifest has `format` 1, a UUID `build`, the collection commit, the snapshot's digest, the application commit as `tooling`, `base` `null`, `pusher` `null`, the outcome `built`, the published release's name, and the `language`, `procedures`, `sequences` and `deleted` the fake `manifest` printed, and was sent with the token and the `Host` of the snapshot request

### Requirement: Forgejo
`deploy/compose.yaml` SHALL run Forgejo as `forge`, from `codeberg.org/forgejo/forgejo:15.0.11-rootless`, keeping its data in the volume `forge`, with port 2222, its SSH server, published, starting once `forge-db` has completed. Its settings come from environment variables, none from a hand-edited file and none substituted by Compose from the shell: as constants in `compose.yaml`, the PostgreSQL database `forge` on `db` as the role `forge`, the installation locked, registration only through an external source, an account created at the first sign-in through one, named by the `nickname` claim, no linking to an existing account, no password sign-in form, the built-in SSH server on port 2222, and `USER_DISABLED_FEATURES` `change_username,deletion`, so that a Forgejo account keeps the lab user name; and, from `orgsyndb.env` at start, the root URL `<ORGSYNDB_URL>/git/` and the database password `FORGE_DB_PASSWORD`, which `deploy/forge/forge-start`, mounted read-only and run as the service's entrypoint, exports before it runs the image's own entrypoint.

`forge-db`, from `postgres:18`, runs once after `db` is healthy and creates the role `forge` with `FORGE_DB_PASSWORD` and the database `forge` it owns when either is missing, so that a database volume made before gains them; it changes nothing that exists. It also makes the root of the volume `pushes`, and the files in it, owned by UID 1000, the user of Forgejo's rootless image and of the builder's image, so that `forge` can append to the push log and `builder` read it.

`deploy/forge/forge-setup`, mounted read-only into `forge` as well and run with `docker compose exec forge`, creates the admin account `orgsyndb` with `ORGSYNDB_FORGE_PASSWORD` when it is missing, adds or updates the OpenID Connect source `lab` with the discovery URL `${ORGSYNDB_APP_INTERNAL_URL}/lab/o/.well-known/openid-configuration`, the client id `forgejo`, `ORGSYNDB_FORGE_CLIENT_SECRET`, the scopes `openid profile email`, the group claim `groups` mapped to the team `authors` of the organisation `lab`, with membership removed when the claim no longer names it; creates, when missing, the public organisation `lab`, its team `authors`, and the public repository `lab/collection` with the default branch `main`, giving the team write access to that repository alone; protects `main`, so that Forgejo refuses a force push to it; links `deploy/forge/gate` into the repository's `hooks/pre-receive.d/` as `orgsyndb-gate` (Gate) and `deploy/forge/push-log` into its `hooks/post-receive.d/` as `orgsyndb-push-log` (Push log); creates the push log when missing and stops with an error naming `ORGSYNDB_PUSH_LOG` when it cannot append to it; and sets up the mirror (Mirror). Run again it changes only what differs. `deploy/orgsyndb.env.example` names `ORGSYNDB_URL`, the address people reach the site at; `ORGSYNDB_OIDC_KEY`, with the command that generates it; `ORGSYNDB_FORGE_CLIENT_SECRET`, `ORGSYNDB_FORGE_PASSWORD` and `FORGE_DB_PASSWORD`, each with how to generate it; `ORGSYNDB_FORGE_URL`, `http://forge:3000/api/v1` by default; `ORGSYNDB_GATE_TOKEN`, with how to generate it; `ORGSYNDB_WAKE_URL`, `http://builder:8091/wake`; `ORGSYNDB_MIRROR_URL`, `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN`, empty, with what a mirror overwrites; and, as `ORGSYNDB_COLLECTION_REPO`, `http://forge:3000/lab/collection.git`, the repository `forge-setup` creates.

#### Scenario: Forgejo's service
- **WHEN** a test runs `docker compose config` as in Compose file
- **THEN** with no `ORGSYNDB_` or `FORGE_` variable in the shell, `forge` uses the pinned image, has `forge-start` as its entrypoint, mounts the volume `forge`, publishes 2222, depends on `forge-db` completing, and its environment sets the database `forge` on `db`, `ENABLE_AUTO_REGISTRATION`, `ACCOUNT_LINKING` `disabled` and `ENABLE_INTERNAL_SIGNIN` `false`, and the output holds no unresolved or empty substitution; `forge-db` depends on `db` being healthy and does not restart

#### Scenario: The start script
- **WHEN** a test runs `deploy/forge/forge-start` with `ORGSYNDB_URL=http://localhost:8080` and `FORGE_DB_PASSWORD=x` in its environment and a stand-in for the image's entrypoint
- **THEN** the stand-in runs with `FORGEJO__server__ROOT_URL=http://localhost:8080/git/` and `FORGEJO__database__PASSWD=x` in its environment

#### Scenario: Creating the database once
- **WHEN** a test runs `forge-db`'s script against a PostgreSQL server twice, skipping without one
- **THEN** after the first run the role and the database `forge` exist, and the second run succeeds and changes nothing

#### Scenario: The push log's volume
- **WHEN** a test reads `deploy/forge/forge-db`
- **THEN** it makes `/var/lib/orgsyndb-pushes` owned by UID 1000

#### Scenario: The set-up script
- **WHEN** a test reads `deploy/forge/forge-setup`
- **THEN** it creates the admin `orgsyndb`, the organisation `lab`, the team `authors`, the repository `lab/collection` and the protection of `main` each only when missing, adds the source `lab` when missing and updates it otherwise, with the discovery URL, the client id `forgejo`, the scopes `openid profile email` and the group claim `groups` mapped to the team `authors`, links the gate into `hooks/pre-receive.d/` and the push log into `hooks/post-receive.d/`, and checks that the push log can be appended to

### Requirement: Gate
`deploy/forge/gate` SHALL be the pre-receive hook of `lab/collection`. For each update of `refs/heads/main` that does not delete it, it sends the new commit with its history, the output of `git pack-objects --stdout --revs` given the commit, by `POST` to `ORGSYNDB_GATE_URL`, `http://builder:8091/check` by default, with the header `X-Orgsyndb-Commit: <commit>` and `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, waiting at most `ORGSYNDB_GATE_TIMEOUT` seconds, 150 by default, a time Forgejo waits for a pre-receive hook over HTTPS and SSH alike. On `200` the update passes. On any other answer, or none in time, the hook writes `Gate: <reason>` and then each line of the answer's body to its standard error, which Forgejo shows the pusher, and exits non-zero, so that Forgejo refuses the push. Updates of other refs pass unchecked. Without `ORGSYNDB_GATE_TOKEN` the hook refuses every update of `main`, saying that the gate is not configured.

`orgsyndb-deploy run` SHALL serve `POST /check` on port 8091 for the hook from a thread beside its cycles, the builder's server, which also answers `POST /wake` (Waking the builder) and runs when `ORGSYNDB_GATE_TOKEN` or `ORGSYNDB_BUILDER_TOKEN` is set. With `ORGSYNDB_GATE_TOKEN` empty, `/check` answers `503` to every request, saying that the gate is not configured. A request without `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, compared in constant time, answers 401; another path or method answers 404 or 405; a body over 200 MB answers 413; one without a commit id of 40 hexadecimal digits in `X-Orgsyndb-Commit` answers 400. One check runs at a time: a request while one runs answers 503 at once, before its body has arrived, saying that the gate is busy and to push again; the server then discards what arrives of that body for at most 2 seconds and closes the connection.

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

#### Scenario: No token, no server
- **WHEN** `run` starts with `ORGSYNDB_BUILDER_TOKEN` and `ORGSYNDB_GATE_TOKEN` both empty
- **THEN** nothing listens on the server's port

#### Scenario: Gate not configured
- **WHEN** the builder's server runs with `ORGSYNDB_BUILDER_TOKEN` set and `ORGSYNDB_GATE_TOKEN` empty, and a test posts a pack to `/check` with any token
- **THEN** the answer is 503, saying that the gate is not configured, and no check ran

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
