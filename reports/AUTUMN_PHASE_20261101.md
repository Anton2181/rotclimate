# Subtropical land peaks early: the marine air is too continental — 1 November 2026

P7 diagnosis on r41. **Scripts:** `scripts/diag_autumn_phase.py`; the
marine-air comparison is in the session scratchpad (`marine_air.py`).
**Output:** `output/autumn_phase_20261101/` (`diag.json`,
`marine_air.json`).

## 1. The phase error on r41

Each dev31 region's first harmonic, model against observed (from r41's
dev31 run, `output/spring_refit_20261101/refit41/candidate_dev31`).

**Subtropical land at 28–39° peaks early, by 4–9 days.** Its autumns are
2–3 °C colder than its springs, relative to the observations:

| region | phase | spring | autumn |
|---|---:|---:|---:|
| Levant | −9 d | +0.3 | −3.0 |
| Japan | −9 d | +3.6 | +0.6 |
| East China | −8 d | +3.8 | +1.4 |
| Anatolia | −8 d | +0.7 | −2.0 |
| Iran plateau | −6 d | −2.0 | −4.2 |
| Morocco | −5 d | −0.4 | −2.0 |
| Korea | −5 d | +3.6 | +1.6 |
| Texas plains | −4 d | 0.0 | −1.4 |
| southeast US | −5 d | +1.0 | −0.6 |

**The maritime mid-latitudes peak late,** with springs too cold:

| region | phase |
|---|---:|
| New Zealand | +31 d |
| British Isles | +28 d |
| Patagonia | +22 d |
| western Europe | +20 d |
| Pacific NW | +8 d |
| eastern Europe | +8 d |
| Alps | +8 d |

## 2. It is not the sea surface or the circulation

The nine early regions were re-run with the existing diagnostic switches:
the observed sea surface (WOA18), observed winds (NCEP), and both. The
table gives the phase error in days.

| region | model | WOA18 sea | NCEP winds | both |
|---|---:|---:|---:|---:|
| Levant | −9.1 | −8.6 | −9.4 | −8.7 |
| Anatolia | −7.9 | −7.3 | −8.7 | −8.1 |
| Iran plateau | −5.7 | −5.3 | −7.8 | −7.7 |
| Morocco | −5.4 | −7.3 | −6.5 | −6.8 |
| Japan | −8.8 | −7.9 | −7.8 | −7.1 |
| East China | −8.1 | −8.4 | −8.9 | −8.9 |
| Korea | −5.1 | −4.1 | −4.2 | −3.3 |
| Texas plains | −4.3 | −2.9 | −2.2 | −2.1 |
| southeast US | −5.1 | −5.2 | −2.3 | −2.5 |

**Neither swap removes the early phase.** Observed winds help only the US
Gulf coast, and they worsen its mean error.

## 3. The air over the sea does not follow the sea

Over each region's sea cells, the model's air temperature was compared
with NCEP's observed 995 hPa air temperature.

| region | phase vs NCEP | amplitude ratio |
|---|---:|---:|
| Levant | −17 d | 1.31 |
| Anatolia | −11 d | 1.25 |
| Japan | −13 d | 1.13 |
| Korea | −12 d | 1.12 |
| East China | −10 d | 1.01 |
| southeast US | −10 d | 1.23 |
| Texas plains | −9 d | 1.15 |
| Iran plateau | −8 d | 0.81 |
| Morocco | +3 d | 1.21 |

- **The model's marine air is too continental.** It peaks 8–17 days early
  in 8 of the 9 regions and swings 10–30 % too far.
- **The real marine air** already leads the sea surface by 15–30 days.
- **With the observed sea surface imposed,** the model's marine air still
  leads WOA18 by about 31–36 days, much as without it. The air over the
  sea is barely tied to the water.

**The cause is in the numbers:**
- r41 relaxes the air over the sea toward the sea surface on a 2.7-day
  timescale (`ocean_tau_days`, a rate of 0.37 a day).
- Its eddy mixing pulls every cell toward the 850 km regional mean at a
  rate of 1.43 a day (`eddy_rate`, `eddy_scale_km`). Next to a continent
  that mean is set by the land.
- So coastal seas carry the land's early, wide swing back onto the coast.
  Autumn on the coast is then as cold as the land behind it, instead of
  being held up by the still-warm sea.

## 4. Screen: fast air–sea coupling (not taken forward)

The two existing opt-in switches let air take the sea's temperature
faster wherever the two differ. Both are off in r41:
- **e51** (`ocean_tau_unstable`): cold air over a warm sea;
- **e3** (`ocean_tau_stable`): warm air over a cold sea.

Each was screened at a 0.5-day coupling time on nine regions
(`output/autumn_phase_20261101/couple.json`). The table gives each region's
mean error in °C and its phase error in days.

