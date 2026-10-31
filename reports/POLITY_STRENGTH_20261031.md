# State strength at contested borders, 31 October 2026

Idea: larger, richer polities hold land farther from their own roads and
towns. Plan frozen before any run: `calibration/polity_20261025/plan_strength_20261031.json`;
script `scripts/polity_strength_check.py`; results
`output/polity_strength_20261031/strength.json`. **Not adopted; political
reach on the maps is unchanged.** A second design with networks independent
of the polygons (below) confirms it: no strength term.

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

## Second design: networks independent of the polygons (not adopted)

Addendum `calibration/polity_20261025/addendum_strength_cities_20261031.json`,
frozen before its runs. Parthia's network is now its royal and vassal
capitals from the literature (Ctesiphon, Babylon, Susa, Ecbatana, Rhagae,
Hecatompylos, Nisa, Merv, Spasinou Charax, Arbela, Istakhr, Ganzak, Hatra);
the blind test sets Han's AD 2 county seats
against the excavated Xiongnu elite centres (Noin-Ula, Gol Mod, Ivolga,
Tsaraam, Terelj, Duurlig Nars, Egiin Gol) instead of density camps inside the
Xiongnu polygon. All contests use the travel model as adopted at run time
(with the autumn-mud topsoil layer). Results
`output/polity_strength_20261031/strength_cities.json`.

| contest | γ = 0 | 0.1 | 0.2 | 0.3 | 0.5 |
|---|---:|---:|---:|---:|---:|
| Rome vs Parthia AD 150, Parthian capitals (fit) | **0.965** | 0.943 | 0.928 | 0.849 | 0.656 |
| Han vs Xiongnu AD 2, excavated centres (blind test) | **0.728** | 0.650 | 0.594 | 0.557 | 0.515 |
| Han vs Xiongnu AD 2, density camps (seen) | **0.967** | 0.960 | 0.950 | 0.941 | 0.921 |

The fit is now informative (Parthia right 93 % at γ = 0, 31 % at 0.5) and it
chooses γ = 0: within two days of its own network Rome's taxable base is
15.7 M people against 0.63 M for Parthia's thirteen capitals, and every
strength term pushes Rome past the Euphrates. The blind test agrees. The plain
nearest-network rule stays. One thing it shows: with only seven Xiongnu
centres, all far north of the Gobi, Han's reach takes half of the Xiongnu
polygon (Xiongnu right 46 %); a pastoral polity's reach comes from its
herds and seasonal camps, which the camps version represents and the
centres do not.
