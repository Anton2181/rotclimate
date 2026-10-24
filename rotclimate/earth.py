"""Earth mode: run the production model on real geography and score it
against observed climate.

The fantasy calibration infers unknowns (latitude, tilt, spin, surroundings)
together with physics constants. On Earth every geographic unknown is known,
so the same physics can be tested directly: build the model grid from
WorldClim 2.1 terrain for a region, run it with Earth's tilt, spin and
calendar, and compare its monthly temperature and rain with WorldClim's
1970-2000 normals on the same cells.

Grid: azimuthal equidistant projection about the region centre (distances
exact, local north within a few degrees of grid-up near the centre), square
cells of `cell_km`, the scored rectangle plus `pad_km` of real surroundings on
every side. Each cell averages the WorldClim 5-arc-minute pixels inside it,
weighted by pixel area; a cell is land where at least half of it is.

The scored region's "painted zones" are what the zone rules say for the
observed climate (with the Koppen label gate), so every fantasy score
(coverage, precision, F1, strict agreement) has an Earth counterpart.

    python -I scripts/earth_benchmark.py --region california --params <file>
"""
from __future__ import annotations

import io
import json
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import DATA, Params
from .geography import Grid
from .koppen import CODES, classify, climate_indices, summer_months

R_EARTH_KM = 6371.0
WORLDCLIM = DATA / "cache" / "worldclim"
CACHE = DATA / "cache" / "earth"
WINTER = np.array([0, 1, 2, 9, 10, 11])          # Oct-Mar, as in the V10 Earth tests

# scored rectangles (km, in the local projection) chosen to match the V10
# Earth domains, plus the regions standing in for the other painted zones
REGIONS = {
    "california": dict(lat0=37.0, lon0=-118.8, width_km=900, height_km=1270,
                       note="Mediterranean coast, Central Valley, Sierra Nevada, Mojave/Sonoran desert"),
    "iberia": dict(lat0=37.1, lon0=-3.45, width_km=2400, height_km=1690,
                   note="Iberia, the western Mediterranean and north-west Africa"),
    # analogues of the other painted zones, at the map's latitudes
    "southeast_us": dict(lat0=31.0, lon0=-89.0, width_km=2000, height_km=1300,
                         note="Gulf coast swamps, Florida, humid subtropical south, Appalachians, Texas plains"),
    "levant": dict(lat0=36.0, lon0=36.5, width_km=1900, height_km=1300,
                   note="Aegean/Levant Mediterranean coasts, Anatolian steppe, Syrian desert, Zagros"),
    "central_asia": dict(lat0=42.0, lon0=66.0, width_km=2000, height_km=1300,
                         note="Turan steppe and deserts, Tian Shan / Pamir foothills"),
    "east_china": dict(lat0=29.0, lon0=113.0, width_km=1800, height_km=1300,
                       note="monsoon humid subtropics: Yangtze, south China hills, Sichuan basin"),
    # southern-hemisphere Mediterranean climates (held out; run mirrored, see region_case)
    "chile": dict(lat0=-34.0, lon0=-71.0, width_km=700, height_km=1500,
                  note="central Chile: Mediterranean coast, Andes, Atacama edge"),
    "cape": dict(lat0=-33.4, lon0=20.6, width_km=780, height_km=560,
                 note="Western Cape Mediterranean, Karoo, southern coast"),
    "sw_australia": dict(lat0=-32.0, lon0=118.5, width_km=1200, height_km=1000,
                         note="south-west Australia: Mediterranean coast to the interior deserts"),
    # more held-out regions (19 October): the humid subtropics on three more
    # coasts and a hot desert, the climates the training set has least of
    "east_australia": dict(lat0=-29.0, lon0=151.0, width_km=1300, height_km=1500,
                           note="humid subtropical east coast, Great Dividing Range, inland plains"),
    "south_brazil": dict(lat0=-31.0, lon0=-55.5, width_km=1600, height_km=1300,
                         note="Pampas and south Brazil: humid subtropical, no dry season"),
    "japan": dict(lat0=35.0, lon0=134.0, width_km=1500, height_km=1200,
                  note="maritime humid subtropics: southern Japan and the Korea Strait"),
    "mexico": dict(lat0=27.0, lon0=-104.5, width_km=1500, height_km=1300,
                   note="northern Mexico: hot deserts and steppes, the Sierra Madre"),
    # mid-latitude regions added after the physics rounds e11-e25, as a fresh
    # test of physics tuned on the 13 subtropical ones (oceanic and continental)
    "pacific_nw": dict(lat0=46.0, lon0=-121.5, width_km=1100, height_km=1100,
                       note="Pacific Northwest: oceanic and dry-summer coast, the Cascades' rain shadow"),
    "western_europe": dict(lat0=49.0, lon0=1.5, width_km=1600, height_km=1200,
                           note="France, the Low Countries and southern England: oceanic"),
    "eastern_europe": dict(lat0=50.0, lon0=28.0, width_km=1600, height_km=1200,
                           note="Ukraine, Poland and Belarus: cold continental"),
    "us_midwest": dict(lat0=41.0, lon0=-91.0, width_km=1800, height_km=1200,
                       note="the Corn Belt: hot-summer continental"),
    "manchuria": dict(lat0=44.0, lon0=126.0, width_km=1400, height_km=1200,
                      note="north-east China and the Russian Far East: the Siberian High's winter monsoon"),
    "new_zealand": dict(lat0=-41.5, lon0=173.0, width_km=1000, height_km=1300,
                        note="New Zealand: oceanic, the Southern Alps' rain shadow"),
}


