## Why

German procedures can now be written and validated, but nothing says
how their text should read. Authors who learned their laboratory German
from English papers produce calques such as *Esterifizierung* for
*Veresterung*, *refluxieren* for *unter Rückfluss erhitzen* or *quenchen*
for *hydrolysieren* or *zersetzen*, and mix instruction forms (*lösen
lassen*, *wird gelöst*, *lösen Sie*) within one procedure. Native
speakers who grew up with the German practical textbooks know the
established forms; non-native authors, and native ones trained mainly on
English literature, often do not, and no document in the repository
records them.

## What Changes

- **Style guide.** A new `docs/STYLE.de.md`, written in German for
  native and non-native authors alike, without English glosses: English
  appears only as the English equivalents in the glossary tables. It sets the instruction form of the working
  sections, the tense and voice of observations and characterisation,
  numbers, units and abbreviations, current spelling against the
  historical spellings an author meets in older literature, and the
  established German term against the anglicism. It states the German
  practical textbooks and handbooks of the twentieth century its rules
  rest on, and cites them where a rule is drawn from them.
- **Glossary.** A new `docs/GLOSSARY.de.md` of at least 500 entries:
  terms, fixed phrases and reusable sentences specific to organic
  synthesis, each with its English equivalent, grouped by topic. Entries
  for a form to avoid (an anglicism, a calque, an outdated spelling) name
  the form to use instead.
- **Links.** The README lists both under its authoring references; the
  German Markdown and Org authoring guides point to the style guide where
  they ask for the procedure text, and the English guides point to it in
  their sections on writing in German, so the German and English guides
  keep covering the same rules.

The rules are derived from the historical German sources, not from the
demo collection's German variants, so that the guide does not codify
the demo's own habits. Where the demo or the templates disagree with the
guide, that is reported and left to a change of its own.

## Capabilities

### Modified Capabilities

- `localization`: the German authoring documentation gains the style
  guide and the glossary.

## Impact

- Docs: new `docs/STYLE.de.md` and `docs/GLOSSARY.de.md`; links in
  `README.md` and the four authoring guides.
- Code, site, templates, demo collection and tests: unchanged. The
  validator does not check procedure prose against the guide.
- Dependencies: none.
