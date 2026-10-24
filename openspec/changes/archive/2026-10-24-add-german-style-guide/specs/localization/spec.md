## ADDED Requirements

### Requirement: German style guide and glossary
The application SHALL ship `docs/STYLE.de.md`, a style guide for the text of German procedures, and `docs/GLOSSARY.de.md`, a glossary for it. Both are written in German for native and non-native authors. English appears only in the glossary tables, as each entry's English equivalent; the running text of both documents contains no English sentences or glosses. The style guide SHALL cover at least: the instruction form of the steps in `Durchführung` and `Aufarbeitung und Reinigung`; the tense and voice of observations and of `Charakterisierung`; numbers, units and abbreviations; current spelling and nomenclature against the historical spellings of older German literature; and the established German term against the anglicism or calque. It SHALL name the twentieth-century German practical textbooks and handbooks it rests on, and cite them where a rule is drawn from them. The glossary SHALL hold at least 500 entries, counting terms, fixed phrases and reusable sentences specific to organic synthesis, grouped by topic; every entry gives its English equivalent, and every entry for a form to avoid names the form to use instead. The README lists both documents under its authoring references; `docs/AUTHORING.de.md` and `docs/AUTHORING-ORG.de.org` point to the style guide where they ask for the procedure text, and `docs/AUTHORING.md` and `docs/AUTHORING-ORG.org` point to it in their sections on writing in German, so that each German guide still covers the same rules as its English original.

#### Scenario: Style guide and glossary exist
- **WHEN** a reviewer lists `docs/` and reads the README and the four authoring guides
- **THEN** `docs/STYLE.de.md` and `docs/GLOSSARY.de.md` exist, the README links both under its authoring references, each German authoring guide links the style guide in its section on writing the procedure text, and each English authoring guide links it in its section on writing in German

#### Scenario: Style guide covers its topics and sources
- **WHEN** a reviewer reads `docs/STYLE.de.md`
- **THEN** it has a section for each topic the requirement lists, names the historical German sources it rests on with enough bibliographic detail to find them, and contains no English sentences or glosses

#### Scenario: Glossary size and shape
- **WHEN** a reviewer counts the entries of `docs/GLOSSARY.de.md`
- **THEN** there are at least 500, every entry has a German form and an English equivalent, and every entry marked as a form to avoid names its replacement
