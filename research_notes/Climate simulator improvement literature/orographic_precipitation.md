# Orographic precipitation: linear theory (Smith & Barstad), LFPM, implementations and real rain-shadow gradients, for use in rotclimate

Research scope: what the orographic-precipitation literature offers a fast 2-D steady climate simulator on a 7–14 km grid (about 300×150 cells) with 4 height tiers. The simulator's known problems are rain shadows that are too sharp in places (347 vs 1,548 mm/yr within 40 km) and a "spillover" scheme that went unstable at 50 km.

Source access notes: the Smith & Barstad (2004) J. Atmos. Sci. paper itself could not be downloaded (journals.ametsoc.org returned 403). Its equations and parameter values below come from (a) the authors' own 2003 AMS conference preprint of the same theory, (b) the authors' 2004 Oregon application preprint, (c) the PISM manual, which reproduces SB04 Eq. 49, (d) the fastscape-lem source code, and (e) Hergarten & Robl (2022), who discuss SB04 in detail. These agree with one another.

---

## Q1. Smith & Barstad (2004) linear theory (LT): equations, τc/τf, spillover, FFT, parameter values, limits; Smith & Evans 2007, Barstad & Schüller 2011, Jiang & Smith 2003 on calibration

### Takeaway
LT is a single FFT transfer function. It multiplies the terrain spectrum by an upslope source (Cw·iσ·ĥ), a mountain-wave airflow factor 1/(1−i·m·Hw), and two cloud-delay factors 1/(1+iστc) and 1/(1+iστf). The result is inverse-transformed, a background rate is added, and negative values are truncated. Spillover is built in: condensed water drifts downwind about U·τ per stage, roughly 15–36 km for τ = 1000–2400 s and U = 15 m/s. The default τc = τf = 1000 s is weakly constrained by observations (anywhere from 500 to 5000 s). Isotope-based calibrations give more than 600 s for Oregon and about 1700 s for the southern Andes. The theory assumes linear, saturated, steady flow in one wind direction. It has no water budget, so it can rain out more than the incoming vapour flux, and it tends to make lee sides too dry.

