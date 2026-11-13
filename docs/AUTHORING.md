# Writing a procedure in Markdown

This guide takes you from the supplied template to a checked procedure. The
procedures live in a *collection*, a project folder of its own that the
OrgSynDB program turns into the website. You do not need to know Git, Org,
TOML, or Hugo.

Markdown is a plain-text format that uses marks such as `##` for headings.
TOML is the small metadata block at the top of each procedure. Hugo is the
program that turns the procedure files into the website. You can follow this
guide without using any of them directly.

For exact spelling, allowed values, and field rules, use the
[procedure schema](SCHEMA.md). This guide explains the work in order instead
of repeating that reference.

Diese Anleitung gibt es auch auf Deutsch: [AUTHORING.de.md](AUTHORING.de.md).

## 1. Get a procedure file

If you write in Emacs, the `orgsyndb` package completes keys and values in
the information block at the top of the file. It shows problems while you
write and after saving, keeps the modification time current and previews
the page. For installation, see the application's README, section “Edit in
Emacs”.

The file to copy is
[`templates/procedure.md`](../templates/procedure.md).

The easiest method is to ask the owner to create your file with:

```sh
orgsyndb new --md "Product name"
```

Run it inside the collection folder. This creates a file such as
`md/procedures/OSDB-0003-product-name.md`. It fills in the assigned procedure
number, the web-page name, the title, and both dates.

When `registry` in the collection's `orgsyndb.toml` is an HTTP or HTTPS
address, the lab application assigns the number. You need a personal
access token: a secret that lets the command request a number as your
account. Sign in to the lab application, choose **Access tokens** beside
your initials or open `/lab/accounts/tokens/`, enter a **Name** and choose
**Create**. Copy the token immediately; it is shown only once.

Put it on the first line of `~/.config/orgsyndb/token` on the computer
running the command. If `XDG_CONFIG_HOME` is set and not empty, use
`$XDG_CONFIG_HOME/orgsyndb/token` instead. You can also set `ORGSYNDB_TOKEN`
in the command's environment; a non-empty value takes precedence over the
file. Keep the token outside the collection. To stop a token working,
choose **Revoke** on the same page. Deactivating its account also stops it.

If no token is available, the command reports `no access token`. If the
application is unreachable or refuses the request, the command shows the
address and reason. In each case it exits 1 and creates no file. It waits
up to 30 seconds; you cannot get an ID offline. For status 401, check your
token and whether your account is active. For status 409 with
`no import of the collection has been accepted yet, so its IDs are not known`,
ask the owner to get the collection's first import accepted, then try again.

With a registry file or no `registry` setting, the command takes the next
number above those in the procedure sources, exports and available Git
history. Deleted numbers are not reused. It warns if history is unavailable
or the copy holds only part of it (a shallow clone), because older deleted
numbers may be unseen. `ORGSYNDB_REGISTRY` does not change where `new`
gets its number.

If you copy the template yourself, first ask the owner to create a stub
with `orgsyndb new --md` for this file and give you its `OSDB-NNNN` number.
Replace `OSDB-0000` in `id` and in the file name. Replace
`osdb-0000` in `slug` with the same number in lowercase. Save the file with
this pattern:

```text
OSDB-NNNN-short-name.md
```

Use lowercase letters, digits, and single hyphens in `short-name`. The owner
can make these replacements for you if you send back the unrenamed template.

## 2. Fill in the information block

The information block, called *front matter*, is everything between the two
`+++` lines. Keep both `+++` lines. Lines beginning with `#` are instructions
and are not shown on the website.

Change the value after each equals sign. Keep text in double quotes. Keep
numbers without quotes. Keep lists inside square brackets. Text entries
use double quotes; each product entry uses curly braces, as shown below.

The template describes a **specific procedure**, one run. For a shared
method applied to several substrates, use a **general procedure**, as
explained below.

Fill in these required fields:

- `id` and `slug`: leave the values supplied by `new`, or use the number the
  owner gave you.
