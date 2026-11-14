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

## Where the remaining east/west gap sits (post-hoc, exploratory)

`scripts/east_gap_diagnostic.py` → `output/supply_people_level_20261114/east_gap_diagnostic.json`. Frier level, 270 km,
at the west's 95% share (0.345): the west is 95.1% fed and the east 88.6%.

| Eastern region | Residents | Fed | Shortfall (person-years) |
|---|---:|---:|---:|
| Greece and Aegean | 1.30 M | 74% | 339,000 |
| Egypt | 1.21 M | 83% | 212,000 |
| Asia Minor | 1.28 M | 96% | 50,000 |
| Levant, Syria, Cyrenaica, Balkans | 1.27 M | 100% | 0 |

The largest single shortfalls are:
- **Arsinoe in the Fayum** (126,000 residents, 3% fed). The Fayum lies beyond the rule's 30 km reach from the
  Nile; historically it was watered through the Bahr Yusuf.
- **The Peloponnese towns** Corinth, Argos, Tegea, Mantinea, Orchomenus and Phlius (6–15% fed).
- **Athens** (63% fed).

**Two hypotheses, neither tested:**

1. **Greek areas are wall circuits.** In Hanson's catalogue 65% of Greek areas are walls, against 37% elsewhere.
   Classical circuits such as Tegea (190 ha), Argos (199 ha) and Mantinea (121 ha) enclosed open ground, so residents
   at the sliding density may be overstated there. A quantitative inhabited share for Greek circuits was not found
   in this search (Hansen's *Shotgun Method* is the likely source), so no correction is made. Sizes on the map stay
   as the owner set them; any correction would be a calibration-side sensitivity first.
2. **The Fayum needs its canal.** Basin land fed by the Bahr Yusuf is outside the rule's reach. A canal-fed basin is
   a different rule, and it would need its own Earth evidence.
