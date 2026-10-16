# Event-forcing preflight

Full-year independent circulation/boundary queries, not state integration; two tiny manufactured steps and 48 independent regional <=60-second probes (36 new + 12 exact frozen-step regression).

| Region | Max monthly incoming-water error | Max monthly mean velocity change | Max face component at lift 1 / 16 | Minimum step at lift 1 / 16 |
|---|---:|---:|---:|---:|
| california | 8.53e-14 mm | 2.34e-15 m/s | 27.72 / 27.74 m/s | 898.4 / 915.1 s |
| iberia | 5.68e-14 mm | 2.36e-15 m/s | 32.83 / 32.83 m/s | 1037.8 / 1040.3 s |

| Region | Coastal winter positive ascent, lift 1 → 16 | Annual boundary water dose | Normalization scale range |
|---|---:|---:|---:|
| california | 0.01862 → 0.02090 Pa/s | 2037.2 mm / full domain | 0.989–1.003 |
| iberia | 0.01416 → 0.01646 Pa/s | 1088.0 mm / full domain | 0.975–1.002 |

Synthetic event mechanism sensitivity; no observed event statistics, full thermal front or matched actual humidity distributions. Actual monthly gross import is enforced in future seasonal runs.

A forcing-only contrast audit tested fixed multipliers 1/4/16/32/64 before any seasonal result. Sixteen is the smallest with at least 10% more coastal winter positive ascent in both regions; four gives only about 1%. This chooses experimental contrast, not calibrated or observed storm strength. The original fourfold preflight and its source snapshot are preserved in output/v10_event_preflight/.

Two held-boundary controls run first and stop the batch if they materially differ from the old continuously interpolated-boundary climates. All cases retain zero prescribed incoming upper humidity; this assumption is not observed. No atlas publication or parameter search. No real seasonal run was launched during preflight.

User-run seasonal command:

```sh
caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run
```
