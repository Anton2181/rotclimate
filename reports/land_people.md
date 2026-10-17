# Land and people around 200 AD

What the simulated climate of the map would grow, and how many farmers it
could feed, for a world of Han and Parthian farming (the campaign's mix of
the Persian empires and the Three Kingdoms). Everything here comes from
published empirical relationships, run on the climate fit of the map (the
free-fit world D2, `calibration/earth/free_d2_polish_ds16.json`), and checked
in two ways: the same rules run on Earth's own climate against populations of
the period, and the map's numbers hex by hex against the campaign sheet.

Viewer: `land/index.html` (the Ravages Harvest Atlas). Scripts:
`scripts/land_people.py` (the analysis), `scripts/land_people_hexes.py`
(per hex, and the sheet check), `scripts/land_people_earth.py` (the Earth
check), `scripts/build_land_page.py` (the viewer's files).

## Method

1. **Climate.** Monthly temperature and rain of the fit at the drawing's
   resolution divided by four (1100 × 509 cells of 11.2 km²), corrected for
   height with the fit's lapse rate. The day/night swing comes from the
   WorldClim-trained model of `rotclimate/diurnal.py`.
2. **Evaporation demand.** Hargreaves & Samani (1985): 0.0023 (T + 17.8)
   √(day/night range) × the sunlight at the top of the air (FAO-56 eq. 21,
   from the world's latitude and tilt). The first version used Thornthwaite
   (1948), which needs only temperature; on Earth it let Riyadh, Merv and
   Isfahan grow full rain-fed barley on 120-150 mm of rain, because it badly
   underestimates the demand of dry, sunny winters.
3. **Soil water and growing period.** A 100 mm bucket; the FAO length of
   growing period counts months at or above 5 °C whose rain plus stored
   water reaches half the demand.
4. **Crops.** Each staple is tried in every run of months it could fill:
   its temperature window, its heat sum (degree days above its base) and
   the water balance of the season (rain × 0.8 plus the soil's store against
   the crop's need, kc × demand, plus 300 mm of flooding for paddy). The
   FAO-33 yield response (Doorenbos & Kassam 1979, Ky) holds for deficits up
   to about half the need; with under a third of it the crop fails (a
   smooth step between 0.3 and 0.5). Irrigated land is fully watered.

   | crop | window °C | heat (base) | months | kc | Ky | t/ha | edible | kcal/kg | seed |
   |---|---|---|---|---|---|---|---|---|---|
   | wheat | 3-24 | 1500 (0 °C) | 4-9 | 0.80 | 1.05 | 1.0 | 0.90 | 3300 | 0.14 |
   | barley | 2-25 | 1200 (0 °C) | 3-8 | 0.75 | 0.90 | 1.0 | 0.87 | 3540 | 0.12 |
   | foxtail millet | 14-33 | 1100 (10 °C) | 3-5 | 0.70 | 0.80 | 0.9 | 0.78 | 3780 | 0.02 |
   | paddy rice | 19-35 | 1700 (10 °C) | 4-6 | 1.15 | 1.20 | 1.8 | 0.68 | 3600 | 0.03 |
   | date palm | coldest month ≥ 7 °C, 5 months ≥ 24 °C, irrigated, annual rain under 300-500 mm | | | | | 3.0 | 1 | 2800 | 0 |

   Yields are the low-input yields of the period (Roman, Han and
   Mesopotamian estimates); edible shares are what hulling or milling
   leaves; calories are USDA values; seed is the share of the harvest sown
   again (about 140 kg/ha of wheat, 120 of barley, 15 of millet, 50 of
   transplanted rice).
5. **Irrigation.** From the drawn rivers in their two classes
   (`scripts/vector_rivers.py`): exp(−d / 6 km) of the land near a
   navigable river, 0.6 exp(−d / 2.5 km) along a stream.
6. **A second crop** in the months the first leaves free, at half weight,
   only where water allows it every year: irrigated land, or ten months or
   more of growing period.
7. **People.** Calories per hectare × arable share (by drawn terrain:
   lowland 0.85, upland 0.75, hills 0.45, mountains 0.08, the GAEZ slope
   classes weighted by the slopes typical of each) × 0.6 of it in fields
   (the rest pasture, wood, villages, roads) × the share sown in a year
   (0.68, fitted on Earth to the Han census, below; all of it where a second
   crop fits) ÷ 1.1 million kcal, a person's year with storage losses and
   draft animals.
8. **Also mapped:** net primary productivity (Miami model, Lieth 1975), rain
   against evaporation, and malaria climate (MARA, Craig, Snow & le Sueur
   1999: the best run of five months at 22-32 °C with 80 mm of rain or
   more, fuzzy edges).

The capacity is a ceiling: how many farmers the land could carry once fully
settled and farmed this way, not how many live there.

## The map

The map's land (3.29 million km²) could feed about
**310 million people**, 94 per km². Barley (with wheat
close behind) is the best crop on 75 % of the land and paddy rice,
in the wet west and south, on 23 %; foxtail millet comes
within 5 % of barley on a quarter of the land but rarely beats it; date palms grow
only along the few irrigated rivers in dry country. A second crop fits on
15 % of the land. The world is wetter and warmer than Earth's
same latitudes, so it feeds more per km² than the Mediterranean or northern China.

The ten provinces and realms of the sheet that could feed the most:

| province or realm | could feed | per km² | sheet settlement | sheet wealth |
|---|---|---|---|---|
| River Cities | 26.1 M | 180 | 23.9 | 10.0 |
| Anušiya Cities | 23.9 M | 123 | 24.2 | 20.5 |
| Xšāça | 18.0 M | 118 | 23.3 | 11.4 |
| Ul-Bit Hamadrun | 12.3 M | 84 | 20.6 | 5.2 |
| Kasos | 12.3 M | 93 | 21.9 | 13.3 |
| (E) Dars | 12.0 M | 195 | 23.9 | 13.3 |
| Selonken | 10.4 M | 177 | 22.6 | 13.5 |
| Tarani Kingdom | 8.7 M | 76 | 22.6 | 10.9 |
| Lasiŕos | 8.1 M | 142 | 22.9 | 12.2 |
| Yu’ež Tokar | 7.4 M | 51 | 20.7 | 10.2 |

## Checked against Earth

`scripts/land_people_earth.py` runs the same analysis on WorldClim 2.1
(5 arc-min, 1970-2000; day/night range from its own maximum and minimum)
from the Atlantic to the Pacific, 0-56°N, with Natural Earth's river
centrelines for irrigation (scale rank 0-4 navigable, the rest streams) and
local relief over ~25 km in place of the drawn tiers (under 150 m lowland,
150-400 upland, 400-1000 hills, more mountains). It then compares the people
the land could feed with the people who lived there around 1-200 AD
(figures gathered from the literature; where a region is known by its
density, that density is applied to the land of the outline used here).

The one free number, the share of fields sown in a year, was set to 0.68
so that the Han North China Plain (the provinces Yan, Yu, Ji, Qing and Xu:
29.4 million people on 365,000 km² in the census of AD 2, Hanshu 28) sits at
its capacity. Everything else is a test:

| region | could feed | lived there | share | source |
|---|---|---|---|---|
| Egypt | 3.5 M | 4.5-5 M | 130-145 % | 1st-2nd c., with Alexandria: Bagnall & Frier 1994, Rathbone 1990, Frier 2000 |
| North China Plain (Han Yan, Yu, Ji, Qing, Xu) (fitted) | 33.7 M | 34 M | 101 % | AD 2 census (Hanshu 28): 29.4 M on 365,000 km²; areas Zheng & Wu 2026 |
| Wei valley (Han Sanfu, with Chang'an) | 3.5 M | 2.6 M | 75 % | AD 2 census: 2.44 M on 55,400 km² |
| Sichuan basin (Han Shu, Guanghan, Ba) | 25.1 M | 2.3 M | 9 % | AD 2 census: 2.62 M on 245,000 km² |
| Hunan and Jiangxi (Han Changsha, Yuzhang) | 28.7 M | 0.8 M | 3 % | AD 2 census: 0.59 M on 246,000 km² |
| Roman Italy (mainland) | 13.0 M | 6-11.3 M | 46-87 % | AD 14-165, low count (Beloch 1886, Frier 2000) to high (Lo Cascio 1994, Harper 2017) |
| Roman Gaul | 50.2 M | 5-11.1 M | 10-22 % | AD 14-165: Beloch 1886, Frier 2000, Harper 2017 |
| Iberia | 39.3 M | 5.1-9 M | 13-23 % | AD 14-165: Frier 2000, Harper 2017 |
| Asia Minor | 31.4 M | 10.3-16.6 M | 33-53 % | AD 14-165: Frier 2000, Harper 2017, Beloch 1886 |
| Roman Syria | 5.5 M | 4.9-6.9 M | 90-126 % | AD 14-165: Frier 2000, Harper 2017, Beloch 1886 |
| Mesopotamian alluvium | 7.5 M | 0.7-2 M | 9-27 % | Parthian to Sasanian peak: Adams 1965, 1981 (settled area, 100-200 per ha) |

The old, densely settled cores of the period lived near the ceiling: the
Wei valley, Roman Syria and Italy at 46-126 %. Egypt is above it because
Natural Earth draws only two branches of the Delta, so most of the Delta
gets no river water here (about 16,000 km² watered against 25,000-27,000 km² of
cultivable land in antiquity, Butzer 1976). The Roman West, Asia Minor, the
alluvium under the Parthians and the Han south held a tenth to a half of
what their land could feed: the Han south (Changsha, Yuzhang) only 3 %, the
frontier the Three Kingdoms would fill. Two checks of the numbers per field:
the Han registers give 0.64 ha of cultivated land per person (8.27 million
qing for 59.6 million people), and the analysis 0.6 ha per person on fully
watered, single-cropped grain land (more where water is short); excavated registers from Donghai and Tangyi show
denser counties (0.36-0.41 ha per person).

Two fixes came out of the Earth run before the calibration: Thornthwaite
evaporation gave rain-fed barley to Riyadh, Merv and Isfahan, and the FAO-33
line, used far below half the crop's water, gave the Sahara a harvest.

Sources for the populations: Hanshu 28 (census of AD 2) with commandery
areas from Zheng & Wu 2026 (Scientific Data 13:876) and Hu & Zhang 1984;
Bagnall & Frier 1994, Rathbone 1990, Frier 2000 and Butzer 1976 for Egypt;
Beloch 1886, Frier 2000 (Cambridge Ancient History XI), Lo Cascio 1994,
Scheidel 2007 and Harper 2017 for the Roman provinces; Adams 1965 and 1981
for Mesopotamia.

## Checked against the campaign sheet

The sheet gives each land hex a settlement level (10, 20, 40, 60, 80 or 100)
and a wealth base (5-40). Over 2,226 land hexes the people a hex could
feed rank with the settlement level at Spearman ρ = 0.32 and with the
wealth base at ρ = 0.30; among flatland hexes alone, at 0.31 and
0.26. The plain annual temperature ranks better than any farming
measure (ρ = 0.50 with settlement): the sheet's settled core lies in the
warmer part of the map. The sheet was set by hand and the climate fitted only to
the painted climate zones, so agreement in the large is what to expect.

## Limits

* Irrigation reaches only a few km from the drawn rivers. On Earth this
  gives the Nile valley about the right width but misses most of the Delta
  (Natural Earth draws two branches) and the canal networks of
  Mesopotamia; the map's wide floodplains are likewise undercounted.
* Arable land comes from the four drawn height tiers, not from slopes.
* No herding, fishing or trade: a steppe or a coast feeds more people than
  its fields do.
* One set of yields and one sown share for the whole world, fitted to the
  Han plains: irrigated Egypt and the Delta-like floodplains of the map
  could carry more, a fallowing frontier less.
