+++
# So füllen Sie diesen Block aus
# ------------------------------
# Zeilen, die mit # beginnen, sind Hinweise für Sie; die Website
# ignoriert sie. Jede andere Zeile ist eine Angabe: ein Name, ein
# Gleichheitszeichen, dann der Wert. Ändern Sie nur den Teil nach dem
# Gleichheitszeichen. Die Namen bleiben englisch.
# - Text steht in doppelten Anführungszeichen: "so wie hier".
# - Zahlen stehen ohne Anführungszeichen und mit Dezimalpunkt: 85.5
# - Eine Liste steht in eckigen Klammern, jeder Eintrag in
#   Anführungszeichen, durch Kommas getrennt: ["erster", "zweiter"]
# Lassen Sie die beiden +++-Zeilen genau so, wie sie sind.

# Nummer der Vorschrift. Sie wird für Sie eingetragen; nicht ändern.
id = "OSDB-0000"

# Webadresse der Seite. Immer die Vorschriftennummer in Kleinbuchstaben.
# Sie wird für Sie eingetragen; nicht ändern.
slug = "osdb-0000"

# Name des Produkts, wie er in der Seitenüberschrift erscheint.
title = "Produktname"

# Wann die Vorschrift zuerst geschrieben wurde: Datum, der Buchstabe T,
# Uhrzeit, dann +01:00 im Winter oder +02:00 im Sommer (deutsche Zeit).
# Ohne Anführungszeichen.
date = 2026-10-22T20:20:00+02:00

# Wann Sie sie zuletzt geändert haben, genauso geschrieben. Bei jeder
# Änderung aktualisieren. Darf nicht vor date liegen.
lastmod = 2026-10-22T20:20:00+02:00

# Alle, die die Vorschrift geschrieben haben, als Liste von Namen.
authors = ["A. Example"]

# Stand der Vorschrift, immer englisch geschrieben: "draft", solange Sie
# daran schreiben, "checked", sobald jemand sie geprüft hat, "retired",
# wenn sie nicht mehr verwendet werden soll.
status = "draft"

# Die Art der Reaktion: genau ein Eintrag. Die erlaubten Werte stehen in
# site/data/reaction_types.toml, zum Beispiel "esterification"
# (Veresterung), "reduction" (Reduktion) oder "cross-coupling"
# (Kreuzkupplung).
reaction_types = ["esterification"]

# Schlagwörter für die Suche, mindestens eines. Nur Kleinbuchstaben und
# Ziffern, Bindestrich statt Leerzeichen: "acid-catalysed". Eine
# Übersetzung verwendet dieselben Schlagwörter wie das Original.
tags = ["change-me"]

# Wie viel Produkt die Vorschrift liefert: eine Zahl, ein Leerzeichen,
# eine Einheit.
scale = "25 mmol"

# Ausbeute in Prozent, eine Zahl von 0 bis 100, ohne Anführungszeichen
# und ohne %.
yield_percent = 85

# Die wichtigsten Gefahren, mindestens eine, jeweils als kurzer Satz.
hazards = ["Entzündbare Flüssigkeit"]

# Optionale Angaben. Um eine Zeile zu verwenden, das # am Zeilenanfang
# löschen und den Wert ändern.

# Nummern der Vorschriften, von denen diese ausgeht, z. B. die ihres
# Ausgangsstoffs. Jede muss eine Vorschrift sein, die es auf der Website
# gibt.
# precursors = ["OSDB-0001"]

# Bild der Strukturformel des Produkts, eine .svg- oder .png-Datei im
# Ordner static/structures/ der Sammlung. Den Pfad mit structures/
# beginnen.
# structure_image = "structures/osdb-0001.svg"

# Wer die Vorschrift geprüft hat, als Liste von Namen.
# checked_by = ["B. Example"]

# Literaturangaben, ein Eintrag je Zitat.
# references = ["Example, A. J. Fictitious Chem. 2020, 1, 1."]

# Name des KI-Modells, das beim Schreiben geholfen hat. Die Zeile ganz
# weglassen, wenn keine KI beteiligt war.
# ai_model = "example-model-1"

# Angaben zum Produkt. Dieser Block muss als letzter stehen, direkt vor
# der schließenden +++-Zeile.
[product]
# Name des Produkts.
name = "Produktname"
# Summenformel, z. B. "C4H8O2".
formula = "C4H8O2"
# Molmasse in g/mol, eine Zahl ohne Anführungszeichen, mit Dezimalpunkt.
mw = 88.11
# Strukturformel als SMILES.
smiles = "CCOC(C)=O"
# Optionale CAS-Nummer, z. B. "141-78-6". Das # löschen, um sie zu
# verwenden.
# cas = "141-78-6"
+++

## Zusammenfassung

Ein oder zwei Sätze: was woraus und wie hergestellt wird.

## Reagenzien

| Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv. |
|---|---|---|---|---|---|
| Ausgangsstoff | 64-19-7 | 60,05 | 1,50 g | 25,0 | 1,0 |
| Zweites Reagenz | 64-17-5 | 46,07 | 1,73 g | 37,5 | 1,5 |

## Durchführung

1. Erster Schritt, mit Mengen, Temperatur und Zeit.
2. Nächster Schritt.

## Aufarbeitung und Reinigung

Wie das Produkt isoliert und gereinigt wird.

## Charakterisierung

Aussehen, Schmelz- oder Siedepunkt und spektroskopische Daten.

## Anmerkungen

1. Praktische Hinweise, Fallstricke oder Varianten.

## Gefahren und Entsorgung

Besondere Gefahren der Reagenzien und des Produkts, und wie die Abfälle
gesammelt werden.

## Literatur

Literatur, auf der die Vorschrift beruht, oder „Keine.“
