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

## 4. Screen: fast air–sea coupling (in progress)