### Cited Findings
**Governing equations (steady, vertically integrated):**
- Cloud water q_c and hydrometeors q_h obey U·∇q_c = S(x,y) − q_c/τc and U·∇q_h = q_c/τc − q_h/τf. Ground precipitation is P = q_h/τf. The source can be the classical upslope form S = Cw·U·∇h (Smith 1979) or can be computed with mountain-wave theory. Lifting drives S positive. In downslope regions S is negative, which dries the air and evaporates hydrometeors — [Smith & Barstad 2003 AMS preprint "A Linear Theory of Orographic Precipitation"](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- Transfer function: P̂(k,l) = Cw·iσ·ĥ(k,l) / [(1 − i·m·Hw)(1 + iστc)(1 + iστf)], with σ = Uk + Vl (intrinsic frequency), m = {[(Nm² − σ²)/σ²](k² + l²)}^½ and Cw = ρ_v0·Γm/γ — [Smith & Barstad 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf). The PISM manual gives the same formula as "equation 49 in" SB04 and writes Cw = ρ_Sref·Γm/γ — [PISM manual, Orographic precipitation](https://www.pism.io/docs/climate_forcing/atmosphere.html)
- With Coriolis: m(k,l) = {[(Nm² − σ²)/(σ² − f²)](k² + l²)}^½, "the proper root". The physical field is P(x,y) = Max[∫∫P̂ e^{i(kx+ly)} dk dl + P∞, 0], where P∞ is background (synoptic) precipitation — [Smith, Barstad & Bonneau, AMS preprint "Orographic precipitation and Oregon's climate transition"](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Meaning of the factors: "The first bracket shifts the pattern upstream while the second and third brackets shift the pattern downstream. All three brackets generally decrease the precipitation amount." The Max() truncation "sets negative values equal to zero in regions of strong descent". When Cw = 1, mHw << 1 and τc = τf = 0, LT reduces to the simple upslope model — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Downslope evaporation is "not contained explicitly in (2), but is present when the predicted precipitation field P(x,y) is truncated according to P_Trun(x,y) = Maximum(P,0)." τc and τf are "mathematically analogous" — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- τc describes both the conversion of cloud water to hydrometeors and the evaporation of hydrometeors in subsaturated air — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Efficiency diagnostics: PE_dyn = S_dyn/S_ref (lost because wave lifting does not penetrate the moist layer) and PE_cloud = P/S_dyn (lost because condensate is advected into the lee and evaporates) — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- Scale selectivity: "Vertical motions from small horizontal scales (D<1km) do not penetrate substantially into the moist layer and have little influence on precipitation. Intermediate scales (D~5km) generate lee wave clouds but little precipitation. Longer scales (D>15km) are increasingly efficient at producing precipitation." — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)

**Spillover:**
- Spillover comes from the cloud-delay factors. If τ is short, condensate forms and falls on the windward side. If τ is long, condensate is carried to the lee and evaporates — [IMO report 2012-003 (Crochet), Sect. 2](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf). In idealized Oregon, "the cloud effect decays on the advection scale Uτ = 15 m/s × 2400 s = 36 km" — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- In the Olympic Mountains demo (SW wind 15 m/s, Nm = 0.005 s⁻¹, Hw = 2.5 km, τ = 1000 s each): "There is some spillover, but mostly the northeast lee slopes are dry", with a maximum of about 26 mm per 6 h just upwind of Mt Olympus — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- Physical range of hydrometeor drift: fall speeds run from about 1 m/s (snow) to 10 m/s (rain). With winds of 5–30 m/s, a particle starting at 3 km height "can get advected anywhere between 1.5 and 90 km before reaching the surface" — [Roe 2005, Annu. Rev. Earth Planet. Sci.](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)

**Typical parameter values:**
- SB 2003 triangle-ridge example: T0 = 280 K, γ = −5.8 K/km, Γm = −6.5 K/km, U = 15 m/s, Nm = 0.005 s⁻¹, ρ_Sref = 7.4 g/m³, Hw = 2500 m, τc = τf = 1000 s, ridge h = 500 m, half-width a = 15 km. Raw upslope gives 15 mm/h. With dynamics and delays the peak drops to about 3 mm/h near the hilltop — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- PISM defaults: τc = τf = 1000 s, Hw = 2500 m, γ = −5.8 K/km, Γm = −6.5 K/km, ρ_Sref = 0.0074 kg/m³, U = 10 m/s, wind from 270°, Coriolis latitude 0. The default Nm is 0.05 s⁻¹, ten times the 0.005 s⁻¹ in the SB examples. Options: background_precip_pre and background_precip_post, truncate = true, a Gaussian smoothing option, and grid_size_factor = 2 — [PISM manual](https://www.pism.io/docs/climate_forcing/atmosphere.html)
- Idealized Oregon reference run: ρ = 1.2 kg/m³, qv = 0.0044, U = 15 m/s, Nm = 0.003 s⁻¹, Hw = 3000 m, f = 10⁻⁴ s⁻¹, τc = τf = 2400 s. Two Gaussian ridges (750 m and 1500 m, 30 km width, 200 km apart) peak at 1.4 and 3.4 mm/h — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Hergarten & Robl summarise SB04 as suggesting "timescales of 200 to 2000 s for the conversion of cloud water and for fallout, corresponding to length scales Lc and Lf of 10 to 100 km at wind speeds of 50 m s⁻¹". They also note SB04 suggested Lc = Lf, and that SB04 uses a nondimensional Ĥ (hydrostatic airflow parameter) with Ĥ = 1 "suggested as a typical value" — [Hergarten & Robl 2022, GMD 15:2063](https://gmd.copernicus.org/articles/15/2063/2022/)

**Calibration studies:**
- Oregon: state-wide gauge and satellite patterns "constrain the taus only within a broad range from about 500 to 5000 seconds". Oxygen-18 data imply a drying ratio of about 43%, "requiring an average cloud physics delay time greater than τ = 600 seconds". The climate runs used τ = 1200 s — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Sensitivity to τ: halving τ from 2400 to 1200 s nearly doubled the two precipitation maxima and moved them upstream. Total precipitation became 240 kg/(m·s) against an incoming vapour flux of 216 kg/(m·s): "in the 1200s run, the total precipitation exceeds the incoming flux!" — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Smith & Evans 2007 (J. Hydrometeorol. 8:3–19, southern Andes 40–48°S): 71 stream-water isotope samples give a drying ratio near 50%. The best-fit cloud delay time in the linear model is about 1700 s. Column water vapour drops from about 1.4 to 0.7 cm across the range — [abstract as indexed by NASA MODIS science team](https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=02353). This is from the abstract only; the full text was not read.
- Smith & Evans 2007 also proposed reducing the water vapour flux downwind along the trajectory to account for depletion. IMO implements this as a drying ratio DR(x,y) = ∫P ds/(F0 − F∞) along the upstream path and scales precipitation by Θ = exp(−DR) — [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf)
- Iceland (Crochet et al. 2007, J. Hydrometeorol. 8:1285–1306): Nm, τc and τf were "fixed once for all by statistical optimization" against gauge and glaciological data. A later IMO version parameterizes τc from the melting-layer height, τc = 1200·(0.5 + arctan((z − (zm + 200))/500)/π) s, and caps hydrometeor fall speed at 0.1–5 m/s — [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf)
- Jiang & Smith (2003, "Cloud physics time scales and orographic precipitation", JAS) "discuss a strong non-linearity associated with collection and accretion". SB call the constant-τ assumption "particularly problematic" — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf)
- Barstad & Schüller (2011) extended LT to multiple vertical layers. Hergarten & Robl say SB "still predicts extremely dry leeward sides, and improving this behavior was obviously one of the motivations for extending the model by multiple layers" — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)

**Limits:**
- SB list "linear wave dynamics, near saturation, steady state, etc." as strong assumptions — [SB 2003 preprint](https://ams.confex.com/ams/pdfpapers/62756.pdf). The Oregon paper adds "simplification of vertical structure by vertical integration, linearization of the fluid and cloud dynamics and the lack of a full water budget. Far downstream, all perturbation quantities return to zero, implying a return to a saturated state with a background precipitation rate." It also says high terrain "may push the linear theory beyond its range of applicability" — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Linearity in terrain: precipitation patterns "depend only on the lateral structure of the topography but not on the absolute elevation". A descending ramp gives negative precipitation. For short, high ramps these negatives are "too high to be compensated for by the background rate", hence the truncation. The SB model "cannot predict transport over long distances" and needs refilling from a background reservoir. On a large plain, precipitation always relaxes back to the background rate whatever lies upwind — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- The FFT requires periodic input. Implementations pad with zeros onto an extended grid. Sharp breaks in surface gradient cause Gibbs oscillations, which PISM handles with optional Gaussian smoothing of elevation ("Values around dx appear to be effective") — [PISM manual](https://www.pism.io/docs/climate_forcing/atmosphere.html)
- At synoptic and climate scales, Coriolis and non-hydrostatic terms matter little for 30 km-wide ridges: "the changes are too small to perceive" — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)

### Inferences
- The cloud-delay part of LT is equivalent in physical space to convolving the condensation source along the wind with a two-stage linear-reservoir kernel. For τc ≠ τf the kernel is g(s) = [e^(−s/(Uτc)) − e^(−s/(Uτf))]/[U(τc − τf)]. For τc = τf = τ it is g(s) = s·e^(−s/(Uτ))/(Uτ)² for s > 0. This is derived from the transfer function above, not quoted from a source. Implemented this way (a downwind exponential or gamma kernel applied to rotclimate's existing uplift source, or an implicit upwind sweep), spillover is unconditionally stable for any drift length. The instability rotclimate saw at 50 km most likely comes from an explicit or under-resolved discretisation, not from the physics.
- With U·τ about 15–36 km and grid cells of 7–14 km, the drift distance spans only 1–5 cells. Spillover should therefore change rain on the lee crest and upper lee slope, not 40 km into the plain. That fits rotclimate's finding of "no gain at 15–30 km".
- LT will not by itself cure an over-sharp rain shadow. Its negative lee values, truncated at 0, are the very behaviour Hergarten & Robl and Barstad & Schüller criticise. If LT is adopted, add the large-scale background after truncation (PISM's background_precip_post) rather than before, so lee descent cannot erase the synoptic rain.
- The terrain has only 4 tiers. Because LT depends on ∇h through iσĥ, tier edges act as slope spikes. Smoothing h with σ ≈ 1–2 dx before the FFT (as PISM advises) is probably essential, or rain will collect in lines along tier boundaries.

### Gaps
- The SB04 paper itself was not accessible (403), so its exact nondimensional analysis (e.g. definitions of Ĥ, the drying-ratio and precipitation-efficiency formulas, and its own recommended τ range) is reported only second-hand via Hergarten & Robl and the authors' preprints.
- Barstad & Schüller (2011) and Jiang & Smith (2003) were not read in full. Only their roles as reported by citing papers are given.
- The Smith & Evans (2007) 1700 s value comes from an indexed abstract, not the full paper.

---

## Q2. Python and open-source implementations (licence, how wind/time are handled)

### Takeaway
Two ready implementations exist. fastscape-lem `orographic_precipitation` is MIT-licensed pure numpy (one function, scalar wind per call). PISM's C++ `orographic_precipitation` modifier and the PISM/Aschwanden QGIS "LinearTheoryOrographicPrecipitation" plugin are both GPL-3.0. Testing in this session found a wavenumber-scaling bug in the fastscape code for non-square grids, which matters directly for a 300×150 grid. One call on a 150×300 grid took about 27 ms here.

### Cited Findings
- fastscape-lem/orographic-precipitation: "A Python framework that implements the Linear Theory of Orographic Precipitation following Smith & Barstad (2004)". It needs Python ≥ 3.9 and numpy, with optional fastscape and xarray-simlab for the fastscape extension. Install with pip from GitHub or conda-forge — [GitHub repo](https://github.com/fastscape-lem/orographic-precipitation); [PyPI](https://pypi.org/project/orographic_precipitation/0.1rc0/)
- Licence: MIT, "Copyright (c) 2020 Raphael Lange" — [LICENSE](https://github.com/fastscape-lem/orographic-precipitation/blob/master/LICENSE)
- API: `compute_orographic_precip(elevation, dx, dy, **param)` with keys latitude, precip_base (mm/h, "usually [0, 10]"), precip_min, wind_speed (m/s), wind_dir ("0: south, 270: west"), conv_time (s), fall_time (s), nm (1/s), hw (m) and cw (kg/m³, "product of saturation water vapor sensitivity ref_density and environmental lapse rate (lapse_rate_m / lapse_rate)"). It returns mm/h — [source code](https://github.com/fastscape-lem/orographic-precipitation/blob/master/orographic_precipitation/orographic_precipitation.py)
- How the code works:
  - It zero-pads by min(ceil(sum(shape)/2), 200) cells and runs `np.fft.fft2`.
  - It sets m = sign(σ)·sqrt(|(Nm² − σ²)/(σ² − f²)·(k² + l²)|), clipping Nm² − σ² at 0 and the denominator at ±machine-epsilon.
  - It multiplies by the SB transfer function, inverse-transforms, multiplies by 3600 to get mm/h, and adds precip_base.
  - It then sets values ≤ 0 equal to precip_min (a replacement, not an addition).
  - Wind is a single scalar speed and direction per call.
  - [source code](https://github.com/fastscape-lem/orographic-precipitation/blob/master/orographic_precipitation/orographic_precipitation.py)
- **Bug found in this session (reproducible):** the code builds the column wavenumbers from `fftfreq(ny, 1/ny)` (ny = number of columns) but scales them by `x_len = nx*dx` (nx = number of rows), and does the reverse for rows. On square arrays it matched an independent numpy re-implementation exactly (max difference 0.000 mm/h on 200×200). On a 150×300 array the peaks were 12.31 vs 10.92 mm/h, with a maximum point difference of 2.88 mm/h (same parameters, dx = 10 km, smoothed random terrain to 3 km). Workaround: pad the input to a square before calling, or patch the code to use `fftfreq(ncols, d=dx)` and `fftfreq(nrows, d=dy)`. Based on [the source code](https://github.com/fastscape-lem/orographic-precipitation/blob/master/orographic_precipitation/orographic_precipitation.py) plus a test run in this session.
- PISM `-atmosphere ...,orographic_precipitation` (C++ class pism::atmosphere::OrographicPrecipitation) implements SB04 with Coriolis. The output is P = max(P_pre + P_LT, 0)·S + P_post. Elevation is the only spatially variable input. The wind convention is U = −sin(φ)·W, V = −cos(φ)·W, with φ "the direction the wind is coming from", measured clockwise from y. The extended grid is (Z(Mx−1)+1) × (Z(My−1)+1) with Z = 2. It runs as a modifier on top of another atmosphere model, e.g. `-atmosphere yearly_cycle,orographic_precipitation` — [PISM manual](https://www.pism.io/docs/climate_forcing/atmosphere.html)
- PISM licence: GNU GPL v3 — [PISM COPYING](https://github.com/pism/pism/blob/main/COPYING)
- "Linear Theory (LT) of Orographic Precipitation Model QGIS plugin", "A Python/numpy plugin for QGIS by Andy Aschwanden and Constantine Khrulev … original Python code written by Leif Anderson". Licence GPL-3.0, Zenodo DOI badge — [pism/LinearTheoryOrographicPrecipitation README](https://github.com/pism/LinearTheoryOrographicPrecipitation)
- Measured cost in this session: about 27 ms per `compute_orographic_precip` call on a 150×300 grid (padded to 550×700) with numpy on the sandbox CPU, averaged over 50 calls. Measurement only, no external source.

### Inferences
- For rotclimate, a self-written roughly 30-line numpy version (as in the test) is the safest route. It avoids the GPL licence (PISM, the QGIS plugin), the non-square bug, and the ambiguous wind convention. The fastscape package names wind_dir as "0: south, 270: west" with v0 = +cos, while PISM uses V = −cos and "coming from". Whichever is used, check it with a single test ridge.
- ĥ is fixed because terrain is static. Compute fft2(h) once. Each wind state then costs one complex multiply plus one ifft2, probably well under 27 ms. The current pad of 200 cells (1,400–2,800 km at 7–14 km spacing) is far more than needed. Padding by about 3–5 drift lengths plus a mountain-wave decay scale (about 100–200 km, i.e. 10–30 cells) would be enough, but test this.

### Gaps
- No search was made for standalone pip packages named "LTOP" other than the PISM QGIS plugin. Whether a pip-installable stand-alone LTOP exists was not verified.
- fastscape notebook examples, showing parameter values chosen in practice and any monthly or seasonal use, were not read.

---

## Q3. Roe (2005) key scales; Hergarten & Robl (2022) LFPM and its advantages at large scale

### Takeaway
Roe (2005) gives the core scales:
- moisture scale height Hm ≈ 2–4 km;
- the upslope model works for ranges wider than about 40 km and higher than about 1.5 km;
- hydrometeor drift of 1.5–90 km;
- a "factor 2 over tens of km" pattern variability even without a range-scale shadow.

LFPM (Hergarten & Robl 2022) adds re-evaporation feedback to a two-component (vapour plus cloud water) steady advection model. This gives two emergent length scales: a short orographic one, Ls, and a long continental transport one, Ll of about 100–1000 km. The result is a closed water budget, no negative lee values, built-in smoothing, and O(N) cost via an implicit upwind sweep. It is structurally very close to rotclimate's existing advection–diffusion moisture field.

### Cited Findings
**Roe 2005 (Annu. Rev. Earth Planet. Sci. 33:645–71):**
- Saturated vapour density is ρ·q_sat(z) ≈ ρ0·q0_sat·exp(−z/Hm). "Hm is approximately 4 km in the tropics and 2 km at high latitudes". A 10 °C cooling halves saturated moisture content — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)
- Upslope source example: for |u| ≈ 10 m/s, slope ≈ 2/50, ρ0 ≈ 1.2 kg/m³ and q0_sat = 8 g/kg, S = 14 mm/h at sea level, "which would be very heavy precipitation". The ratio of observed precipitation to S is the precipitation efficiency. Because condensation falls exponentially with surface height, precipitation for large ranges tends to peak lower on the windward slopes — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)
- "At spatial scales greater than approximately 40 km, and for mountain ranges exceeding approximately 1.5 km in height, the forced upslope ascent model generally gives a good basic description … the precipitation pattern is offset downwind somewhat, owing to the advection of hydrometeors" — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)
- Large ranges have their maxima on the windward flank away from the crest. Small hills peak near the crest — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)

**LFPM (Hergarten & Robl 2022, GMD 15:2063–2084, CC BY 4.0):**
- Steady equations for vapour flux Fv and cloud flux Fc, with advection along x and transverse dispersion Ld:
  - −∂Fv/∂x + Ld·∂²Fv/∂y² − (Fv − βFc)/Lc = 0
  - −∂Fc/∂x + Ld·∂²Fc/∂y² + (Fv − βFc)/Lc − Fc/Lf = 0
  - P = Fc/Lf, with Lc = v·τc and Lf = v·τf
  - Altitude enters only through re-evaporation: β = β0·exp(−H/H0).
  - [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Two emergent length scales: Ll = Lc/λ−, Ls = Lc/λ+, with λ± = (1+β+φ)/2 ± sqrt(((1+β+φ)/2)² − φ) and φ = Lc/Lf. Their product is Ll·Ls = Lc·Lf. Ll > max(Lc, Lf) and Ls < min(Lc, Lf). Ll is "the ability to transport moisture over large distances". Ls "can be considered the length scale of orographic precipitation" and provides smoothing "on its own". Ll shrinks with elevation and Ls grows — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Example: with β = 10 and Lc, Lf of 10–100 km, Ll ranges from 119 to 1191 km. Makarieva et al. (2009) found an exponential decay of mean precipitation with distance from the ocean, with a decay length of about 600 km, at non-forested areas — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- β can be set from a chosen Ll: β = (Lc/Ll)·(Ll/Lf − 1)·… (Eq. 33: β = (1 − Lc/Ll)(Ll/Lf − 1)). The inflow boundary should be in the long-range mode, Fc = F·Lf/Ll, to avoid a spurious coastal transition — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Transverse dispersion makes a transverse anomaly of half-wavelength Ly decay downwind over Lx = Ly²/(π²·Ld). Without dispersion, an obstacle "causes an infinite precipitation shadow" — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Evapotranspiration as a fixed fraction ε of precipitation (recycled to vapour) lengthens transport, L̃l ≈ Ll/(1 − ε). It is made height-dependent as ε = ε0·exp(−H/H0) — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Numerics: an upwind difference in x plus implicit transverse dispersion gives, at each x-column, a block-tridiagonal (2×2 blocks) system in y solved directly. That is a single sweep downwind with linear time complexity. Cost was about 2.4× the simplest stream-power erosion step. Periodic y-boundaries are the default; Neumann would be cheaper — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Advantages over SB claimed by the authors:
  - SB is one-way coupled (β = 0), so its transport length is only max(Lc, Lf), about 10–100 km, and it needs a background reservoir.
  - SB "still predicts extremely dry leeward sides" and needs truncation.
  - LFPM guarantees Fv, Fc ≥ 0, so "no truncation in order to avoid negative precipitation rates".
  - LFPM predicts dry high plateaus (Tibet), which SB cannot.
  - LFPM preserves O(N) cost.
  - [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Real-world test (India–Asia, 1 km grid, uniform wind from S or from SW):
  - Settings: Lc = Lf = 25 km, Ll = 500 km, ε0 = 0.75, H0 = 2 km, Ld = 25 km. Influx was scaled so the domain mean matched TRMM (0.99 m/yr).
  - RMS error was 0.81 m/yr vs TRMM2b31 (S wind) and 0.84 (SW), and 0.77/0.80 vs WorldClim. Tuning reduced it to about 0.6 m/yr. For comparison, TRMM vs WorldClim RMS is 0.42 m/yr.
  - "the flow direction has a strong influence on the precipitation pattern. Compared to this influence, the effect of the parameter values is much weaker". The authors call the uniform wind direction a principal limitation.
  - [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Code: FreiDok doi:10.6094/UNIFR/219131, and OpenLEM (http://hergarten.at/openlem) "also contains an implementation of the LFPM" plus a stand-alone version — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- The Garcia-Castellanos (2007) one-component model is the Lc → 0 limit of LFPM. It keeps long-range transport but loses Ls, so it needs ad-hoc half-Gaussian upwind smoothing (about 2Ls) — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- A GMD reviewer asked for validation against observations and comparison with SB-type models, noting SB had "done this job thoroughly" — [GMD discussion, referee comment](https://gmd.copernicus.org/preprints/gmd-2022-144/gmd-2022-144-ATC3.pdf). This came from search snippets and is attributed only to the discussion.

### Inferences
- rotclimate already has a single-component steady advection–diffusion moisture field with uplift rain. That is essentially Garcia-Castellanos-like, the Lc → 0 limit of LFPM. Upgrading to LFPM means adding a second carried field (cloud water). That supplies:
  - a physical spillover and smoothing scale Ls, without explicit hydrometeor transport;
  - lee rain that never goes negative or to zero, since the background comes from the carried vapour;
  - an implicit sweep that is stable for any Lc/dx.
- This targets both of rotclimate's issues (too-sharp shadow, unstable spillover) more directly than LT.
- On a 7–14 km grid, Lc = Lf ≈ 25 km is only 2–4 cells, so Ls (< 25 km) will be about 1–2 cells. Expect LFPM's own smoothing to be modest at this resolution. Transverse dispersion Ld and the β(H) dependence will matter more for shadow sharpness.
- LFPM's elevation dependence through β = β0·exp(−H/H0) with H0 ≈ 2 km suits a 4-tier terrain better than LT's slope dependence. Tier steps change β in steps, which LFPM smooths over Ls, whereas LT turns steps into slope spikes.

### Gaps
- The licence of the LFPM/OpenLEM code was not checked; only the paper's CC BY 4.0 licence was seen.
- How LFPM handles non-axis-aligned wind (the SW case) on a regular grid is not described in the parts read. Grid rotation or resampling is presumably needed.

---

## Q4. Real-world rain-shadow gradients (halving distances, windward/leeward ratios)

### Takeaway
Strong real rain shadows across major ridges perpendicular to the prevailing wind fall by about 7–12× over about 50–65 km. That is a halving distance of about 14–23 km. rotclimate's 1,548 → 347 mm/yr over 40 km (4.5×, halving about 18.5 km) is therefore within the real-world range for a major barrier such as the Olympics or Southern Alps. It is too sharp only if the barrier is a low (hill-tier) or discontinuous ridge, or if storms come from several directions (Alps-like). Ridge–valley contrasts of 1.5–2× at 10 km scale and up to 5× at 40 km also exist on the windward side.

### Cited Findings
- **Southern Alps (NZ):** 2–3 m/yr over the western lowlands, a maximum of 11–12 m/yr about 20 km upwind of the divide, then dropping "off rapidly to less than 1 m year⁻¹ over the eastern plains" (Wratt et al. 2000 gauge transect). Roe calls it "one of the most dramatic" rain shadows anywhere — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf). About 1,000 mm/yr roughly 30 km east of the main divide — [Wikipedia: Southern Alps](https://en.wikipedia.org/wiki/Southern_Alps) (secondary). Up to 13 m/yr in a narrow band just west of the divide — [Te Ara: rainfall across the Southern Alps](https://teara.govt.nz/mi/graph/4872/rainfall-across-the-southern-alps)
- **Olympic Mountains (WA):** more than 3 m/yr in the Hoh valley (W) vs 0.4 m/yr at Sequim (NE corner), citing Thomas et al. 1999 — [Anders et al. 2007, J. Hydrometeorol.](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/AndersEtAl_Olympics_JHM07.pdf). The rainforest is "less than 35 miles" (56 km) from Sequim — [NPS Olympic weather brochure](https://www.nps.gov/olym/planyourvisit/weather-brochure.htm)
- **Small-scale (windward) gradients:**
  - Olympics: totals are "50% higher on top of an ~800-m-high ridge relative to valleys on either side, 10 km distant". MM5 4-km runs give ridges 1.5–3× neighbouring valleys 10–15 km away — [Anders et al. 2007](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/AndersEtAl_Olympics_JHM07.pdf). A 50–70% ridge-crest excess over adjacent valleys (ridges about 10 km wide, about 800 m high) in the annual mean — [Minder et al. 2008, QJRMS](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/MinderEtal_Olympics_QJRMS08.pdf)
  - Alps: annual precipitation "varies by a factor of 2 over spatial scales of less than 50 km", not because of a range-scale rain shadow. Himalaya: fivefold variation over 40 km between valleys and ridges (TRMM, Anders et al. 2006) — [Anders et al. 2007](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/AndersEtAl_Olympics_JHM07.pdf)
- **European Alps:** "does not have a well-defined rain shadow: Precipitation maximizes at approximately the same value on the northern and southern flanks, and at rates roughly twice as large as in the higher interior" — [Roe 2005](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/Roe_OrogPrec_AnnRev05.pdf)
- **Oregon:** LT reproduces Oregon's "sharp east-west climate transition". Isotopes show a drying ratio of about 43% across the Coast Range and Cascades — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf). Southern Andes drying ratio is about 50% — [Smith & Evans 2007 abstract](https://modis.gsfc.nasa.gov/sci_team/pubs/abstract_new.php?id=02353)
- **Washington Cascades:** Ellensburg about 9 in (230 mm)/yr in the rain shadow vs Seattle about 38 in. Precipitation approaches 25 in/yr closer to the crest within the field-trip area — [CWU field-trip guide](https://www.cwu.edu/academics/geography/_documents/margins-of-the-eastern-cascades-field-trip.pdf); about 230 mm on the eastern foothills — [Wikipedia: Cascade Range](https://en.wikipedia.org/wiki/Cascade_Range)
- **Sierra Nevada:** Bishop (Owens Valley) about 14 cm/yr. The Sierra peaks a few miles west receive "nearly 4 times that amount" — [Bishop visitor site](https://bishopvisitor.com/about-bishop/) (low-quality tourism source; treat as indicative only)

### Inferences
- These halving distances are computed here from the cited endpoints, not given by the sources:
  - Southern Alps, about 12 m → about 1 m over about 50 km (20 km W of divide to 30 km E): ratio about 12, halving about 14 km, e-folding about 20 km.
  - Olympics, about 3 m → 0.4 m over about 56–66 km: ratio about 7.5, halving about 19–23 km.
  - rotclimate, 1,548 → 347 mm over 40 km: ratio 4.5, halving about 18.5 km.
- So rotclimate's gradient is not by itself unphysical. It is unrealistic only where the barrier is lower or narrower than about 1.5 km × 40 km (Roe's upslope-validity scale), or where the climatology mixes wind directions.
- A useful plausibility rule for the simulator: the leeward/windward-maximum ratio should be about 0.1–0.2 only for tall (> 1.5–2 km), continuous, wind-perpendicular ranges with a dominant wind direction (Southern Alps, Olympics, Cascades). It should be closer to 0.5–1 for ranges hit from several sides (Alps). The drying ratio across a single major range is about 40–50% (isotope-based), which bounds how much vapour a range can remove.

### Gaps
- No peer-reviewed crest-to-lee transect with distances was found for the Cascades or the Sierra Nevada. A PRISM transect would be the proper source.
- The Southern Alps "30 km east" figure is from Wikipedia. The primary source is Wratt et al. (1996/2000) or Griffiths & McSaveney (1983), which were not read.

---

## Q5. Applying LT/LFPM in a seasonal model with varying winds; combining with a background field; cost on about 300×150

### Takeaway
Published climatological uses of LT run it once per wind state:
- every 6 h with reanalysis winds (Iceland);
- a few wind directions weighted by observed frequency (Oregon).

Each run adds a background (synoptic) precipitation field from which the coarse-orography part has been removed to avoid double counting, truncates, and then averages. They often also apply a downwind vapour-depletion factor exp(−drying ratio). On a 300×150 grid one LT evaluation costs about 10–30 ms, so even hundreds of wind states per year are negligible. LFPM needs wind along a grid axis, so it requires grid rotation per direction, but it is O(N).

### Cited Findings
- Oregon "climate runs": "we ran the model with three SW wind directions and speeds and weighted the results with the observed frequency distribution. A value of τ = 1200 s is used" on 1 km terrain — [Oregon preprint](https://ams.confex.com/ams/pdfpapers/76934.pdf)
- Iceland (IMO), forced by ERA-40 "with a time step of 6 hours":
  - LT is first applied to the ERA-40 (coarse) orography to estimate the orographic precipitation already present in the background, which is removed "in order not to double count it". Background below 0.15 mm/6 h is set to 0.
  - LT is then applied with true orography plus the corrected background.
  - [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf)
- Iceland multi-domain runs:
  - The model "was run three times per time step over the entire domain". Mean wind, Nm and τ were computed per sub-domain, and each sub-domain's result was taken from the run using its own winds, then merged. The reason given is that mean wind direction "may vary within the domain and will have a strong impact on the spatial pattern of precipitation".
  - A humidity factor λ = 1 − exp(−((RH850 − 0.8)/0.125)⁴) for RH850 > 0.8 (else 0) restricts where orographic rain is produced.
  - Vapour depletion: Θ = exp(−DR) with DR = ∫P ds/(F0 − F∞).
  - [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf)
- The Crochet et al. 2007 / Jóhannesson et al. 2007 product is a 1 km daily gridded precipitation dataset for Iceland, 1958–2006 — [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf). Other LT climatological applications listed: Alps (Barstad & Smith 2005), southern Andes (Smith & Evans 2007), Norway (Schuler et al. 2008), British Columbia (Jarosch et al. 2010), and climate-scenario downscaling for western Norway (Caroletti & Barstad 2010) — [IMO report 2012-003](https://vedur.is/media/vedurstofan/utgafa/skyrslur/2012/2012_003_web.pdf)
- PISM combines LT with other atmosphere components as a modifier. Background can be added before (P_pre) or after (P_post) truncation, with a scale factor S — [PISM manual](https://www.pism.io/docs/climate_forcing/atmosphere.html)
- LFPM real-world runs used one uniform wind direction per run (S or SW). The domain was "extended in such a way that each flow line … starts from a point in the ocean", ocean cells act as uniform-influx boundaries, and influx was scaled to match the observed domain mean — [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)
- Cost: about 27 ms per full fastscape call (150×300 padded to 550×700) measured in this session. LFPM is linear-time, about 2.4× the cost of a stream-power erosion step, according to [Hergarten & Robl 2022](https://gmd.copernicus.org/articles/15/2063/2022/)

### Inferences
Suggested rotclimate recipe (synthesised here, not taken from one source):
- **(a)** For each season or month, take a small wind rose (e.g. 4–8 directions, each with speed and frequency weight from the seasonal circulation) and compute LT for each from a cached fft2(h).
- **(b)** Truncate each run separately: add the background before truncation (P = max(P_bg + P_LT, 0)), or use a "post" background so lee rain never falls below a floor. Then take the frequency-weighted mean. Truncation is nonlinear, so weighting the transfer function first and truncating once will over-dry the lee.
- **(c)** Remove double counting: rotclimate's existing uplift rain is already an orographic term, so LT should replace it, not add to it. Or follow IMO and subtract the LT response to a heavily smoothed terrain.
- **(d)** Apply an IMO/Smith-Evans depletion factor exp(−∫P ds/F0) along the wind so a range cannot rain out more vapour than arrives (the Oregon 1200 s run exceeded influx by 11%).
- **(e)** Cost: about 12 months × 8 directions × about 15–30 ms is about 1.5–3 s per simulated year in numpy. Negligible.

Other inferences:
- rotclimate's 2-D steady advection–diffusion moisture field already supplies the long-range (Ll-type) continental decay that LT lacks. A hybrid that keeps that field as the vapour budget, uses an LT-style or LFPM-style local cloud-delay kernel for orographic redistribution, and debits rain from the vapour field is consistent with both literatures.
- If rotclimate adopts LFPM instead, each wind direction requires resampling the grid so that wind lies along an axis (or a sweep ordering along characteristics). Bilinear rotation of a 300×150 field, then a sweep, then rotation back is O(N) and still cheap. Rotation smears 4-tier terrain, which may be desirable anyway.

### Gaps
- No published benchmark of LT run time on a grid of about 300×150 was found. The only timing is the sandbox measurement here.
- No source was found that compares "per-wind-direction LT then average" against "LT with a mean wind" for climatology error. That comparison would need testing in rotclimate.
- The parts of the IMO report read here do not quantify the skill of the multi-domain and depletion refinements. The report's skill-score sections were not read in detail.
