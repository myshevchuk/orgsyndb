## 1. Tests

- [x] 1.1 Updater against throwaway repositories with a fake
  `tools/orgsyndb`: first publish, no rebuild without change, new
  collection commit, pruning, failed collection, application update,
  broken application with fallback, application needing a new image,
  updates off, application ref, collection ref and path, missing
  settings file, PDFs, unreachable collection, settings errors,
  `status`, `retry`, usage error
- [x] 1.2 Files: stdlib-only updater, contents of `deploy/docker/`,
  Dockerfile, Caddyfile, `docker compose config`

## 2. Implementation

- [x] 2.1 `deploy/docker/orgsyndb-deploy`
- [x] 2.2 `deploy/docker/Dockerfile` and `deploy/docker/Caddyfile`
- [x] 2.3 `deploy/compose.yaml` and `deploy/orgsyndb.env.example`

## 3. Docs and archive

- [x] 3.1 `README.md`
- [x] 3.2 Archive
