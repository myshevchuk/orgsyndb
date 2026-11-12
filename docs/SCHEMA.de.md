# Schema-Referenz für Vorschriften

Diese Referenz legt fest, was gültige OrgSynDB-Vorschriften und
Synthesewege sind und welche Registerdaten sie verwenden. Schlagen
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
| `authors` | Die Laborkonten aller, die die Vorschrift geschrieben haben. | Nicht leeres Array von Benutzernamen als Strings | Ja | Jeder Benutzername muss zu einem Konto im Register der Sammlung gehören, ob aktiv oder nicht, und darf nur einmal vorkommen. | `authors = ["klehmann", "aschmidt"]` |
| `status` | Der Bearbeitungsstand. | String | Ja | Genau `draft`, `checked` oder `retired`. Eine deutsche Website zeigt *Entwurf*, *geprüft* oder *zurückgezogen*. | `status = "draft"` |
| `reaction_types` | Die festgelegte Reaktionsklasse. | String-Array | Ja | Genau ein Kürzel aus dem Vokabular `reaction-types` des Registers. | `reaction_types = ["esterification"]` |
| `tags` | Suchbegriffe. | Nicht leeres String-Array | Ja | Jedes Schlagwort besteht aus Kleinbuchstaben oder Ziffern mit einzelnen Bindestrichen zwischen den Gruppen. | `tags = ["acid-catalysed"]` |
| `products` | Die hergestellten Verbindungen mit ihren Ausbeuten. | Nicht leeres Array von Tabellen | Nur ohne `scope` | Jeder Eintrag enthält `compound` und `yield_percent`, wie unten beschrieben. | `products = [{ compound = "ethyl-acetate", yield_percent = 85 }]` |
| `scale` | Wie viel Produkt die Vorschrift liefert; bei einer allgemeinen Vorschrift die typische Ansatzgröße. | String | Ja | Eine Zahl, Leerraum und eine Einheit. Die Zahl darf einen Dezimalpunkt oder ein Dezimalkomma haben. Die Einheiten sind nicht festgelegt. | `scale = "2,5 mmol"` |
| `hazards` | Die wichtigsten Gefahren. | Nicht leeres Array nicht leerer Strings | Ja | Mindestens eine kurze Beschreibung. | `hazards = ["Entzündbare Flüssigkeit"]` |

Ein Datum mit anderem Versatz als dem Berliner bezeichnet trotzdem einen
genauen Zeitpunkt und ergibt deshalb nur eine Warnung. Ein Datum in
Anführungszeichen, ein Datum ohne Versatz oder ein bloßes Datum ist ein
Fehler. Der Validator vergleicht `date` und `lastmod` als Zeitpunkte,
einschließlich ihres Versatzes.

### Autoren

Verwenden Sie in `authors` die Benutzernamen der Laborkonten, jeden genau
einmal. Der Register-Snapshot, die gespeicherte Kopie des Laborregisters,
führt die Konten unter `accounts` auf. Jedes hat `username` und `name`,
seinen Anzeigenamen. Ersetzen Sie das `a.example` der Vorlage vor der
Prüfung durch Ihren Benutzernamen.

Wenn die zuständigen Mitarbeitenden ein Konto anlegen, muss dessen
Benutzername der Regel von Forgejo entsprechen: höchstens 40 Zeichen,
ASCII-Buchstaben und Ziffern mit einzelnen `.`, `-` oder `_` dazwischen.
Er muss mit einem Buchstaben oder einer Ziffer beginnen und enden. Nach
dem Anlegen des Kontos kann der Benutzername nicht mehr geändert werden;
die Verwaltung zeigt ihn schreibgeschützt an.

Die Website zeigt den Namen des Kontos wie gespeichert, einschließlich
der Groß- und Kleinschreibung. Die Links unter **Autoren** im Datenfeld
einer Vorschrift führen zu `/authors/<user name>/`, zum Beispiel
`/authors/klehmann/`. Das Autorenverzeichnis, die Autorenseiten und der
Filter **Autor** im Katalog zeigen ebenfalls die Namen der Konten.
`checked_by` ist eine getrennte, freie Liste von Namen.

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
einem Eintrag und Produkt in einem anderen sein. Zwei Einträge derselben
Vorschrift dürfen nicht dieselben Ausgangsstoffe und dieselben
Produktverbindungen haben. Beim Vergleich zählt nur, welche Verbindungen
jede Liste enthält. Reihenfolge und Ausbeuten unterscheiden die Einträge
nicht. So kann eine
Synthesewegstufe anhand der Verbindungen genau einen Eintrag auswählen.
Schreiben Sie `scope` in Markdown als Array von Tabellen in geschweiften
Klammern. Die
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

Vorschriften und Synthesewege teilen sich die Stoffe im Register der
Laboranwendung. Legen Sie Stoffe unter `/lab/registry/` in dieser Anwendung
an und bearbeiten Sie sie dort. Ein Verbindungsschlüssel ist der Schlüssel
eines Stoffs: Zwei Vorschriften meinen genau dann dieselbe Verbindung,
wenn sie denselben Schlüssel verwenden. Strukturen werden dafür nicht
verglichen. Ein Schlüssel entspricht `[a-z0-9]+(-[a-z0-9]+)*`:
Kleinbuchstaben und Ziffern mit einzelnen Bindestrichen zwischen den Gruppen,
etwa `ethyl-acetate`. Ein Stoff, den keine Vorschrift nennt, ist gültig.

Die Sammlung benennt ihr Register in `orgsyndb.toml`:

```toml
format = 1
registry = "http://localhost:8000/lab/registry/snapshot.json"
```

`registry` ist ein nicht leerer String. Er benennt eine mit `http://` oder
`https://` beginnende Adresse des Snapshots der Laboranwendung oder den
Pfad einer Snapshot-Datei. Ein Snapshot ist eine gespeicherte Kopie des
Laborregisters. Ein relativer Pfad beginnt im Ordner der Sammlung; absolute
Pfade sind ebenfalls erlaubt. Eine nicht leere Umgebungsvariable
`ORGSYNDB_REGISTRY` ersetzt die Einstellung. Die Beispielsammlung verwendet
`registry = "../../webapp/demo/registry.json"` und benötigt keine laufende
Laboranwendung. Verzeichnisse der Sammlung namens `compounds/` oder
`vocabularies/` werden ignoriert.

`orgsyndb validate`, `build`, `serve`, `pdf` und `index` lesen dieses Register.
Die ersten vier speichern den Snapshot in `build/registry.json` und seine
Quelle in `build/registry.source`; `index` schreibt nichts. Anfragen an eine
Adresse haben eine Zeitgrenze von 30 Sekunden. Ist die Adresse nicht lesbar
oder liefert sie keinen Snapshot, verwenden die Werkzeuge die gespeicherte
Kopie nur, wenn `build/registry.source` dieselbe Adresse nennt. Sie warnen mit:

```text
orgsyndb: warning: cannot read the registry: <address>: <reason>; using the copy in build/registry.json, digest <digest>
```

Ohne passende Kopie scheitert der Befehl mit einem Fehler, der die Adresse
nennt. Auch eine fehlende oder nicht lesbare Snapshot-Datei führt zum
Abbruch; für sie gibt es keinen Rückgriff auf eine andere Kopie.

Der Snapshot ist UTF-8-JSON im Format 1. Sein `digest` ist ein Fingerabdruck
des Inhalts. Er liefert die Vokabulare `chemical-classes`,
`inventory-groups`, `projects` und `reaction-types` sowie die Stoffe. Ein
Vokabular ist eine Liste erlaubter Begriffe. Die Website verwendet Namen,
Summenformel, Molmasse (`mw`, in g/mol), SMILES als Textschreibweise für
Molekülstrukturen, CAS-Registriernummer (`cas`), Artikelnummer, Kurzname,
Stoffklassen und Gruppe jedes Stoffs. Eine englische Website verwendet
`name`, eine deutsche `name_de`, falls vorhanden, sonst `name`. Ohne
Summenformel, Molmasse oder SMILES bleibt die jeweilige Zelle im Verzeichnis
leer. Der Stoff hat dann weder den entsprechenden Suchtext noch die Angabe
auf seiner Seite. Die Laboranwendung prüft die Werte der Stoffe; der
Validator der Sammlung prüft Verweise auf deren Schlüssel.