- `title`: the product name or general method shown at the top of the page.
- `date`: when the procedure was first written.
- `lastmod`: when the procedure was last changed. Update it after every
  later edit.
- `authors`: the lab account user names of everyone who wrote the procedure,
  each once, for example `authors = ["klehmann", "aschmidt"]`. Each account
  must appear in the collection's registry snapshot; it may be inactive.
  Replace the template's `a.example` with your user name before validating.
- `status`: whether the procedure is a draft, checked, or retired.
- `reaction_types`: one category from the lab registry’s `reaction-types`
  vocabulary.
- `tags`: useful lowercase search terms. Replace the template's
  `change-me`. The `sample-data` tag adds a warning banner to the page and
  to printouts, so never use it for a real procedure.
- `scale`: the amount of product made, or the typical scale of a general
  procedure.
- `hazards`: short descriptions of the main hazards.
- `products`: required for a specific procedure; for a general procedure, use
  `scope` instead, as explained below. List one or more compound keys, each
  with its isolated yield. A key identifies a substance in the lab
  application’s registry; the next section explains how to find or add one.

The template also contains optional, commented fields for starting
materials (`substrates`), checkers, literature references and an AI model.
Delete the `#` at the start of an optional line when you need it. Leave the
line commented when it does not apply. `checked_by` is a free-text list of
names.

In Emacs, completion for `authors` offers the registry's account user names,
each annotated with the account's name. Completion for `checked_by` offers
names already used under that key in procedures; you can also enter other
names.

Use `notebook` to name the paper notebook entry the procedure comes from,
and `project` to assign it to a project. These two optional *journal fields*
are built in for every collection; do not declare them in `orgsyndb.toml`.
Your collection can declare other fields under `[[fields.procedure]]`,
such as the demo's `working_time` and `inert_atmosphere`.
Add values as `key = value` lines in the information block, before any
table. The demo's aspirin procedure sets these after `scale`:

```toml
notebook = "AE-1/2"
project = "first-year-practical"
working_time = 2.5
inert_atmosphere = false
```

Keep text and choice keys in double quotes. Write numbers and `true` or
`false` without quotes; numbers use a decimal point and no unit. A choice
uses a term key from its named registry vocabulary; `multiple = true`
requires a non-empty list of different keys. A field with `required = true`
must be set, including in a general procedure. A field with `unique = true`
needs a value no other procedure uses. In the demo, all four are optional.

Write a notebook reference as `<code>/<number>`, such as `AE-1/2` for entry
2 of notebook `AE-1`. The code uses capital letters and digits joined by
single hyphens; the entry number runs from 1 to 9999 and has no leading zero.
The exact pattern is `[A-Z0-9]+(-[A-Z0-9]+)*/[1-9][0-9]{0,3}`. Register the
notebook in the lab application at `/lab/journal/` before validating or
importing the procedure. If you see `unknown notebook`, check the code and
that the collection's registry snapshot lists the notebook. No other
procedure may use the same entry; translations of one procedure share it.
The entry's contents stay on paper.

