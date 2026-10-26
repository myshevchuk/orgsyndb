# Schema-Referenz für Vorschriften

Diese Referenz legt fest, was eine gültige OrgSynDB-Vorschrift ist. Schlagen
Sie hier die genaue Schreibweise, den Typ und die Regel eines Feldes nach,
oder die Bedeutung einer Meldung von `tools/validate.py` oder dem Befehl
`orgsyndb export`. Die englische Fassung ist [SCHEMA.md](SCHEMA.md); bei
Abweichungen gilt sie.

Feldnamen, Org-Schlüsselwörter, Statuswerte, Reaktionstyp-Kürzel,
Schlagwörter sowie die Meldungen des Validators und des Org-Exports sind in
jeder Sprache englisch. Deutsch sind die Texte einer deutschen Vorschrift,
ihre Abschnittsüberschriften und die Spalten ihrer Reagenzientabelle, und
auf einer deutschen Website die Oberfläche.

Eine Markdown-Vorschrift beginnt mit einem TOML-Datenblock (*Front
Matter*), der zwischen einer öffnenden und einer schließenden `+++`-Zeile
steht. Die öffnende `+++`-Zeile muss die erste Zeile der Datei sein. Der
Text nach der schließenden `+++`-Zeile ist der Inhalt der Vorschrift.

In den Tabellen unten ist ein **String** Text in doppelten
Anführungszeichen, ein **String-Array** eine durch Kommas getrennte Liste in
eckigen Klammern und eine **Tabelle** eine Gruppe, die mit einer Überschrift
wie `[product]` beginnt. Ein **Datum mit Zeitzonenversatz** ist ein Datum
mit Uhrzeit und UTC-Versatz ohne Anführungszeichen, etwa
`2026-10-19T17:42:05+02:00`.

## Nummern, Dateinamen und URLs

