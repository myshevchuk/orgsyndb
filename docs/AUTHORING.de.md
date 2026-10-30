# Eine Vorschrift in Markdown schreiben

Diese Anleitung führt Sie von der Vorlage bis zur geprüften Vorschrift. Die
Vorschriften liegen in einer *Sammlung*, einem eigenen Projektordner, aus
dem das Programm OrgSynDB die Website erzeugt. Sie brauchen dafür weder
Git noch Org, TOML oder Hugo zu kennen.

Markdown ist ein Textformat, das Zeichen wie `##` für Überschriften
verwendet. TOML ist der kleine Datenblock am Anfang jeder Vorschrift. Hugo
ist das Programm, das aus den Vorschriftendateien die Website macht. Sie
können dieser Anleitung folgen, ohne eines davon direkt zu benutzen.

Die Website ist auf Deutsch, sofern die oder der Verantwortliche sie nicht
auf Englisch umgestellt hat, und zeigt Vorschriften in jeder Sprache.
Diese Anleitung beschreibt, wie Sie eine Vorschrift auf Deutsch schreiben
(Abschnitte 1 bis 6) und wie Sie eine englische Vorschrift übersetzen
(Abschnitt 7).

Genaue Schreibweisen, erlaubte Werte und Feldregeln stehen in der
[Schema-Referenz](SCHEMA.de.md). Diese Anleitung erklärt die Arbeit der
Reihe nach, statt die Referenz zu wiederholen. Die englische Fassung ist
[AUTHORING.md](AUTHORING.md).

## 1. Eine Vorschriftendatei bekommen

Die Vorlage für deutsche Vorschriften ist
[`templates/procedure.de.md`](../templates/procedure.de.md).

Am einfachsten bitten Sie die Verantwortliche oder den Verantwortlichen der
Sammlung, Ihre Datei so anzulegen:

```sh
orgsyndb new --md --lang de "Produktname"
```

Der Befehl wird im Ordner der Sammlung ausgeführt. Er legt eine Datei wie
`md/procedures/OSDB-0003-produktname.de.md` an und trägt die nächste
freie Vorschriftennummer, den Seitennamen, den Titel und beide Zeitangaben
ein. Umlaute und ß im Titel werden im Dateinamen ausgeschrieben: aus
„Größe“ wird `groesse`.

Wenn Sie die Vorlage selbst kopieren, fragen Sie zuerst nach der nächsten
`OSDB-NNNN`-Nummer. Ersetzen Sie `OSDB-0000` in `id` und im Dateinamen und
`osdb-0000` in `slug` durch dieselbe Nummer in Kleinbuchstaben. Speichern
Sie die Datei nach diesem Muster:

```text
OSDB-NNNN-kurzer-name.de.md
```

Das `.de` vor der Endung kennzeichnet die Datei als deutsch. Eine Datei
ohne Sprachkürzel darf ebenfalls deutsch sein; dann tragen Sie im
Datenblock `language = "de"` ein. In `kurzer-name` stehen nur
Kleinbuchstaben,
Ziffern und einzelne Bindestriche. Wenn Sie die unveränderte Vorlage
zurückschicken, kann die oder der Verantwortliche die Ersetzungen auch für
Sie vornehmen.

## 2. Den Datenblock ausfüllen

Der Datenblock, *Front Matter* genannt, ist alles zwischen den beiden
`+++`-Zeilen. Lassen Sie beide `+++`-Zeilen stehen. Zeilen, die mit `#`
beginnen, sind Hinweise und erscheinen nicht auf der Website.

Ändern Sie jeweils den Wert nach dem Gleichheitszeichen. Die Namen vor dem
Gleichheitszeichen bleiben englisch. Text steht in doppelten
Anführungszeichen. Zahlen stehen ohne Anführungszeichen und mit
Dezimalpunkt, also `88.11`, nicht `88,11`. Listen stehen in eckigen
Klammern. Texteinträge stehen in doppelten Anführungszeichen;
Produkteinträge stehen in geschweiften Klammern, wie unten gezeigt.

Füllen Sie diese Pflichtfelder aus:

- `id` und `slug`: die Werte von `new` stehen lassen oder die Nummer
  verwenden, die Sie bekommen haben.
- `title`: der Produktname, der oben auf der Seite steht.
- `date`: wann die Vorschrift zuerst geschrieben wurde.
- `lastmod`: wann die Vorschrift zuletzt geändert wurde. Nach jeder
  späteren Änderung aktualisieren.
