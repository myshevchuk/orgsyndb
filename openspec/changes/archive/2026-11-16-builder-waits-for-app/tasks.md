## 1. Compose

- [x] 1.1 Tests: the app's health check on port 8000 and the builder's
  wait for it, as text and under `docker compose config`
- [x] 1.2 `deploy/compose.yaml`: the health check and the dependency

## 2. Review and archive

- [x] 2.1 Codex reviewer
- [x] 2.2 Archive and squash-merge into `develop`
- [ ] 2.3 The owner runs `docker compose up -d --build` on the test
  server and the builder's first cycle fetches the snapshot
