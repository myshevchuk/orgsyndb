## 1. Staging

- [x] 1.1 Tests: `help_slug`, `help_page` (titles, front matter, link
  rewriting in Markdown and Org, links inside code left alone, errors)
  and `stage_help` (target emptied, names, slug clash, unknown
  language, missing `docs/`); red first
- [x] 1.2 `tools/pipeline.py`: `help_slug`, `help_page`, `stage_help`;
  `hugo_overlay` gains the help mount; `tools/orgsyndb`: `run_build`
  stages the help pages

## 2. Site

- [x] 2.1 Tests: overlay mounts, `markup.highlight.noClasses`, the
  navigation (English and German), current-section marks, the help
  index and help pages of a theme build, German titles; the sandbox
  copies `docs/`; red first
- [x] 2.2 `site/hugo.toml`, `site/content/help/_index.md`,
  `site/layouts/help/section.html` and `page.html`, the site header,
  both i18n files, `pre` styles

## 3. Docs and verification

- [x] 3.1 Doc writer: update the README's "Use the site"
- [x] 3.2 Full suite green, with and without Emacs
- [x] 3.3 Build the demo; check `/help/`, an Org guide and the glossary
  in headless Firefox screenshots, and that the cross-document links
  with a fragment match heading ids
