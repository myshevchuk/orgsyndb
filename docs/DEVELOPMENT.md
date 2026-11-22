# Development notes

Technical notes for people working on the repository. How to run the
suites day to day is in `AGENTS.md` ("Tests") and `README.md`; this
file records why the test setup is the way it is.

## Test suite speed

The repository has two suites: the program's (`python3 -m pytest` at
the root, about 1600 tests) and the lab application's (`uv run pytest`
in `webapp/`, about 2900 tests). Run serially, each took about ten
minutes, and a change used to run both several times.

### Area tests locally, full suites on CI

While working, only the tests of the area a change touches run, and
serially. The full suites run on CI for every pushed branch:

| Workflow | File | Runs | Blocks a merge |
|---|---|---|---|
| `Program` | `program.yml` | root suite, Fedora, latest stable Emacs | yes |
| `Lab application` | `webapp.yml` | lab suite on PostgreSQL | yes |
| `Emacs versions (informational)` | `emacs.yml` | Emacs tests on older stable Emacs | no |

The baseline for a change is the CI result of the commit its branch
grew from (`gh run list --commit <sha>`), not a local full run. A
local full run happens only when CI has no result or failed.

The `Program` job runs as an unprivileged user (`useradd`, then
`su`), because root ignores file permissions and some tests rely on
them. It builds the demo collection first, which fills the ox-hugo and
Pagefind caches the integration tests use.

### Supported Emacs versions

Locally the suite runs on whatever Emacs is installed. CI runs the
whole suite on the latest stable Emacs (Fedora's), and the Emacs tests
alone (`tests/test_elisp.py`, `tests/test_export_integration.py`) on
the older versions still common in distributions: Emacs 29 from
Ubuntu 24.04, Emacs 30 from Debian trixie. Those jobs are
`continue-on-error`: a failure there is fixed in time but blocks
nothing. The oldest supported Emacs is the one in the
`Package-Requires` header of `emacs/orgsyndb.el`; `tools/export.el`
and the tests read it from there.

### Parallel runs

Both suites run under pytest-xdist (`-n auto`) on CI and for any
local full run. pytest-django gives each worker its own test database.

Tests that start local HTTP servers took a free port from the
operating system, and two workers could be handed the same one between
the probe and the bind (`Address already in use`). `free_port()` in
`tests/pipeline_support.py` now gives each worker its own block of
`PORT_BLOCK` (400) ports, starting at `20000 + 400 × worker`, below
the ephemeral range. A worker takes ports from its block in turn and
skips any that fail to bind, so a port is not reused until the block
has gone round.

### The demo data set, written once

Many lab test classes need the demo data set, which `seed(day)` in
`webapp/tests/demo_support.py` writes through the `demo` command. A
write takes seconds, and every such class used to make one.

`seed_once(day)` writes the data set the first time a test process
asks for a day, compares every table before and after, and keeps the
rows of the tables that changed. Later calls for that day delete those
tables' rows and insert the kept ones, then reset the id sequences
with `connection.ops.sequence_reset_sql`. The restore runs inside the class's
`setUpTestData` transaction, so it is rolled back like the write it
replaces. `SeededCase` uses it.

The cache holds only while the database contains nothing but what the
migrations wrote when `seed_once` runs; a class that writes other rows
first must call `seed` instead.

### Results

| Suite | Before | After |
|---|---|---|
| Lab, local full run | 10 min 45 s | 3 min 45 s |
| Program, local full run | about 10 min | 4 min 16 s |
| CI, all jobs of a push | — | about 6.5 min (PostgreSQL is the longest) |
