## Why

The lab runs on PostgreSQL in every deployment, and SQLite will never
be used in production. Keeping both costs a second CI job, a
backend-specific branch in the lock, tests that hold only on one
database, and specs that state guarantees twice. The owner decided on
2026-11-22 to drop SQLite.

## What Changes

- **BREAKING** `ORGSYNDB_DATABASE_URL` accepts PostgreSQL only. Its
  default becomes `postgres://lab:lab@localhost:5432/lab`, the local
  development database, in place of `webapp/db.sqlite3`. A
  `sqlite:///` URL stops the start like any other scheme.
- `orgsyndb_web.lock.hold()` always takes the advisory lock.
- The lab suite runs on PostgreSQL alone, locally and on CI. The
  SQLite job leaves `webapp.yml`, and so do tests that exist only for
  SQLite or skip without PostgreSQL.
- `webapp/db.sqlite3` leaves `.gitignore` and the image's ignore
  file. The README and `docs/DEVELOPMENT.md` describe a local
  PostgreSQL container for the tests, the server and the demo.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: "Settings from the environment".
- `collection-import`: "One lock".
- `end-product-inventory`: "Item movements".
- `task-tracker`: "Task numbers".
- `database-diagram`: "Diagram command".

## Impact

- `webapp/orgsyndb_web/config.py`, `lock.py`; `webapp/tests/settings.py`;
  `webapp/inventory/bookings.py` and `webapp/tests/test_inventory_closing.py`
  docstrings.
- Tests: `test_config.py`, `test_lock.py`, `test_inventory_closing.py`,
  `test_inventory_batches.py`; root `tests/test_webapp_layout.py`.
- `.github/workflows/webapp.yml`, `.gitignore`,
  `deploy/webapp/Dockerfile.dockerignore`.
- `README.md`, `docs/DEVELOPMENT.md`, `openspec/STATE.md`.
- Running the lab suite locally needs a PostgreSQL server, such as a
  `postgres:18` container.
