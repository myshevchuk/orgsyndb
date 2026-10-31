# Schema-Referenz für Vorschriften

Diese Referenz legt fest, was gültige OrgSynDB-Vorschriften,
Verbindungseinträge und Synthesewege sind. Schlagen
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
Synthesewege verwenden dieselben Begrenzungszeilen; ihr Text enthält
Anmerkungen.

In den Tabellen unten ist ein **String** Text in doppelten
Anführungszeichen, ein **String-Array** eine durch Kommas getrennte Liste in
eckigen Klammern und eine **Tabelle** eine Gruppe benannter Werte in
geschweiften Klammern oder unter einer Tabellenüberschrift. Ein **Datum
mit Zeitzonenversatz** ist ein Datum mit Uhrzeit und UTC-Versatz ohne
Anführungszeichen, etwa
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
beschriebenes Pflicht-Array muss mindestens einen Eintrag haben. Jeder
Eintrag in einem String-Array muss Text enthalten, der nicht nur aus
Leerraum besteht.

Eine Vorschrift mit `scope` ist eine **allgemeine Vorschrift**: eine Methode
für mehrere Substrate. Ohne `scope` ist sie eine **Einzelvorschrift**. Die
Website leitet die Art aus `scope` ab; legen Sie kein Feld `kind` an.

### Pflichtfelder

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `id` | Die Vorschriftennummer. | String | Ja | Muss `OSDB-0001` bis `OSDB-9999` sein und in den geprüften Verzeichnissen eindeutig, außer unter den Fassungen einer Vorschrift. | `id = "OSDB-0001"` |
| `slug` | Der Wert in der URL der Vorschrift. | String | Ja | Muss genau die `id` in Kleinbuchstaben sein. | `slug = "osdb-0001"` |
| `title` | Die Überschrift der Vorschrift, meist der Name des Produkts. | Nicht leerer String | Ja | Darf nicht leer sein. | `title = "Produktname"` |
| `date` | Wann die Vorschrift angelegt wurde. | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen. Der Versatz sollte der zu diesem Zeitpunkt geltende von Europe/Berlin sein. | `date = 2026-10-19T17:42:05+02:00` |
| `lastmod` | Wann die Vorschrift zuletzt geändert wurde. | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen, nicht früher als `date`, mit dem zu diesem Zeitpunkt geltenden Versatz von Europe/Berlin. | `lastmod = 2026-10-19T17:42:05+02:00` |
| `authors` | Alle, die die Vorschrift geschrieben haben. | Nicht leeres Array nicht leerer Strings | Ja | Mindestens ein Name. | `authors = ["A. Example"]` |
| `status` | Der Bearbeitungsstand. | String | Ja | Genau `draft`, `checked` oder `retired`. Eine deutsche Website zeigt *Entwurf*, *geprüft* oder *zurückgezogen*. | `status = "draft"` |
| `reaction_types` | Die festgelegte Reaktionsklasse. | String-Array | Ja | Genau ein Kürzel aus dem Reaktionstyp-Vokabular. | `reaction_types = ["esterification"]` |
| `tags` | Suchbegriffe. | Nicht leeres String-Array | Ja | Jedes Schlagwort besteht aus Kleinbuchstaben oder Ziffern mit einzelnen Bindestrichen zwischen den Gruppen. | `tags = ["acid-catalysed"]` |
| `products` | Die hergestellten Verbindungen mit ihren Ausbeuten. | Nicht leeres Array von Tabellen | Nur ohne `scope` | Jeder Eintrag enthält `compound` und `yield_percent`, wie unten beschrieben. | `products = [{ compound = "ethyl-acetate", yield_percent = 85 }]` |
| `scale` | Wie viel Produkt die Vorschrift liefert; bei einer allgemeinen Vorschrift die typische Ansatzgröße. | String | Ja | Eine Zahl, Leerraum und eine Einheit. Die Zahl darf einen Dezimalpunkt oder ein Dezimalkomma haben. Die Einheiten sind nicht festgelegt. | `scale = "2,5 mmol"` |
| `hazards` | Die wichtigsten Gefahren. | Nicht leeres Array nicht leerer Strings | Ja | Mindestens eine kurze Beschreibung. | `hazards = ["Entzündbare Flüssigkeit"]` |

Ein Datum mit anderem Versatz als dem Berliner bezeichnet trotzdem einen
genauen Zeitpunkt und ergibt deshalb nur eine Warnung. Ein Datum in
Anführungszeichen, ein Datum ohne Versatz oder ein bloßes Datum ist ein
Fehler. Der Validator vergleicht `date` und `lastmod` als Zeitpunkte,
einschließlich ihres Versatzes.

### Produkte und Ausgangsstoffe

Bei einer Einzelvorschrift enthält `products` auf oberster Ebene eine Tabelle
pro Produkt. Jeder Verbindungsschlüssel darf im Array nur einmal vorkommen.
Eine Vorschrift darf mehrere Produkte haben, jedes mit einer eigenen Ausbeute.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `products[n].compound` | Der Schlüssel des Produkts im Verbindungsregister. | String | Ja | Muss einen vorhandenen Registereintrag benennen. | `compound = "ethyl-acetate"` |
| `products[n].yield_percent` | Isolierte Ausbeute dieses Produkts in Prozent. | Ganz- oder Gleitkommazahl | Ja | Endlich und von 0 bis 100 einschließlich. Ohne Anführungszeichen und ohne `%`, mit Dezimalpunkt. Ein Wahrheitswert ist keine Zahl. | `yield_percent = 85` |

Schreiben Sie die Einträge wie in der Vorschriftenvorlage direkt in
geschweifte Klammern:

```toml
products = [{ compound = "ethyl-acetate", yield_percent = 85 }]
```

Sie dürfen auch TOML-Tabellenüberschriften `[[products]]` verwenden, wie der
Org-Export. Diese Tabellen stehen nach allen Feldern der obersten Ebene:
Felder nach einer Tabellenüberschrift gehören zu dieser Tabelle.

Bei einer Einzelvorschrift benennt das optionale Array `substrates` die
Ausgangsstoffe durch ihre Verbindungsschlüssel. Es darf leer sein. Jeder
Schlüssel muss im Register vorkommen, darf nur einmal genannt werden und darf
nicht auch unter den Produkten stehen.

Die Website leitet **Vorstufen** aus den anderen veröffentlichten Vorschriften
ab, die einen dieser Ausgangsstoffe herstellen. Unter **Verwendet in** stehen
Vorschriften, die eines der Produkte dieser Vorschrift als Ausgangsstoff
verwenden. Beide Listen sind nach Vorschriftennummer geordnet und funktionieren
über Sprachgrenzen hinweg. Sie tragen dafür keine Vorschriftennummern ein. Bei
einer allgemeinen Vorschrift berücksichtigt die Website alle Produkte und
Ausgangsstoffe aller Einträge, jede Verbindung einmal in der Reihenfolge ihres
ersten Auftretens. Das gilt auch für Datenfeld, Verbindungsverzeichnis,
Katalogdetails und Suche einschließlich SMILES-Treffern.

Das Datenfeld ergänzt nach **Verwendet in** die **Synthesewege**, in denen
diese Vorschrift eine Stufe ist. Es verlinkt deren Titel, nach Nummer geordnet.

### Allgemeine Vorschriften und Einträge in scope

