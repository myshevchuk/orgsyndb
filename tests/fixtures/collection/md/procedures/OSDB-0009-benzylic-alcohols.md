+++
id = "OSDB-0009"
slug = "osdb-0009"
title = "Secondary benzylic alcohols by sodium borohydride reduction"
date = 2026-10-19T21:40:12+02:00
lastmod = 2026-10-19T22:05:41+02:00
authors = ["E. Example"]
status = "draft"
reaction_types = ["reduction"]
tags = ["sample-data", "sodium-borohydride"]
scale = "10 mmol"
scheme_image = "structures/aryl-ketone-reduction.svg"
scope = [
  { substrates = ["4-acetylbiphenyl"], time = "30 min", products = [{ compound = "1-biphenyl-4-yl-ethanol", yield_percent = 90 }] },
  { substrates = ["acetophenone"], time = "20 min", products = [{ compound = "1-phenylethanol", yield_percent = 85 }] },
  { substrates = ["4-bromoacetophenone"], scale = "5 mmol", time = "30 min", note = "The product melts near room temperature and may be obtained as an oil that solidifies on standing.", products = [{ compound = "1-4-bromophenyl-ethanol", yield_percent = 88 }] },
]
hazards = [
  "Sodium borohydride: in contact with water releases flammable hydrogen, toxic if swallowed, causes severe skin burns and eye damage, may damage fertility or the unborn child",
  "Ethanol: highly flammable liquid and vapour, causes serious eye irritation",
  "Hydrochloric acid, 1 M: may irritate skin and eyes",
  "Ethyl acetate: highly flammable liquid and vapour, may cause drowsiness",
]
references = [
  "Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R. Vogel's Textbook of Practical Organic Chemistry, 5th ed.; Longman: Harlow, 1989.",
]
ai_model = "claude-sonnet-5-5"
+++

## Summary

A general procedure for the reduction of aryl methyl ketones to the
racemic secondary benzylic alcohols with sodium borohydride in ethanol
at room temperature, followed by an acidic quench and extraction. The
scope table lists three ketones, among them 4-acetylbiphenyl, the
product of OSDB-0004, which gives the alcohol of OSDB-0005. This is
sample data: the quantities follow the textbook method but are not
experimentally verified.

## Reagents

| Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv |
|---|---|---|---|---|---|
| 4-Acetylbiphenyl | 92-91-1 | 196.25 | 1.96 g | 10.0 | 1.0 |
| Sodium borohydride | 16940-66-2 | 37.83 | 0.227 g | 6.00 | 0.6 |

## Procedure

1. Dissolve the ketone (entry 1: 4-acetylbiphenyl, 1.96 g, 10.0 mmol)
   in ethanol (40 mL) in a 100 mL conical flask with a magnetic
   stirring bar, warming gently if necessary, then cool the solution to
   room temperature. Some ketone may crystallise again; this does no
   harm.
2. Stand the flask in a water bath at room temperature and add the
   sodium borohydride (0.227 g, 6.00 mmol) in four small portions over
   5 minutes (Note 1).
3. Stir the mixture at room temperature for the time the scope table
   gives for the ketone, 30 minutes for entry 1 (Note 2).
4. Check by thin-layer chromatography (silica, heptane–ethyl acetate
   3:1, UV at 254 nm) that no ketone remains; the alcohol runs lower
   than the ketone.
5. Cool the flask in an ice bath and add 1 M hydrochloric acid dropwise
   (about 10 mL) until gas evolution stops and the mixture is just
   acidic to indicator paper (Note 3).
6. For a homologous ketone, repeat steps 1 to 5 on the scale of its
   entry (10 mmol unless the scope table gives another), with 0.6
   equivalent of sodium borohydride and the stirring time of its entry.

## Workup and Purification

Remove most of the ethanol on a rotary evaporator (bath at 40 °C), add
water (40 mL) and extract the product with ethyl acetate in two 30 mL
portions. Wash the combined extracts with saturated sodium chloride
solution (30 mL), dry them over anhydrous sodium sulfate, filter and
evaporate. Recrystallise the white solid of entry 1 from a small volume
of hot heptane containing a little ethyl acetate, cool in ice, collect
by suction filtration and dry in air. Expected yield for entry 1: 1.78 g
(9.00 mmol, 90 %).

## Characterization

Determine the melting point of a solid product. The IR spectrum (ATR)
of each product shows a broad O–H stretch near 3350 cm⁻¹ and no ketone
C=O stretch near 1675 cm⁻¹, which distinguishes it from its starting
material. The ¹H NMR spectrum (CDCl₃) of each product shows a quartet
near δ 4.9 (1H) and a doublet near δ 1.5 (3H) for the CH(OH)CH₃ group;
for entry 1 the expected signals are δ 7.62–7.55 (m, 4H), 7.48–7.40 (m,
4H), 7.34 (t, 1H), 4.96 (q, J = 6.4 Hz, 1H), 1.85 (br s, 1H, OH),
1.55 (d, J = 6.4 Hz, 3H).

## Notes

1. Each mole of borohydride can reduce up to four moles of ketone, so
   0.6 equivalent is a comfortable excess. Adding it in portions keeps
   the slight warming and the hydrogen evolution under control.
2. The times of the scope table are the stirring times of step 3. Follow
   the reaction by thin-layer chromatography as in step 4 and stir
   longer if ketone remains.
3. The acid destroys the excess borohydride and hydrolyses the borate
   esters. Hydrogen is evolved; do this in a fume hood away from flames.
4. The products are racemates; the reduction creates a new stereocentre
   without any preference for either configuration.

## Hazards and Waste Disposal

Sodium borohydride releases flammable hydrogen with water and acids, is
toxic if swallowed, causes severe burns, and may damage fertility or the
unborn child; weigh it in a fume hood with gloves and eye protection, and
keep it away from water until it is used. Ethanol and ethyl acetate are
highly flammable. Quench every residue of borohydride with dilute acid
before disposal. Neutralise the aqueous layers and dispose of them as
aqueous waste, and collect the organic filtrates as halogen-free organic
waste; the filtrates of entry 3 contain bromine and go into the
halogenated organic waste.

## References

1. Furniss, B. S.; Hannaford, A. J.; Smith, P. W. G.; Tatchell, A. R.
   *Vogel's Textbook of Practical Organic Chemistry*, 5th ed.; Longman:
   Harlow, 1989.