# well-known places for climographs (lat, lon); the model cell containing each
STATIONS = {
    "california": {"San Francisco": (37.77, -122.42), "Sacramento": (38.58, -121.49), "Fresno": (36.74, -119.79),
                   "Los Angeles": (34.05, -118.24), "San Diego": (32.72, -117.16), "Reno": (39.53, -119.81),
                   "Las Vegas": (36.17, -115.14)},
    "iberia": {"Lisbon": (38.72, -9.14), "Porto": (41.15, -8.61), "Madrid": (40.42, -3.70), "Seville": (37.39, -5.98),
               "Valencia": (39.47, -0.38), "Barcelona": (41.39, 2.17), "Algiers": (36.75, 3.06),
               "Marrakech": (31.63, -7.99)},
    "southeast_us": {"Houston": (29.76, -95.37), "New Orleans": (29.95, -90.07), "Memphis": (35.15, -90.05),
                     "Atlanta": (33.75, -84.39), "Tampa": (27.95, -82.46), "Miami": (25.76, -80.19)},
    "levant": {"Athens": (37.98, 23.73), "Istanbul": (41.01, 28.98), "Ankara": (39.93, 32.86), "Beirut": (33.89, 35.50),
               "Damascus": (33.51, 36.28), "Jerusalem": (31.77, 35.21)},
    "central_asia": {"Ashgabat": (37.95, 58.38), "Bukhara": (39.77, 64.42), "Samarkand": (39.65, 66.96),
                     "Tashkent": (41.30, 69.24), "Dushanbe": (38.56, 68.77), "Aralsk": (46.80, 61.67)},
    "east_china": {"Shanghai": (31.23, 121.47), "Nanjing": (32.06, 118.80), "Wuhan": (30.59, 114.31),
                   "Changsha": (28.23, 112.94), "Chongqing": (29.56, 106.55), "Guangzhou": (23.13, 113.26)},
    "chile": {"La Serena": (-29.90, -71.25), "Valparaiso": (-33.05, -71.62), "Santiago": (-33.45, -70.67),
              "Concepcion": (-36.83, -73.05)},
    "cape": {"Cape Town": (-33.92, 18.42), "Worcester": (-33.65, 19.45), "George": (-33.96, 22.46),
             "Beaufort West": (-32.35, 22.58)},
    "sw_australia": {"Geraldton": (-28.78, 114.61), "Perth": (-31.95, 115.86), "Albany": (-35.02, 117.88),
                     "Kalgoorlie": (-30.75, 121.47)},
    "east_australia": {"Brisbane": (-27.47, 153.03), "Toowoomba": (-27.56, 151.95), "Moree": (-29.47, 149.85),
                       "Coffs Harbour": (-30.30, 153.11), "Dubbo": (-32.25, 148.60), "Sydney": (-33.87, 151.21)},
    "south_brazil": {"Florianopolis": (-27.60, -48.55), "Santa Maria": (-29.69, -53.81),
                     "Porto Alegre": (-30.03, -51.23), "Rosario": (-32.95, -60.65), "Montevideo": (-34.90, -56.16),
                     "Buenos Aires": (-34.60, -58.38)},
    "japan": {"Busan": (35.18, 129.08), "Fukuoka": (33.59, 130.40), "Kagoshima": (31.60, 130.56),
              "Osaka": (34.69, 135.50), "Nagoya": (35.18, 136.91), "Tokyo": (35.68, 139.69)},
    "mexico": {"Hermosillo": (29.07, -110.96), "Chihuahua": (28.63, -106.07), "El Paso": (31.76, -106.49),
               "Torreon": (25.54, -103.41), "Durango": (24.02, -104.67), "Monterrey": (25.69, -100.32)},
    "pacific_nw": {"Seattle": (47.61, -122.33), "Portland": (45.52, -122.68), "Vancouver": (49.28, -123.12),
                   "Eugene": (44.05, -123.09), "Yakima": (46.60, -120.51), "Spokane": (47.66, -117.43)},
    "western_europe": {"London": (51.51, -0.13), "Paris": (48.86, 2.35), "Brest": (48.39, -4.49),
                       "Bordeaux": (44.84, -0.58), "Brussels": (50.85, 4.35), "Strasbourg": (48.58, 7.75)},
    "eastern_europe": {"Warsaw": (52.23, 21.01), "Lviv": (49.84, 24.03), "Kyiv": (50.45, 30.52),
                       "Minsk": (53.90, 27.57), "Odesa": (46.48, 30.73), "Kharkiv": (49.99, 36.23)},
    "us_midwest": {"Chicago": (41.88, -87.63), "Minneapolis": (44.98, -93.27), "Des Moines": (41.59, -93.62),
                   "Kansas City": (39.10, -94.58), "St. Louis": (38.63, -90.20), "Indianapolis": (39.77, -86.16)},
    "manchuria": {"Harbin": (45.80, 126.53), "Qiqihar": (47.35, 123.92), "Changchun": (43.82, 125.32),
                  "Shenyang": (41.81, 123.43), "Dalian": (38.91, 121.60), "Vladivostok": (43.12, 131.89)},
    "new_zealand": {"Auckland": (-36.85, 174.76), "Nelson": (-41.27, 173.28), "Wellington": (-41.29, 174.78),
                    "Hokitika": (-42.72, 170.97), "Christchurch": (-43.53, 172.64), "Dunedin": (-45.87, 170.50)},
}


