# Research round 2: physics for the Earth model's remaining failures (17 October 2026)

Four literature reviews, each given the model's structure, its remaining Earth
failures (r5 fit) and what had already been tried. Each had to propose
equation-level changes that use only the model's own fields, so they also run
on the fantasy map. Summaries below; implemented items are marked.

## A. Cool summers on cold-current coasts

Literature:
- The marine boundary layer under the subtropical inversion is ~0.6-1 km deep
  off central Chile (~13 °C potential temperature at 33°S). Inside it the
  flow is along-shore with no cross-shore wind below 1 km; the offshore
  continental flow runs above the inversion (Rahn & Garreaud 2010,
  doi:10.5194/acp-10-4491-2010; Muñoz & Garreaud 2005, doi:10.1175/MWR3074.1).
- Marine stratus reaches inland only on terrain connected to the sea and below
  the inversion base, ~500-600 m (Iacobellis & Cayan 2013,
  doi:10.1002/jgrd.50652). NWS Sacramento: the Delta breeze enters the Valley
  only when the marine layer is >~600 m deep.
- Sea-breeze reach is ~50 km in a 1-2 m/s offshore background wind, ~10 km at
  4-5 m/s, and none above ~6-11 m/s (Crosman & Horel 2010,
  doi:10.1007/s10546-010-9517-9).
- Nearshore summer SST off central Chile is ~13-14 °C (Aguirre et al. 2021,
  doi:10.3389/fmars.2021.702051).
- PRISM scores coastal influence with a least-cost path from the sea that
  penalises distance and climbing (Daly et al. 2003, doi:10.1002/joc.937).
  The lowest possible crest between a point and the sea is a Priority-Flood
  (Barnes et al. 2014, doi:10.1016/j.cageo.2013.04.024).

Why the earlier marine layer failed: an offshore wind of 5 m/s crosses a 56 km
cell in ~3 h, so any relaxation toward the sea weaker than ~3 h is swamped
inside the advection solve.

Proposals:
1. **Sub-grid marine-air fraction, applied as a diagnostic tile blend**
   (implemented as `marine_fraction`). F = c · f_inv · <exp(-d/L)> ·
   σ((h_i − z*)/δz), with f_inv = clip((T_land − SST_coast)/ΔT, 0, 1), d the
   distance to the sea, z* the lowest crest on any path from the sea, h_i the
   inversion height. The reported cell temperature is T − F·max(T − T_marine,
   0); winds and rain keep using the continental tile.
2. Marine-layer wind below the inversion (no offshore component where a
   marine layer exists) for upwelling and the coastal sea air.
3. Stratocumulus/fog shading of coastal land: cloud ~ 0.14 + b·(inversion
   strength) (Wood & Bretherton 2006, doi:10.1175/JCLI3988.1).
4. Calibrate on coast-minus-inland contrast.

## B. What intermediate-complexity models have that this one lacks

