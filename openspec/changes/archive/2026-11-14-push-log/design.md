## Context

`collection-gate` made `lab/collection` in Forgejo the collection's
home and put the gate in front of `main`. The builder fetches from
there every `ORGSYNDB_INTERVAL` seconds (300 by default), or at once on
SIGHUP, and its server on port 8091 answers the gate's `POST /check`.
An import records what was built and why (`trigger`), not who pushed.
The spike against Forgejo 15.0.11 (`spike-4.md`) found that hooks see
`GITEA_PUSHER_ID` and `GITEA_PUSHER_NAME`, that a post-receive hook can
append to a file on a volume, once per accepted push, over HTTPS, SSH
and the API, and that `POST /repos/{owner}/{repo}/push_mirrors` with
basic auth as the admin creates a push mirror.

## Goals / Non-Goals

**Goals:**

- Every import names the account that pushed the commit it was built
  from, as Forgejo reports it.
- A push, or a registry change, starts a build within seconds.
- The collection's outside remote receives every change to
  `lab/collection`.

**Non-Goals:**

- The backup of Forgejo's data: the next change.
- The pusher of a commit pushed before this change, or of a collection
  outside Forgejo: none is recorded.
- Mirroring over SSH; mirrors other than the one `forge-setup` adds.

## Decisions

### The push log is a file Forgejo appends to

Draft 07: the log, not the wake-up, is what counts. The post-receive
hook `deploy/forge/push-log` appends one line per accepted update of
`refs/heads/main` that does not delete it, `<time> <commit> <id>
<name>`: the time in UTC as `YYYY-MM-DDTHH:MM:SSZ`, the new commit,
`GITEA_PUSHER_ID` and `GITEA_PUSHER_NAME`, each `-` when unset. The
line is built first and written with one write to the file opened for
appending: `O_APPEND` places each write at the end, and Linux
serializes writes to one regular file on a local file system, so
concurrent pushes add whole lines (a test runs hooks concurrently; the
end-to-end run checks the image's shell). Post-receive runs only after
the update is accepted (spike), and its exit status does not undo it.

The file lives on a new volume `pushes`, mounted read-write into
`forge` and read-only into `builder` at `/var/lib/orgsyndb-pushes`.
Posting the line to the builder instead would lose it while the
builder is down; a Git ref such as `refs/notes/` would be writable by
every author. Forgejo's rootless image and the builder's image both run
as UID 1000; `forge-db`, which already runs once as root before
`forge` starts, makes the volume's root owned by UID 1000, so the
first mount does not decide its ownership; it also hands it the
files already there, the log among them.

### The pusher is resolved by user name

The builder reads the log when it makes the manifest of commit C,
after the build's commands have run, and takes the name of the last
line naming C; no line, or `-`, gives `null`. Reading it then, not at
the fetch, covers a cycle that fetched C between Forgejo's update of
`main` and the hook's append: the hook appends within moments of the
update, a build takes longer. A line appended after the manifest was
made is not used, and that import keeps no pusher; the next import of
C, after a registry or tooling change, names it. A build
triggered by a registry change or new tooling names the same pusher:
the pusher belongs to the commit (draft 07). The manifest carries the
name as `pusher`, and the app sets `pushed_by` to the account with
that user name, compared case-insensitively, or none when no account
has it (Forgejo's own admin `orgsyndb`).

A Forgejo account is named by the `nickname` claim, the lab user name,
and neither side can rename it (`forge-accounts`, `collection-gate`),
so the name identifies the account. Forgejo's numeric id, which the lab
does not hold, stays in the log for the record; resolving it would need
Forgejo's admin API at push or import time.

### Waking the builder

The builder's server answers `POST /wake` with `202` and sets the same
event SIGHUP sets: an idle builder starts a cycle at once, a busy one
runs one more after the current cycle, however many wake-ups came. It
takes `Authorization: Bearer` with `ORGSYNDB_GATE_TOKEN`, which the
hook holds, or `ORGSYNDB_BUILDER_TOKEN`, which the app holds. The
server now runs when either token is set; without the gate token,
`/check` answers `503`, saying the gate is not configured.

The hook wakes the builder after appending, at `ORGSYNDB_WAKE_URL`
(`http://builder:8091/wake` by default), waiting at most 5 seconds; a
failure tells the pusher that the builder builds the push at its next
check. The poll stays as the backstop for a lost wake-up.

The app wakes the builder once per committed transaction that saved
or deleted a row the snapshot's digest covers, whatever fields
changed: the writes One lock has take the lock for those rows,
through a model's `save` and `delete`, the bulk querysets,
`User.save` and `snapshot.load`. The wake-up is registered beside
that lock, not in `hold()`, which imports, issued IDs and task steps
take too. It is sent when
`ORGSYNDB_WAKE_URL` is set (the example sets it; empty by default, so
a development server tries nothing). It posts with the builder token
and a 2-second timeout after the commit, logs a failure as a warning
and never fails the write. A wake-up after a write that left the
digest unchanged, such as a booking that creates an article without
a number, costs one cycle that builds nothing. Imports, issued IDs and
task steps wake nothing. A registration made inside a savepoint that
is rolled back is dropped with it, and a later write in the same
transaction registers again.

### The mirror

`forge-setup`, when `ORGSYNDB_MIRROR_URL` (an `https://` address) is
set, removes the push mirrors of `lab/collection` to that address and
adds one with `ORGSYNDB_MIRROR_USER` and `ORGSYNDB_MIRROR_TOKEN`,
`sync_on_commit` on and an interval of 8 hours, so that a run applies
changed credentials. Without the setting it changes no mirror. A push
mirror makes the target a copy, all branches and tags, so the target
must serve as nothing else: the collection's old remote, which nobody
pushes to any more (draft 07). Forgejo refuses mirror addresses on
local networks unless `[migrations] ALLOW_LOCALNETWORKS` is set.

## Risks / Trade-offs

- A push accepted while the log cannot be written leaves its imports
  without a pusher; the hook tells the pusher, and `forge-setup`
  checks that the log is writable.
- A lost wake-up delays the build until the next poll.
- The log grows by one short line per push and is never trimmed.

## Verified, and to verify

- Spike, sixth round (Forgejo 15.0.11): a push to the source syncs the
  mirror within seconds; the target's `main` is replaced even with
  unrelated history, and a branch only the target has is deleted, also
  with a branch filter of `main`. Hence the warning.
- Local end-to-end run before review (task 2.5): `forge-db`'s
  ownership change on a fresh and an existing volume, `forge`
  appending and `builder` reading; a push over HTTPS and over SSH
  logged with its pusher and waking the builder; the image's shell
  appending whole lines; the mirror added by `forge-setup` synced by a
  push.
