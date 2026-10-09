"""Model parameters.

Every free choice the climate model makes lives here, so that the calibration
loop can search over them and every rendered map can be reproduced from a
saved JSON file.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SOURCE = DATA / "source"
OUTPUT = REPO / "output"


@dataclass
class Params:
    # ---------------------------------------------------------------- planet
    lat_center: float = 34.0          # latitude of the map centre [deg N]
    tilt: float = 23.44               # axial tilt [deg]
    retrograde: bool = False          # spin opposite to Earth (flips Coriolis)
    eccentricity: float = 0.0167
    perihelion_after_solstice: float = 13.0  # days after the winter solstice
    year_days: int = 365
    # day-of-year (0-based, day 0 = Titian Marigold 1) of the winter solstice.
    # Day 22 puts the solstice in "early winter", the equinox in "middle
    # spring", the summer solstice in "early summer" etc. - see calendar.py
    winter_solstice_day: float = 22.0

    # ---------------------------------------------------------------- map
    map_width_mi: float = 2200.5
    map_height_mi: float = 1018.5
    # unknown terrain tiers -> top elevation of each tier [m]
    # (lowland green, hill cream, upland orange, mountain red)
    tier_tops: tuple = (350.0, 900.0, 1800.0, 3300.0)
    lapse_rate: float = 6.0           # K / km (environmental)

    # What lies beyond each edge of the map is unknown.
    # beyond_style 'procedural' (default): edge features continue and fade
    # over beyond_continuity_km, then seeded fractal land/sea with a land
    # *fraction* per side (0 = open ocean, 1 = continent) and low hills.
    beyond_style: str = "procedural"
    beyond_north_land: float = 0.6
    beyond_south_land: float = 0.6
    beyond_west_land: float = 0.3
    beyond_east_land: float = 0.3
    beyond_southeast_land: float = -1.0   # v6: east half of the south edge (-1 = same as south)
    beyond_northeast_land: float = -1.0   # v6: east half of the north edge (-1 = same as north)
    beyond_continuity_km: float = 300.0
    beyond_relief_m: float = 400.0
    beyond_seed: int = 1
    # legacy 'blocks' style (rounds 0-2): per side 'ocean' | 'land' |
    # 'extend', with *_gap_km of open sea before the unknown coast.
    beyond_north: str = "extend"
    beyond_south: str = "extend"
    beyond_west: str = "ocean"
    beyond_east: str = "ocean"
    beyond_north_gap_km: float = 0.0
    beyond_south_gap_km: float = 0.0
    beyond_west_gap_km: float = 0.0
    beyond_east_gap_km: float = 0.0
    pad_km: float = 1100.0

    # ---------------------------------------------------------------- energy
    land_tau_days: float = 3.0        # air-mass adjustment time over land
    ocean_tau_days: float = 1.5       # ... over sea
    heat_diffusion: float = 4.0e4     # m^2/s, horizontal mixing of air
    current_strength: float = 4.0     # K, boundary current SST anomaly
    sst_offset: float = 0.0           # K, global SST tweak
    land_offset: float = 0.0          # K, global land-column tweak
    inland_sea_warming: float = 2.0   # enclosed seas take 0.1*this of the land's swing
    lake_coupling: float = 0.0        # v4: lakes/small seas follow land temp (0 = off)
    land_amplitude: float = 1.0       # v4: scale of the continental seasonal swing
    storm_asym: float = 0.0           # v5: storm track stronger on the warm-current side
    storm_reach: float = 0.0          # v5: ... and this many degrees further equatorward
    instability: float = 0.0          # v6: extra rain efficiency in hot, moist air

    # ---------------------------------------------------------------- winds
    hadley_edge: float = 30.0         # annual-mean subtropical high latitude
    hadley_shift: float = 5.0         # seasonal poleward shift in summer
    itcz_mean: float = 5.0
    itcz_shift: float = 10.0
    trade_speed: float = 6.0          # m/s
    westerly_speed: float = 7.0       # m/s
    polar_speed: float = 3.0
    monsoon_strength: float = 1.0     # thermal-low wind scaling
    monsoon_scale_km: float = 500.0   # smoothing of the thermal pressure field
    cross_isobar_deg: float = 35.0    # friction turning toward low pressure
    terrain_drag: float = 0.5         # wind slow-down over high ground

    # ---------------------------------------------------------------- water
    ocean_rh: float = 0.80
    evap_tau_days: float = 2.0
    land_recycling: float = 0.35      # fraction of land P re-evaporated
    precip_tau_days: float = 6.0      # background rain-out time scale
    rh_threshold: float = 0.45
    storm_track: float = 1.6          # extra-tropical cyclone rain factor
    storm_width: float = 9.0          # deg
    convective: float = 2.0           # convergence-driven rain factor
    orographic: float = 2.5           # upslope rain factor
    subsidence: float = 0.75          # subtropical-high suppression (0..1)
    subsidence_asym: float = 0.0      # east/west-of-basin asymmetry of the highs
    moisture_diffusion: float = 6.0e4  # m^2/s
    eddy_rate: float = 0.0            # 1/day, storm-eddy exchange (0 = off)
    eddy_scale_km: float = 450.0

    # ---------------------------------------------------------------- numerics
    downsample: int = 8               # source pixels per model cell
    steps_per_year: int = 73          # 73 x 5-day weeks
    picard_iters: int = 3

    def to_json(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def from_json(cls, path: Path | str) -> "Params":
        d = json.loads(Path(path).read_text())
        known = {f.name for f in fields(cls)}
        d = {k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items() if k in known}
        d.setdefault("beyond_style", "blocks")   # files from before procedural surroundings
        return cls(**d)

    def replace(self, **kw) -> "Params":
        d = asdict(self)
        d.update(kw)
        return Params(**d)
