## 1. Templates and tests

- [x] 1.1 Remove `data-catalogue-search` from `site/layouts/_partials/site-header.html`
- [x] 1.2 Remove `data-fixed` from `details.facet` in `site/layouts/_partials/catalogue.html`
- [x] 1.3 Update `tests/catalogue_support.py`, `tests/test_catalogue_integration.py`, and `tests/test_theme_integration.py`

## 2. Check

- [x] 2.1 Validate OpenSpec change strictly (`openspec validate drop-unused-catalogue-hooks --strict`)
- [x] 2.2 Run catalogue, theme, general-procedures, and localization integration tests
