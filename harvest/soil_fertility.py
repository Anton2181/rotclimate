"""Soil fertility state: RothC-26.3 carbon turnover with SUNDIAL-style nitrogen.

Carbon follows the RothC-26.3 description (Coleman and Jenkinson, Rothamsted
Research; RothC_description.pdf), monthly:
  pools DPM, RPM, BIO, HUM (+ inert IOM), k = 10.0, 0.3, 0.66, 0.02 per year;
  a pool holding Y keeps Y exp(-a b c k / 12) at the month's end;
  a = 47.91 / (1 + exp(106.06 / (T + 18.27)));
  b from the accumulated topsoil moisture deficit (maximum
    -(20 + 1.3 clay - 0.01 clay^2) x depth/23, bare /1.8; b = 1 above 0.444 of
    the maximum, else 0.2 + 0.8 (max - acc) / (max - 0.444 max));
  c = 0.6 under vegetation, 1.0 bare;
  decomposed carbon: x / (x + 1) to CO2, the rest 46 % BIO and 54 % HUM,
    x = 1.67 (1.85 + 1.60 exp(-0.0786 clay));
  plant inputs DPM/RPM 1.44 (59 % DPM); FYM 49 % DPM, 49 % RPM, 2 % HUM.
Evapotranspiration in the deficit is 0.75 x open-pan evaporation in RothC; here
the caller passes that evapotranspiration directly.

Nitrogen follows SUNDIAL (Bradbury et al. 1993): BIO and HUM hold N at C:N 8.5;
DPM and RPM carry the N of their inputs. Decomposing pools release their N;
the new BIO + HUM take N at 8.5. The difference is net mineralization (negative
= immobilization from the mineral pool). If the mineral pool cannot supply an
immobilization, the decomposition of DPM and RPM that month is scaled down, so
nitrogen is conserved exactly.

Carbon in t C/ha, nitrogen in kg N/ha.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

K = dict(dpm=10.0, rpm=0.3, bio=0.66, hum=0.02)
CN_BIOHUM = 8.5
DPM_SHARE_PLANT = 1.44 / 2.44
FYM_SPLIT = (0.49, 0.49, 0.02)          # DPM, RPM, HUM
BIO_SHARE = 0.46


def rate_temperature(t):
    """RothC temperature factor a (mean monthly air temperature, deg C)."""
    if t <= -18.27 + 1e-9:
        return 0.0
    return 47.91 / (1.0 + math.exp(106.06 / (t + 18.27)))


def max_tsmd(clay, depth_cm=23.0):
    """RothC maximum topsoil moisture deficit (mm, negative) for the layer."""
    return -(20.0 + 1.3 * clay - 0.01 * clay * clay) * depth_cm / 23.0


def co2_ratio(clay):
    """RothC CO2 / (BIO + HUM)."""
    return 1.67 * (1.85 + 1.60 * math.exp(-0.0786 * clay))


def inert(toc):
    """Falloon et al. (1998): IOM = 0.049 TOC^1.139 (t C/ha)."""
    return 0.049 * toc ** 1.139


@dataclass
class Pools:
    dpm: float = 0.0
    rpm: float = 0.0
    bio: float = 0.0
    hum: float = 0.0
    dpm_n: float = 0.0       # kg N/ha
    rpm_n: float = 0.0
    tsmd: float = 0.0        # accumulated topsoil moisture deficit (mm, <= 0)

    @property
    def active_c(self):
        return self.dpm + self.rpm + self.bio + self.hum

    @property
    def organic_n(self):
        return self.dpm_n + self.rpm_n + 1000.0 * (self.bio + self.hum) / CN_BIOHUM


def moisture(pools, rain, et, vegetated, clay, depth_cm=23.0):
    """Update the accumulated TSMD and return (new_tsmd, b)."""
    mx = max_tsmd(clay, depth_cm)
    acc = pools.tsmd
    balance = rain - et
    if balance < 0:
        limit = mx if vegetated else mx / 1.8
        if acc > limit:                       # bare soil stops at BareSMD unless already drier
            acc = max(acc + balance, limit)
    else:
        acc = min(acc + balance, 0.0)
    if acc >= 0.444 * mx:
        b = 1.0
    else:
        b = 0.2 + 0.8 * (mx - acc) / (mx - 0.444 * mx)
    return acc, b


def add_plant(pools, carbon, cn):
    """Plant residue input (t C/ha) at C:N cn, split DPM/RPM 1.44."""
    if carbon <= 0:
        return pools
    d = carbon * DPM_SHARE_PLANT
    r = carbon - d
    n = 1000.0 * carbon / cn
    return replace(pools, dpm=pools.dpm + d, rpm=pools.rpm + r,
                   dpm_n=pools.dpm_n + n * d / carbon, rpm_n=pools.rpm_n + n * r / carbon)


def add_fym(pools, carbon, nitrogen, hum_share=None):
    """Farmyard manure (t C/ha, kg N/ha): 49 % DPM, 49 % RPM, 2 % HUM (RothC), or
    hum_share to HUM and the rest split equally DPM/RPM (round-2 option).

    The HUM share takes N at 8.5; the remaining N is split between DPM and RPM
    in proportion to their carbon. Returns (pools, mineral N surplus): if the
    manure is too N-poor for its HUM share, the shortfall is returned as a
    negative surplus to be taken from the mineral pool.
    """
    if carbon <= 0:
        return pools, 0.0
    split = FYM_SPLIT if hum_share is None else ((1 - hum_share) / 2, (1 - hum_share) / 2, hum_share)
    d, r, h = (carbon * s for s in split)
    n_h = 1000.0 * h / CN_BIOHUM
    rest = nitrogen - n_h
    surplus = min(rest, 0.0)
    rest = max(rest, 0.0)
    return replace(pools, dpm=pools.dpm + d, rpm=pools.rpm + r, hum=pools.hum + h,
                   dpm_n=pools.dpm_n + rest * d / (d + r), rpm_n=pools.rpm_n + rest * r / (d + r)), surplus


def rothc_month(pools, temperature, rain, et, vegetated, clay, mineral_n, depth_cm=23.0):
    """One RothC month. Returns (pools, net mineralization kg N/ha, CO2 t C/ha, abc)."""
    tsmd, b = moisture(pools, rain, et, vegetated, clay, depth_cm)
    a = rate_temperature(temperature)
    c = 0.6 if vegetated else 1.0
    f = {k: 1.0 - math.exp(-a * b * c * v / 12.0) for k, v in K.items()}
    x = co2_ratio(clay)
    keep = 1.0 / (x + 1.0)
    dec_bh = pools.bio * f['bio'] + pools.hum * f['hum']
    dec_d, dec_r = pools.dpm * f['dpm'], pools.rpm * f['rpm']
    n_d = pools.dpm_n * f['dpm']
    n_r = pools.rpm_n * f['rpm']

    def net(scale):
        released = 1000.0 * dec_bh / CN_BIOHUM + scale * (n_d + n_r)
        needed = 1000.0 * keep * (dec_bh + scale * (dec_d + dec_r)) / CN_BIOHUM
        return released - needed

    scale = 1.0
    m = net(1.0)
    if mineral_n + m < 0.0:
        # immobilization limited by mineral N: scale plant-litter decomposition (linear in scale)
        m0, m1 = net(0.0), net(1.0)
        scale = max(0.0, min(1.0, (-mineral_n - m0) / (m1 - m0))) if m1 != m0 else 0.0
        m = net(scale)
    dd, dr = scale * dec_d, scale * dec_r
    formed = keep * (dec_bh + dd + dr)
    out = Pools(dpm=pools.dpm - dd, rpm=pools.rpm - dr,
                bio=pools.bio - pools.bio * f['bio'] + BIO_SHARE * formed,
                hum=pools.hum - pools.hum * f['hum'] + (1.0 - BIO_SHARE) * formed,
                dpm_n=pools.dpm_n - scale * n_d, rpm_n=pools.rpm_n - scale * n_r, tsmd=tsmd)
    co2 = (1.0 - keep) * (dec_bh + dd + dr)
    return out, m, co2, a * b * c


def equilibrium(months, clay, plant=None, fym=None, depth_cm=23.0, years=3000, tol=1e-10):
    """Spin a repeating 12-month climate to equilibrium.

    months: 12 dicts with T, rain, et, vegetated.
    plant: 12 (t C, C:N) residue inputs; fym: 12 (t C, kg N) manure inputs.
    Mineral N is treated as unlimited during spin-up (no scaling).
    """
    p = Pools()
    plant = plant or [(0.0, 40.0)] * 12
    fym = fym or [(0.0, 0.0)] * 12
    last = None
    for _ in range(years):
        for i, m in enumerate(months):
            p = add_plant(p, *plant[i])
            p, _ = add_fym(p, *fym[i])
            p, _, _, _ = rothc_month(p, m['T'], m['rain'], m['et'], m['vegetated'], clay, 1e12, depth_cm)
        state = (p.dpm, p.rpm, p.bio, p.hum)
        if last is not None and max(abs(s - t) for s, t in zip(state, last)) < tol:
            break
        last = state
    return p


# ---------------------------------------------------------------------------
# Plot simulation: soil organic matter + one mineral N pool + crops
# ---------------------------------------------------------------------------

GRAIN_N = 23.0                    # kg N exported per t grain (grain + straw)
RESIDUE_C = (1.03, 0.63)          # t C/ha = a + b x grain (RothC Hoosfield barley inputs)
RESIDUE_CN = 40.0
POTATO = dict(demand=150.0, residue_c=0.8, residue_cn=25.0)


@dataclass
class Season:
    crop: str                     # 'cereal', 'potato', 'clover', 'fallow'
    harvest: tuple                # (year, month) of harvest / end
    uptake: frozenset = frozenset()
    vegetated: frozenset = frozenset()
    potential_t_ha: float | None = None     # cereals: kappa x A0 is applied by the simulator
    label: str = ''
    curve: dict | None = None     # (year, month) -> cumulative share of season N demand (round-2 amendment)


@dataclass
class Params:
    input_n: float                # non-fertilizer N input, kg N/ha/yr
    uptake_rate: float            # fraction of the mineral pool taken per uptake month
    kappa: float                  # climate potential scale on A0
    prior_manure: float = 0.0     # t C/ha/yr FYM in the spin-up regime
    # round-2 options (plan_round2.json); defaults reproduce round 1
    fym_hum: float | None = None  # FYM humified share (None: RothC 49/49/2)
    thermal_uptake: bool = False  # uptake in every vegetated month at r_u x min(1, T/10)
    wet_deposition: bool = False  # add Rothamsted's measured wet deposition W(year) to input_n
    demand_curve: bool = False    # cap cumulative uptake by the season's demand curve (amendment_round2.json)


def wet_deposition(year):
    """Goulding et al. (1998): NO3 + NH4 N in Rothamsted precipitation, 4 kg N/ha/yr in 1855
    rising to 18 in 1980 (linear between; 4 before 1855)."""
    if year <= 1855:
        return 4.0
    return 4.0 + 14.0 * min(year - 1855, 125) / 125.0


def cereal_uptake_for(grain):
    return GRAIN_N * grain + 1000.0 * (RESIDUE_C[0] + RESIDUE_C[1] * grain) / RESIDUE_CN


def cereal_from_uptake(u):
    base = cereal_uptake_for(0.0)
    per_t = cereal_uptake_for(1.0) - base
    grain = max(0.0, (u - base) / per_t)
    return grain, RESIDUE_C[0] + RESIDUE_C[1] * grain, u - GRAIN_N * grain


def simulate(forcing, seasons, params, clay, water_mm, *, start=None, events=None, depth_cm=23.0):
    """Run one plot month by month.

    forcing: list of dicts (year, month, T, rain, et, drainage) in order.
    seasons: list of Season. events: dict (year, month) -> list of
      ('fym', t C, kg N) | ('fert', kg N) | ('residue', t C, C:N).
    start: initial Pools (equilibrium spin-up), mineral N starts at 0.
    Returns dict with per-season results and an N ledger that must close.
    """
    events = events or {}
    pools = start or Pools()
    mineral = 0.0
    crop_n = {}
    open_n0 = pools.organic_n
    totals = dict(input=0.0, fert=0.0, fym=0.0, residue_added=0.0, export=0.0, leached=0.0)
    by_harvest = {s.harvest: s for s in seasons}
    active = []
    results = []
    veg = set()
    upt = {}
    vegetated_by = {}
    for s in seasons:
        veg |= set(s.vegetated)
        for m in s.uptake:
            upt.setdefault(m, []).append(s)
        for m in s.vegetated:
            vegetated_by.setdefault(m, []).append(s)
    for row in forcing:
        key = (row['year'], row['month'])
        for ev in events.get(key, []):
            if ev[0] == 'fym':
                pools, surplus = add_fym(pools, ev[1], ev[2], params.fym_hum)
                mineral += surplus
                totals['fym'] += ev[2]
            elif ev[0] == 'fert':
                mineral += ev[1]
                totals['fert'] += ev[1]
            elif ev[0] == 'residue':
                pools = add_plant(pools, ev[1], ev[2])
                totals['residue_added'] += 1000.0 * ev[1] / ev[2]
        pools, net, _, _ = rothc_month(pools, row['T'], row['rain'], row['et'], key in veg, clay, max(mineral, 0.0), depth_cm)
        monthly_in = (params.input_n + (wet_deposition(row['year']) if params.wet_deposition else 0.0)) / 12.0
        mineral += net + monthly_in
        totals['input'] += monthly_in
        if params.thermal_uptake:
            active_now = [s for s in vegetated_by.get(key, []) if s.crop in ('cereal', 'potato')]
            g = min(1.0, max(0.0, row['T']) / 10.0)
        else:
            active_now = upt.get(key, [])
            g = 1.0
        for s in active_now:
            if s.crop == 'cereal':
                demand = cereal_uptake_for(params.kappa * (s.potential_t_ha or 0.0))
            elif s.crop == 'potato':
                demand = POTATO['demand']
            else:
                continue
            got = crop_n.get(s.harvest, 0.0)
            if params.demand_curve and s.curve is not None:
                demand = demand * s.curve.get(key, 0.0)
            u = max(0.0, min(demand - got, g * params.uptake_rate * mineral))
            mineral -= u
            crop_n[s.harvest] = got + u
        d = max(row['drainage'], 0.0)
        leach = mineral * d / (d + water_mm) if mineral > 0 else 0.0
        mineral -= leach
        totals['leached'] += leach
        s = by_harvest.get(key)
        if s is not None:
            u = crop_n.pop(key, 0.0)
            if s.crop == 'cereal':
                grain, rc, rn = cereal_from_uptake(u)
            elif s.crop == 'potato':
                grain = None
                rn = min(u, 1000.0 * POTATO['residue_c'] / POTATO['residue_cn'])
                rc = POTATO['residue_c']
            else:
                grain, rc, rn = None, 0.0, 0.0
            if rc > 0:
                if rn > 0:
                    pools = add_plant(pools, rc, 1000.0 * rc / rn)
                else:
                    pools = replace(pools, dpm=pools.dpm + rc * DPM_SHARE_PLANT, rpm=pools.rpm + rc * (1 - DPM_SHARE_PLANT))
            totals['export'] += u - rn
            results.append(dict(harvest=key, crop=s.crop, label=s.label, uptake=u, grain_t_ha=grain,
                                potential_t_ha=None if s.potential_t_ha is None else params.kappa * s.potential_t_ha,
                                mineral_after=mineral, organic_n=pools.organic_n, soc_active=pools.active_c))
    standing = sum(crop_n.values())
    stock1 = pools.organic_n + mineral + standing
    gained = totals['input'] + totals['fert'] + totals['fym'] + totals['residue_added']
    lost = totals['export'] + totals['leached']
    residual = (open_n0 + gained - lost) - stock1
    if abs(residual) > 1e-6 * max(1.0, open_n0 + gained):
        raise RuntimeError(f'N ledger did not close: {residual}')
    return dict(seasons=results, totals=totals, residual=residual, pools=pools, mineral=mineral)