Set `project` to one key from the lab registry’s `projects` vocabulary,
including `first-year-practical` under `teaching` in the demo. Use one
quoted key, not a list. Working time is in hours and must be at least zero.
A choice field’s `vocabulary` names `chemical-classes`, `inventory-groups`,
`projects` or `reaction-types`. The
[field reference](SCHEMA.md#procedure-field-declarations) gives the exact rules.

Name products and starting materials by their registry keys. For example,
the demo's aspirin procedure uses:

```toml
substrates = ["salicylic-acid", "acetic-anhydride"]
products = [{ compound = "acetylsalicylic-acid", yield_percent = 75 }]
```

Give every product its own `compound` and `yield_percent` inside braces.
Separate product entries with commas inside the square brackets. Yields
are numbers from 0 to 100, without quotes or `%`. Do not list a key twice
in either list or list a product as a starting material.

The site links the starting materials to their compound pages. It derives
**Precursors** from other procedures that make those compounds and
**Used in** from procedures that start from your products. For example,
the aspirin page links to OSDB-0001 because that procedure makes
`salicylic-acid`. You do not enter these procedure links yourself.

Write `date` and `lastmod` without quotes. Use Europe/Berlin local time and
include `+01:00` in winter or `+02:00` in summer, as shown in the template.
The [procedure schema](SCHEMA.md#front-matter-fields) gives the exact format
and every allowed value.

### Find or add the compounds

The *compound registry* is the lab application's list of substances, shared
by every procedure that makes or uses them. Open `/lab/registry/` in the lab
application and look for an existing substance before adding one. The key
identifies the compound; the site does not compare structures to find
duplicates.

Create and edit substances in the lab application. Use the substance's key
in `products` or `substrates`, for example `ethyl-acetate`. Keys use lowercase
letters and digits separated by single hyphens. Replace the template's
`example-compound` with the key you actually use. Creating a procedure stub
does not create a substance.

The collection's `orgsyndb.toml` names the registry in `registry`: the address
of the lab application's snapshot, a saved copy of its registry, such as
`http://localhost:8000/lab/registry/snapshot.json`, or a snapshot file's path.
A relative path starts at the collection folder. A non-empty
`ORGSYNDB_REGISTRY` environment variable overrides this setting. Ask the
owner to set it if the collection has no registry.

Names and chemical data come from the substance in that registry: formula,
molar mass in g/mol, SMILES (a text notation for molecular structures) and
CAS Registry Number. An English site uses `name`; a German site uses
`name_de` when supplied, otherwise `name`. The site also shows the substance's article number, short name,
chemical classes and group. These four fields are built in; their display
is fixed. The [field reference](SCHEMA.md#collection-field-declarations)
gives the details.

To show a structure, place `static/structures/<key>.svg` or
`static/structures/<key>.png` in the collection, using the substance's key.
For example, use `static/structures/isopentyl-acetate.svg` for
`isopentyl-acetate`. The build uses the SVG when both files exist. A
substance without either file has no structure image. For an SVG, use black
lines and text on a white background rectangle. Give the file a `<title>`,
and do not include scripts, external images, or other external references.
The site shows the image on a white panel in dark mode. Ask the owner to add
or check the image if you do not work with SVG files.

You may register a starting material even if no procedure makes it. A compound
that no procedure uses is also allowed. **Compounds** in the site navigation
opens the catalogue at `/compounds/`, which you can filter and search.
Each name links to a page with chemical data, the structure when supplied,
**Made by** procedures with yields and status, and **Used in** procedures
with status. A general procedure appears
under **Made by** once per entry that makes the compound, as
`<ID> <title> · entry <n> · <yield> % · <status>`. **Used in** lists each
procedure once, and the directory counts each procedure once. After
**Used in**, **Sequences** links the sequences that name this compound as their
target, by sequence ID. It appears only when there are matching sequences.

**Routes** ends the page, after **Sequences** when present, if a route goes
beyond one step: a procedure makes a starting material for another step.
The tree shows steps that make the compound, then each step's starting
materials, then the steps that make those, down to compounds no procedure
makes. Under a compound, any one step will do; under a step, all starting
materials are needed. Each step shows the procedure link, entry number when
needed, yield and status, as in **Made by**. All published procedures take
part, whatever their status. A general procedure's entry uses only its own
starting materials. Compound links carry the substance’s article number
and short name when supplied.

A step is omitted if it starts from a compound already above it on the same
branch, so the tree never follows a cycle. If all steps would loop back, the
compound appears without steps and must be obtained another way. The display
uses a fixed depth limit of 6 steps and a fixed budget of 200 steps per
tree. A larger tree is drawn to the largest depth that fits. When more than
200 steps make the compound directly, the tree shows only those. A compound
cut off by a limit ends with **more steps on its page**; follow its link to
continue. Routes are derived during the build. You write nothing extra in a
procedure or `orgsyndb.toml`.

### Write a general procedure

When one method covers several substrates, write it once as a **general
procedure**. Put each application of the method in `scope`, a list of entries
with starting materials, products and yields. Its presence makes the procedure
general; you do not add a `kind` field.

Remove the template's top-level `products` and `substrates` lines. Keep all
other required fields, including `scale` for the typical scale. Inside the
front matter, write an array of tables in braces. This excerpt uses the three
entries of the demo's general procedure:

```toml
scale = "10 mmol"
scope = [
  { substrates = ["4-acetylbiphenyl"], time = "30 min", products = [{ compound = "1-biphenyl-4-yl-ethanol", yield_percent = 90 }] },
  { substrates = ["acetophenone"], time = "20 min", products = [{ compound = "1-phenylethanol", yield_percent = 85 }] },
  { substrates = ["4-bromoacetophenone"], scale = "5 mmol", time = "30 min", products = [{ compound = "1-4-bromophenyl-ethanol", yield_percent = 88 }] },
]
```

Each entry requires non-empty `substrates` and `products`. Products use the
same `compound` and `yield_percent` fields as above. Entries are numbered from
1 in their order. Within each entry, do not repeat a key or list a product as a
starting material. A compound may be a starting material in one entry and a
product in another. Two entries of one procedure must not have the same
substrates and the same product compounds, even in a different order or with
different yields. This lets a sequence step identify one entry by its compounds.

You may add `scale`, `time`, `temperature` and `note` to an entry. Write a time
as a number followed by `min`, `h` or `d`, such as `"30 min"`. Write
temperature as an unquoted number in °C, such as `temperature = 80`, without a
unit. `scale` follows the usual number-and-unit rule; `note` is non-empty text.
Keep the eight body sections and describe the shared method there. The complete
[OSDB-0009
example](../examples/demo/md/procedures/OSDB-0009-benzylic-alcohols.md) reduces
three aryl methyl ketones with sodium borohydride. It is the ninth procedure in
the demo, which contains sample data rather than verified experimental results.

To show the overall reaction, place an SVG or PNG under `static/structures/`
and set this optional procedure field:

```toml
scheme_image = "structures/aryl-ketone-reduction.svg"
```

The path must start with `structures/`, contain no `..` component and name an
existing `.svg` or `.png` file under `static/`. Any procedure may use
`scheme_image`; it replaces product structures in the title block. A general
procedure without it shows the **No structure image** placeholder.

### How the fields appear on the page

The labels below are those of an English site; a German site, the default,
shows them in German, such as **Kopieren** for **Copy**. The title block shows
`id` and a `status` badge above the title. When `status` is `checked` and
`checked_by` is set, the checkers' names follow the badge, so the line reads
**checked by** followed by the names. Under the title, `scale` appears as
**Scale** and the product yields as **Yield**. For a specific procedure, one
product shows only its percentage; several show a percentage and compound name
for each, in product order. The **Print / Save as PDF** button follows them.
For a general procedure, **Scale** is the typical top-level scale and **Yield**
is the range over all products of all entries, `<min>–<max> %`, or one
percentage when all yields are equal.

Without `scheme_image`, a specific procedure shows one structure figure for
each product whose compound has an image, in product order. On a wide screen,
the figures sit to the right of the title, above the information panel. In a
narrow window they follow the print button, before the panel. In print they
also precede the panel. When neither a scheme nor product figures are shown,
the screen shows a **No structure image** placeholder, which is omitted from
printouts. A rule closes the title block on screen.

The information panel always links the product names to their compound pages
under **Product** or **Products**, even when a name equals the title. For a
single product it also shows formula, molecular weight, CAS number when present
and SMILES. For several products, find those data on the compound pages.
**Starting materials** links the compounds in `substrates`. For a general
procedure, both lists include all entries, each compound once in order of first
appearance. Precursor and used-in links also consider every entry. The panel
then shows reaction type, tags, authors, checkers when present for draft or
retired procedures under **Checked by**, journal fields, declared procedure
fields, created and modified times, and precursor or used-in links. When your
procedure is a
step of a sequence,
**Sequences** follows **Used in** and links those sequences by title, ordered
by sequence ID. Formula digits appear as subscripts. Molecular
weight gains `g/mol`, yield gains a percent sign, and SMILES has a **Copy**
button. Reaction type and tag values link to pages that list related
procedures. Under **Authors**, each account's name links to
`/authors/<user name>/`, for example `/authors/klehmann/`. The site shows
names exactly as the accounts have them, including capitalization. The
author directory, author pages and catalogue's **Author** filter show these
names too. The eight body sections appear beside the panel on a
wide screen and after it in a narrow window or in print.

After each product or starting-material link, the panel shows the substance’s
article number and short name when supplied, in that order.
The link text stays the compound's name. One space and a muted note in
parentheses follow it, for example **Acetic anhydride (Ac2O)** in the
demo. Values appear without labels, separated by `, `, as on the compound
page.
A compound with none of these values gets no note. Procedure search finds
these values because the panel is indexed. The yield line, catalogue
**Details**, image alt texts and page titles carry no note.

The panel shows the journal fields you set first, then the collection's
fields in declaration order, before **Created** and after **Checked by**
when that label is present.
The demo shows **Lab notebook**, **Project**, **Working time** and
**Inert atmosphere**. Choices use their vocabulary labels, such as
**Teaching › First-year practical**; working time appears as `2.5 h`, and
booleans as **Yes** or **No**. A German site uses the declared German labels,
`2,5 h` and **Ja** or **Nein**. Catalogue search finds these displayed values.

A general procedure adds **Scope** before **Summary**, with one row per entry.
**Entry**, **Starting materials**, **Products** and **Yield** always appear.
**Scale**, **Time**, **Temperature** and **Note** appear only when some entry
sets them; an unset value leaves an empty cell. Starting materials and products
link to compound pages, and products show small structure images when the
collection has matching image files. The compound links carry the same notes
as the panel. For example, entry 1 of OSDB-0009 makes the same alcohol as OSDB-0005,
so that compound's page lists both routes.

## 3. Write the procedure

Write below the closing `+++`. Keep these eight `##` headings in this order:

1. Summary
2. Reagents
3. Procedure
4. Workup and Purification
5. Characterization
6. Notes
7. Hazards and Waste Disposal
8. References

Replace the example text and table rows. Include the quantities,
temperatures, times, observations, workup, purification, characterization,
and safety information needed to follow the procedure. Write `None.` under
References when there is no reference.

To let readers jump from a step to a note, number the notes as an ordered
list under Notes. In the body, write a reference as plain text `(Note 2)`:
the word `Note`, a space and the number, in parentheses. The site links
it to note 2 if that note exists. Forms such as `(Notes 2 and 3)`,
`(Note 2a)` and `see Note 2` stay plain text. References inside code
blocks or inline code are not linked.

Keep the Reagents table's six columns in this order: **Reagent**, **CAS**,
**MW (g/mol)**, **Amount**, **mmol**, and **Equiv**. A wide table scrolls
sideways inside its own area on screen and wraps to fit the paper when
printed.

You can compare your structure with
[`OSDB-0002-aspirin.md`](../examples/demo/md/procedures/OSDB-0002-aspirin.md)
in the demo collection.
That file is sample data, not an experimentally verified procedure.

## 4. Save or send the file

If you have the collection folder, save the finished file directly inside
its `md/procedures/`. Do not put it in a subfolder.

If you do not have the collection, send the `.md` file to the owner. Tell the
owner whether you used a procedure number they assigned or left the template
number in place. The owner can then place, rename, and check it. Include
any new structure images, and ask the owner to add any missing substances
in the lab application.

## 5. Check the file

A validator is a program that checks the file for known mistakes. A terminal
is a window where you type commands. If you have the collection and the
OrgSynDB program, open a terminal in the collection folder and run:

```sh
orgsyndb validate
```

The command reads the registry, exports the owner's Org procedures and then
checks every procedure and the sequences in `md/sequences/` against it.
The lab application checks substance values. Each problem has this form:

```text
path/to/file.md:field: error: message
path/to/file.md:field: warning: message
```

Read each line from left to right:

- The first part is the file to open.
- The second part is the field or body section to inspect.
- `error` means a procedure, sequence or registry is invalid and the
  check fails.
- `warning` means the check can finish, but you should review and correct
  the problem.
- The final text explains what is wrong.

For example, `products[1].yield_percent` names the yield in the first
product entry; product numbers start at 1. An `unknown compound` error
means you must check the key in the lab registry. A registry error under
`substances` names a substance keyed `group`, which conflicts with the
site’s group-tab directory. The lab application refuses this key, so the
snapshot file was made another way; give the substance another key there.
A line naming `body` tells you to inspect the section headings. Run the
command again after correcting the file. The last line reports how many
files, errors, and warnings were found; its file count includes procedures
and sequences, including language variants.

An `unknown author` error under `authors` means the registry snapshot has
no account with that user name. Check the spelling and ask staff to create
the account if needed. `"<name>" is named twice` means you must remove the
repeated user name. `must be a list of user names, e.g. ["a.example"]`
asks for a list of quoted user names; `must not be empty` asks for at least
one author. Use the plural key `authors`; `author` reports
`use authors, a list of user names`.

For a general procedure, `scope[2].products[1].yield_percent` means the yield
of the first product in entry 2. `must not be empty` under `scope` means you
need at least one entry. If a top-level field reports
`a general procedure lists them in scope; move <key> into its entries`, remove
that line and put the data inside the relevant entries. A time error asks for a
number followed by `min`, `h` or `d`; a temperature error asks for an unquoted
number in °C. `has the same substrates and products as entry <m>` under
`scope[n]` means entry n repeats entry m's compounds; keep only one such entry.

For a sequence, `steps[2].product` names the product used to select step 2's
scope entry. `name its entry by a product: <keys>` asks you to choose a product
key. If the message says it is a product of several entries, give the chosen
entry's complete `substrates` and `products` lists instead of `product`.
`steps[2].entry` reports `not a key of a step; name the entry by its product`.
`must list at least two steps` requires a longer sequence; `not found in any
content root` means a step's procedure ID is missing. `starts from none of the
products of step 1` under `steps[2]` means that step 2 takes no product of step
1 as a starting material. Check the order and the chosen scope entries.
`is not a product of the last step` under `target` means the final step does
not make the named target. The [sequence message table](SCHEMA.md#sequence-messages)
explains the remaining errors.

If a message is unclear, look up its field in the
[procedure schema](SCHEMA.md). If you sent the file to the owner, the owner
can run the same check and send you the messages.

## 6. Preview the page

Run:

```sh
orgsyndb serve
```

Wait for this line:

```text
serving http://127.0.0.1:8000/ (Ctrl-C to stop)
```

Open <http://127.0.0.1:8000/> in a web browser on the same computer. The
address is local to that computer. Press `Ctrl-C` in the terminal to stop the
preview.

The navigation is **Procedures**, **Compounds**, **Sequences**, **Help**.
The home page's **Browse** list includes **Sequences** with a count. Open it
or the navigation link to browse `/sequences/`, ordered by ID with linked
titles and targets, step counts and overall yields. A sequence page shows
its ID and title, **Steps** and **Overall yield**, a scheme, its linked
procedures with entry numbers where needed, reaction type, yield and status,
then your notes. The scheme shows starting materials, intermediates and target
with matching structure images from `static/structures/` where available.
Compound links in the scheme and the directory's targets carry the same
notes as the panel.
A plus joins the first step's starting materials, and arrows show step
number, reaction type and yield. It runs down the page in narrow windows.
Sequence pages are absent from the procedure search index; use their links
to find them.

On a procedure page, choose **Print / Save as PDF** to open the browser's
print dialog. The print layout is A4, complete, and black on white. Firefox
does not add the running header and page numbers that the owner's
WeasyPrint-generated PDFs contain.

The preview does not update while it is running. After an edit, stop it and
run `orgsyndb serve` again.

To find your general procedure, open **Procedures** and use the **Kind**
filter: **Specific procedure** or **General procedure**. The tabs are **All
procedures**, **General procedures**, **Reaction types**, **Tags** and
**Authors**. **General procedures** opens `/general-procedures/`, a catalogue
limited to general procedures. Its header search is labelled **Search general
procedures** and searches within that list. **Only general procedures · Browse
all procedures** links back to the full catalogue. **Clear all** keeps this
restriction; **Browse all procedures** removes it while carrying your query,
other filters, sort and view. The address parameter `kind=general` selects the
same kind in the full catalogue. Without JavaScript, the general-procedures
page still lists its procedures by ID. Catalogue **Details** includes products
from every entry and shows the yield range.

The built-in **Project** field and your collection's declared boolean and
choice fields with `facet = true` also appear as filters between **Status**
and **Tag**, including on
reaction-type, tag, author and general-procedure pages. In the demo, use
**Project** and **Inert atmosphere**. Selecting **Teaching** includes its
practicals; selecting **Research** includes biaryls and cinnamates. Every
catalogue offers values from the whole collection. You can share selections
through the address, for example
`/procedures/?project=research&inert_atmosphere=true`.

## 7. Write in German or translate a procedure

The site shows one language, German unless the owner has set it to
English. A procedure in any language appears on it. When a procedure has
a file in the site's language, that file is shown instead of the others.

To start a new procedure in German, ask for a German stub:

```sh
orgsyndb new --md --lang de "Produktname"
```

This creates a file such as `md/procedures/OSDB-0003-produktname.de.md`
from the German template, with German notes and German section headings.
The [German version of this guide](AUTHORING.de.md) explains it step by
step. A file without `.de` may also be written in German; then add
`language = "de"` to its information block.

Use the [German procedure style guide](STYLE.de.md) for the wording and the
[German organic-synthesis glossary](GLOSSARY.de.md) for terms, fixed
phrases, reusable sentences, and their English equivalents.

To translate an existing procedure, copy its file and add the language code
before the extension, for example `OSDB-0002-aspirin.md` to
`OSDB-0002-aspirin.de.md`. Keep the `id`, `slug`, `status`, `reaction_types`,
`tags`, `products`, `substrates` and `scheme_image` as they are. Repeat every
journal field and declared procedure field with the same value, or omit it
in both variants.
Do not translate these values; the site uses `label_de` for German field
labels. Keep `scope` and its entry order, translating only each entry's `note`.
The check reports
differences in the shared fields as errors. Numeric yields compare by value, so
`85` and `85.0` agree. Compound names come from `name` and `name_de` in the
lab registry; add or edit `name_de` in the lab application for the German
name. Translate the title, the hazards and the body, set `date` and `lastmod`
to the time of the translation, and use the section headings and Reagents columns of the new
language, which the [procedure schema](SCHEMA.md#languages-and-variants) lists.

## 8. Write a synthesis sequence

When you use several procedures in order to make a target compound, record
that route as a **synthesis sequence**. Each step names the procedure you run
and, for a general procedure, the scope entry you use. The site checks that
the steps connect and calculates their overall yield.
The sequence records the route your group runs; the compound page's
**Routes** tree is derived from the collection's procedures.

From inside the collection, create a stub with:

```sh
orgsyndb new --sequence "Aspirin route"
```

The command uses [templates/sequence.md](../templates/sequence.md) to create
`md/sequences/SEQ-NNNN-aspirin-route.md`, where `NNNN` is the assigned
number from `0001` to `9999`. `orgsyndb init` creates this folder. The
command fills `id`, its lowercase `slug`, the title and both dates. Leave
`id` and `slug` as supplied. With a registry address it requests the ID
from the lab application using your token, as in section 1. With a registry
file or no setting it takes the next ID above those in `md/sequences/`
and all its available Git history, including deleted files. The same
failure messages and history warnings apply.

Sequences are Markdown files, even when their steps use Org procedures.
Do not add `--md` or `--lang` to `--sequence`; either combination exits 2.
The file name has the form `SEQ-NNNN-short-slug.md`; use lowercase letters,
digits and single hyphens in the short slug. For a German version, copy the
file with `.de` before `.md` and translate the title and notes. There is
no German sequence template.

Keep the two `+++` lines. Set `title` and give `date` and `lastmod` as
unquoted datetimes with their UTC offsets, as for a procedure. `lastmod`
must not precede `date`. Set `target` to the final compound's registry key and replace
the template's steps with your procedures in execution order. This complete
example is the demo's second sequence:

```markdown
+++
id = "SEQ-0002"
slug = "seq-0002"
title = "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone"
date = 2026-10-23T10:05:00+02:00
lastmod = 2026-10-23T10:20:00+02:00
target = "1-biphenyl-4-yl-ethanol"
steps = [{ procedure = "OSDB-0004" }, { procedure = "OSDB-0009", product = "1-biphenyl-4-yl-ethanol" }]
+++

## Notes

The 4-acetylbiphenyl from step 1 is reduced in step 2 as entry 1 of the
general procedure.
```

You need at least two steps. Each `procedure` must name an existing procedure.
For a general procedure, set `product` to a compound key made by exactly one
scope entry. If that product belongs to several entries, give `substrates`
and `products` instead. Both lists must contain the chosen entry's compound
keys in full, in any order, without repeats. Write product keys without yields.
This is the complete-list form for the same demo entry:

```toml
{ procedure = "OSDB-0009", substrates = ["4-acetylbiphenyl"], products = ["1-biphenyl-4-yl-ethanol"] }
```

Use one form only. A specific procedure takes none of `product`, `substrates`
or `products`. `entry` is not a step key. Reordering the procedure's scope
keeps the step on the same chemistry; the build determines the entry number
for the page and manifest.

In Emacs, complete inside the `product` string to choose from the named
general procedure's products. Each appears once in file order, with the entry
numbers that make it, for Markdown and Org general procedures alike.
Completion inside `substrates` and `products` lists offers compound keys.
A specific procedure offers no `product` candidates; there is no completion
after `entry =`.

Each step after the first must start from a product of the previous step;
for general procedures, use only the chosen entry's starting materials and
products. The target must be a product
of the last step. Do not add `authors`: the steps credit their procedures'
authors. The body holds notes, such as which intermediate you dry or purify;
it does not need a procedure's eight sections.

The demo also includes
[SEQ-0001, “Aspirin from oil of wintergreen”](../examples/demo/md/sequences/SEQ-0001-aspirin-from-wintergreen.md),
OSDB-0001 → OSDB-0002, with an overall yield of 60 %. SEQ-0002 goes through
entry 1 of OSDB-0009 and gives 77 %. These are sample data. Overall yield
multiplies each step's yield of the product used by the next step and the
last step's yield of the target. If several products carry on, it uses the
first in product order. The displayed result rounds to a whole percent, with
halves rounded up. Enter no yield in the sequence itself.

To translate it, copy the file with `.de` or `.en` before `.md`. Keep the
base name, `id`, `slug`, `target` and ordered `steps` exactly as written,
including the order within `substrates` and `products` lists. Translate the
title and notes and set the dates for that version. Both demo sequences have
German variants. The site publishes one variant per ID: the site's language
first, then an untagged file, then the other language. Run `orgsyndb validate` and
restart `orgsyndb serve` to check the sequence and its links. The
[schema reference](SCHEMA.md#synthesis-sequences) gives the exact rules.
