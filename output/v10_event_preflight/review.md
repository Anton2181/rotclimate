# Event-forcing preflight

Full-year independent circulation/boundary queries, not state integration; two tiny manufactured steps and 48 independent regional <=60-second probes (36 new + 12 exact frozen-step regression).

| Region | Max monthly incoming-water error | Max monthly mean velocity change | Max face component at lift 1 / 4 | Minimum step at lift 1 / 4 |
|---|---:|---:|---:|---:|
| california | 8.53e-14 mm | 2.36e-15 m/s | 27.72 / 27.73 m/s | 898.4 / 903.0 s |
| iberia | 5.68e-14 mm | 2.36e-15 m/s | 32.83 / 32.83 m/s | 1037.8 / 1038.3 s |

| Region | Coastal winter positive ascent, lift 1 → 4 | Annual boundary water dose | Normalization scale range |
|---|---:|---:|---:|
| california | 0.01862 → 0.01880 Pa/s | 2037.2 mm / full domain | 0.996–1.003 |
| iberia | 0.01416 → 0.01437 Pa/s | 1088.0 mm / full domain | 0.997–1.002 |

Synthetic event mechanism sensitivity; no observed event statistics, full thermal front or matched actual humidity distributions. Actual monthly gross import is enforced in future seasonal runs.

Two held-boundary controls run first and stop the batch if they materially differ from the old continuously interpolated-boundary climates. All cases retain zero prescribed incoming upper humidity; this assumption is not observed. No atlas publication or parameter search. No real seasonal run was launched during preflight.

User-run seasonal command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run
```