| region | r41 | e51 0.5 d | e51 + e3 0.5 d |
|---|---:|---:|---:|
| Levant | 2.19 (−9.1 d) | 2.11 (−8.8) | **2.00** (−8.2) |
| Anatolia | 1.80 (−7.9) | 1.68 (−7.5) | **1.51** (−6.6) |
| Texas plains | 1.36 (−4.3) | 1.34 (−4.3) | **1.30** (−3.8) |
| British Isles | 2.16 (+28.4) | 1.94 (+29.5) | **1.90** (+27.7) |
| western Europe | 1.73 (+19.5) | 1.79 (+19.7) | **1.69** (+18.9) |
| New Zealand | **1.83** (+30.5) | 1.84 (+30.4) | 1.92 (+31.2) |
| Japan | **1.84** (−8.8) | 3.05 (−5.3) | 2.93 (−4.1) |
| Korea | **2.04** (−5.1) | 2.95 (−3.3) | 2.81 (−2.4) |
| East China | **2.06** (−8.1) | 2.51 (−8.0) | 2.50 (−7.8) |

**What the screen shows:**
- **Tying the marine air to the sea works where it should.** The
  Levant's marine air now leads the sea by 26 days instead of 33, and the
  Mediterranean coasts and the British Isles improve.
- **It moves the land's phase by only about a day.** East Asia is the
  exception, at 3–5 days.
- **It warms East Asia's coasts.** Those coasts are already 2–4 °C too
  warm in spring and autumn, and their error rises by 0.4–1.2 °C.

So the coupling switch cannot be adopted while East Asia's warm seasons
stand (P6). It was not run on dev31.

## What it leaves

- **The early phase of subtropical land is mostly the land's own.** In
  r41 the land relaxes to its equilibrium in about 1.3 days
  (`land_tau_days`), and that equilibrium follows the sun.
- **The coupling is half of the answer.** It is the right physics for
  the coasts, and it becomes usable once East Asia's spring warmth is
  fixed.
- **The next step is P6**, East Asia's spring: monsoon ascent and frontal
  rain. Then rescreen e51 + e3 on dev31.

## Addendum, 8 November 2026: the coupling re-screened on r44 (after P6)

Same nine regions and settings, on the released r44 physics (`scripts/diag_autumn_phase.py --params
calibration/local_accuracy_20261023/r44_params.json`; `output/autumn_phase_20261108/couple_r44.json`). Mean error, °C:

| region | r44 | e51 0.5 d | e51 + e3 0.5 d |
|---|---:|---:|---:|
| Levant | 2.01 | 1.94 | **1.76** |
| Anatolia | 1.78 | 1.68 | **1.44** |
| Iran plateau | 2.47 | **2.39** | 2.42 |
| Morocco | 1.72 | 1.72 | **1.65** |
| Texas plains | 1.10 | 1.08 | **1.06** |
| south-east US | 1.13 | 1.13 | 1.13 |
| Japan | **1.77** | 2.96 | 2.86 |
| East China | **2.06** | 2.60 | 2.59 |
| Korea | **2.01** | 2.89 | 2.77 |
| mean | **1.78** | 2.05 | 1.97 |

* **P6 did not remove the conflict.** The fast coupling still helps the Mediterranean and Texas, and still overheats
  East Asia's coasts. Korea's autumn bias goes from +1.8 to +2.8 °C, and Japan's from +0.7 to +2.1 °C.
* **Why East Asia.** Cold continental air crosses a warm sea there, the Sea of Japan and the Kuroshio. A 0.5-day
  unstable coupling brings it almost to sea temperature before it reaches land. The real outflow stays cold in its
  deep boundary layer.
* **Verdict.** A global switch is not adoptable. P8 needs a coupling that depends on the air mass's depth or fetch,
  not on the sea alone. No dev49 run and no sealed set were spent.

## Addendum 2, 8 November 2026: plan P8a (frozen refit), not adopted

Plan: `calibration/maritime_p8_20261108/plan.json`. A new switch, e51b (`ocean_unstable_cap`), puts a K/day ceiling on
e51's convective warming, because a deep cold outbreak warms only so fast. It is default off.

| Candidate | S49 | T | P | 28 km |
|---|---|---|---|---|
| C1: e3 at 0.25 days | 0.9931 | −1.7 % | +0.3 % | 0.990 |
| C2: e3 at 0.5 days | 0.9921 | −1.7 % | +0.1 % | 0.991 |
| **C3: e51 at 0.5 days + 2 K/day ceiling + e3 at 0.5 days** | **0.9910** | −2.1 % | +0.3 % | 0.992 |
| C4: as C3, with e3 at 0.25 days | 0.9914 | −2.2 % | +0.5 % | 0.990 |

* **Stage 1.** All four pass the development (S49) and 28 km gates. C3 is the finalist.
* **Stage 2.** Sealed set h was released by the owner and run once, paired with r44. It scored **S 1.0014: fail**
  (T +1.7 %, P −1.5 %).
* **Where it failed.** The temperature loss is on the tropical coasts:
  * Top End 2.02 → 2.24 °C, its cool bias deepening from −1.79 to −2.05;
  * New Guinea 1.58 → 1.73 °C;
  * Ivory Coast 0.71 → 0.76 °C.
  Taimyr improves, and rain improves where the temperature worsens.
* **Why.** The stable coupling (e3) pulls the dry-season air of tropical coasts down to the sea's temperature. The 49
  development regions barely sample such coasts.
* **Verdict.** r44 stays. Set h is spent. A next attempt should:
  * restrict e3 to seas cooler than the tropical warm pool, or to the cool season;
  * develop on h's tropical coasts, now seen;
  * declare a fresh unseen set before its milestone.
