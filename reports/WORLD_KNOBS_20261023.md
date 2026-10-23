# World knobs for the Earth-fit map — 23 October 2026

The question: which settings could the Earth-fit add, so the invented world matches
its painted zones better? The physics and chemistry stay Earth's. Gravity, day
length and year length stay Earth's too. A knob qualifies only if it describes the
world, not how air, water or radiation behave.

## What the Earth-fit can change today

The Earth-fit fits 16 world genes (`WORLD_GENES` in `rotclimate/calibrate.py`) with
r35's physics held fixed:

- Placement:
  - the latitude of the map centre;
  - which way is north;
  - the axial tilt;
  - the spin direction (held reversed in the fits).
- Height: the four terrain-tier tops.
- Surroundings off the map:
  - the land share beyond each side;
  - how continuous that land is;
  - its relief.

Everything else in the world is Earth's:

- the orbit (eccentricity 0.0167, perihelion 13 days after the winter solstice);
- the star (1,361 W m⁻²);
- the planet's land-by-latitude profile;
- the ocean's heat transport across the equator;
- the strength of the currents;
- any land poleward of the 1,100 km band modelled around the map.

## Where the Earth-fit fails

r35 physics with the r33 world refit, one surroundings layout, 32× coarse grid
(`scripts/probe_world_knobs.py`):

| Painted zone | Rule factor that fails | Model | The rule needs |
|---|---|---|---|
| Swamp (south-centre) | hot year | annual mean 14.6 °C; coldest month 3.3 °C | annual mean above 21 °C |
| Hot desert (far south) | aridity, heat | twice the dry threshold; annual mean 17.4 °C | below the threshold; annual mean above 18 °C |
| Cold steppe (north-centre) | aridity | 1.9× the dry threshold | below 1× |
| Tree (south-east) | humidity | 1.1× | above 1.6× |
| Warm-wet | mild winter | coldest month 0.6 °C | above 1 °C |
| Mediterranean | summer drought | driest summer month 34 mm against 94 in the wettest winter month | below a third of it |
| Cold-wet (north) | none | coldest month −2.2 °C | below 1 °C |

The hardest constraint is geometric. On the map the cold-wet zone ends and the
swamp begins only 4–9° of latitude apart. On Earth's east coasts, a coldest month
below 1 °C and an annual mean above 21 °C lie about 11° apart:

- the US: New York to Tampa;
- East Asia: Zhengzhou to Fuzhou.

East Asia's winter monsoon makes that the steepest such gradient on Earth.

## Candidate world knobs and their effect

Each probe changes one or a few settings, with every other world gene left where
the refit put it. A full refit lets the knobs trade against latitude and tilt, so
these numbers understate what a fit could find.

