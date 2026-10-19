+++
# How to fill in this block
# -------------------------
# Lines starting with # are notes for you; the website ignores them.
# Every other line is one piece of information: a name, an equals sign,
# then the value. Change only the part after the equals sign.
# - Text goes inside double quotes: "like this".
# - Numbers have no quotes: 85
# - A list goes inside square brackets, each entry in quotes, separated
#   by commas: ["first", "second"]
# Keep the two +++ lines exactly as they are.

# Procedure number. It is filled in for you; do not change it.
id = "OSDB-0000"

# Web address of the page. Always the procedure number in lowercase.
# It is filled in for you; do not change it.
slug = "osdb-0000"

# Name of the product, as shown in the page heading.
title = "Product Name"

# When the procedure was first written: date, the letter T, time, then
# +01:00 in winter or +02:00 in summer (German time). No quotes.
date = 2026-10-19T22:32:22+02:00

# When you last changed it, written the same way. Update it on every
# edit. It must not be earlier than date.
lastmod = 2026-10-19T22:32:22+02:00

# Everyone who wrote the procedure, as a list of names.
authors = ["A. Example"]

# Where the procedure stands: "draft" while you are writing it,
# "checked" once someone has checked it, "retired" when it should no
# longer be used.
status = "draft"

# The kind of reaction: exactly one entry. Allowed values are listed in
# site/data/reaction_types.toml, for example "esterification",
# "reduction" or "cross-coupling".
reaction_types = ["esterification"]

# Keywords for searching, at least one. Lowercase letters and digits
# only, with a hyphen instead of a space: "acid-catalysed".
tags = ["change-me"]

# How much product the procedure makes: a number, a space, a unit.
scale = "25 mmol"

# Yield in percent, a number from 0 to 100, without quotes or %.
yield_percent = 85

# The main hazards, at least one, each as a short phrase.
hazards = ["Flammable liquid"]

# Optional information. To use a line, delete the # at its start and
# change the value.

# Procedure numbers this one starts from, e.g. its starting material.
# Each must be a procedure that exists on the site.
# precursors = ["OSDB-0001"]

# Picture of the product's structure, an .svg or .png file placed in
# site/static/structures/. Write the path starting with structures/.
# structure_image = "structures/osdb-0001.svg"

# Who checked the procedure, as a list of names.
# checked_by = ["B. Example"]

# Literature references, one entry per reference.
# references = ["Example, A. J. Fictitious Chem. 2020, 1, 1."]

# Name of the AI model that helped write the procedure. Leave this line
# out entirely if no AI was involved.
# ai_model = "example-model-1"

# Details of the product. This block must stay last, just before the
# closing +++ line.
[product]
# Name of the product.
name = "Product name"
# Molecular formula, e.g. "C4H8O2".
formula = "C4H8O2"
# Molecular weight in g/mol, a number without quotes.
mw = 88.11
# Structure written as SMILES.
smiles = "CCOC(C)=O"
# Optional CAS registry number, e.g. "141-78-6". Delete the # to use it.
# cas = "141-78-6"
+++

## Summary

One or two sentences: what is made, from what, and how.

## Reagents

| Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv |
|---|---|---|---|---|---|
| Starting material | 64-19-7 | 60.05 | 1.50 g | 25.0 | 1.0 |
| Second reagent | 64-17-5 | 46.07 | 1.73 g | 37.5 | 1.5 |

## Procedure

1. First step, with amounts, temperature and time.
2. Next step.

## Workup and Purification

How the product is isolated and purified.

## Characterization

Appearance, melting or boiling point, and spectroscopic data.

## Notes

1. Practical remarks, pitfalls, or variations.

## Hazards and Waste Disposal

Specific hazards of the reagents and product, and how waste is
collected.

## References

Literature this procedure is based on, or "None."
