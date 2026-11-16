## MODIFIED Requirements

### Requirement: Web server and Compose file
`deploy/docker/Caddyfile` SHALL serve `/var/lib/orgsyndb/current/public` with `file_server` at the site address `ORGSYNDB_ADDRESS`, `:8080` by default, `/pdf/` from `current/pdf` with a directory listing, answer `404` for every path beginning with `/lab/collection/manifest` or `/lab/collection/check`, forward `/lab/` and every other path below it, unchanged, to the application at `ORGSYNDB_APP_UPSTREAM`, `app:8000` by default, and forward every path below `/git/`, with `/git` taken off, to Forgejo at `ORGSYNDB_FORGE_UPSTREAM`, `forge:3000` by default, redirecting `/git` to `/git/`. It sets the header `Cache-Control: no-cache` on every response but Forgejo's, which sets its own, and turns Caddy's admin endpoint off.

`deploy/compose.yaml` SHALL define these services, each reading `orgsyndb.env`:

- `builder`, running `orgsyndb-deploy run` with an init process and `ORGSYNDB_LAB=true` in its environment, so that the site it builds links the lab application's views, starting once `app` is healthy, and `web`, running Caddy with port 8080 published, both from one image built from `deploy/docker` with the build arguments `APP_REPO` and `APP_REF`, both mounting the volume `data` at `/var/lib/orgsyndb`, read-only for `web`, and `builder` mounting the volume `pushes` read-only at `/var/lib/orgsyndb-pushes` (Push log);
- `db`, from `postgres:18`, keeping its data in the volume `db`, with a health check by `pg_isready`;
- `app`, from the image built from the repository root with `deploy/webapp/Dockerfile`, mounting `data` read-only at `/var/lib/orgsyndb`, starting once `db` is healthy, with a health check that passes once a TCP connection to its port 8000 opens;
- `backup`, from `postgres:18`, running `deploy/backup/orgsyndb-backup`, mounted read-only, with `deploy/backups/` mounted at `/backups`, `orgsyndb.env` read-only at `/opt/orgsyndb/orgsyndb.env`, the volumes `forge` and `pushes` read-only at `/var/lib/gitea` and `/var/lib/orgsyndb-pushes`, and `forge-control` read-write at `/var/lib/orgsyndb-forge-control` (Backups);
- `restore`, from `postgres:18` with the same script, only in the profile `restore`, running `orgsyndb-backup restore`, with `deploy/backups/` read-only and the volumes `forge`, `pushes` and `data` read-write at `/var/lib/gitea`, `/var/lib/orgsyndb-pushes` and `/var/lib/orgsyndb`, starting once `db` is healthy and `forge-db` has completed, since the restore creates `forge` owned by the role `forge`;
- `forge-db` and `forge` (Forgejo), both mounting the volume `pushes` read-write at `/var/lib/orgsyndb-pushes`.

`deploy/orgsyndb.env.example` lists the settings, among them `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, the matching `ORGSYNDB_DATABASE_URL`, `ORGSYNDB_SECRET_KEY`, with how to generate a key, `ORGSYNDB_ALLOWED_HOSTS`, with `app` among the hosts, `ORGSYNDB_BUILDER_TOKEN`, with how to generate a token, and the settings of Forgejo with how to generate each secret. Git ignores `deploy/orgsyndb.env` and `deploy/backups/`.

#### Scenario: Caddyfile
- **WHEN** a test reads the Caddyfile, and runs `caddy adapt` on it when Caddy is installed
- **THEN** it names `/var/lib/orgsyndb/current/public`, the `Cache-Control` header, `/lab/*`, `reverse_proxy`, `/lab/collection/manifest*` and `/lab/collection/check*`, each answered with `404` ahead of the `/lab/*` route, and `/git/*` with `handle_path`, and adapts without error

#### Scenario: Compose file
- **WHEN** a test copies `deploy/` with `orgsyndb.env.example` as `orgsyndb.env` and runs `docker compose config`, skipping without Docker
- **THEN** it succeeds, the services are `builder`, `web`, `db`, `app`, `backup`, `forge-db` and `forge`, with `restore` only under the profile `restore`, `backup` mounts `forge` and `pushes` read-only and `forge-control` read-write, `restore` mounts `forge`, `pushes` and `data` read-write and depends on `forge-db` completing, `builder` runs `orgsyndb-deploy run`, reads the settings and has `ORGSYNDB_LAB` set to `true`, `web` and `app` mount the data volume read-only, `db`'s health check runs `pg_isready`, `app` depends on `db` being healthy, `app`'s health check connects to port 8000, `builder` depends on `app` being healthy, `app` receives the example's `ORGSYNDB_DATABASE_URL`, `builder` mounts `pushes` read-only and `forge` and `forge-db` mount it read-write