Mit `scope` erfassen Sie Ausgangsstoffe, Produkte und Ausbeuten jeder Anwendung
einer gemeinsamen Methode. Es ist ein nicht leeres Array von Tabellen. Die
Einträge sind in ihrer Reihenfolge ab 1 nummeriert. Lassen Sie `products` und
`substrates` auf oberster Ebene ganz weg, auch leere Arrays. `scale` bleibt
dort Pflicht und nennt die typische Ansatzgröße.

| Feld | Bedeutung | TOML-Typ | Pflicht je Eintrag | Regel | Beispiel |
|---|---|---|---|---|---|
| `scope[n].substrates` | Ausgangsstoffe dieses Eintrags. | Nicht leeres String-Array | Ja | Registerschlüssel; keine Wiederholungen und kein Produkt desselben Eintrags. | `substrates = ["acetophenone"]` |
| `scope[n].products` | Produkte und ihre isolierten Ausbeuten. | Nicht leeres Array von Tabellen | Ja | Dieselben Regeln wie für `products` auf oberster Ebene, mit `compound` und `yield_percent` je Produkt. | `products = [{ compound = "1-phenylethanol", yield_percent = 85 }]` |
| `scope[n].scale` | Ansatzgröße dieses Eintrags. | String | Nein | Dieselbe Regel für Zahl und Einheit wie bei `scale` auf oberster Ebene. | `scale = "5 mmol"` |
| `scope[n].time` | Reaktionszeit dieses Eintrags. | String | Nein | Eine Zahl, Leerraum und genau `min`, `h` oder `d`; Dezimalpunkt oder Dezimalkomma sind erlaubt. | `time = "30 min"` |
| `scope[n].temperature` | Temperatur dieses Eintrags in °C. | Ganz- oder Gleitkommazahl | Nein | Endlich, ohne Anführungszeichen, kein Wahrheitswert. Keine Einheit anhängen. | `temperature = 80` |
| `scope[n].note` | Anmerkung zu diesem Eintrag. | Nicht leerer String | Nein | Darf nicht leer sein, wenn vorhanden; darf übersetzt werden. | `note = "Rückfluss"` |

