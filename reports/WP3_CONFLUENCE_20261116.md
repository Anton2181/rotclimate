# WP3: river confluences as a town-site factor — 16 November 2026

Development screen (`calibration/wp3_site_factors_20261116/plan.json`, `scripts/wp3_site_factors.py`): the release-3 site prior
multiplied by (1 + k x confluence within 15 km), count matched to each catalogue. Composite (F1 within 25 km, block-count rank,
nearest-neighbour KS):

| k | Han | Rome |
|---|---|---|
| 0 (release 3) | 0.568 | 0.529 |
| 0.5 | 0.573 | 0.543 |
| **1.0** | **0.587** | **0.540** |

k = 1.0 passed the declared screen (+0.019, +0.012; bar 0.01 on both).

## Blind test (`blind_buringh.json`, amendment A1; `scripts/wp3_buringh_blind.py`)

Buringh 2021 European urban population (CC0), cities of at least 5,000 at 1300 with source or proxied (not imputed) estimates, in
a 1,400 x 1,000 km window over France, the Low Countries and western Germany (146 distinct city cells;
494 rows with broken coordinates dropped). No roads (medieval roads unknown).

| | composite | F1 | recall | precision | block rank |
|---|---|---|---|---|---|
| release 3 (k = 0) | 0.431 | 0.279 | 0.295 | 0.265 | 0.29 |
| confluences (k = 1) | 0.458 | 0.304 | 0.315 | 0.295 | 0.40 |

**Gain +0.028 (bar 0.01): PASS.** The first site factor to pass an unseen test. The pool's position use is now spent;
its population values (sizes) stay reserved.

Next: declare the map integration (the drawn rivers' confluences in the release-3 prior) and republish through the chain runner.