@dataclass
class EarthCase:
    name: str
    grid: Grid
    lon: np.ndarray            # deg, per cell
    obs_T: np.ndarray          # [12, ny, nx] observed monthly mean temperature (C), NaN over sea
    obs_P: np.ndarray          # [12, ny, nx] observed monthly rain (mm), NaN over sea
    coast_km: np.ndarray       # distance from the sea (km)


# ---------------------------------------------------------------- projection
def forward(lat, lon, lat0, lon0):
    """(lat, lon) deg -> (x, y) km, azimuthal equidistant about (lat0, lon0)."""
    p, l = np.radians(lat), np.radians(lon - lon0)
    p0 = np.radians(lat0)
    cosc = np.clip(np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(l), -1, 1)
    c = np.arccos(cosc)
    k = np.where(c > 1e-12, c / np.maximum(np.sin(c), 1e-12), 1.0)
    x = R_EARTH_KM * k * np.cos(p) * np.sin(l)
    y = R_EARTH_KM * k * (np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(l))
    return x, y


def inverse(x, y, lat0, lon0):
    """(x, y) km -> (lat, lon) deg."""
    p0 = np.radians(lat0)
    rho = np.hypot(x, y)
    c = rho / R_EARTH_KM
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.clip(np.cos(c) * np.sin(p0) + np.where(rho > 0, y * np.sin(c) * np.cos(p0) / rho, 0),
                                -1, 1))
        lon = lon0 + np.degrees(np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c)))
    return np.degrees(lat), lon


# ---------------------------------------------------------------- WorldClim
def _wc(var, month=None):
    member = f"wc2.1_5m_{var}.tif" if month is None else f"wc2.1_5m_{var}_{month:02d}.tif"
    from PIL import Image

    im = Image.open(io.BytesIO(zipfile.ZipFile(WORLDCLIM / f"wc2.1_5m_{var}.zip").read(member)))
    a = np.array(im, dtype=np.float32)
    nd = im.tag_v2.get(42113)
    if nd is not None:
        a[a == np.float32(float(str(nd).strip("\x00 ")))] = np.nan
    a[a < -1e30] = np.nan
    return a


def region_case(name: str, cell_km: float = 28.0, pad_km: float = 1100.0) -> EarthCase:
    spec = REGIONS[name]
    lat0, lon0 = spec["lat0"], spec["lon0"]
    half_w, half_h = spec["width_km"] / 2 + pad_km, spec["height_km"] / 2 + pad_km
    nx = int(np.ceil(2 * half_w / cell_km))
    ny = int(np.ceil(2 * half_h / cell_km))
    key = f"{name}_{cell_km:g}km_{pad_km:g}pad.npz"
    CACHE.mkdir(parents=True, exist_ok=True)
    if (CACHE / key).exists():
        z = np.load(CACHE / key)
        fields = {k: z[k] for k in z.files}
    else:
        fields = _aggregate(lat0, lon0, nx, ny, cell_km, half_w, half_h)
        np.savez_compressed(CACHE / key, **fields)
    xs = -half_w + (np.arange(nx) + 0.5) * cell_km
    ys = half_h - (np.arange(ny) + 0.5) * cell_km
    X, Y = np.meshgrid(xs, ys)
    lat, lon = inverse(X, Y, lat0, lon0)
    if lat0 < 0:
        # The model is written for a northern-hemisphere map. The mirror image
        # (north <-> south) of a southern region is the same physics in the
        # north: the Coriolis turning and the reflection both flip handedness,
        # winds still blow west to east in the westerlies. Seasons move by half
        # a year: observed July is the mirrored January.
        fields = {k: (np.roll(v[:, ::-1], 6, axis=0) if v.ndim == 3 else v[::-1]) for k, v in fields.items()}
        lat, lon, Y = -lat[::-1], lon[::-1], -Y[::-1]
    land = fields["land_frac"] >= 0.5
    inmap = (np.abs(X) <= spec["width_km"] / 2) & (np.abs(Y) <= spec["height_km"] / 2)
    pad = int(round(pad_km / cell_km))
    from scipy import ndimage as ndi

    coast = ndi.distance_transform_edt(land) * cell_km
    obs_T = np.where(land[None], fields["T"], np.nan)
    obs_P = np.where(land[None], fields["P"], np.nan)
    elev = np.where(land, np.nan_to_num(fields["elev"], nan=0.0), 0.0)
    elev_max = np.where(land, np.nan_to_num(fields["elev_max"], nan=0.0), 0.0)
    g = Grid(params=None, f=1, pad=pad, ny=ny, nx=nx, cell_km=cell_km, land=land,
             land_frac=fields["land_frac"], elev=np.maximum(elev, np.where(land, 1.0, 0.0)),
             elev_max=np.maximum(elev_max, elev), lat=lat, inmap=inmap,
             target=np.zeros((ny, nx), np.int8), rivers=np.zeros((ny, nx)), lake=np.zeros((ny, nx), bool))
    g.target = observed_zones(obs_T, obs_P, g)
    g.chi_far = fetch_at(-lat if lat0 < 0 else lat, lon)     # real-world latitude for mirrored regions
    g.chi_far_long = fetch_at(-lat if lat0 < 0 else lat, lon, fetch_km=3.0 * FETCH_KM)   # e23
    g.chi_pole = pole_fetch_at(lat if lat0 >= 0 else -lat, lon)   # e31 (real latitude: south of southern regions)
    g.sea_reach = sea_reach_at(lat if lat0 >= 0 else -lat, lon)   # e42 (degrees from the equator)
    g.obs_sst = observed_sst(-lat if lat0 < 0 else lat, lon, mirrored=lat0 < 0)   # WOA18, for sst_source="observed"
    g.cloud_ref = land_cloud_at(-lat if lat0 < 0 else lat, mirrored=lat0 < 0)    # e43
    return EarthCase(name=name, grid=g, lon=lon, obs_T=obs_T, obs_P=obs_P, coast_km=coast)


