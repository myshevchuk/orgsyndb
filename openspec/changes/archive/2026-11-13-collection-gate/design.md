## Context

`forge-accounts` runs Forgejo 15 at `/git/` with sign-in through the
lab app; Forgejo holds no repository yet. The builder clones the
collection from `ORGSYNDB_COLLECTION_REPO`, polls it every
`ORGSYNDB_INTERVAL` seconds, builds, and posts a manifest that the app
accepts or refuses (collection-import). A spike against Forgejo 15.0.11
(`spike-4.md`, third to fifth rounds) settled the behaviour cited
below.

## Goals / Non-Goals

**Goals:**

- The collection lives in Forgejo, and every lab account may push.
- A commit reaches `main` only after the builder has checked it
  against the registry and the tooling as they are at the push, with
  the checks an import makes.

**Non-Goals:**

- A guarantee that the commit is later published: the registry or the
  tooling may change before the build, and the import checks again.
- The push log, the pusher on imports, waking the builder, and the
  mirror to the outside remote: the next change. The builder keeps
  polling.
- The backup of Forgejo's data.

## Decisions

### Repository, team and rights

`forge-setup` creates, when missing, the public organisation `lab`,
its team `authors`, and the public repository `lab/collection` with the
default branch `main`; gives the team write access to that repository
alone; and protects `main` (spike: Forgejo then refuses a force push to
it, and refuses deleting the default branch). Reading needs no
account; writing does.

Every lab account is an author (draft 07: writing needs an account, for
provenance, not secrecy). The source `lab` maps the claim `groups` to
the team (`--group-claim-name groups --group-team-map
'{"authors":{"lab":["authors"]}}' --group-team-map-removal`), and the
lab app's ID token carries `groups: ["authors"]` for every account, so
the first sign-in makes the account an author (spike: membership
follows the claim at each sign-in). The claim is under the scope
`profile`, which Forgejo already asks for.

`USER_DISABLED_FEATURES = change_username, deletion` keeps a Forgejo
account's name the lab user name and leaves deleting accounts to staff
(spike: the settings form's name field is disabled).

### The gate sends the commit itself

`git archive` honours a committed `.gitattributes` (`export-ignore`,
`export-subst`), so an archive can hold other files than the builder's
checkout of the same commit. The gate therefore sends the commit with
its history: `git pack-objects --stdout --revs` of the new tip, which
the hook can read from the quarantine, with the commit's id in the
header `X-Orgsyndb-Commit` (spike: from a pre-receive hook the pack
rebuilds a repository whose checkout holds a file `export-ignore`
dropped from the archive). The builder indexes the pack into a new
repository, points `main` at the commit and checks it out, as a build
does, so the files and the history (`deleted`) are the build's.

`deploy/forge/gate` is the repository's pre-receive hook, which
`forge-setup` links into `lab/collection.git/hooks/pre-receive.d/`
(Forgejo runs every executable there, spike). For an update of
`refs/heads/main` that is not a deletion it posts the pack to
`ORGSYNDB_GATE_URL` (`http://builder:8091/check`) with `curl`, which the
image has (spike), with `Authorization: Bearer <ORGSYNDB_GATE_TOKEN>`,
waiting at most `ORGSYNDB_GATE_TIMEOUT` seconds, 150 by default
(spike: Forgejo waits that long for a pre-receive hook over HTTPS and
SSH alike; its own Git timeout is 360 seconds). It prints each line of
a refusal to stderr, which Forgejo shows the pusher as `remote:` lines
(spike), and exits non-zero; so it does when the builder does not
answer in time or at all, so that `main` never takes an unchecked
commit. Other refs pass: draft 07 checks only `main`.

### The builder's check, apart from its cycle

`orgsyndb-deploy run` serves `POST /check` on port 8091 inside the
compose network from a thread; no port is published and Caddy routes
nothing there. Signals stay with the main thread: on `SIGTERM` it stops
the server, kills a running check's process group and removes its
directory before exiting.

A check shares no file with the cycle, which checks out other
application commits and rewrites the snapshot file while it runs. The
check owns its own clone of the application, `<data>/check/app/`,
which before each check it fetches from the cycle's clone and checks
out, keeping its ignored tool caches, at the application commit of the
published release the cycle's state names (the commit the next build
starts from); and it fetches its own snapshot into the check's
directory. Commands run in a new process group.

One check runs at a time; a second request while one runs answers 503
at once, saying the gate is busy, and the pusher pushes again. A check
has one deadline, `ORGSYNDB_GATE_TIMEOUT` less 10 seconds from its
start, so that it ends before the hook stops waiting: each step's
timeout is the time left, and when it passes the process group is
killed and the answer is 503, saying the check took too long.

The steps: index the pack and check out the commit; `tools/orgsyndb
-C <checkout>/<ORGSYNDB_COLLECTION_PATH> validate` (which exports) and
then `manifest`, with `ORGSYNDB_REGISTRY` naming the check's snapshot;
then the app's check path with the manifest's collection half.

### The app's check path

`POST /lab/collection/check/` takes `language`, `procedures`,
`sequences` and `deleted` as `tools/orgsyndb manifest` prints them,
with the builder token, and answers 200 with `{"errors": [...]}`:
exactly what an import of it would refuse it for (collection-import
"Import checks"), computed as `receive` does, so that before the first
accepted import the manifest's IDs and `deleted` count as issued, as
the first import adopts them; it takes no lock and writes nothing.
Caddy answers 404 for it from outside, as for the manifest path.

### Fetching from Forgejo

The example settings name `http://forge:3000/lab/collection.git` as
`ORGSYNDB_COLLECTION_REPO`; Forgejo serves a public repository without
sign-in. Moving an existing collection in is a one-time push of its
`main` (or the branch it lived on) by an author, through the gate.

## Risks / Trade-offs

- [A slow check holds the push] The pusher waits for the export,
  validation, manifest and the app. → One deadline bounds it; a
  refusal by timeout says so.
- [Two pushes at once] The second is refused as busy. → Pushes to the
  collection's `main` are rare; the message says to push again.
- [The builder down] No push to `main` succeeds while the builder is
  down. → Intended: `main` takes only checked commits.
- [The check and the build disagree] The build runs later, maybe
  against a newer registry or tooling. → The import still checks; a
  refused build stays on the imports page, as today.
