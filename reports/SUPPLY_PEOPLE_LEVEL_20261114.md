# People level for the supply calibration: Egypt fed, whole empire still just short — 14 November 2026

Plan: `calibration/supply_people_level_20261114/plan.json`, committed (3244339a) before output. Owner: "Fix the people side
first, then port to the fantasy map." Floodplain rule in production as in FLOODPLAIN_RULE_20261114 (A2).

The heartland people pattern (capacity on the floodplain grid × exp(−D/800 km)) is set to one of two levels:
- **Frier (primary):** scaled to 61.4 M on Roman land (Frier 2000, AD 164).
- **Absolute:** no rescaling.

| Level (270 km) | Empire | Egypt proper | e95 west / east | West→east / east→west | Passes |
|---|---:|---:|---|---|---|
| **Frier 61.4 M** | 61.4 M | 5.77 M | 0.35 / 0.43 (×1.24, kept) | **0.884** / 1.00 | **no** (transfer < 0.90) |
| Frier, without Egypt | 61.4 M | — | 0.35 / 0.37 | 0.93 / 0.97 | yes, e95 0.357 |
| Absolute | 51.5 M | 4.83 M | 0.32 / 0.42 (×1.33) | 0.96 / 0.94 | no (270 km not kept; best 135 km) |
| Absolute, without Egypt | 51.5 M | — | 0.32 / 0.42 (×1.32) | 0.95 / 0.95 | no (270 km not kept) |

**Result: the declared fix fails, narrowly.** Egypt itself is no longer the blocker. With the Frier level, Egyptian
cities are 89% fed at share 0.4 and 96% at 0.5 (46% with the committed field, 0% at the start of the day). The
remaining gap is a general east/west difference of about 1.24–1.33×, which appears even without Egypt at the
absolute level. Under the Frier level the west's setting feeds 88.4% of the east, against the declared 90%.

**What it says about the adopted share.** Every passing or near-passing run puts the 95% share between 0.36 and
0.43, around the adopted 0.39. With Egypt and the Frier level, e95 for all cities is 0.388.

**Checks.** The review rebuilds every e95, the haul-limit choice, the transfer flags and the level arithmetic
(60 checks). A fresh run is byte-identical.

**Next, per the owner:** port the floodplain rule to the fantasy map as its own declared step. Egypt's supply is now
fed in development, but the whole-empire test is still not passed.