Für ein Strukturbild legen Sie `static/structures/<key>.svg` oder
`static/structures/<key>.png` in der Sammlung ab. Sind beide vorhanden,
verwendet der Build das SVG. Ohne eine dieser Dateien hat der Stoff kein
Bild. Es gibt kein Feld `structure_image` zum Ausfüllen. Der Build schreibt
je Stoff eine Datei `build/data/compounds/<key>.json` und setzt
`structure_image` in diesen erzeugten Daten nur, wenn er ein Bild findet.
Hugo liest die Dateien als `data/compounds`.

Das Argument `--static-dir` bestimmt, wo der Validator das `scheme_image`
einer Vorschrift sucht. Ohne Angabe nimmt er `static` im aktuellen
Verzeichnis. `orgsyndb validate` übergibt das `static/` der Sammlung. Bei
falschem Pfadanfang oder falscher Endung entfällt die Existenzprüfung.

Eine Verbindungsseite ergänzt nach **Verwendet in** den Abschnitt
**Synthesewege**, wenn Synthesewege diese Verbindung als Ziel nennen. Die
Liste verlinkt deren Titel, nach Nummer geordnet.

**Herstellungswege** ist der letzte Abschnitt der Verbindungsseite, nach
**Synthesewege**, sofern dieser Abschnitt vorhanden ist. Er zeigt Wege zur
Verbindung aus den veröffentlichten Vorschriften der Sammlung, einschließlich
der Vorschriften für ihre Ausgangsstoffe. Er erscheint nur, wenn ein Weg
über eine Stufe hinausgeht. Stellt keine Vorschrift einen der Ausgangsstoffe
her, deckt **Hergestellt nach** die verfügbaren Stufen bereits ab; der
Abschnitt **Herstellungswege** entfällt.

Der Baum besteht aus verschachtelten Listen. Unter einer Verbindung stehen
alternative Stufen: Eine davon genügt. Unter einer Stufe werden alle
aufgeführten Ausgangsstoffe benötigt. Jeder Ausgangsstoff verlinkt auf seine
Verbindungsseite; darunter stehen wiederum seine Herstellungsstufen, bis zu
Verbindungen, die keine Vorschrift herstellt. Die Verbindungslinks tragen
wie sonst auf der Website Artikelnummer und Kurzname des Stoffs, sofern
vorhanden.

Jede Stufe zeigt Nummer und Titel der Vorschrift, bei einer allgemeinen
Vorschrift die Eintragsnummer, Ausbeute und Status wie unter **Hergestellt
nach**. Die Stufen sind nach Vorschriftennummer geordnet, die Einträge einer
allgemeinen Vorschrift nach Eintragsreihenfolge. Jeder Eintrag ist eine
eigene Stufe und verwendet nur seine eigenen Ausgangsstoffe. Alle
veröffentlichten Vorschriften nehmen unabhängig vom Status teil; die
Statusmarkierung zeigt ihn an.

Beginnt eine Stufe mit einer Verbindung, die auf demselben Ast bereits
weiter oben steht, entfällt diese Stufe. So werden Kreise wie das Anbringen
und Entfernen einer Schutzgruppe nicht verfolgt. Würden alle Stufen einer
Verbindung zurückführen, erscheint sie ohne Stufen: Sie müssen sie anders
beschaffen.

Die Anzeige verwendet eine feste Tiefengrenze von 6 Stufen und ein festes
Budget von 200 Stufen pro Baum. Dies sind keine Sammlungseinstellungen. Ein
zu großer Baum wird bis zur größten Tiefe gezeigt, die noch passt. Stellen
mehr als 200 Stufen die Verbindung direkt her, zeigt der Baum nur diese.
Eine abgeschnittene Verbindung trägt den Zusatz **weitere Stufen auf ihrer
Seite**; folgen Sie ihrem Link, um den Weg fortzusetzen.

Der Build leitet die Herstellungswege automatisch ab. Dafür tragen Sie
nichts in eine Vorschrift oder `orgsyndb.toml` ein.
Verbindungsseiten bleiben außerhalb des Suchindex; die Herstellungswege
ändern die Suche daher nicht.

## Felddeklarationen der Sammlung