FETCH_KM = 1700.0      # e6: ~ the model's CONTINENTAL_FETCH_DAYS at 5 m/s


def west_fetch(fetch_km: float = FETCH_KM) -> tuple:
    """Global land share upwind to the west with an exponential memory of
    fetch_km, on a 0.5-degree grid (WorldClim land): (field, lat, lon).
    Westward land share with a ~2,000 km memory and latitude explain 85 % of
    the variance of WorldClim's annual temperature range over land (15-65
    deg, below 1,500 m), against 60 % for latitude alone."""
    key = CACHE / f"west_fetch_{fetch_km:g}km.npz"
    if key.exists():
        z = np.load(key)
        return z["fetch"], z["lat"], z["lon"]
    elev = _wc("elev")
    land = np.isfinite(elev) & (elev > -1000)
    f = 6
    H, W = land.shape[0] // f, land.shape[1] // f
    lf = land[:H * f, :W * f].reshape(H, f, W, f).mean((1, 3))
    lat = 90 - (np.arange(H) + 0.5) * 0.5
    lon = -180 + (np.arange(W) + 0.5) * 0.5
    out = np.empty_like(lf)
    for i in range(H):
        Lc = fetch_km / (111.2 * 0.5 * max(np.cos(np.radians(lat[i])), 0.1))   # cells
        n = np.arange(int(6 * Lc) + 1)
        k = np.exp(-n / Lc)
        kw = np.zeros(W)
        np.add.at(kw, n % W, k / k.sum())                                      # land n cells to the west
        out[i] = np.real(np.fft.ifft(np.fft.fft(lf[i]) * np.fft.fft(kw)))
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(key, fetch=out.astype(np.float32), lat=lat, lon=lon)
    return out, lat, lon


POLE_FETCH_KM = 2000.0  # e31
BARRIER_M = (1500.0, 1000.0)   # e31: cold air is shallow; ground above 1,500 m passes exp(-excess / 1,000 m) per 0.5 deg


def pole_fetch(fetch_km: float = POLE_FETCH_KM) -> tuple:
    """Global land share poleward (north in the northern hemisphere, south in
    the southern) that shallow cold air can reach, with an exponential memory
    of fetch_km on the 0.5-degree WorldClim grid: each 0.5-degree step past
    ground higher than 1,500 m passes exp(-excess / 1,000 m) of the path, so
    the Himalaya and Tibet shut north India off from Siberia, the Alborz Iran
    from the Kazakh steppe, while Korea and the US plains lie open to Siberia
    and Canada. (field, lat, lon)."""
    key = CACHE / f"pole_fetch_{fetch_km:g}km.npz"
    if key.exists():
        z = np.load(key)
        return z["fetch"], z["lat"], z["lon"]
    elev = _wc("elev")
    land = np.isfinite(elev) & (elev > -1000)
    f = 6
    H, W = land.shape[0] // f, land.shape[1] // f
    lf = land[:H * f, :W * f].reshape(H, f, W, f).mean((1, 3))
    ev = np.where(land, np.nan_to_num(elev), 0.0)[:H * f, :W * f].reshape(H, f, W, f).mean((1, 3))
    lat = 90 - (np.arange(H) + 0.5) * 0.5
    lon = -180 + (np.arange(W) + 0.5) * 0.5
    trans = np.exp(-np.maximum(ev - BARRIER_M[0], 0.0) / BARRIER_M[1])
    Lc = fetch_km / (111.2 * 0.5)
    out = np.zeros_like(lf)
    for i in range(H):
        step = -1 if lat[i] >= 0 else 1                 # toward the pole: rows decrease in the north
        acc, tr, ksum = np.zeros(W), np.ones(W), 0.0
        for n in range(1, int(5 * Lc) + 1):
            k = np.exp(-n / Lc)
            ksum += k
            r = i + step * n
            if 0 <= r < H:
                acc += k * tr * lf[r]
                tr = tr * trans[r]
        out[i] = acc / ksum
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(key, fetch=out.astype(np.float32), lat=lat, lon=lon)
    return out, lat, lon