- `authors`: alle, die die Vorschrift geschrieben haben.
- `status`: ob die Vorschrift ein Entwurf (`"draft"`), geprüft
  (`"checked"`) oder zurückgezogen (`"retired"`) ist. Der Wert bleibt
  englisch; die deutsche Seite zeigt *Entwurf*, *Geprüft* oder
  *Zurückgezogen*.
- `reaction_types`: genau ein Reaktionstyp, als englisches Kürzel wie
  `"esterification"`. Die [Schema-Referenz](SCHEMA.de.md#reaktionstypen)
  listet die Kürzel mit ihren deutschen Bezeichnungen.
- `tags`: nützliche Suchbegriffe in Kleinbuchstaben. Ersetzen Sie das
  `change-me` der Vorlage. Das Schlagwort `sample-data` setzt einen
  Warnhinweis auf die Seite und auf Ausdrucke; verwenden Sie es nie für
  eine echte Vorschrift.
- `scale`: wie viel Produkt die Vorschrift liefert, etwa `"2,5 mmol"`.
  Hier ist ein Dezimalkomma erlaubt, weil der Wert Text ist.
- `hazards`: kurze Beschreibungen der wichtigsten Gefahren.
- `products`: ein oder mehrere Verbindungsschlüssel, jeder mit seiner
  isolierten Ausbeute. Ein Schlüssel ist der Name einer Datei in
  `compounds/` ohne `.toml`. Der nächste Abschnitt erklärt, wie Sie den
  passenden Eintrag finden oder anlegen.

Die Vorlage enthält außerdem auskommentierte, optionale Felder für
Ausgangsstoffe (`substrates`), Prüfende, Literaturangaben und ein KI-Modell.
Löschen Sie das `#` am Zeilenanfang, wenn Sie ein Feld brauchen. Lassen Sie
die Zeile auskommentiert, wenn es nicht zutrifft.

Benennen Sie Produkte und Ausgangsstoffe durch ihre Schlüssel im Register.
Die Aspirin-Vorschrift der Beispielsammlung verwendet zum Beispiel:

```toml
substrates = ["salicylic-acid", "acetic-anhydride"]
products = [{ compound = "acetylsalicylic-acid", yield_percent = 75 }]
```

Jedes Produkt erhält ein eigenes `compound` und `yield_percent` in
geschweiften Klammern. Trennen Sie mehrere Produkteinträge innerhalb der
eckigen Klammern durch Kommas. Ausbeuten sind Zahlen von 0 bis 100, ohne
Anführungszeichen oder `%`, mit Dezimalpunkt. Nennen Sie keinen Schlüssel
doppelt in einer Liste und kein Produkt auch als Ausgangsstoff.

Die Website verlinkt die Ausgangsstoffe auf ihre Verbindungsseiten. Sie
leitet **Vorstufen** aus anderen Vorschriften ab, die diese Verbindungen
herstellen, und **Verwendet in** aus Vorschriften, die von Ihren Produkten
ausgehen. Die Aspirin-Seite verlinkt zum Beispiel OSDB-0001, weil diese
Vorschrift `salicylic-acid` herstellt. Diese Vorschriftenlinks tragen Sie
nicht selbst ein.

Schreiben Sie `date` und `lastmod` ohne Anführungszeichen. Verwenden Sie
die Ortszeit Europe/Berlin und hängen Sie im Winter `+01:00`, im Sommer
`+02:00` an, wie in der Vorlage. Die
[Schema-Referenz](SCHEMA.de.md#felder-des-datenblocks) nennt das genaue
Format und jeden erlaubten Wert.

### Verbindungen finden oder anlegen

Das *Verbindungsregister* ist der Ordner `compounds/` der Sammlung. Jede
Verbindung hat eine Datei `<key>.toml` mit ihrem Namen und ihren chemischen
Daten. Alle Vorschriften, die sie herstellen oder verwenden, teilen sich
diese Daten. Suchen Sie zuerst nach einem vorhandenen Eintrag. Der Schlüssel
bestimmt die Identität der Verbindung; die Website vergleicht keine
Strukturen, um doppelte Einträge zu erkennen.

Kopieren Sie für eine neue Verbindung
[`templates/compound.toml`](../templates/compound.toml) nach `compounds/`.
Wählen Sie einen Dateinamen aus Kleinbuchstaben und Ziffern mit einzelnen
Bindestrichen, etwa `ethyl-acetate.toml`. In der Vorschrift verwenden Sie
`ethyl-acetate` als Schlüssel. Ersetzen Sie dort den Vorlagenschlüssel
`example-compound` durch den tatsächlich verwendeten Schlüssel. Ein neues
Vorschriftengerüst legt keine Verbindungseinträge an.

Füllen Sie `name`, `formula`, `mw` in g/mol und `smiles` aus. SMILES ist die
Textschreibweise der Strukturformel. Das optionale `name_de` liefert den
Namen auf einer deutschen Website; fehlt es, zeigt diese `name`. Eine
englische Website verwendet immer `name`. Optional sind auch `cas`, die
CAS-Registriernummer, und `structure_image`. Text steht in
Anführungszeichen, die Molmasse als positive Zahl ohne Anführungszeichen
und mit Dezimalpunkt. Verbindungsdateien enthalten weder `+++`-Zeilen noch
eine Überschrift `[product]`.

Für ein Strukturbild legen Sie eine SVG- oder PNG-Datei in
`static/structures/` der Sammlung ab. Setzen Sie `structure_image` in der
Verbindungsdatei, etwa `structure_image = "structures/isopentyl-acetate.svg"`
für `isopentyl-acetate`. Ein SVG verwendet schwarze Linien und Schrift auf
einem weißen Hintergrundrechteck. Geben Sie der Datei ein `<title>`-Element
und lassen Sie Skripte, externe Bilder und andere externe Verweise weg.
Die Website zeigt das Bild im dunklen Modus auf einer weißen Fläche.
Bitten Sie die Verantwortliche oder den Verantwortlichen, das Bild
hinzuzufügen oder zu prüfen, wenn Sie nicht mit SVG-Dateien arbeiten.

Sie dürfen einen Ausgangsstoff registrieren, ohne dass eine Vorschrift ihn
herstellt. Auch eine Verbindung, die keine Vorschrift verwendet, ist
zulässig. **Verbindungen** in der Navigation öffnet das Verzeichnis unter
`/compounds/`. Jeder Name verlinkt auf eine Seite mit chemischen Daten,
dem Strukturbild, sofern vorhanden, Vorschriften unter **Hergestellt nach**
mit Ausbeute und Status sowie Vorschriften unter **Verwendet in** mit Status.

### So erscheinen die Felder auf der Seite

Der Titelblock zeigt über dem Titel die `id` und ein Statusabzeichen.
Wenn `status` den Wert `checked` hat und `checked_by` ausgefüllt ist,
folgen die Namen der Prüfenden auf das Abzeichen: **Geprüft von** und die
Namen. Unter dem Titel erscheinen `scale` als **Ansatzgröße** und
die Produktausbeuten als **Ausbeute**. Bei einem Produkt steht nur die
Prozentzahl, bei mehreren für jedes Produkt die Prozentzahl mit dem
Verbindungsnamen, in der Reihenfolge von `products`. Darunter steht
die Schaltfläche **Drucken / Als PDF speichern**.

Die Seite zeigt für jedes Produkt mit Strukturbild eine Abbildung, in der
Reihenfolge von `products`. Auf einem breiten Bildschirm stehen die Bilder
rechts neben dem Titel, über dem Datenfeld. In einem schmalen Fenster
folgen sie auf die Druckschaltfläche, vor dem Datenfeld. Auch im Ausdruck
stehen sie vor dem Datenfeld. Hat kein Produkt ein Bild, erscheint der
Platzhalter **Keine Strukturformel**, der im Ausdruck fehlt. Eine Linie
schließt den Titelblock auf dem Bildschirm ab.

Das Datenfeld verlinkt die Produktnamen immer unter **Produkt** oder
**Produkte** auf ihre Verbindungsseiten, auch bei gleichem Namen wie im
Titel. Bei einem Produkt zeigt es außerdem Summenformel, Molmasse,
gegebenenfalls die CAS-Nummer und SMILES. Bei mehreren Produkten finden
Sie diese Daten auf den Verbindungsseiten. **Ausgangsstoffe** verlinkt die
Verbindungen aus `substrates`. Es folgen Reaktionstyp, Schlagwörter,
Autoren, bei Entwürfen und zurückgezogenen Vorschriften gegebenenfalls
die Prüfenden unter **Geprüft von**,
Erstellungs- und Änderungszeit sowie die Links zu Vorstufen und
Folgevorschriften. Ziffern der Summenformel erscheinen tiefgestellt.
Molmasse und Ausbeute erscheinen mit Dezimalkomma, mit `g/mol` und
Prozentzeichen; neben SMILES steht eine Schaltfläche **Kopieren**.
Reaktionstyp, Schlagwörter und Autoren verlinken auf Seiten mit verwandten
Vorschriften. Autorennamen werden mit großem Anfangsbuchstaben angezeigt,
aus `van` wird also `Van`. Die acht Abschnitte des Textes stehen auf einem
breiten Bildschirm neben dem Datenfeld, in einem schmalen Fenster und im
Ausdruck danach.

## 3. Die Vorschrift schreiben

Schreiben Sie unterhalb der schließenden `+++`-Zeile. Behalten Sie diese
acht `##`-Überschriften in dieser Reihenfolge:

1. Zusammenfassung
2. Reagenzien
3. Durchführung
4. Aufarbeitung und Reinigung
5. Charakterisierung
6. Anmerkungen
7. Gefahren und Entsorgung
8. Literatur

Ersetzen Sie den Beispieltext und die Tabellenzeilen. Geben Sie Mengen,
Temperaturen, Zeiten, Beobachtungen, Aufarbeitung, Reinigung,
Charakterisierung und Sicherheitshinweise so an, dass man der Vorschrift
folgen kann. Schreiben Sie im Text Dezimalkommas: „2,76 g“. Steht unter
Literatur nichts, schreiben Sie `Keine.`

Damit Lesende vom Text zur passenden Anmerkung springen können, schreiben
Sie die Anmerkungen als nummerierte Liste im Abschnitt Anmerkungen.
Schreiben Sie den Verweis als normalen Text `(Anmerkung 2)`: das
ausgeschriebene Wort, ein Leerzeichen und die Nummer in Klammern. Die
Website verlinkt ihn, wenn die Anmerkung vorhanden ist. Andere Formen wie
`(Anmerkungen 2 und 3)`, `(Anmerkung 2a)` oder `siehe Anmerkung 2`
bleiben unverlinkt. In Codeblöcken und als Code ausgezeichnetem Text
entstehen keine Links.

Der [Stilratgeber für deutsche Vorschriften](STYLE.de.md) erklärt, wie der
Text formuliert wird. Verwenden Sie das
[Glossar zur organischen Synthese](GLOSSARY.de.md) für Fachbegriffe, feste
Wendungen und wiederverwendbare Sätze mit englischen Entsprechungen.

Behalten Sie die sechs Spalten der Reagenzientabelle in dieser
Reihenfolge: **Reagenz**, **CAS**, **M (g/mol)**, **Menge**, **mmol** und
**Äquiv.** Schreiben Sie `kat.` in **mmol** und **Äquiv.** eines
Katalysators. Eine breite Tabelle lässt sich auf dem Bildschirm in ihrem
eigenen Bereich seitlich verschieben und wird beim Drucken an das Papier
angepasst.

Zum Vergleich dient
[`OSDB-0002-aspirin.de.md`](../examples/demo/md/procedures/OSDB-0002-aspirin.de.md)
in der Beispielsammlung. Die Datei enthält Beispieldaten, keine
experimentell überprüfte Vorschrift.

## 4. Die Datei speichern oder schicken

Wenn Sie den Ordner der Sammlung haben, speichern Sie die fertige Datei
direkt in dessen `md/procedures/`, nicht in einem Unterordner.

Wenn Sie die Sammlung nicht haben, schicken Sie die `.md`-Datei an die
Verantwortliche oder den Verantwortlichen. Sagen Sie dazu, ob Sie eine
zugeteilte Vorschriftennummer verwendet oder die Nummer der Vorlage stehen
gelassen haben. Dann kann die Datei abgelegt, umbenannt und geprüft
werden. Schicken Sie neue Verbindungsdateien und Strukturbilder mit oder
bitten Sie darum, die Registereinträge anzulegen.

## 5. Die Datei prüfen

Ein Validator ist ein Programm, das die Datei auf bekannte Fehler prüft.
Ein Terminal ist ein Fenster, in das man Befehle eintippt. Wenn Sie die
Sammlung und das Programm OrgSynDB haben, öffnen Sie ein Terminal im
Ordner der Sammlung und führen Sie aus:

```sh
orgsyndb validate
```

Der Befehl exportiert die Org-Vorschriften der Sammlung und prüft dann
alle Vorschriften und Verbindungseinträge. Jedes Problem hat diese Form:

```text
pfad/zur/datei.de.md:feld: error: Meldung
pfad/zur/datei.de.md:feld: warning: Meldung
```

Lesen Sie jede Zeile von links nach rechts:

- Der erste Teil ist die Datei, die Sie öffnen.
- Der zweite Teil ist das Feld oder der Textabschnitt, den Sie ansehen.
- `error` heißt, eine Vorschrift oder ein Verbindungseintrag ist ungültig
  und die Prüfung schlägt fehl.
- `warning` heißt, die Prüfung läuft durch, aber Sie sollten das Problem
  ansehen und beheben.
- Der Text am Ende sagt, was falsch ist. Die Meldungen sind englisch.

Eine Zeile mit `products[1].yield_percent` nennt die Ausbeute im ersten
Produkteintrag; die Zählung beginnt bei 1. Bei `unknown compound` prüfen
Sie den Schlüssel und seine Datei in `compounds/`. Eine Meldung wie
`compounds/ethyl-acetate.toml:mw` betrifft das Feld in dieser
Verbindungsdatei. Eine Zeile mit `body` betrifft die
Abschnittsüberschriften; `missing section "Notes"` statt
`missing section "Anmerkungen"` zeigt, dass der Dateiname kein `.de` hat
und die Datei deshalb als englisch gilt. Führen Sie den Befehl nach der
Korrektur erneut aus. Die letzte Zeile nennt die Zahl der Dateien, Fehler
und Warnungen; die Dateizahl umfasst auch Verbindungseinträge.

Wenn eine Meldung unklar ist, schlagen Sie ihr Feld in der
[Schema-Referenz](SCHEMA.de.md) nach. Wenn Sie die Datei verschickt haben,
kann die oder der Verantwortliche dieselbe Prüfung ausführen und Ihnen die
Meldungen schicken.

## 6. Die Seite ansehen

Führen Sie aus:

```sh
orgsyndb serve
```

Warten Sie auf diese Zeile:

```text
serving http://127.0.0.1:8000/ (Ctrl-C to stop)
```

Öffnen Sie <http://127.0.0.1:8000/> in einem Browser auf demselben
Rechner. Die Adresse funktioniert nur auf diesem Rechner. Drücken Sie im
Terminal `Strg+C`, um die Vorschau zu beenden.

Auf einer Vorschriftenseite öffnet **Drucken / Als PDF speichern** den
Druckdialog des Browsers. Das Drucklayout ist A4, vollständig und schwarz
auf weiß. Firefox druckt die Kopfzeile und die Seitenzahlen nicht, die
die mit WeasyPrint erzeugten PDFs enthalten.

Die Vorschau aktualisiert sich nicht von selbst. Beenden Sie sie nach
einer Änderung und starten Sie `orgsyndb serve` erneut.

## 7. Eine englische Vorschrift übersetzen

Dateien mit derselben Nummer sind Fassungen einer Vorschrift. Die Website
veröffentlicht jede Vorschrift genau einmal, in der Fassung, die zu ihrer
Sprache passt: auf einer deutschen Website die `.de`-Datei, sonst die
Datei ohne Sprachkürzel, sonst die `.en`-Datei. Eine Übersetzung ersetzt
also auf der deutschen Website das englische Original.

1. Kopieren Sie die englische Datei und fügen Sie `.de` vor der Endung
   ein: aus `OSDB-0002-aspirin.md` wird `OSDB-0002-aspirin.de.md`. Der
   übrige Name bleibt gleich.
2. Übersetzen Sie `title`, `hazards` und bei
   Bedarf `references`. `scale`, `authors` und `checked_by` dürfen Sie
   anpassen.
3. Setzen Sie `date` und `lastmod` auf den Zeitpunkt der Übersetzung.
   Steht im Original `language = "en"`, ändern Sie es in `"de"` oder
   löschen Sie die Zeile.
4. Lassen Sie `id`, `slug`, `status`, `reaction_types`, `tags`, `products`
   und `substrates` wie im Original. Die Prüfung meldet jede Abweichung
   als Fehler unter dem jeweiligen Feldnamen. Zahlen werden nach ihrem
   Wert verglichen: `85` und `85.0` stimmen überein. Verbindungsnamen
   kommen aus `name` und `name_de` im gemeinsamen Register. Tragen Sie
   den deutschen Verbindungsnamen dort in `name_de` ein.

5. Übersetzen Sie den Text, ersetzen Sie die englischen Überschriften und
   Tabellenspalten durch die deutschen aus Abschnitt 3 und schreiben Sie
   Dezimalkommas. Richten Sie sich dabei nach dem
   [Stilratgeber](STYLE.de.md), und verwenden Sie das
   [Glossar](GLOSSARY.de.md) für Begriffe, feste Wendungen und
   wiederverwendbare Sätze.

Ändert sich später eine gemeinsame Angabe, etwa der Status, ändern Sie sie
in beiden Dateien. Eine Vorschrift ohne deutsche Fassung erscheint auf der
deutschen Website in ihrer vorhandenen Fassung.
