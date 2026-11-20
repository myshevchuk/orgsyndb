## 1. Tests

- [x] 1.1 Pinned values read from their code: the Pagefind version and
  path from `tools/pipeline.py`, the ox-hugo and tomelr commits from
  `tools/export.el`, the oldest Emacs from `emacs/orgsyndb.el`
- [x] 1.2 The old-Emacs scenario pretends a version below the declared
  oldest one and expects that version in the message
- [x] 1.3 `export.el`'s oldest Emacs is the one `Package-Requires` names
- [x] 1.4 Image, Python and path assertions without versions

## 2. Implementation

- [x] 2.1 `tools/export.el` reads its oldest Emacs from
  `emacs/orgsyndb.el`
- [x] 2.2 Hugo 0.169: `term-keys.html`, `[security]` in
  `site/hugo.toml`, `hugo.Data` in the templates

## 3. Verification

- [x] 3.1 The program's suite passes in full, and CI's runs on the
  branch are green
- [x] 3.2 `tools/orgsyndb -C examples/demo build` prints no Hugo error
  or warning

## 4. Archive

- [x] 4.1 Archive and squash-merge into `develop`