def pole_fetch_at(lat, lon, fetch_km: float = POLE_FETCH_KM):
    """Poleward reachable land (0-1) at points, bilinear on the 0.5-degree grid."""
    from scipy import ndimage as ndi

    F, flat, flon = pole_fetch(fetch_km)
    i = (flat[0] - np.asarray(lat)) / 0.5
    j = ((np.asarray(lon) - flon[0]) % 360.0) / 0.5
    Fw = np.concatenate([F, F[:, :1]], axis=1)
    return ndi.map_coordinates(Fw, [i, j], order=1, mode="nearest")


def sea_reach() -> tuple:
    """e42: for every 0.5-degree cell the latitude (degrees from the equator)
    at which a path due poleward first meets land (a cell at least half land
    on WorldClim), 90 where the sea runs open to the pole or the polar ice.
    An eastern-boundary current carries water down from the westerlies; seas
    shut off poleward before ~30 deg (the Arabian Sea at 25 N, the Bay of
    Bengal at 22 N, the Red Sea, the Persian Gulf) have no such current.
    (field, lat, lon)."""
    key = CACHE / "sea_reach.npz"
    if key.exists():
        z = np.load(key)
        return z["reach"], z["lat"], z["lon"]
    elev = _wc("elev")
    land = np.isfinite(elev) & (elev > -1000)
    f = 6
    H, W = land.shape[0] // f, land.shape[1] // f
    lf = land[:H * f, :W * f].reshape(H, f, W, f).mean((1, 3))
    lat = 90 - (np.arange(H) + 0.5) * 0.5
    lon = -180 + (np.arange(W) + 0.5) * 0.5
    out = np.empty_like(lf)
    reach = np.full(W, 90.0)
    for i in range(H):                          # north: from the pole down to the equator
        if lat[i] < 0:
            break
        reach = np.where(lf[i] >= 0.5, lat[i], reach)
        out[i] = reach
    reach = np.full(W, 90.0)
    for i in range(H - 1, -1, -1):              # south: from the pole up
        if lat[i] >= 0:
            break
        reach = np.where(lf[i] >= 0.5, -lat[i], reach)
        out[i] = reach
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(key, reach=out.astype(np.float32), lat=lat, lon=lon)
    return out, lat, lon


def sea_reach_at(lat, lon):
    """e42: sea_reach at points (real latitude: southern points look south)."""
    from scipy import ndimage as ndi

    F, flat, flon = sea_reach()
    i = (flat[0] - np.asarray(lat)) / 0.5
    j = ((np.asarray(lon) - flon[0]) % 360.0) / 0.5
    Fw = np.concatenate([F, F[:, :1]], axis=1)
    return ndi.map_coordinates(Fw, [i, j], order=1, mode="nearest")


def land_cloud() -> tuple:
    """e43: the globe's land-mean cloud cover by 0.5-degree latitude row and
    month, from the model's own cloud formula (ClimateModel: 0.2 sqrt(P) +
    ((rh - 0.3) / 0.7)^2, P in mm/day) applied to WorldClim's rain and its
    humidity (vapour pressure over the saturation at the mean temperature).
    The latitude-mean land column of the energy balance carries this
    cloudiness; a clearer place gets more sunshine. (field [12, H], lat)."""
    key = CACHE / "land_cloud.npz"
    if key.exists():
        z = np.load(key)
        return z["cloud"], z["lat"]
    elev = _wc("elev")
    f = 6
    H, W = elev.shape[0] // f, elev.shape[1] // f
    lat = 90 - (np.arange(H) + 0.5) * 0.5
    out = np.full((12, H), np.nan)
    days = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    for m in range(12):
        P = _wc("prec", m + 1) / days[m]
        T = _wc("tavg", m + 1)
        e = _wc("vapr", m + 1)
        es = 0.6112 * np.exp(17.67 * T / (T + 243.5))
        rh = np.clip(e / es, 0.0, 1.0)
        fc = np.clip(0.2 * np.sqrt(np.clip(P, 0.0, 10.0)) + np.clip((rh - 0.3) / 0.7, 0.0, 1.0) ** 2, 0.0, 1.0)
        fc = fc[:H * f, :W * f].reshape(H, f, W * f)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # rows of sea only
            out[m] = np.nanmean(fc.reshape(H, -1), axis=1)
    rows = np.isfinite(out).all(0)
    for m in range(12):                                  # rows without land: the nearest row with land
        out[m] = np.interp(lat[::-1], lat[rows][::-1], out[m][rows][::-1])[::-1]
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(key, cloud=out.astype(np.float32), lat=lat)
    return out, lat


def land_cloud_at(lat, mirrored=False):
    """e43: land_cloud at the cells' (real) latitudes, [12, ...]; months
    shifted by six for mirrored southern regions, as observed_sst."""
    F, flat = land_cloud()
    lat = np.asarray(lat, float)
    out = np.stack([np.interp(lat, flat[::-1], F[m][::-1]) for m in range(12)])
    return np.roll(out, 6, axis=0) if mirrored else out


