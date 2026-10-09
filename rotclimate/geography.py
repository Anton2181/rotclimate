"""Turn the hand-drawn map layers into model grids.

Layers (all 2000 x 926 px, 1 px = 1.1 mi = 1.77 km):
  elevation.webp       transparent = water, 4 colour tiers of height
  rivers.webp          river lines (used only for validation / drawing)
  climate_target.webp  the painted target climate zones
  roads.webp           roads + settlement dots (drawing only)
  labels.webp          place names (positions transcribed to places.csv)

The map is 2000 x 926 px, so its *long* side (2200.5 mi) runs east-west and
the short side (1018.5 mi ~ 14.7 deg of latitude) north-south.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .config import DATA, SOURCE, Params

EARTH_KM_PER_DEG = 111.195
MI_KM = 1.609344

TIER_COLORS = np.array(
    [(185, 215, 116), (251, 239, 175), (243, 153, 78), (205, 91, 66)], float
)
TIER_NAMES = ["lowland", "hills", "upland", "mountain"]

# target classes painted on climate_target.webp
TARGET_CLASSES = [
    # id, key, label, paint colour (RGB) used on the source image
    (1, "cold_wet", "Cold and wet (forest)", (0, 125, 10)),
    (2, "cold_dry", "Cold and dry", (255, 235, 125)),
    (3, "warm_wet", "Warm and wet", (0, 255, 255)),
    (4, "med", "Temperate / Mediterranean", (180, 255, 0)),
    (5, "swamp", "Hot and wet, swampy", (75, 255, 0)),
    (6, "tree", "Tree (hot, forested)", (75, 255, 0)),
    (7, "hot_dry", "Hot and dry", (255, 215, 0)),
]
TARGET_KEYS = {c[0]: c[1] for c in TARGET_CLASSES}
TARGET_LABELS = {c[0]: c[2] for c in TARGET_CLASSES}
TARGET_DRAW_COLORS = {
    1: "#1d5c3a", 2: "#e3c45a", 3: "#16c7c7", 4: "#a8d400",
    5: "#3aa832", 6: "#0e8a7a", 7: "#e09a00",
}


def _rgba(name: str) -> np.ndarray:
    return np.array(Image.open(SOURCE / name).convert("RGBA"))


@lru_cache(maxsize=1)
def source_layers():
    elev = _rgba("elevation.webp")
    land = elev[..., 3] > 128
    d = ((elev[..., None, :3].astype(float) - TIER_COLORS[None, None]) ** 2).sum(-1)
    tier = np.where(land, d.argmin(-1) + 1, 0).astype(np.int8)
    # tidy anti-aliased fringes: a pixel whose colour is far from every tier
    # colour takes the most common tier of its neighbourhood
    bad = land & (d.min(-1) > 900)
    if bad.any():
        filled = ndi.median_filter(tier, size=5)
        tier[bad] = np.maximum(filled[bad], 1)
    # lakes = water not connected to the outer ocean
    water = ~land
    lab, _ = ndi.label(water)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    lake = water & ~np.isin(lab, border[border > 0])
    rivers = _rgba("rivers.webp")[..., 3] > 60
    roads = _rgba("roads.webp")
    return dict(land=land, tier=tier, lake=lake, rivers=rivers, roads=roads)


@lru_cache(maxsize=1)
def _tier_ramps():
    """For every tier k, a 0..1 ramp from its lower to its upper boundary."""
    tier = source_layers()["tier"]
    ramps = {}
    for k in range(1, 5):
        inside = tier == k
        if not inside.any():
            continue
        d_lo = ndi.distance_transform_edt(tier >= k)          # distance to lower tier
        higher = tier > k
        if higher.any():
            d_hi = ndi.distance_transform_edt(~higher)
            s = d_lo / (d_lo + d_hi + 1e-9)
            # very wide plains do not climb all the way to the next tier
            s = np.minimum(s, 1 - np.exp(-d_lo / 60.0)) if k == 1 else s
        else:
            s = 1 - np.exp(-d_lo / 8.0)
        ramps[k] = np.where(inside, s, 0.0)
    return ramps


def elevation_fullres(tier_tops) -> np.ndarray:
    """Continuous elevation [m] at source resolution from the tier map."""
    tier = source_layers()["tier"]
    tops = [0.0] + list(tier_tops)
    h = np.zeros(tier.shape)
    for k, s in _tier_ramps().items():
        h += np.where(tier == k, tops[k - 1] + (tops[k] - tops[k - 1]) * s, 0.0)
    h = ndi.gaussian_filter(h, 2.0)
    return np.where(source_layers()["land"], np.maximum(h, 1.0), 0.0)


@lru_cache(maxsize=1)
def target_fullres() -> np.ndarray:
    """Integer class map (0 = unlabelled) at source resolution.

    Only the six flat paint colours are read (they are uniform to within
    +-2 RGB, while the nearest base-map colours are >= 40 away, so a strict
    match cannot pick up the underlying hills / biome colours).  Black label
    text and its anti-aliased fringe are then re-filled from the nearest
    paint, and any gap fully enclosed by one class is filled with it.
    """
    img = Image.open(SOURCE / "climate_target.webp").convert("RGB")
    img = np.array(img.resize((2000, 926), Image.NEAREST)).astype(int)
    H, W = img.shape[:2]
    paints = []                        # unique paint colours -> provisional ids
    for _, key, _, col in TARGET_CLASSES:
        if col not in paints:
            paints.append(col)
    lab = np.zeros((H, W), np.int16)
    for k, col in enumerate(paints, start=1):
        m = np.abs(img - np.array(col)).max(-1) < 20
        m = ndi.binary_opening(m, structure=np.ones((3, 3)))
        cc, n = ndi.label(m)
        if n:
            sizes = ndi.sum(m, cc, range(1, n + 1))
            m = np.isin(cc, 1 + np.where(sizes > 1500)[0])
        lab[m & (lab == 0)] = k
    # text (dark strokes + anti-aliased halo) takes the nearest paint
    text = ndi.binary_dilation(img.max(-1) < 150, iterations=2)
    edge = ndi.binary_dilation(lab > 0, iterations=3) & (lab == 0)
    fill = (text | edge) & (lab == 0)
    dist, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
    near = lab[iy, ix]
    lab[fill & (dist <= 10)] = near[fill & (dist <= 10)]
    # fill gaps enclosed by a single class, smooth ragged outlines
    for k in range(1, len(paints) + 1):
        m = ndi.binary_closing(lab == k, structure=np.ones((5, 5)), iterations=2)
        m = ndi.binary_fill_holes(m)
        lab[m & (lab == 0)] = k
    # drop fringe pixels that were only added next to the paint but are not text
    # and not enclosed (they are the 1-2 px anti-aliased paint border: keep)
    out = np.zeros((H, W), np.int8)
    xx = np.arange(W)[None, :].repeat(H, 0)
    for k, col in enumerate(paints, start=1):
        cids = [c[0] for c in TARGET_CLASSES if c[3] == col]
        m = lab == k
        if len(cids) == 2:             # same green paints swamp (west) and trees (east)
            out[m & (xx < 1150)] = cids[0]
            out[m & (xx >= 1150)] = cids[1]
        else:
            out[m] = cids[0]
    return out


def load_places():
    rows = []
    with open(DATA / "places.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(dict(name=r["name"], x=float(r["x"]), y=float(r["y"]), kind=r.get("kind", "town")))
    return rows


@dataclass
class Grid:
    params: Params
    f: int                 # source px per cell
    pad: int               # padding cells on each side
    ny: int
    nx: int
    cell_km: float
    land: np.ndarray       # bool
    land_frac: np.ndarray
    elev: np.ndarray       # m (mean)
    elev_max: np.ndarray   # m (block max, for barriers)
    lat: np.ndarray        # deg (2-D)
    inmap: np.ndarray      # bool, inside the drawn map
    target: np.ndarray     # int class (0 = none) on the grid
    rivers: np.ndarray     # river pixel fraction
    lake: np.ndarray       # bool

    @property
    def dx_m(self) -> float:
        return self.cell_km * 1000.0

    def map_slice(self):
        return (slice(self.pad, self.pad + self.ny_map), slice(self.pad, self.pad + self.nx_map))

    @property
    def ny_map(self) -> int:
        return self.inmap.sum(0).max()

    @property
    def nx_map(self) -> int:
        return self.inmap.sum(1).max()

    def src_to_grid(self, x, y):
        return x / self.f + self.pad - 0.5, y / self.f + self.pad - 0.5


def _block(a: np.ndarray, f: int, how="mean") -> np.ndarray:
    H, W = a.shape
    Hp, Wp = -(-H // f) * f, -(-W // f) * f
    a = np.pad(a, ((0, Hp - H), (0, Wp - W)), mode="edge")
    b = a.reshape(Hp // f, f, Wp // f, f)
    return getattr(b, how)(axis=(1, 3))


def _pad_side(a: np.ndarray, p: int, side: str, mode: str, fill_land: float, is_land: bool,
              gap: int = 0):
    """Pad one side of a 2-D array according to a 'beyond the map' mode.

    'ocean'  open sea all the way out
    'land'   an unknown landmass whose coast lies `gap` cells beyond the edge
    'extend' the map's own edge continued outward (blurred)
    """
    widths = {"north": ((p, 0), (0, 0)), "south": ((0, p), (0, 0)),
              "west": ((0, 0), (p, 0)), "east": ((0, 0), (0, p))}[side]
    if mode == "extend":
        # continue the edge outward, letting it blur so coastlines open up
        # into a generic continent instead of straight stripes
        out = np.pad(a.astype(float), widths, mode="edge")
        axis_rows = side in ("north", "south")
        for k in range(1, p + 1):
            if side == "north":
                out[p - k] = ndi.gaussian_filter1d(out[p - k + 1], 1.2, mode="nearest")
            elif side == "south":
                i = out.shape[0] - p - 1 + k
                out[i] = ndi.gaussian_filter1d(out[i - 1], 1.2, mode="nearest")
            elif side == "west":
                out[:, p - k] = ndi.gaussian_filter1d(out[:, p - k + 1], 1.2, mode="nearest")
            else:
                i = out.shape[1] - p - 1 + k
                out[:, i] = ndi.gaussian_filter1d(out[:, i - 1], 1.2, mode="nearest")
        del axis_rows
        return out
    val = (1.0 if is_land else fill_land) if mode == "land" else 0.0
    out = np.pad(a.astype(float), widths, mode="constant", constant_values=val)
    if mode == "land" and gap > 0:
        g = min(gap, p)
        H, W = a.shape
        if side == "north":
            out[p - g:p] = 0.0
        elif side == "south":
            out[H:H + g] = 0.0
        elif side == "west":
            out[:, p - g:p] = 0.0
        else:
            out[:, W:W + g] = 0.0
    return out


def build_grid(params: Params) -> Grid:
    if params.beyond_style == "procedural":
        beyond = ("procedural",
                  tuple(round(float(getattr(params, f"beyond_{s}_land")), 3)
                        for s in ("north", "south", "west", "east"))
                  + tuple(round(float(v), 3) if v is not None and v >= 0 else -1.0
                          for v in (params.beyond_southeast_land, params.beyond_northeast_land)),
                  round(float(params.beyond_continuity_km), 1),
                  round(float(params.beyond_relief_m), 1), int(params.beyond_seed))
    else:
        beyond = ("blocks",) + tuple(
            (side, getattr(params, f"beyond_{side}"),
             round(float(getattr(params, f"beyond_{side}_gap_km")), 1))
            for side in ("north", "south", "west", "east"))
    return _build_grid_cached(
        params.downsample, tuple(params.tier_tops), beyond, params.pad_km, params.lat_center,
        params.map_width_mi, params.map_height_mi,
    )._with_params(params)


@lru_cache(maxsize=8)
def _noise(seed: int, scales_km=(45.0, 90.0, 180.0, 360.0, 720.0), weights=(0.12, 0.3, 0.45, 0.7, 1.0),
           spacing_km=20.0, extent_km=(-2400.0, 4100.0, -2400.0, 6000.0)):
    """Seeded multi-scale noise on a fixed physical lattice (resolution
    independent): returns (field, y0, x0, spacing) with unit std."""
    y0, y1, x0, x1 = extent_km
    ny, nx = int((y1 - y0) / spacing_km), int((x1 - x0) / spacing_km)
    rng = np.random.default_rng(seed)
    out = np.zeros((ny, nx))
    for sc, w in zip(scales_km, weights):
        f = ndi.gaussian_filter(rng.standard_normal((ny, nx)), sc / spacing_km, mode="wrap")
        out += w * f / f.std()
    return out / out.std(), y0, x0, spacing_km


def _noise_at(seed, ykm, xkm):
    n, y0, x0, sp = _noise(seed)
    return ndi.map_coordinates(n, [(ykm - y0) / sp, (xkm - x0) / sp], order=1, mode="nearest")


def _procedural_offmap(core: dict, p: int, cell_km: float, low_fill: float, spec):
    """Plausible unknown surroundings for the map.

    * Near the map, whatever touches an edge (sea, coast, a mountain range)
      continues outward and fades over `continuity_km`.
    * Farther out, fractal noise makes coastlines, islands, inland seas and low
      hills; each side's land *fraction* is a free parameter (0 = open ocean,
      1 = continent).  Corners blend the two neighbouring sides.
    """
    from statistics import NormalDist

    _, fracs, cont_km, relief, seed = spec
    h, w = core["land_frac"].shape
    H, W = h + 2 * p, w + 2 * p
    ii, jj = np.mgrid[0:H, 0:W]
    dy_n, dy_s = np.maximum(p - ii, 0), np.maximum(ii - (p + h - 1), 0)
    dx_w, dx_e = np.maximum(p - jj, 0), np.maximum(jj - (p + w - 1), 0)
    dy, dx = dy_n + dy_s, dx_w + dx_e
    dist = np.hypot(dy, dx) * cell_km
    inmap = dist == 0
    ykm = (ii - p + 0.5) * cell_km
    xkm = (jj - p + 0.5) * cell_km
    # per-side land fraction, blended by direction in the corners
    tot = np.maximum(dy + dx, 1e-9)
    fN, fS, fW, fE = fracs[:4]
    # optional separate east halves of the south / north edges (v6); the west
    # halves keep fS / fN, with a ~300 km blend across the map's middle
    fSE = fracs[4] if len(fracs) > 4 and fracs[4] >= 0 else fS
    fNE = fracs[5] if len(fracs) > 5 and fracs[5] >= 0 else fN
    east = 1 / (1 + np.exp(-(jj - (p + w / 2)) * cell_km / 150.0))
    fS_x = fS * (1 - east) + fSE * east
    fN_x = fN * (1 - east) + fNE * east
    frac = (dy_n * fN_x + dy_s * fS_x + dx_w * fW + dx_e * fE) / tot
    nd = NormalDist()
    z = np.vectorize(lambda q: nd.inv_cdf(min(max(q, 0.002), 0.998)))(np.round(frac, 3))
    noise = _noise_at(seed, ykm, xkm)

    # continuation of the edge: the edge profile is blurred more and more with
    # distance (a coast spreads and dissolves) and its position meanders
    warp = 0.45 * _noise_at(seed + 500, ykm, xkm) * dist / cell_km
    ci = np.clip(ii - p + np.where(dx > 0, warp, 0.0), 0, h - 1)
    cj = np.clip(jj - p + np.where(dy > 0, warp, 0.0), 0, w - 1)
    sigmas = [0.0, 1.5, 3.0, 6.0, 12.0, 24.0]
    edge_land = np.zeros((H, W))
    edge_elev = np.zeros((H, W))
    edge_emax = np.zeros((H, W))
    s_need = 0.35 * dist / cell_km
    wsum = np.zeros((H, W))
    for k, sg in enumerate(sigmas):
        # triangular weights in sigma space
        lo = sigmas[k - 1] if k else -1.0
        hi = sigmas[k + 1] if k + 1 < len(sigmas) else 1e9
        wk = np.where(s_need <= sg, np.clip((s_need - lo) / max(sg - lo, 1e-9), 0, 1),
                      np.clip((hi - s_need) / max(hi - sg, 1e-9), 0, 1))
        if not wk.any():
            continue
        blur = {key: (ndi.gaussian_filter(core[key], sg, mode="nearest") if sg else core[key])
                for key in ("land_frac", "elev", "elev_max")}
        for acc, key in ((edge_land, "land_frac"), (edge_elev, "elev"), (edge_emax, "elev_max")):
            acc += wk * ndi.map_coordinates(blur[key], [ci, cj], order=1, mode="nearest")
        wsum += wk
    edge_land /= np.maximum(wsum, 1e-9)
    edge_elev /= np.maximum(wsum, 1e-9)
    edge_emax /= np.maximum(wsum, 1e-9)

    wc = np.exp(-dist / max(cont_km, 1.0))
    Z = (1 - wc) * (noise + z) + wc * (2.2 * (2 * edge_land - 1) + 0.5 * noise)
    land_frac = np.where(inmap, 0.0, 1 / (1 + np.exp(-4 * Z)))
    # terrain: edge ranges fade out, plus noise hills
    hills = np.maximum(_noise_at(seed + 1000, ykm, xkm), 0) * relief
    we = np.exp(-dist / max(0.6 * cont_km, 1.0))
    elev = we * edge_elev + (1 - we) * (low_fill + hills)
    elev_max = we * edge_emax + (1 - we) * (low_fill + 1.3 * hills)
    out = {}
    for k, v in (("land_frac", land_frac), ("elev", elev), ("elev_max", elev_max)):
        full = np.zeros((H, W))
        full[p:p + h, p:p + w] = core[k]
        out[k] = np.where(inmap, full, v)
    return out, inmap


@lru_cache(maxsize=8)
def _build_grid_cached(f, tier_tops, beyond, pad_km, lat_center, width_mi, height_mi):
    L = source_layers()
    px_km = width_mi * MI_KM / L["land"].shape[1]
    cell_km = px_km * f
    land_frac = _block(L["land"].astype(float), f)
    h_full = elevation_fullres(tier_tops)
    elev = _block(h_full, f)
    elev_max = _block(h_full, f, "max")
    tgt_full = target_fullres()
    # majority class per cell
    tgt = np.zeros(land_frac.shape, np.int8)
    best = np.zeros(land_frac.shape)
    for cid in range(1, 8):
        fr = _block((tgt_full == cid).astype(float), f)
        sel = fr > np.maximum(best, 0.5)
        tgt[sel] = cid
        best = np.maximum(best, fr)
    rivers = _block(L["rivers"].astype(float), f)
    lake = _block(L["lake"].astype(float), f) > 0.5
    inmap = np.ones(land_frac.shape, bool)

    p = int(round(pad_km / cell_km))
    low_fill = 0.5 * tier_tops[0]
    if beyond[0] == "procedural":
        core = dict(land_frac=land_frac, elev=elev, elev_max=elev_max)
        fields, inmap = _procedural_offmap(core, p, cell_km, low_fill, beyond)
        widths = ((p, p), (p, p))
        tgt = np.pad(tgt, widths).astype(np.int8)
        rivers = np.pad(rivers, widths)
        lake = np.pad(lake, widths).astype(bool)
        land_frac = fields["land_frac"]
        land = land_frac >= 0.5
        elev = np.where(land, np.maximum(fields["elev"], 1.0), 0.0)
        elev_max = np.where(land, np.maximum(fields["elev_max"], elev), 0.0)
    else:
        fields = dict(land_frac=land_frac, elev=elev, elev_max=elev_max)
        for side, mode, gap_km in beyond[1:]:
            gap = int(round(gap_km / cell_km))
            for k in fields:
                fields[k] = _pad_side(fields[k], p, side, mode,
                                      fill_land=(1.0 if k == "land_frac" else low_fill),
                                      is_land=(k == "land_frac"), gap=gap)
            tgt = _pad_side(tgt, p, side, "ocean", 0, False).astype(np.int8)
            rivers = _pad_side(rivers, p, side, "ocean", 0, False)
            lake = _pad_side(lake, p, side, "ocean", 0, False).astype(bool)
            inmap = _pad_side(inmap, p, side, "ocean", 0, False).astype(bool)

        land_frac = fields["land_frac"]
        land = land_frac >= 0.5
        # extended terrain relaxes toward a low plain with distance from the map
        dist = ndi.distance_transform_edt(~inmap) * cell_km
        relax = np.exp(-dist / 150.0)
        elev = np.where(inmap, fields["elev"], low_fill + (fields["elev"] - low_fill) * relax)
        elev_max = np.where(inmap, fields["elev_max"], low_fill + (fields["elev_max"] - low_fill) * relax)
        elev = np.where(land, np.maximum(elev, 1.0), 0.0)
        elev_max = np.where(land, np.maximum(elev_max, elev), 0.0)

    ny, nx = land.shape
    rows = np.arange(ny) - (p + (L["land"].shape[0] / f) / 2.0 - 0.5)
    lat1d = lat_center - rows * cell_km / EARTH_KM_PER_DEG
    lat = np.repeat(lat1d[:, None], nx, axis=1)
    g = Grid(params=None, f=f, pad=p, ny=ny, nx=nx, cell_km=cell_km, land=land,
             land_frac=land_frac, elev=elev, elev_max=elev_max, lat=lat, inmap=inmap,
             target=tgt, rivers=rivers, lake=lake)
    return g


def _with_params(self, params):
    import copy
    g = copy.copy(self)
    g.params = params
    return g


Grid._with_params = _with_params
