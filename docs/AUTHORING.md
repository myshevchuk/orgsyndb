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
numbers without quotes. Keep lists inside square brackets, with every entry
in double quotes.

Fill in these required fields:

- `id` and `slug`: leave the values supplied by `new`, or use the number the
  owner gave you.
- `title`: the product name shown at the top of the page.
- `date`: when the procedure was first written.
- `lastmod`: when the procedure was last changed. Update it after every
  later edit.
- `authors`: everyone who wrote the procedure.
- `status`: whether the procedure is a draft, checked, or retired.
- `reaction_types`: one reaction category.
- `tags`: useful lowercase search terms. Replace the template's
  `change-me`. The `sample-data` tag adds a warning banner to the page and
  to printouts, so never use it for a real procedure.
- `scale`: the amount of product made.
- `yield_percent`: the isolated yield as a number without a percent sign.
- `hazards`: short descriptions of the main hazards.
- `[product]`: the product name, formula, molecular weight, and SMILES, the
  text notation used for the product structure.

The template also contains optional, commented fields for precursor
procedures, a structure image, checkers, literature references, an AI model,
and the product's CAS number. Delete the `#` at the start of an optional line
when you need it. Leave the line commented when it does not apply.

Set `precursors` to the procedure numbers that make the starting material
for this procedure. For example:

```toml
precursors = ["OSDB-0007"]
```

The page then links to OSDB-0007 under **Precursors**. The OSDB-0007 page
automatically links back to this procedure under **Used in**.

To show a product structure, place an SVG or PNG file in
the collection's `static/structures/` and set a path such as:

```toml
structure_image = "structures/osdb-NNNN.svg"
```

For an SVG, use black lines and text on a white background rectangle. Give
the file a `<title>`, and do not include scripts, external images, or other
external references. The site shows the image on a white panel in dark mode.
Ask the owner to add or check the image if you do not work with SVG files.

Keep the `[product]` block last, immediately before the closing `+++`. TOML
treats fields after `[product]` as part of that product block.

Write `date` and `lastmod` without quotes. Use Europe/Berlin local time and
include `+01:00` in winter or `+02:00` in summer, as shown in the template.
The [procedure schema](SCHEMA.md#front-matter-fields) gives the exact format
and every allowed value.

### How the fields appear on the page

The page shows `id` and a `status` badge above the title. Its information
panel repeats the ID and shows the product name, formula, molecular weight,
CAS number when present, SMILES, scale, yield, reaction type, tags, authors,
checkers when present, created and modified times, and precursor or used-in
links. Formula digits appear as subscripts. Molecular weight gains `g/mol`,
yield gains a percent sign, and SMILES has a **Copy** button. Reaction type,
tag, and author values link to pages that list related procedures. The site
title-cases author names for display, so a name entered as `van` appears as
`Van`.

The structure image appears after the information panel. Without one, the
screen shows a **No structure image** placeholder, which is omitted from
printouts. The eight body sections follow it.

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
number in place. The owner can then place, rename, and check it.

## 5. Check the file

A validator is a program that checks the file for known mistakes. A terminal
is a window where you type commands. If you have the collection and the
OrgSynDB program, open a terminal in the collection folder and run:

```sh
orgsyndb validate
```

The command exports the owner's Org procedures and then checks every
procedure. Each problem has this form:

```text
path/to/file.md:field: error: message
path/to/file.md:field: warning: message
```

Read each line from left to right:

- The first part is the file to open.
- The second part is the field or body section to inspect.
- `error` means the procedure is invalid and the check fails.
- `warning` means the check can finish, but you should review and correct
  the problem.
- The final text explains what is wrong.

For example, a line naming `yield_percent` tells you to inspect that field
near the top of the file. A line naming `body` tells you to inspect the
section headings. Run the command again after correcting the file. The last
line reports how many files, errors, and warnings were found.

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

On a procedure page, choose **Print / Save as PDF** to open the browser's
print dialog. The print layout is A4, complete, and black on white. Firefox
does not add the running header and page numbers that the owner's
WeasyPrint-generated PDFs contain.

The preview does not update while it is running. After an edit, stop it and
run `orgsyndb serve` again.
