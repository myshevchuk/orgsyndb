# OrgSynDB

OrgSynDB is a local, in-house website for curated synthetic procedures,
modelled on *Organic Syntheses*. Each procedure lives in one source file:
the owner writes Org files in `org/procedures/`, and co-workers can write
Markdown files in `md/procedures/`. The build treats both formats alike.

The finished site is static. Viewing it loads no fonts, analytics, or other
resources from the internet. It has a responsive light and dark theme,
full-text search, browse pages, and an A4 print layout.

## Install the dependencies

OrgSynDB is designed for Fedora and uses fish for its build command. Install
the required system packages with:

```fish
sudo dnf install emacs git python3 hugo weasyprint
```

You do not need Node. Caddy is optional and is used only by the deployment
example.

On the first export or build, OrgSynDB fetches pinned copies of ox-hugo and
tomelr into `.emacs-batch/`. On the first build, it also fetches Pagefind
1.5.2 into `.tools/` and verifies its SHA-256 checksum. The first run
therefore needs network access and Git. These tools do not write to your
Emacs configuration.

Check the current machine before building:

```fish
tools/build.fish check-deps
```

The command reports each installed or missing tool. If packages are missing,
its final line is the `sudo dnf install ...` command for only those packages.
It reports Caddy separately as optional and never runs `sudo` itself.

A machine with all required tools and both downloaded caches reports:

```text
ok      emacs
ok      git
ok      python3
ok      hugo
ok      weasyprint
optional caddy (not installed; only for deploy/Caddyfile.example)
auto    pagefind 1.5.2 (cached in .tools/)
auto    ox-hugo/tomelr (cached in .emacs-batch/)
```

## Quick start

Run these commands from the repository root:

```fish
# Check required and optional tools.
tools/build.fish check-deps

# Export Org, validate every procedure, and build public/.
tools/build.fish build

# Build and preview at http://127.0.0.1:8000/.
tools/build.fish serve

# Build and create one A4 PDF per procedure in pdf/.
tools/build.fish pdf

# Choose one source format. Create the next Org procedure:
tools/build.fish new "Ethyl acetate"

# Or create the next Markdown procedure:
tools/build.fish new --md "Ethyl acetate"
```

A successful build of the shipped procedures prints these steps:

```text
==> export: recovering build/export/
==> export: planning org/procedures/
==> export: running ox-hugo
==> export: installing build/export/
==> validate: tools/validate.py --org-root org/procedures build/export md/procedures
validated 14 files: 0 errors, 0 warnings
==> build: hugo
==> build: pagefind
```

Press `Ctrl-C` to stop the preview server. It listens only on
`127.0.0.1`, so other machines cannot reach it. Use `serve --port N` to
choose another port. The preview does not reload after an edit; stop it and
run `serve` again.

`new` selects the next free `OSDB-NNNN` identifier across the Org sources,
Markdown sources, exports, and available Git history. It fills the file
name, slug, title, and current Europe/Berlin timestamps. Add
`--ai-model ID` when that model assisted with the procedure. Without this
option, an Org stub uses `#+AI_MODEL: none`, and a Markdown stub has no
`ai_model` field.

## Use the site

The built site provides these pages:

- `/` introduces the collection, searches it, lists recent procedures, and
  links reaction types and tags with their procedure counts.
- `/procedures/` lists every procedure by ID.
  `/procedures-by-date/` lists the same procedures by creation date, newest
  first. Each page links to the other ordering.
- `/procedures/osdb-NNNN/` shows one procedure, including its metadata,
  structure image or on-screen placeholder, and eight body sections.
- `/reaction_types/`, `/tags/`, and `/authors/` list the terms in each
  category. Their term pages list the matching procedures. For example,
  `/reaction_types/esterification/`, `/tags/sample-data/`, and
  `/authors/a.-example/` are term-page URLs.
- `/search/` provides full-text search and filters.

Search finds a procedure by its ID, product name, CAS number, any part of
its SMILES string, a tag, or a word in the procedure text. SMILES searches
ignore punctuation and compare only letters and digits. A fragment may
therefore match more than one compound. Results appear five at a time; use
**Load more results** to continue.

The Status, Reaction type, Tag, and Author filters each narrow a search term.
Selecting two values in the same group requires a procedure to carry both,
so selecting two reaction types produces no results. An empty search box
lists nothing. Search needs the site over HTTP, from
`tools/build.fish serve` or another web server; it does not work when you
open `public/index.html` through a `file:` URL. Without JavaScript, use the
browse-page links shown on the search page.

On a procedure page, **Copy** copies the SMILES and briefly reports
**Copied**. Clipboard access needs a secure context: `https:` or
`http://127.0.0.1`. At another address the button selects the SMILES and
reports **Selected: press Ctrl+C** instead.

## Print procedures

`tools/build.fish pdf` uses WeasyPrint to create A4 PDFs in `pdf/`. These
PDFs have the procedure ID and title in a running header and `Page N of M`
in the footer. Navigation, buttons, and an empty structure-image placeholder
are omitted. The sample-data banner remains. Tables stay within the margins,
numeric columns do not wrap, and table rows and numbered steps stay together
across page breaks.

The first printed page includes its full procedure URL, ID, status, and
last-modified time. The URL begins with `params.siteurl` from
`site/hugo.toml`, which defaults to `http://127.0.0.1:8000`. Set the public
origin for a PDF run with `HUGO_PARAMS_SITEURL`, for example:

