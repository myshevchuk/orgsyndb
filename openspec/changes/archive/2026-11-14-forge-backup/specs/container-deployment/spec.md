## RENAMED Requirements

- FROM: `### Requirement: Database backups`
- TO: `### Requirement: Backups`

## MODIFIED Requirements

### Requirement: Backups
`deploy/backup/orgsyndb-backup` SHALL be an executable POSIX shell script with the subcommands `run`, the default, `once` and `restore <set>`. Its settings: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, the lab database on host `db`; `ORGSYNDB_BACKUP_DIR`, default `/backups`; `ORGSYNDB_KEEP_BACKUPS`, default 14; `ORGSYNDB_BACKUP_HOURS`, default 24; `ORGSYNDB_FORGE_DATA`, Forgejo's directory, default `/var/lib/gitea`; `ORGSYNDB_FORGE_CONTROL`, the directory of Forgejo's pause (Forgejo), default `/var/lib/orgsyndb-forge-control`; `ORGSYNDB_FORGE_PAUSE_TIMEOUT`, default 300 seconds; `ORGSYNDB_PUSH_LOG`, default `/var/lib/orgsyndb-pushes/pushes.log` (Push log); `ORGSYNDB_SETTINGS_FILE`, default `/opt/orgsyndb/orgsyndb.env`; and, for `restore`, `ORGSYNDB_DATA`, the builder's data, default `/var/lib/orgsyndb`. A malformed number exits 1 naming the variable; an unknown subcommand, or `restore` without one set name, exits 2 with a usage line.

`once` holds an exclusive `flock` on `<dir>/.lock`, `<dir>` being `ORGSYNDB_BACKUP_DIR`, so that runs follow one another, and writes a backup set: a directory `<dir>/orgsyndb-<UTC time as YYYYMMDDTHHMMSSZ>/`, built as `<dir>/.orgsyndb-<time>.partial/` and renamed when complete; when a set of that name exists, it waits for the next second. When `ORGSYNDB_FORGE_DATA` is a directory, it first pauses Forgejo: when run as root it makes `ORGSYNDB_FORGE_CONTROL` owned by UID 1000, since a container engine may hand a volume that is empty when it is mounted to the mounting container's user; it writes the file `pause` in `ORGSYNDB_FORGE_CONTROL` holding a request id unique to the run, replacing a `pause` a crashed run left, and waits until the file `paused` there holds that id, at most `ORGSYNDB_FORGE_PAUSE_TIMEOUT` seconds. Then, in this order, it:

1. writes `lab.dump`, `pg_dump` in custom format of `POSTGRES_DB` as `POSTGRES_USER` with `POSTGRES_PASSWORD`;
2. copies the push log as `pushes.log`, when it exists;
3. writes `forge.dump`, `pg_dump` in custom format of the database `forge` as `POSTGRES_USER`;
4. writes `forge.tar`, a tar archive of the whole of `ORGSYNDB_FORGE_DATA` with numeric owners, modes and symbolic links kept;
5. checks that `paused` still holds its request id, and fails, saying Forgejo resumed during the backup, when it does not;
6. removes `pause`, whether or not the steps before succeeded;
7. copies `ORGSYNDB_SETTINGS_FILE` as `orgsyndb.env`, when it exists.

Without the Forgejo directory, it pauses nothing, writes only steps 1 and 7, and logs that Forgejo was not backed up. Every file of a set is readable by its owner only. On SIGTERM, SIGINT or SIGHUP, in `once` and in `run` alike, the run stops its current step, removes `pause` when it wrote it and its partial set, and exits, so that a stopped container leaves Forgejo running. When a step fails, or `paused` does not hold the request id in time, the partial set is removed and `once` exits 1 with `orgsyndb-backup: error:` and the reason on stderr, the timeout's naming Forgejo's pause. After a complete set, all but the `ORGSYNDB_KEEP_BACKUPS` newest `orgsyndb-*` sets are removed, and so is every partial set; other files in the directory are left alone. `run` writes a set as `once` does every `ORGSYNDB_BACKUP_HOURS` hours, starting at once, logs a failed run and keeps going.

