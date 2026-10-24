## Why

The demo collection can only be seen by building it locally. A public
copy on GitHub Pages lets anyone try the site without installing
Emacs, Hugo and Pagefind.

## What Changes

- Add `.github/workflows/demo-site.yml`, a GitHub Actions workflow that
  builds `examples/demo` in a Fedora container on every push to `main`,
  pull request and manual dispatch, and deploys the result to GitHub
  Pages from `main` only.
- Add a static test of the workflow file.

The site already works below a path prefix such as `/orgsyndb/`: Hugo
writes relative URLs, and Pagefind derives its bundle path and its
result URLs from the location of its own script.

## Impact

Adds the demo-site capability, `.github/workflows/demo-site.yml` and
`tests/test_demo_site.py`. The repository's GitHub Pages source must
be set to GitHub Actions.
