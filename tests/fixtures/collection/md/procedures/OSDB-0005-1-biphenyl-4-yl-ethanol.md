+++
id = "OSDB-0005"
slug = "osdb-0005"
title = "1-(Biphenyl-4-yl)ethanol"
date = 2026-10-20T09:58:16+02:00
lastmod = 2026-10-20T10:16:05+02:00
authors = ["E. Example"]
status = "draft"
reaction_types = ["reduction"]
tags = ["sample-data", "sodium-borohydride", "biphenyl"]
scale = "5 mmol"
substrates = ["4-acetylbiphenyl"]
products = [{ compound = "1-biphenyl-4-yl-ethanol", yield_percent = 90 }]
hazards = [
  "Sodium borohydride: in contact with water releases flammable hydrogen, toxic if swallowed, causes severe skin burns and eye damage, may damage fertility or the unborn child",
  "Ethanol: highly flammable liquid and vapour, causes serious eye irritation",
  "Hydrochloric acid, 1 M: may irritate skin and eyes",
  "Ethyl acetate: highly flammable liquid and vapour, may cause drowsiness",
]
references = [
  "Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R. Vogel's Textbook of Practical Organic Chemistry, 5th ed.; Longman: Harlow, 1989.",
]
ai_model = "claude-opus-5-5"
+++

## Summary

1-(Biphenyl-4-yl)ethanol by reduction of 4-acetylbiphenyl, the product
of OSDB-0004, with sodium borohydride in ethanol at room temperature,
followed by an acidic quench and extraction. The racemic secondary
alcohol is obtained. This is sample data: the quantities follow the
textbook method but are not experimentally verified.

## Reagents

| Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv |
|---|---|---|---|---|---|
| 4-Acetylbiphenyl | 92-91-1 | 196.25 | 0.981 g | 5.00 | 1.0 |
| Sodium borohydride | 16940-66-2 | 37.83 | 0.114 g | 3.01 | 0.6 |

## Procedure

1. Dissolve the 4-acetylbiphenyl (0.981 g, 5.00 mmol) in ethanol
   (20 mL) in a 100 mL conical flask with a magnetic stirring bar,
   warming gently if necessary, then cool the solution to room
   temperature. Some ketone may crystallise again; this does no harm.
2. Stand the flask in a water bath at room temperature and add the
   sodium borohydride (0.114 g, 3.01 mmol) in four small portions over
   5 minutes (Note 1).
3. Stir the mixture at room temperature for 30 minutes. Any suspended
   ketone dissolves as it is reduced.
4. Check by thin-layer chromatography (silica, heptane–ethyl acetate
   3:1, UV at 254 nm) that no 4-acetylbiphenyl remains; the alcohol runs
   lower than the ketone.
5. Cool the flask in an ice bath and add 1 M hydrochloric acid dropwise
   (about 5 mL) until gas evolution stops and the mixture is just acidic
   to indicator paper (Note 2).

## Workup and Purification

Remove most of the ethanol on a rotary evaporator (bath at 40 °C), add
water (20 mL) and extract the product with ethyl acetate in two 20 mL
portions. Wash the combined extracts with saturated sodium chloride
solution (15 mL), dry them over anhydrous sodium sulfate, filter and
evaporate. Recrystallise the white solid from a small volume of hot
heptane containing a little ethyl acetate, cool in ice, collect by
suction filtration and dry in air. Expected yield 0.892 g (4.50 mmol,
90 %).

## Characterization

White crystalline solid. Determine the melting point. The IR spectrum
(ATR) shows a broad O–H stretch near 3350 cm⁻¹ and no ketone C=O stretch
near 1675 cm⁻¹, which distinguishes the product from its starting
material. Expected ¹H NMR signals (CDCl₃): δ 7.62–7.55 (m, 4H),
7.48–7.40 (m, 4H), 7.34 (t, 1H), 4.96 (q, J = 6.4 Hz, 1H), 1.85 (br s,
1H, OH), 1.55 (d, J = 6.4 Hz, 3H).

## Notes

1. Each mole of borohydride can reduce up to four moles of ketone, so
   0.6 equivalent is a comfortable excess. Adding it in portions keeps
   the slight warming and the hydrogen evolution under control.
2. The acid destroys the excess borohydride and hydrolyses the borate
   esters. Hydrogen is evolved; do this in a fume hood away from flames.
3. The product is a racemate; the reduction creates a new stereocentre
   without any preference for either configuration.

## Hazards and Waste Disposal

Sodium borohydride releases flammable hydrogen with water and acids, is
toxic if swallowed, causes severe burns, and may damage fertility or the
unborn child; weigh it in a fume hood with gloves and eye protection, and
keep it away from water until it is used. Ethanol and ethyl acetate are
highly flammable. Quench every residue of borohydride with dilute acid
before disposal. Neutralise the aqueous layers and dispose of them as
aqueous waste, and collect the organic filtrates as non-halogenated
organic waste.

## References

1. Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R.
   *Vogel's Textbook of Practical Organic Chemistry*, 5th ed.; Longman:
   Harlow, 1989.
