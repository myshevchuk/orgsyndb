## Context

`deploy/backup/orgsyndb-backup` runs in the `backup` service
(`postgres:18`, which has GNU tar and `flock`, no Git) and writes
`lab-<time>.dump` every `ORGSYNDB_BACKUP_HOURS`, keeping
`ORGSYNDB_KEEP_BACKUPS`. The README restores one with `pg_restore`
through `db`, then reconciles IDs issued since the dump (`adopt_ids`).
Forgejo 15.0.11 (rootless) keeps everything in its volume `forge` at
`/var/lib/gitea` (spike, seventh round): `custom/conf/app.ini` with the
generated `SECRET_KEY`, `INTERNAL_TOKEN` and `JWT_SECRET`, signing keys,
SSH host keys, `data/`, `git/repositories/` with each repository's
hooks, and its persistent queues (`queues/`, pending work such as push
updates), indexers and caches. Its database is `forge` on `db`. The
push log is on the volume `pushes`. The lab app stores no files.
`forge-start` is `forge`'s entrypoint and execs the image's own.

## Goals / Non-Goals

**Goals:**

- One backup set holds the data to bring back the lab app, Forgejo,
  the collection and the push log, with `orgsyndb.env` beside it.
- Forgejo's database and files in a set belong together, and every
  commit an import in the set's lab dump names is in the set.
- A restore is a short sequence of commands, tested end to end.

**Non-Goals:**

- Releases and the builder's data: the builder rebuilds them.
- Off-site copies: the operator copies `deploy/backups/`; the push
  mirror keeps a copy of the collection anyway.
- A backup without pausing Forgejo, or at a fixed time of day.

## Decisions

### Forgejo is paused while its data is copied

Copying a running Forgejo pairs a database dump with repositories,
queues and files from another moment: a repository created, deleted or
pushed to in between, or queued work such as a push's database update,
leaves the restored database and files disagreeing (Forgejo's own
backup guide stops it first). The backup service cannot stop a
container without Docker's socket, which it must not have. So Forgejo
pauses on request: `forge-start` runs the image's entrypoint as a
child instead of exec'ing it and checks every 2 seconds for the file
`pause` in `/var/lib/orgsyndb-forge-control`, a new volume
`forge-control` that `forge` and `backup` share.

Before stopping Forgejo, `forge-start` waits until no push is in
flight: no process of the container runs `git receive-pack`. The
end-to-end run showed why: stopped while a push sat in its gate check,
Forgejo closed its listeners, the push still updated `main` and wrote
its push-log line, but Forgejo's own post-receive call failed, and the
push is missing from Forgejo's records (its activity, its mirror
trigger). While `pause` exists the gate refuses every push to
`lab/collection`, so that no new push starts meanwhile; pushes to
other repositories are only waited for.

The backup, which runs as root, makes the control directory UID
1000's before it writes `pause`: podman hands a volume that is empty
when a container mounts it to that container's user, so the backup's
own mount would otherwise lock `forge-start` out (seen end to end).

The request carries an id unique to the backup run, and `paused`
acknowledges that id, so that an acknowledgement left by a crash, or
by the run before, is never taken for the current one; `forge-start`
also removes `paused` when it starts. To acknowledge, it stops Forgejo
with SIGTERM and waits for it, then waits until no other process of
the container but the init process and itself remains, and only then
writes the id to `paused`. It signals none of them: Git runs
post-receive after updating the refs, so killing a push-log hook still
running would leave an accepted push without its line. A process that
never ends leaves the request unacknowledged, and the backup times out
and fails rather than copy a Forgejo still writing. Once `pause` is
gone it removes `paused` and starts Forgejo again. A pause ends by
itself after `ORGSYNDB_FORGE_PAUSE_LIMIT` seconds (an hour), so that a
backup that died with its request in place does not keep Forgejo down;
`forge-start` then removes that `pause` too. The backup checks, after
its last copy, that `paused` still holds its id, and discards the set
otherwise: a set is published only when Forgejo stayed paused
throughout. When Forgejo exits on its own, `forge-start` exits with its
status, so that Compose restarts the container; SIGTERM stops Forgejo
and then `forge-start`. `forge` gets an init process, since
`forge-start` is no longer replaced by one.

While paused, pushes and Forgejo's pages fail; the builder's fetch
fails and it keeps its last commit (Update cycle). A pause lasts the
database dump and the archive, seconds for a lab's data, plus Forgejo's
stop and start.

### A set per run, all of it inside one pause

`once` takes `flock` on `<dir>/.lock`, so a second run waits for the
first, then writes `<dir>/.orgsyndb-<stamp>.partial/` and renames it to
`orgsyndb-<stamp>/` when every part is written, waiting for the next
second when that name exists; a failed part removes the partial set
and fails the run. It pauses Forgejo first (up to
`ORGSYNDB_FORGE_PAUSE_TIMEOUT` seconds, 300), then writes, in order,
`lab.dump`, `pushes.log`, `forge.dump` and `forge.tar` (the whole
Forgejo directory, numeric owners, modes and symbolic links kept),
checks the pause still holds, resumes Forgejo (also when a part
failed), and copies `orgsyndb.env`.

