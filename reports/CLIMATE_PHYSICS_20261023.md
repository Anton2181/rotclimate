# Climate physics and calibration — 23 October 2026

## Milestone 1: conservative storm-water exchange

The production storm approximation applies a spatially varying rate after
Gaussian mixing: `r_i * (G(W)_i - W_i)`. Even on a closed domain this can
create or remove water. The new opt-in `eddy_moisture_scheme="conservative"`
uses symmetric pair conductances instead. For column mass `c`, specific
humidity `q=W/c`, and reflecting Gaussian `G`, the transfer from j to i is

`G_ij * (r_i*c_i + r_j*c_j)/2 * (q_j - q_i)`.

Each transfer has an equal and opposite partner. Rates and incoming water
stay nonnegative, and uniform specific humidity is an equilibrium. The loss
coefficient enters the implicit solver; incoming water is updated by the
existing checked nonlinear iteration. Reflecting Gaussian kernels agree
with SciPy, including the FFT implementation for wide kernels. The fixed
outer ring remains a reservoir: its delivery to the solved interior is
recorded explicitly. This conserves **storm exchange**, not the entire
atmosphere: the existing mean-wind concentration advection, prescribed
circulation and subsidence closure remain approximations.

The old crest-clipping option removes mixed vapour without adding that loss
to rainfall. It is incompatible with this scheme and rejected explicitly;
`eddy_rainout=0` is required. The default remains `legacy`, preserving saved
fits. No atlas climate or physical parameter file changes in this milestone.

### Paired Earth pilot

Four predeclared profiles were run on six cached WorldClim development
regions at 56 km, 25 seasonal steps, with the saved strict linear,
temperature and nonlinear moisture criteria. The baseline uses the current
Earth-fit physics. All **24 cases** pass every observed numerical check.
These regions have been used previously; they are not independent validation.

| Profile | Mean climate distance, lower better |
|---|---:|
| Current physics | 2.211846 |
| No crest clipping | 2.211846 |
| Conservative exchange, equal column mass | 2.284636 |
| Conservative exchange, column mass scale 3 km | 2.612372 |

Earth physics already has crest clipping disabled, so its control exactly
reproduces the baseline. Conservative exchange improves Iberia from 2.090786
to 1.941968 but worsens Central Asia from 1.876983 to 2.198520 and East China
from 2.465534 to 2.642198. It therefore needs calibration and **is not
promoted** as a better climate fit. The 3 km mass profile is also retained
as a negative result.

Across the conservative cases the maximum storm-exchange cancellation error
is below **1.72e-16** of gross exchanged water. The baseline maximum is
0.026963. These full padded-grid operator measurements include the Gaussian
edge rule; they are not estimates of a planet-wide rainfall bias.

The reproducible protocol, per-region temperatures/rainfall/Köppen metrics,
all parameters, source hashes, numerical certificates and boundary exchanges
are in `output/climate_physics_20261023/earth_pilot/`. Run with:

```sh
.venv/bin/python -I scripts/screen_climate_physics.py \
  --profiles calibration/climate_physics_20261023/storm_profiles.json \
  --regions california iberia central_asia east_china western_europe chile \
  --out output/climate_physics_20261023/earth_pilot --workers 2
```

Thirteen new focused tests cover Gaussian symmetry, pairwise conservation,
terrain mass, humidity-variance dissipation, zero rates, invalid mass,
unaccounted crest clipping, and a coupled climate solve whose recorded
moisture residual matches the new exchange. Existing core, Earth, moisture,
transport, seasonal-column and solver-certificate tests also pass.
