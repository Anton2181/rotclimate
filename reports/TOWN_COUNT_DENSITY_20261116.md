# Town count against population density (development diagnostic) — 16 November 2026

Question (after both blind size failures): does the model place too few towns where people were dense? Data: the count study's
Earth blocks (`output/settlement_counts_20261111/blocks.npz`; development pools, exposed): per block the model's people, the
production town count, and the catalogue count (Hanson's Roman cities; the Han records).

| Pool, block size | densest 10 % of blocks: model / catalogue towns | below-median density |
|---|---|---|
| Rome, 100 km | **2.31** | 0.96 |
| Rome, 300 km | **2.79** | 0.76 |
| Han, 100 km | **3.89** | 1.20 |
| Han, 300 km | **6.93** | 1.15 |

The opposite of the starting guess: in dense cores the model places **2-7 times too many** towns, at about the right count
elsewhere. Real dense cores concentrated their people in fewer, larger cities; the model divides them among many small towns.
Together with the size model's weak dependence on hinterland people (0.147 lnH), that explains both blind size failures (southern
Mesopotamia: no town above 200 ha; the Valley of Mexico, the reverse case: maize-only densities too low for any town in the
surveyed area).

The 11 November count study already pointed the same way: a count proportional to density^beta fits best at beta 0.5 (covered
blocks, equal-pool deviance 2.27 per record, vs 2.43 at beta 1 and 2.43 at beta 0); it was not adopted (zero-prediction blocks
gave infinite deviance on the full domain), and production still counts in proportion to people.

## Work package (proposed): density-saturating town count

1. Replace the production count's proportionality with density^beta inside dense cores (development fit on Han and Rome, blocks
   cross-validated by quadrant as before), keeping total counts calibrated.
2. Let the people the removed towns would have held go to the remaining towns' hinterlands (sizes follow).
3. Validate on an unseen pool: both earlier blind pools are spent; a new one is needed (the bottleneck).
4. Only then republish the map through the chain runner (proposed towns in the densest provinces would thin out and grow).
