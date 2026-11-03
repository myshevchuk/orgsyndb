## 1. Tests, red first

- [x] 1.1 `tests/test_demo_site.py` and `tests/test_emacs_29_workflow.py`:
  the push trigger names `main` and `develop`

## 2. Implementation

- [x] 2.1 Both workflows: push branches `[main, develop]`

## 3. Documents

- [x] 3.1 README: the two workflow paragraphs, the branches in
  Development, and `:branch` for installing from Git (doc writer)

## 4. Verification

- [ ] 4.1 After the merge: both workflows run on the push to `develop`,
  and the demo site's deploy job is skipped there
- [x] 4.2 `openspec validate ci-develop --strict`
