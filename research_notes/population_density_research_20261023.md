# Predicted population density: HYDE and similar measures

Research notes, 23 October 2026. Written for the food-capacity model
(`scripts/land_people.py`, `scripts/land_people_earth.py`,
`reports/land_people.md`) and the population-allocation lab
(`population/models.py`, `reports/ITERATION_20261023.md`,
`reports/HARVEST_MIGRATION_20261022.md`). No repository code or data was
changed; nothing was committed.

## How to read the source marks

Every factual claim carries one of three marks.

- **[V]** verified: I opened the paper, data page, API record or data file in
  this session and read the statement there.
- **[P]** partly verified: I saw it only in an abstract, a search-engine
  summary or a third-party catalogue, not in the primary text.
- **[R]** recalled: from memory, not checked in this session. Treat as a lead
  to check before citing.

Numbers that I computed myself from verified data are marked **[V, computed]**.

---

## Summary

1. **HYDE is a model, not an observation.** For any year before 1500 CE, a
   HYDE map is a country (or province) total taken from McEvedy & Jones,
   Maddison and a few other compilations, spread over the country with
   weights built from soil suitability, distance to rivers and coasts, slope
   and temperature [V]. These are the same kinds of proxies the repository's
   capacity and attraction fields use. So agreement with HYDE within a
   country mostly shows that two sets of proxies agree. It does not show that
   either one is right.
2. **HYDE 3.3 has a 200 CE slice**, on a 100-year step from 0 CE to 1700 CE.
   There is no 1 CE or 2 CE slice; the first CE slice is labelled 0 CE/0 AD
   [V]. The grid is 5 arc-minutes (4320 × 2160 cells) [V]. Those are exactly
   the WorldClim 5′ cells that `land_people_earth.py` already uses, so the
   repository window is `[408:1080, 2016:3660]` of a HYDE grid [V, computed].
3. **Access from this environment.**
   - The official HYDE 3.3 deposits on Utrecht's YODA (four DOIs) answer only
     with an anti-bot JavaScript challenge, so scripts cannot list or size
     the files [V].
   - The Utrecht **HYDE portal** (which says its data is HYDE 3.3) answers
     `HEAD` requests for single-year rasters with 200 OK and
     `Content-Disposition: attachment`, but gives no size [V].
   - Its time-series API returned HYDE 3.3 country totals [V].
   - The DANS deposit of HYDE 3.2.1 is fully reachable through its API. The
     baseline is one 5.34 GB zip [V].
4. **Newer versions exist.** HYDE 3.4 (2025) and HYDE 3.5 (2025) are
   published as "HYDE data for the Global Carbon Budget". Their records say
   3.5 replaces 3.4, which replaces 3.3 [V]. There is still no methods paper
   newer than the HYDE 3.2 paper (2017); users are asked to cite that one [V].
5. **HYDE totals for antiquity sit low.** For the Roman provinces they sit at
   or below the low end of the repository's literature ranges: modern Turkey
   has 7.0 M at 200 CE, while the repository uses 10.3-16.6 M for Asia Minor
   [V, computed].
6. **HYDE's ancient urban shares are not usable as targets.** Italy is 4.4 %
   urban and Egypt 1.3 % at 200 CE [V, computed], although Rome alone was
   0.45-1.2 M people in the city compilations [V].
7. **Han China is the best independent target.** The AD 2 census of
   commanderies (prefectures) is a real count with polygons. It is now
   available as a CC BY 4.0 dataset (Zheng & Wu 2026) [V].
8. **Land productivity drives density across countries.** Ashraf & Galor
   (2011) find that a 1 % rise in land productivity raises population density
   in 1 CE by about 0.4-0.56 % [V].

---

## 1. HYDE (History Database of the Global Environment)

### 1.1 What it is

HYDE is "an internally consistent combination of historical population
estimates and allocation algorithms with time-dependent weighting maps for
land use" [V] ([Klein Goldewijk et al. 2017, ESSD 9:927](https://doi.org/10.5194/essd-9-927-2017)).
It covers 10 000 BCE to the present at 5 arc-minutes, about 85 km² at the
equator [V].

It gives population (total, urban, rural, density and built-up area) together
with land use:

- cropland, split into irrigated and rain-fed, and into rice and other crops;
- grazing land, split into pasture, converted rangeland and unconverted
  rangeland [V].

It is maintained by Kees Klein Goldewijk at Utrecht University and PBL [V].

### 1.2 Method

**Totals.**

- After 1950, totals come from UN World Population Prospects [V].
- Before 1950 they come "largely" from McEvedy & Jones (1978), Livi-Bacci
  (2007) and Maddison (2001). These are supplemented by Populstat
  sub-national series and country sources [V] (HYDE 3.2, sect. 2.1).
- Time series are built for every province or state of every *modern*
  country, with boundaries held fixed over time. Older units such as the
  Roman Empire are split into fractions of modern units [V].
- The source supplement adds an important detail. Before the earliest listed
  data point, a series is "hind-casted by growth rates" ("guestimates!") [V]
  (Supplement A of the 2017 paper).
- For antiquity the listed sources are:

  | country | sources |
  |---|---|
  | Italy | Maddison 2001 and McEvedy & Jones from 0 AD; Russell 1958 from 400 AD |
  | China | McEvedy & Jones and Chao 1996 from 0 AD; Populstat sub-national only from 1787 |
  | Egypt | Maddison from 0 AD; McEvedy & Jones from 5000 BC |
  | Turkey, Iran | Maddison from 0 AD |
  | Iraq, Syria | McEvedy & Jones |

  All entries [V].
- So the *within-country* (provincial) split for 0-200 CE comes from growth-rate
  hindcasts from much later data, not from ancient registers. This is my
  inference from the supplement text, and it is the key reason why the Han
  census is an independent test.

**Allocation of population** (sect. 3.1) [V]:

- For the present, population inside each administrative unit follows LandScan
  2012 patterns.
- Going back in time, these patterns "are gradually replaced with combined
  weighting maps based on various proxies such as soil suitability, slope,
  distance to water and case studies from several disciplines (e.g. history,
  archaeology)".
