"""Koppen-Geiger classification (Peel et al. 2007 / Beck et al. 2018 rules).

Monthly statistics are computed on 12 equal "Earth months" (365/12 days)
so the thresholds keep their usual meaning; the summer half-year is the six
months nearest the summer solstice.  (The local 10-month calendar is used for
all the charts.)
"""
from __future__ import annotations

import numpy as np

CODES = [
    "Af", "Am", "Aw",
    "BWh", "BWk", "BSh", "BSk",
    "Csa", "Csb", "Csc", "Cwa", "Cwb", "Cwc", "Cfa", "Cfb", "Cfc",
    "Dsa", "Dsb", "Dsc", "Dsd", "Dwa", "Dwb", "Dwc", "Dwd", "Dfa", "Dfb", "Dfc", "Dfd",
    "ET", "EF",
]
COLORS = {
    "Af": (0, 0, 255), "Am": (0, 120, 255), "Aw": (70, 170, 250),
    "BWh": (255, 0, 0), "BWk": (255, 150, 150), "BSh": (245, 165, 0), "BSk": (255, 220, 100),
    "Csa": (255, 255, 0), "Csb": (200, 200, 0), "Csc": (150, 150, 0),
    "Cwa": (150, 255, 150), "Cwb": (100, 200, 100), "Cwc": (50, 150, 50),
    "Cfa": (200, 255, 80), "Cfb": (100, 255, 80), "Cfc": (50, 200, 0),
    "Dsa": (255, 0, 255), "Dsb": (200, 0, 200), "Dsc": (150, 50, 150), "Dsd": (150, 100, 150),
    "Dwa": (170, 175, 255), "Dwb": (90, 120, 220), "Dwc": (75, 80, 180), "Dwd": (50, 0, 135),
    "Dfa": (0, 255, 255), "Dfb": (55, 200, 255), "Dfc": (0, 125, 125), "Dfd": (0, 70, 95),
    "ET": (178, 178, 178), "EF": (102, 102, 102),
}
DESCRIPTIONS = {
    "Af": "Tropical rainforest", "Am": "Tropical monsoon", "Aw": "Tropical savanna",
    "BWh": "Hot desert", "BWk": "Cold desert", "BSh": "Hot steppe", "BSk": "Cold steppe",
    "Csa": "Mediterranean, hot summer", "Csb": "Mediterranean, warm summer",
    "Csc": "Mediterranean, cool summer",
    "Cwa": "Humid subtropical, dry winter", "Cwb": "Subtropical highland, dry winter",
    "Cwc": "Subpolar oceanic, dry winter",
    "Cfa": "Humid subtropical", "Cfb": "Oceanic", "Cfc": "Subpolar oceanic",
    "Dsa": "Continental, dry hot summer", "Dsb": "Continental, dry warm summer",
    "Dsc": "Subarctic, dry summer", "Dsd": "Subarctic, dry summer, extreme winter",
    "Dwa": "Continental monsoon, hot summer", "Dwb": "Continental monsoon, warm summer",
    "Dwc": "Subarctic monsoon", "Dwd": "Subarctic monsoon, extreme winter",
    "Dfa": "Humid continental, hot summer", "Dfb": "Humid continental, warm summer",
    "Dfc": "Subarctic", "Dfd": "Subarctic, extreme winter",
    "ET": "Tundra", "EF": "Ice cap",
}
INDEX = {c: i for i, c in enumerate(CODES)}


def monthly_weights(days, year_days=365, n_months=12):
    """Matrix [n_months, nt] averaging model steps into equal months."""
    nt = len(days)
    step = year_days / nt
    edges = np.arange(n_months + 1) * year_days / n_months
    Wm = np.zeros((n_months, nt))
    for k in range(nt):
        a, b = k * step, (k + 1) * step
        for m in range(n_months):
            ov = min(b, edges[m + 1]) - max(a, edges[m])
            if ov > 0:
                Wm[m, k] = ov
    return Wm / Wm.sum(1, keepdims=True)


def summer_months(year_days=365, n_months=12, summer_solstice=204.5):
    c = (np.arange(n_months) + 0.5) * year_days / n_months
    dist = np.abs((c - summer_solstice + year_days / 2) % year_days - year_days / 2)
    return dist < year_days / 4


