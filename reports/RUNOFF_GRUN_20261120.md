# River seasons vs observed runoff: Earth test, 20 November 2026

**Outcome: the current model is validated; no change is adopted.** The monthly runoff that drives the map's river flood and
low-water indices has the right seasonal shape against GRUN, an observation-based global runoff reconstruction. Twelve alternative
settings did no better by the declared margin.

Protocol: [plan](../calibration/runoff_20261120/plan.json), declared before any score.

- **Target:** GRUN v1 (Ghiggi et al. 2019), averaged over 1970–2000.
- **Model:** `polity/seasons.py` on WorldClim over the Earth run's area (0–56° N, 12° W–125° E).
- **Scoring:** 2.5° blocks, split by a 10° checkerboard into development and blind halves.

## Results

| Blind (292 blocks) | Current (100 mm bucket, Hargreaves PET) | Best on development (100 mm, Droogers–Allen PET) |
|---|---:|---:|
| Seasonal shape, median correlation | **0.80** | 0.81 |
| Shape, lower quartile | 0.56 | 0.59 |
| Flood months (flow > 1.5× mean), F1 | 0.68 | 0.69 |
| Low-water months (< 0.4× mean), F1 | 0.60 | 0.61 |
| Annual runoff rank across blocks | 0.82 | 0.81 |
| Annual runoff, model / observed (median) | 0.38 | 0.49 |

Gates:
- **V passes:** the current seasonal shape is above 0.6, so the pattern is supported.
- **G1 fails:** the alternative's gain is +0.007, below the +0.05 needed.
- **G2 passes.**

## Notes

- **Bucket size.** On development, larger soil buckets (150–300 mm) damage the seasonal shape; smaller ones (25–50 mm) are no
  better than 100 mm.
- **Amount is low.** The model's runoff *amount* is about a third to a half of observed. The map uses runoff only relative to each
  basin's own mean, so floods and low water are unaffected. Any future use of absolute river discharge would need a level
  correction first.
- **Mud** (same bucket) was tested separately at weather stations and is unchanged.

Reproduce: `.venv/bin/python -I scripts/runoff_grun.py dev` and then `blind`. The blind run has been done once.