Die Vorschriftennummer hat genau die Form `OSDB-NNNN`, wobei `NNNN` vier
Ziffern von `0001` bis `9999` sind. `OSDB-0001` ist also gültig.
`OSDB-0000` ist den Vorlagen vorbehalten und keine gültige Nummer.
Eine Nummer muss in allen Inhaltsverzeichnissen, die der Validator prüft,
eindeutig sein; nur die Fassungen einer Vorschrift in verschiedenen
Sprachen teilen sich eine Nummer, siehe
[Sprachen und Fassungen](#sprachen-und-fassungen).

Der Dateiname hat diese Form:

```text
OSDB-NNNN-kurzer-slug.md
OSDB-NNNN-kurzer-slug.org
OSDB-NNNN-kurzer-slug.de.md     (deutsche Fassung)
OSDB-NNNN-kurzer-slug.en.org    (englische Fassung)
```

Das Präfix `OSDB-NNNN` muss gleich der `id` der Vorschrift sein. Der kurze
Slug nach dem Präfix besteht aus Kleinbuchstaben oder Ziffern, mit einzelnen
Bindestrichen zwischen den Gruppen, wie in `OSDB-0001-ethyl-acetate.md`.
Vor der Endung darf ein Sprachkürzel stehen, `.de` oder `.en`; jedes andere
Kürzel ist ein Fehler.

Der `slug` im Datenblock ist nicht der kurze Slug des Dateinamens. Er ist
immer die Nummer in Kleinbuchstaben: aus `OSDB-0001` wird `osdb-0001`. Die
Seite erhält so die URL `/procedures/osdb-0001/`. Fügen Sie kein Feld `url`
hinzu; die URL ergibt sich aus `slug`.

Der Validator prüft Vorschriftendateien nur auf der obersten Ebene jedes
Verzeichnisses. Ein Unterverzeichnis ist ein Fehler. Versteckte Dateien und
`_index.md` überspringt er stillschweigend. Jede andere Datei mit falscher
Endung ergibt eine Warnung und wird übergangen.

## Felder des Datenblocks

Jedes Pflichtfeld muss vorhanden sein. Ein Pflicht-String muss Text
enthalten, der nicht nur aus Leerraum besteht. Ein als nicht leer
beschriebenes Pflicht-Array muss mindestens einen Eintrag haben, und jeder
Eintrag muss Text enthalten.

### Pflichtfelder

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `id` | Die Vorschriftennummer. | String | Ja | Muss `OSDB-0001` bis `OSDB-9999` sein und in den geprüften Verzeichnissen eindeutig, außer unter den Fassungen einer Vorschrift. | `id = "OSDB-0001"` |
| `slug` | Der Wert in der URL der Vorschrift. | String | Ja | Muss genau die `id` in Kleinbuchstaben sein. | `slug = "osdb-0001"` |
| `title` | Der Produktname in der Seitenüberschrift. | Nicht leerer String | Ja | Darf nicht leer sein. | `title = "Produktname"` |
| `date` | Wann die Vorschrift angelegt wurde. | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen. Der Versatz sollte der zu diesem Zeitpunkt geltende von Europe/Berlin sein. | `date = 2026-10-19T17:42:05+02:00` |
| `lastmod` | Wann die Vorschrift zuletzt geändert wurde. | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen, nicht früher als `date`, mit dem zu diesem Zeitpunkt geltenden Versatz von Europe/Berlin. | `lastmod = 2026-10-19T17:42:05+02:00` |
| `authors` | Alle, die die Vorschrift geschrieben haben. | Nicht leeres Array nicht leerer Strings | Ja | Mindestens ein Name. | `authors = ["A. Example"]` |
| `status` | Der Bearbeitungsstand. | String | Ja | Genau `draft`, `checked` oder `retired`. Eine deutsche Website zeigt *Entwurf*, *geprüft* oder *zurückgezogen*. | `status = "draft"` |
| `reaction_types` | Die festgelegte Reaktionsklasse. | String-Array | Ja | Genau ein Kürzel aus dem Reaktionstyp-Vokabular. | `reaction_types = ["esterification"]` |
| `tags` | Suchbegriffe. | Nicht leeres String-Array | Ja | Jedes Schlagwort besteht aus Kleinbuchstaben oder Ziffern mit einzelnen Bindestrichen zwischen den Gruppen. | `tags = ["acid-catalysed"]` |
| `product` | Angaben zum Produkt. | Tabelle | Ja | Muss alle unten beschriebenen Pflichtfelder des Produkts enthalten. | `[product]` |
| `scale` | Wie viel Produkt die Vorschrift liefert. | String | Ja | Eine Zahl, Leerraum und eine Einheit. Die Zahl darf einen Dezimalpunkt oder ein Dezimalkomma haben. Die Einheiten sind nicht festgelegt. | `scale = "2,5 mmol"` |
| `yield_percent` | Isolierte Ausbeute in Prozent. | Ganz- oder Gleitkommazahl | Ja | Endlich und von 0 bis 100 einschließlich. Ohne Anführungszeichen und ohne `%`, mit Dezimalpunkt. Ein Wahrheitswert ist keine Zahl. | `yield_percent = 85` |
| `hazards` | Die wichtigsten Gefahren. | Nicht leeres Array nicht leerer Strings | Ja | Mindestens eine kurze Beschreibung. | `hazards = ["Entzündbare Flüssigkeit"]` |

Ein Datum mit anderem Versatz als dem Berliner bezeichnet trotzdem einen
genauen Zeitpunkt und ergibt deshalb nur eine Warnung. Ein Datum in
Anführungszeichen, ein Datum ohne Versatz oder ein bloßes Datum ist ein
Fehler. Der Validator vergleicht `date` und `lastmod` als Zeitpunkte,
einschließlich ihres Versatzes.

### Felder des Produkts

Die Tabelle `[product]` ist Pflicht. Schreiben Sie sie in handgeschriebenem
TOML als letzte, direkt vor das schließende `+++`: TOML rechnet alle
folgenden Felder zu dieser Tabelle.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `product.name` | Der Produktname. | Nicht leerer String | Ja | Darf nicht leer sein. | `name = "Produktname"` |
| `product.formula` | Die Summenformel. | Nicht leerer String | Ja | Darf nicht leer sein. | `formula = "C4H8O2"` |
| `product.mw` | Molmasse in g/mol. | Ganz- oder Gleitkommazahl | Ja | Endlich und größer als null. Ohne Anführungszeichen, mit Dezimalpunkt. Ein Wahrheitswert ist keine Zahl. | `mw = 88.11` |
| `product.smiles` | Die Struktur des Produkts als SMILES. | Nicht leerer String | Ja | Darf nicht leer sein. | `smiles = "CCOC(C)=O"` |
| `product.cas` | Die CAS-Nummer. | String | Nein | 2 bis 7 Ziffern, Bindestrich, 2 Ziffern, Bindestrich und die Prüfziffer. Die Prüfziffer muss stimmen. | `cas = "141-78-6"` |

Eine vollständige Produkttabelle sieht so aus:

```toml
[product]
name = "Produktname"
formula = "C4H8O2"
mw = 88.11
smiles = "CCOC(C)=O"
cas = "141-78-6"
```

Der Validator prüft, dass `formula` und `smiles` nicht leere Strings sind.
Er prüft weder die Schreibweise der Summenformel noch die Gültigkeit des
SMILES, noch ob die Molmasse zur Summenformel passt.

### Optionale Felder

Lassen Sie ein optionales Feld weg, wenn es nicht zutrifft.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `precursors` | Vorschriften, von denen diese ausgeht. | String-Array | Nein | Jeder Eintrag muss eine gültige Vorschriftennummer sein, in einem der geprüften Verzeichnisse vorkommen, in welcher Sprache auch immer, und darf nicht die eigene Nummer sein. | `precursors = ["OSDB-0001"]` |
| `structure_image` | Das Strukturbild im Verzeichnis für statische Dateien. | String | Nein | Ein relativer Pfad unter `structures/` ohne `..`, mit der Endung `.svg` oder `.png`, der auf eine vorhandene Datei zeigt. | `structure_image = "structures/osdb-0001.svg"` |
| `checked_by` | Wer die Vorschrift geprüft hat. | Array nicht leerer Strings | Nein | Das Array darf leer sein, ein Eintrag aber nicht. | `checked_by = ["B. Example"]` |
| `references` | Literaturangaben als Metadaten. | Array nicht leerer Strings | Nein | Das Array darf leer sein, ein Eintrag aber nicht. | `references = ["Example, A. J. Fictitious Chem. 2020, 1, 1."]` |
| `ai_model` | Das KI-Modell, das beim Schreiben geholfen hat. | Nicht leerer String | Nein | Weglassen, wenn keine KI beteiligt war. Der Wert `"none"` ist ein Fehler. | `ai_model = "example-model-1"` |
| `language` | Die Sprache, in der die Vorschrift geschrieben ist. | String | Nein | `de` oder `en`; trägt der Dateiname ein Sprachkürzel, muss es dieselbe Sprache sein. | `language = "de"` |

Das Argument `--static-dir` bestimmt, wo der Validator ein
`structure_image` sucht. Ohne das Argument nimmt er `static` im aktuellen
Verzeichnis; das passt, wenn er im Hauptordner einer Sammlung läuft.
`orgsyndb validate` übergibt immer das `static/` der Sammlung.

## Geduldete, abgelehnte und unbekannte Felder

Die folgenden Hugo- oder Export-Metadaten gehören nicht zum Schema, werden
aber stillschweigend akzeptiert, wenn sie den angegebenen Typ haben.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `draft` | Hugo-Veröffentlichungsangabe, die ein Exporter schreiben kann. | Wahrheitswert | Nein | Nur `false` ist erlaubt. | `draft = false` |
| `description` | Geduldete Hugo-Seitenangabe. | String | Nein | Jeder String ist erlaubt. | `description = ""` |
| `aliases` | Geduldete Hugo-Seitenangabe. | String-Array | Nein | Jeder Eintrag muss ein String sein. | `aliases = []` |
| `weight` | Geduldete Hugo-Seitenangabe. | Ganzzahl | Nein | Eine Ganzzahl, kein Wahrheitswert. | `weight = 1` |

Diese Felder werden abgelehnt:

| Feld oder Wert | Warum abgelehnt | Stattdessen |
|---|---|---|
| `draft = true` | Der Bearbeitungsstand gehört ins Schema, und ein echter Hugo-Entwurf wird nicht veröffentlicht. | `status = "draft"` und `draft` weglassen, oder `draft = false` behalten, wenn ein Exporter es schreibt. |
| `author = ["A. Example"]` | Das Schema verwendet die Mehrzahl. | `authors = ["A. Example"]` |
| `url = "/procedures/osdb-0001/"` | Die URL ergibt sich aus `slug`. | `slug = "osdb-0001"` |

Jedes andere Feld der obersten Ebene ergibt die Warnung `unknown field`,
auch Tippfehler wie `checkedby`. Ein unbekanntes Feld in `[product]` ergibt
ebenfalls eine Warnung, unter seinem Namen mit Punkt, etwa
`product.colour`.

## Org-Schlüsselwörter auf Dateiebene

`orgsyndb export` prüft, dass eine Org-Vorschrift jedes dieser
Schlüsselwörter genau einmal enthält. Groß- und Kleinschreibung der Namen
spielt keine Rolle.

| Org-Schlüsselwort | Wert | Exportierter Datenblock |
|---|---|---|
| `#+CREATED` | Ein inaktiver Zeitstempel genau in der Form `[YYYY-MM-DD Day hh:mm:ss]`. | `date`, mit demselben Ortsdatum und derselben Ortszeit und dem zu diesem Zeitpunkt geltenden Versatz von Europe/Berlin. |
| `#+LAST_MODIFIED` | Ein inaktiver Zeitstempel genau in der Form `[YYYY-MM-DD Day hh:mm:ss]`. | `lastmod`, ebenso. |
| `#+AI_MODEL` | `none` für eine von Menschen geschriebene Datei oder eine Modellkennung, die `[A-Za-z0-9][A-Za-z0-9._:/@+-]*` entspricht. | Kein Feld `ai_model` bei `none`, sonst ein String `ai_model` mit dem Wert des Schlüsselworts. |

Zum Beispiel:

```org
#+CREATED: [2026-10-19 Mon 17:42:05]
#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]
#+AI_MODEL: none
```

`Day` muss der richtige englische Wochentag mit drei Buchstaben sein, von
`Mon` bis `Sun`, auch in einer deutschen Vorschrift. Der Zeitstempel ist
Berliner Ortszeit und hat keinen Versatz. Datum und Uhrzeit müssen
existieren, auch bei der Zeitumstellung: Eine Uhrzeit, die die Umstellung im
Frühjahr überspringt, ist ungültig.

`#+LAST_MODIFIED` darf nicht vor `#+CREATED` liegen. In der wiederholten
Stunde der Umstellung im Herbst kann eine Ortszeit zwei Zeitpunkte
bezeichnen. Die Org-Prüfung akzeptiert die Zeitstempel, wenn eine Wahl der
beiden Berliner Versätze sie in die richtige Reihenfolge bringt. Maßgeblich
ist die Prüfung des exportierten Datenblocks, weil `date` und `lastmod` dort
einen ausdrücklichen Versatz haben.

Die Org-Vorlage bildet außerdem `#+TITLE` auf `title`, `#+HUGO_SLUG` auf
`slug` und `#+HUGO_TAGS` auf `tags` ab. Wiederholte
`#+HUGO_CUSTOM_FRONT_MATTER`-Zeilen liefern die übrigen Felder. Der Export
darf kein Feld `author` enthalten.

Eine Org-Quelle darf `date`, `lastmod`, `ai_model` oder den Dateinamen des
Exports nicht über eine andere von ox-hugo gelesene Angabe setzen.
`orgsyndb export` weist die Schlüsselwörter `#+DATE`, `#+HUGO_LASTMOD`,
`#+HUGO_AUTO_SET_LASTMOD`, `#+HUGO_FRONT_MATTER_KEY_REPLACE`,
`#+EXPORT_FILE_NAME`, `#+HUGO_BASE_DIR`, `#+HUGO_BASE_CONTENT_FOLDER`,
`#+HUGO_SECTION`, `#+HUGO_BUNDLE`, `#+SETUPFILE` und `#+INCLUDE` zurück;
ebenso die Schlüssel `:date`, `:lastmod` und `:ai_model` in
`#+HUGO_CUSTOM_FRONT_MATTER`, `#+PROPERTY`- oder Schubladeneigenschaften
namens `EXPORT_*` oder `LOG_INTO_DRAWER`, eine `:LOGBOOK:`-Schublade
sowie das Kopfargument `:front_matter_extra` eines Quelltextblocks.
Zeilen in `#+begin_`-...-`#+end_`-Blöcken werden ignoriert. Die allgemeine
Fehlermeldung lautet `must not be used; the export sets date, lastmod,
ai_model and the export file name itself`. Bei `#+PROPERTY` lautet sie
`must not set <NAME>; the export sets date, lastmod, ai_model and the export
file name itself`. Die Fehler für `#+HUGO_CUSTOM_FRONT_MATTER` lauten `must
not set :date; the export writes it from #+CREATED`, `must not set
:lastmod; the export writes it from #+LAST_MODIFIED` und `must not set
:ai_model; the export writes it from #+AI_MODEL`.

## Reaktionstypen

`reaction_types` enthält genau ein Kürzel aus dieser Tabelle. Das Kürzel
ist der Wert im Datenblock, in jeder Sprache. Die Bezeichnungen sind die
Namen, die eine englische und eine deutsche Website zeigen.

| Kürzel | Englisch | Deutsch |
|---|---|---|
| `acylation` | Acylation | Acylierung |
| `aldol-condensation` | Aldol condensation | Aldolkondensation |
| `alkylation` | Alkylation | Alkylierung |
| `amide-coupling` | Amide coupling | Amidkupplung |
| `cross-coupling` | Cross-coupling | Kreuzkupplung |
| `cycloaddition` | Cycloaddition | Cycloaddition |
| `deprotection` | Deprotection | Entschützung |
| `esterification` | Esterification | Veresterung |
| `hydrolysis` | Hydrolysis | Hydrolyse |
| `nucleophilic-substitution` | Nucleophilic substitution | Nucleophile Substitution |
| `olefination` | Olefination | Olefinierung |
| `oxidation` | Oxidation | Oxidation |
| `protection` | Protection | Schützung |
| `reduction` | Reduction | Reduktion |
| `reductive-amination` | Reductive amination | Reduktive Aminierung |

Das Vokabular steht in `site/data/reaction_types.toml`. Jeder Eintrag ist
ein Kürzel aus Kleinbuchstaben und Bindestrichen, dessen Tabelle ein nicht
leeres `label` und ein nicht leeres `label_de` enthält. Fehlt `label_de`,
zeigt eine deutsche Website `label`; ein leeres `label_de` lehnt der
Validator ab.

## Abschnitte des Textes

Jede Vorschrift auf Deutsch hat diese acht Abschnitte in dieser
Reihenfolge:

1. Zusammenfassung
2. Reagenzien
3. Durchführung
4. Aufarbeitung und Reinigung
5. Charakterisierung
6. Anmerkungen
7. Gefahren und Entsorgung
8. Literatur

Eine englische Vorschrift verwendet stattdessen Summary, Reagents,
Procedure, Workup and Purification, Characterization, Notes, Hazards and
Waste Disposal und References. Welche Namen gelten, bestimmt das
Sprachkürzel im Dateinamen, sonst das Feld `language`. Eine Datei ohne
beides wird mit dem Satz verglichen, zu dem ihre Überschriften besser
passen; sie darf also beide verwenden.

In Markdown sind das Überschriften der zweiten Ebene wie
`## Zusammenfassung`, in Org Überschriften der obersten Ebene wie
`* Zusammenfassung`. Ein fehlender Markdown-Abschnitt oder eine falsche
Reihenfolge ergibt eine Warnung, keinen Fehler. `orgsyndb validate` wendet
diese Prüfung auf das aus einer Org-Vorschrift exportierte Markdown an.
`tools/validate.py` liest Org-Quellen nicht direkt.

Der Vergleich in Markdown ignoriert Groß- und Kleinschreibung sowie Leerraum
am Rand oder mehrfachen Leerraum. Er akzeptiert auch ein exportiertes
Attribut am Ende wie `## Zusammenfassung {#zusammenfassung}` und eine
schließende `#`-Folge. Eine Überschrift in einem umzäunten Codeblock zählt
nicht. Weitere Überschriften der zweiten Ebene und Überschriften anderer
Ebenen sind erlaubt.

## Sprachen und Fassungen

Der Dateiname einer Vorschrift darf vor der Endung ein Sprachkürzel
tragen, `.de` oder `.en`. Jedes andere Kürzel ist ein Fehler. Eine Datei
ohne Kürzel darf in jeder der beiden Sprachen geschrieben sein. Dateien
mit derselben Nummer sind *Fassungen* einer Vorschrift, zum Beispiel
`OSDB-0001-salicylic-acid.org` und ihre deutsche Übersetzung
`OSDB-0001-salicylic-acid.de.org`. Org und Markdown dürfen gemischt
werden. Unter einer Nummer darf jedes Kürzel, und das Fehlen eines
Kürzels, einmal vorkommen.

Die Website hat eine Sprache, festgelegt durch `locale` in der Datei
`site/hugo.toml` der Anwendung (voreingestellt `"de"`). Jede Vorschrift
wird genau einmal veröffentlicht, in der Fassung, die zu dieser Sprache
passt: die Datei mit diesem Kürzel, sonst die Datei ohne Kürzel, sonst
eine Datei mit dem Kürzel der anderen Sprache. Eine Vorstufe darf jede
Vorschrift sein, in welcher Sprache ihre Fassungen auch sind.

Die Fassungen einer Vorschrift

- haben denselben Grundnamen, den Dateinamen ohne Kürzel und Endung;
- haben dieselbe `id` und denselben `slug`;
- haben denselben Wert, oder dasselbe Fehlen, von `status`,
  `reaction_types`, `tags`, `yield_percent`, `precursors`,
  `structure_image` sowie `formula`, `mw`, `smiles` und `cas` in
  `[product]`;
- dürfen sich in allen übrigen Feldern und im Text unterscheiden: `title`,
  `product.name`, `scale`, `hazards`, `references`, `authors`,
  `checked_by`, `ai_model`, `language`, `date` und `lastmod`.

Der Validator vergleicht jede Fassung mit einer Bezugsfassung: der Datei
ohne Kürzel, sonst der `.de`-Datei. Jede Abweichung ist ein Fehler an der
anderen Fassung, der die Bezugsfassung nennt, zum Beispiel:

```text
md/procedures/OSDB-0002-aspirin.de.md:yield_percent: error: must equal the value in md/procedures/OSDB-0002-aspirin.md (75); the variants of a procedure share it
```

Das optionale Feld `language` gibt die Sprache einer Vorschrift an,
`"de"` oder `"en"`. Trägt der Dateiname ein Kürzel, muss das Feld dieselbe
Sprache nennen; einer Datei mit Kürzel, der das Feld fehlt, fügt der Build
es hinzu. Bei einer Datei ohne Kürzel bestimmt es, welche
Abschnittsnamen gelten. Ist die veröffentlichte Fassung in einer anderen
Sprache als die Website, kennzeichnet ihre Seite die Vorschrift mit einem
`lang`-Attribut.

Die Reagenzientabelle einer deutschen Vorschrift hat die Spalten
**Reagenz**, **CAS**, **M (g/mol)**, **Menge**, **mmol** und **Äquiv.**;
ein Katalysator hat `kat.` in **mmol** und **Äquiv.** Deutscher Text
schreibt Dezimalkommas. Zahlen im Datenblock wie `yield_percent` und
`product.mw` bleiben in jeder Sprache TOML-Zahlen mit Dezimalpunkt; eine
deutsche Website zeigt sie mit Komma.

## Meldungen des Validators lesen

Starten Sie den Validator mit mindestens einem Markdown-Verzeichnis:

```text
tools/validate.py [--vocabulary FILE] [--static-dir DIR] CONTENT_ROOT...
```

Jedes `CONTENT_ROOT` ist ein Verzeichnis mit Markdown-Vorschriften.
Ohne Angabe ist `--vocabulary` die Datei `site/data/reaction_types.toml` der
Anwendung, ausgehend vom Ort des Skripts und nicht vom aktuellen
Verzeichnis, und `--static-dir` ist `static` im aktuellen Verzeichnis.

Jedes Problem ist eine Zeile auf der Standardausgabe:

```text
<pfad>:<feld>: <schwere>: <meldung>
```

Das Feld ist meist ein Feld des Datenblocks. Felder des Produkts haben
Namen mit Punkt wie `product.mw`. Weitere mögliche Felder sind `file_name`,
`front_matter` und `body`. Die Meldungen sind englisch.

`orgsyndb export` schreibt Probleme der Org-Quellen in derselben Zeilenform
auf die Standardausgabe. Seine Felder können auch Org-Schlüsselwörter wie
`#+CREATED`, Eigenschaften wie `#+PROPERTY` oder `:EXPORT_DATE:` und
Schubladen wie `:LOGBOOK:` sein.

Ein `error` bedeutet, dass die Vorschrift ungültig ist. Eine `warning`
bezeichnet ein Problem, das die Prüfung nicht scheitern lässt, etwa einen
fehlenden Abschnitt oder ein unbekanntes Feld. Nach den Problemzeilen
schreibt der Validator eine Zusammenfassung auf die Standardfehlerausgabe:

```text
validated 1 files: 1 errors, 0 warnings
```

Die ersten beiden Zeilen sind echte Ausgaben des Validators. Die letzte
Zeile erzeugt `orgsyndb export` in derselben Form für eine Org-Quelle:

```text
tests/fixtures/invalid/yield-out-of-range/OSDB-0110-yield-out-of-range.md:yield_percent: error: 104.5 must be between 0 and 100
tests/fixtures/warn/missing-section/OSDB-0151-missing-section.md:body: warning: missing section "Notes"
tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)
```

Der Rückgabewert sagt einem aufrufenden Befehl, ob die Prüfung gelungen ist:

| Rückgabewert | Bedeutung |
|---|---|
| `0` | Kein Fehler gefunden. Warnungen können ausgegeben worden sein. |
| `1` | Mindestens ein Fehler in einer Vorschrift. |
| `2` | Aufruf oder Konfiguration des Validators ist ungültig, etwa kein Verzeichnis, ein Verzeichnis, das keines ist, oder eine fehlende oder fehlerhafte Vokabulardatei. |

Aufruf- und Konfigurationsfehler gehen auf die Standardfehlerausgabe und
enthalten `validate.py: error:`. Der Validator unterdrückt Prüfungen, die
von einem fehlenden oder fehlerhaften Wert abhängen, sodass ein Fehler
meist keine Kette von Folgemeldungen auslöst.
