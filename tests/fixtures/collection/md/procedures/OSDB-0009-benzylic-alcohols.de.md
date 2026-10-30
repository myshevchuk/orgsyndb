+++
id = "OSDB-0009"
slug = "osdb-0009"
title = "Sekundäre Benzylalkohole durch Reduktion mit Natriumborhydrid"
date = 2026-10-22T20:20:00+02:00
lastmod = 2026-10-22T20:20:00+02:00
authors = ["E. Example"]
status = "draft"
reaction_types = ["reduction"]
tags = ["sample-data", "sodium-borohydride"]
scale = "10 mmol"
scheme_image = "structures/aryl-ketone-reduction.svg"
scope = [
  { substrates = ["4-acetylbiphenyl"], time = "30 min", products = [{ compound = "1-biphenyl-4-yl-ethanol", yield_percent = 90 }] },
  { substrates = ["acetophenone"], time = "20 min", products = [{ compound = "1-phenylethanol", yield_percent = 85 }] },
  { substrates = ["4-bromoacetophenone"], scale = "5 mmol", time = "30 min", note = "Das Produkt schmilzt nahe der Raumtemperatur und fällt zunächst möglicherweise als Öl an, das beim Stehen erstarrt.", products = [{ compound = "1-4-bromophenyl-ethanol", yield_percent = 88 }] },
]
hazards = [
  "Natriumborhydrid: entwickelt in Berührung mit Wasser entzündbaren Wasserstoff, giftig bei Verschlucken, verursacht schwere Verätzungen der Haut und schwere Augenschäden, kann die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen",
  "Ethanol: leicht entzündbare Flüssigkeit und Dampf, verursacht schwere Augenreizung",
  "Salzsäure, 1 M: kann Haut und Augen reizen",
  "Ethylacetat: leicht entzündbare Flüssigkeit und Dampf, kann Schläfrigkeit verursachen",
]
references = [
  "Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R. Vogel's Textbook of Practical Organic Chemistry, 5th ed.; Longman: Harlow, 1989.",
]
ai_model = "claude-sonnet-5-5"
+++

## Zusammenfassung

Eine allgemeine Vorschrift für die Reduktion von Arylmethylketonen zu
den racemischen sekundären Benzylalkoholen mit Natriumborhydrid in
Ethanol bei Raumtemperatur, gefolgt von saurem Quenchen und Extraktion.
Die Tabelle des Anwendungsbereichs führt drei Ketone auf, darunter
4-Acetylbiphenyl, das Produkt von OSDB-0004, das den Alkohol von
OSDB-0005 liefert. Dies sind Beispieldaten: Die Mengen folgen der
Lehrbuchmethode, sind aber nicht experimentell überprüft.

## Reagenzien

| Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv. |
|---|---|---|---|---|---|
| 4-Acetylbiphenyl | 92-91-1 | 196,25 | 1,96 g | 10,0 | 1,0 |
| Natriumborhydrid | 16940-66-2 | 37,83 | 0,227 g | 6,00 | 0,6 |

## Durchführung

1. Das Keton (Eintrag 1: 4-Acetylbiphenyl, 1,96 g, 10,0 mmol) in einem
   100-mL-Erlenmeyerkolben mit Magnetrührstab in Ethanol (40 mL) lösen,
   falls nötig unter leichtem Erwärmen, und die Lösung dann auf
   Raumtemperatur abkühlen. Etwas Keton kann wieder auskristallisieren;
   das schadet nicht.
2. Den Kolben in ein Wasserbad von Raumtemperatur stellen und das
   Natriumborhydrid (0,227 g, 6,00 mmol) in vier kleinen Portionen
   innerhalb von 5 Minuten zugeben (Anmerkung 1).
3. Das Gemisch so lange bei Raumtemperatur rühren, wie die Tabelle des
   Anwendungsbereichs für das Keton angibt, bei Eintrag 1 30 Minuten
   (Anmerkung 2).
4. Dünnschichtchromatographisch prüfen (Kieselgel, Heptan–Ethylacetat
   3:1, UV bei 254 nm), dass kein Keton mehr vorhanden ist; der Alkohol
   läuft tiefer als das Keton.
