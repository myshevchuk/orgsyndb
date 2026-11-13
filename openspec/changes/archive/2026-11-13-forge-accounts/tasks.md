## 1. Tests

- [x] 1.1 Accounts: reserved user names, unique email addresses
- [x] 1.2 The OpenID provider: discovery, authorization, token, user info, an account without an address, provider off, `forge_client`
- [x] 1.3 Forgejo accounts: blocking on deactivation, the warning, `forge_accounts`
- [x] 1.4 Deployment: Caddyfile, Compose services, the image's command, `forge-db`'s script, `forge-setup`, the example settings
- [x] 1.5 Demo accounts' email addresses

## 2. Implementation

- [x] 2.1 Accounts and the provider (django-oauth-toolkit, claims, discovery view, `forge_client`)
- [x] 2.2 The Forgejo client, the admin warning and `forge_accounts`
- [x] 2.3 Deployment files and `deploy/forge/`
- [x] 2.4 Demo; schema diagram regenerated

## 3. Docs and archive

- [x] 3.1 README: container deployment, Forgejo set-up, accounts
- [ ] 3.2 Test server, by the owner: a browser sign-in at `/git/` through the lab app (a new Forgejo account named after the lab user), a second sign-in to the same account, `forge-setup` run twice, an account without an address refused, and a push with an access token and with an SSH key before deactivation, refused during it and accepted after reactivation
- [x] 3.3 Review, then archive