WOA_SST = CACHE / "woa18_sst_1deg.npz"     # scripts/build_woa_sst.py


def observed_sst(lat, lon, mirrored=False):
    """Monthly sea-surface temperature [12, ...] (deg C) at points from the World
    Ocean Atlas 2018 1-degree climatology, land gaps filled from the nearest sea;
    months shifted by six for mirrored southern regions (their calendar runs as
    the northern one). None when the climatology has not been built."""
    if not WOA_SST.exists():
        return None
    from scipy import ndimage as ndi

    z = np.load(WOA_SST)
    sst = z["sst"].astype(float)
    filled = np.empty_like(sst)
    for m in range(12):
        bad = ~np.isfinite(sst[m])
        idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
        filled[m] = sst[m][tuple(idx)]
    i = np.asarray(lat, float) + 89.5
    j = (np.asarray(lon, float) + 179.5) % 360.0
    wrap = np.concatenate([filled, filled[:, :, :1]], axis=2)
    out = np.stack([ndi.map_coordinates(wrap[m], [i, j], order=1, mode="nearest") for m in range(12)])
    return np.roll(out, 6, axis=0) if mirrored else out


def fetch_at(lat, lon, fetch_km: float = FETCH_KM):
    """West fetch (0-1) at points, bilinear on the 0.5-degree grid."""
    from scipy import ndimage as ndi

    F, flat, flon = west_fetch(fetch_km)
    i = (flat[0] - np.asarray(lat)) / 0.5
    j = ((np.asarray(lon) - flon[0]) % 360.0) / 0.5
    Fw = np.concatenate([F, F[:, :1]], axis=1)                                 # wrap in longitude
    return ndi.map_coordinates(Fw, [i, j], order=1, mode="nearest")


def _aggregate(lat0, lon0, nx, ny, cell_km, half_w, half_h):
    """Area-weighted means of WorldClim pixels in each projected cell."""
    elev = _wc("elev")
    H, W = elev.shape
    plat = 90 - (np.arange(H) + 0.5) / 12
    plon = -180 + (np.arange(W) + 0.5) / 12
    # a lat/lon window safely containing the projected rectangle
    span = np.degrees(np.hypot(half_w, half_h) / R_EARTH_KM) + 1
    rows = np.flatnonzero(np.abs(plat - lat0) <= span)
    dlon = span / max(np.cos(np.radians(min(abs(lat0) + span, 89))), 0.05)
    cols = np.flatnonzero(np.abs(((plon - lon0 + 180) % 360) - 180) <= dlon)
    LAT, LON = np.meshgrid(plat[rows], plon[cols], indexing="ij")
    x, y = forward(LAT, LON, lat0, lon0)
    i = np.floor((half_h - y) / cell_km).astype(int)
    j = np.floor((x + half_w) / cell_km).astype(int)
    ok = (i >= 0) & (i < ny) & (j >= 0) & (j < nx)
    flat = np.where(ok, i * nx + j, -1).ravel()
    w = np.cos(np.radians(LAT)).ravel()
    sub = (rows[:, None], cols[None, :])
    e = elev[sub].ravel()
    isl = np.isfinite(e)
    n = ny * nx
    sel = flat >= 0

    def binsum(vals, mask):
        m = sel & mask
        return np.bincount(flat[m], weights=vals[m], minlength=n)

    wall = binsum(w, np.ones_like(isl))
    wland = binsum(w, isl)
    out = dict(land_frac=(wland / np.maximum(wall, 1e-12)).reshape(ny, nx))
    with np.errstate(invalid="ignore", divide="ignore"):
        out["elev"] = (binsum(w * np.nan_to_num(e), isl) / wland).reshape(ny, nx)
        emax = np.full(n, -np.inf)
        np.maximum.at(emax, flat[sel & isl], e[sel & isl])
        out["elev_max"] = np.where(np.isfinite(emax), emax, np.nan).reshape(ny, nx)
        T = np.full((12, ny, nx), np.nan, np.float32)
        P = np.full((12, ny, nx), np.nan, np.float32)
        for m in range(12):
            for var, arr in (("tavg", T), ("prec", P)):
                v = _wc(var, m + 1)[sub].ravel()
                good = np.isfinite(v)
                arr[m] = (binsum(w * np.nan_to_num(v), good) / binsum(w, good)).reshape(ny, nx)
    out["T"], out["P"] = T, P
    return out


