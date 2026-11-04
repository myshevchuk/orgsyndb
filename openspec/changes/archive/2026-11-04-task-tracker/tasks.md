## 1. Tests

- [x] 1.1 Root suite: `pytest.ini` keeps collection to `tests/`
- [x] 1.2 Settings: secret key, flags, database URLs
- [x] 1.3 Index reader: demo lookups by key and unique field, names by
  language, `mw`, sequences and their steps, missing and malformed
  file, reread on change
- [x] 1.4 Compound links and the compound `datalist`
- [x] 1.5 Accounts: initials, unusable password, sign-in, sign-out,
  password change; permissions on every form and action path
- [x] 1.6 Page shell and language: stylesheets, navigation,
  `aria-current`, sign-in state, no `script`, German and English dates
- [x] 1.7 Tasks: numbers and the counter, state, follow-up, progress,
  steps from a sequence, history
- [x] 1.8 Task list: columns, order, counts, filters including the
  compound name, unknown filter values
- [x] 1.9 Task page, actions in and out of state, forms and their
  validation, admin
- [x] 1.10 Deployment (`tests/test_deploy.py`): index in the release,
  failing and timed-out index, fallback when a new application's index
  fails; Caddyfile; Compose services, health check and settings;
  application Dockerfile; backup script with a fake `pg_dump`

## 2. Application

- [x] 2.1 `webapp/pyproject.toml`, `uv.lock`, `manage.py`,
  `orgsyndb_web` settings and URLs
- [x] 2.2 `accounts`: user model, sign-in views and templates
- [x] 2.3 Index reader and compound links
- [x] 2.4 Page shell, `lab.css`, the site's stylesheets as static
  files, translations
- [x] 2.5 `tasks`: model, counter, history, list, page, actions,
  forms, admin

## 3. Deployment

- [x] 3.1 `orgsyndb-deploy`: write `index.json` into each release
- [x] 3.2 Caddyfile: forward `/lab/`
- [x] 3.3 `deploy/webapp/Dockerfile`
- [x] 3.4 `deploy/backup/orgsyndb-backup`
- [x] 3.5 `deploy/compose.yaml`, `deploy/orgsyndb.env.example`,
  `.gitignore`
- [ ] 3.6 Build the images and run the stack once on a machine with
  Docker: sign in, create a task, take and restore a dump

## 4. CI

- [x] 4.1 `.github/workflows/webapp.yml`: the application's suite on
  SQLite and on a PostgreSQL 18 service, on the same triggers as the
  other workflows

## 5. Docs and archive

- [x] 5.1 `README.md`: the application, first account, updates with a
  backup first, restoring a dump
- [x] 5.2 Review, then archive
