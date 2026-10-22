"""Whittaker climate envelopes digitized from Ricklefs (2008), figure 5.5.

Polygon data: Valentin Stefan's plotbiomes (MIT; see data/WHITTAKER_LICENSE.txt).
Annual temperature (C) and precipitation (mm/year) determine potential biome,
not observed vegetation. Outside-envelope climates remain unclassified.
"""
from functools import lru_cache
import csv
import numpy as np
from matplotlib.path import Path
from scipy.spatial import cKDTree
from .config import DATA

LABELS = ['Outside diagram', 'Tropical seasonal forest / savanna', 'Subtropical desert',
          'Temperate rainforest', 'Tropical rainforest', 'Woodland / shrubland', 'Tundra',
          'Boreal forest', 'Temperate grassland / desert', 'Temperate seasonal forest']
COLORS = ['#b8b8b8', '#a8bf48', '#e7be72', '#479b8a', '#176445', '#b8a36b', '#b4bbd6',
          '#7b9d8e', '#d1cc8c', '#68a64f']
NOTE = ('Potential biomes from mean annual temperature and total annual precipitation; '
        'digitized Whittaker envelopes (Ricklefs 2008, via plotbiomes). '
        'Seasonality, soils, fire and land use can change actual vegetation. '
        'Grey land lies outside the diagram; it is not forced into a biome. '
        'Percentages are shares of mapped land pixels.')
SOURCE = 'https://github.com/valentinitnelav/plotbiomes'

@lru_cache(maxsize=1)
def polygons():
    groups = {}
    with (DATA / 'whittaker_biomes.csv').open() as f:
        for row in csv.DictReader(f):
            groups.setdefault(int(row['biome_id']), []).append((float(row['temp_c']), float(row['precp_cm']) * 10))
    return {k: np.asarray(v) for k, v in sorted(groups.items())}


def classify(temperature, precipitation, land=None):
    """Return uint8 IDs (0 outside/invalid, 1..9 biome, 255 ocean).

    Exact/shared boundaries use the lowest polygon ID deterministically.
    The small positive radius includes digitized edges; no extrapolation.
    """
    t, p = np.broadcast_arrays(np.asarray(temperature, float), np.asarray(precipitation, float))
    out = np.zeros(t.shape, np.uint8)
    valid = np.isfinite(t) & np.isfinite(p) & (p >= 0)
    if land is not None:
        land = np.broadcast_to(np.asarray(land, bool), t.shape)
        valid &= land
        out[~land] = 255
    # Bounding boxes avoid testing every map pixel against every polygon.
    for code, vertices in polygons().items():
        sel = valid & (out == 0) & (t >= vertices[:,0].min()-1e-8) & (t <= vertices[:,0].max()+1e-8) \
              & (p >= vertices[:,1].min()-1e-8) & (p <= vertices[:,1].max()+1e-8)
        idx = np.flatnonzero(sel)
        path = Path(vertices)
        corners = cKDTree(vertices)
        # radius sign depends on polygon orientation, so test both to include edges.
        for start in range(0, len(idx), 200000):
            ii = idx[start:start+200000]
            points = np.column_stack((t.ravel()[ii], p.ravel()[ii]))
            inside = path.contains_points(points, radius=1e-8) | path.contains_points(points, radius=-1e-8)
            # The digitization contains a zero-area spike. Path winding rules
            # cannot include its tip; exact vertices still belong to the edge.
            missing = ~inside
            inside[missing] |= corners.query(points[missing], distance_upper_bound=1e-8)[0] < 1e-8
            out.ravel()[ii[inside]] = code
    return out


def legend(classes, land):
    values = classes[np.asarray(land, bool)]
    return [dict(id=i, label=label, color=COLORS[i], share=float(np.mean(values == i)) if values.size else 0.)
            for i, label in enumerate(LABELS)]


def rgb_image(classes):
    from matplotlib.colors import to_rgb
    colors = np.array([to_rgb(c) for c in COLORS])
    rgb = colors[np.minimum(classes, len(COLORS)-1)]
    return np.where((classes == 255)[...,None], np.array([0.84,0.89,0.94]), rgb)


def diagram(temperature, precipitation, land, path,
            title='Whittaker climate envelopes · simulated land'):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    fig, ax = plt.subplots(figsize=(9,6), layout='constrained')
    for code, vertices in polygons().items():
        ax.add_patch(Polygon(vertices, facecolor=COLORS[code], edgecolor='white', lw=0.8, label=LABELS[code]))
    t,p = np.asarray(temperature)[land], np.asarray(precipitation)[land]
    step = max(1, int(np.ceil(len(t)/20000)))
    # Preserve climate extremes in the spatial sample and show the full range;
    # otherwise very wet model outliers can disappear beyond a percentile limit.
    extremes = np.unique([np.argmax(p), np.argmin(t), np.argmax(t)])
    sample = np.unique(np.r_[np.arange(0, len(t), step), extremes])
    ax.scatter(t[sample], p[sample], s=1, c='#172430', alpha=0.12, rasterized=True)
    ax.scatter(t[extremes], p[extremes], s=18, facecolors='none', edgecolors='#172430',
               linewidths=.7, label='Temperature / rainfall extremes')
    ax.set(xlabel='Mean annual temperature (°C)', ylabel='Annual precipitation (mm)',
           title=title, xlim=(min(-16,float(t.min())-1),max(32,float(t.max())+1)),
           ylim=(0,max(4500,float(p.max())*1.05)))
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=7, frameon=False)
    fig.savefig(path, dpi=140); plt.close(fig)