# ---------------------------------------------------------------- zones and params
def observed_zones(T, P, g) -> np.ndarray:
    """The painted-zone label the zone rules give the observed climate."""
    from .score import best_zone, memberships, terrain_slope

    summer = summer_months(365, 12, 172.0)
    land = g.land & np.isfinite(T).all(0)
    Tf, Pf = np.nan_to_num(T, nan=0.0), np.nan_to_num(P, nan=0.0)
    ix = climate_indices(Tf, Pf, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    z = best_zone(mem, koppen=classify(Tf, Pf, summer))
    return np.where(land, z, 0).astype(np.int8)


def earth_params(base: Params, case: EarthCase) -> Params:
    """Earth's own geometry and calendar (day 0 = 1 January) with the
    physics constants of `base`."""
    lat0 = REGIONS[case.name]["lat0"]
    land = base.ebm_land
    if land == "earth" and lat0 < 0:
        land = "earth_mirrored"
    return base.replace(ebm_land=land, tilt=23.44, retrograde=False, north_bearing=0.0, eccentricity=0.0167,
                        # mirrored southern regions: perihelion falls in their (mirrored) summer
                        perihelion_after_solstice=13.0 if lat0 >= 0 else 13.0 + 365.25 / 2,
                        year_days=365, winter_solstice_day=354.5, lat_center=abs(lat0))


# ---------------------------------------------------------------- scoring
def compare(result, case: EarthCase) -> dict:
    """Skill against WorldClim on the scored land cells."""
    from .koppen import monthly_stats
    from .score import best_zone, memberships, objective, precision_f1, terrain_slope

    g = case.grid
    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    Ts, Ps, summer = st["Tm"], st["Pm"], st["summer"]
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    To, Po = np.nan_to_num(case.obs_T), np.nan_to_num(case.obs_P)
    ks = classify(Ts, Ps, summer)
    ko = classify(To, Po, summer)
    kr = classify(To, Ps, summer)                   # observed temperature, simulated rain (V10's convention)
    names = np.array(CODES)

    def kstats(k):
        a, b = names[ko[m]], names[k[m]]
        med = np.char.startswith(a, "Cs")
        return dict(exact=float((a == b).mean()), main_group=float(np.mean([x[0] == y[0] for x, y in zip(a, b)])),
                    arid_share=float(np.char.startswith(b, "B").mean()),
                    cs_to_arid=float(np.char.startswith(b[med], "B").mean()) if med.any() else None,
                    cs_retained=float(np.char.startswith(b[med], "Cs").mean()) if med.any() else None)

    ann_s, ann_o = Ps.sum(0), Po.sum(0)
    coast = m & (case.coast_km < 150)
    ix = climate_indices(Ts, Ps, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    cov = {}
    from .geography import TARGET_CLASSES
    for cid, key, _, _ in TARGET_CLASSES:
        sel = m & (g.target == cid)
        cov[key] = float(mem[key][sel].mean()) if sel.any() else float("nan")
    present = {k: v for k, v in cov.items() if np.isfinite(v)}
    prec, f1 = precision_f1(mem, g.target, m, cov, elev=g.elev)
    pred = best_zone(mem, koppen=ks)
    painted = m & (g.target > 0)
    recall = {key: float((pred[m & (g.target == cid)] == cid).mean())
              for cid, key, _, _ in TARGET_CLASSES if (m & (g.target == cid)).any()}
    f1p = {k: f1[k] for k in present}
    obj = objective(dict(f1=f1p, per_class=present,
                         realism=dict(map_median=float(np.median(ann_s[m])), map_p95=float(np.percentile(ann_s[m], 95)))),
                    "f1")
    return dict(
        region=case.name, scored_land_cells=int(m.sum()), cell_km=g.cell_km,
        climate_distance=climate_distance(result, case), reference_distances=reference_distances(case),
        temperature=dict(bias_C=float((Ts - To)[:, m].mean()), rmse_C=float(np.sqrt(((Ts - To)[:, m] ** 2).mean())),
                         monthly_bias_C=[float(x) for x in (Ts - To)[:, m].mean(1)],
                         coldest_bias_C=float((Ts.min(0) - To.min(0))[m].mean()),
                         warmest_bias_C=float((Ts.max(0) - To.max(0))[m].mean())),
        rain=dict(sim_mean_annual_mm=float(ann_s[m].mean()), obs_mean_annual_mm=float(ann_o[m].mean()),
                  sim_monthly_mm=[float(x) for x in Ps[:, m].mean(1)], obs_monthly_mm=[float(x) for x in Po[:, m].mean(1)],
                  monthly_mae_mm=float(np.abs(Ps - Po)[:, m].mean()),
                  annual_log_rmse=float(np.sqrt((np.log((ann_s[m] + 50) / (ann_o[m] + 50)) ** 2).mean())),
                  annual_rank_corr=_spearman(ann_s[m], ann_o[m]),
                  coast_winter_sim_mm=float(Ps[WINTER].sum(0)[coast].mean()) if coast.any() else None,
                  coast_winter_obs_mm=float(Po[WINTER].sum(0)[coast].mean()) if coast.any() else None,
                  winter_share_mae=float(np.abs(Ps[WINTER].sum(0) / np.maximum(ann_s, 1)
                                                - Po[WINTER].sum(0) / np.maximum(ann_o, 1))[m & (ann_o >= 50)].mean())),
        koppen_full_model=kstats(ks), koppen_observed_T_sim_rain=kstats(kr),
        zones=dict(objective_f1=obj, strict_agreement=float((pred[painted] == g.target[painted]).mean()),
                   coverage=present, f1=f1p, recall=recall))


def station_cell(case: EarthCase, lat, lon):
    """(row, col) of the land cell holding (lat, lon), or the nearest land cell
    (a coastal city can fall in a cell that is mostly sea)."""
    spec = REGIONS[case.name]
    x, y = forward(lat, lon, spec["lat0"], spec["lon0"])
    g = case.grid
    if spec["lat0"] < 0:
        y = -y                                   # mirrored region
    half_w, half_h = g.nx * g.cell_km / 2, g.ny * g.cell_km / 2
    i, j = int((half_h - y) // g.cell_km), int((x + half_w) // g.cell_km)
    if not g.land[i, j]:
        ii, jj = np.nonzero(g.land)
        k = np.argmin((ii - i) ** 2 + (jj - j) ** 2)
        i, j = int(ii[k]), int(jj[k])
    return i, j


def station_table(result, case: EarthCase) -> dict:
    """Monthly simulated and observed temperature (C) and rain (mm) at the
    region's STATIONS, with both Koppen classes (calendar months; for a
    mirrored southern region month 0 is July)."""
    from .koppen import monthly_stats

    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    out = {}
    for name, (la, lo) in STATIONS.get(case.name, {}).items():
        i, j = station_cell(case, la, lo)
        Ts, Ps = st["Tm"][:, i, j], st["Pm"][:, i, j]
        To, Po = case.obs_T[:, i, j], case.obs_P[:, i, j]
        if not np.isfinite(To).all():
            continue
        k = lambda T, P: CODES[int(classify(T[:, None], P[:, None], st["summer"])[0])]
        out[name] = dict(cell=(i, j), elev_m=float(case.grid.elev[i, j]), sim_T=Ts.tolist(), obs_T=To.tolist(),
                         sim_P=Ps.tolist(), obs_P=Po.tolist(), sim_koppen=k(Ts, Ps), obs_koppen=k(To, Po))
    return out


def climate_distance(result, case: EarthCase) -> float:
    """Mean over scored land cells of the atlas's climate distance to the
    observed climate: RMS monthly temperature error / 2.5 C + RMS monthly
    sqrt-rain error / 2 (0 = identical; 1 ~ 2.5 C or 100 vs 144 mm off)."""
    from .koppen import monthly_stats

    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    dT = np.sqrt(((st["Tm"] - np.nan_to_num(case.obs_T)) ** 2)[:, m].mean(0))
    dP = np.sqrt(((np.sqrt(np.maximum(st["Pm"], 0)) - np.sqrt(np.nan_to_num(case.obs_P))) ** 2)[:, m].mean(0))
    return float((dT / 2.5 + dP / 2.0).mean())


def _distance(Tp, Pp, To, Po, m):
    dT = np.sqrt(((Tp - To) ** 2)[:, m].mean(0))
    dP = np.sqrt(((np.sqrt(np.maximum(Pp, 0)) - np.sqrt(Po)) ** 2)[:, m].mean(0))
    return float((dT / 2.5 + dP / 2.0).mean())


def reference_distances(case: EarthCase, lapse=0.006) -> dict:
    """Climate distances of two references built from the observations
    themselves: every land cell given the region's mean climate (no skill),
    and every cell given the mean observed climate of its 2-degree latitude
    band, corrected for its height at 6 K/km (a perfect zonal model: right
    latitude and height, no coast-to-interior structure)."""
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    To, Po = np.nan_to_num(case.obs_T), np.nan_to_num(case.obs_P)
    Tr = np.broadcast_to(To[:, m].mean(1)[:, None, None], To.shape)
    Pr = np.broadcast_to(Po[:, m].mean(1)[:, None, None], Po.shape)
    band = np.floor(g.lat / 2.0)
    Tz, Pz = np.zeros_like(To), np.zeros_like(Po)
    for b in np.unique(band[m]):
        sel = m & (band == b)
        Tz[:, sel] = (To[:, sel] + lapse * g.elev[sel]).mean(1)[:, None] - lapse * g.elev[sel]
        Pz[:, sel] = Po[:, sel].mean(1)[:, None]
    return dict(region_mean=_distance(Tr, Pr, To, Po, m), latitude_band_and_height=_distance(Tz, Pz, To, Po, m))


def _spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def run_case(base: Params, case: EarthCase, steps=25):
    from .model import ClimateModel

    p = earth_params(base, case).replace(steps_per_year=steps)
    return ClimateModel(p, grid=case.grid).run()


def summary_line(r: dict) -> str:
    t, rn, k, kr, z = r["temperature"], r["rain"], r["koppen_full_model"], r["koppen_observed_T_sim_rain"], r["zones"]
    pct = lambda x: "  - " if x is None else f"{x:4.0%}"
    mm = lambda x: "  - " if x is None else f"{x:4.0f}"
    ref = r.get("reference_distances")
    refs = f" (refs {ref['region_mean']:.2f}/{ref['latitude_band_and_height']:.2f})" if ref else ""
    return (f"{r['region']:12s} d {r['climate_distance']:.2f}{refs} | T bias {t['bias_C']:+5.1f} C (rmse {t['rmse_C']:4.1f}) | "
            f"rain {rn['sim_mean_annual_mm']:5.0f}/{rn['obs_mean_annual_mm']:5.0f} mm, coast winter "
            f"{mm(rn['coast_winter_sim_mm'])}/{mm(rn['coast_winter_obs_mm'])} | Koppen exact {pct(k['exact'])} "
            f"(obs-T {pct(kr['exact'])}), Cs->arid {pct(k['cs_to_arid'])}, Cs kept {pct(k['cs_retained'])} "
            f"| zones {pct(z['strict_agreement'])}")


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1))