The lab database is dumped inside the pause, not before it. Forgejo
binds an account to the lab account's numeric id (the OpenID subject):
an account created and signed in to Forgejo between a lab dump taken
outside the pause and Forgejo's copy would exist in Forgejo's part
only, and after a restore the lab could give its number to someone
else. Inside the pause no sign-in, push or other Forgejo write
happens, so every Forgejo account names a lab account in the set, and
every commit and push line an import names is in it. The lab app keeps
running; `pg_dump` takes its own consistent snapshot. Its writes to
Forgejo during the pause (account sync) fail as they do whenever
Forgejo is down; `manage.py forge_accounts` brings Forgejo in line.

Without the Forgejo directory (`ORGSYNDB_FORGE_DATA`, `/var/lib/gitea`
by default) the run pauses nothing, writes `lab.dump` and
`orgsyndb.env` only, and logs that Forgejo was not backed up. When
Forgejo does not pause in time (stopped, or slow), the run fails,
removes `pause` and says so.

`ORGSYNDB_KEEP_BACKUPS` counts complete sets; partial sets are removed
under the lock, so only those of crashed runs. Files are root's with
mode 600, directories 700: a set holds password hashes, Forgejo's
secrets and `orgsyndb.env`. Earlier `lab-*.dump` files are left alone.

### Restore

`orgsyndb-backup restore <set>` runs in a Compose service `restore`:
`postgres:18` with the backup script, profile `restore` (so a plain
`up` leaves it out; `docker compose run` starts it when asked), with
`backups/` read-only and the volumes `forge`, `pushes` and `data`
read-write. With every service stopped but `db` and `forge-db`, it:

1. checks the set before changing anything: it exists, has
   `lab.dump`, and has both `forge.dump` and `forge.tar` or neither (a
   lab-only set comes from a deployment without Forgejo; one part alone
   is an incomplete set);
2. drops the lab database, with its connections, creates it again owned
   by `POSTGRES_USER` and restores `lab.dump` into the empty database;
   then the same for `forge`, owned by `forge` (`forge-db` has made the
   role). Restoring into empty databases leaves no object of a newer
   schema behind, which `pg_restore --clean` would. In `forge` it then
   deletes the rows of `push_mirror`: the restored Forgejo would
   otherwise sync its push mirror soon after starting, overwriting the
   mirror's newer history with the set's older one before the operator
   has taken from it what came after the set. `forge-setup` adds the
   mirror again at the end of the recovery;
3. empties the Forgejo directory and extracts `forge.tar` with its
   numeric owners, modes and symbolic links: hooks, the links to the
   gate and the push log (targets under `/opt/orgsyndb/forge/`, which
   Compose mounts), queues and secrets come back as they were;
4. copies `pushes.log` back, owned by UID 1000;
5. removes the builder's clone of the collection, `<data>/collection`,
   so that the builder cannot fall back to a commit pushed after the
   set when its first fetch fails;
6. prints the next steps.

The next steps keep a recovery boundary: start every service but
`web` and `builder`, so that nobody reaches the lab app to be issued an
ID, nobody reaches Forgejo over HTTP, and nothing is built yet; clear
the builder's failed builds with `docker compose run --rm builder
orgsyndb-deploy retry` while `builder` is stopped (a running cycle
saves the state it loaded and would bring the failures back), since a
combination recorded as failed before is not built again; start
`builder` alone, since the gate asks its check about every push to
`main` and refuses the push when it cannot (found while writing the
README); reconcile the IDs issued after the set (`adopt_ids`, as the
README describes) and, when a mirror was configured, push the commits
it holds beyond the set to `lab/collection` over SSH, which needs no
`web` (the gate names their unissued IDs; the push log names the
operator as their pusher); start `web`; run `forge-setup`, which adds the mirror
again. The images must be
of the set's version or newer: an older application or Forgejo cannot
read a newer schema.

On the same server the builder keeps its releases and state: it points
`current` at the release of the restored latest accepted import when
it still has it, then builds `main` of the restored collection when it
differs. On a new server it builds `main` against the restored
registry. `orgsyndb.env` is restored by hand, first: the restore reads
its credentials.

## Risks / Trade-offs

- Forgejo is unavailable for each backup's pause; `run` backs up at
  its start and then every `ORGSYNDB_BACKUP_HOURS`, at whatever time of
  day that falls.
- A stopped `forge` makes every backup fail until it runs again, the
  lab database's included: a set is all of it or nothing.
- Every set is a full copy; size grows with the repositories and
  attachments, times `ORGSYNDB_KEEP_BACKUPS`.
- A restore empties Forgejo's directory: with the wrong set it loses
  what came after. The README says to take a set first.

## To verify during implementation (end-to-end run)

- `forge-start` against Forgejo 15.0.11 with PostgreSQL: pause and
  resume, also with a push in flight (its push-log line written before
  `paused`); a stale `paused` at
  start; a pause past its limit; the container still stops on `docker
  compose stop`; Forgejo's secrets survive repeated restarts.
- Back up a running deployment, wipe both databases and the volumes,
  restore, start without `web`, `retry`, then `web`: sign-in through
  the lab works, `lab/collection` has its history and hooks, a push
  passes the gate and is logged, the source's secret still decrypts,
  issue search works, and the restored Forgejo has no push mirror.
  Once more on the same server with the builder's state kept.
