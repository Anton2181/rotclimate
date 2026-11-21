# River runoff amount vs observed runoff: Earth test, 21 November 2026

**Outcome: adopted.** The Budyko–Fu curve (w = 2.6) replaces the monthly cap rule for annual runoff, the input to absolute river discharge. Discharge sets delta-fan size and the simulated river network. All three blind gates pass.

Protocol: [plan](../calibration/runoff_amount_20261121/plan.json), declared before any score.

- **Target:** GRUN v1, observation-based global runoff, averaged over 1970–2000.
- **Model input:** WorldClim monthly temperature and rain, the rule's only inputs.
- **Split:** cells of 0.5°, divided into development and blind halves by a new 10° checkerboard offset by 5° from the earlier runoff test.

| Blind half (10,061 cells) | Current (P − 0.75 PET monthly) | Adopted Fu, w 2.6 |
|---|---:|---:|
| Log error, RMSE of ln((m+10)/(o+10)) | 0.872 | **0.657** (−25 %) |
| Median model/observed | 0.81 | 0.87 |
| Spearman rank | 0.863 | 0.904 |

Gates:
- **G1** (error ≤ 0.85 × current): pass.
- **G2** (rank not more than 0.02 worse): pass.
- **G3** (median ratio within 0.8–1.25): pass.

w = 2.6 is the standard global Fu value; it was chosen on the development half from {1.5, 2.0, 2.6, 3.5}.

Figure: [reports/figures/runoff_amount_20261121.png](figures/runoff_amount_20261121.png).

What the current rule got wrong:
- It gave the wet monsoon and equatorial belts too much runoff and the dry belts and steppe too little.
- Fu fixes most of that.
- What remains: the Tibetan Plateau and Mongolia are still too dry. GRUN there includes snow and glacier melt.

**Why it matters:** `data/delta_fan_model.json` sizes deltas from discharge using a fit to **observed** discharge (area ~ Q^1.06), so the map's discharge has to be at Earth level for that fit to hold.

**Wiring:**
- `rotclimate/routing.py` takes the Fu rule for both `runoff_from_months` (deltas) and `fine_discharge` (simulated rivers).
- `rotclimate/hydrology.py` (climate diagnostics, part of the simulation identity) is unchanged.
- The atlas changes at the next full rebuild, because deltas feed the harvest cascade.

Reproduce: `.venv/bin/python -I scripts/runoff_amount_grun.py dev`. The blind run has been done once.
