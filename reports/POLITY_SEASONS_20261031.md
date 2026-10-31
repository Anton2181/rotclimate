# Political reach: autumn mud and monsoon coasts, 31 October 2026

Two of the open items of `reports/POLITY_V2_20261025.md` ("Open"), tested
under an addendum frozen before any run:
`calibration/polity_20261025/addendum_seasons_20261031.json`. Station
climate: WorldClim 2.1 5′ monthly mean, maximum and minimum temperature and
rain (`scripts/polity_season_stations.py`, results
`output/polity_seasons_20261031/stations.json`); winds: NCEP/NCAR
1981–2010 monthly vector means. **Neither change is adopted; the atlases'
political reach is unchanged.**

## Autumn mud (topsoil layer, opt-in, not adopted)

The travel model's mud comes from a 100 mm soil bucket nearly full or a
month of snowmelt, so the bucket emptied by summer leaves the autumn dry:
Kyiv had mud in March only (expected March, April, October, November). The
change adds a 25 mm topsoil layer, part of the same bucket (soil totals,
runoff and the river floods are unchanged by construction), filled first by
rain and melt and emptied first by evaporation; mud also when it is nearly
full.

| station | mud months (≥ 0.5) before | with the topsoil layer |
|---|---|---|
| Kyiv | Mar | Mar, Nov |
| Moscow | Apr | Apr, Oct |
| Rome | Jan–Mar, Dec | Jan–Mar, Nov, Dec |
| Patna | Jul–Sep | Jul–Sep |
| Cairo | none | none |
| Beijing | none | Jul, Aug (monsoon rains) |

Moscow now has its spring and autumn rasputitsa and no dry season gains mud,
but Kyiv reaches 2 of its 4 months (October and April stay dry: Hargreaves'
evaporation in a cloudy October is still about equal to the rain), short of
the frozen rule's 3. Not adopted; `polity.seasons.TOPSOIL_MM` stays 0. The
Roman and Han extent tests that would show its effect on year-round control
could not be rerun here (their datasets are not in this container).

## Monsoon coasts (diagnostic, not adopted)

The sea's closure uses storminess (the swing of the wind about its mean,
fitted to Vegetius' season) and strong mean winds, so the steady south-west
monsoon left the Konkan coast open all summer (test T5 failed). The
diagnostic rule closes sea within 100 km of land where the monthly mean
wind blows onshore at Beaufort 4 (uncertain, 5.5 m/s) or 5 (closed, 8 m/s).

| place | onshore wind, m/s (Jan … Dec) | result |
|---|---|---|
| Konkan coast, 16° N 71° E | −1.6 … 6.5 (Jun) 8.9 (Jul) 7.7 (Aug) … −2.8 | uncertain Jun and Aug, closed Jul, open Dec–Feb: **as expected** (T5's numbers were known, so not blind) |
| Coromandel coast, 13° N 81° E | 2.4 … 1.4 (Nov) 1.6 (Dec) | open in November: **fails** (NCEP's 2.5° winds barely see the north-east monsoon there) |
| Alexandria approaches | at most 4.7 (Jul) | open all summer: as expected |
| Gulf of Lion | offshore all year | open all summer: as expected |

One of the four expectations fails, so by the frozen rule the rule is not
carried to the map (the map has no monsoon coast, and its model sea winds
run stronger than NCEP's, which would make an onshore-gale rule close west
coasts too readily).

## Western Mediterranean sailing (not addressed)

Casson's western routes come out 2–4× too slow (Rome–Narbo 12 days against
3, Rome–Carthage 7.5 against 3) and the long passages upwind to Rome 2.5×
too fast (`calibration/polity_20261025/sea.json`, T6). Diagnosing it needs
the Rome window's world, which is built from Earth datasets not in this
container (the land and people grid, ORBIS, Hanson's towns); recorded as
open.
