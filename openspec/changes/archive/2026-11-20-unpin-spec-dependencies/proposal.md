## Why

Seventeen requirements name versions of the software the application
depends on: Hugo, Pagefind with its download address and hashes, the
commits ox-hugo and tomelr are fetched at, the oldest Emacs, Python,
WeasyPrint, Forgejo, and the container images' tags. The owner decided
on 2026-11-21 that specs give general direction and fix no such
detail, as they already fix no layout and no test tooling: versions
belong to the files that pin them, which a dependency update changes
without a proposal.

The pin of Hugo 0.162.1 also no longer matches the machines the
application is built on: Fedora now ships Hugo 0.169.0, which rejects
a `return` that is not the last command of a pipeline, refuses Org
content unless the security policy allows it, and warns about
`site.Data`, so every build stops before it publishes a page.

## What Changes

- The requirements keep what they fix and drop the versions:
  - build-script: the entry point and the helper module are Python
    programs; `check-deps` reports Pagefind; the ignore-rules scenario
    names a path under `.tools/` without a version;
  - site-build: Hugo without a version; the Pagefind binary is the
    pinned version, accepted by the hashes `tools/pipeline.py` pins,
    fetched from Pagefind's GitHub releases; the search index carries
    the pinned version; the data entries are named `hugo.Data.…`;
  - org-export: the export works with the oldest Emacs the package
    `orgsyndb` declares and refuses an older one; ox-hugo and tomelr
    are fetched at the commits `tools/export.el` pins;
  - emacs-mode: the package declares its oldest Emacs in
    `Package-Requires`;
  - print-layout: WeasyPrint without a version;
  - web-app: `pyproject.toml` declares the Python it requires;
    Forgejo's reserved names without a version;
  - container-deployment: a `fedora` base image, a `postgres` image
    and a rootless Forgejo image, without tags;
  - reaction-types: the data entry is named `hugo.Data.…`.
- The tests read pinned values from the code that pins them instead of
  repeating them.
- `tools/export.el` reads its oldest Emacs from `emacs/orgsyndb.el`'s
  `Package-Requires` instead of repeating it.
- The site builds with Hugo 0.169: `term-keys.html` returns a
  parenthesized pipeline, `site/hugo.toml` allows Org content and keeps
  raw HTML content refused, and the templates read `hugo.Data`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-script`, `site-build`, `org-export`, `emacs-mode`,
  `print-layout`, `web-app`, `container-deployment`, `reaction-types`:
  requirements that named versions or `site.Data` restated without
  them.

## Impact

- `site/hugo.toml`, `site/layouts/` (every template reading data),
  `tools/export.el`.
- Tests: `tests/pipeline_support.py`, `test_export_integration.py`,
  `test_build_integration.py`, `test_site_config.py`,
  `test_build_script.py`, `test_webapp_layout.py`, `test_deploy.py`,
  `test_backup_compose.py`, `test_forge_deploy.py`.
- No document states a pinned version the change removes.
