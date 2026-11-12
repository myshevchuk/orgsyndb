## 1. Tests

- [x] 1.1 Access tokens: the page, shown once, digest only, revoke,
  inactive accounts, last use
- [x] 1.2 The ID endpoint: procedure and sequence IDs in turn, the
  account, 401 (a session alone too), 400, 409 before an import, the
  lock
- [x] 1.3 Adoption by the first accepted import with `deleted`; an
  unissued ID refused later; `adopt_ids`; the demo's import adopts
  its IDs; `--replace` deletes issued IDs
- [x] 1.4 `orgsyndb new` with an address and a token, without a token,
  refused, with a registry file; `next_id` with a prefix;
  `new --sequence`; `deleted` in the manifest

## 2. Implementation

- [x] 2.1 `accounts.AccessToken`, its page, admin and the bearer check
- [x] 2.2 `collection.IssuedId`, the endpoint, adoption, `adopt_ids`
  and the import check; procedure and sequence keys
- [x] 2.3 `pipeline` and `tools/orgsyndb`: `take_id`, the token,
  `next_id` with a prefix, `new --sequence`, `deleted`; the Emacs
  docstring
- [x] 2.4 Demo (`manifest.json`, replace); schema diagram regenerated

## 3. Docs and archive

- [x] 3.1 `README.md`, the authoring guides in both languages
- [x] 3.2 Review, then archive
