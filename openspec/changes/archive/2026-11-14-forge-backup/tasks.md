## 1. Tests

- [x] 1.1 `orgsyndb-backup once`: a set's parts, everything inside the pause, a stale acknowledgement, Forgejo resuming during the backup, a failed part, pruning sets and partial ones, one run at a time and two in a row, without Forgejo
- [x] 1.2 `orgsyndb-backup restore`: both databases dropped, created and restored, Forgejo's volume with its links, the push log, the builder's clone, the next steps, incomplete sets, usage
- [x] 1.3 `forge-start`: the child's environment, pausing with the request id and resuming, a stale acknowledgement at start, a pause past its limit, exiting with the child's status, SIGTERM
- [x] 1.4 Deployment: compose's `backup`, `restore` and `forge` services and the volume `forge-control`, `forge-db`'s ownership
- [x] 1.5 The gate refusing pushes during a pause; `forge-start` waiting for a push in flight; the backup owning the control directory

## 2. Implementation

- [x] 2.1 `orgsyndb-backup`: sets, the pause, pruning, the lock, `restore`
- [x] 2.2 `forge-start`'s pause, `forge-db`, compose
- [x] 2.3 Local end-to-end run with PostgreSQL and Forgejo 15.0.11: pause and resume (idle, a push in flight, a stale acknowledgement, past the limit, `docker compose stop`); back up, wipe, restore, start without `web`, `retry`, `web`; sign-in, history and hooks, a gated and logged push, the source's secret readable, issue search; a same-server restore with the builder's state kept
- [x] 2.4 The end-to-end run's findings: the gate refusing pushes during a pause, `forge-start` waiting for pushes in flight, the backup owning the control directory
- [x] 2.5 The restore's next steps start `builder` before the ID reconciliation, so that recovered commits pass the gate, and `web` after it
- [x] 2.6 Review findings: a stopped backup withdraws its pause; `restore` waits for `forge-db`; a set of a Forgejo never started restores

## 3. Docs and archive

- [x] 3.1 README: back up and restore (sets, Forgejo's pause, restoring step by step, `orgsyndb.env`, IDs after a restore), the service list
- [x] 3.2 Review, then archive
- [ ] 3.3 Test server, by the owner: rebuild; a set is written with every part and Forgejo comes back; optionally a restore rehearsal