Um weitere Vorschriftenangaben wie Laborjournalverweise oder Projekte zu
erfassen, deklarieren Sie Felder in der `orgsyndb.toml` der Sammlung. Diese
UTF-8-TOML-Datei muss `format = 1` als Ganzzahl enthalten. Die anderen
erlaubten Schlüssel auf oberster Ebene sind `registry` und `fields`.
`registry` benennt den Snapshot wie unter
[Verbindungsregister](#verbindungsregister) beschrieben. `fields` ist eine
optionale Tabelle, deren einziger erlaubter Schlüssel `procedure` ist,
ein Array von Felddeklarationen. Ohne `fields` oder `fields.procedure`
deklariert die Sammlung keine weiteren Vorschriftenfelder.

Verbindungen haben vier fest eingebaute Registerfelder in dieser
Reihenfolge. Ihre Anzeige ist für jede Sammlung vorgegeben:

| Schlüssel | Wert des Stoffs | Typ und Vokabular | Feldname (Englisch / Deutsch) | Anzeige |
|---|---|---|---|---|
| `article_number` | Artikelnummer | Text | Article no. / Artikelnr. | Verzeichnisspalte, Suche, neben Links |
| `short_name` | Kurzname | Text | Short name / Kurzname | Suche, neben Links |
| `chemical_class` | `chemical_classes`, in ihrer Reihenfolge | Mehrfachauswahl, `chemical-classes` | Chemical class / Stoffklasse | Verzeichnisspalte, Filter |
| `group` | Gruppe | Einzelauswahl, `inventory-groups` | Group / Gruppe | Filter, Reiter |

Setzen Sie diese Werte in der Laboranwendung. Die Sammlung deklariert nur
Vorschriftenfelder; `fields.compound` ist ein Konfigurationsfehler.

### Schlüssel einer Deklaration

Die folgenden Tabellen beschreiben Vorschriftendeklarationen. Schreiben Sie
je Feld eine Tabelle `[[fields.procedure]]`; eine einzelne Tabelle
`[fields.procedure]` ist ungültig.

| Schlüssel | TOML-Typ | Pflicht oder Vorgabe | Regel |
|---|---|---|---|
| `key` | String | Pflicht | Entspricht `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`: Kleinbuchstaben und Ziffern, Wörter mit einzelnen Unterstrichen verbunden, mit einem Buchstaben beginnend. Darf nur einmal deklariert sein, nicht auf `_de` enden und keiner der unten aufgeführten reservierten Vorschriftenschlüssel sein. |
| `type` | String | Pflicht | `text`, `number`, `boolean` oder `choice`. |
| `label` | Nicht leerer String | Pflicht | Der Feldname auf einer englischen Website. |
| `label_de` | Nicht leerer String | Optional | Der Feldname auf einer deutschen Website; fehlt er, verwendet sie `label`. |
| `required` | Wahrheitswert | `false` | Bei `true` muss jede Vorschrift das Feld setzen, auch eine allgemeine Vorschrift. |

Nur die folgenden zusätzlichen Schlüssel sind je nach Typ erlaubt. Eine
Option bei einem anderen Typ ist ein Konfigurationsfehler.

| Schlüssel | Feldtyp | TOML-Typ | Pflicht oder Vorgabe | Regel |
|---|---|---|---|---|
| `pattern` | `text` | String | Optional | Ein gültiger regulärer Ausdruck in Python, dem der ganze Wert entsprechen muss. |
| `unique` | `text`, `number` | Wahrheitswert | `false` | Zwei Vorschriften dürfen nicht denselben gültigen Wert setzen; Sprachfassungen zählen als eine Vorschrift. |
| `min` | `number` | Ganz- oder Gleitkommazahl | Optional | Endliche untere Grenze, einschließlich; darf `max` nicht überschreiten, wenn beide gesetzt sind. Ein Wahrheitswert ist keine Zahl. |
| `max` | `number` | Ganz- oder Gleitkommazahl | Optional | Endliche obere Grenze, einschließlich. Ein Wahrheitswert ist keine Zahl. |
| `unit` | `number` | Nicht leerer String | Optional | Steht nach der Zahl, durch ein Leerzeichen getrennt. |
| `vocabulary` | `choice` | String | Pflicht | Benennt eines der Registervokabulare: `chemical-classes`, `inventory-groups`, `projects` oder `reaction-types`. |
| `multiple` | `choice` | Wahrheitswert | `false` | Bei `true` setzt die Vorschrift eine nicht leere Liste verschiedener Begriffsschlüssel statt eines einzelnen Strings. |
| `facet` | `boolean`, `choice` | Wahrheitswert | `false` | Bei `true` bieten die Vorschriftenkataloge das Feld als Filter an. |

### Felddeklarationen für Vorschriften

Um Laborjournalverweise, Projekte oder andere Vorschriftendaten zu erfassen,
schreiben Sie je Feld eine Tabelle `[[fields.procedure]]` in `orgsyndb.toml`,
in Anzeigereihenfolge. Ohne `fields.procedure` sind keine Vorschriftenfelder
deklariert. Die Beispielsammlung deklariert etwa:

```toml
[[fields.procedure]]
key = "notebook"
type = "text"
label = "Lab notebook"
label_de = "Laborjournal"
unique = true
pattern = '[A-Z]{2}-\d+/\d+'

[[fields.procedure]]
key = "project"
type = "choice"
label = "Project"
label_de = "Projekt"
vocabulary = "projects"
facet = true
```

Es gelten die obigen Deklarationsschlüssel, Typen und Vorgaben. Außerdem
gelten diese Regeln:

- `column`, `search`, `tabs` und `beside` sind nie erlaubt, auch nicht mit
  `false`.
- `required = true` verlangt das Feld in jeder Vorschrift, auch in allgemeinen
  Vorschriften. Die Vorgabe ist `false`.
- `unique = true` ist für `text` und `number` verfügbar und verbietet denselben
  gültigen Wert in zwei Vorschriften. Sprachfassungen einer Vorschrift zählen
  dabei als eine Vorschrift. Die Vorgabe ist `false`.
- `facet = true` ist für `boolean` und `choice` verfügbar und macht das Feld
  zum Filter der Vorschriftenkataloge. Die Vorgabe ist `false`.
- `key` muss `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` entsprechen, darf nicht auf `_de`
  enden und darf innerhalb von `fields.procedure` nur einmal vorkommen.
  Für Vorschriften sind diese Schlüsselgruppen reserviert:

  **Vorschriftenschema:** `id`, `slug`, `title`, `date`, `lastmod`, `authors`,
  `status`, `reaction_types`, `tags`, `products`, `scale`, `hazards`, `substrates`,
  `scope`, `scheme_image`, `checked_by`, `references`, `ai_model`, `language`,
  `draft`, `description`, `aliases`, `weight`, `author`, `url`.

  **Von Hugo gelesene Front-Matter-Schlüssel:** `build`, `cascade`,
  `expirydate`, `headless`, `iscjklanguage`, `keywords`,
  `kind`, `lang`, `layout`, `linktitle`, `markup`, `menu`, `menus`, `modified`,
  `outputs`, `params`, `path`, `pubdate`, `publishdate`, `published`,
  `resources`, `sitemap`, `sites`, `summary`, `translationkey`, `type`,
  `unpublishdate`, `authors_weight`, `reaction_types_weight`, `tags_weight`.

  **Vorschriftenkatalog:** `tag`, `created`, `text`, `q`, `sort`, `view`.

Auswahlfelder für Vorschriften verwenden die Begriffe des benannten
Registervokabulars. Eine Auswahl darf einen Begriff auf jeder Ebene dieses
Vokabulars benennen.

Setzen Sie Vorschriftenwerte als Schlüssel auf oberster Ebene im TOML-
Datenblock einer Markdown-Datei, vor jeder Tabelle. Die Aspirin-Vorschrift
der Beispielsammlung setzt nach `scale`:

```toml
notebook = "AE-1/2"
project = "first-year-practical"
working_time = 2.5
inert_atmosphere = false
```

Die Beispielsammlung deklariert `working_time` als `number` mit `unit = "h"`
und `min = 0`, `inert_atmosphere` als `boolean` mit `facet = true`. Keines
ihrer vier Vorschriftenfelder ist Pflicht. Eine neue Beispielvorschrift darf
sie weglassen; ein gesetztes `notebook` muss dem Muster entsprechen und noch
unvergeben sein.

Jede Markdown-Vorschrift und jeder Org-Export wird gegen die
Vorschriftendeklarationen geprüft. Wertfehler erscheinen am Vorschriftenpfad
unter dem Feldschlüssel und verwenden die
[Meldungen für Vorschriftenwerte](#vorschriftenwerte-und-meldungen), darunter
`required field missing` sowie Typ-, Muster-, Grenzwert- und Auswahllistenfehler.
Bei `unique` lautet die Meldung
`"<value>" is also set by <other procedure IDs>`; Zahlen erscheinen ohne
Anführungszeichen. Der Vergleich verwendet eine Bezugsfassung je
Vorschriftennummer und nur Werte, die ihre Feldprüfung bestehen. Eine Datei
mit nicht lesbarem Datenblock liefert keinen Wert. Alle Fassungen müssen
dieselben deklarierten Werte wiederholen; siehe
[Sprachen und Fassungen](#sprachen-und-fassungen). Die Org-Syntax und ihre
Grenze bei String-Werten stehen unter
[Org-Schlüsselwörter auf Dateiebene](#org-schlüsselwörter-auf-dateiebene).

### Vokabulare

Ein Vokabular enthält die erlaubten Begriffe eines Auswahlfeldes. Alle vier
Vokabulare kommen aus dem Register: `chemical-classes`, `inventory-groups`,
`projects` und `reaction-types`. Legen Sie Begriffe in der Laboranwendung
an und bearbeiten Sie sie dort. Eine Vorschrift speichert den Schlüssel
eines Begriffs; die Website zeigt seine Bezeichnung.

Jeder Begriff hat eine englische Bezeichnung `label` und kann eine deutsche
Bezeichnung `label_de` haben. Eine deutsche Website verwendet `label_de`,
falls vorhanden, sonst `label`. `chemical-classes`, `inventory-groups` und
`projects` dürfen mehrere Ebenen haben: `parent` benennt einen anderen
Begriff desselben Vokabulars, unter dem dieser Begriff eingeordnet ist.
Wer `parent` folgt, muss schließlich einen Begriff ohne übergeordneten
Begriff erreichen; kein Begriff darf sein eigener Vorfahr sein. Die Zahl
der Ebenen ist unbegrenzt. Auswahlfelder dürfen Begriffe auf jeder Ebene
wählen. Im Beispielregister ist etwa `esters` unter `acid-derivatives`
eingeordnet und dieses unter `carbonyl-compounds`. Reaktionstypen haben
nur eine Ebene.

Filter und Reiter zeigen jeden Begriff mit den darunter eingeordneten
Begriffen, jeweils wiederum mit deren untergeordneten Begriffen. Begriffe
auf gleicher Ebene unter demselben übergeordneten Begriff stehen in
Schlüsselreihenfolge. Die Auswahl eines übergeordneten Begriffs in einem
Filter erfasst auch Werte unter dessen untergeordneten Begriffen.

### Verbindungswerte und Meldungen

Die Laboranwendung prüft die Werte der Stoffe. Der Validator der Sammlung
meldet keine Feldwertfehler an einzelnen Stoffen.

Ein Stoff mit dem Schlüssel `group` kollidiert mit `/compounds/group/`, dem
Verzeichnis der Gruppenreiter. Die Laboranwendung lässt diesen Schlüssel
nicht zu; nur eine anders erzeugte Snapshot-Datei kann ihn enthalten. Der
Validator meldet einen Fehler am
Snapshot-Pfad, wie er an `--registry` übergeben wurde, unter `substances`:

```text
the substance "group" has the key of the directory of the compound tabs, /compounds/group/, which no substance may take
```

### Vorschriftenwerte und Meldungen

Setzen Sie deklarierte Vorschriftenfelder als Schlüssel auf oberster Ebene
im Datenblock. Wertprobleme sind Fehler am Pfad der Vorschriftendatei,
unter dem deklarierten Schlüssel:

| Feldtyp oder Regel | Meldung | Bedeutung |
|---|---|---|
| `required = true` | `required field missing` | Das Feld in jeder Vorschrift setzen, auch in einer allgemeinen Vorschrift. |
| `text`, einzelnes `choice` | `must be a string` | Den Wert in Anführungszeichen setzen. |
| `text` | `must not be empty` | Nicht leeren Text angeben. |
| `text` mit `pattern` | `must match the pattern <pattern>` | Der ganze String muss dem deklarierten Muster entsprechen. |
| `number` | `must be a number, unquoted` | Eine endliche TOML-Ganz- oder Gleitkommazahl ohne Anführungszeichen oder Einheit angeben; ein Wahrheitswert ist keine Zahl. |
| `number` mit `min` | `must be at least <min>` | Den Wert auf die untere Grenze oder darüber erhöhen. |
| `number` mit `max` | `must be at most <max>` | Den Wert auf die obere Grenze oder darunter verringern. |
| `boolean` | `must be true or false, unquoted` | `true` oder `false` ohne Anführungszeichen verwenden. |
| `choice` | `unknown value "<v>" of the vocabulary <name>` | Einen Begriffsschlüssel aus dem benannten Registervokabular verwenden, auf beliebiger Ebene. |
| `choice` mit `multiple = true` | `must be a list of strings, e.g. ["<a term>"]` | Eine Liste von Begriffsschlüsseln in Anführungszeichen angeben. Das Beispiel nennt den ersten Begriff im Snapshot oder `a term`, wenn das Vokabular leer ist. |
| `choice` mit `multiple = true` | `must not be empty` | Mindestens einen Auswahlwert angeben. |
| `choice` mit `multiple = true` | `repeats "<v>"` | Den wiederholten Wert entfernen. |
| `unique = true` | `"<value>" is also set by <other procedure IDs>` | Einen Wert verwenden, den keine andere Vorschrift setzt. Zahlen stehen in der Meldung ohne Anführungszeichen. |

Ein Wert mit falschem Typ ergibt nur diesen Typfehler. Leerer Text mit
einem Muster ergibt nur `must not be empty`. Eine Auswahlliste ergibt
eine Meldung `unknown value` je unbekanntem String. Die
Eindeutigkeitsprüfung vergleicht Werte, die ihre Feldprüfung bestehen,
und meldet jede Vorschrift, die denselben Wert setzt. Sie verwendet dabei
eine Bezugsfassung je Vorschriftennummer.

### Konfigurationsfehler

Der Validator lehnt Einstellungen ab, die eine Deklarationsregel verletzen.
Dazu zählen ungültige reguläre Ausdrücke, nicht endliche Grenzen, `min`
größer als `max` und doppelte Deklarationen. Eine mit `--settings`
ausdrücklich benannte Datei muss vorhanden sein. Einstellungen müssen als
UTF-8-TOML lesbar sein. Eine Registerdatei muss vorhanden und als UTF-8-JSON
lesbar sein und einen Snapshot im Format 1 mit den vier Vokabularen und
einer Stoffliste enthalten. Enthält er `accounts`, muss dieser Wert eine
Liste von Tabellen sein, jede mit einem nicht leeren String `username`
und einem String `name`. Kein Benutzername darf mehrfach vorkommen. Ein
Snapshot ohne `accounts` führt keine Konten auf; damit lässt sich kein
Vorschriftenautor einem Konto zuordnen.

Dies sind Konfigurationsfehler: Rückgabewert 2, keine Standardausgabe
und `validate.py: error: ...` auf der Standardfehlerausgabe. Die Meldungen
nennen die Einstellungs- oder Registerdatei, den Feldschlüssel, sofern
gültig, und den beanstandeten Schlüssel oder Wert. Eine Option für einen
anderen Typ ergibt etwa `a number field does not take pattern`; eine
unbekannte Option ergibt `unknown key <key>`. Ein unbekannter Schlüssel
auf oberster Ebene der Einstellungen ergibt
`unknown key <key>; only format, registry, fields are allowed`.

`fields` erlaubt nur `procedure`. Ein Eintrag wie `fields.compound` oder
`fields.reagent` ergibt
`unknown key fields.<key>; only fields.procedure is allowed: a collection declares the fields of its procedures, and its compounds have the registry's`.
Eine einzelne Tabelle `[fields.procedure]` ergibt
`fields.procedure must be an array of tables, each written [[fields.procedure]]`.

| Problem | Meldung oder kennzeichnender Text |
|---|---|
| Fehlende Registerdatei | `registry file not found` |
| Register ist kein JSON | `not UTF-8 JSON: <reason>` |
| Register ist kein Snapshot | `not a registry snapshot: <reason>` |
| Ungültige Einstellung `registry` | `registry must be the address of the lab application's registry snapshot or the path of a snapshot file, a non-empty string` |
| Fehlendes Auswahlvokabular | `vocabulary missing; a choice field names one of the registry's vocabularies, chemical-classes, inventory-groups, projects, reaction-types` |
| Unbekanntes Auswahlvokabular | `vocabulary '<name>' is not one of the registry's vocabularies, chemical-classes, inventory-groups, projects, reaction-types` |
| Nicht erlaubte Option | `a procedure field does not take column` (oder `search`, `tabs`, `beside`), auch bei `false` |
| Schlüssel des Vorschriftenschemas | `declaration 5 of fields.procedure: key 'status' is a key of the procedure schema` |
| Hugo-Schlüssel | `declaration 5 of fields.procedure: key 'layout' is a front-matter key that Hugo reads` |
| Katalogschlüssel | `declaration 5 of fields.procedure: key 'tag' is reserved by the procedure catalogue; the reserved keys are tag, created, text, q, sort, view` |

Die Deklarationsnummer ist die Position innerhalb von `fields.procedure`.
Schlüsselfehler, auch doppelte oder falsch geschriebene Schlüssel, nennen
`fields.procedure`. Fehlerhafte Snapshots nennen das beanstandete Vokabular,
den Begriff, den Stoff oder das Konto. Diese Prüfungen betreffen Aufbau
und Typen des Snapshots, nicht die Werte der Stoffe.

Befehle, die das Register lesen, benötigen außerdem eine Registerquelle.
Ohne `registry` oder eine nicht leere Umgebungsvariable `ORGSYNDB_REGISTRY`
melden sie
`no registry named; set registry to the address of the lab application's registry snapshot`,
gefolgt von einer Beispieladresse und den Möglichkeiten, einen Dateipfad
oder die Umgebungsvariable zu verwenden. Eine nicht lesbare Adresse ohne
passende gespeicherte Kopie ergibt
`cannot read the registry: <address>: <reason>; there is no copy of it in build/registry.json`.

Vor einem Befehl prüft das Build-Programm das TOML der Einstellungsdatei,
`format`, die Schlüssel auf oberster Ebene und den Wert von `registry`.
Der Validator prüft die Vorschriftendeklarationen. Eine fehlerhafte
Deklaration verhindert daher weder `clean` noch `new`.

### Anzeige auf der Website

Vorschriftenseiten zeigen jedes gesetzte deklarierte Vorschriftenfeld im
Datenfeld, in Deklarationsreihenfolge nach **Geprüft von** und vor **Erstellt**.
Eine deutsche Website verwendet `label_de`, falls vorhanden, sonst `label`.
Text erscheint wie eingetragen, Zahlen mit dem Dezimalzeichen der Website
und der Einheit, etwa `2,5 h`. Wahrheitswerte erscheinen als **Ja**/**Nein**,
auf Englisch als **Yes**/**No**. Auswahlwerte zeigen den Pfad ihrer Namen,
verbunden durch ` › `, etwa **Lehre › Grundpraktikum**. Mehrere Auswahlwerte
stehen mit `, ` getrennt in der Reihenfolge der Vorschrift. Das Datenfeld
wird indexiert; die Katalogsuche findet diese angezeigten Werte.

Jedes Vorschriftenfeld vom Typ `boolean` oder `choice` mit `facet = true`
ergänzt einen Filter zwischen **Status** und **Schlagwort**, in
Deklarationsreihenfolge, anfangs geöffnet und ohne Link „Alle Werte“.
Wahrheitsfilter zeigen zuerst **Ja**, dann **Nein**, jeweils nur, wenn eine
veröffentlichte Vorschrift den Wert setzt. Auswahlfilter zeigen verwendete
Werte und deren übergeordnete Werte als eingerückten Baum in
Vokabularreihenfolge. Die Auswahl eines übergeordneten Werts erfasst auch
Vorschriften unter den darunter eingeordneten Werten. Diese Filter stehen
unter `/procedures/`, auf jeder Reaktionstyp-, Schlagwort- und Autorenseite
sowie unter `/general-procedures/`. Jede Seite bietet Werte der gesamten
Sammlung an. Die Adresse verwendet den deklarierten Schlüssel, etwa
`/procedures/?project=research&inert_atmosphere=true`. Es gelten dieselben
ODER/UND- und Zählregeln wie für die Verbindungsfilter unten.
Vorschriftenfelder ergänzen keine Tabellenspalten, Werte in der Ansicht
**Details** oder Reiter.

Verbindungsseiten zeigen die vier fest eingebauten Felder nach Summenformel,
Molmasse, CAS und SMILES. Fehlende Werte erscheinen nicht. Die Reihenfolge
ist **Artikelnr.**, **Kurzname**, **Stoffklasse**, **Gruppe**, auf einer
englischen Website **Article no.**, **Short name**, **Chemical class**,
**Group**. Artikelnummern und Kurznamen erscheinen wie eingetragen.

Die Werte für Artikelnummer und Kurzname stehen nach den Verbindungslinks
unter **Produkt**/**Produkte** und **Ausgangsstoffe** im Datenfeld, in der
Tabelle zum Anwendungsbereich einer allgemeinen Vorschrift, im Schema einer
Synthesewegseite, beim Ziel im Synthesewegverzeichnis und in den
Herstellungswegen auf Verbindungsseiten. Der Linktext bleibt der
Verbindungsname. Nach einem Leerzeichen folgt ein Zusatz in Klammern und
gedeckter Farbe, in der Beispielsammlung etwa
**Essigsäureanhydrid (Ac2O)** oder **Acetylsalicylsäure (CH-0010, ASA)**.
Er enthält nur die Werte, die der Stoff hat, zuerst die Artikelnummer,
ohne Feldnamen, durch `, ` getrennt. Hat ein Stoff keinen dieser Werte,
entfällt der Zusatz. Die Angaben unter dem Titel, die Katalogansicht
**Details**, Alternativtexte von Bildern und Seitentitel tragen keinen
Zusatz. Das Datenfeld wird indexiert; daher findet die Vorschriftensuche
auch diese Werte.

Ein Auswahlwert auf einer Verbindungsseite zeigt die Namen seiner
übergeordneten Werte und seinen eigenen Namen, verbunden durch ` › `,
etwa **Carbonylverbindungen › Carbonsäurederivate › Ester**. Mehrere
Stoffklassen sind durch `, ` getrennt, in der Reihenfolge des Stoffs.
Das Verbindungsverzeichnis ergänzt **Artikelnr.** und **Stoffklasse** nach
CAS. Es zeigt nur den eigenen Namen jeder Stoffklasse und lässt ungesetzte
Werte als leere Zellen.

`/compounds/` und jede Gruppenreiterseite beginnen mit einer Reiterzeile,
wie im Bereich **Vorschriften**. **Alle Verbindungen** (auf Englisch
**All compounds**) verlinkt `/compounds/`. Danach folgen die Bezeichnungen
der Begriffe auf der obersten Ebene des Vokabulars `inventory-groups`, in
Schlüsselreihenfolge. Ein Begriff erscheint nur, wenn ein Stoff ihn oder
einen darunter eingeordneten Begriff verwendet. Der Reiter der aktuellen
Seite ist markiert.

Eine Reiterseite liegt unter `/compounds/group/<value>/`; Überschrift und
Seitentitel sind die Bezeichnung des Werts. Sie listet nach Namen geordnet
die Stoffe, die diesen Wert oder einen darunter eingeordneten Wert setzen.
Anzahl, Filter und Suche beziehen sich auf diese Liste und funktionieren
wie unter `/compounds/`. Die Beispielsammlung hat die Seiten **Zugekauft**
unter `/compounds/group/purchased/` und **Selbst hergestellt** unter
`/compounds/group/synthesised/`, mit zehn beziehungsweise elf Stoffen.

Auf einer Reiterseite zeigen die Filter nur Werte ihrer Stoffe.
Der Filter **Gruppe** lässt den Wert des Reiters weg und rückt die darunter
eingeordneten Werte um eine Ebene nach oben. Ein Filter ohne Werte entfällt.
Die Suche im Kopf heißt **Verbindungen durchsuchen: \<label\>** (auf Englisch
**Search compounds: \<label\>**). Reiterlinks übernehmen weder Suchtext noch
Filter. Ohne JavaScript zeigt eine Reiterseite ihre vollständige Liste.

Unter `/compounds/` ist das Verzeichnis ein durchsuchbarer, filterbarer
Katalog aller Registereinträge. Die Zeilen bleiben nach dem angezeigten
Namen in der Sprache der Website geordnet. **Stoffklasse** und **Gruppe**
erscheinen als Filter in dieser Reihenfolge. Jeder zeigt die von Stoffen
verwendeten Werte und deren übergeordnete Werte als eingerückten Baum.
Auf jeden Begriff folgen seine untergeordneten Begriffe; Begriffe mit
demselben übergeordneten Begriff stehen in Schlüsselreihenfolge. Wählen Sie
einen übergeordneten Wert, erfasst der Filter auch Verbindungen unter dessen
untergeordneten Werten: **Carbonylverbindungen** schließt Ketone und Ester ein.

Ausgewählte Werte innerhalb eines Filters sind mit ODER verknüpft,
verschiedene Filter mit UND. Die Anzahl neben einem Wert berücksichtigt
die Suche und alle anderen Filter, jedoch nicht die Auswahl im eigenen
Filter. Ausgewählte Werte erscheinen als einzeln entfernbare Schaltflächen;
**Alles zurücksetzen** löscht Suchtext und Auswahl. Der Katalog zeigt die
Gesamtzahl oder beim Filtern **{shown} von {total} Verbindungen**.

Das Suchfeld **Verbindungen durchsuchen** im Kopf berücksichtigt englische
und deutsche Namen, Summenformel, CAS-Nummer, SMILES, Artikelnummer und
Kurzname. Jedes Suchwort muss als Teil einer Zeichenfolge
vorkommen. Dabei zählen weder Groß- und Kleinschreibung noch Zeichen außer
Buchstaben und Ziffern. Suchangaben wie `50-78-2`, `salicyl` und `c1ccccc1O`
funktionieren ohne Pagefind-Index. Außerhalb dieser Kataloge, auch auf
einzelnen Verbindungsseiten, durchsucht das Feld Vorschriften;
Verbindungsseiten bleiben außerhalb des Suchindex für Vorschriften.

Die Adresse hält Suchtext und Auswahl fest, etwa
`/compounds/?q=ester&chemical_class=esters&group=final-products`. Parameter,
die die Seite nicht anwenden kann, nennt sie in einem Hinweis und entfernt
sie aus der Adresse. Suche und Filter brauchen JavaScript. Ohne JavaScript zeigt
die Seite die vollständige Tabelle und einen entsprechenden Hinweis.

## Synthesewege

Ein Syntheseweg hält eine geordnete Folge von mindestens zwei Vorschriften
fest. Schreiben Sie ihn in Markdown, auch wenn seine Stufen Org-Vorschriften
verwenden. Kopieren Sie [templates/sequence.md](../templates/sequence.md) nach
`md/sequences/` der Sammlung. `orgsyndb init` legt diesen Ordner an; ein
fehlender Ordner enthält keine Synthesewege. `orgsyndb new` erzeugt
Vorschriften, daher kopieren Sie die Vorlage für Synthesewege von Hand.

Ein Syntheseweg hält den Weg fest, den Ihre Gruppe durchführt. Den Baum
**Herstellungswege** auf der Verbindungsseite leitet die Website aus den
Vorschriften der Sammlung ab.

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
`unknown field`. Eine Stufe erlaubt nur `procedure`, `product`, `substrates`
und `products`. `entry` ist ein Fehler; jedes andere unbekannte Feld einer
Stufe ergibt eine Warnung unter `steps[n].<key>`.

| Feld | TOML-Typ | Pflicht | Regel | Beispiel |
|---|---|---|---|---|
| `id` | String | Ja | `SEQ-0001` bis `SEQ-9999`; einmal je Sprachkürzel und einmal ohne Kürzel eindeutig. | `id = "SEQ-0001"` |
| `slug` | String | Ja | Genau die `id` in Kleinbuchstaben. | `slug = "seq-0001"` |
| `title` | Nicht leerer String | Ja | Seitentitel. | `title = "Aspirin aus Wintergrünöl"` |
| `date` | Datum mit Zeitzonenversatz | Ja | Ohne Anführungszeichen; dieselben Regeln wie bei Vorschriften. | `date = 2026-10-23T09:15:00+02:00` |
| `lastmod` | Datum mit Zeitzonenversatz | Ja | Dieselben Regeln wie für `date`; nicht früher als `date`. | `lastmod = 2026-10-23T09:40:00+02:00` |
| `target` | String | Ja | Vorhandener Stoffschlüssel im Register; ein Produkt der letzten Stufe. | `target = "acetylsalicylic-acid"` |
| `steps` | Array von Tabellen | Ja | Mindestens zwei Stufen, in Ausführungsreihenfolge. | `steps = [{ procedure = "OSDB-0001" }, { procedure = "OSDB-0002" }]` |
| `steps[n].procedure` | String | In jeder Stufe | Vorschriftennummer aus den geprüften Inhaltsverzeichnissen, aus Org exportiert oder in Markdown geschrieben. | `procedure = "OSDB-0009"` |
| `steps[n].product` | String | Bei allgemeinen Vorschriften, sofern nicht beide folgenden Listen angegeben sind | Ein Verbindungsschlüssel, der in genau einem Scope-Eintrag dieser Vorschrift als Produkt vorkommt. Bei Einzelvorschriften verboten. | `product = "1-biphenyl-4-yl-ethanol"` |
| `steps[n].substrates` | String-Array | Zusammen mit `products`, wenn beide Listen den Eintrag auswählen | Alle Ausgangsstoffschlüssel des gewählten Eintrags, in beliebiger Reihenfolge, ohne Wiederholungen. Bei Einzelvorschriften verboten. | `substrates = ["4-acetylbiphenyl"]` |
| `steps[n].products` | String-Array | Zusammen mit `substrates`, wenn beide Listen den Eintrag auswählen | Alle Schlüssel der Produktverbindungen des gewählten Eintrags, in beliebiger Reihenfolge, ohne Wiederholungen. Bei Einzelvorschriften verboten. | `products = ["1-biphenyl-4-yl-ethanol"]` |

Wählen Sie bei einer allgemeinen Vorschrift den Eintrag mit `product` aus.
Kommt das Produkt in mehreren Einträgen vor, geben Sie stattdessen sowohl
`substrates` als auch `products` an. Die Listen müssen die Verbindungen
eines Eintrags vollständig wiedergeben. In einer Stufe ist `products` eine
Liste von Verbindungsschlüsseln ohne Ausbeuten. Kombinieren Sie `product`
mit keiner der beiden Listen. Eine Einzelvorschrift erhält nur `procedure`.

Schreiben Sie nach der schließenden `+++`-Zeile Anmerkungen, etwa unter
`## Anmerkungen`. Die acht Textabschnitte einer Vorschrift sind nicht
vorgeschrieben. [SEQ-0002 der
Beispielsammlung](../examples/demo/md/sequences/SEQ-0002-biphenylyl-ethanol.de.md)
zeigt eine Stufe mit einer allgemeinen Vorschrift:

```toml
target = "1-biphenyl-4-yl-ethanol"
steps = [{ procedure = "OSDB-0004" }, { procedure = "OSDB-0009", product = "1-biphenyl-4-yl-ethanol" }]
```

Wenn Sie die Scope-Tabelle einer Vorschrift umordnen, führt der Syntheseweg
weiterhin dieselben Reaktionen aus. Der Build ermittelt die Nummer des
gewählten Eintrags für die Synthesewegseite und das Manifest. Die Zählung
beginnt bei 1 und folgt der Reihenfolge in der Datei.

### Zusammenhang der Stufen, Fassungen und Ausbeute

Jede Stufe nach der ersten muss mindestens ein Produkt der vorigen Stufe als
Ausgangsstoff verwenden. Bei einer allgemeinen Vorschrift zählen nur die
Ausgangsstoffe und Produkte des gewählten Eintrags. Das Ziel muss ein Produkt
der letzten Stufe sein. Der Validator prüft diesen Zusammenhang nur an der
Bezugsfassung: der Datei ohne Sprachkürzel, sonst `.de`, sonst `.en`. Dafür
müssen mindestens zwei Stufentabellen vorliegen. Eine Stufe mit unbekannter
Vorschrift, nicht bestimmbarem Eintrag oder Feldern zur Eintragsauswahl bei
einer Einzelvorschrift bleibt bei der Zusammenhangsprüfung unberücksichtigt.
Die Zielprüfung setzt zusätzlich einen bekannten Verbindungsschlüssel voraus.

Fassungen teilen Grundnamen, `id`, `slug`, `target` und die geordneten `steps`.
Die Stufen müssen genau wie geschrieben übereinstimmen, einschließlich der
Reihenfolge innerhalb der Listen `substrates` und `products`. Für die Auswahl
des Eintrags spielt diese Reihenfolge dagegen keine Rolle.
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
| `author = ["klehmann"]` | Das Schema verwendet die Mehrzahl; die Fehlermeldung lautet `use authors, a list of user names`. | `authors = ["klehmann"]` |
| `url = "/procedures/osdb-0001/"` | Die URL ergibt sich aus `slug`. | `slug = "osdb-0001"` |

Ein unter `fields.procedure` deklarierter Schlüssel wird als
Vorschriftenfeld geprüft und ergibt keine Warnung `unknown field`.

Jedes andere Feld der obersten Ebene ergibt die Warnung `unknown field`,
auch Tippfehler wie `checkedby` und die Felder `product`, `yield_percent`
auf oberster Ebene, `precursors` und `structure_image`. Ein unbekanntes Feld
in einem Eintrag von `products` ergibt etwa `products[1].colour` als Warnung.

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

Setzen Sie deklarierte Vorschriftenfelder auf weiteren Zeilen
`#+HUGO_CUSTOM_FRONT_MATTER:` vor `:products`, etwa nach `:scale`:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :notebook "AE-1/1" :project "first-year-practical" :working_time 3 :inert_atmosphere false
```

Strings stehen in doppelten Anführungszeichen; Zahlen und Wahrheitswerte
bleiben ungequotet. Eine Mehrfachauswahl verwendet eine gequotete Liste,
etwa `:project '("first-year-practical" "advanced-practical")`, wenn die
Sammlung `project` mit `multiple = true` deklariert und das Vokabular
`projects` des Beispielregisters verwendet.

Der Export mit ox-hugo/tomelr erhält nicht jeden gequoteten String als Text.
Er schreibt einen String ohne Anführungszeichen, wenn er `true` oder `false`
lautet, die Form eines Datums oder Datums mit Uhrzeit hat (`2026-01-01`,
`2026-01-01T10:00:00+01:00`) oder eine Ganzzahl ist: ein optionales Vorzeichen,
gefolgt von Ziffern und Unterstrichen (`1234`, `-7`, `7_000`, `0012`). Das
gilt auch für gequotete Quellwerte und Listeneinträge. Solche Werte sind in
Org-Quellen weder als Text noch als Schlüssel einer Einfach- oder
Mehrfachauswahl verwendbar. Die Prüfung meldet `must be a string`, oder der
exportierte Datenblock ist nicht lesbar; etwa ist ungequotetes `0012`
ungültiges TOML. Wenn Autoren Org verwenden, wählen Sie Muster und
Vokabularschlüssel, die diese Formen vermeiden. Markdown-Quellen haben
diese Einschränkung nicht.

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

`reaction_types` enthält genau ein Kürzel, einen Schlüssel wie
`esterification`, aus dem Vokabular `reaction-types` des Registers.
Verwenden Sie in jeder Sprache dasselbe Kürzel im Datenblock. Legen Sie
Reaktionstypen in der Laboranwendung an und bearbeiten Sie sie dort.
Eine Vorschrift mit einem Schlüssel, den das Register nicht enthält,
besteht die Prüfung nicht und erhält diese Meldung:

```text
unknown reaction type "<value>"; the registry has no such reaction type
```

Das Beispielregister enthält diese Reaktionstypen:

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

Eine englische Website zeigt `label` des Begriffs. Eine deutsche Website
zeigt `label_de`, falls vorhanden, sonst `label`. Die Liste unter
`/reaction_types/` und der Reaktionstypfilter des Katalogs sortieren nach
der angezeigten Bezeichnung. Reaktionstypen haben nur eine Ebene.

Enthält das Register keine Reaktionstypbegriffe, hat die Sammlung keine
Reaktionstypen. Der Reaktionstyp jeder Vorschrift ist dann unbekannt.
Eine Sammlung, die nur Stoffe enthält, besteht die Prüfung weiterhin.
Ein deklariertes Auswahlfeld für Vorschriften darf
`vocabulary = "reaction-types"` wie jedes andere Registervokabular benennen.
Ein fehlerhafter Snapshot ist ein Konfigurationsfehler; sowohl
`orgsyndb validate` als auch `build` scheitern daran.

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
  `tags`, `products`, `substrates`, `scope`, `scheme_image` und jedem
  deklarierten Vorschriftenfeld;
- dürfen `note` in jedem Eintrag von `scope` übersetzen; alle anderen Werte von
  `scope` und die Reihenfolge der Einträge müssen übereinstimmen;
- dürfen sich in allen übrigen Feldern und im Text unterscheiden: `title`,
  `scale`, `hazards`, `references`, `authors`, `checked_by`, `ai_model`,
  `language`, `date` und `lastmod`.

Auch bei abweichenden `authors` muss jeder Benutzername genau einmal
vorkommen und zu einem Konto im Register-Snapshot der Sammlung gehören.

Der Validator vergleicht jede Fassung mit einer Bezugsfassung: der Datei ohne
Kürzel, sonst der `.de`-Datei. Jede Abweichung ist ein Fehler an der anderen
Fassung, der die Bezugsfassung nennt. Ein geänderter Produktschlüssel oder eine
geänderte Ausbeute erscheint unter `products`, eine geänderte Liste der
Ausgangsstoffe unter `substrates`. Abweichungen in `scope` erscheinen unter
`scope`, ohne Vergleich der Anmerkungen; ein geänderter Schemapfad unter
`scheme_image`. Zahlen werden nach ihrem Wert verglichen: `85` und `85.0`
stimmen überein. Bei anderen Werten müssen Wert und Typ übereinstimmen.

Bei einem deklarierten Vorschriftenfeld ergeben ein geänderter Wert, ein
fehlender oder ein hinzugefügter Schlüssel einen Fehler unter diesem Schlüssel:
`must equal the value in <path of the reference variant> (<value>); the variants of a procedure share it`.
Wiederholen Sie Werte ohne Übersetzung. Der angezeigte Feldname kommt auf
einer deutschen Website aus `label_de`, falls vorhanden.

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
Produktausbeuten in `products` oder `scope` und Temperaturen in `scope`
bleiben in jeder Sprache TOML-Zahlen mit Dezimalpunkt; eine deutsche Website
zeigt sie mit Komma. Die Molmasse kommt aus dem Register und verwendet
auf der Website ebenfalls deren Dezimalzeichen.

## Meldungen des Validators lesen

Starten Sie den Validator mit mindestens einem Markdown-Verzeichnis:

```text
tools/validate.py [--settings FILE] [--static-dir DIR] [--registry FILE] [--sequences DIR] CONTENT_ROOT...
```

Jedes `CONTENT_ROOT` ist ein Verzeichnis mit Markdown-Vorschriften.
Ohne Angabe ist `--static-dir` gleich `static` im aktuellen Verzeichnis.
Der Validator sucht das `scheme_image` einer Vorschrift darunter.
`--registry` ist ohne Angabe `build/registry.json` im aktuellen Verzeichnis.
Die Option erwartet eine Snapshot-Datei, keine Adresse. Der Validator prüft
Verbindungsschlüssel der Vorschriften und Synthesewege, Benutzernamen der
Autoren, Reaktionstypen und deklarierte Vorschriftenwerte gegen diesen
Snapshot. Er prüft keine Werte der Stoffe. Eine nicht lesbare Datei oder
eine Datei, die kein Snapshot ist, ergibt einen Konfigurationsfehler mit
Rückgabewert 2. `--compounds` und
`--vocabulary` werden nicht akzeptiert; beide ergeben einen Aufruffehler,
ebenfalls mit Rückgabewert 2.

`orgsyndb validate` liest das von der Sammlung benannte Register ein,
speichert es in `build/registry.json`, exportiert die Org-Quellen und
übergibt dann
`--settings orgsyndb.toml --static-dir static --registry build/registry.json --sequences md/sequences`
sowie die vorhandenen Vorschriftenverzeichnisse `build/export` und
`md/procedures` aus dem Hauptordner der Sammlung.

`--settings` benennt die `orgsyndb.toml` der Sammlung. Ohne diese Option
verwendet der Validator `orgsyndb.toml` im aktuellen Verzeichnis; fehlt
diese Vorgabedatei, sind keine weiteren Felder deklariert. Eine mit
`--settings` ausdrücklich benannte Datei muss vorhanden sein. Der
Validator prüft die Vorschriftendeklarationen gegen die vier
Registervokabulare und danach die deklarierten Werte jeder Vorschrift.
Org-Vorschriften erreichen diese Prüfung als Markdown-Exporte.

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
keine Tabelle ist, erscheint unter `products[n]`. Ein Registerfehler nennt
den Snapshot-Pfad, wie er an `--registry` übergeben wurde, und das Feld
`substances`: Ein Stoff mit dem Schlüssel `group` kollidiert mit den
Gruppenreitern.
Die Laboranwendung lässt diesen Schlüssel nicht zu; die Snapshot-Datei
wurde also anders erzeugt. Geben Sie dem Stoff dort einen anderen Schlüssel.
Weitere mögliche Felder sind `file_name`,
`front_matter`, `toml` und `body`. Die Meldungen sind englisch.

Autorenfehler erscheinen unter `authors`:

| Meldung | Korrektur |
|---|---|
| `must be a list of user names, e.g. ["a.example"]` | Eine Liste von Benutzernamen der Laborkonten in Anführungszeichen angeben. |
| `must not be empty` | Mindestens einen Autor nennen. |
| `unknown author "<name>"; the registry has no account of this user name` | Den Benutzernamen prüfen und sicherstellen, dass der Register-Snapshot der Sammlung das Konto aufführt. |
| `"<name>" is named twice` | Jeden Benutzernamen nur einmal behalten. |

Fehler deklarierter Vorschriftenfelder nennen die Markdown-Quelle oder
den Org-Export und den deklarierten Schlüssel, etwa `notebook` oder `project`.
Typ-, Muster-, Grenzwert- und Auswahlmeldungen stehen unter
[Felddeklarationen für Vorschriften](#felddeklarationen-für-vorschriften).
`also set by` nennt andere Vorschriftennummern; `must equal the value in`
nennt die sprachliche Bezugsfassung, deren Wert Sie wiederholen müssen.

Felder eines Eintrags heißen `scope[n].<key>`, Produktfelder darin
`scope[n].products[m].<key>`. Beide Zählungen beginnen bei 1. Ein Eintrag, der
keine Tabelle ist, erscheint unter `scope[n]`. Ein unbekanntes Feld in einem
Eintrag ergibt eine Warnung `unknown field` unter dem vollen Feldnamen.

| Feld | Meldung | Bedeutung |
|---|---|---|
| `products` oder `substrates` | `a general procedure lists them in scope; move <key> into its entries` | Feld auf oberster Ebene entfernen und Daten den passenden Einträgen zuordnen. |
| `scope` | `must not be empty` | Mindestens einen Eintrag angeben. |
| `scope[n]` | `has the same substrates and products as entry <m>` | Nur einen Eintrag für diese Kombination von Ausgangsstoffen und Produktverbindungen behalten; eine andere Reihenfolge oder andere Ausbeuten unterscheiden die Einträge nicht. |
| `scope` oder `scope[n]` | `must be an array of tables` oder `must be a table` | TOML-Form korrigieren; die Meldung zeigt auch ein Beispiel. |
| `scope[n].time` | `"<value>" must be a number followed by min, h or d, e.g. "2 h"` | Eine Zahl mit einer der drei Einheiten angeben. |
| `scope[n].temperature` | `must be a number in °C, unquoted, e.g. 80` | Anführungszeichen und Einheit entfernen; eine endliche Zahl verwenden. |

Fehlende Pflichtfelder, doppelte Schlüssel, unbekannte Verbindungen und
ungültige Ausbeuten verwenden die folgenden Produkt- und Ausgangsstoffmeldungen
unter dem jeweiligen Feld in `scope`.

Bei `products` bedeutet `must not be empty`, dass Sie mindestens einen
Eintrag angeben müssen. `must be an array of tables` oder
`must be a table` bezeichnet eine falsche TOML-Form. `required field missing` nennt ein fehlendes Feld.
Ein unbekannter Schlüssel ergibt
`unknown compound "<key>"; the registry has no substance of this key`.
Prüfen Sie die Schreibweise und den Stoff in der Laboranwendung.
`lists <key> twice` bezeichnet ein doppelt genanntes Produkt oder einen
Ausgangsstoff; `<key> is also a product` bedeutet,
dass ein Ausgangsstoff auch als Produkt aufgeführt ist.

`orgsyndb export` schreibt Probleme der Org-Quellen in derselben Zeilenform
auf die Standardausgabe. Seine Felder können auch Org-Schlüsselwörter wie
`#+CREATED`, Eigenschaften wie `#+PROPERTY` oder `:EXPORT_DATE:` und
Schubladen wie `:LOGBOOK:` sein.

Ein `error` bedeutet, dass eine Vorschrift, ein Syntheseweg oder das
Register ungültig ist. Eine `warning`
bezeichnet ein Problem, das die Prüfung nicht scheitern lässt, etwa einen
fehlenden Abschnitt oder ein unbekanntes Feld. Nach den Problemzeilen
schreibt der Validator eine Zusammenfassung auf die Standardfehlerausgabe.
Die Dateizahl umfasst Vorschriften und Synthesewegdateien einschließlich
aller Sprachfassungen; Stoffe und die Snapshot-Datei werden nicht gezählt.
Für die Beispielsammlung einschließlich vorhandener Org-Exporte lautet sie:

```text
validated 24 files: 0 errors, 0 warnings
```

Die ersten drei Zeilen sind echte Ausgaben des Validators. Die letzte
Zeile erzeugt `orgsyndb export` in derselben Form für eine Org-Quelle:

```text
tests/fixtures/invalid/yield-out-of-range/OSDB-0110-yield-out-of-range.md:products[1].yield_percent: error: 104.5 must be between 0 and 100
tests/fixtures/invalid/unknown-compound/OSDB-0123-unknown-compound.md:products[1].compound: error: unknown compound "no-such-compound"; the registry has no substance of this key
tests/fixtures/warn/missing-section/OSDB-0151-missing-section.md:body: warning: missing section "Notes"
tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)
```

Der Rückgabewert sagt einem aufrufenden Befehl, ob die Prüfung gelungen ist:

| Rückgabewert | Bedeutung |
|---|---|
| `0` | Kein Fehler gefunden. Warnungen können ausgegeben worden sein. |
| `1` | Mindestens ein Fehler in einer Vorschrift, einem Syntheseweg oder im Register. |
| `2` | Aufruf oder Konfiguration des Validators ist ungültig, etwa kein Verzeichnis, ein Verzeichnis, das keines ist, eine fehlende ausdrücklich benannte Einstellungsdatei, ungültige Einstellungen oder Deklarationen oder ein nicht lesbarer oder fehlerhafter Register-Snapshot. |

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
| `target` | `unknown compound "<key>"; the registry has no substance of this key` | Schlüssel korrigieren oder Stoff in der Laboranwendung anlegen. |
| `steps` | `must list at least two steps` | Genügend Stufen für einen Syntheseweg angeben. |
| `steps` oder `steps[n]` | `must be an array of tables` oder `must be a table` | Die oben gezeigten TOML-Formen verwenden. |
| `steps[n].procedure` | `<id> not found in any content root` | Vorhandene Vorschriftennummer verwenden; beim direkten Aufruf deren Verzeichnis mitgeben. |
| `steps[n].product` | `OSDB-NNNN is a general procedure; name its entry by a product: <keys>` | Einen Produktschlüssel aus der Liste wählen; jeder erscheint einmal in der Reihenfolge seines ersten Auftretens in `scope`. |
| `steps[n].product` | `<key> is a product of no entry of OSDB-NNNN` | Einen Produktschlüssel aus dem Anwendungsbereich dieser Vorschrift verwenden. |
| `steps[n].product` | `<key> is a product of entries <m> and <n> of OSDB-NNNN; name the entry by its substrates and products` | Statt `product` die vollständigen Listen `substrates` und `products` des gewählten Eintrags angeben. Die Meldung nennt alle passenden Einträge. |
| `steps[n].product` | `must be a string, e.g. "ethyl-acetate"` | Einen Verbindungsschlüssel in Anführungszeichen schreiben. |
| `steps[n].product`, `steps[n].substrates` oder `steps[n].products` | `OSDB-NNNN has no scope entries; remove <key>` | Das genannte Feld bei einer Einzelvorschrift entfernen. |
| `steps[n].substrates` | `no entry of OSDB-NNNN has these substrates and products` | Die Schlüssel der Ausgangsstoffe und Produktverbindungen eines Scope-Eintrags vollständig wiedergeben. |
| `steps[n].substrates` | `must be given with products` | Die vollständige Liste der Produktschlüssel des Eintrags ergänzen. |
| `steps[n].products` | `must be given with substrates` | Die vollständige Liste der Ausgangsstoffschlüssel des Eintrags ergänzen. |
| `steps[n].substrates` oder `steps[n].products` | `must be a list of compound keys, e.g. ["ethanol"]` | Ein Array von Schlüsseln in Anführungszeichen verwenden, ohne Produkttabellen oder Ausbeuten. |
| `steps[n].substrates` oder `steps[n].products` | `must not list a compound twice` | Jeden Schlüssel in jeder Liste nur einmal behalten. |
| `steps[n]` | `name the entry by product or by substrates and products, not both` | Nur `product` oder beide vollständigen Listen verwenden. |
| `steps[n].entry` | `not a key of a step; name the entry by its product` | `product` verwenden oder beide vollständigen Listen, wenn das Produkt in mehreren Einträgen vorkommt. |
| `steps[n]` | `starts from none of the products of step <k> (<keys>)` | Stufenreihenfolge und Ausgangsstoffe und Produkte der gewählten Einträge prüfen. |
| `target` | `<key> is not a product of the last step, step N` | Ziel und letzte Vorschrift oder letzten Eintrag prüfen. |
| `target` oder `steps` | `must equal the value in <path>` | In jeder Fassung dasselbe Ziel und genau dieselben Stufen wie geschrieben verwenden, einschließlich der Listenreihenfolge. |
| `authors`, `tags` oder `reaction_types` | `must not be set; a sequence joins no procedure taxonomy` | Feld entfernen; die Vorschriften der Stufen tragen diese Angaben. |
| Jedes andere Feld | `unknown field` | Feld entfernen oder korrigieren. |