| Knob (physical meaning) | Probe | Zone-fit | Strict accuracy | Notes |
|---|---|---|---|---|
| none (start) | | 0.153 | 21.2 % | swamp annual mean 14.6 °C |
| **Orbital eccentricity and perihelion phase** (another orbit, same year) | e 0.03, perihelion at the summer solstice | 0.029 | 27.4 % | wetter-zone gains, but 22 % of the wet-summer lowland passes 30 °C (guard limit 5.6 %) |
| | e 0.045, perihelion at the summer solstice | −0.141 | 29.7 % | guard share 57 % |
| | e 0.045, perihelion at the spring equinox | 0.095 | 25.2 % | guard share 14 % |
| | e 0.06, perihelion at the summer solstice | −0.140 | 31.8 % | Mediterranean 0.21 → 0.38; guard penalty |
| | e 0.06, perihelion at the winter solstice | 0.151 | 18.6 % | |
| **Star brightness** (stellar flux; proxied by +1.5 / +3 °C on both land and sea) | +1.5 °C | 0.161 | 28.5 % | |
| | +3 °C | 0.134 | 27.8 % | warm-wet 0.45, tree 0.47; cold zones lost |
| | +3 °C, map 2° further north | 0.150 | 28.5 % | |
| **Ocean heat transport across the equator** (basin geometry, as the Atlantic's on Earth) | 2.0 PW (r35: 1.1) | **0.165** | 26.8 % | |
| | 3.0 PW | 0.134 | 24.9 % | |
| | −0.5 PW | 0.135 | 17.2 % | |
| **A continent poleward of the map** (land beyond the modelled band) | 2,000 km band, northern land 0.9 | 0.161 | 24.4 % | Mediterranean 0.21 → 0.37 |
| Boundary-current strength (ocean basin width) | ×1.5 | 0.155 | 22.6 % | little effect |
| The planet's land by latitude | uniform 30 % instead of Earth's | 0.147 | 19.0 % | worse |
| Map latitude (already a gene) | 3° further south | 0.148 | 20.1 % | |
| Combination | 2 PW, northern continent, e 0.03 at summer | −0.136 | **30.2 %** | Mediterranean 0.49; guard share 58 % |

Findings:

- **Eccentricity with perihelion near midsummer** is the strongest lever on
  accuracy. It gains 6–11 points from hotter summers. Those same summers break the
  realism guard against humid summers hotter than Earth's, so the zone-fit
  objective falls. Perihelion at the spring equinox avoids most of the penalty.
  The guard is part of the objective and should stay.
- **More ocean heat across the equator** (2 PW) is the best single change under the
  objective.
- **A larger northern continent** helps the Mediterranean band.
- **A brighter star** helps the warm zones and costs the cold ones. Latitude can
  partly offset that.
- **No knob makes the swamp.** Even +3 °C leaves its annual mean at 16–17 °C. Its
  rule needs a Florida-like annual mean above 21 °C at about 35° N, inside 9° of
  latitude from cold-winter forest. Earth's gradients do not allow that.

## Greenhouse and planet size (added on request)

Both are now knobs (`greenhouse_wm2`, `planet_radius`); defaults reproduce the
model exactly (the start re-scores 0.153).

- **Greenhouse:** a forcing in W m⁻² on the outgoing longwave of the zonal
  energy balance. Doubled CO₂ is about 3.7 W m⁻².
- **Planet radius**, with Earth's gravity, day and year (a denser planet):
  - a degree of latitude is radius × 111 km;
  - the zonal energy balance keeps the eddies' diffusivity in m² s⁻¹, so its
    diffusion in sin-latitude scales as 1 / radius²;
  - the Hadley cells' reach scales as radius^−½ (eddy-limited, Held 2000);
  - the storm-track, subsidence and subtropical-high widths keep their size
    in km, so in degrees they scale as 1 / radius.

  These scalings are first-order theory, not Earth-tested physics.

| Probe | Zone-fit | Strict accuracy | Swamp annual mean | Cold-wet coldest month |
|---|---|---|---|---|
| start | 0.153 | 21.2 % | 14.6 °C | −2.2 °C |
| greenhouse +3.7 W m⁻² | **0.160** | 26.2 % | 16.5 | −0.2 |
| greenhouse +7.4 W m⁻² | 0.015 | 23.7 % | 18.5 | +1.8 (guard share 22 %) |
| radius 0.9 | 0.152 | 20.9 % | 15.2 | −0.1 |
| radius 0.8 | 0.110 | 9.9 % | 15.7 | +2.2 |
| radius 0.7 | 0.083 | 5.5 % | 16.1 | +4.2 |
| radius 0.8, 3° further south | 0.088 | 5.2 % | 16.4 | +3.3 |
| radius 0.8, greenhouse +3.7 | 0.086 | 6.0 % | 17.5 | +4.1 |
| radius 1.15 | 0.147 | 20.4 % | 13.4 | −5.1 |
| radius 1.3 | 0.120 | 14.2 % | 12.1 | −7.8 |
| radius 1.3, 3° further south | 0.152 | 21.3 % | 14.5 | −4.6 |

**A smaller planet flattens the map's north–south contrast.** The map spans
more degrees of latitude, but heat spreads across a smaller sphere more easily,
and the wider Hadley cells push the subtropical high north. The north warms more
than the south.

**A larger planet steepens the contrast.** At 1.3 × Earth's radius the north's
winter falls 5.6 °C and the swamp cools only 2.5 °C. Moved 3° south, it keeps
the start's zone-fit with a 2.4 °C colder northern winter. The combination the
painted zones ask for, a larger planet, further south, with a stronger
greenhouse, is for the joint world-plus refit to find.

## Knobs left out

- **Atmospheric mass:** surface pressure changes the atmosphere's physics. Greenhouse
  forcing was added on request (above).
- **Gravity, rotation rate and orbital period:** fixed by the question.
- **Planet radius** was added on request (above), with the circulation rescaled by
  theory.
- **Soil depth and vegetation** (the soil bucket). Arguably the world's geology,
  but it is one of the land-surface settings calibrated on Earth's average.

## Recommendation

Add seven world genes to the Earth-fit (`--physics worldplus`):

| Gene | Range | Code |
|---|---|---|
| eccentricity | 0–0.06 | exists |
| perihelion phase | full year | exists |
| stellar flux | 0.96–1.04 × Earth's | new `solar_flux` (EBM and land insolation) |
| ocean heat transport across the equator | −0.5 to 2.5 PW | exists |
| poleward land beyond the grid | 0–1 | new `far_pole_land` (continental cold, e31) |
| greenhouse forcing | −2 to 8 W m⁻² | new `greenhouse_wm2` |
| planet radius | 0.6–1.3 × Earth's | new `planet_radius` |

Then refit the world with the same budget and objective as the standard refit,
and compare the two on the three-layout publication climate. Defaults reproduce
today's model, so the Earth benchmark and the other fits are unaffected.
