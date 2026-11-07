## MODIFIED Requirements

### Requirement: Application image
`deploy/webapp/Dockerfile` SHALL build an image from `fedora:44` that installs Python 3 and uv, copies `webapp/` and `site/assets/css/` from the build context, the repository root, installs the locked dependencies without the development ones, and collects the static files. It runs as the user `orgsyndb` with UID 1000 and exposes port 8000. Its command applies pending migrations, then runs `manage.py demo_data --if-empty`, which seeds an empty database when `ORGSYNDB_DEMO` is true and otherwise changes nothing (lab-demo "Demo data command"), and then serves `orgsyndb_web.wsgi` with gunicorn on `0.0.0.0:8000`. `ORGSYNDB_INDEX` defaults to `/var/lib/orgsyndb/current/index.json`. `deploy/orgsyndb.env.example` names `ORGSYNDB_DEMO`, commented out, with a comment saying that it fills an empty database with invented records whose accounts share a password shown on the sign-in page, and is for test deployments only.

#### Scenario: Image inputs
- **WHEN** a test reads `deploy/webapp/Dockerfile`
- **THEN** it names `fedora:44`, `uv sync --frozen --no-dev`, `collectstatic`, `migrate`, `demo_data --if-empty` and `gunicorn`, in the command in the order `migrate`, `demo_data`, `gunicorn`, and `USER orgsyndb`

#### Scenario: Demo flag in the example settings
- **WHEN** a test reads `deploy/orgsyndb.env.example`
- **THEN** it holds the line `#ORGSYNDB_DEMO=false`
