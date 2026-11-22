# Dry summer-rain margins under r50 — diagnosis only (22 Nov 2026)

Rain ratio (model/obs, dev49): Namibia-Kalahari 0.10 (worst region, loss 1.06), south Brazil 0.48, Bengal 0.52,
Mexico 0.65, north India 0.64, Texas 0.63, SW Australia 0.37.

Moisture budgets (r50, scripts in scratch, outputs budget_*.txt; mm/day, mirrored calendar for the south):
- Kalahari: 1-3 mm/day imported (advection + storms) is all removed by column drying (-2 to -3.8, mostly the
  e70b branch core at 0.278/day); soil evaporation ~0; convergence import ~0 even in summer; P ~0 Oct-Mar (obs 1.6/day).
- Algeria-Sahara: the same drying, but the land rain belt's convergence import reaches it in Jul (1.9 mm/day).
- Najd: drying + monsoon descent (-1.9 Jul). South Brazil, Mexico: column drying -2.3/-3.4 at the wet-season onset.
So the Kalahari's summer is the Sahara's in model terms: the land rain belt (convergence import) does not reach
20-26 S over southern Africa. A heat-low gate on the drying (e80/e80b) already failed on the deserts. Needs a
circulation change (the summer continental rain belt's poleward reach in the south), not another drying gate. Parked.