Jeder Eintrag wird für sich geprüft. Eine Verbindung darf Ausgangsstoff in
einem Eintrag und Produkt in einem anderen sein. Schreiben Sie `scope` in
Markdown als Array von Tabellen in geschweiften Klammern. Die
[Beispielvorschrift
OSDB-0009](../examples/demo/md/procedures/OSDB-0009-benzylic-alcohols.de.md)
zeigt drei Einträge. In Org verwenden Sie die [benannte
Tabelle](#org-tabelle-scope).

Auf der Vorschriftenseite steht **Anwendungsbereich** vor **Zusammenfassung**.
Die Spalten heißen **Eintrag**, **Ausgangsstoffe**, **Produkte** und
**Ausbeute**. **Ansatzgröße**, **Zeit**, **Temperatur** und **Anmerkung**
erscheinen nur, wenn mindestens ein Eintrag das Feld setzt. Verbindungsnamen
verlinken auf ihre Seiten; Produkte mit Strukturbild zeigen kleine Bilder. Die
Angaben unter dem Titel nennen die typische Ansatzgröße und die Ausbeutespanne
aller Produkte aller Einträge, `<min>–<max> %`, bei gleichen Ausbeuten nur eine
Prozentzahl. Unter **Hergestellt nach** nennt eine Verbindungsseite jeden
Eintrag, der sie herstellt:
`<ID> <Titel> · Eintrag <n> · <Ausbeute> % · <Status>`. **Verwendet in** und
Verzeichniszähler zählen jede Vorschrift nur einmal.

### Optionale Felder

Lassen Sie ein optionales Feld weg, wenn es nicht zutrifft.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `substrates` | Die Ausgangsstoffe einer Einzelvorschrift; mit `scope` auf oberster Ebene verboten. | String-Array | Nein | Schlüssel im Register, ohne Wiederholungen und ohne einen der Produktschlüssel. | `substrates = ["ethanol"]` |
| `scope` | Die Einträge einer allgemeinen Vorschrift. | Nicht leeres Array von Tabellen | Nein | Regeln oben; verbietet `products` und `substrates` auf oberster Ebene. | Siehe OSDB-0009. |
| `scheme_image` | Reaktionsschema im Titelblock anstelle der Produktstrukturen. | String | Nein | Relativer Pfad unter `structures/`, ohne `..`, mit `.svg` oder `.png`, unter dem Verzeichnis für statische Dateien vorhanden. Ohne dieses Feld zeigt eine allgemeine Vorschrift den Platzhalter. | `scheme_image = "structures/aryl-ketone-reduction.svg"` |
| `checked_by` | Wer die Vorschrift geprüft hat. | Array nicht leerer Strings | Nein | Das Array darf leer sein, ein Eintrag aber nicht. | `checked_by = ["B. Example"]` |
| `references` | Literaturangaben als Metadaten. | Array nicht leerer Strings | Nein | Das Array darf leer sein, ein Eintrag aber nicht. | `references = ["Example, A. J. Fictitious Chem. 2020, 1, 1."]` |
| `ai_model` | Das KI-Modell, das beim Schreiben geholfen hat. | Nicht leerer String | Nein | Weglassen, wenn keine KI beteiligt war. Der Wert `"none"` ist ein Fehler. | `ai_model = "example-model-1"` |
| `language` | Die Sprache, in der die Vorschrift geschrieben ist. | String | Nein | `de` oder `en`; trägt der Dateiname ein Sprachkürzel, muss es dieselbe Sprache sein. | `language = "de"` |

## Verbindungsregister

Speichern Sie jede Verbindung einmal, damit mehrere Vorschriften und ihre
Übersetzungen dieselben Daten verwenden. Im Verzeichnis `compounds/` der
Sammlung steht eine UTF-8-TOML-Datei pro Verbindung, namens `<key>.toml`.
Der Schlüssel bestimmt die Identität: Zwei Vorschriften meinen genau dann
dieselbe Verbindung, wenn sie denselben Schlüssel verwenden. Strukturen
werden dafür nicht verglichen.

Ein Schlüssel entspricht `[a-z0-9]+(-[a-z0-9]+)*`: Kleinbuchstaben und
Ziffern mit einzelnen Bindestrichen zwischen den Gruppen, etwa
`ethyl-acetate`. In `products` und `substrates` steht er ohne `.toml`.
Eine Verbindung, die keine Vorschrift nennt, ist gültig. Kopieren Sie zum
Anlegen [templates/compound.toml](../templates/compound.toml). Die Datei
enthält nur TOML, ohne `+++`-Zeilen oder eine Überschrift `[product]`.

| Feld | Bedeutung | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|---|
| `name` | Der Verbindungsname auf einer englischen Website. | Nicht leerer String | Ja | Darf nicht leer sein. | `name = "Ethyl acetate"` |
| `name_de` | Der Verbindungsname auf einer deutschen Website. | Nicht leerer String | Nein | Darf nicht leer sein, wenn vorhanden. Fehlt er, verwendet die deutsche Website `name`. | `name_de = "Ethylacetat"` |
| `formula` | Die Summenformel. | Nicht leerer String | Ja | Darf nicht leer sein. | `formula = "C4H8O2"` |
| `mw` | Molmasse in g/mol. | Ganz- oder Gleitkommazahl | Ja | Endlich und größer als null. Ohne Anführungszeichen, mit Dezimalpunkt. Ein Wahrheitswert ist keine Zahl. | `mw = 88.11` |
| `smiles` | Die Struktur als SMILES, eine Textschreibweise für Molekülstrukturen. | Nicht leerer String | Ja | Darf nicht leer sein. | `smiles = "CCOC(C)=O"` |
| `cas` | Die CAS-Nummer, eine Registriernummer für chemische Stoffe. | String | Nein | 2 bis 7 Ziffern, Bindestrich, 2 Ziffern, Bindestrich und die Prüfziffer. Die Prüfziffer muss stimmen. | `cas = "141-78-6"` |
| `structure_image` | Das Strukturbild im Verzeichnis für statische Dateien. | String | Nein | Ein relativer Pfad unter `structures/` ohne `..`, mit der Endung `.svg` oder `.png`, der auf eine vorhandene Datei zeigt. | `structure_image = "structures/ethyl-acetate.svg"` |

Zum Beispiel kann `compounds/ethyl-acetate.toml` so aussehen:

```toml
name = "Ethyl acetate"
name_de = "Ethylacetat"
formula = "C4H8O2"
mw = 88.11
smiles = "CCOC(C)=O"
cas = "141-78-6"
```

Der Validator prüft, dass `formula` und `smiles` nicht leere Strings sind.
Er prüft weder die Schreibweise der Summenformel noch die Gültigkeit des
SMILES, noch ob die Molmasse zur Summenformel passt.

Das Argument `--static-dir` bestimmt, wo der Validator das `structure_image`
einer Verbindung oder das `scheme_image` einer Vorschrift sucht. Ohne Angabe
nimmt er `static` im aktuellen Verzeichnis. `orgsyndb validate` übergibt das
`static/` der Sammlung. Bei falschem Pfadanfang oder falscher Endung entfällt
die Existenzprüfung.

Das Register hat keine Unterverzeichnisse. Ein Unterverzeichnis ist ein
Fehler unter `file_name` mit `subdirectories are not supported`.
Versteckte Dateien werden stillschweigend übergangen. Jede andere Datei,
die nicht `<key>.toml` heißt, ist ein Fehler unter `file_name` mit
`must be named <key>.toml` und definiert keine Verbindung. Eine nicht als
UTF-8-TOML lesbare Datei erhält einen Fehler unter `toml` und definiert
keine Verbindung; ein Syntaxfehler enthält `invalid TOML`. Ein fehlendes
Pflichtfeld ergibt `required field missing`. Eine Verbindung darf auch die
von ihrer Sammlung deklarierten Felder setzen. Nur Schlüssel, die weder zu
den eingebauten Feldern noch zu diesen Deklarationen gehören, ergeben
Warnungen mit `unknown field`.

Eine Verbindungsseite ergänzt nach **Verwendet in** den Abschnitt
**Synthesewege**, wenn Synthesewege diese Verbindung als Ziel nennen. Die
Liste verlinkt deren Titel, nach Nummer geordnet.

## Felddeklarationen der Sammlung

Um weitere Angaben wie Artikelnummern oder Stoffklassen zu erfassen,
deklarieren Sie Verbindungsfelder in der `orgsyndb.toml` der Sammlung.
Diese UTF-8-TOML-Datei muss `format = 1` als Ganzzahl enthalten. Als
einziger weiterer Schlüssel auf oberster Ebene ist `fields` erlaubt,
eine Tabelle, deren einziger erlaubter Schlüssel `compound` ist. Ohne
`fields` deklariert die Sammlung keine weiteren Felder.

Schreiben Sie eine Tabelle `[[fields.compound]]` je Feld, in der
gewünschten Anzeigereihenfolge. Eine einzelne Tabelle `[fields.compound]`
ist ungültig. Diese Deklaration stammt aus den
[Einstellungen der Beispielsammlung](../examples/demo/orgsyndb.toml):

```toml
format = 1

[[fields.compound]]
key = "item_number"
type = "text"
label = "Item no."
label_de = "Artikelnr."
required = true
unique = true
pattern = 'CH-\d{4}'
column = true
search = true
```

### Schlüssel einer Deklaration

| Schlüssel | TOML-Typ | Pflicht oder Vorgabe | Regel |
|---|---|---|---|
| `key` | String | Pflicht | Entspricht `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`: Kleinbuchstaben und Ziffern, Wörter durch einzelne Unterstriche verbunden, beginnend mit einem Buchstaben. Darf nur einmal deklariert sein, nicht auf `_de` enden und kein eingebauter Schlüssel sein: `name`, `name_de`, `formula`, `mw`, `smiles`, `cas` oder `structure_image`. Der Katalog reserviert außerdem `id`, `title`, `created`, `modified`, `text`, `q`, `sort` und `view` für seine Zeilen und die Adresse. |
| `type` | String | Pflicht | `text`, `number`, `boolean` oder `choice`. |
| `label` | Nicht leerer String | Pflicht | Der Feldname auf einer englischen Website. |
| `label_de` | Nicht leerer String | Optional | Der Feldname auf einer deutschen Website; fehlt er, verwendet sie `label`. |
| `required` | Wahrheitswert | `false` | Bei `true` muss jede Verbindung das Feld setzen. |
| `column` | Wahrheitswert | `false` | Bei `true` zeigt das Verbindungsverzeichnis das Feld als Spalte. |

Nur die folgenden zusätzlichen Schlüssel sind je nach Typ erlaubt. Eine
Option bei einem anderen Typ ist ein Konfigurationsfehler.

| Schlüssel | Feldtyp | TOML-Typ | Pflicht oder Vorgabe | Regel |
|---|---|---|---|---|
| `pattern` | `text` | String | Optional | Ein gültiger regulärer Ausdruck in Python, dem der ganze Wert entsprechen muss. |
| `search` | `text` | Wahrheitswert | `false` | Bei `true` berücksichtigt die Suche im Verbindungskatalog die Werte des Felds. |
| `unique` | `text`, `number` | Wahrheitswert | `false` | Zwei Verbindungen dürfen nicht denselben gültigen Wert setzen. |
| `min` | `number` | Ganz- oder Gleitkommazahl | Optional | Endliche untere Grenze, einschließlich; darf `max` nicht überschreiten, wenn beide gesetzt sind. Ein Wahrheitswert ist keine Zahl. |
| `max` | `number` | Ganz- oder Gleitkommazahl | Optional | Endliche obere Grenze, einschließlich. Ein Wahrheitswert ist keine Zahl. |
| `unit` | `number` | Nicht leerer String | Optional | Steht nach der Zahl, durch ein Leerzeichen getrennt. |
| `vocabulary` | `choice` | String | Pflicht | Benennt `vocabularies/<name>.toml` neben `orgsyndb.toml`, ohne Verzeichnis und Endung. Der Name entspricht `[a-z0-9]+(-[a-z0-9]+)*`. |
| `multiple` | `choice` | Wahrheitswert | `false` | Bei `true` setzt die Verbindung eine nicht leere Liste verschiedener Werte statt eines einzelnen Strings. |
| `facet` | `boolean`, `choice` | Wahrheitswert | `false` | Bei `true` bietet der Verbindungskatalog das Feld als Filter an. |

Die Beispielsammlung deklariert außerdem `short_name` als Text mit
`search = true`, `chemical_class` als Pflichtauswahl mit `multiple = true`,
`column = true` und `facet = true`, `stock` als Zahl mit `min = 0` und
`unit = "g"` sowie `in_house` als Wahrheitswert mit `facet = true`.

### Vokabulare

Ein Vokabular enthält die erlaubten Werte eines Auswahlfeldes. Speichern
Sie es als UTF-8-TOML in `vocabularies/<name>.toml` neben der
Einstellungsdatei. Der Dateiname ohne `.toml` und jeder Wertschlüssel auf
oberster Ebene müssen `[a-z0-9]+(-[a-z0-9]+)*` entsprechen: Kleinbuchstaben
und Ziffern mit einzelnen Bindestrichen zwischen den Gruppen. Jeder Wert
ist eine Tabelle mit diesen Schlüsseln und keinen weiteren:

| Schlüssel | TOML-Typ | Pflicht | Regel |
|---|---|---|---|
| `label` | Nicht leerer String | Ja | Der Name des Werts auf einer englischen Website. |
| `label_de` | Nicht leerer String | Nein | Der Name des Werts auf einer deutschen Website; fehlt er, verwendet sie `label`. |
| `parent` | String | Nein | Ein anderer Wertschlüssel derselben Datei, unter dem dieser Wert eingeordnet ist. |

Ein Vokabular muss mindestens einen Wert enthalten. Wer `parent` folgt,
muss schließlich einen Wert ohne übergeordneten Wert erreichen; kein Wert
darf sein eigener Vorfahr sein. Die Zahl der Ebenen ist unbegrenzt.
Verbindungen dürfen Werte auf jeder Ebene wählen. Der Aufbau entspricht
dem Reaktionstyp-Vokabular, ergänzt um `parent`.

Das
[Vokabular der Beispielsammlung](../examples/demo/vocabularies/chemical-classes.toml)
enthält etwa:

```toml
[carbonyl-compounds]
label = "Carbonyl compounds"
label_de = "Carbonylverbindungen"

[acid-derivatives]
label = "Carboxylic acid derivatives"
label_de = "Carbonsäurederivate"
parent = "carbonyl-compounds"

[esters]
label = "Esters"
label_de = "Ester"
parent = "acid-derivatives"
```

Die Sammlung darf `vocabularies/` weglassen, wenn kein Feld es benötigt.
`init` legt das Verzeichnis nicht an.

### Verbindungswerte und Meldungen

Setzen Sie jedes deklarierte Feld als normalen Schlüssel auf oberster
Ebene in der Verbindungsdatei, neben `name`, `cas` und den anderen
eingebauten Feldern. Die `methyl-salicylate.toml` der Beispielsammlung
setzt etwa:

```toml
item_number = "CH-0018"
chemical_class = ["esters", "phenols"]
```

Das Vokabular der Beispielsammlung definiert beide Auswahlwerte.
`item_number` und `chemical_class` sind dort Pflichtfelder. Eine neu
hinzugefügte Verbindung muss daher beide setzen und eine noch nicht
vergebene Artikelnummer verwenden. Der Schlusskommentar der
Verbindungsvorlage fordert dazu auf, die von Ihrer Sammlung deklarierten
Felder als weitere Zeilen derselben Form einzutragen.

Wertprobleme sind Fehler am Pfad der Verbindungsdatei, unter dem Schlüssel
des deklarierten Feldes:

| Feldtyp oder Regel | Meldung | Bedeutung |
|---|---|---|
| `required = true` | `required field missing` | Das Feld in jeder Verbindung setzen. |
| `text`, einzelnes `choice` | `must be a string` | Den Wert in Anführungszeichen setzen. |
| `text` | `must not be empty` | Nicht leeren Text angeben. |
| `text` mit `pattern` | `must match the pattern <pattern>` | Der ganze String muss dem deklarierten Muster entsprechen. |
| `number` | `must be a number, unquoted` | Eine endliche TOML-Ganz- oder Gleitkommazahl ohne Anführungszeichen oder Einheit angeben; ein Wahrheitswert ist keine Zahl. |
| `number` mit `min` | `must be at least <min>` | Den Wert auf die untere Grenze oder darüber erhöhen. |
| `number` mit `max` | `must be at most <max>` | Den Wert auf die obere Grenze oder darunter verringern. |
| `boolean` | `must be true or false, unquoted` | `true` oder `false` ohne Anführungszeichen verwenden. |
| `choice` | `unknown value "<v>"; see vocabularies/<name>.toml for the allowed values` | Einen Wertschlüssel aus dem genannten Vokabular verwenden, auf beliebiger Ebene. |
| `choice` mit `multiple = true` | `must be a list of strings, e.g. ["<a value>"]` | Eine Liste von Wertschlüsseln in Anführungszeichen angeben. Das Beispiel nennt einen Wert aus dem Vokabular. |
| `choice` mit `multiple = true` | `must not be empty` | Mindestens einen Auswahlwert angeben. |
| `choice` mit `multiple = true` | `repeats "<v>"` | Den wiederholten Wert entfernen. |
| `unique = true` | `"<value>" is also set by <other compound keys>` | Einen Wert verwenden, den keine andere Verbindung setzt. Zahlen stehen in der Meldung ohne Anführungszeichen. |

Ein Wert mit falschem Typ ergibt nur diesen Typfehler. Leerer Text mit
einem Muster ergibt nur `must not be empty`. Eine Auswahlliste ergibt
eine Meldung `unknown value` je unbekanntem String. Die
Eindeutigkeitsprüfung vergleicht Werte, die ihre Feldprüfung bestehen,
und meldet jede Verbindung, die denselben Wert setzt.

### Konfigurationsfehler

Der Validator lehnt Einstellungen oder Vokabulare ab, die eine der
obigen Regeln verletzen. Dazu zählen ungültige reguläre Ausdrücke, nicht
endliche Grenzen, `min` größer als `max`, doppelte Deklarationen,
fehlende Vokabulardateien und Schleifen der übergeordneten Werte. Eine
mit `--settings` ausdrücklich benannte Datei muss vorhanden sein.
Einstellungs- und Vokabulardateien müssen als UTF-8-TOML lesbar sein.

Dies sind Konfigurationsfehler: Rückgabewert 2, keine Standardausgabe
und `validate.py: error: ...` auf der Standardfehlerausgabe. Die Meldungen
nennen die Einstellungs- oder Vokabulardatei, den Feldschlüssel, sofern
gültig, und den beanstandeten Schlüssel oder Wert. Eine Option für einen
anderen Typ ergibt etwa `a number field does not take pattern`; eine
unbekannte Option ergibt `unknown key <key>`. Ein unbekannter Schlüssel
auf oberster Ebene der Einstellungen ergibt
`unknown key <key>; only format and fields are allowed`.

Vor einem Befehl prüft das Build-Programm nur das TOML der
Einstellungsdatei, `format` und die Schlüssel auf oberster Ebene. Der
Validator prüft die Deklarationen und Vokabulare. Eine fehlerhafte
Deklaration verhindert daher weder `clean` noch `new`.

### Anzeige auf der Website

Verbindungsseiten zeigen gesetzte Felder nach Summenformel, Molmasse,
CAS und SMILES, in Deklarationsreihenfolge und mit den Feldnamen in der
Sprache der Website. Text erscheint wie eingetragen. Zahlen verwenden
das Dezimalzeichen der Website und die deklarierte Einheit, etwa
`12,5 g` auf einer deutschen Website. Wahrheitswerte erscheinen als
**Yes** oder **No**, auf Deutsch als **Ja** oder **Nein**.

Ein Auswahlwert auf einer Verbindungsseite zeigt die Namen seiner
übergeordneten Werte und seinen eigenen Namen, verbunden durch ` › `,
etwa **Carbonylverbindungen › Carbonsäurederivate › Ester**. Mehrere
Auswahlwerte sind durch `, ` getrennt, in der Reihenfolge der Verbindung.
Das Verbindungsverzeichnis ergänzt Felder mit `column = true` nach CAS,
in Deklarationsreihenfolge. Es zeigt nur den eigenen Namen jedes
Auswahlwerts, lässt ungesetzte Werte als leere Zellen und richtet
Zahlenspalten rechtsbündig aus.

Unter `/compounds/` ist das Verzeichnis ein durchsuchbarer, filterbarer
Katalog aller Registereinträge. Die Zeilen bleiben nach dem angezeigten
Namen in der Sprache der Website geordnet. Felder mit `facet = true`
erscheinen als Filter in Deklarationsreihenfolge. Ein Auswahlfilter zeigt
die von Verbindungen verwendeten Werte und deren übergeordnete Werte als
eingerückten Baum. Er folgt der Reihenfolge in der Vokabulardatei; alle
untergeordneten Werte stehen unmittelbar nach dem zugehörigen übergeordneten
Wert. Wählen Sie einen übergeordneten Wert, erfasst der Filter auch
Verbindungen unter dessen untergeordneten Werten: **Carbonylverbindungen**
schließt Ketone und Ester ein. Filter für Wahrheitswerte bieten **Ja** und
**Nein** (auf Englisch **Yes** und **No**) jeweils nur an, wenn eine
Verbindung den Wert setzt.

Ausgewählte Werte innerhalb eines Filters sind mit ODER verknüpft,
verschiedene Filter mit UND. Die Anzahl neben einem Wert berücksichtigt
die Suche und alle anderen Filter, jedoch nicht die Auswahl im eigenen
Filter. Ausgewählte Werte erscheinen als einzeln entfernbare Schaltflächen;
**Alles zurücksetzen** löscht Suchtext und Auswahl. Der Katalog zeigt die
Gesamtzahl oder beim Filtern **{shown} von {total} Verbindungen**. Ohne
Felder mit `facet = true` entfällt die Filterspalte; Anzahl und Suche bleiben.

Das Suchfeld **Verbindungen durchsuchen** im Kopf berücksichtigt englische
und deutsche Namen, Summenformel, CAS-Nummer, SMILES und Werte von Textfeldern
mit `search = true`. Jedes Suchwort muss als Teil einer Zeichenfolge
vorkommen. Dabei zählen weder Groß- und Kleinschreibung noch Zeichen außer
Buchstaben und Ziffern. Suchangaben wie `50-78-2`, `salicyl` und `c1ccccc1O`
funktionieren ohne Pagefind-Index. Auf anderen Seiten, auch auf
Verbindungsseiten, durchsucht das Feld Vorschriften; Verbindungsseiten
bleiben außerhalb des Suchindex für Vorschriften.

Die Adresse hält Suchtext und Auswahl fest, etwa
`/compounds/?q=ester&chemical_class=esters&in_house=true`. Parameter, die die
Seite nicht anwenden kann, nennt sie in einem Hinweis und entfernt sie aus
der Adresse. Suche und Filter brauchen JavaScript. Ohne JavaScript zeigt
die Seite die vollständige Tabelle und einen entsprechenden Hinweis.

## Synthesewege

Ein Syntheseweg hält eine geordnete Folge von mindestens zwei Vorschriften
fest. Schreiben Sie ihn in Markdown, auch wenn seine Stufen Org-Vorschriften
verwenden. Kopieren Sie [templates/sequence.md](../templates/sequence.md) nach
`md/sequences/` der Sammlung. `orgsyndb init` legt diesen Ordner an; ein
fehlender Ordner enthält keine Synthesewege. `orgsyndb new` erzeugt
Vorschriften, daher kopieren Sie die Vorlage für Synthesewege von Hand.

Der Dateiname ist `SEQ-NNNN-short-slug.md`, optional mit `.de` oder `.en` vor
`.md`. Der kurze Slug entspricht `[a-z0-9]+(-[a-z0-9]+)*`. Die Nummer im
Dateinamen muss gleich `id` sein. Ersetzen Sie die Vorlagenwerte `SEQ-0000`
und `seq-0000` durch eine freie Nummer von `SEQ-0001` bis `SEQ-9999` und ihre
Kleinschreibung. Die Seite steht unter `/sequences/seq-NNNN/`.

Der Validator liest nur die oberste Ebene. Unterordner sind Fehler;
versteckte Dateien und `_index.md` überspringt er stillschweigend. Eine Datei
ohne Endung `.md` ergibt `not a sequence file; ignored`; eine Markdown-Datei
mit falschem Namen einen Fehler unter `file_name`.

### Felder eines Synthesewegs

Behalten Sie alle sieben Pflichtfelder zwischen den `+++`-Zeilen. Ersetzen
Sie Ziel und Stufen der Vorlage durch Ihren Weg. Fügen Sie kein `authors`
hinzu: Jede Stufe nennt die Autoren ihrer Vorschrift. Die Taxonomiefelder
der Vorschriften, `authors`, `tags` und `reaction_types`, sind in einem
Syntheseweg Fehler und halten den Build an: Hugo würde den Syntheseweg
sonst unter den Vorschriften eines Autors, Schlagworts oder Reaktionstyps
führen. Jedes andere Feld außerhalb dieses Schemas ergibt eine Warnung
`unknown field`. Unbekannte Felder einer Stufe erscheinen unter
`steps[n].<key>`.

| Feld | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|
| `id` | String | Ja | `SEQ-0001` bis `SEQ-9999`; einmal je Sprachkürzel und einmal ohne Kürzel eindeutig. | `id = "SEQ-0001"` |
| `slug` | String | Ja | Genau die `id` in Kleinbuchstaben. | `slug = "seq-0001"` |
| `title` | Nicht leerer String | Ja | Seitentitel. | `title = "Aspirin aus Wintergrünöl"` |
| `date` | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen; dieselben Regeln wie bei Vorschriften. | `date = 2026-10-23T09:15:00+02:00` |
| `lastmod` | Datum mit Zeitzonenversatz | Ja | Dieselben Regeln wie für `date`; nicht früher als `date`. | `lastmod = 2026-10-23T09:40:00+02:00` |
| `target` | String | Ja | Vorhandener Verbindungsschlüssel ohne `.toml`; ein Produkt der letzten Stufe. | `target = "acetylsalicylic-acid"` |
| `steps` | Array von Tabellen | Ja | Mindestens zwei Stufen, in Ausführungsreihenfolge. | `steps = [{ procedure = "OSDB-0001" }, { procedure = "OSDB-0002" }]` |
| `steps[n].procedure` | String | In jeder Stufe | Vorschriftennummer aus den geprüften Inhaltsverzeichnissen, aus Org exportiert oder in Markdown geschrieben. | `procedure = "OSDB-0009"` |
| `steps[n].entry` | Ganzzahl | Nur bei allgemeinen Vorschriften | Eintragsnummer von 1 bis zur Zahl der Scope-Einträge; bei Einzelvorschriften verboten. Kein Wahrheitswert. | `entry = 1` |

Schreiben Sie nach der schließenden `+++`-Zeile Anmerkungen, etwa unter
`## Anmerkungen`. Die acht Textabschnitte einer Vorschrift sind nicht
vorgeschrieben. [SEQ-0002 der
Beispielsammlung](../examples/demo/md/sequences/SEQ-0002-biphenylyl-ethanol.de.md)
zeigt eine Stufe mit einer allgemeinen Vorschrift:

```toml
target = "1-biphenyl-4-yl-ethanol"
steps = [{ procedure = "OSDB-0004" }, { procedure = "OSDB-0009", entry = 1 }]
```

### Zusammenhang der Stufen, Fassungen und Ausbeute

Jede Stufe nach der ersten muss mindestens ein Produkt der vorigen Stufe als
Ausgangsstoff verwenden. Bei einer allgemeinen Vorschrift zählen nur die
Ausgangsstoffe und Produkte des gewählten Eintrags. Das Ziel muss ein Produkt
der letzten Stufe sein. Der Validator prüft diesen Zusammenhang nur an der
Bezugsfassung: der Datei ohne Sprachkürzel, sonst `.de`, sonst `.en`. Dafür
müssen mindestens zwei Stufentabellen vorliegen. Eine Stufe mit unbekannter
Vorschrift oder fehlendem, ungültigem oder verbotenem Eintrag bleibt bei der
Zusammenhangsprüfung unberücksichtigt. Die Zielprüfung setzt zusätzlich einen
bekannten Verbindungsschlüssel voraus.

Fassungen teilen Grundnamen, `id`, `slug`, `target` und die geordneten `steps`.
Jedes Sprachkürzel und das Fehlen eines Kürzels darf je Nummer einmal
vorkommen. Titel, Zeitangaben und Text dürfen sich unterscheiden. Abweichungen
der gemeinsamen Felder sind Fehler an der anderen Fassung, die die
Bezugsdatei nennen. Der Build veröffentlicht eine Fassung: die mit dem
Sprachkürzel der Website, sonst die ohne Kürzel, sonst die andere Sprache.
Er legt sie unter `build/content/sequences/` ab.

Die Gesamtausbeute multipliziert die Ausbeuten der Produkte, die jeweils in
die nächste Stufe eingehen, und die Ausbeute des Ziels in der letzten Stufe.
Gehen mehrere Produkte weiter, zählt das erste in Produktreihenfolge. Die
Anzeige rundet auf ganze Prozent, bei genau einem halben Prozent nach oben.
Die Seite zeigt **Stufen** und **Gesamtausbeute**, ein Schema mit verlinkten
Verbindungen und Stufen, eine Liste mit Vorschriftenlinks, gegebenenfalls
Eintragsnummer, Reaktionstyp, Ausbeute und Status, danach die Anmerkungen.
`/sequences/` listet Synthesewege nach Nummer mit Titel, Zielverbindung,
Stufenzahl und Gesamtausbeute. Synthesewegseiten stehen nicht im Suchindex.

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
auch Tippfehler wie `checkedby` und die Felder `product`, `yield_percent`
auf oberster Ebene, `precursors` und `structure_image`. Ein unbekanntes Feld
in einem Eintrag von `products` ergibt etwa `products[1].colour` als Warnung.
Registerfelder sind nur dann unbekannt, wenn sie weder zu den eingebauten
Verbindungsfeldern noch zu den Deklarationen der Sammlung gehören. Sie
ergeben Warnungen an der Verbindungsdatei unter dem jeweiligen Feldnamen.

## Org-Schlüsselwörter auf Dateiebene

`orgsyndb export` prüft, dass eine Org-Vorschrift `#+CREATED` und
`#+LAST_MODIFIED` genau einmal enthält. `#+AI_MODEL` darf höchstens einmal
vorkommen. Groß- und Kleinschreibung der Namen spielt keine Rolle.

| Org-Schlüsselwort | Wert | Exportierter Datenblock |
|---|---|---|
| `#+CREATED` | Ein inaktiver Zeitstempel genau in der Form `[YYYY-MM-DD Day hh:mm:ss]`. | `date`, mit demselben Ortsdatum und derselben Ortszeit und dem zu diesem Zeitpunkt geltenden Versatz von Europe/Berlin. |
| `#+LAST_MODIFIED` | Ein inaktiver Zeitstempel genau in der Form `[YYYY-MM-DD Day hh:mm:ss]`. | `lastmod`, ebenso. |
| `#+AI_MODEL` (optional) | Falls vorhanden: `none` oder eine Modellkennung, die `[A-Za-z0-9][A-Za-z0-9._:/@+-]*` entspricht. | Kein Feld `ai_model`, wenn das Schlüsselwort fehlt oder den Wert `none` hat; sonst ein String `ai_model` mit dem Wert des Schlüsselworts. |

Zum Beispiel:

```org
#+CREATED: [2026-10-19 Mon 17:42:05]
#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]
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

Bei einer Einzelvorschrift setzen Sie `products` allein auf die letzte
Custom-Front-Matter-Zeile. `substrates` und alle anderen benutzerdefinierten
Felder stehen davor:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :substrates '("ethanol")
#+HUGO_CUSTOM_FRONT_MATTER: :products '(((compound . "ethyl-acetate") (yield_percent . 85)))
```

Jedes Produkt ist ein Eintrag `((compound . "key") (yield_percent . N))`
in der gequoteten Liste. Zahlen haben in jeder Sprache einen Dezimalpunkt.
Der Export hält tabellenartige Metadaten zusätzlich am Ende, damit spätere
Felder nicht zur letzten Tabelle `[[products]]` gehören.

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

### Org-Tabelle scope

Entfernen Sie bei einer allgemeinen Vorschrift die Custom-Front-Matter-Zeilen
`:products` und `:substrates` auf oberster Ebene. Schreiben Sie eine
Org-Tabelle unmittelbar nach `#+NAME: scope`, außerhalb von Blöcken. Groß- und
Kleinschreibung des Tabellennamens spielt keine Rolle. Die erste Zeile benennt
die Spalten, gefolgt von einer Trennlinie und einer Zeile je Eintrag.
`substrates`, `products` und `yield_percent` sind Pflichtspalten; `scale`,
`time`, `temperature` und `note` sind optional. Die Spaltennamen bleiben
englisch.

Trennen Sie Verbindungsschlüssel in `substrates` und `products` durch
Leerzeichen. In `yield_percent` steht eine Zahl je Produkt, in derselben
Reihenfolge und durch Leerzeichen getrennt. `temperature` enthält eine Zahl.
Zahlen dürfen ein Dezimalkomma haben, etwa `45,5`. Text in `scale`, `time` und
`note` wird am Rand von Leerraum befreit. Eine leere Zelle lässt das Feld
ungesetzt; Pflichtfelder je Eintrag prüft weiterhin der Validator.

Die [Org-Beispieldatei](../tests/fixtures/export/OSDB-0909-scope-table.org)
zeigt drei Einträge, darunter einen mit zwei Produkten. Der Export schreibt
`scope` in den Datenblock und entfernt die Tabelle samt `#+NAME` aus dem Text.
Je Eintrag stehen `products` nach den anderen Feldern, damit diese nicht zur
letzten Produkttabelle gehören. Ein Reaktionsschema setzen Sie so:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :scheme_image "structures/aryl-ketone-reduction.svg"
```

Fehlerhafte Tabellen brechen den Export mit dem Feld `scope` ab. Die
Zeilenzählung beginnt nach der Trennlinie bei 1:

| Meldung | Korrektur |
|---|---|
| `appears more than once` | Nur eine Tabelle namens `scope` behalten. |
| `"<name>" is not a scope column` | Einen der sieben Spaltennamen oben verwenden. |
| `column "<name>" missing` | Die genannte Pflichtspalte ergänzen. |
| `column "<name>" appears more than once` | Die genannte Spalte nur einmal behalten. |
| `row <n>: <p> products but <y> yields` | Eine Ausbeute je Produkt in dessen Reihenfolge angeben. |
| `row <n>: "<cell>" is not a number` | Ausbeute oder Temperatur als Zahl ohne Einheit schreiben. |

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

Jede Vorschrift auf Deutsch, auch eine allgemeine Vorschrift, hat diese acht
Abschnitte in dieser Reihenfolge. Die Website fügt die Tabelle des
Anwendungsbereichs davor ein:

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
eine Datei mit dem Kürzel der anderen Sprache. Eine abgeleitete Vorstufe
darf jede Vorschrift sein, in welcher Sprache ihre Fassungen auch sind.

Die Fassungen einer Vorschrift

- haben denselben Grundnamen, den Dateinamen ohne Kürzel und Endung;
- haben dieselbe `id` und denselben `slug`;
- haben denselben Wert, oder dasselbe Fehlen, von `status`, `reaction_types`,
  `tags`, `products`, `substrates`, `scope` und `scheme_image`;
- dürfen `note` in jedem Eintrag von `scope` übersetzen; alle anderen Werte von
  `scope` und die Reihenfolge der Einträge müssen übereinstimmen;
- dürfen sich in allen übrigen Feldern und im Text unterscheiden: `title`,
  `scale`, `hazards`, `references`, `authors`, `checked_by`, `ai_model`,
  `language`, `date` und `lastmod`.

Der Validator vergleicht jede Fassung mit einer Bezugsfassung: der Datei ohne
Kürzel, sonst der `.de`-Datei. Jede Abweichung ist ein Fehler an der anderen
Fassung, der die Bezugsfassung nennt. Ein geänderter Produktschlüssel oder eine
geänderte Ausbeute erscheint unter `products`, eine geänderte Liste der
Ausgangsstoffe unter `substrates`. Abweichungen in `scope` erscheinen unter
`scope`, ohne Vergleich der Anmerkungen; ein geänderter Schemapfad unter
`scheme_image`. Zahlen werden nach ihrem Wert verglichen: `85` und `85.0`
stimmen überein. Bei anderen Werten müssen Wert und Typ übereinstimmen.

Verbindungsnamen kommen aus dem Register, unabhängig von der Sprache der
Vorschrift. Eine deutsche Website verwendet `name_de`, wenn vorhanden,
sonst `name`; eine englische verwendet `name`. Das gilt für
Verbindungsseiten und deren Reihenfolge im Verzeichnis, Produkt- und
Ausgangsstofflinks, Ausbeuten, Bildbeschreibungen, Katalogdetails und
indexierte Suchbegriffe.

Das optionale Feld `language` gibt die Sprache einer Vorschrift an,
`"de"` oder `"en"`. Trägt der Dateiname ein Kürzel, muss das Feld dieselbe
Sprache nennen; einer Datei mit Kürzel, der das Feld fehlt, fügt der Build
es hinzu. Bei einer Datei ohne Kürzel bestimmt es, welche
Abschnittsnamen gelten. Ist die veröffentlichte Fassung in einer anderen
Sprache als die Website, kennzeichnet ihre Seite die Vorschrift mit einem
`lang`-Attribut.

Die Reagenzientabelle einer deutschen Vorschrift hat die Spalten **Reagenz**,
**CAS**, **M (g/mol)**, **Menge**, **mmol** und **Äquiv.**; ein Katalysator hat
`kat.` in **mmol** und **Äquiv.** Deutscher Text schreibt Dezimalkommas.
Produktausbeuten in `products` oder `scope`, Temperaturen in `scope` und `mw`
in Verbindungsdateien bleiben in jeder Sprache TOML-Zahlen mit Dezimalpunkt;
eine deutsche Website zeigt sie mit Komma.

## Meldungen des Validators lesen

Starten Sie den Validator mit mindestens einem Markdown-Verzeichnis:

```text
tools/validate.py [--vocabulary FILE] [--settings FILE] [--static-dir DIR] [--compounds DIR] [--sequences DIR] CONTENT_ROOT...
```

Jedes `CONTENT_ROOT` ist ein Verzeichnis mit Markdown-Vorschriften.
Ohne Angabe ist `--vocabulary` die Datei `site/data/reaction_types.toml` der
Anwendung, ausgehend vom Ort des Skripts und nicht vom aktuellen
Verzeichnis. `--static-dir` ist `static` und `--compounds` ist `compounds`
im aktuellen Verzeichnis. Der Validator prüft dort jede Verbindungsdatei
und löst die Schlüssel der Vorschriften gegen dieses Register auf. Ein
fehlendes Registerverzeichnis ist leer: Jeder genannte Schlüssel ist dann
unbekannt. Ein vorhandener Pfad, der kein Verzeichnis ist, ergibt einen
Konfigurationsfehler. `orgsyndb validate` übergibt nach dem Org-Export
`--settings orgsyndb.toml --static-dir static --compounds compounds --sequences md/sequences`
aus dem Hauptordner der Sammlung.

`--settings` benennt die `orgsyndb.toml` der Sammlung. Ohne diese Option
verwendet der Validator `orgsyndb.toml` im aktuellen Verzeichnis; fehlt
diese Vorgabedatei, sind keine weiteren Felder deklariert. Eine mit
`--settings` ausdrücklich benannte Datei muss vorhanden sein. Der
Validator prüft die Deklarationen und sucht deren Vokabulare ausgehend
vom Verzeichnis der Einstellungsdatei. Danach prüft er die Werte jeder
Verbindung gegen die Deklarationen.

`--sequences` ist ohne Angabe `md/sequences` im aktuellen Verzeichnis. Ein
fehlender Ordner enthält keine Synthesewege; ein vorhandener Pfad, der kein
Verzeichnis ist, ergibt einen Konfigurationsfehler. Stufen verweisen auf
Vorschriften aus den angegebenen Inhaltsverzeichnissen, Ziele auf das
Verbindungsregister.

Jedes Problem ist eine Zeile auf der Standardausgabe:

```text
<pfad>:<feld>: <schwere>: <meldung>
```

Das Feld ist meist ein Feld des Datenblocks. Produktfelder heißen etwa
`products[1].yield_percent`; die Zählung beginnt bei 1. Ein Eintrag, der
keine Tabelle ist, erscheint unter `products[n]`. Registerprobleme nennen
den Pfad der Verbindungsdatei und den Feldnamen, etwa
`compounds/ethyl-acetate.toml:mw`. Weitere mögliche Felder sind `file_name`,
`front_matter`, `toml` und `body`. Die Meldungen sind englisch.

Felder eines Eintrags heißen `scope[n].<key>`, Produktfelder darin
`scope[n].products[m].<key>`. Beide Zählungen beginnen bei 1. Ein Eintrag, der
keine Tabelle ist, erscheint unter `scope[n]`. Ein unbekanntes Feld in einem
Eintrag ergibt eine Warnung `unknown field` unter dem vollen Feldnamen.

| Feld | Meldung | Bedeutung |
|---|---|---|
| `products` oder `substrates` | `a general procedure lists them in scope; move <key> into its entries` | Feld auf oberster Ebene entfernen und Daten den passenden Einträgen zuordnen. |
| `scope` | `must not be empty` | Mindestens einen Eintrag angeben. |
| `scope` oder `scope[n]` | `must be an array of tables` oder `must be a table` | TOML-Form korrigieren; die Meldung zeigt auch ein Beispiel. |
| `scope[n].time` | `"<value>" must be a number followed by min, h or d, e.g. "2 h"` | Eine Zahl mit einer der drei Einheiten angeben. |
| `scope[n].temperature` | `must be a number in °C, unquoted, e.g. 80` | Anführungszeichen und Einheit entfernen; eine endliche Zahl verwenden. |

Fehlende Pflichtfelder, doppelte Schlüssel, unbekannte Verbindungen und
ungültige Ausbeuten verwenden die folgenden Produkt- und Ausgangsstoffmeldungen
unter dem jeweiligen Feld in `scope`.

Bei `products` bedeutet `must not be empty`, dass Sie mindestens einen
Eintrag angeben müssen. `must be an array of tables` oder
`must be a table` bezeichnet eine falsche TOML-Form. `required field missing` nennt ein fehlendes Feld.
Ein unbekannter Schlüssel ergibt `unknown compound "<key>"; the compound
registry has no <key>.toml`. Prüfen Sie die Schreibweise und das
Registerverzeichnis. `lists <key> twice` bezeichnet ein doppelt genanntes
Produkt oder einen Ausgangsstoff; `<key> is also a product` bedeutet,
dass ein Ausgangsstoff auch als Produkt aufgeführt ist.

`orgsyndb export` schreibt Probleme der Org-Quellen in derselben Zeilenform
auf die Standardausgabe. Seine Felder können auch Org-Schlüsselwörter wie
`#+CREATED`, Eigenschaften wie `#+PROPERTY` oder `:EXPORT_DATE:` und
Schubladen wie `:LOGBOOK:` sein.

Ein `error` bedeutet, dass eine Vorschrift, ein Verbindungseintrag oder ein
Syntheseweg ungültig ist. Eine `warning`
bezeichnet ein Problem, das die Prüfung nicht scheitern lässt, etwa einen
fehlenden Abschnitt oder ein unbekanntes Feld. Nach den Problemzeilen
schreibt der Validator eine Zusammenfassung auf die Standardfehlerausgabe.
Die Dateizahl umfasst Vorschriften, Verbindungsdateien und Synthesewegdateien,
einschließlich aller Sprachfassungen. Für die
Beispielsammlung einschließlich vorhandener Org-Exporte lautet sie:

```text
validated 42 files: 0 errors, 0 warnings
```

Die ersten drei Zeilen sind echte Ausgaben des Validators. Die letzte
Zeile erzeugt `orgsyndb export` in derselben Form für eine Org-Quelle:

```text
tests/fixtures/invalid/yield-out-of-range/OSDB-0110-yield-out-of-range.md:products[1].yield_percent: error: 104.5 must be between 0 and 100
tests/fixtures/invalid/unknown-compound/OSDB-0123-unknown-compound.md:products[1].compound: error: unknown compound "no-such-compound"; the compound registry has no no-such-compound.toml
tests/fixtures/warn/missing-section/OSDB-0151-missing-section.md:body: warning: missing section "Notes"
tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)
```

Der Rückgabewert sagt einem aufrufenden Befehl, ob die Prüfung gelungen ist:

| Rückgabewert | Bedeutung |
|---|---|
| `0` | Kein Fehler gefunden. Warnungen können ausgegeben worden sein. |
| `1` | Mindestens ein Fehler in einer Vorschrift, Verbindungsdatei oder einem Syntheseweg. |
| `2` | Aufruf oder Konfiguration des Validators ist ungültig, etwa kein Verzeichnis, ein Verzeichnis, das keines ist, eine fehlende ausdrücklich benannte Einstellungsdatei, ungültige Einstellungen oder Deklarationen oder eine fehlende oder fehlerhafte Vokabulardatei. |

Aufruf- und Konfigurationsfehler gehen auf die Standardfehlerausgabe und
enthalten `validate.py: error:`; die Standardausgabe bleibt leer. Der
Validator unterdrückt Prüfungen, die von einem fehlenden oder fehlerhaften
Wert abhängen, sodass ein Fehler meist keine Kette von Folgemeldungen
auslöst.

### Meldungen zu Synthesewegen

Probleme nennen die Synthesewegdatei, etwa
`md/sequences/SEQ-0002-biphenylyl-ethanol.de.md`, mit Feldern `steps[n]` oder
`steps[n].<key>`; die Stufenzählung beginnt bei 1. Die Tabelle nennt die
Meldung oder den kennzeichnenden Teil einer längeren Meldung. Datums- und
TOML-Fehler folgen denselben Regeln wie bei Vorschriften.

| Feld | Meldung | Korrektur |
|---|---|---|
| Jedes Pflichtfeld | `required field missing` | Das Feld aus der Feldtabelle ergänzen. |
| `id` | `must match SEQ-NNNN` oder `must be between SEQ-0001 and SEQ-9999` | `SEQ-` und vier Ziffern von `0001` bis `9999` verwenden. |
| `id` | `duplicate id <id>, also used by <path>` | Eine freie Nummer vergeben; je Sprachkürzel und einmal ohne Kürzel darf eine Datei sie teilen. |
| `slug` | `must be "<value>" (the lowercased id)` | Die `id` in Kleinbuchstaben verwenden. |
| `file_name` | `must be named SEQ-NNNN-short-slug.md` oder `does not match id <id>` | Dateinamen oder Nummer korrigieren. |
| `target` | `unknown compound "<key>"` | Schlüssel korrigieren oder Registereintrag anlegen. |
| `steps` | `must list at least two steps` | Genügend Stufen für einen Syntheseweg angeben. |
| `steps` oder `steps[n]` | `must be an array of tables` oder `must be a table` | Die oben gezeigten TOML-Formen verwenden. |
| `steps[n].procedure` | `<id> not found in any content root` | Vorhandene Vorschriftennummer verwenden; beim direkten Aufruf deren Verzeichnis mitgeben. |
| `steps[n].entry` | `OSDB-NNNN is a general procedure; name one of its entries 1 to <count>` | Die gewählte Eintragsnummer ergänzen. |
| `steps[n].entry` | `OSDB-NNNN has no scope entries; remove entry` | `entry` bei einer Einzelvorschrift entfernen. |
| `steps[n].entry` | `must be between 1 and <count>, the number of an entry of OSDB-NNNN's scope` | Einen vorhandenen Eintrag als Ganzzahl ohne Anführungszeichen wählen. |
| `steps[n]` | `starts from none of the products of step <k> (<keys>)` | Stufenreihenfolge und Ausgangsstoffe und Produkte der gewählten Einträge prüfen. |
| `target` | `<key> is not a product of the last step, step N` | Ziel und letzte Vorschrift oder letzten Eintrag prüfen. |
| `target` oder `steps` | `must equal the value in <path>` | In jeder Fassung dasselbe Ziel und dieselben geordneten Stufen verwenden. |
| `authors`, `tags` oder `reaction_types` | `must not be set; a sequence joins no procedure taxonomy` | Feld entfernen; die Vorschriften der Stufen tragen diese Angaben. |
| Jedes andere Feld | `unknown field` | Feld entfernen oder korrigieren. |
