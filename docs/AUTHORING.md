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

The file to copy is
[`templates/procedure.md`](../templates/procedure.md).

The easiest method is to ask the owner to create your file with:

```sh
orgsyndb new --md "Product name"
```

Run it inside the collection folder. This creates a file such as
`md/procedures/OSDB-0003-product-name.md`. It fills in the next procedure
number, the web-page name, the title, and both dates.

If you copy the template yourself, first ask the owner for the next
`OSDB-NNNN` number. Replace `OSDB-0000` in `id` and in the file name. Replace
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
- `authors`: everyone who wrote the procedure.
- `status`: whether the procedure is a draft, checked, or retired.
- `reaction_types`: one reaction category.
- `tags`: useful lowercase search terms. Replace the template's
  `change-me`. The `sample-data` tag adds a warning banner to the page and
  to printouts, so never use it for a real procedure.
- `scale`: the amount of product made, or the typical scale of a general
  procedure.
- `hazards`: short descriptions of the main hazards.
- `products`: required for a specific procedure; for a general procedure, use
  `scope` instead, as explained below. List one or more compound keys, each
  with its isolated yield. A key is the name of a file in `compounds/` without
  `.toml`; the next section explains how to find or create it.

The template also contains optional, commented fields for starting
materials (`substrates`), checkers, literature references and an AI model.
Delete the `#` at the start of an optional line when you need it. Leave the
line commented when it does not apply.

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

The *compound registry* is the collection's `compounds/` folder. Each
compound has one `<key>.toml` file containing its name and chemical data,
shared by every procedure that makes or uses it. Look there for an existing
entry before adding one. The key identifies the compound; the site does
not compare structures to find duplicates.

For a new compound, copy
[`templates/compound.toml`](../templates/compound.toml) into `compounds/`.
Choose a file name with lowercase letters and digits separated by single
hyphens, such as `ethyl-acetate.toml`. Use `ethyl-acetate` as the key in
your procedure. Replace the template's `example-compound` key in your
procedure with the key you actually use. Creating a procedure stub does not
create its compound records.

Fill in `name`, `formula`, `mw` in g/mol, and `smiles`, the text notation
for the structure. The optional `name_de` supplies the name on a German
site; without it, that site uses `name`. An English site always uses `name`.
You may also add `cas`, the CAS Registry Number, and `structure_image`.
Keep text in quotes and molecular weight as a positive number without
quotes. Compound files contain no `+++` lines or `[product]` heading.

To show a structure, place an SVG or PNG file in the collection's
`static/structures/` and set `structure_image` in the compound file, for
example `structure_image = "structures/isopentyl-acetate.svg"` for
`isopentyl-acetate`. For an SVG, use black lines and text on a white
background rectangle. Give the file a `<title>`, and do not include scripts,
external images, or other external references. The site shows the image on
a white panel in dark mode. Ask the owner to add or check the image if you
do not work with SVG files.

You may register a starting material even if no procedure makes it. A compound
that no procedure uses is also allowed. **Compounds** in the site navigation
opens the directory at `/compounds/`. Each name links to a page with chemical
data, the structure when supplied, **Made by** procedures with yields and
status, and **Used in** procedures with status. A general procedure appears
under **Made by** once per entry that makes the compound, as
`<ID> <title> · entry <n> · <yield> % · <status>`. **Used in** lists each
procedure once, and the directory counts each procedure once. After
**Used in**, **Sequences** links the sequences that name this compound as their
target, by sequence ID. It appears only when there are matching sequences.

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
product in another.

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
retired procedures under **Checked by**, created and modified times, and
precursor or used-in links. When your procedure is a step of a sequence,
**Sequences** follows **Used in** and links those sequences by title, ordered
by sequence ID. Formula digits appear as subscripts. Molecular
weight gains `g/mol`, yield gains a percent sign, and SMILES has a **Copy**
button. Reaction type, tag, and author values link to pages that list related
procedures. The site title-cases author names for display, so a name entered as
`van` appears as `Van`. The eight body sections appear beside the panel on a
wide screen and after it in a narrow window or in print.

