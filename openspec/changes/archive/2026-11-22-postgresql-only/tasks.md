## 1. Code and tests

- [x] 1.1 Settings accept PostgreSQL only, with the local default;
  `test_config.py` follows
- [x] 1.2 The lock without its SQLite branch; `test_lock.py` loses the
  SQLite test
- [x] 1.3 Tests and docstrings that name SQLite, and the PostgreSQL
  skip in `test_inventory_closing.py`
- [x] 1.4 `webapp.yml` without the SQLite job; `.gitignore`, the
  image's ignore file and `tests/test_webapp_layout.py`

## 2. Documentation

- [x] 2.1 `README.md`, `docs/DEVELOPMENT.md`, `openspec/STATE.md`

## 3. Verification

- [x] 3.1 The lab suite passes locally on PostgreSQL and on CI

## 4. Review and archive

- [x] 4.1 Codex reviewer
- [x] 4.2 Archive and squash-merge into `develop`