def monthly_stats(T, P, days, year_days=365, summer_solstice=204.5):
    """T [nt,...] in C and P [nt,...] in mm/day -> dict of monthly fields."""
    Wm = monthly_weights(days, year_days)
    shp = T.shape[1:]
    Tm = (Wm @ T.reshape(len(days), -1)).reshape((12,) + shp)
    Pm = (Wm @ P.reshape(len(days), -1)).reshape((12,) + shp) * year_days / 12.0
    summer = summer_months(year_days, 12, summer_solstice)
    return dict(Tm=Tm, Pm=Pm, summer=summer)


def climate_indices(Tm, Pm, summer):
    MAT = Tm.mean(0)
    MAP = Pm.sum(0)
    Tcold = Tm.min(0)
    Thot = Tm.max(0)
    Tmon10 = (Tm > 10).sum(0)
    Pdry = Pm.min(0)
    Ps, Pw = Pm[summer], Pm[~summer]
    Psdry, Pwdry = Ps.min(0), Pw.min(0)
    Pswet, Pwwet = Ps.max(0), Pw.max(0)
    Psum, Pwin = Ps.sum(0), Pw.sum(0)
    # Koppen dryness threshold (MAP < 10 * Pth [mm] => B climate)
    Pth = np.where(Pwin >= 0.7 * MAP, 2 * MAT,
                   np.where(Psum >= 0.7 * MAP, 2 * MAT + 28, 2 * MAT + 14))
    Pth = np.maximum(Pth, 0.5)
    return dict(MAT=MAT, MAP=MAP, Tcold=Tcold, Thot=Thot, Tmon10=Tmon10, Pdry=Pdry,
                Psdry=Psdry, Pwdry=Pwdry, Pswet=Pswet, Pwwet=Pwwet, Pth=Pth,
                Psum=Psum, Pwin=Pwin,
                aridity=MAP / (10 * Pth))


def classify(Tm, Pm, summer, cd_threshold=0.0):
    """Return an integer array of indices into CODES."""
    x = climate_indices(Tm, Pm, summer)
    MAT, MAP, Tc, Th = x["MAT"], x["MAP"], x["Tcold"], x["Thot"]
    out = np.full(MAT.shape, -1, int)

    def put(mask, code):
        sel = mask & (out < 0)
        out[sel] = INDEX[code]

    isB = MAP < 10 * x["Pth"]
    put(isB & (MAP < 5 * x["Pth"]) & (MAT >= 18), "BWh")
    put(isB & (MAP < 5 * x["Pth"]), "BWk")
    put(isB & (MAT >= 18), "BSh")
    put(isB, "BSk")
    put(Th <= 0, "EF")
    put(Th <= 10, "ET")
    # A
    A = Tc >= 18
    put(A & (x["Pdry"] >= 60), "Af")
    put(A & (x["Pdry"] >= 100 - MAP / 25), "Am")
    put(A, "Aw")
    # C / D precipitation regime
    s = (x["Psdry"] < 40) & (x["Psdry"] < x["Pwwet"] / 3)
    w = x["Pwdry"] < x["Pswet"] / 10
    # both can hold (e.g. tropical highlands); the wetter half-year decides
    both = s & w
    s = s & ~(both & (x["Psum"] >= x["Pwin"]))
    w = w & ~s
    reg = np.where(s, "s", np.where(w, "w", "f"))
    t_a = Th >= 22
    t_b = x["Tmon10"] >= 4
    for group, gmask in (("C", Tc > cd_threshold), ("D", Tc <= cd_threshold)):
        for r in "swf":
            m = gmask & (reg == r)
            put(m & t_a, f"{group}{r}a")
            put(m & t_b, f"{group}{r}b")
            if group == "D":
                put(m & (Tc < -38), f"D{r}d")
            put(m, f"{group}{r}c")
    return out


def rgb_image(classes, mask=None, background=(255, 255, 255)):
    lut = np.array([COLORS[c] for c in CODES] + [background], np.uint8)
    idx = np.where(classes < 0, len(CODES), classes)
    img = lut[idx]
    if mask is not None:
        img[~mask] = background
    return img
