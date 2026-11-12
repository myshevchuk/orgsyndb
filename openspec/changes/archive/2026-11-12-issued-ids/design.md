## Context

`pipeline.next_id` picks the next `OSDB-NNNN` from the clone's files
and git history. Since `collection-import` the application holds the
imported procedures and sequences; since `authors-as-accounts` every
author is an account. No program outside the browser can act as an
account. The builder makes each attempt a new build and forgets its
failed builds on `orgsyndb-deploy retry`.

## Goals / Non-Goals

**Goals:**

- No two authors take one ID; every new ID records who took it.
- No ID that the collection's history names is issued again.
- A collection without the application (the demo, a registry file)
  keeps working.

**Non-Goals:**

- Refusing an unissued ID when it is pushed: Forgejo's gate, change 4.
  The validator does not check IDs.
- The snapshot's list of issued IDs, which only the gate needs.
- An Emacs command for a new sequence.

## Decisions

### Personal access tokens

A token is `osdb_` and 32 random bytes in URL-safe base64; the
application stores its SHA-256 digest and compares digests. Revoking
deletes the row; deleting an account deletes its tokens. A token
authenticates only the ID path; it never signs anyone in to pages, and
a session never authorizes the ID path, which is exempt from CSRF.

### Issuing under the lock, after adoption

The ID view takes the one lock, reads the highest issued ID of the
kind and records the next, so two requests never get one ID and an
import never adopts one at the same moment. It issues nothing before
the first accepted import, because until then the application does
not know which IDs the collection has. Gaps are never filled: an ID
below the highest may have been deleted.

### Adoption by the first accepted import

The first accepted import, on a demo database the data set's own one,
adopts every ID of its manifest, and the IDs its history names that
its files no longer have (`deleted`), so that a procedure deleted
before the application existed keeps its ID. After that, an import
naming an ID nobody took is refused.

### Reconciling by hand

`manage.py adopt_ids` adopts the IDs an operator names. It is the way
back after restoring a database dump older than the collection: the
next import is refused, naming the IDs issued after the dump; the
operator adopts them and runs `orgsyndb-deploy retry`, whose next
attempt is a new build. The README's restore steps say so.

### Where `new` gets its ID

The collection's own `registry` setting decides, not
`ORGSYNDB_REGISTRY`, which the builder and offline work set to a file:
an address names the application, and `new` asks at its origin (the
application's paths are under `/lab/` at the root); a path means the
collection has no application, and `new` picks the next free ID from
the clone. The token comes from the environment or a file under the
user's configuration directory, never from the collection. Sequences
get IDs the same way, from `md/sequences/` and its history when local.

## Risks / Trade-offs

- [`new` needs the application] → With a registry address, `new`
  fails offline, by design: an ID cannot be taken offline. Emacs's
  `orgsyndb-new-procedure` waits up to the 30-second timeout.
- [A restored dump forgets IDs issued after it] → Until the operator
  adopts them, the application may issue one of them again; the
  validator refuses the duplicate ID when both files meet. The
  restore steps put the reconciliation right after the restore.
- [The demo collection names a file but is imported into the test
  server] → An ID added to it locally is refused there until adopted
  or until `demo_data --replace`, whose manifest names it.
