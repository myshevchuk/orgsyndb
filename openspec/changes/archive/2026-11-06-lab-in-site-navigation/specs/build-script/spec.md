## MODIFIED Requirements

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`, write the field data `build/data/fields.json`, the JSON form of `pipeline.fields_data(<collection>/orgsyndb.toml, <language>)` for the site's language (compound-fields "Field data for the site"), write the reaction-type data `build/data/reaction_types.json`, the JSON form of `pipeline.reaction_types_data(<collection>/orgsyndb.toml, <language>)` (reaction-types "Reaction-type data for the site"), write the route data `build/data/routes.json`, the JSON form of `pipeline.routes_data(<published procedures>)`, the published procedures being the `(path, front matter)` pairs of the variants the build staged (synthesis-routes "Derived routes"), and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration"), with the lab application's views when the environment variable `ORGSYNDB_LAB` is `true`, `1`, `yes` or `on`, in any case, and without them when it is unset, empty, `false`, `0`, `no` or `off`.
4. Run `hugo --source <app>/site --configDir <collection>/build/hugo-config --minify --quiet --noBuildLock`.
5. Obtain the Pagefind binary, and run it with `--site <collection>/public --quiet`.

A failing step stops the command with exit 1. Any other value of `ORGSYNDB_LAB` stops it with exit 1 before its first step, with a message naming the variable and the value.

#### Scenario: Validation error stops the build before Hugo
- **WHEN** an integration test builds once, adds an invalid Markdown procedure to `md/procedures/`, and builds again
- **THEN** the second build exits 1, and `public/` still holds the first build's output

#### Scenario: Second build without changes
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` twice on a copy of the demo collection without changing any source
- **THEN** both runs exit 0, and `build/export/` is not empty and holds identical bytes after each

#### Scenario: Field data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/fields.json` parses as JSON to `pipeline.fields_data` of the copy's `orgsyndb.toml` for the language `pipeline.site_language` reports

#### Scenario: Reaction-type data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/reaction_types.json` parses as JSON to `pipeline.reaction_types_data` of the copy's `orgsyndb.toml` for the language `pipeline.site_language` reports

#### Scenario: Route data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/routes.json` parses as JSON to `pipeline.routes_data` of the procedures the build staged

#### Scenario: Lab views on request
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection with `ORGSYNDB_LAB=true`, and once with `ORGSYNDB_LAB=maybe`
- **THEN** the first exits 0, its overlay sets `params.lab = true` and its home page's header links `/lab/tasks/`; the second exits 1 with a message naming `ORGSYNDB_LAB` and `maybe`, and runs no export
