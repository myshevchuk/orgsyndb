## Why

Forgejo signs in through the lab and links each of its accounts to the
lab account's primary key, the `sub` of the ID token (web-app
"OpenID Connect provider", "Forgejo accounts"). `demo_data --replace`
deletes the demo accounts and creates them again with new keys, so
after every reseed Forgejo meets unknown identities, tries to register
users whose names it already has, and answers sign-in with an error.
The owner hit this on the test server on 2026-11-24.

## What Changes

- The demo data set gives its five accounts fixed primary keys, 1 to 5
  in the order of the "Demo accounts" table, on every write, and moves
  the key sequence past them, so accounts created afterwards take
  higher keys.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-demo`: the demo accounts keep their primary keys across writes.

## Impact

- `webapp/demo/seed.py`, a demo command test. PostgreSQL only, as the
  application is.
