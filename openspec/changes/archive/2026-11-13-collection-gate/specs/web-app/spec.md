## MODIFIED Requirements

### Requirement: OpenID provider
The application SHALL be an OpenID Connect provider, under `/lab/o/`, for one client, Forgejo, when `ORGSYNDB_OIDC_KEY` holds a PEM-encoded RSA private key in base64; without it every path under `/lab/o/` answers 404. `manage.py forge_client` creates or updates the client from `ORGSYNDB_FORGE_CLIENT_SECRET`, and does nothing without it: client id `forgejo`, confidential, the authorization code flow without PKCE, which Forgejo does not send, ID tokens signed with RS256, the one redirect URI `<ORGSYNDB_URL>/git/user/oauth2/lab/callback`, and no consent page. The issuer is `<ORGSYNDB_URL>/lab/o` in every ID token, whichever host the token was requested through.

`/lab/o/.well-known/openid-configuration` names the issuer `<ORGSYNDB_URL>/lab/o` and the authorization endpoint `<ORGSYNDB_URL>/lab/o/authorize/`, which the person's browser reaches, and the token, user-info and keys endpoints under `ORGSYNDB_APP_INTERNAL_URL`, `http://app:8000` by default, at `/lab/o/token/`, `/lab/o/userinfo/` and `/lab/o/.well-known/jwks.json`, which only Forgejo's server calls; it lists the scopes `openid`, `profile` and `email`.

The authorization endpoint needs a signed-in user, as every page that changes data does (Permissions). For a signed-in account with an email address it sends the person back to the redirect URI with a code at once. For one without, it answers with the page `Kein Zugang zu Forgejo` (`No access to Forgejo`), saying that staff must give the account an email address first, and sends nobody back. The ID token and the user info carry `sub`, the account's primary key as text, `nickname` and `preferred_username`, both the user name, `name`, the display name, and `email`, the email address, and `groups`, the list `["authors"]` for every account, under the scope `profile`, so that Forgejo makes the account a member of the team `authors` at each sign-in (container-deployment "Forgejo"). An inactive account cannot sign in (Accounts and sign-in), so it authorizes nothing; and a code, a refresh token or an access token issued to an account that has since been deactivated is refused, at the token and user-info endpoints alike.

#### Scenario: Discovery
- **WHEN** the provider is on with `ORGSYNDB_URL=http://localhost:8080` and a test client requests `/lab/o/.well-known/openid-configuration`
- **THEN** the issuer is `http://localhost:8080/lab/o`, the authorization endpoint `http://localhost:8080/lab/o/authorize/`, the token endpoint `http://app:8000/lab/o/token/` and the scopes include `openid`, `profile` and `email`

#### Scenario: Signing in to Forgejo
- **WHEN** `klehmann`, with the address `kl@example.org`, is signed in and the client `forgejo` requests the authorization endpoint with the scopes `openid profile email` and its redirect URI and no code challenge, and then posts the code it received to the token endpoint with its secret, with the host `app:8000`
- **THEN** the first answer redirects to the redirect URI with a code and the given state, and the ID token, signed with RS256, has the issuer `http://localhost:8080/lab/o`, the audience `forgejo`, `sub` the account's primary key, `nickname` and `preferred_username` `klehmann`, `name` `Katrin Lehmann` and `email` `kl@example.org`, as has the user info for the access token, and both carry `groups` `["authors"]`

#### Scenario: Not signed in
- **WHEN** a test client that is not signed in requests the authorization endpoint
- **THEN** it redirects to the sign-in page with `next` set to the requested path and query

#### Scenario: An account without an address
- **WHEN** a signed-in account without an email address requests the authorization endpoint for `forgejo`
- **THEN** the answer is the page `Kein Zugang zu Forgejo` and no code was issued

#### Scenario: Provider off
- **WHEN** `ORGSYNDB_OIDC_KEY` is unset and a test client requests `/lab/o/.well-known/openid-configuration` and `/lab/o/authorize/`
- **THEN** both answer 404

#### Scenario: Deactivated after the code
- **WHEN** `klehmann` receives a code, is then deactivated, and the client posts the code to the token endpoint
- **THEN** the answer is an error and carries no token, and the user info for an access token issued before the deactivation is refused too

#### Scenario: A wrong secret
- **WHEN** a client posts a valid code to the token endpoint with another secret
- **THEN** the answer is 401 and carries no token
