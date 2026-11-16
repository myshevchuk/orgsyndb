## Context

The builder's `run` starts its first cycle as soon as the container
starts. The app container runs `migrate`, `demo_data --if-empty` and
`forge_client` before gunicorn binds port 8000. `db` already has a
health check by `pg_isready`, and `app`, `backup`, `restore` and
`forge-db` wait for it with `condition: service_healthy`.

## Goals / Non-Goals

**Goals:** after `docker compose up`, the builder's first cycle finds
the app answering.

**Non-Goals:** cycles while the app restarts later, which build nothing
and try again after the interval, as "Update cycle" states.

## Decisions

**A connection to port 8000, not a request.** The check runs every few
seconds for the life of the container; opening a TCP connection with
the image's Python tells that gunicorn listens, which is what the
builder lacked, without a database query or a `Host` the settings must
allow. A start period covers a first start whose migrations and demo
data take longer than the retries.

**Compose orders the start; the updater stays as it is.** Rejected:
retrying a failed snapshot fetch sooner in `orgsyndb-deploy run`. It
would also cover later restarts, but it changes the cycle's timing for
every failure and needs a back-off, for a race that only start-up
causes.
