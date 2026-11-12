## Context

`authors` is a list of non-empty strings, a Hugo taxonomy whose term
keys are the names lowercased (`a. example`, URL `/authors/a.-example/`).
The site writes the name as written. Accounts live only in the lab
application; the snapshot carries substances and vocabularies.

## Goals / Non-Goals

**Goals:**

- One identity per author across the files, the site and the
  application, as draft 07 settled.
- The site keeps showing people's names, not user names.

**Non-Goals:**

- `checked_by`, which stays a list of names: draft 07 settles authors
  only.
- Issued IDs, Forgejo sign-in: later changes.

## Decisions

### User names as Forgejo takes them

At most 40 characters: letters and digits, with single `.`, `-` or `_`
between them, ASCII only. A user name is read-only once the account
exists, in the admin and every form, since files name it.

### Names travel in the snapshot

`accounts` lists every account, active or not, by user name with its
display name; a deactivated author still has a name. It is inside the
digest, so a renamed person reaches the site with the next build.
`registry_load` neither reads nor creates accounts: accounts are made
in the application.

### Names on the site come from staged data

As reaction-type labels do, author names come from
`build/data/authors.json`; the taxonomy's terms are the user names, so
an author's page is `/authors/<user name>/` and its key is the user
name. The layouts that write an author call one partial.

### The import keeps authors as rows

The manifest gives each procedure's user names in file order; the
import resolves them to accounts and refuses one it lacks.

### Fixtures and the demo

The test collections name fictitious accounts `<initial>.example`
named `<Initial>. Example`, so most expectations about shown names
hold. The demo credits its five accounts: `A.`→`klehmann`,
`B.`→`tbauer`, `C.`→`aschmidt`, `D.`→`jkoch`, `E.`→`mwolf`,
`F.`→`jkoch`, `G.`→`aschmidt`, a mapping under which no procedure
names one account twice.

## Risks / Trade-offs

- [Author URLs change] → `/authors/a.-example/` becomes
  `/authors/a.example/`; the product has no published links to keep.
