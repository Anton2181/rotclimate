"""Stream-power erosion for the satellite renderer: carves branching valleys
into a height field so drawn mountain ranges read as ranges.

Each step floods the surface from the sea (priority flood, so every cell
drains and the pop order runs from the outlets uphill), accumulates drainage
area down the receivers, and lowers each cell towards its receiver with the
implicit stream-power update of Braun & Willett (2013):

    z_i <- (z_i + F z_r) / (1 + F),   F = K dt A_i^m / dx_ir

Valleys cut where the drainage area is large, ridges stay between them.
"""
from __future__ import annotations

import numpy as np
from numba import njit

_DY = np.array([-1, -1, -1, 0, 0, 1, 1, 1])
_DX = np.array([-1, 0, 1, -1, 1, -1, 0, 1])
_DD = np.array([1.4142135623730951, 1.0, 1.4142135623730951, 1.0, 1.0, 1.4142135623730951, 1.0, 1.4142135623730951])


@njit(cache=True)
def _push(hk, hi, n, key, idx):
    hk[n] = key
    hi[n] = idx
    c = n
    while c > 0:
        p = (c - 1) >> 1
        if hk[p] <= hk[c]:
            break
        hk[p], hk[c] = hk[c], hk[p]
        hi[p], hi[c] = hi[c], hi[p]
        c = p
    return n + 1


@njit(cache=True)
def _pop(hk, hi, n):
    key, idx = hk[0], hi[0]
    n -= 1
    hk[0] = hk[n]
    hi[0] = hi[n]
    c = 0
    while True:
        l = 2 * c + 1
        if l >= n:
            break
        r = l + 1
        m = r if (r < n and hk[r] < hk[l]) else l
        if hk[c] <= hk[m]:
            break
        hk[c], hk[m] = hk[m], hk[c]
        hi[c], hi[m] = hi[m], hi[c]
        c = m
    return key, idx, n


@njit(cache=True)
def _flood(z, domain, eps):
    """Priority flood from the sea: fills pits in place, returns the receiver
    of every cell, the distance to it (in cells) and the visiting order."""
    H, W = z.shape
    N = H * W
    recv = -np.ones(N, np.int64)
    dist = np.ones(N, np.float64)
    seen = np.zeros(N, np.bool_)
    order = np.empty(N, np.int64)
    hk = np.empty(N, np.float64)
    hi = np.empty(N, np.int64)
    n = 0
    for y in range(H):
        for x in range(W):
            if domain[y, x]:
                continue
            seen[y * W + x] = True
            for k in range(8):
                yy, xx = y + _DY[k], x + _DX[k]
                if 0 <= yy < H and 0 <= xx < W and domain[yy, xx]:
                    n = _push(hk, hi, n, z[y, x], y * W + x)
                    break
    no = 0
    while n > 0:
        key, c, n = _pop(hk, hi, n)
        cy, cx = c // W, c % W
        if domain[cy, cx]:
            order[no] = c
            no += 1
        for k in range(8):
            yy, xx = cy + _DY[k], cx + _DX[k]
            if not (0 <= yy < H and 0 <= xx < W):
                continue
            j = yy * W + xx
            if seen[j] or not domain[yy, xx]:
                continue
            seen[j] = True
            if z[yy, xx] <= z[cy, cx] + eps:
                z[yy, xx] = z[cy, cx] + eps
            recv[j] = c
            dist[j] = _DD[k]
            n = _push(hk, hi, n, z[yy, xx], j)
    return recv, dist, order[:no]


@njit(cache=True)
def _erode_step(z, recv, dist, order, K, dx, m):
    H, W = z.shape
    N = H * W
    A = np.zeros(N, np.float64)
    for i in range(order.size):
        A[order[i]] = dx * dx
    for i in range(order.size - 1, -1, -1):          # uphill to downhill
        c = order[i]
        r = recv[c]
        if r >= 0:
            A[r] += A[c]
    zf = z.ravel()
    Kf = K.ravel()
    for i in range(order.size):                       # downhill to uphill
        c = order[i]
        r = recv[c]
        if r < 0:
            continue
        F = Kf[c] * A[c] ** m / (dist[c] * dx)
        zf[c] = (zf[c] + F * zf[r]) / (1.0 + F)
    return A


def erode(z, domain, K, dx, steps=12, m=0.5, eps=1e-3):
    """Carve z (m) over `domain` (land and lakes; everything else is sea at
    base level). K is the per-cell erodibility times the time step. Returns
    the carved surface and the drainage area (m^2) of the last step."""
    z = np.ascontiguousarray(z, np.float64).copy()
    domain = np.ascontiguousarray(domain, np.bool_)
    K = np.ascontiguousarray(K, np.float64)
    A = None
    for _ in range(steps):
        recv, dist, order = _flood(z, domain, eps)
        A = _erode_step(z, recv, dist, order, K, float(dx), float(m))
    return z, A.reshape(z.shape)


def uplift_landscape(target, domain, dx, steps=150, K=2e-3, m=0.5, seed=0, jitter=0.5):
    """Grow a landscape to steady state under an uplift pattern shaped like
    `target` against stream-power erosion. The uplift is patchy (`jitter`)
    and every step adds a little fresh noise, so the channel network
    organises itself into branching valleys instead of the straight lines of
    a single steepest-descent pass. Returns the grown surface (not scaled to
    `target`)."""
    rng = np.random.default_rng(seed)
    domain = np.ascontiguousarray(domain, np.bool_)
    z = np.where(domain, rng.random(target.shape) * 5.0, 0.0).astype(np.float64)
    patch = rng.standard_normal(target.shape)
    from scipy import ndimage as ndi
    patch = ndi.gaussian_filter(patch, 3.0)
    patch /= patch.std() + 1e-12
    U = np.where(domain, np.maximum(target, 0.0) * (1.0 + jitter * patch).clip(0.2, None) * 4.0 / steps, 0.0)
    Kf = np.full(target.shape, K, np.float64)
    for _ in range(steps):
        z += U + np.where(domain, rng.random(target.shape) * 0.02 * U.max(), 0.0)
        recv, dist, order = _flood(z, domain, 1e-3)
        _erode_step(z, recv, dist, order, Kf, float(dx), float(m))
    return z
