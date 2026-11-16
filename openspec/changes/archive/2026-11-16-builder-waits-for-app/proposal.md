## Why

`docker compose up -d --build` recreates the builder and the app
together. The builder starts a cycle at once, while the app is still
migrating and has not bound port 8000, so the cycle cannot fetch the
snapshot, builds nothing and waits `ORGSYNDB_INTERVAL` (five minutes
by default) before it tries again. The owner met this on the test
server after the last update.

## What Changes

- `app` gets a health check that passes once the application accepts
  connections on port 8000.
- `builder` starts once `app` is healthy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-deployment`: "Web server and Compose file" adds the app's
  health check and the builder's wait for it.

## Impact

- `deploy/compose.yaml`; the Compose tests in `tests/test_deploy.py`.
- An app that never becomes healthy now keeps the builder from
  starting, and `docker compose up` reports it.
