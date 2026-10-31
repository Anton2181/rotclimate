# State strength at contested borders, 31 October 2026

Idea: larger, richer polities hold land farther from their own roads and
towns. Plan frozen before any run: `calibration/polity_20261025/plan_strength_20261031.json`;
script `scripts/polity_strength_check.py`; results
`output/polity_strength_20261031/strength.json`. **Not adopted; political
reach on the maps is unchanged.**

## Data, restored for this test

The Earth inputs of the political-reach checks had been fetched by hand in an
earlier container. Rebuilt with `scripts/prepare_polity_data.py` (sources and
hashes in `data/cache/polity_sources.json`, not committed): Cliopatria v0.2.1
(Seshat, CC BY 4.0; subsets for AD 2/117/150 and 742/1102/1820), Hanson's
(2016) OxREP cities (1,354 standing in AD 150), Itiner-e static 2024 roads
(Zenodo 10.5281/zenodo.17122148; 14,616 segments of AD 150), Zheng & Wu's
(2026) county seats (1,294 for AD 2), the Natural Earth rivers, and the Earth
land and people grid (`scripts/land_people_earth.py`). `polity.earth._ncep`
now reads the cached NCEP long-term means. The E3 steppe borders reproduce
their archived balanced accuracies exactly (0.967 and 0.934).

## Rule and result

Each polity's taxable base F is the modelled people within 2 year-round days
of its own sources; a cell goes to the polity with the smallest days / k,
k = (F / √(F_A F_B))^γ (γ = 0 is today's nearest-network rule).

| contest | bases F (M people) | γ = 0 | 0.1 | 0.2 | 0.3 | 0.5 |
|---|---|---:|---:|---:|---:|---:|
| Rome vs Parthia, AD 150 (fit) | 15.7 / 14.5 | **0.993** | 0.993 | 0.993 | 0.993 | 0.993 |
| Han vs Xiongnu, AD 2 (test) | 24.8 / 5.3 | **0.967** | 0.960 | 0.950 | 0.941 | 0.921 |
| Tang vs Türgesh, AD 742 (test) | 27.0 / 12.5 | 0.934 | 0.937 | 0.945 | **0.953** | 0.952 |

The fit selects γ = 0, so by the frozen rule nothing changes; the tests also
disagree with each other. Strength pushes Han's reach past the Xiongnu border
(Han right 0.985 → 0.995, Xiongnu right 0.949 → 0.846 at γ 0.5): the AD 2
border sat where the farming state's reach ran out, as E3 found. For Tang
against the Türgesh it helps (0.934 → 0.953 at γ 0.3), mostly by giving Tang
the farmed oases its own seats reached slowly.

**Design flaw, recorded:** the fit contest is uninformative. The Parthian
seats were placed inside the Cliopatria polygon, so the nearest-network rule
already reproduces the Roman-Parthian border to 99.3 % and the two bases
inside the window are nearly equal (strength ratio 1.04); no γ can move it.
A better fit case needs two polities whose networks come from independent
data (both from towns and roads, not from seats placed inside the polygons
being tested). The ORBIS dataset (sailing and river times, test T7) was not
re-fetched.
