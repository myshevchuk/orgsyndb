+++
id = "OSDB-0008"
slug = "osdb-0008"
title = "Cinnamic acid"
date = 2026-10-20T09:58:17+02:00
lastmod = 2026-10-20T10:26:30+02:00
authors = ["G. Example", "B. Example"]
status = "draft"
reaction_types = ["hydrolysis"]
tags = ["sample-data", "saponification", "cinnamate"]
scale = "3 mmol"
yield_percent = 90
hazards = [
  "Sodium hydroxide: causes severe skin burns and eye damage",
  "Concentrated hydrochloric acid: causes severe skin burns and eye damage, may cause respiratory irritation",
  "Ethanol: highly flammable liquid and vapour, causes serious eye irritation",
  "Cinnamic acid: causes skin and serious eye irritation",
]
precursors = ["OSDB-0007"]
references = [
  "Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R. Vogel's Textbook of Practical Organic Chemistry, 5th ed.; Longman: Harlow, 1989.",
]
ai_model = "claude-opus-5-5"

[product]
name = "(E)-Cinnamic acid"
formula = "C9H8O2"
mw = 148.16
smiles = "OC(=O)/C=C/c1ccccc1"
cas = "140-10-3"
+++

## Summary

(E)-Cinnamic acid by saponification of ethyl (E)-cinnamate, the product
of OSDB-0007, with aqueous sodium hydroxide in ethanol at reflux,
followed by acidification with hydrochloric acid, as in OSDB-0001. This
is sample data: the quantities follow the textbook method but are
not experimentally verified.

## Reagents

| Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv |
|---|---|---|---|---|---|
| Ethyl (E)-cinnamate | 103-36-6 | 176.21 | 0.529 g (0.504 mL) | 3.00 | 1.0 |
| Sodium hydroxide | 1310-73-2 | 40.00 | 0.360 g | 9.00 | 3.0 |
| Hydrochloric acid, 37 % (12.1 M) | 7647-01-0 | 36.46 | 1.00 mL | 12.1 | 4.0 |

## Procedure

1. Dissolve the sodium hydroxide (0.360 g, 9.00 mmol) in water (5 mL) in
   a 50 mL round-bottomed flask, and add ethanol (5 mL) and a magnetic
   stirring bar.
2. Add the ethyl (E)-cinnamate (0.529 g, 0.504 mL, 3.00 mmol). The ester
   forms oily droplets at first.
3. Fit a reflux condenser and heat the mixture under gentle reflux for
   30 minutes, until the droplets have disappeared and the solution is
   homogeneous (Note 1).
4. Let the flask cool, transfer the solution to a 100 mL beaker, rinsing
   with water (10 mL), and cool the beaker in an ice bath.
5. With stirring, add the concentrated hydrochloric acid (1.00 mL,
   12.1 mmol) dropwise until the mixture is strongly acidic (pH 1 to 2 on
   indicator paper). Cinnamic acid precipitates as a voluminous white
   solid (Note 2).
6. Keep the suspension in the ice bath for 15 minutes to complete the
   precipitation.

## Workup and Purification

Collect the solid by suction filtration and wash it with two portions of
ice-cold water (5 mL each). Recrystallise it from hot water containing a
little ethanol, cool slowly and then in ice, filter, and dry the crystals
in air to constant mass. Expected yield 0.400 g (2.70 mmol, 90 %).

## Characterization

Colourless crystals. Determine the melting point. The IR spectrum (ATR)
shows a broad carboxylic acid O–H band from about 3300 to 2500 cm⁻¹, the
conjugated C=O stretch near 1680 cm⁻¹, and no ester C=O band near
1710 cm⁻¹. Expected ¹H NMR signals (DMSO-d₆): δ 12.4 (br s, 1H, CO₂H),
7.70–7.64 (m, 2H), 7.58 (d, J = 16.0 Hz, 1H), 7.44–7.38 (m, 3H), 6.53
(d, J = 16.0 Hz, 1H).

## Notes

1. Ethanol keeps the ester in solution so that the hydrolysis is fast;
   ethanol is also the by-product and stays in the filtrate.
2. Add the acid slowly: the neutralisation is exothermic, and a warm
   suspension gives smaller, less pure crystals.
3. The double bond keeps its (E) configuration under these conditions.

## Hazards and Waste Disposal

Sodium hydroxide and concentrated hydrochloric acid cause severe burns
to skin and eyes; wear gloves and eye protection, and add the acid in a
fume hood because of its vapour. Ethanol is highly flammable; heat it
with a heating mantle or a water bath, never over a flame. Cinnamic acid
irritates skin and eyes. Neutralise the acidic filtrate before disposing
of it as aqueous waste, and collect the recrystallisation mother liquor
as aqueous waste.

## References

1. Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R.
   *Vogel's Textbook of Practical Organic Chemistry*, 5th ed.; Longman:
   Harlow, 1989.
