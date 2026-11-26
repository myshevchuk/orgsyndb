## 1. Custom QuerySet helpers

- [x] 1.1 Add `ItemQuerySet`, `VesselQuerySet`, and `MovementQuerySet` in `webapp/inventory/models.py` (preserving `Article`'s `LockedQuerySet`) and verify zero pending migrations
- [x] 1.2 Adopt QuerySet helpers in `webapp/inventory/figures.py`

## 2. Split inventory.views into package

- [x] 2.1 Create `webapp/inventory/views/common.py` with unified `oldest_vessel_order()`, `pick_selected()`, `htmx_detail_or_redirect()`, and shared navigation/form/URL helpers
- [x] 2.2 Create `items.py`, `categories.py` (with per-category config/predicate helpers), `bulk.py`, `notes.py`, `batches.py`, `vessels.py`, and `__init__.py`, and remove `webapp/inventory/views.py`

## 3. Verification

- [x] 3.1 Run `makemigrations --check --dry-run` and the full inventory, query-count, widget, and shell test suites locally
- [x] 3.2 Verify green CI (`Program` and `Lab application`) on the pushed branch
