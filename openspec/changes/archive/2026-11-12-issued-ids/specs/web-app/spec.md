## ADDED Requirements

### Requirement: Access tokens
A signed-in user SHALL manage their own access tokens at `/lab/accounts/tokens/`, headed `Zugangsschlüssel` (`Access tokens`): a table of their tokens with the columns `Name`, `Angelegt` (`Created`) and `Zuletzt benutzt` (`Last used`) and, beside each, a button `Widerrufen` (`Revoke`) that deletes it; and a form with a `Name` of at most 100 characters that creates a token and shows it once, with the note `Kopieren Sie den Schlüssel jetzt; er wird nicht wieder angezeigt.` (`Copy the token now; it is not shown again.`). A token is `osdb_` followed by 43 URL-safe characters from a secure random source; the application keeps only its SHA-256 digest, its account, its name, when it was created and when it was last used. A request carrying `Authorization: Bearer <token>` is made by the token's account when the digest matches a token of an active account, and the request records the time as its last use; an unknown token, one of an inactive account or a revoked one is refused with 401. Staff see and delete tokens in the admin. The page needs a signed-in user, as every page that changes data does (Permissions).

#### Scenario: A token shown once
- **WHEN** user `klehmann` posts the name `Laptop` to `/lab/accounts/tokens/`
- **THEN** the answer shows a token beginning `osdb_`, the table lists `Laptop`, a second request of the page shows no token, and no stored value equals the token

#### Scenario: A revoked token
- **WHEN** user `klehmann` revokes the token `Laptop` and a client then requests the issuing of an ID with it
- **THEN** the request is refused with 401

#### Scenario: An inactive account
- **WHEN** an account holding a token is deactivated and a client requests the issuing of an ID with that token
- **THEN** the request is refused with 401

## MODIFIED Requirements

### Requirement: Permissions
Pages that show data SHALL need no sign-in. Every page and action that changes data needs a signed-in user: a request without one, GET or POST, redirects to the sign-in page with `next` set to the requested path and changes nothing. The exceptions are the manifest path, which the builder signs with a service token (collection-import "Manifest"), and the ID path, which needs an account's access token, a signed-in session not being enough (collection-import "Issued IDs"); neither redirects. The admin needs staff status. The views offer no deletion, except that a user revokes their own access tokens (Access tokens); staff delete in the admin.

#### Scenario: Form without sign-in
- **WHEN** a test client that is not signed in requests and posts `/lab/tasks/new/`
- **THEN** both redirect to `/lab/accounts/login/?next=/lab/tasks/new/` and no task exists
