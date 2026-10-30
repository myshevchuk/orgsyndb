+++
# How to fill in this block
# -------------------------
# This file describes one synthesis sequence: procedures run one after
# the other, the product of each the starting material of the next. It
# lives in the collection's md/sequences/ folder, named after its number
# and a short name, e.g. SEQ-0001-aspirin-from-wintergreen.md. A German
# version of the same sequence is a copy named with .de before .md.
#
# Lines starting with # are notes for you; the website ignores them.
# Every other line is one piece of information: a name, an equals sign,
# then the value. Change only the part after the equals sign.
# - Text goes inside double quotes: "like this".
# - Numbers have no quotes: 2
# Keep the two +++ lines exactly as they are.

# id: the sequence number, SEQ- and four digits, e.g. "SEQ-0001". Use
# the next number not yet taken in md/sequences/. It must match the
# start of the file name.
id = "SEQ-0000"

# slug: the web address of the page. Always the id in lowercase, e.g.
# "seq-0001".
slug = "seq-0000"

# title: the name of the sequence, as shown in the page heading.
title = "Aspirin from oil of wintergreen"

# date: when the sequence was first written: date, the letter T, time,
# then +01:00 in winter or +02:00 in summer (German time). No quotes.
date = 2026-10-23T09:15:00+02:00

# lastmod: when you last changed it, written the same way. It must not
# be earlier than date.
lastmod = 2026-10-23T09:15:00+02:00

# target: the compound the sequence makes, as its key in the compounds/
# folder, e.g. "acetylsalicylic-acid". It must be a product of the last
# step.
target = "acetylsalicylic-acid"

# steps: the procedures in the order they are run, at least two. Each
# step is { procedure = "OSDB-NNNN" }, the procedure's number; each step
# must start from a product of the step before it.
# For a general procedure, one with a scope table, add entry, the number
# of the scope entry the step runs, counted from 1:
# { procedure = "OSDB-0009", entry = 1 }. A specific procedure takes no
# entry.
steps = [{ procedure = "OSDB-0001" }, { procedure = "OSDB-0002" }]
+++

## Notes

What to watch between the steps, e.g. which intermediate is purified or
dried before it is carried on.
