## Why

A group runs the site on an in-house server. Today it builds the site
by hand and copies `public/` to a web server, and updates the
application by hand. The server should instead keep the site built from
the collection's Git repository, wherever that repository lives, and
follow the application's repository by itself, without ever replacing a
working site with a failed build.

## What Changes

- `deploy/docker/Dockerfile` builds a Fedora 44 image with the build
  tools, Caddy, and a clone of the application whose ox-hugo, tomelr
  and Pagefind caches are filled, so that a build in the container
  needs no internet access.
- `deploy/docker/orgsyndb-deploy`, a standard-library Python program in
  the image, fetches the application and the collection, builds the
  site when either moved, and publishes a successful build by switching
  a symlink to a new release. A failing application commit falls back
  to the previous one; a failed combination is not rebuilt.
- An application commit that changes `deploy/docker/` is not used,
  since it needs a new image.
- `deploy/docker/Caddyfile` serves the published release, and its PDFs
  under `/pdf/`.
- `deploy/compose.yaml` runs a `builder` and a `web` service from the
  image on one data volume; `deploy/orgsyndb.env.example` lists the
  settings.

## Capabilities

### New Capabilities

- `container-deployment`: the image, the updater, the Caddyfile and the
  Compose file.

## Impact

- New files under `deploy/`; `tests/test_deploy.py`.
- Docs: `README.md` gains "Container deployment"; the Caddy example
  moves under "Serve a copy with Caddy".