5. Den Kolben im Eisbad kühlen und 1 M Salzsäure zutropfen (etwa
   10 mL), bis die Gasentwicklung aufhört und das Gemisch auf
   Indikatorpapier gerade sauer reagiert (Anmerkung 3).
6. Bei einem homologen Keton die Schritte 1 bis 5 im Maßstab seines
   Eintrags wiederholen (10 mmol, sofern die Tabelle keinen anderen
   angibt), mit 0,6 Äquivalenten Natriumborhydrid und der Rührzeit
   seines Eintrags.

## Aufarbeitung und Reinigung

Den größten Teil des Ethanols am Rotationsverdampfer entfernen (Bad
40 °C), Wasser (40 mL) zugeben und das Produkt mit zwei Portionen
Ethylacetat zu 30 mL extrahieren. Die vereinigten Extrakte mit
gesättigter Natriumchlorid-Lösung (30 mL) waschen, über wasserfreiem
Natriumsulfat trocknen, filtrieren und eindampfen. Den weißen Feststoff
von Eintrag 1 aus wenig heißem Heptan mit etwas Ethylacetat
umkristallisieren, im Eisbad abkühlen, absaugen und an der Luft
trocknen. Erwartete Ausbeute für Eintrag 1: 1,78 g (9,00 mmol, 90 %).

## Charakterisierung

Bei einem festen Produkt den Schmelzpunkt bestimmen. Das IR-Spektrum
(ATR) jedes Produkts zeigt eine breite O–H-Valenzschwingung bei etwa
3350 cm⁻¹ und keine C=O-Valenzschwingung des Ketons bei etwa
1675 cm⁻¹, was es vom Edukt unterscheidet. Das ¹H-NMR-Spektrum (CDCl₃)
jedes Produkts zeigt für die CH(OH)CH₃-Gruppe ein Quartett bei etwa
δ 4,9 (1H) und ein Duplett bei etwa δ 1,5 (3H); für Eintrag 1 werden
erwartet: δ 7,62–7,55 (m, 4H), 7,48–7,40 (m, 4H), 7,34 (t, 1H), 4,96
(q, J = 6,4 Hz, 1H), 1,85 (br s, 1H, OH), 1,55 (d, J = 6,4 Hz, 3H).

## Anmerkungen

1. Ein Mol Borhydrid kann bis zu vier Mol Keton reduzieren, 0,6
   Äquivalente sind also ein reichlicher Überschuss. Die portionsweise
   Zugabe hält die leichte Erwärmung und die Wasserstoffentwicklung
   unter Kontrolle.
2. Die Zeiten der Tabelle des Anwendungsbereichs sind die Rührzeiten von
   Schritt 3. Den Verlauf wie in Schritt 4 dünnschichtchromatographisch
   verfolgen und länger rühren, wenn noch Keton vorhanden ist.
3. Die Säure zerstört das überschüssige Borhydrid und hydrolysiert die
   Borsäureester. Dabei entsteht Wasserstoff; im Abzug und fern von
   Flammen arbeiten.
4. Die Produkte sind Racemate; die Reduktion erzeugt ein neues
   Stereozentrum ohne Bevorzugung einer Konfiguration.

## Gefahren und Entsorgung

Natriumborhydrid entwickelt mit Wasser und Säuren entzündbaren
Wasserstoff, ist giftig bei Verschlucken, verursacht schwere
Verätzungen und kann die Fruchtbarkeit beeinträchtigen oder das Kind im
Mutterleib schädigen; im Abzug mit Schutzhandschuhen und Schutzbrille
einwiegen und bis zur Verwendung von Wasser fernhalten. Ethanol und
Ethylacetat sind leicht entzündbar. Alle Borhydridreste vor der
Entsorgung mit verdünnter Säure zersetzen. Die wässrigen Phasen
neutralisieren und als wässrigen Abfall entsorgen; die organischen
Filtrate als halogenfreien organischen Abfall sammeln, die Filtrate von
Eintrag 3 enthalten jedoch Brom und gehören in den halogenhaltigen
organischen Abfall.

## Literatur

1. Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R.
   *Vogel's Textbook of Practical Organic Chemistry*, 5th ed.; Longman:
   Harlow, 1989.