Survey of CLIMBER-2, CLIMBER-X (SESAM), UVic EMBM, PlaSim, SPEEDY, Aeolus,
moist EBMs. Both CLIMBER-X and UVic keep a warm winter bias over eastern
continents (East China's failure here), so gains there are plausible, not
demonstrated.

1. Diagnosed sea-level pressure + friction-balanced (mixed-layer) surface wind
   and its divergence (Petoukhov et al. 2000, doi:10.1007/PL00007919;
   Willeit et al. 2022 App. A2, doi:10.5194/gmd-15-5905-2022; Back &
   Bretherton 2009, doi:10.1175/2009JCLI2392.1). p_s = γ_PW·G_L(T*) +
   γ_BL·(T* − G_L(T*)) (~2 hPa/K at large scale, 0.5-1 hPa/K in the boundary
   layer); U, V from f k×U + ε_i U = ε_e U_T − ∇p/ρ0 (regular at the equator);
   w = −h ∇·U drives ascent and replaces the prescribed subsidence factor.
   Back & Bretherton: SST-gradient pressure alone gives surface-wind pattern
   correlation 0.97 and convergence 0.65 against QuikSCAT.
2. Diagnostic cloud fraction with shortwave and longwave corrections to T_eq
   (SESAM f = [c1 + c2·tanh(c3·w)]·RH^1.5; SPEEDY CLC = 0.2·√min(P,10) +
   ((RH − 0.3)/0.7)²; PlaSim). Targets dry interiors too cool in summer and
   cloudy winters.
3. Baroclinicity-driven, advected eddy kinetic energy setting the storm-eddy
   mixing (SESAM synoptic scheme; Siler et al. 2018, doi:10.1175/JCLI-D-18-0081.1).
4. Energy-limited evaporative fraction and soil-moisture-driven albedo
   (PlaSim/SimBA bucket; PALADYN β_s, doi:10.5194/gmd-9-3817-2016).
5. Convergence-fraction rain closure plus lee re-evaporation (SESAM; LFPM,
   Hergarten & Robl 2022, doi:10.5194/gmd-15-2063-2022).

## C. Continental winter cold and the East Asian monsoon

- The Siberian High is a shallow cold dome built by clear-sky longwave loss
  over snow plus subsidence; cooling raises surface pressure only above the
  ~1000 km deformation radius (Ding & Krishnamurti 1987; Jones & Cohen 2011,
  doi:10.1175/2010JCLI3970.1). Mountains channel the outflow east of Tibet;
  the Mongolian ranges matter ~4x more than Tibet (White et al. 2017,
  doi:10.1175/JCLI-D-16-0401.1). Heat release over warm currents (Kuroshio)
  forces a high and cold air to its west (Kaspi & Schneider 2011).
- CLIMBER-X diagnoses azonal sea-level pressure p* ≈ −2.3 hPa/K × T*_sl and
  still keeps eastern-continent winters too warm.
- Meiyu rain: southerlies between the Asian heat low and the Pacific high,
  advection of moist static energy by the stationary meridional wind (Sampe &
  Xie 2010, doi:10.1175/2009JCLI3128.1; Chen & Bordoni 2014,
  doi:10.1175/JCLI-D-13-00479.1); summer subtropical highs are forced by
  monsoon heating through the Sverdrup balance (Rodwell & Hoskins 2001).
- Check: the model's thermal wind already uses the sea-level-equivalent
  temperature, as CLIMBER-X does (no false summer high over Tibet).

Proposals: (1) a local radiative correction to land T_eq: cloud proxy from the
rain machinery, clear-sky emissivity from column water (Prata 1996,
doi:10.1002/qj.49712253306), snow albedo, a calm-air coupling for inversions
(estimated −5 to −9 K over Inner Mongolia in January); (2) poleward monsoon
flow from rain heating, v = s·tanφ·(P − P0), and weaker summer trades over
land; (3) frontal ascent from moist-static-energy advection; (4) blocking of
cold air by terrain (Froude number) and a Kaspi-Schneider high west of warm
seas.

## D. Rain shadows, dry interiors and dryland summer heat

- Diagnosis: the storm-eddy moisture mixing relaxes W toward a smoothed field
  of mostly sea-level columns, but a column over high ground holds ~exp(−z/2.5
  km) less water; plateaus and basins behind ranges get sea-level moisture at
  inflated humidity (Reno ~1.7x). CLIMBER-X mixes specific humidity above the
  surface (Willeit et al. 2022 eqs. A42-A51); UVic found vapour "not
  sufficiently depleted" over high land (Brennan et al. 2011).
- Smith & Barstad linear theory: condensation ≈ (W/H_w)·U·∇h with 1000-2400 s
  cloud times (under one 56 km cell); descent is an equal negative source that
  evaporates spillover. Observed drying ratios 0.32 (northern California),
  0.42 (Oregon Cascades).
- Clouds cut land surface sunshine by >100 W m−2 in humid regions and cool the
  surface by up to 7 K; the effect vanishes in arid regions (Ghausi et al.
  2023, doi:10.1073/pnas.2220400120). With a latitude-only albedo every column
  carries its latitude's mean cloudiness.

Proposals: (1) **terrain-aware eddy moisture mixing** (implemented as
`eddy_moisture_height_km`): mix the sea-level equivalent W·exp(z/H_w) and
convert back, W_e = exp(−z/H_w)·S[W·exp(z/H_w)]; (2) **cloud cover from the
model's RH and ascent shading the land relative to its latitude's mean**
(implemented with item C1 as `cloud_radiation`); (3) moisture-flux upslope
condensation with subtractive lee evaporation (drying-ratio law); (4) eddy
mixing scaled by storm-track strength.
