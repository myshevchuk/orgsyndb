## MODIFIED Requirements

### Requirement: Settings from the environment
The settings SHALL come from these environment variables:

- `ORGSYNDB_SECRET_KEY`: Django's secret key; required unless `ORGSYNDB_DEBUG` is true.
- `ORGSYNDB_DEBUG`: a flag, default false.
- `ORGSYNDB_DATABASE_URL`: `postgres://<user>:<password>@<host>[:<port>]/<name>` for PostgreSQL or `sqlite:///<path>` for SQLite; default `sqlite:///` and the absolute path of `webapp/db.sqlite3`.
- `ORGSYNDB_ALLOWED_HOSTS`: the host names the site is reached by, separated by commas; required unless `ORGSYNDB_DEBUG` is true, when it defaults to `localhost,127.0.0.1`.
- `ORGSYNDB_DEMO`: a flag, default false, that permits writing the demo data (lab-demo "Demo data command").
- `ORGSYNDB_BUILDER_TOKEN`: the token the builder signs its manifests with (collection-import "Manifest"); default empty, which turns the manifest path off.
- `ORGSYNDB_WAKE_URL`: the builder's wake-up address (collection-import "Wake-up after a registry write"); default empty, which sends no wake-up.

A flag takes the words `orgsyndb-deploy` accepts. A missing secret key or host list, a malformed flag or a database URL of another scheme stops the start with a message naming the variable. A request forwarded with `X-Forwarded-Proto: https` counts as secure. The time zone is `Europe/Berlin`. `webapp/db.sqlite3` is ignored by Git.

#### Scenario: Secret key required
- **WHEN** a test loads the settings without `ORGSYNDB_SECRET_KEY` and with `ORGSYNDB_DEBUG` unset
- **THEN** loading fails with a message naming `ORGSYNDB_SECRET_KEY`

#### Scenario: Requests through the proxy
- **WHEN** a test client with CSRF checks enforced posts the sign-in form to host `lab.example.org`, listed in `ORGSYNDB_ALLOWED_HOSTS`, with `X-Forwarded-Proto: https` and the origin `https://lab.example.org`, and once with the host `other.example.org`
- **THEN** the first is treated as secure and accepted, and the second answers 400

#### Scenario: Database URLs
- **WHEN** a test loads the settings with `ORGSYNDB_DATABASE_URL` set to `postgres://lab:secret@db:5432/lab`, to `sqlite:////tmp/x.sqlite3` and to `mysql://db/lab`
- **THEN** the first gives the PostgreSQL engine with name `lab`, user `lab`, password `secret`, host `db` and port `5432`, the second the SQLite engine with name `/tmp/x.sqlite3`, and the third fails naming `ORGSYNDB_DATABASE_URL`

#### Scenario: Demo flag
- **WHEN** a test loads the settings with `ORGSYNDB_DEMO` unset, set to `yes` and set to `maybe`
- **THEN** the first gives the flag false, the second true, and the third fails naming `ORGSYNDB_DEMO`

#### Scenario: Wake-up address
- **WHEN** a test loads the settings with `ORGSYNDB_WAKE_URL` unset and set to `http://builder:8091/wake`
- **THEN** the first gives an empty address and the second that address

#### Scenario: Builder token
- **WHEN** a test loads the settings with `ORGSYNDB_BUILDER_TOKEN` unset and set to `s3cret`
- **THEN** the first gives an empty token and the second `s3cret`
