+++
id = "OSDB-0008"
slug = "osdb-0008"
title = "Zimtsäure"
date = 2026-10-22T20:20:00+02:00
lastmod = 2026-10-22T20:20:00+02:00
authors = ["G. Example", "B. Example"]
status = "draft"
reaction_types = ["hydrolysis"]
tags = ["sample-data", "saponification", "cinnamate"]
scale = "3 mmol"
yield_percent = 90
hazards = [
  "Natriumhydroxid: verursacht schwere Verätzungen der Haut und schwere Augenschäden",
  "Konzentrierte Salzsäure: verursacht schwere Verätzungen der Haut und schwere Augenschäden, kann die Atemwege reizen",
  "Ethanol: leicht entzündbare Flüssigkeit und Dampf, verursacht schwere Augenreizung",
  "Zimtsäure: verursacht Hautreizungen und schwere Augenreizung",
]
precursors = ["OSDB-0007"]
references = [
  "Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R. Vogel's Textbook of Practical Organic Chemistry, 5th ed.; Longman: Harlow, 1989.",
]
ai_model = "claude-opus-5-5"

[product]
name = "(E)-Zimtsäure"
formula = "C9H8O2"
mw = 148.16
smiles = "OC(=O)/C=C/c1ccccc1"
cas = "140-10-3"
+++

## Zusammenfassung

(E)-Zimtsäure durch Verseifung von (E)-Zimtsäureethylester, dem Produkt
von OSDB-0007, mit wässriger Natronlauge in Ethanol unter Rückfluss und
anschließendes Ansäuern mit Salzsäure, wie in OSDB-0001. Dies sind
Beispieldaten: Die Mengen folgen der Lehrbuchmethode, sind aber nicht
experimentell überprüft.

## Reagenzien

| Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv. |
|---|---|---|---|---|---|
| (E)-Zimtsäureethylester | 103-36-6 | 176,21 | 0,529 g (0,504 mL) | 3,00 | 1,0 |
| Natriumhydroxid | 1310-73-2 | 40,00 | 0,360 g | 9,00 | 3,0 |
| Salzsäure, 37 % (12,1 M) | 7647-01-0 | 36,46 | 1,00 mL | 12,1 | 4,0 |

## Durchführung

1. Das Natriumhydroxid (0,360 g, 9,00 mmol) in einem 50-mL-Rundkolben
   in Wasser (5 mL) lösen und Ethanol (5 mL) und einen Magnetrührstab
   zugeben.
2. Den (E)-Zimtsäureethylester (0,529 g, 0,504 mL, 3,00 mmol) zugeben.
   Der Ester bildet zunächst ölige Tröpfchen.
3. Einen Rückflusskühler aufsetzen und das Gemisch 30 Minuten unter
   schwachem Rückfluss erhitzen, bis die Tröpfchen verschwunden sind und
   die Lösung homogen ist (Anmerkung 1).
4. Den Kolben abkühlen lassen, die Lösung unter Nachspülen mit Wasser
   (10 mL) in ein 100-mL-Becherglas überführen und das Becherglas im
   Eisbad kühlen.
5. Unter Rühren die konzentrierte Salzsäure (1,00 mL, 12,1 mmol)
   zutropfen, bis das Gemisch stark sauer ist (pH 1 bis 2 auf
   Indikatorpapier). Zimtsäure fällt als voluminöser weißer Feststoff
   aus (Anmerkung 2).
6. Die Suspension 15 Minuten im Eisbad stehen lassen, damit die Fällung
   vollständig wird.

## Aufarbeitung und Reinigung

Den Feststoff absaugen und mit zwei Portionen eiskaltem Wasser (je
5 mL) waschen. Aus heißem Wasser mit etwas Ethanol umkristallisieren,
langsam und dann im Eisbad abkühlen, absaugen und die Kristalle an der
Luft bis zur Massenkonstanz trocknen. Erwartete Ausbeute 0,400 g
(2,70 mmol, 90 %).

## Charakterisierung

Farblose Kristalle. Den Schmelzpunkt bestimmen. Das IR-Spektrum (ATR)
zeigt eine breite O–H-Bande der Carbonsäure von etwa 3300 bis
2500 cm⁻¹, die konjugierte C=O-Valenzschwingung bei etwa 1680 cm⁻¹ und
keine Ester-C=O-Bande bei etwa 1710 cm⁻¹. Erwartete ¹H-NMR-Signale
(DMSO-d₆): δ 12,4 (br s, 1H, CO₂H), 7,70–7,64 (m, 2H), 7,58 (d,
J = 16,0 Hz, 1H), 7,44–7,38 (m, 3H), 6,53 (d, J = 16,0 Hz, 1H).

## Anmerkungen

1. Ethanol hält den Ester in Lösung, sodass die Hydrolyse schnell
   verläuft; Ethanol ist zugleich das Nebenprodukt und bleibt im
   Filtrat.
2. Die Säure langsam zugeben: Die Neutralisation ist exotherm, und eine
   warme Suspension gibt kleinere, weniger reine Kristalle.
3. Die Doppelbindung behält unter diesen Bedingungen ihre
   (E)-Konfiguration.

## Gefahren und Entsorgung

Natriumhydroxid und konzentrierte Salzsäure verursachen schwere
Verätzungen von Haut und Augen; Schutzhandschuhe und Schutzbrille tragen
und die Säure wegen ihrer Dämpfe im Abzug zugeben. Ethanol ist leicht
entzündbar; mit einem Heizpilz oder Wasserbad erhitzen, nie über einer
Flamme. Zimtsäure reizt Haut und Augen. Das saure Filtrat vor der
Entsorgung als wässriger Abfall neutralisieren und die Mutterlauge der
Umkristallisation als wässrigen Abfall sammeln.

## Literatur

1. Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R.
   *Vogel's Textbook of Practical Organic Chemistry*, 5th ed.; Longman:
   Harlow, 1989.