- The full population scheme is in the HYDE 3.1 paper
  ([Klein Goldewijk, Beusen & Janssen 2010, The Holocene 20:565](https://doi.org/10.1177/0959683609356587)),
  which I could not open (paywalled; the open copy sits behind the same
  anti-bot wall). [R] As I remember it, in HYDE 3.1:
  - rural population is weighted by distance to water (rivers, lakes,
    coast), suitability, slope or elevation and temperature;
  - urban population is placed first.

**Urban population and built-up area.** Built-up area equals urban population
divided by an average urban density. That density follows a bell-shaped curve
over time for each country. In the supplement's parameters, the curve's left
asymptote is 0.2 of its peak and its right asymptote 0.5, with an asymmetry
factor of 1.5 [V] (Supplement B). The urban *fraction* over time is an input
series per country [V].

**Allocation of cropland** (sect. 3.2) [V], which also explains the
population weights. For years before 1500 CE the weight is a product of
normalised maps:

```
W_crop_historic = W_pop · W_suit · W_river · W_coast · W_slope · W_temp_crop
```

The six rules behind it are:

- (i) urban built-up area is excluded;
- (ii) population density below 0.1 per km² allows no permanent farming;
- (iii) better GAEZ soil suitability is used first;
- (iv) coasts and river plains (from Natural Earth) are preferred;
- (v) steep slopes (from ETOPO5) are penalised;
- (vi) no farming below 0 °C annual mean temperature (CRU 1961-1990).

The satellite reference map's weight rises linearly from 0 in 1500 CE to 1 in
2010 CE [V] (Supplement D). Usable land per cell is
`G_max = G_cell − U_area − P_area − NL_area` [V].

Land use itself is population × land use per person. The per-person curve is
fitted back from FAO's 1960 values; the paper calls this "very sensitive to
the shape of the curve into the past" [V].

### 1.3 Time steps and grid

| Item | Value | Mark |
|---|---|---|
| Grid | ESRI ASCII, `ncols 4320, nrows 2160, xllcorner -180, yllcorner -90, cellsize 0.0833333, NODATA -9999` | [V] HYDE 3.2.1 readme |
| BCE steps | 1000 years (10 000 BCE ... 1000 BCE) | [V] readme; [V] portal year list |
| 0-1700 CE | 100 years: 0, 100, **200**, 300 ... 1700 CE | [V] |
| 1700-1950 | 10 years (portal); the 3.2 readme says 10 years to 2000 | [V] |
| After 1950 | yearly (portal, to 2023); 3.2 readme: yearly 2000-2015 | [V] |
| File naming | `yearBC_pop.zip` / `yearAD_pop.zip`, each with `popc_<yr>.asc`, `popd_<yr>.asc`, ... | [V] readme; the exact token for 200 CE (e.g. `200AD`) is inferred |

There is no 1 CE slice. HYDE's first CE map is labelled 0 CE (0 AD) and stands
for the turn of the era.

### 1.4 Variables

From the HYDE 3.2.1 readme [V] and the portal's variable list [V]:

| Code | Content | Unit |
|---|---|---|
| `popc` | total population | inhabitants per cell |
| `popd` | population density | inhabitants per km² |
| `rurc` | rural population | inhabitants per cell |
| `urbc` | urban population (the 3.2.1 readme writes `urb_`; the 3.3 portal uses `urbc`) | inhabitants per cell |
| `uopp` | built-up area (towns, cities) | km² per cell |
| `cropland`, `grazing`, `pasture`, `rangeland`, `conv_rangeland` | land-use areas | km² per cell |
| `ir_rice`, `rf_rice`, `ir_norice`, `rf_norice`, `tot_irri`, `tot_rainfed`, `tot_rice` | irrigated/rain-fed rice and other crops | km² per cell |
| General files | `garea_cr.asc` (cell area), `landlake_cr.asc`, `maxln_cr.asc` (maximum land area), `iso_cr.asc`, `sub_iso_cr.asc` (country and province codes) | |
| Anthromes | Ellis & Ramankutty classes 11-63 | class |

The readme labels the `ir_*` and `rf_*` descriptions inconsistently (for
example, `ir_norice` is described as "irrigated rice") [V]. Check the files
before use.

For a density comparison, compute `popc / maxln` yourself rather than relying
on how `popd` was normalised.

### 1.5 Uncertainty

**HYDE 3.2** [V] (sect. 4.1 and 5):

- Two bands around the baseline: range A is ±1 % in 2000 CE, ±5 % in 1900,
  ±10 % in 1800, ±25 % in 1700, ±50 % in 850 CE, **±75 % in 1 CE** and ±95 % in
  10 000 BCE. Range B is twice range A. Years in between are interpolated.
- World population in 1 CE is 232 M. The literature range is 170-330 M; the
  HYDE range is 58-406 M.
- The bands are applied to totals and multiplied by per-person land use. They
  are described as "expert judgement [that] should be treated with care".
- The authors add that McEvedy & Jones, Maddison and Livi-Bacci are "for some
  regions and time periods not undisputed and probably on the low side".

**HYDE 3.3.** The full release contains Baseline, Lower and Upper scenarios
([pastclim documentation](https://evolecolgroup.github.io/pastclim/reference/HYDE_3.3_baseline.html)
[V]; GCB-2023 record [V]). I did not see the 3.3 band widths.

The scenarios scale totals. I found nothing saying they change the spatial
weights; I assume the pattern is the same (not verified).

### 1.6 Versions, DOIs and licences

All rows below are from DataCite records [V], except where noted.

| Version | DOI / location | Issued | Licence | Note |
|---|---|---|---|---|
| HYDE 3.5 (GCB 2025) | [10.24416/UU01-F45D44](https://doi.org/10.24416/UU01-F45D44) | 2025 | CC BY 4.0 | "replaces former HYDE 3.4"; 10 000 BCE-2024 CE (one bullet says 2025); radiocarbon (IMSET) and ArchaeoGLOBE onset-of-farming data; netCDF added |
| HYDE 3.4 (GCB 2024) | [10.24416/UU01-BV65K3](https://doi.org/10.24416/UU01-BV65K3) | 2025-05-13 | CC BY 4.0 | "replaces former HYDE 3.3" |
| HYDE 3.3 (GCB 2023, `hyde33_MapBiomas_c7`) | [10.24416/UU01-OGXYNO](https://doi.org/10.24416/UU01-OGXYNO) | 2024-06-14 | CC BY 4.0 | baseline, lower and upper scenarios |
| **HYDE 3.3** | [10.24416/UU01-94FNH0](https://doi.org/10.24416/UU01-94FNH0) | 2024-03-15 | CC BY 4.0 | the latest 3.3 record; Datahub cites this DOI [P] |
| HYDE 3.3 | [10.24416/UU01-2CBQHL](https://doi.org/10.24416/UU01-2CBQHL) | 2024-02-09 | CC BY 4.0 | same description |
| HYDE 3.3 | [10.24416/UU01-AEZZIT](https://doi.org/10.24416/UU01-AEZZIT) | 2023-11-30 | CC BY 4.0 | same description |
| HYDE 3.3 | [10.24416/UU01-67UHB4](https://doi.org/10.24416/UU01-67UHB4) | 2023 (updated 2023-10-04) | CC BY 4.0 | first 3.3 record |
| HYDE 3.2.1 (UU copies) | [10.24416/UU01-XUTQN5](https://doi.org/10.24416/UU01-XUTQN5), [10.24416/UU01-MO2FF3](https://doi.org/10.24416/UU01-MO2FF3) | 2024, 2022 | CC BY 4.0 | |
| HYDE 3.2.1 (DANS) | [10.17026/dans-25g-gez3](https://doi.org/10.17026/dans-25g-gez3) | 2017 (v2 2025) | DANS metadata says CC0-1.0, the readme inside says CC BY 3.0 | resolves to `archaeology.datastations.nl` |
| HYDE 3.1 | [10.24416/UU01-G4HO5I](https://doi.org/10.24416/UU01-G4HO5I), [UU01-8K9D7F](https://doi.org/10.24416/UU01-8K9D7F) | 2022/2023 | CC BY 4.0 | "old version" |
| PBL FTP | `ftp://ftp.pbl.nl/hyde/hyde3.2/` (named in the 2017 paper [V]) | | | the host does not resolve from here [V] |

What the four HYDE 3.3 records differ in is not stated anywhere I could read.
Use 94FNH0, the latest, unless the YODA page says otherwise. The DANS licence
conflict should be settled by attributing anyway (CC BY is the stricter
reading).

### 1.7 What can be reached from this environment

All checks used `curl -sSI` through the configured proxy, with TLS
verification on. Small JSON or metadata requests are marked as such. No data
file was downloaded.

| URL | Result | Size |
|---|---|---|
| `https://doi.org/10.24416/UU01-94FNH0` (and the other 3.3 DOIs) | 302 to `https://public.yoda.uu.nl/geo/UU01/<ID>.html` | |
| `https://public.yoda.uu.nl/geo/UU01/AEZZIT.html`, `https://geo.public.data.uu.nl/vault-hyde/` and `.../vault-hyde-data/HYDE%203.2%5B1648738557%5D/original/` | HTTP 200, but the body is an anti-bot JavaScript proof-of-work page (7,316 bytes) | file list and sizes **not obtainable** from a script; use a browser |
| `https://hyde-portal.geo.uu.nl/api/raster/tif/popd/ce_200`, `.../asc/popd/ce_200`, `.../tif/popc/ce_0`, `.../asc/popc/ce_100` | **HTTP 200**, `Content-Disposition: attachment`, no `Content-Length` (streamed); mislabelled `text/html` | not reported. A 4320 × 2160 float32 GeoTIFF would be about 37.3 MB uncompressed [computed estimate] |
| `https://hyde-portal.geo.uu.nl/api/txt/<var>/<iso-numeric or 10000>/<from>/<to>` | small JSON (GET); used for the numbers below | 2.5 KB |
| `https://archaeology.datastations.nl/api/datasets/:persistentId/?persistentId=doi:10.17026/DANS-25G-GEZ3` | 200, JSON file list (metadata GET) | |
| `.../api/access/datafile/5490328` `HYDE3_2_1-baseline.zip` | HEAD: 303 to a signed SURF object-store URL; HEAD on that URL gives 403, because the URL is signed for GET only | **5,339,653,974 B** (from the Dataverse API) |
| `.../datafile/5490327` `HYDE3_2_1-general_supplementary.zip` | 303 as above | 23,585,889 B |
| `.../datafile/5490329` `HYDE3_2_1-anthromes.zip` | (API) | 141,764,831 B |
| `.../datafile/5396388` `readme_release_HYDE3.2.1.txt` | read (8,826 B) | 8,826 B |

How the portal API works [V] (from the portal's own JavaScript):

- Variable keys: `popc, popd, urbc, rurc, uopp, cropland, grazing, pasture,
  rangeland, conv_rangeland, ir_rice, rf_rice, tot_rice, ir_norice,
  rf_norice, tot_irri, tot_rainfed`.
- Year keys: `bce_10000 ... bce_1000, ce_0, ce_100, ce_200, ..., ce_1700,
  ce_1710, ..., ce_1950, ce_1951 ... ce_2023`.
- The portal text says "The visualized data is from HYDE 3.3".
- It is an undocumented, app-internal API, probably baseline only. Use it
  sparingly, and record the date of retrieval.

### 1.8 HYDE 3.3 baseline numbers for 0-300 CE

Retrieved from the portal API; modern borders; millions [V].

| Area (ISO) | 0 CE | 100 CE | 200 CE | 300 CE |
|---|---:|---:|---:|---:|
| World | 232.27 | 237.05 | 240.76 | 227.70 |
| China (156) | 57.71 | 51.17 | 42.95 | 21.79 |
| India (356) | 75.00 | 78.75 | 82.50 | 86.25 |
| Italy (380) | 7.46 | 7.08 | 6.71 | 6.33 |
| France (250) | 4.94 | 5.69 | 6.43 | 5.70 |
| Spain (724) | 4.60 | 4.80 | 5.00 | 4.75 |
| Portugal (620) | 0.41 | 0.46 | 0.46 | 0.46 |
| Turkey (792) | 6.00 | 6.50 | 7.00 | 6.50 |
| Syria (760) | 1.55 | 2.11 | 2.86 | 3.88 |
| Egypt (818) | 4.00 | 4.30 | 4.60 | 4.30 |
| Iraq (368) | 1.00 | 1.05 | 1.10 | 1.10 |
| Iran (364) | 4.00 | 4.17 | 4.33 | 4.50 |

**Points from this table** [V, computed]:

- **China 0 CE = 57.71 M.** This is essentially the registered Han total of
  AD 2 (Bielenstein's commandery sum is about 57.7 M [R]).
- China then falls to 43.0 M at 200 CE and 21.8 M at 300 CE. That follows the
  collapse of the *registers* after 184 CE, not necessarily of the people.
  For China, compare with HYDE 0 CE, not 200 CE.
- **Urban share at 200 CE:**

  | area | urban M | share |
  |---|---:|---:|
  | world | 7.11 of 240.8 | 3.0 % |
  | China | 0.70 | 1.6 % |
  | Italy | 0.295 | 4.4 % |
  | Egypt | 0.059 | 1.3 % |

  Set these against Rome, given as 450,000 in AD 100 (Chandler) or 1.2 M in
  AD 200 (Modelski), and Alexandria at 600,000 in AD 200 (Modelski) [V]
  ([Reba et al. 2016 data](https://doi.org/10.1038/sdata.2016.34)). HYDE's
  ancient urban layer is far too small for city questions.
- **Cropland per person at 200 CE:**

  | area | cropland | per person |
  |---|---:|---:|
  | world | 1.51 M km² | 0.63 ha |
  | China | 336,000 km² | 0.78 ha |
  | Italy | 94,000 km² | 1.40 ha |
  | Egypt | 4,385 km² | 0.095 ha |

  The Chinese value fits the Han registers' 0.64 ha per person
  (`reports/land_people.md`). Egypt's is about five times too small against
  the 25,000-27,000 km² of ancient cultivable land (Butzer 1976, as cited in
  the repository). HYDE's ancient land use is weakest exactly where
  irrigation mattered.

**Comparison with the repository's Earth regions.** The first two columns are
from `output/land_people/earth/regions.json`. Outlines and modern borders
differ, so read this column by column, not as exact matches.

| Repository region | Repository capacity (M) | Literature range used (M) | HYDE 3.3, 200 CE, nearest modern unit (M) |
|---|---:|---:|---:|
| Egypt | 3.46 | 4.5-5.0 | Egypt 4.60 |
| Roman Italy (mainland) | 12.96 | 6.0-11.3 | Italy (with islands) 6.71 |
| Roman Gaul | 50.24 | 5.0-11.1 | France 6.43 (smaller area) |
| Iberia | 39.34 | 5.1-9.0 | Spain and Portugal 5.46 |
| Asia Minor | 31.44 | 10.3-16.6 | Turkey 7.00 |
| Mesopotamian alluvium | 7.50 | 0.7-2.0 | Iraq (whole country) 1.10 |
| North China Plain (fitted) | 33.7 | 34.0 | China (whole) 42.95; 0 CE: 57.71 |

HYDE, through McEvedy & Jones and Maddison, sits at or below the low end of
the classical estimates used in the repository. Calibrating the sown share on
HYDE totals would therefore pull the model's occupation fractions down.

---

## 2. Other historical reconstructions

### 2.1 Overview

| Reconstruction | What it gives | Method | Coverage near 200 CE | Mark |
|---|---|---|---|---|
| **KK10** (Kaplan et al. 2011) | fraction of each 5′ cell under land use, **annually** 8000 BP to AD 1850 (7,901 steps) | land use from a non-linear relation between population density and land use observed in pre-industrial Europe (Kaplan et al. 2009), with technology change | year 200 exists; one 17.3 GB netCDF on PANGAEA; CC BY 3.0 | [V] [PANGAEA 10.1594/PANGAEA.871369](https://doi.org/10.1594/PANGAEA.871369), [Holocene 21:775](https://doi.org/10.1177/0959683610386983) |
| McEvedy & Jones 1978, *Atlas of World Population History* | country totals by modern borders, prehistory to 1975 | literature compilation with expert judgement; deliberately conservative | backbone of HYDE's ancient totals | [V] for its use in HYDE; [R] for the method |
| Maddison 2001 (and the Maddison Project) | population and GDP per head from 1 CE for some countries | compilation; ancient population taken mostly from earlier compilations | 1 CE (and 1000 CE) | [V] for use in HYDE and Ashraf & Galor; [R] for detail |
| Clio-Infra | country series (the total population series is by Klein Goldewijk) | HYDE-linked compilation | mostly after 1500 | HYDE 3.2 used "new (census) data sources from the Clio Infra project" [V]. The site returned 403, "taken offline on advice of KNAW information security", on 23 October 2026 [V] |
| Chandler 1987 / Modelski 2003, spatialised by **Reba, Reitsma & Seto 2016** | point locations and sizes of cities, 3700 BC to AD 2000 | digitised and geocoded, with no re-estimation; reliability ranking for each location | Chandler: 4 cities with values at AD 100 and 1 at AD 260. Modelski: 18 at AD 100 and 17 at AD 200, all inside the repository's Earth window | [V] [10.1038/sdata.2016.34](https://doi.org/10.1038/sdata.2016.34); figshare CC BY 4.0 [V]; counts [V, computed] |
| **Hanson 2016**, Roman cities database (OxREP) | catalogue of sites with urban characteristics, 100 BC to AD 300: locations, dates, inhabited areas, monuments, status | archaeological areas × a range of densities; Barrington Atlas as backbone | about 1,388 sites [P]; xlsx reachable [V] | [V] [OxREP page](https://oxrep.web.ox.ac.uk/cities-database), [DOI 10.5287/bodleian:eqapevAn8](https://doi.org/10.5287/bodleian:eqapevAn8) |
| Hanson & Ortman 2017 | populations of Greek and Roman settlements from area by a scaling relation | settlement-scaling theory | per site | [V] title: [JRA 30:301](https://doi.org/10.1017/S1047759400074134) |
| Roman Empire totals (Beloch 1886, Frier 2000, Scheidel 2007, Lo Cascio 1994, Harper 2017) | empire and provincial totals | census fragments, densities, analogy | AD 14 to 165 | [R]: Frier gives about 45 M (AD 14) to about 61 M (AD 164); Harper about 75 M; the repository already uses these |
| **ORBIS** (Scheidel and Meeks) | network cost model of the Roman world around 200 CE | sea, river and road network; Diocletian's Price Edict | about 750 sites | cost ratio sea 1 : river 5 (downstream) or 10 (upstream) : wagon 52 [V] ([Scheidel 2013 working paper](https://www.ltrr.arizona.edu/~rtouchan/Mediterranean_publications/scheidel.pdf)) |
| **Han census of AD 2** (Hanshu 28) | registered households and people per commandery or kingdom | census | AD 2 | [R]: total about 59.6 M people and 12.2 M households (the repository uses 59.6 M); about 103 commanderies and kingdoms |
| **Zheng & Wu 2026**, Sci. Data 13:876 | county-level population for AD 2, 742, 1102, 1820, with prefecture polygons | prefecture totals matched to *The Historical Atlas of China* polygons, redistributed over five relief classes, then split into Thiessen polygons around 1,294 county seats (AD 2) | AD 2 | [V] [10.1038/s41597-026-07086-6](https://doi.org/10.1038/s41597-026-07086-6); [figshare 10.6084/m9.figshare.30518417](https://doi.org/10.6084/m9.figshare.30518417), CC BY 4.0, 1.28 MB xlsx and 563 MB shapefile zip [V] |
| **GLUES** (Lemmen, Wirtz, Gronenborn) | regional simulated population density, technology and subsistence, before the Bronze Age | adaptive dynamic model driven by resources; uses HYDE scaling parameters to turn population into cropland | mostly before 1000 BC | [V] abstract [10.4000/geomorphologie.7756](https://doi.org/10.4000/geomorphologie.7756); [JAS 38:3459](https://doi.org/10.1016/j.jas.2011.08.008) |
| **ArchaeoGLOBE** (Stephens et al. 2019) | expert-coded land-use levels by region and time slice | survey of 255 archaeologists [R] | includes 2000 BP [R] | [V] abstract [Science 365:897](https://doi.org/10.1126/science.aax1192); used by HYDE 3.3-3.5 for the onset of farming [V] |

### 2.2 How they compare and how uncertain the totals are

**KK10 against HYDE.** KK10 assumes much more land use per person before
1500 CE. Driven by KK10, cumulative carbon emissions by AD 1850 were
325-357 Pg; driven by HYDE 3.1, 137-189 Pg [V]. In northern and central
Europe, KK10 matched pollen-based land cover (REVEALS) better than HYDE 3.1
did [V, partial abstract] ([Kaplan et al. 2017, Land 6:91](https://doi.org/10.3390/land6040091)).
The claim that HYDE "underestimated land use increasingly back in time" comes
from a search summary [P].

KK10 does not publish its own population grid; only the land-use fraction is
on PANGAEA [V].

**Critiques of HYDE.** [Klein Goldewijk & Verburg 2013](https://doi.org/10.1007/s10980-013-9877-x)
show that the shape of the per-person land-use curve dominates the
pre-industrial totals [V] (as cited in HYDE 3.2). A summary of the same paper
says the equal weighting of location factors is arbitrary [P].

**World population in 1 CE** [V] (Our World in Data compilation of historical
sources, downloaded CSV):

| Source | Year | Millions |
|---|---|---:|
| McEvedy & Jones 1978 | 1 / 100 / 200 | 170 / 180 / 190 |
| Olofsson & Hickler 2007 | 1 | 170 |
| HYDE 3.1 (2010) | 1 / 100 / 200 | 188 / 195 / 202 |
| Thomlinson 1975, lower | 1 | 200 |
| Maddison 2001 | 1 | 231 |
| HYDE 3.2 (2017) | 0 / 100 / 200 | 232 / 237 / 241 |
| HYDE 3.3 (portal) | 0 / 100 / 200 | 232 / 237 / 241 |
| Biraben 1980; Livi-Bacci 1997 | 1 | 252 |
| Clark 1967; Grigg 1987 | 1 | 256 |
| Durand 1974 | 1 | 270-330 |
| Haub 1995 | 1 | 300 |

The spread is a factor of about 2, and regional spreads are larger. For
example, Roman Italy at 6-11 M depends on how the Augustan census figures
are read [R].

---

## 3. Modern gridded population products

All modern products start from census counts for administrative units and
then distribute them inside each unit (dasymetric mapping). They differ in the
weights.

| Product | Resolution and years | How population is placed | Covariates that matter most | Licence | Marks |
|---|---|---|---|---|---|
| **GPW v4.11** (CIESIN) | 30″ (about 1 km); 2000-2020 every 5 years | proportional allocation (areal weighting) from about 13.5 million national and sub-national units; no covariates; density = count / land area | none (only the size of the unit) | [R] CC BY 4.0 | [P] [Doxsey-Whitfield et al. 2015](https://doi.org/10.1080/23754931.2015.1014272) |
| **GHS-POP R2023A** (JRC) | 100 m Mollweide; 3″ and 30″ WGS84; 1975-2030 every 5 years | GPW v4.11 counts disaggregated to cells "informed by the distribution, density, and classification of built-up" | **built-up volume** (GHS-BUILT-V R2022A), with non-residential volume removed | free reuse with acknowledgement [P] | [V] [JRC catalogue](https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe) |
| **LandScan Global** (ORNL) | 30″; yearly | "multi-variable dasymetric" with models tailored to each country; **ambient** (24-hour average) population; machine learning and imagery | land cover, roads, slope, urban areas, village locations, high-resolution imagery | CC BY 4.0 [P] | [V] DataCite [10.48690/1529167](https://doi.org/10.48690/1529167); HYDE 3.2 sect. 2.2 [V] |
| **WorldPop** (Southampton) | 100 m and 1 km; 2000-2020; R2025A 2015-2030 at 30″ | random forest predicts log density per census unit, and the prediction becomes the dasymetric weight | land cover; distance to built land cover "typically extremely important"; night lights (VIIRS); elevation and slope; MODIS NPP; climate; roads, rivers, settlements, facilities. In Kenya, distance to health facility ranked first | CC BY 4.0 (R2025A) [V] | [V] [Stevens et al. 2015](https://doi.org/10.1371/journal.pone.0107042); [R2025A](https://doi.org/10.5258/SOTON/WP00845) |
| **HRSL** (Meta/CIESIN) | 30 m; around 2015 | a neural network classifies 0.5 m image patches as containing buildings; census counts are then allocated in proportion to settled area | presence of buildings only | [R] CC BY 4.0 | [P] [Tiecke et al. 2017](https://arxiv.org/abs/1712.05839) |

A review of how fit these products are for different uses is
[Leyk et al. 2019, ESSD 11:1385](https://doi.org/10.5194/essd-11-1385-2019) [V title].

**Lesson for this project.** Modern accuracy comes almost entirely from
observing where buildings and roads are. Before 1800 there is no such layer.
HYDE therefore falls back on environmental proxies, which is the weakest part
of any ancient reconstruction. The pre-industrial stand-ins for "buildings"
are:

- known settlement and market locations (Pleiades, Hanson, county seats);
- water access;
- terrain.

The repository already uses all three: market anchors, water distance and
slope.

---

## 4. Environmental predictors of pre-industrial population density

### 4.1 Land productivity: the Malthusian elasticity

[Ashraf & Galor 2011, AER 101:2003](https://doi.org/10.1257/aer.101.5.2003)
([working paper](https://www.nber.org/papers/w17037)) [V], Tables 2-4:

**Data.**

- Dependent variable: log population density. Density is McEvedy & Jones
  population divided by land area, for 128-147 countries.
- Land productivity: the first principal component of log % arable land and
  log agricultural suitability (Ramankutty et al. 2002).
- Distance to the nearest coast or river is measured in thousands of km.

**Coefficients** (column 4 OLS, with continent dummies):

| Year | log years since Neolithic | log land productivity | log abs. latitude | mean distance to coast/river (1000 km) | % land within 100 km of coast/river | R² | N |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 CE | 1.930 | **0.394** | 0.057 (ns) | −0.685 | 0.857 | 0.69 | 128 |
| 1000 CE | 1.480 | **0.497** | −0.229 | −0.528 | 0.716 | 0.67 | 142 |
| 1500 CE | 1.087 | **0.576** | −0.314 | −0.392 | 0.899 | 0.73 | 147 |

**Reading the coefficients.**

- Land productivity alone (column 2) gives 0.40 / 0.47 / 0.59 for the three
  years; with the Neolithic timing (column 3) 0.56 / 0.56 / 0.64.
- IV estimates: 0.48 / 0.55 / 0.57.
- Moving a country from 0 % to 100 % of land within 100 km of a coast or
  navigable river multiplies 1 CE density by e^0.857 ≈ 2.4 [V, computed].
- Income per head does not respond significantly. That is the Malthusian
  result: productivity buys people, not wealth.

**Use here.** The elasticity is below 1. In a cross-section, doubling land
productivity raises density by about 2^0.4-0.6, roughly ×1.3-1.5, not ×2,
because occupation and technology differ. The repository's capacity is linear
in calories. Its realised-to-capacity ratios (3 % in Han Hunan and Jiangxi to
about 100 % on the plains) are what this elasticity predicts when frontier
regions are less occupied.

### 4.2 Caloric Suitability Index (Galor & Özak) and GAEZ

**CSI** [V] ([website](https://ozak.github.io/Caloric-Suitability-Index/),
[Galor & Özak 2016, AER 106:3064](https://doi.org/10.1257/aer.20150020) [V DOI],
[data, Zenodo 10.5281/zenodo.14714917](https://doi.org/10.5281/zenodo.14714917)):

- Built from GAEZ potential yields under **low inputs and rain-fed**
  conditions. Yields are converted to calories with USDA values, using
  dry-weight yields as a proxy for storage losses.
- Each cell gets the crop with the highest calories, with separate sets for
  **pre-1500** and post-1500 crops.
- 5′ GeoTIFFs; `pre1500MaximumCalories0.tif` is 36,037,264 B (HEAD against
  Zenodo) [V]. CC BY-SA 4.0 [V].
- The site claims CSI "is a good predictor of population density during the
  Malthusian period, improving over Ramankutty et al." [V].

This is almost the same construct as the repository's `kcal_ha`: low-input
calories from the best crop. The difference is that CSI uses the GAEZ process
model rather than the repository's FAO-33 bucket model.

**GAEZ v4** (FAO/IIASA 2021):

- Suitability and attainable yields for about 50 crops, rain-fed and
  irrigated, at low and high inputs [P].
- Climate baselines 1961-1990, 1971-2000 and 1981-2010 [P].
- Mainly 5′, with some 30″ layers [P].
- Portal `https://gaez.fao.org/` answers 200 [V].
- [Model documentation, 10.4060/cb4744en](https://doi.org/10.4060/cb4744en) [V title].

### 4.3 Net primary productivity and forager density

[Tallavaara, Eronen & Luoto 2018, PNAS 115:1232](https://doi.org/10.1073/pnas.1715638115) [V]:

- **Data.** 300 ethnographic hunter-gatherer groups from Binford (2001) and
  Kelly (2013), plus the Saami. NPP comes from the **Miami model** run on
  WorldClim annual temperature and precipitation. The repository already
  computes Miami NPP in `earth.npz`.
- **Breakpoint at about 1,360 g m⁻² yr⁻¹.** Below it, density rises with NPP.
  Above it, density is "largely independent of additional increases" while
  pathogen stress rises. A piecewise model explains 44 % of the variance in
  log density. The split is 234 low-productivity and 66 high-productivity
  groups.
- **Structural equation models.** At low productivity, biodiversity has the
  strongest direct effect, then NPP. At high productivity, pathogen stress
  dominates. Temperate and subtropical biomes give the highest densities.

Binford 2001, *Constructing Frames of Reference* (University of California
Press) [R]: 339 forager cases with environmental variables. Typical forager
densities are about 0.01-1 per km² [R].

[Kavanagh et al. 2018, Nature Human Behaviour 2:478](https://doi.org/10.1038/s41562-018-0358-8)
hindcast global forager densities from this kind of data [V title; R
content].

### 4.4 Boserup: intensity rises with density

Boserup ([1965, *The Conditions of Agricultural Growth*](https://doi.org/10.4324/9781315016320);
1981, *Population and Technological Change*) argues that density drives a
shortening of fallow. The sequence runs forest fallow → bush fallow → short
fallow → annual cropping → multicropping.

The 1981 book uses ten density classes, each double the one before [P]. As I
remember it, the systems map roughly to these densities [R]:

| system | people per km² |
|---|---|
| forest fallow | 0-4 |
| bush fallow | 4-16 |
| short fallow | 16-64 |
| annual cropping | 64-256 |
| multicropping | above 256 |

Check these bands against the book's table before quoting them.

Lee 1986 ("Malthus and Boserup: a dynamic synthesis") combines the two views
[R]. Population grows to the capacity set by technology (Malthus), while
density pushes technology (Boserup).

**For the repository.** The single "share sown in a year" (0.68) is a
Boserupian intensity parameter. It could depend on density or occupation
instead of being one global constant.

### 4.5 Water access, coasts and elevation

- **Ashraf & Galor:** coefficients above. Water access is the second-largest
  geographic effect after land productivity [V].
- **[Henderson et al. 2018, QJE 133:357](https://doi.org/10.1093/qje/qjx030)**
  [V abstract]:
  - 24 physical-geography variables explain 47 % of worldwide and 35 % of
    within-country variation in night lights over 240,000 cells.
  - In countries that developed early, agricultural variables explain more
    than six times as much as trade variables. That fits a pre-industrial
    pattern locked in before transport became cheap.
- **[Cohen & Small 1998, PNAS 95:14009](https://doi.org/10.1073/pnas.95.24.14009)**
  [V abstract]:
  - In 1994, 33.5 % of people lived within 100 vertical metres of sea level,
    on 15.6 % of inhabited land.
  - The median person lived at 194 m.
  - Numbers fall "faster than exponentially" with elevation.

  This gives an elevation histogram to compare with model output. Use it with
  care, because modern coasts are inflated by industrial ports.
- **Gallup, Sachs & Mellinger 1999**, "Geography and Economic Development"
  ([NBER w6849](https://doi.org/10.3386/w6849)) [V title]: population is
  concentrated within 100 km of coasts or sea-navigable rivers [R detail].
- **Terrain weighting inside Han prefectures:** Zheng & Wu weight five relief
  classes by the density of county seats in each class. That is an empirical
  slope penalty fitted on Chinese data [V].

### 4.6 Disease ecology

- **Malaria.**
  - The Malaria Ecology / stability index of
    [Kiszewski et al. 2004, AJTMH 70:486](https://doi.org/10.4269/ajtmh.2004.70.486)
    is built from the vector's human-biting share, daily survival, the length
    of the transmission season and the incubation period, on a 0.5° grid
    [V abstract].
  - [Gallup & Sachs 2001](https://doi.org/10.4269/ajtmh.2001.64.85) report
    the economic burden [V title].
  - Ancient evidence: Roman Italy's malarial lowlands (Sallares 2002) [R].
  - The repository's health factor `H = 1 − 0.35 × potential` has no
    published slope. The Kiszewski index could be correlated with HYDE's
    density residuals, and with Han and Roman residuals, to fit one.
- **Tsetse.** [Alsan 2015, AER 105:382](https://doi.org/10.1257/aer.20130604)
  [V abstract]: ethnic groups in tsetse-suitable areas had lower population
  density and fewer draft animals and ploughs. This is a model of a disease
  acting through farming technology.
- **Sickle cell.** [Depetris-Chauvin & Weil](https://doi.org/10.3386/w19603)
  estimate the long-run burden of malaria in Africa [V title].
- **Pathogens limit even foragers in the tropics**: Tallavaara et al. above [V].

### 4.7 Market access and transport cost

- **Tobler's walking function** is already in `population/models.py`.
- **ORBIS cost ratios** [V]: sea 1, river 5 (downstream) or 10 (upstream),
  road wagon 52. They compare with 1 : 5 : 23 in early 18th-century England,
  and with downriver against land at 1 : 10 in China in 1202.

  So a cell 50 km inland by road is about as "far" as 2,600 km by sea.
  This is the main reason ancient cities and dense populations hug coasts
  and rivers.
- **Özak's Human Mobility Index** [P]
  ([project page](https://github.com/human-mobility-index/human-mobility-index.github.io);
  [paper](https://doi.org/10.2139/ssrn.1989216) [V title]): least-cost
  travel times before steam, without sea travel, with sea travel on known
  routes, and with sea travel everywhere (CLIWOC winds).
- **[Weiss et al. 2018, Nature 553:333](https://doi.org/10.1038/nature25181)**
  [V title]: a global friction surface and travel time to cities, for modern
  conditions.
- **Market potential** in the Donaldson & Hornbeck (2016) form,
  `MA_i = Σ_j N_j τ_ij^−θ`, is the usual economic summary [R].

### 4.8 City sizes: rank-size and settlement scaling

- **Zipf.** Within a system, city size is roughly inversely proportional to
  rank ([Gabaix 1999, QJE 114:739](https://doi.org/10.1162/003355399556133)
  [V title]). Modelski used rank-size rules to fill gaps in ancient city
  lists [V] (Reba et al.), so those lists are not fully independent tests of
  Zipf.
- **Settlement scaling.**
  [Ortman, Cabaniss, Sturm & Bettencourt 2015, Sci. Adv. 1:e1400066](https://doi.org/10.1126/sciadv.1400066)
  [V] give the relation between settled area and population as A ∝ N^α, with
  2/3 ≤ α ≤ 5/6:
  - 2/3 for "amorphous" settlements;
  - 5/6 for settlements organised along streets and networks;
  - Basin of Mexico estimates range from about 0.58 to 0.75 by period.

  Two consequences follow:
  - **Density rises with size, as about N^(1/3) to N^(1/6).**
  - Output per head rises as about N^(1/6).

  See also [Ortman et al. 2014, PLoS ONE](https://doi.org/10.1371/journal.pone.0087902)
  and [Bettencourt et al. 2007, PNAS](https://doi.org/10.1073/pnas.0610172104)
  [V titles]. Hanson & Ortman (2017) apply this to Greek and Roman towns [V
  title].

---

## 5. How to use this here

### 5a. Validating and calibrating the food-capacity and allocation model on Earth

**Data alignment.** `earth.npz` covers latitude 0-56°N and longitude 12°W to
125°E at 5′. That is rows `408:1080` and columns `2016:3660` of any global
5′ grid that starts at 90°N and 180°W, which is HYDE's layout [V, computed]:

```python
# HYDE ESRI ASCII: ncols 4320, nrows 2160, xll -180, yll -90, first row = north
import numpy as np

def read_asc(path):
    with open(path) as f:
        hdr = {k.lower(): float(v) for k, v in (f.readline().split() for _ in range(6))}
        a = np.loadtxt(f, dtype=np.float32)          # 2160 x 4320, row 0 = 90-89.92 N
    a[a == hdr['nodata_value']] = np.nan
    return a

win = np.s_[408:1080, 2016:3660]           # same cells as output/land_people/earth/earth.npz
popc = read_asc('popc_200AD.asc')[win]     # file name pattern from the 3.2.1 readme; check in the 3.3 zip
land_km2 = read_asc('maxln_cr.asc')[win]   # HYDE land area per cell
```

(Header keys follow the 3.2.1 readme. The sketch is untested. The 3.3
files may also come as netCDF.)

Get the files in one of two ways:

- **Official route:** open DOI 10.24416/UU01-94FNH0 in a browser, which
  passes the anti-bot check, and download the baseline and lower/upper
  population zips for 0, 100 and 200 CE.
- **Scripted route:** `https://hyde-portal.geo.uu.nl/api/raster/asc/popc/ce_200`,
  probably baseline only. Record the date and check the grid header.

**Experiments, in order of independence from HYDE.**

| # | Test | Reference | What it tells you |
|---|---|---|---|
| E1 | Rank correlation of `capacity` (and of `kcal_ha`) with HYDE `popc/maxln`, after aggregation to 0.5° or 1°, within modern-country groups | HYDE 3.3, 0/100/200 CE | Whether the repository's proxies resemble HYDE's (agreement of proxies, not truth) |
| E2 | **Allocation only:** fix each country's total to HYDE's and run `allocate(C, a, total)`; compare cell shares with HYDE | HYDE | Separates the *pattern* question from the *total* question, which is how HYDE itself is built |
| E3 | **Han commanderies AD 2:** allocate the Han total over Han territory and compare commandery totals | Zheng & Wu prefecture polygons (counties are modelled, so do not use them as truth) | An independent test of within-empire allocation. Also aggregate **HYDE 0 CE** to the same polygons: HYDE's split inside China is a hindcast from late data, so this tests HYDE too. I expect HYDE to put too many people in the Yangtze south, but that is unchecked |
| E4 | **Roman out-of-sample test:** keep the E3 parameters, allocate an empire total (45-61 M) and compare with provincial ranges (Frier, Beloch, Harper) | Frier 2000; repository regions | Whether parameters fitted on Han transfer to another civilisation |
| E5 | City placement: share of Hanson's sites (by area) and Modelski's AD 200 cities that fall in the top decile of model attraction and support | OxREP xlsx; Reba figshare | Whether markets and cities sit where the model's attraction peaks |
| E6 | Check the crop model: Spearman correlation of `kcal_ha` against CSI pre-1500 maximum calories (and GAEZ v4 low-input yields) | CSI 5′ GeoTIFF (36 MB) | An independent process-model check of the calorie layer, before any population enters |

**Metrics.**

- **Log-density RMSE**, area-weighted, after aggregation:
  `sqrt(mean_w((log10(d_m+ε) − log10(d_r+ε))²))`, with ε of about
  0.1 per km² so that empty cells do not dominate.
- **Spearman ρ at 0.5° or 1°.** Use spatial block bootstrap (for example
  5° blocks) for confidence intervals. Neighbouring cells are not
  independent, so naive p-values will be far too small.
- **Dissimilarity index** (the share of people who would have to move):
  `D = ½ Σ |p_i/P − q_i/Q|`, reported as `1 − D`. It is the natural metric
  when totals are forced equal, as in E2-E4.
- **Unit totals.** Report the ratio Σmodel / Σreference and the log-ratio
  RMSE across units. Use Poisson deviance with the overall total fixed when
  *fitting* λ and the attraction scales (`water_distance_scale_km`,
  `slope_scale`, `market_time_scale_hours`) on Han units.
- **Shape diagnostics:**
  - concentration: share of people on the densest 10 % of land, or a Lorenz
    curve;
  - share of people within 10 km of a river and within 50 km of the coast;
  - an elevation histogram (compare with Cohen & Small's modern shape
    qualitatively only).
- **Nulls to beat:**
  - uniform within a country or unit;
  - support C alone (attraction set to 1);
  - a HYDE-like weight product (suitability × river × coast × slope ×
    temperature);
  - the repository's full attraction.

  A model that cannot beat "C alone" on the Han test should not keep extra
  attraction parameters.

**Pitfalls.**

1. **Circularity.** HYDE's ancient pattern is suitability × water × slope ×
   temperature, and the repository's is capacity × water × slope × market.
   High agreement (E1, E2) is expected and proves little. Only E3-E5 use
   independent observations.
2. **Totals drive HYDE.**
   - Before 1500, every HYDE number is a modern-border country total
     (McEvedy & Jones or Maddison) times a weight map.
   - Comparing summed capacity with HYDE country totals compares the model
     with McEvedy & Jones, which is at the low end for Rome.
   - Do not refit the sown share (0.68) on HYDE totals.
3. **200 CE is a bad year for China.** HYDE China drops from 57.7 M (0 CE) to
   43.0 M (200 CE) [V], tracking the end of the Han registers. Use 0 CE for
   China and 100-200 CE for Rome (before the Antonine plague of 165 CE [R]).
4. **Urban layer.** HYDE's urban shares for antiquity (1-4 %) and its
   built-up areas are not credible targets [V, computed]. Use Hanson and
   Modelski for cities.
5. **Land use in irrigated regions.** HYDE Egypt has 4,385 km² of cropland at
   200 CE, about 0.1 ha per person [V, computed]. Do not use HYDE cropland to
   test irrigation reach. The repository's Delta problem (Natural Earth shows
   only two branches) needs a historical-hydrology fix instead.
6. **Grid-scale noise.** At 5′, HYDE's within-country pattern carries the
   arbitrary sharpness of multiplied weights. Compare at 0.5-1° or by
   historical unit.
7. **Changed landscapes.** Coasts and rivers have moved since antiquity
   [R]:
   - the Yellow River shifted course in AD 11;
   - the Po, Menderes and Mesopotamian deltas have grown;
   - the climate differs (Roman Climate Optimum against WorldClim 1970-2000).

   These are smaller errors than the totals but matter cell by cell.
8. **Registered is not real.** Census registers undercount, worse at
   frontiers and in crises (the Han south; China after 184 CE) [R]. Treat a
   unit ratio below 1 at a frontier as partly an artefact of registration.

**Independent targets worth assembling**, all reachable [V]:

- **Han AD 2 commanderies.** Zheng & Wu figshare: 1.28 MB xlsx and 563 MB
  shapefiles, CC BY 4.0.
- **Roman cities.** OxREP Hanson xlsx.
- **Ancient cities.** Reba et al. CSVs (1.4 MB and 17 KB, CC BY 4.0).
- **Settlement points.** Pleiades gazetteer dump,
  `https://atlantides.org/downloads/pleiades/dumps/pleiades-places-latest.csv.gz`,
  6,823,954 B (HEAD [V]). The density of known sites reflects how much
  research a region has had, so use ranks within regions only.
- **Roman provincial estimates.** Frier and Beloch (already in
  `REGIONS` in `scripts/land_people_earth.py`).
- **Mesopotamian survey.** Adams, already used.
- **Land use.** ArchaeoGLOBE regional land-use levels at 2000 BP [R], and KK10
  land use at AD 200, as an alternative to HYDE's land use. KK10's single
  netCDF is 17.3 GB [V], so extract only year 200 with a remote or chunked
  read.

### 5b. Other population-like measures worth adding

1. **Urban share and city sizes.**
   - Take an urban share u per region; the evidence base is Hanson for Rome
     and Zheng & Wu county seats for Han.
   - Distribute uP people over the market anchors by a Zipf rule
     (size ∝ rank^−1), weighted by each anchor's market potential.
   - Give each city an area A = a·N^α with α between 2/3 and 5/6 (Ortman).
   - Report each city's food catchment against local support. With
     0.6 ha per person and half the land in fields, a city of 100,000 needs
     about 1,200 km², a radius of about 20 km. Rome at 1 M needs a radius of
     about 62 km, which is why it imported by sea [computed, illustrative].
   - This adds the missing "urban densities above local support" noted in
     `ITERATION_20261023.md`.
2. **Capacity under different technologies**, kept as separate layers:
   - forager (Tallavaara: log density against Miami NPP with a breakpoint
     at 1,360 g m⁻² yr⁻¹);
   - pastoral (the existing grazing allowance);
   - rain-fed, irrigated and double-cropped;
   - a Boserupian sown share that rises with density.

   This turns "frontier, central, core" into technology and occupation
   choices, not one scalar.
3. **Transport-cost surface and market potential.**
   - Add sea and river edges to the Tobler graph, with ORBIS mode ratios
     (land 52 : downriver 5 : upriver 10 : sea 1, per tonne-km).
   - Compute `MA_i = Σ_j N_j exp(−cost_ij / κ)`.
   - Check the Earth version against Özak's Human Mobility Index and ORBIS
     travel costs to Rome.
4. **Disease ecology.**
   - Replace the fixed 0.35 malaria penalty with a slope fitted on Earth
     residuals (E3 and E4 residuals regressed on Kiszewski stability or the
     Mordecai thermal index).
   - Consider schistosomiasis near irrigation, and tsetse-like livestock
     limits (Alsan) where the fantasy world has such vectors.
5. **Occupation fraction.**
   - The ratio of realised people to capacity ranges from 3 % (Han south) to
     about 100 % (core plains).
   - Model it from distance to the political core, years since state
     incorporation, malaria and market potential, fitted on Earth units.
   - This is the Ashraf & Galor "technology or time since farming" term at
     the regional scale.
6. **Diagnostics for each map:**
   - population by elevation band;
   - share within 10 km of rivers and 50 km of coasts;
   - a Lorenz curve of density;
   - the city rank-size slope.

   These are cheap to compute and comparable across fits and with Earth.

---

## 6. Top recommendations

1. **Build an Earth comparison harness with HYDE 3.3, but treat it as a
   consistency check (E1, E2).**
   - Download the 0, 100 and 200 CE population zips (or portal rasters).
   - Align them with `earth.npz` (rows 408-1080, columns 2016-3660).
   - Report dissimilarity, Spearman at 1° with block bootstrap, and
     log-RMSE against the four nulls.
   - Do not refit totals on HYDE.
2. **Calibrate the allocation on the Han AD 2 commanderies (E3) and test on
   Rome (E4, E5).**
   - Fit λ and the water, slope and market scales by Poisson deviance on the
     roughly 100 commandery totals.
   - Then check Roman provincial ranges and the placement of Hanson's and
     Modelski's cities without refitting.
   - This is the only route here that is independent of HYDE's weights.
3. **Add an urban and transport layer.**
   - City sizes from Zipf and scaling, with food catchments.
   - Market potential with ORBIS mode ratios.
   - Check urban shares against Hanson and Modelski, not HYDE.
   - As a quick side check, compare `kcal_ha` with the CSI pre-1500 raster
     (E6) before any population fitting.

---

## Appendix: what could not be verified

- The HYDE 3.3 file list and file sizes on YODA (behind the anti-bot wall),
  and what distinguishes its four 3.3 DOIs.
- The HYDE 3.1 population-weighting details (Holocene 2010 full text not
  opened).
- The HYDE 3.3 widths of the lower and upper bands.
- Whether the portal rasters are baseline only.
- Exact Boserup density bands; Binford's case count; the Frier, Harper and
  Beloch provincial numbers; the Han household and person totals. All are
  recalled, and the last three are already cited in `reports/land_people.md`.
- LandScan, GPW and HRSL licences (from third-party catalogues or memory).
- KK10's population inputs (only the land-use output and the abstract were
  read).
- Clio-Infra (website offline on 23 October 2026).
