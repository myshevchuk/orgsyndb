## Why

A compound has two pages: the site's `/compounds/<key>/`, built from
the collection, and the lab's `/lab/registry/substances/<key>/`. The
lab's page now shows everything the site's does — the record, the
procedures that make and use the substance, its sequences, its route
tree and its structure image — and the site no longer needs to work
without the lab. The owner sees the site's compound pages, their
catalogue and its tabs as legacy and wants one page per substance, the
lab's.

## What Changes

- **BREAKING**: the site no longer builds `/compounds/`, the compound
  catalogue with its text search, its group tabs
  `/compounds/group/<group>/`, or a page per compound. The menu loses
  `Verbindungen` (`Compounds`); the home page's count of compounds
  links the lab's substance list.
- Every compound link on the site — the metadata panel, scope tables,
  sequence schemes and the sequence directory — leads to the
  substance's lab page, `/lab/registry/substances/<key>/`, with the
  values beside it as before.
- **BREAKING**: the build no longer derives route trees
  (`pipeline.routes_data`, `build/data/routes.json`); the lab draws them,
  and "Routes in the lab" states the rules it follows.
- The catalogue script loses the compound catalogue's text search
  (`match`) and every catalogue searches with Pagefind.
- **BREAKING**: registry fields keep one presentation, `beside`; the
  options `column`, `search`, `facet` and `tabs`, which only the
  compound directory and catalogue read, end.
- The substance key `group`, which the compound tabs reserved, is
  allowed again in the validator and the lab's forms.
- The lab's substance page loses the link `In der Sammlung` (`In the
  collection`), whose target retires.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-catalogue`: "Compound catalogue", "Compound text search" and
  "Compound tabs" go; the procedure catalogue's requirements lose the
  compound catalogue's variants and keep the declared facets' value
  rules.
- `site-theme`: "Compound pages" and "Compound directory" go; the page
  shell, metadata panel, home page, section tabs and navigation follow.
- `synthesis-routes`: "Derived routes" and "Routes on compound pages"
  go; "Routes in the lab" states the rules.
- `compound-fields`: "Registry fields", "Field data for the site",
  "Field display" and "Values beside compound links" follow.
- `compound-registry`: "Registry checks" no longer reserves `group`.
- `lab-registry`: "Registry pages" loses `In der Sammlung`; "Registry
  forms" no longer reserves `group`.
- `collection-index`: "Index data" lists the registry fields' remaining
  options.
- `site-build`: "Deployment under a path prefix" names the links into
  the lab that every build writes.
- `site-build`, `build-script`, `general-procedures`,
  `synthesis-sequences`, `localization`: the passages that name
  compound pages or the route data.

## Impact

- `site/` (layouts, content, `hugo.toml`, i18n, catalogue scripts and
  styles), `tools/pipeline.py`, `tools/validate.py`, `tools/orgsyndb`.
- `webapp/registry/` (the link and its query, the reserved key).
- Tests of the site, the catalogue, the routes, the validator and the
  lab; README and the `docs/` guides, through the doc writer.
- Collections that declare nothing are unaffected; a collection's
  settings name no registry-field option.