```fish
env HUGO_PARAMS_SITEURL=https://orgsyndb.example.org tools/build.fish pdf
```

The URL is printed as text and is not fetched. The procedure page's
**Print / Save as PDF** button, or the browser's `Ctrl-P` command, uses the
same complete black-on-white A4 layout. Browser support for running headers
and page numbers varies; Firefox prints neither, while WeasyPrint includes
both.

## Daily workflow

1. Create a stub with `tools/build.fish new "Title"` for Org or add `--md`
   for Markdown.
2. Fill in its metadata and all eight body sections. Follow the appropriate
   authoring guide below.
3. Update `#+LAST_MODIFIED` in Org or `lastmod` in Markdown whenever you
   change the procedure.
4. Run `tools/build.fish validate`. Fix every error and review every warning.
5. Run `tools/build.fish serve`, then open
   <http://127.0.0.1:8000/> to inspect the built page.
6. Run `tools/build.fish pdf` when you need printable A4 files.

Org files remain the source of truth. Never edit their generated Markdown
copies in `build/export/`.

## Build command reference

`tools/build.fish` finds the repository from its own location, so you can
invoke it by path from another directory.

| Command | What it does |
|---|---|
| `export` | Exports every top-level `org/procedures/*.org` file into `build/export/`. Emacs output goes to `build/export.log` and is printed if export fails. |
| `validate` | Exports first, then validates the Org sources, their exports, and all Markdown procedures. Errors fail the command; warnings do not. |
| `validate ARGS...` | Passes the arguments directly to `tools/validate.py` without exporting. This form needs only Python. |
| `build` | Runs export and validation, builds the site into `public/` with Hugo, then indexes it with Pagefind. A validation error stops the command before Hugo. |
| `serve [--port N]` | Runs `build`, then serves `public/` on `http://127.0.0.1:N/` until `Ctrl-C`. The default port is `8000`. |
| `pdf` | Runs `build`, removes the previous `pdf/`, and renders every procedure to `pdf/<source-file-name>.pdf` with WeasyPrint. |
| `new [--md] [--ai-model ID] TITLE...` | Creates an Org stub with the next free ID, or a Markdown stub with `--md`. It never overwrites an existing file. |
| `clean` | Removes `build/`, `public/`, `pdf/`, and Hugo's generated cache files. |
| `clean --all` | Also removes `.emacs-batch/` and `.tools/`. Their contents are fetched again on the next relevant run. |
| `check-deps` | Reports required tools, optional Caddy, fetched tools, and the Fedora install command when something is missing. |
| `help` | Prints the command summary. `-h` and `--help` do the same. |

The normal `validate` command checks only top-level procedure files. A
subdirectory under `md/procedures/` is invalid. Procedure dates do not
schedule publication: a valid procedure with a future date is built
immediately.

## Generated directories

These directories are generated and must not be committed:

| Directory | Contents |
|---|---|
| `build/` | Org exports, export plans, temporary export data, and `export.log`. |
| `public/` | The complete static website and Pagefind index. |
| `pdf/` | One generated PDF per procedure. |
| `.emacs-batch/` | Repository-local ox-hugo and tomelr installations. |
| `.tools/` | The verified Pagefind binary. |
| `site/resources/` | Hugo's generated resource cache. |

Hugo may also create `site/.hugo_build.lock`. `clean` removes the build,
site, PDF, and Hugo cache outputs. `clean --all` also removes both fetched
tool caches.

## Development

Run the test suite from the repository root with:

```fish
python3 -m pytest tests
```

The command needs pytest. Node is optional and lets the tests exercise the
real Pagefind search; it is never needed to build or view the site.
`poppler-utils` is also optional and supplies `pdftotext` and `pdfinfo` for
PDF checks. Tests that cannot find an optional tool skip their checks and
name the missing tool.

## Troubleshooting

If a poppler tool reports `Embedded font file may be invalid` for Cantarell
in a WeasyPrint PDF, the warning is harmless and the pages still render
correctly.

## Optional validation before commits

The repository includes `tools/hooks/pre-commit`, an optional Git hook. A
hook is a command that Git runs automatically at a particular point. This
one runs `tools/build.fish validate` before every commit and refuses the
commit if validation finds an error.

Enable it for this repository with:

```fish
git config core.hooksPath tools/hooks
```

Alternatively, link the supplied hook into Git's default hook directory:

```fish
ln -s ../../tools/hooks/pre-commit .git/hooks/pre-commit
```

Nothing enables the hook automatically. It validates files as they exist in
the working tree, including changes that are not staged, and it adds the
normal export time to every commit.

## Deployment example

`tools/build.fish build` creates the deployable site in `public/`; OrgSynDB
does not deploy it. [deploy/Caddyfile.example](deploy/Caddyfile.example)
shows how Caddy can serve a copy of that directory. Replace
`orgsyndb.internal` with the server's internal host name and
`/srv/orgsyndb/public` with the directory containing the copied site. Review
the example's `tls internal` setting against your organisation's TLS setup.

## Authoring references

- [Procedure schema](docs/SCHEMA.md): exact field, file-name, vocabulary,
  body-section, and validator rules.
- [Markdown authoring guide](docs/AUTHORING.md): step-by-step instructions
  for co-workers writing procedures in Markdown.
- [Org authoring guide](docs/AUTHORING-ORG.org): Org templates, timestamps,
  export behaviour, and Emacs conventions.
