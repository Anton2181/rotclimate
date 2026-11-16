# Valley of Mexico blind test (WP6) — 16 November 2026

Declared in `calibration/valley_of_mexico_blind_20261116/plan.json` before any value of the pool was read (headers only);
amendment A1 after the declared minimal reads (period labels, coordinate and area ranges), before scoring. Scored once by
`scripts/valley_of_mexico_blind.py`; the pool is now spent.

Model: the New World Earth run (maize only, FAO 66 parameters; `output/maize_20261116/mexico_newworld`), the release-3
placement rule with history from three Mesoamerican cores outside the Basin (San Lorenzo, San José Mogote, El Mirador), the
published size model. Pool: Parsons/Blanton regional survey, Classic and Early Classic sites (221 sites, 27 of at least 10 ha).

| Test | Result | Bar | Verdict |
|---|---|---|---|
| P positions (3 km grid, Classic towns ≥ 10 ha) | release-3 field percentile **0.616** (environment 0.611) | ≥ 0.55 and capture not worse | **pass** |
| N people in the surveyed area (3,294 km²) | model **34,800** vs survey 20,200 (PopMin 9,700): ratio **1.72** | 0.5-2.0 | **pass** |
| S sizes (9 km grid) | **no model town inside the surveyed area** (10 towns in the whole 160 × 180 km window) | KS ≤ 0.20, total 0.67-1.5 | **fail** |

Notes:
* The positions pass is moderate (the environment field alone reaches 0.611; the Mesoamerican history prior adds little at
  this scale). The 10 km capture is 0 for both placement rules: with maize-only rural densities (~10 per km²) the town rule
  places few towns.
* The survey excludes the city of Teotihuacan (largest site 840 ha; the city, ~2,000 ha and ~100,000 people, was mapped by the
  separate Teotihuacan Mapping Project), so the people test compares the model with the rural Basin; the model's 1.7×
  over-count of the countryside is consistent with a Classic Basin whose people were concentrated in the city.
* The size failure is the same finding as southern Mesopotamia: the model makes too few and too small towns where real
  populations were urban and concentrated; it is a count/primacy problem, not a placement one.

First blind test of the maize crop model and the New World pipeline: positions and rural people pass, towns fail.

## Post-hoc (after scoring; the pool is spent): people per hectare

The survey's Classic sites hold **18.4 people per ha** (20,227 people on 1,099 ha; median 14-20 per ha in every size class).
The size model and the resident rule were fitted on Roman and Greek walled towns at 100-500 per ha. A "10 ha town" in the
Classic Basin held ~200 people: Mesoamerican settlements were low-density, with house-lot gardens. The size test therefore
compares unlike things (area-based Old World towns vs sprawling villages), and its failure says the size and density rules do
not transfer to Mesoamerica as they stand; a New World density rule would need its own Earth evidence. The positions and
rural-people results do not depend on this.
