# Intermediate-complexity models for validating rotclimate (ExoPlaSim/PlaSim, Isca, SPEEDY, EMICs, moist EBMs)

Note on access: readthedocs and arxiv pages could not be opened with WebFetch (DNS error), so they were downloaded with curl through the proxy and searched as text. The ExoPlaSim facts below come from the paper PDF (arXiv 2107.07685) and the model's own source code/docstrings (`exoplasim/__init__.py` on GitHub).

**Citation correction:** Paradise et al. (2022) was published in **MNRAS**, not PASP. The arXiv page says "Accepted to MNRAS" and gives the related DOI 10.1093/mnras/stac172 — [arXiv abs](https://arxiv.org/abs/2107.07685); [DOI](https://doi.org/10.1093/mnras/stac172).

## 1. ExoPlaSim / PlaSim: custom continent, retrograde spin, runtime, install, output, limitations

### Takeaway
ExoPlaSim is the most practical GCM for a one-off check, and it is a realistic job for a 4-core container. You install it with pip. It takes a custom land mask and topography as `.sra` files and writes 12 monthly means by default. At T21 a year takes about 4 minutes on a 4-core laptop. At T42 it takes about 15 minutes on 16 cores, so on 4 cores it is probably close to an hour per year (my extrapolation). Its ocean is a 50 m slab with no ocean heat transport. I found nothing saying the Python API supports retrograde spin, and its calendar code looks like it would break with a negative period. The clean workaround is to run normal prograde spin on an east–west mirrored map (see Q3).

### Cited Findings
**What it is and how it was validated**
- ExoPlaSim is a modified PlaSim built for synchronously rotating planets, non-solar spectra and non-Earth surface pressures. It "agrees qualitatively with more-sophisticated GCMs such as ExoCAM, LMDG, and ROCKE-3D, falling within the ensemble distribution on multiple measures." The paper says it is "fast enough" for surveys of "hundreds to thousands of models". It added a Python API, pip installation and online docs — [Paradise et al., arXiv 2107.07685](https://arxiv.org/abs/2107.07685)
- Physics: spectral core, usually T21 (32×64) or T42 (64×128), with 5 or 10 layers. It uses Kuo deep convection, Tiedtke shallow convection, dry convective adjustment and a simple two-band shortwave scheme with gray water. Rayleigh drag at the top is the default — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- PlaSim itself was described as "able to model a year of climate in under a minute of wall-time" (citing Paradise & Menou 2017) — [Paradise et al.](https://arxiv.org/abs/2107.07685)

**Runtime (concrete numbers from the paper, Sect. 3.1)**
- On HPC nodes with 8–32 threads: T21, 10 layers, 45-min timestep takes **30–60 s of walltime per model year**. With a 30-min timestep it takes 40–90 s per year. With a 5-min timestep (needed for very high or low surface pressure) it takes 6 min per year on 16 MPI threads — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- **T42, 15-min timestep, 16 MPI threads: about 15–16 min of walltime per model year** on Xeon E5-2650 nodes. T170 with 30 layers takes about 60 h per model year on 32 threads — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- **Consumer hardware:** on a 2017 quad-core laptop (i7-7700HQ, 4 MPI threads, other programs running), T21 with 10 layers takes **3.75 min per model year** with a 45-min timestep and **5.5 min per year** with a 30-min timestep — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- Throughput: "a minimum of approximately 7.5 × 10^4 cell-timesteps per second per thread, with 2.5–4 times that more characteristic" — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- Equilibration: "T21 aquaplanet models tend to require 50–200 years to run to energy balance equilibrium" (defined as TOA and surface net fluxes drifting less than 0.5 W/m² per decade). An Earth-like model can get close to equilibrium at T21 on a laptop "over the course of an extended lunch break" — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- A community user (Worldbuilding Pasta, in replies) says runs are "usually already most of the way there within 10" years even if full equilibration takes longer. This is informal — [Worldbuilding Pasta, ExoPlaSim post comments](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- Ocean coupling: MPI must stay within one node, because "inter-node data transfer speeds can slow the model down to runtimes comparable to running in single-thread mode" — [Paradise et al.](https://arxiv.org/abs/2107.07685)

**Installation**
- `pip install exoplasim`. It needs numpy and scipy (matplotlib only for extra utilities), the "GNU C (gcc/g++) and Fortran (gfortran) compilers", and "(optionally) MPI libraries". Optional extras are `exoplasim[netCDF4]` and `exoplasim[HDF5]`. A configuration and compile script runs on first import — [ExoPlaSim GitHub README](https://github.com/alphaparrot/ExoPlaSim)
- Resolutions offered: T21, T42, T63, T85, T106, T127, T170. The docstring says it has been "tested and validated most extensively at T21 and T42". Higher resolutions print "WARNING: This resolution is untested." — [ExoPlaSim source, `__init__.py`](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)
- Parallelism splits the planet into latitude bands, so the core count must divide the number of latitudes (32 at T21, 64 at T42). **4 cores works** — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)
- ExoPlaSim "won't run on Windows"; community users run it on Linux, WSL or VMs. The comment threads show many install pain points: numpy version conflicts, the `exoplasim.pyfft` module not being built on VMs, and runs killed by the Linux OOM killer — [Worldbuilding Pasta post and comments](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- One worldbuilder wrote that "getting ExoPlaSim to work is a huge pain" — [Idraluna Archives, Lunar Climate Simulations](https://idraluna-archives.bearblog.dev/lunar-climate-simulations/)

**Custom continent (land mask and topography)**
- `configure()` takes `landmap` ("Path to a `.sra` file containing a land mask for the chosen resolution") and `topomap` ("Path to a `.sra` file containing geopotential height map. Must include landmap"). The code copies them into the run as `N0xx_surf_0172.sra` (land mask, code 172) and `N0xx_surf_0129.sra` (geopotential, code 129). Other options: `orography` (a relief scaling factor; 0 removes topography), `aquaplanet` and `desertplanet` — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)
- The community workflow turns a grayscale or colour image into `.sra` files with an `image2sra` script from the "koppenpasta" repository. A full worked script template is in the Worldbuilding Pasta tutorial "An Apple Pie From Scratch, Part VI Supplement: Climate: Modeling Climate with ExoPlaSim" — [Worldbuilding Pasta](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- A user-reported bug: with custom `.sra` maps, T42 runs crashed (`mpiexec -np 4 most_plasim_t42_l10_p4.x ... exit status 136`) while T21 ran fine. Setting orography to 0 did not fix it, but removing the SRA arguments did. This is one user's report — [Worldbuilding Pasta comments](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- Planet and orbit settings: `rotationperiod` (days, default 1.0), `year` (days in a sidereal year), `eccentricity`, `obliquity` (default 23.441°), `lonvernaleq`, `fixedorbit`, `keplerian`, `gravity`, `radius`. Surface and land settings: `wetsoil`, `soilwatercap` (default 0.5 m), `soildepth`, `vegetation` (diagnostic or coupled, via the SimBA module) and glaciers — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)

**Retrograde rotation**
- I found no mention of retrograde rotation or negative periods in the docstrings. The code sets `ROTSPD = 1/rotationperiod` and also resets the calendar to `N_DAYS_PER_YEAR = max(int(360/rotationperiod/12+0.5),1)*12` whenever `rotationperiod != 1.0`. A negative period would therefore give a 12-day "year" unless overridden with `otherargs` — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)
- The paper explains that original PlaSim treated `rotspd` as a shortcut for the solar day, which "can produce significant inaccuracies for longer rotation periods". ExoPlaSim changed the code to use the sidereal day for dynamics — [Paradise et al.](https://arxiv.org/abs/2107.07685)

**Output and Köppen**
- The built-in `pyburn` postprocessor writes `.nc` (needs netCDF4), HDF5 and other formats. `cfgpostprocessor` defaults to `times=12, timeaverage=True`, which gives **12 monthly means**. Separate `snapshot` and `highcadence` output types exist — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py); [README](https://github.com/alphaparrot/ExoPlaSim)
- Köppen classification is **not** built in: a search of the source found no Köppen code. The community "koppenpasta" script turns ExoPlaSim output into Köppen maps by building an integer array of zone codes and colouring it — [Worldbuilding Pasta comments](https://worldbuildingpasta.blogspot.com/2021/11/an-apple-pie-from-scratch-part-vi.html)
- Worldbuilding Pasta's script also adjusts CO2 automatically so the climate settles at a chosen global mean temperature — [Idraluna Archives](https://idraluna-archives.bearblog.dev/lunar-climate-simulations/)
- `stormclim=True` adds storm-climatology fields (CAPE, maximum potential intensity, ventilation index) but "roughly doubles the computational cost" — [ExoPlaSim source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)

**Limitations**
- "ExoPlaSim lacks a dynamic ocean model." The ocean is a mixed-layer slab (default `mldepth` 50 m) with "no dynamic heat transport" in the benchmark setups. The authors say this "limits ExoPlaSim to explorations ... that are relatively insensitive to the details of ocean heat transport" — [Paradise et al.](https://arxiv.org/abs/2107.07685); [source](https://raw.githubusercontent.com/alphaparrot/ExoPlaSim/master/exoplasim/__init__.py)
- Other limitations: a simplified radiation scheme with a cooling bias at high pCO2, water-vapour absorption tuned to a solar spectrum, only one tracer (water vapour), limited cloud and precipitation treatment, and a simple land and ocean surface (for example no salinity or wind dependence of ocean albedo) — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- Spectral Gibbs ripples appear near sharp features (sharp topography, ice lines). Physics filters were added to reduce them — [Paradise et al.](https://arxiv.org/abs/2107.07685)
- Community reports (anecdotal):
  - Timestep 1 is not necessarily January, so check which output month is hottest.
  - ExoPlaSim may understate polar winter highs.
  - It "tends to model subtropical overseas highs as one mostly-contiguous ridge".
  - One user found temperatures "much too cold" with a custom topography and fell back to Earth topography.
  
  Sources: [Cartographers' Guild thread 1](https://www.cartographersguild.com/showthread.php?p=452004); [thread 2](https://cartographersguild.com/showthread.php?p=445553). The search summaries did not say clearly which claim is in which thread.
- Worldbuilding use is established. Besides the Worldbuilding Pasta tutorial (Nov 2021, with a long comment thread), the blog has a July 2026 post on public climate data — [WBP 2026 post](https://worldbuildingpasta.blogspot.com/2026/07/public-climate-data-explorations-pangea.html). Alternate-history and mapping forums use ExoPlaSim with koppenpasta for Köppen maps — [AlternateHistory.com thread](https://www.alternatehistory.com/forum/threads/planetocopia-map-thread.368765/page-46)

### Inferences
- **Resolution versus continent size.** A T21 grid cell is about 5.6° (about 625 km at the equator), so the 3,680 × 1,700 km continent covers only about 6 × 3 cells. At T42 (about 2.8°, about 310 km) it covers about 12 × 6 cells. rotclimate's 14 km grid has about 263 × 122 cells. T21 can at best check broad, sign-level behaviour. T42 is the minimum for comparing regional zone patterns, and even then coastal-scale features such as orographic rain shadows will be smeared.
- **Cost on 4 cores.**
  - T21: a 30–50-year run takes roughly 2–3 h at the laptop rate of 3.75 min per year. Two to four runs fit in one working day.
  - T42: if scaling were linear from 16 to 4 threads, a year would take about 1 h, so a 30-year run would take about 30 h. That is feasible only as a single background job, and it is uncertain because scaling is not perfectly linear.
  - rotclimate takes about 11 s per year, so it is roughly 20× faster than T21 and about 300× faster than T42 on the same hardware.
- **Whole-planet setup.** ExoPlaSim needs a global land mask, so the calibrator's unknowns for land and sea beyond the map edges must be fixed to that hypothesis's best-fit values for each run.
- **Ocean currents.** With a slab ocean, ExoPlaSim cannot test the effects of warm or cold boundary currents, and neither can rotclimate. That makes the GCM a clean check of the *atmospheric* part of the spin verdict, but not of ocean-driven coastal asymmetries.

### Gaps
- I found no published ExoPlaSim run with retrograde rotation, and no documentation of whether the Fortran core accepts negative `ROTSPD` or reverses the sun's diurnal path.
- I found no measured T42 runtime on exactly 4 cores; the figure above is extrapolated.
- I could not confirm whether the official docs offer a supported image-to-`.sra` helper. The source imports `exoplasim.randomcontinents`, but I did not check what it does.
- I found no systematic validation of ExoPlaSim Köppen maps against observed Earth Köppen maps.

## 2. Other intermediate-complexity options (Isca, SPEEDY, SpeedyWeather.jl, CLIMBER, moist EBMs, climlab)

### Takeaway
Besides ExoPlaSim, only **Isca** is a real 3-D option that accepts an arbitrary continent with its own topography and a configurable rotation rate. It needs a heavier Fortran/MPI/NetCDF build, and I found no published runtime for it. **SPEEDY/pySPEEDY** is fast but is normally driven by prescribed sea-surface temperatures (SST) and land fields, which would have to be invented for a fantasy world. **CLIMBER-X** is too coarse (5°) and its atmosphere is statistical rather than resolving the circulation. **climlab** and moist EBMs are zonal-mean only, so they cannot see spin direction at all.

### Cited Findings
**Isca (Vallis et al. 2018, GMD 11, 843–859)**
- Isca is a framework covering idealised to more realistic models, with "configurable continental outlines and topography". Continents "may be defined by changing albedo, heat capacity, and evaporative parameters and/or by using a simple bucket hydrology model". Oceanic Q-fluxes can be added "to reproduce specified sea surface temperatures" — [Vallis et al. 2018](https://gmd.copernicus.org/articles/11/843/2018/)
- Python tools build the land–sea mask on the model grid, using realistic ERA-Interim outlines, Brayshaw-style simplified continents, or rectangles, and write it to NetCDF. Topography "may be either idealized ... or be taken from cartography in a NetCDF file", and users can easily construct their own — [Vallis et al. 2018](https://gmd.copernicus.org/articles/11/843/2018/)
- Rotation rate, orbital parameters and the radiation scheme (gray, multi-band, RRTM, SOCRATES) are set through a Python dictionary without recompiling. Typical resolutions are T42 and T63, up to T213 — [Vallis et al. 2018](https://gmd.copernicus.org/articles/11/843/2018/)
- Land is the mixed-layer "ocean" with altered heat capacity, albedo, roughness and evaporation, optionally with a bucket model. This is simpler than PlaSim's soil and vegetation scheme — [Vallis et al. 2018](https://gmd.copernicus.org/articles/11/843/2018/)

**SPEEDY / SPEEDY.f90 / pySPEEDY**
- pySPEEDY is a Python interface (via F2PY) to Sam Hatfield's SPEEDY.f90, a Fortran rewrite of SPEEDY (Kucharski, Molteni, King). It defaults to T30 (about 3.75°) and was made thread-safe so several instances can run in parallel — [pySPEEDY docs](https://pyspeedy.readthedocs.io/); [SPEEDY.f90 GitHub](https://github.com/samhatfield/speedy.f90)
- Required boundary conditions: `orog` (orographic height) and `lsm` (land–sea fraction), plus *monthly climatological fields* of SST, land surface temperature, snow, soil moisture and others. The defaults are Earth's, plus SST anomalies for 1979–2013 — [pySPEEDY user guide](https://pyspeedy.readthedocs.io/en/latest/user_guide.html)

**SpeedyWeather.jl (Julia)**
- It describes itself as "technically ... a climate model with simple, yet interactive representations of ocean, land and sea-ice". It is "fast on CPU and GPU" and supports "various more or less realistic planets and what-if scenarios by easily modifying initial and boundary conditions" — [SpeedyWeather.jl README](https://github.com/SpeedyWeather/SpeedyWeather.jl)

**CLIMBER-X (Willeit et al. 2022, GMD 15, 5905)**
- Components: a 2.5-D semi-empirical statistical–dynamical atmosphere, a 3-D frictional–geostrophic ocean, sea ice and land, all on a 5°×5° grid. It runs about 10,000 simulated years per day on one 16-CPU node, compared with "several hundred model years per day" for coarse full ESMs — [Willeit et al. 2022](https://gmd.copernicus.org/articles/15/5905/2022/)

**climlab (Rose 2018)**
- Provides radiative and radiative-convective column models (RRTMG, Emanuel convection), 1-D advection–diffusion solvers, "Moist and dry Energy Balance Models – Seasonal and annual-mean models", and 2-D latitude–pressure models. Install with `conda install -c conda-forge climlab` — [climlab README](https://github.com/climlab/climlab)

**Moist EBMs**
- In the diffusive moist EBM (MEBM), poleward energy transport is diffusion of near-surface moist static energy (MSE). With a Hadley-cell term added, it reproduces the zonal-mean evaporation-minus-precipitation (E−P) pattern and its change — [Siler, Roe & Armour 2018](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/SilerEtal_HydroCycle_JCIim18.pdf)
- A diffusive MEBM "accurately predicts zonal-mean warming and AHT [atmospheric heat transport] changes" in comprehensive GCMs — [Armour et al. 2019](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/ArmourEtAl_AHT_JClim19.pdf)
- Frierson, Held & Zurita-Gotor (2007, JAS 64, 1680) compare a constant-diffusivity EBM with a gray-radiation aquaplanet GCM. The EBM's assumptions "are not accurately satisfied by the GCM"; a more complex EBM with expressions for diffusivity and the latitude of maximum eddy activity fits better — [Frierson research summary](https://www.atmos.washington.edu/~dargan/summaries/fhz07.html)
- Hwang & Frierson (2010, GRL 37) apply this energetic framework to rising poleward energy transport under warming. A 2011 correction exists — [DOI 10.1029/2010GL045440](https://doi.org/10.1029/2010GL045440); [EarthRef record](https://earthref.org/ERR/131677)

### Inferences
- **Ranking for "run once or a few times in a cloud container":**
  1. **ExoPlaSim**: pip install, real land model, 4-core friendly, about 2–3 h per T21 run.
  2. **Isca**: closest research-grade alternative with explicit idealised-continent tools and Q-flux. The installation is heavier (FMS, MPI, NetCDF-Fortran) and its runtime is unknown.
  3. **SpeedyWeather.jl**: attractive if its custom-planet support checks out, but Julia adds a toolchain.
  4. **pySPEEDY**: only usable if you are prepared to make up SST and land climatologies, which partly decides the answer in advance.
  5. **CLIMBER-X**: not useful here, since 5° is coarser than the continent's short side and its atmosphere is parameterised much like rotclimate's.
  6. **climlab / MEBMs**: good for checking rotclimate's *zonal-mean* energy and moisture budget, but they cannot inform the spin verdict.
- A zonally symmetric model gives exactly the same result for either spin direction (up to a mirror image), so no zonal-mean EBM can test the spin verdict.

### Gaps
- No published Isca wall-clock time per model year at T42 on a given core count turned up. A search found only an Isca T42 setup with no timings.
- I could not confirm whether Isca accepts negative `omega`.
- I could not open SpeedyWeather.jl's documentation pages on orography, land–sea mask and rotation; the URLs I tried returned the site's 404 page. Its exact API for custom planets is unverified.
- I could not verify whether SPEEDY.f90 or pySPEEDY has a working slab-ocean mode that would remove the need for prescribed SST.
- I found no runtime figures for SPEEDY or SpeedyWeather on 4 cores in sources I could fetch.

## 3. Using a few GCM runs to validate or calibrate a fast model; a GCM test of spin direction

### Takeaway
There is a direct precedent. Mikolajewicz et al. (2018) ran a coupled ESM with Earth's spin reversed and compared Köppen zones. As Köppen's idealised continent predicts, the climate zones were "to a first approximation" mirror images. The large exceptions (deserts moving to the Americas, deep-water formation moving to the North Pacific, the ITCZ shifting) involved ocean and monsoon dynamics. The usual ways to tie simple models to GCMs are calibrating EBM diffusivities to GCM transports and pattern scaling, which works well for temperature and less well for precipitation.

### Cited Findings
- **"The climate of a retrograde rotating Earth" (Mikolajewicz et al. 2018, Earth Syst. Dynam. 9, 1191–1215).**
  - Model: MPI-ESM in coarse resolution, with the ECHAM6 atmosphere at T31 and 31 levels (96×48 grid) and the MPIOM ocean (120×101×40 grid) with dynamic sea ice and dynamic vegetation (JSBACH).
  - In RETRO, "the sign of the Coriolis parameter was changed both in the atmospheric and oceanic model components" and "the direction of the Sun's diurnal march was also reversed".
  - Each run was "integrated for 6990 model years"; most physical variables were well equilibrated after about 2000 years. The last 1000 years were analysed.
  
  Source: [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/)
- Reversing the spin changes global and zonal-mean energy budgets only slightly. Its main effects are on continental climates, precipitation patterns and deep-water formation. The Sahara greens while large parts of the Americas become desert. The ITCZ shifts south and the Pacific double ITCZ becomes single. Deep-water formation moves from the North Atlantic to the North Pacific. Northern Hemisphere storm-track activity moves from the oceans toward land — [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/); [MPI-M press release](https://mpimet.mpg.de/en/communication/news/new-study-what-would-happen-to-the-climate-system-if-earth-turned-the-other-way-around)
- **Mirror symmetry and Köppen.**
  - Köppen's idealised continent implies "a retrograde rotating Earth would experience mirror symmetry about the north–south axis in its climate zones".
  - The control run reproduces the east–west asymmetries, for example the shift from deserts in the subtropical continental southwest to moist temperate climates in the southeast. In RETRO, "to a first approximation ... these features do appear with mirror symmetry".
  - However, "some differences ... would not have been predicted from just mirroring the idealized continent". The largest is the shift of deserts from Eurasia–Africa to the Americas, with southern Brazil and Argentina becoming Earth's biggest deserts.
  - Permanent desert area falls by about 25% (from 42 to 31 × 10⁶ km²); in the Northern Hemisphere, desert shrinks by nearly 40%.
  - Western boundary currents become eastern boundary currents.
  
  Source: [Mikolajewicz et al. 2018](https://esd.copernicus.org/articles/9/1191/2018/)
- **Simple models checked against GCMs.**
  - A diffusive MEBM with a Hadley-cell term "accounts for much of the model spread in the zonal-mean response of E and P to climate change" across GCMs — [Siler et al. 2018](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/SilerEtal_HydroCycle_JCIim18.pdf)
  - A diffusive MEBM accurately predicts the zonal-mean warming and heat-transport changes simulated by GCMs — [Armour et al. 2019](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/ArmourEtAl_AHT_JClim19.pdf)
  - An aquaplanet GCM was used to test an EBM's diffusive assumptions, which turned out to be only approximately met — [Frierson et al. 2007 summary](https://www.atmos.washington.edu/~dargan/summaries/fhz07.html)
  - Bischoff & Schneider derived energetic relations for ITCZ position and confirmed them quantitatively with idealised aquaplanet GCM simulations — [Bischoff & Schneider 2016](https://authors.library.caltech.edu/records/tdj6h-mm568)
- **Pattern scaling** (an emulator built from GCM output). Tebaldi & Arblaster (2014, Climatic Change 122, 459–471) find its validity for the forced signal "well established", with CMIP5 patterns similar to CMIP3 — [IDEAS/RePEc record](https://ideas.repec.org/a/spr/climat/v122y2014i3p459-471.html). It performs worse where regional forcing differs strongly (for example aerosols) and for bounded variables such as precipitation — [HELIX D2.4](https://helixclimate.eu/wp-content/uploads/2018/04/HELIX-603864-D2.4-Effectiveness-of-pattern-scaling.pdf)
- **Large ExoPlaSim ensembles are feasible only on HPC.** For example, 40 simultaneous 16-thread runs of 150 years each give about 4000 simulations per week, enough for a 50×80 parameter grid — [Paradise et al.](https://arxiv.org/abs/2107.07685)

### Inferences
- **Mirror equivalence.** If geography is the only east–west asymmetry, a planet spinning retrograde with map M is the mirror image of a planet spinning prograde with the east–west mirrored map. The only difference is that the orbit now runs in the opposite sense relative to the spin, which shifts the count of solar days per year by about 2 (about 0.5% in day length) and should be negligible.
  - The practical test needs no retrograde support in the GCM: run the original map and its east–west mirror, both with normal prograde spin, then mirror the second run's output back. Mikolajewicz et al. instead flipped Coriolis and the sun's diurnal path, which is equivalent.
- **Fair comparison design.** Each spin hypothesis has its own CMA-ES best-fit parameters (latitude, tilt, terrain, off-map land). A fair test is two GCM runs, one per hypothesis at its own best fit, each scored against the painted zones with the same metric. Two "cross" runs (each parameter set under the other spin) would separate the effect of spin from the effect of the refitted parameters. At T21 that is about 4 runs × 2–3 h on 4 cores.
- **What to compare.** Compare in a way that is robust to coarse resolution: which side of the continent is wetter in each latitude band, where the subtropical dry belt sits along the west versus the east coast, and the seasonal timing of rain (summer-wet monsoon versus winter-wet Mediterranean). Pixel-level Köppen agreement is the wrong test.
- **Caution.** Mikolajewicz's non-mirror changes were linked to coupled ocean dynamics (deep-water formation, boundary currents). A slab-ocean ExoPlaSim test would not capture these, and neither does rotclimate.
- **Using GCM output in the calibrator.** Rather than adding a prior, one or two GCM runs could be used to calibrate or check rotclimate's parameterised wind belts, storm-track position and moisture-transport coefficients, similar to how EBM diffusivities are tuned against GCM transports.

### Gaps
- I found no published study that used a handful of GCM runs specifically to adjudicate rotation direction for a fictional or paleo continent, apart from Mikolajewicz et al. (Earth's real geography) and anecdotal worldbuilding runs.
- I found no source on formal Bayesian calibration, history matching, or using GCM fields as priors for a simple regional climate model. That literature (for example history matching or Gaussian-process emulation) was not researched here.

## 4. Strengths and weaknesses of simple moist EBMs for regional precipitation

### Takeaway
Diffusive moist EBMs are good at *zonal-mean* energetics. With a Hadley-cell term they capture the subtropical dry belt and moist mid-latitudes, and energetic frameworks tie the ITCZ position to cross-equatorial energy flux. By construction they miss the zonal asymmetries that set regional patterns: monsoons, west/east-coast contrasts, and differences between ocean basins. The plain diffusive form even gets latent heat transport backwards inside the Hadley cell.

### Cited Findings
- The standard MEBM "does not correctly simulate latent heat transport, which is upgradient within the Hadley cell". Adding a Hadley-cell weighting function lets latent heat travel upgradient while total energy transport stays downgradient, giving "a more realistic representation of the hydrologic cycle". The remaining limitations are that it ignores transport by the Ferrel and polar cells and fixes the eddy/Hadley split — [Siler et al. 2018](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/SilerEtal_HydroCycle_JCIim18.pdf)
- The modified MEBM reproduces zonal-mean E−P and its changes, including the poleward expansion of the subtropical dry zone and extratropical shifts seen in GCMs — [Siler et al. 2018](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/SilerEtal_HydroCycle_JCIim18.pdf)
- EBMs are used mainly for *zonal-mean* climate, because "on long time scales, the zonal-mean net heating" must be balanced by heat-transport divergence — [Siler et al. 2018](https://earthweb.ess.washington.edu/roe/GerardWeb/Publications_files/SilerEtal_HydroCycle_JCIim18.pdf). climlab's EBMs are likewise seasonal or annual-mean latitude models — [climlab README](https://github.com/climlab/climlab)
- ITCZ energetics: ITCZ position is linear in cross-equatorial energy flux when net energy input at the equator is large, and follows a cube-root law when it is small. A double ITCZ appears when equatorial net energy input or its curvature goes negative — [Bischoff & Schneider 2016](https://authors.library.caltech.edu/records/tdj6h-mm568)
- **Monsoons:** the continental monsoons "do not follow the energy and momentum constraints that govern the tropical rain belt". Their variability departs significantly from the ITCZ through mechanisms that are poorly understood and poorly simulated — [Biasutti et al. 2018, Nature Geoscience 11, 392–400](https://boos.berkeley.edu/publication/biasuttietal2018); [accepted manuscript](https://par.nsf.gov/servlets/purl/10078712)
- **Constant diffusivity:** the assumptions of a constant-diffusivity EBM are not accurately satisfied in a moist GCM. Diffusivity and the latitude of eddy activity change with climate, and the jet and eddies shift poleward as moisture increases — [Frierson et al. 2007 summary](https://www.atmos.washington.edu/~dargan/summaries/fhz07.html)
- **East–west asymmetry is a circulation effect:**
  - In mid-latitudes, west coasts are milder and more maritime than east coasts.
  - In the subtropics, west coasts are drier and Mediterranean (winter rain), while east coasts are more seasonal and monsoonal (summer rain).
  - These asymmetries come from westerlies versus easterlies and from western versus eastern boundary currents, and the zonal placement of monsoons and deserts is an active research question (Rodwell & Hoskins 1996).
  
  Source: [Mikolajewicz et al. 2018, introduction](https://esd.copernicus.org/articles/9/1191/2018/)

### Inferences
- **What the GCM check adds.** rotclimate is not a zonal-mean EBM; it is 2-D with imposed wind belts and storm tracks. Its east–west asymmetry therefore comes from those parameterised winds, not from resolved dynamics. A moist EBM check can confirm its zonal-mean energy and moisture balance. Only a GCM can test whether those imposed winds produce the right west/east-coast contrast, monsoon timing and subtropical-high placement, which is exactly what decides the spin verdict.
- **Known weak spots that could bias the spin verdict:**
  - monsoon-season rain on the eastern or equatorward side of the continent;
  - the eastern-boundary dry, stable subtropical west coast, which is an ocean and stationary-wave effect that a slab ocean or parameterised winds may get wrong;
  - storm tracks drifting over land.
  
  Mikolajewicz shows that the last of these changes with spin direction.
- **ExoPlaSim has its own weakness here.** It tends to blur subtropical highs into one ridge (an anecdotal community report). It may therefore *underestimate* exactly the zonal asymmetries that distinguish the two spin directions, so a GCM "no difference" result should be read cautiously.

### Gaps
- I did not find a study that quantitatively scores a 2-D moist EBM or advection–diffusion model against a GCM for *regional* precipitation (west versus east coasts, monsoons). Siler et al. mention "regional-scale variations", but only within a zonal-mean framework; I did not read those passages in detail.
- I did not retrieve the Bischoff & Schneider 2014 J. Climate paper text, or Adam et al.'s Part II on zonally varying ITCZ shifts.