A general procedure adds **Scope** before **Summary**, with one row per entry.
**Entry**, **Starting materials**, **Products** and **Yield** always appear.
**Scale**, **Time**, **Temperature** and **Note** appear only when some entry
sets them; an unset value leaves an empty cell. Starting materials and products
link to compound pages, and products show small structure images when their
registry records have them. For example, entry 1 of OSDB-0009 makes the same
alcohol as OSDB-0005, so that compound's page lists both routes.

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
any new compound files and structure images, or ask the owner to add their
registry entries.

## 5. Check the file

A validator is a program that checks the file for known mistakes. A terminal
is a window where you type commands. If you have the collection and the
OrgSynDB program, open a terminal in the collection folder and run:

```sh
orgsyndb validate
```

The command exports the owner's Org procedures and then checks every
procedure and compound record, plus sequences in `md/sequences/`. Each
problem has this form:

```text
path/to/file.md:field: error: message
path/to/file.md:field: warning: message
```

Read each line from left to right:

- The first part is the file to open.
- The second part is the field or body section to inspect.
- `error` means a procedure, compound record or sequence is invalid and the
  check fails.
- `warning` means the check can finish, but you should review and correct
  the problem.
- The final text explains what is wrong.

For example, `products[1].yield_percent` names the yield in the first
product entry; product numbers start at 1. An `unknown compound` error
means you must check the key and its file in `compounds/`. A message such
as `compounds/ethyl-acetate.toml:mw` names a field in that compound file.
A line naming `body` tells you to inspect the section headings. Run the
command again after correcting the file. The last line reports how many
files, errors, and warnings were found; its file count includes compound
records and sequence files, including language variants.

For a general procedure, `scope[2].products[1].yield_percent` means the yield
of the first product in entry 2. `must not be empty` under `scope` means you
need at least one entry. If a top-level field reports
`a general procedure lists them in scope; move <key> into its entries`, remove
that line and put the data inside the relevant entries. A time error asks for a
number followed by `min`, `h` or `d`; a temperature error asks for an unquoted
number in °C.

For a sequence, `steps[2].entry` names the scope entry selected for step 2.
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
with registry structure images where available; a plus joins the first step's
starting materials, and arrows show step number, reaction type and yield. It
runs down the page in narrow windows. Sequence pages are absent from the
procedure search index; use their links to find them.

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
`tags`, `products`, `substrates` and `scheme_image` as they are. Keep `scope`
and its entry order, translating only each entry's `note`. The check reports
differences in the shared fields as errors. Numeric yields compare by value, so
`85` and `85.0` agree. Compound names come from `name` and `name_de` in the
shared registry; add or edit `name_de` there for the German name. Translate the
title, the hazards and the body, set `date` and `lastmod` to the time of the
translation, and use the section headings and Reagents columns of the new
language, which the [procedure schema](SCHEMA.md#languages-and-variants) lists.

## 8. Write a synthesis sequence

When you use several procedures in order to make a target compound, record
that route as a **synthesis sequence**. Each step names the procedure you run
and, for a general procedure, the scope entry you use. The site checks that
the steps connect and calculates their overall yield.

Copy [templates/sequence.md](../templates/sequence.md) into the collection's
`md/sequences/`. `orgsyndb init` creates this folder. `orgsyndb new` creates
procedure stubs, so copy the sequence template by hand. Ask the owner for a
free `SEQ-NNNN` number from `0001` to `9999`. Replace `SEQ-0000` in `id` and
`seq-0000` in `slug`; save as `SEQ-NNNN-short-slug.md`. Use lowercase letters,
digits and single hyphens in the short slug. Sequences are Markdown files,
even when their steps use Org procedures.

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
steps = [{ procedure = "OSDB-0004" }, { procedure = "OSDB-0009", entry = 1 }]
+++

## Notes

The 4-acetylbiphenyl from step 1 is reduced in step 2 as entry 1 of the
general procedure.
```

You need at least two steps. Each `procedure` must name an existing procedure.
A general procedure requires `entry`, its scope entry number counted from 1.
A specific procedure forbids `entry`. Each step after the first must start
from a product of the previous step; for general procedures, use only the
chosen entry's starting materials and products. The target must be a product
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
base name, `id`, `slug`, `target` and ordered `steps`; translate the title and
notes and set the dates for that version. Both demo sequences have German
variants. The site publishes one variant per ID: the site's language first,
then an untagged file, then the other language. Run `orgsyndb validate` and
restart `orgsyndb serve` to check the sequence and its links. The
[schema reference](SCHEMA.md#synthesis-sequences) gives the exact rules.
