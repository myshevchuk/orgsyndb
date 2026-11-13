## 1. Tests

- [x] 1.1 The app's check path: clean, unissued ID, before the first import, token answers, nothing recorded
- [x] 1.2 The `groups` claim in the ID token and the user info
- [x] 1.3 The builder's check server: valid, `export-ignore`, failing validation, refused by the app, token, size, busy, too slow, the cycle meanwhile, shutdown
- [x] 1.4 The hook `deploy/forge/gate`: main checked, other refs pass, refusal lines, no answer, no token
- [x] 1.5 Deployment: Caddyfile hides the check path, Forgejo's `USER_DISABLED_FEATURES`, `forge-setup` read checks, the example settings

## 2. Implementation

- [x] 2.1 The check path in `webapp/collection/`
- [x] 2.2 The `groups` claim
- [x] 2.3 The check server in `orgsyndb-deploy`, and `deploy/forge/gate`
- [x] 2.4 `forge-setup`, compose, Caddyfile, example settings

## 3. Docs and archive

- [x] 3.1 README: Forgejo set-up, moving the collection in, a refused push
- [x] 3.2 Review, then archive
- [ ] 3.3 Test server, by the owner: `forge-setup` again, push the collection to `lab/collection`, a push that fails validation refused with its errors, a good push built and published, a force push to `main` refused