`restore <set>` restores the set `<dir>/<set>`. It exits 1 before changing anything when the set does not exist, lacks `lab.dump`, or holds only one of `forge.dump` and `forge.tar`. It drops `POSTGRES_DB`, with its connections, and creates it again owned by `POSTGRES_USER`, then restores `lab.dump` into it with `pg_restore`; when the set holds Forgejo's parts, it does the same for `forge`, owned by the role `forge`, with `forge.dump`, deletes every row of Forgejo's table `push_mirror` there, when that table exists (a set taken before Forgejo's first start holds an empty `forge`), so that the restored Forgejo cannot overwrite the mirror's newer history (Mirror), then empties `ORGSYNDB_FORGE_DATA` and extracts `forge.tar` into it with its numeric owners, modes and symbolic links; it copies `pushes.log`, when the set has it, to `ORGSYNDB_PUSH_LOG`, owned by UID 1000 when run as root; and it removes `<ORGSYNDB_DATA>/collection`, the builder's clone of the collection. A set without Forgejo's parts restores the rest and says so. It then prints the next steps: start every service but `web` and `builder`; clear the builder's failed builds with `docker compose run --rm builder orgsyndb-deploy retry` while `builder` is stopped; start `builder`, which the gate asks about every push to `main`, with `web` still stopped; reconcile the IDs issued after the set and, when a mirror was configured, push the commits it holds beyond the set to `lab/collection` over SSH, the gate naming any ID still to adopt; start `web`; run `forge-setup`, which adds the mirror again. A failed step exits 1 naming it.

#### Scenario: A backup set
- **WHEN** a test runs `once` with fake `pg_dump` on `PATH`, `ORGSYNDB_FORGE_DATA` naming a directory with `custom/conf/app.ini`, `queues/x`, a repository `git/repositories/lab/collection.git` and a symbolic link in its `hooks/post-receive.d/`, a stand-in for Forgejo that writes the id of `pause` to `paused` when `pause` appears and removes `paused` when `pause` is gone, a push log and a settings file
- **THEN** one set `orgsyndb-*` exists holding `lab.dump` and `forge.dump` with the fakes' outputs for the two databases, `pushes.log`, `orgsyndb.env`, and `forge.tar` holding `custom/conf/app.ini`, `queues/x`, the repository's files and the link as a link; `pause` is gone; and no file of the set is readable by others

#### Scenario: Everything inside the pause
- **WHEN** the fake `pg_dump` records each call and the content of `paused` at that moment
- **THEN** both databases were dumped while `paused` held the run's request id

#### Scenario: The control directory's owner
- **WHEN** a test reads the script
- **THEN** before writing `pause` it changes the owner of `ORGSYNDB_FORGE_CONTROL` to 1000 when it runs as root

#### Scenario: A stale acknowledgement
- **WHEN** `ORGSYNDB_FORGE_CONTROL` holds a `paused` with another id and no stand-in answers, with `ORGSYNDB_FORGE_PAUSE_TIMEOUT` at 2
- **THEN** `once` exits 1 within about 4 seconds, stderr names Forgejo's pause, `pause` is gone, and no set and no partial set exists

#### Scenario: Forgejo resumes during the backup
- **WHEN** the stand-in removes `paused` while `forge.tar` is written
- **THEN** `once` exits 1 saying Forgejo resumed during the backup, `pause` is gone, and no set and no partial set exists

#### Scenario: A failed part
- **WHEN** the fake `pg_dump` fails for `forge`
- **THEN** `once` exits 1, stderr starts with `orgsyndb-backup: error:`, `pause` is gone, and no set and no partial set exists

#### Scenario: Pruning sets
- **WHEN** the backup directory holds 14 older sets, a partial set and a `lab-20260101T000000Z.dump`, and `once` runs with `ORGSYNDB_KEEP_BACKUPS` unset
- **THEN** 14 sets remain, the oldest and the partial one are gone, and the old dump is still there

#### Scenario: One run at a time
- **WHEN** a test holds the lock on `<dir>/.lock` and starts `once`, then releases the lock after 2 seconds; and separately runs `once` twice in a row without Forgejo
- **THEN** the first `once` wrote no set while the lock was held, and one afterwards; the two runs in a row wrote two sets

#### Scenario: Without Forgejo
- **WHEN** `ORGSYNDB_FORGE_DATA` names a missing directory
- **THEN** the set holds `lab.dump` and `orgsyndb.env` only, no `pause` was created, and the output says Forgejo was not backed up

#### Scenario: A restore
- **WHEN** a test runs `restore` on the set of A backup set, with fake `psql` and `pg_restore` that record their calls, `ORGSYNDB_FORGE_DATA` holding a stray file, an empty push log and `ORGSYNDB_DATA` holding `collection/x`
- **THEN** both databases were dropped and created again, the lab one owned by `POSTGRES_USER` and `forge` by `forge`, `pg_restore` restored `lab.dump` and `forge.dump` into them, the rows of `push_mirror` in `forge` were deleted after that, the stray file is gone, `custom/conf/app.ini`, `queues/x`, the repository's files and the link are back, the push log equals the saved one, `collection` is gone from `ORGSYNDB_DATA`, and the output names `web`, `builder`, `orgsyndb-deploy retry`, the ID reconciliation and `forge-setup`, with `docker compose up -d builder` before the reconciliation, which names SSH, and `docker compose up -d web` after it

#### Scenario: A set of a Forgejo never started
- **WHEN** a test runs `restore` on a complete set with a fake `psql` that fails any statement naming `push_mirror` unless it guards for the table's existence
- **THEN** the restore succeeds and the SQL sent to `forge` deletes the rows of `push_mirror` only when the table exists

#### Scenario: Stopping a backup
- **WHEN** a test sends SIGTERM to `orgsyndb-backup`, run with `once` and, separately, with `run`, while its fake `pg_dump` of `forge` sleeps inside the pause
- **THEN** within about 3 seconds the script has exited, `pause` is gone, no partial set remains and the fake `pg_dump` no longer runs

#### Scenario: An incomplete set
- **WHEN** a test runs `restore` on a set that does not exist, on one without `lab.dump`, and on one holding `forge.dump` but no `forge.tar`
- **THEN** each exits 1, no database command ran, and `ORGSYNDB_FORGE_DATA` is unchanged

#### Scenario: Usage
- **WHEN** a test runs the script with `nonsense`, and with `restore` and no set
- **THEN** both exit 2 with a usage line

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, answer `404` for every path beginning with `/lab/collection/manifest` or `/lab/collection/check`, forward `/lab/` and every other path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default, and forward every path below `/git/`, with `/git` taken off, to Forgejo at `ORGSYNDB_FORGE_UPSTREAM`, `forge:3000` by default, redirecting `/git` to `/git/`. It sets the header `Cache-Control: no-cache` on every response but Forgejo's, which sets its own, and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process and `ORGSYNDB_LAB=true` in its environment, so that the site it builds links the lab application's views, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`, and `builder` mounting the volume `pushes` read-only at `/var/lib/orgsyndb-pushes` (Push log);
- `db`, from `postgres:18`, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb` and starting once `db` is healthy;
- `backup`, from `postgres:18`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`, `orgsyndb.env` read-only at `/opt/orgsyndb/orgsyndb.env`, the volumes `forge` and `pushes` read-only at `/var/lib/gitea` and `/var/lib/orgsyndb-pushes`, and `forge-control` read-write at `/var/lib/orgsyndb-forge-control` (Backups);
- `restore`, from `postgres:18` with the same script, only in the profile `restore`, running `orgsyndb-backup restore`, with `deploy/backups/` read-only and the volumes `forge`, `pushes` and `data` read-write at `/var/lib/gitea`, `/var/lib/orgsyndb-pushes` and `/var/lib/orgsyndb`, starting once `db` is healthy and `forge-db` has completed, since the restore creates `forge` owned by the role `forge`;
- `forge-db` and `forge` (Forgejo), both mounting the volume `pushes` read-write at `/var/lib/orgsyndb-pushes`.

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, `ORGSYNDB_ALLOWED_HOSTS`, with `app` among the hosts, `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token, and the settings of Forgejo with how to generate each secret. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*`, `reverse_proxy`, `/lab/collection/manifest*` and `/lab/collection/check*`, each answered with `404` ahead of the `/lab/*` route, and `/git/*` with `handle_path`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app`, `backup`, `forge-db` and `forge`, with `restore` only under the profile `restore`, `backup` mounts `forge` and `pushes` read-only and `forge-control` read-write, `restore` mounts `forge`, `pushes` and `data` read-write and depends on `forge-db` completing, `builder` runs `orgsyndb-deploy run`, reads the settings and has `ORGSYNDB_LAB` set to `true`, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, `app` receives the example's `ORGSYNDB_DATABASE_URL`, `builder` mounts `pushes` read-only and `forge` and `forge-db` mount it read-write

### Requirement: Forgejo
`deploy/compose.yaml` SHALL run Forgejo as `forge`, from `codeberg.org/forgejo/forgejo:15.0.11-rootless`, keeping its data in the volume `forge`, with an init process, the volume `forge-control` at `/var/lib/orgsyndb-forge-control`, port 2222, its SSH server, published, starting once `forge-db` has completed. Its settings come from environment variables, none from a hand-edited file and none substituted by Compose from the shell: as constants in `compose.yaml`, the PostgreSQL database `forge` on `db` as the role `forge`, the installation locked, registration only through an external source, an account created at the first sign-in through one, named by the `nickname` claim, no linking to an existing account, no password sign-in form, the built-in SSH server on port 2222, and `USER_DISABLED_FEATURES` `change_username,deletion`, so that a Forgejo account keeps the lab user name; and, from `orgsyndb.env` at start, the root URL `<ORGSYNDB_URL>/git/` and the database password `FORGE_DB_PASSWORD`, which `deploy/forge/forge-start`, mounted read-only and run as the service's entrypoint, exports before it runs the image's own entrypoint, given as its arguments, as a child. It pauses Forgejo for a backup (Backups) through the directory `/var/lib/orgsyndb-forge-control`, or the one `ORGSYNDB_FORGE_CONTROL` names: at start it removes a `paused` there and does not start the child while a `pause` exists; every 2 seconds it checks for `pause`. When `pause` holds a request id `paused` does not, it first waits until no push is in flight, no process of the container running `git receive-pack`, since stopping Forgejo during a push loses Forgejo's own processing of it; meanwhile the gate refuses new pushes (Gate). Then it stops the child with SIGTERM and waits for it, then waits, without signalling them, until no other process of the container but its init process and itself remains, so that a hook of a push in flight finishes its work, and only then writes the id to `paused`; a process that never ends leaves the request unacknowledged, and the backup times out. Once `pause` is gone it removes `paused` and starts the child again. A pause that lasts `ORGSYNDB_FORGE_PAUSE_LIMIT` seconds, an hour by default, ends: it logs that, removes `paused` and the `pause` holding that id, and starts the child. When the child exits while no pause holds, `forge-start` exits with its status; on SIGTERM or SIGINT it stops the child, waits for it and exits 0.

`forge-db`, from `postgres:18`, runs once after `db` is healthy and creates the role `forge` with `FORGE_DB_PASSWORD` and the database `forge` it owns when either is missing, so that a database volume made before gains them; it changes nothing that exists. It also makes the roots of the volumes `pushes` and `forge-control`, and the files in them, owned by UID 1000, the user of Forgejo's rootless image and of the builder's image, so that `forge` can append to the push log, `builder` read it, and `forge` answer a pause.

`deploy/forge/forge-setup`, mounted read-only into `forge` as well and run with `docker compose exec forge`, creates the admin account `orgsyndb` with `ORGSYNDB_FORGE_PASSWORD` when it is missing, adds or updates the OpenID Connect source `lab` with the discovery URL `${ORGSYNDB_APP_INTERNAL_URL}/lab/o/.well-known/openid-configuration`, the client id `forgejo`, `ORGSYNDB_FORGE_CLIENT_SECRET`, the scopes `openid profile email`, the group claim `groups` mapped to the team `authors` of the organisation `lab`, with membership removed when the claim no longer names it; creates, when missing, the public organisation `lab`, its team `authors`, and the public repository `lab/collection` with the default branch `main`, giving the team write access to that repository alone; protects `main`, so that Forgejo refuses a force push to it; links `deploy/forge/gate` into the repository's `hooks/pre-receive.d/` as `orgsyndb-gate` (Gate) and `deploy/forge/push-log` into its `hooks/post-receive.d/` as `orgsyndb-push-log` (Push log); creates the push log when missing and stops with an error naming `ORGSYNDB_PUSH_LOG` when it cannot append to it; and sets up the mirror (Mirror). Run again it changes only what differs. `deploy/orgsyndb.env.example` names `ORGSYNDB_URL`, the address people reach the site at; `ORGSYNDB_OIDC_KEY`, with the command that generates it; `ORGSYNDB_FORGE_CLIENT_SECRET`, `ORGSYNDB_FORGE_PASSWORD` and `FORGE_DB_PASSWORD`, each with how to generate it; `ORGSYNDB_FORGE_URL`, `http://forge:3000/api/v1` by default; `ORGSYNDB_GATE_TOKEN`, with how to generate it; `ORGSYNDB_WAKE_URL`, `http://builder:8091/wake`; `ORGSYNDB_MIRROR_URL`, `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN`, empty, with what a mirror overwrites; and, as `ORGSYNDB_COLLECTION_REPO`, `http://forge:3000/lab/collection.git`, the repository `forge-setup` creates.

#### Scenario: Forgejo's service
- **WHEN** a test runs `docker compose config` as in Compose file
- **THEN** with no `ORGSYNDB_` or `FORGE_` variable in the shell, `forge` uses the pinned image, has `forge-start` as its entrypoint, mounts the volume `forge`, publishes 2222, depends on `forge-db` completing, and its environment sets the database `forge` on `db`, `ENABLE_AUTO_REGISTRATION`, `ACCOUNT_LINKING` `disabled` and `ENABLE_INTERNAL_SIGNIN` `false`, and the output holds no unresolved or empty substitution; `forge-db` depends on `db` being healthy and does not restart

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

### Requirement: Gate
`deploy/forge/gate` SHALL be the pre-receive hook of `lab/collection`. For each update of `refs/heads/main` that does not delete it, it sends the new commit with its history, the output of `git pack-objects --stdout --revs` given the commit, by `POST` to `ORGSYNDB_GATE_URL`, `http://builder:8091/check` by default, with the header `X-Orgsyndb-Commit: <commit>` and `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`, waiting at most `ORGSYNDB_GATE_TIMEOUT` seconds, 150 by default, a time Forgejo waits for a pre-receive hook over HTTPS and SSH alike. On `200` the update passes. On any other answer, or none in time, the hook writes `Gate: <reason>` and then each line of the answer's body to its standard error, which Forgejo shows the pusher, and exits non-zero, so that Forgejo refuses the push. Updates of other refs pass unchecked. Without `ORGSYNDB_GATE_TOKEN` the hook refuses every update of `main`, saying that the gate is not configured. While the file `pause` exists in `ORGSYNDB_FORGE_CONTROL`, `/var/lib/orgsyndb-forge-control` by default (Backups), the hook refuses every update, of any ref, writing `Gate: a backup is running; push again in a few minutes`, without asking the check.

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

#### Scenario: During a backup
- **WHEN** a test runs `deploy/forge/gate` with `ORGSYNDB_FORGE_CONTROL` naming a directory holding `pause`, against a fake check server, feeding it an update of `refs/heads/main` and one of `refs/heads/draft`
- **THEN** the hook exits non-zero, its standard error holds `Gate: a backup is running`, and the fake received nothing
