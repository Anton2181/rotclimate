"""Declared point grids with explicit clipped-edge phases;no outcome selection."""
import numpy as np


def phased_land_targets(land, area, *, cell_km, block_cells, row_phase=0, column_phase=0):
    land = np.asarray(land); weights = np.asarray(area, float)
    if land.ndim != 2 or land.dtype.kind != 'b' or weights.shape != land.shape:
        raise ValueError('Matching boolean land and physical area rasters required')
    if not np.isfinite(weights).all() or np.any(weights < 0) or not np.isfinite(cell_km) or cell_km <= 0:
        raise ValueError('Finite nonnegative area and positive cell size required')
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (block_cells, row_phase, column_phase)):
        raise ValueError('Integer block size and phases required')
    if block_cells < 1 or not 0 <= row_phase < block_cells or not 0 <= column_phase < block_cells:
        raise ValueError('Phases must be within the positive block size')
    h, w = land.shape; starts_y = range(-row_phase, h, block_cells); starts_x = range(-column_phase, w, block_cells)
    nodes = []; block_ids = []; areas = []; counts = []
    for iy, start_y in enumerate(starts_y):
        y0, y1 = max(0, start_y), min(h, start_y + block_cells)
        for ix, start_x in enumerate(starts_x):
            x0, x1 = max(0, start_x), min(w, start_x + block_cells)
            yy, xx = np.nonzero(land[y0:y1, x0:x1]); yy += y0; xx += x0
            if not len(yy): continue
            distance = (yy - (y0 + y1 - 1) / 2) ** 2 + (xx - (x0 + x1 - 1) / 2) ** 2
            best = int(np.argmin(distance))
            nodes.append(int(yy[best] * w + xx[best])); block_ids.append(iy * len(starts_x) + ix)
            areas.append(float(weights[yy, xx].sum())); counts.append(len(yy))
    return dict(nodes=np.asarray(nodes, 'i8'), block_ids=np.asarray(block_ids, 'i8'),
        represented_area_km2=np.asarray(areas), land_cells=np.asarray(counts, 'i8'), block_edge_km=float(cell_km * block_cells))
