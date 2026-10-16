"""Closed-mesh, coupled flux-corrected transport prototype; no regional years.

Upwind is the positive low-order step. A centered explicit-midpoint flux is
the high-order proposal. Zalesak-style budgets limit its conservative face
corrections to old-neighbor bounds. One face coefficient is shared by all
bounded fields; other diagnostic fields reuse that coefficient. This is an
explicit finite-volume prototype, not an implementation of implicit FEM-FCT.
Only fixed-mass balanced closed/periodic meshes are supported in this version.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from experiments import v10_cloud_lab as lab
from experiments import v10_pressure_thermo as thermal


@dataclass(frozen=True)
class Mesh:
    mass: np.ndarray
    tail: np.ndarray
    head: np.ndarray
    rate: np.ndarray
    horizontal: np.ndarray
    shape: tuple

    def divergence(self, flux):
        """Positive outgoing amount/rate; face cancellation is conservative."""
        a = np.asarray(flux, float)
        if a.shape[-1] != len(self.rate):
            raise ValueError('Flux/mesh shape mismatch.')
        flat = a.reshape((-1, len(self.rate)))
        out = np.array([np.bincount(self.tail, weights=f, minlength=len(self.mass))
                        -np.bincount(self.head, weights=f, minlength=len(self.mass)) for f in flat])
        return out.reshape(a.shape[:-1]+(len(self.mass),))

    def validate(self):
        n = len(self.mass)
        if self.mass.shape != (n,) or not n or np.prod(self.shape) != n or not np.isfinite(self.mass).all() or (self.mass <= 0).any():
            raise ValueError('Positive finite cell masses and matching shape required.')
        if any(a.ndim != 1 or len(a) != len(self.rate) for a in (self.tail, self.head, self.horizontal)) or not len(self.rate) or not np.isfinite(self.rate).all():
            raise ValueError('Invalid closed face arrays.')
        if self.tail.dtype.kind not in 'iu' or self.head.dtype.kind not in 'iu' or min(self.tail.min(), self.head.min()) < 0 or max(self.tail.max(), self.head.max()) >= n or (self.tail == self.head).any():
            raise ValueError('Invalid face connectivity.')
        if abs(self.divergence(self.rate)).max() > 1e-12*max(1., abs(self.rate).max()):
            raise ValueError('Fixed-mass transport requires balanced dry flow.')

    def outgoing_rate(self):
        return (np.bincount(self.tail, weights=np.maximum(self.rate, 0.), minlength=len(self.mass))
                +np.bincount(self.head, weights=np.maximum(-self.rate, 0.), minlength=len(self.mass)))


def closed_mesh(domain, geometry, flow):
    """Map the existing interior x/y/z fluxes to a common closed face graph."""
    mass = geometry.mass; k, ny, nx = mass.shape
    if flow.x.shape != (k, ny, nx+1) or flow.y.shape != (k, ny+1, nx) or flow.vertical.shape != (k-1, ny, nx):
        raise ValueError('Invalid closed-grid flow shape.')
    if flow.x[..., [0, -1]].any() or flow.y[:, [0, -1], :].any():
        raise ValueError('This prototype does not yet support open boundaries.')
    if not np.isfinite([domain.dx, domain.dy]).all() or min(domain.dx, domain.dy) <= 0:
        raise ValueError('Positive horizontal spacing required.')
    ids = np.arange(mass.size).reshape(mass.shape)
    tails = (ids[..., :-1], ids[:, :-1, :], ids[:-1])
    heads = (ids[..., 1:], ids[:, 1:, :], ids[1:])
    rates = (flow.x[..., 1:-1]/domain.dx, flow.y[:, 1:-1, :]/domain.dy, flow.vertical)
    mesh = Mesh(mass.ravel().copy(), np.concatenate([a.ravel() for a in tails]),
        np.concatenate([a.ravel() for a in heads]), np.concatenate([a.ravel() for a in rates]),
        np.concatenate([np.full(a.size, axis < 2) for axis, a in enumerate(rates)]), mass.shape)
    mesh.validate()
    return mesh


def periodic_mesh(cells, direction=1):
    if isinstance(cells, bool) or not isinstance(cells, (int, np.integer)) or not 4 <= cells <= 4096 or direction not in (-1, 1):
        raise ValueError('Use 4–4096 periodic cells and direction +/-1.')
    ids = np.arange(cells)
    mesh = Mesh(np.full(cells, 1./cells), ids, np.roll(ids, -1), np.full(cells, float(direction)), np.ones(cells, bool), (cells,))
    mesh.validate()
    return mesh


def flux_proposals(values, mesh, dt):
    """Integrated low/high face amounts for every supplied field."""
    a, b, f = mesh.tail, mesh.head, mesh.rate
    low = f*np.where(f >= 0., values[:, a], values[:, b])
    centered = f*.5*(values[:, a]+values[:, b])
    midpoint = values-.5*dt*mesh.divergence(centered)/mesh.mass
    high = f*.5*(midpoint[:, a]+midpoint[:, b])
    return dt*low, dt*high


def transport(values, mesh, dt, bounded=2):
    """Shared conservative correction, with no post-update scalar clipping.

    Fields are concentrations per dry mass. The first `bounded` nonnegative fields constrain
the face limiter; every field uses the same accepted face coefficient. Local
    bounds include the old cell/adjacent concentrations and the low-order state,
    with a 64-epsilon per-field arithmetic allowance and an exact zero floor.
Only balanced fixed-mass meshes with outgoing CFL <= .6 are admitted.
"""
    mesh.validate()
    c = np.asarray(values, float)
    if c.ndim != 2 or c.shape[1] != len(mesh.mass) or not np.isfinite(c).all() or isinstance(bounded, bool) or not isinstance(bounded, (int, np.integer)) or not 1 <= bounded <= len(c):
        raise ValueError('Invalid field array or bounded-field count.')
    if (c[:bounded] < 0).any():
        raise ValueError('Bounded theta/vapor fields must be nonnegative.')
    courant = dt*mesh.outgoing_rate()/mesh.mass
    if not np.isfinite(dt) or dt <= 0 or courant.max() > .6*(1+1e-12):
        raise ValueError('Positive step within the existing .6 outgoing CFL required.')
    low_amount, high_amount = flux_proposals(c, mesh, dt)
    low = c-mesh.divergence(low_amount)/mesh.mass
    correction = high_amount-low_amount
    lo = np.minimum(c[:bounded], low[:bounded]); hi = np.maximum(c[:bounded], low[:bounded])
    for i in range(bounded):
        np.minimum.at(lo[i], mesh.tail, c[i, mesh.head]); np.minimum.at(lo[i], mesh.head, c[i, mesh.tail])
        np.maximum.at(hi[i], mesh.tail, c[i, mesh.head]); np.maximum.at(hi[i], mesh.head, c[i, mesh.tail])
    # Cancellation in a constant O(300 K) theta flux must not veto a genuine
    # vapor correction. This allowance scales separately for each tracer;
    # a zero vapor lower bound remains exact. No prognosed value is clipped.
    allowance = 64*np.finfo(float).eps*np.maximum(abs(c[:bounded]).max(1), abs(low[:bounded]).max(1))
    lo = np.maximum(0., lo-allowance[:, None]); hi += allowance[:, None]
    a = correction[:bounded]
    plus = np.array([np.bincount(mesh.tail, weights=np.maximum(-f, 0.), minlength=len(mesh.mass))
                     +np.bincount(mesh.head, weights=np.maximum(f, 0.), minlength=len(mesh.mass)) for f in a])
    minus = np.array([np.bincount(mesh.tail, weights=np.maximum(f, 0.), minlength=len(mesh.mass))
                      +np.bincount(mesh.head, weights=np.maximum(-f, 0.), minlength=len(mesh.mass)) for f in a])
    rplus = np.minimum(1., np.divide(mesh.mass*np.maximum(hi-low[:bounded], 0.), plus, out=np.ones_like(plus), where=plus>0))
    rminus = np.minimum(1., np.divide(mesh.mass*np.maximum(low[:bounded]-lo, 0.), minus, out=np.ones_like(minus), where=minus>0))
    limits = np.where(a >= 0., np.minimum(rminus[:, mesh.tail], rplus[:, mesh.head]),
                     np.minimum(rplus[:, mesh.tail], rminus[:, mesh.head]))
    # A field with zero correction on a face spends no budget on that face.
    face = np.where(a == 0., 1., limits).min(0)
    # Tiny margin avoids overspending a zero lower-bound budget by roundoff.
    face *= 1-8*np.finfo(float).eps
    amount = low_amount+face*correction
    after = c-mesh.divergence(amount)/mesh.mass
    bound_error = max(float((lo-after[:bounded]).max()), float((after[:bounded]-hi).max()), 0.)
    conservation = np.sum(mesh.mass*(after-c), axis=1)
    if not np.isfinite(after).all() or bound_error > 2e-12*max(1., abs(c[:bounded]).max()) or abs(conservation).max() > 2e-12*max(1., abs(mesh.mass*c).sum()):
        raise FloatingPointError('Coupled flux-correction bounds or conservation failed.')
    return after, amount, {'maximum_courant': float(courant.max()), 'maximum_bound_error': bound_error,
        'conservation_error': conservation, 'face_coefficient': face, 'roundoff_bound_allowance': allowance}


def thermal_transport(state, flow, dt, domain, geometry, target, boundary_q):
    """Closed-mesh counterpart of the frozen thermal transport return contract.

Theta and vapor constrain one face limiter. Passive MSE and temperature reuse
it to diagnose work and signed horizontal/vertical/pressure tendencies. No
boundary input, cloud change or additional heat source is introduced.
"""
    mesh = closed_mesh(domain, geometry, flow)
    g = geometry; mass = g.mass; pi = thermal.exner(g.pressure)
    t = lab.base.temperature(state.energy, mass, state.water, g.height_m)+273.15
    theta = t/pi; q = state.water/mass
    if (theta <= 0).any() or (q < 0).any():
        raise ValueError('Positive theta and nonnegative vapor required.')
    values = np.array([theta.ravel(), q.ravel(), (state.energy/mass).ravel(), t.ravel()])
    after, amount, ledger = transport(values, mesh, dt)
    new_theta = after[0].reshape(mass.shape); water = mass*after[1].reshape(mass.shape)
    if water.min() < 0:
        raise FloatingPointError('Flux-corrected transport produced negative water.')
    energy = mass*(lab.base.CP*pi*new_theta+lab.base.G*g.height_m)+lab.base.LV*water
    passive_energy = mass*after[2].reshape(mass.shape)
    work = energy-passive_energy
    changes = np.zeros((len(thermal.PROCESSES),)+mass.shape)
    for i, faces in enumerate((mesh.horizontal, ~mesh.horizontal)):
        carried = mesh.divergence(amount[3]*faces).reshape(mass.shape)
        dry_div = mesh.divergence(mesh.rate*faces).reshape(mass.shape)
        changes[i] = (-carried+dt*t*dry_div)/mass
    changes[2] = pi*new_theta-t-changes[0]-changes[1]
    wd = mesh.divergence(amount[1]*mesh.horizontal).reshape(mass.shape)/dt
    ed = mesh.divergence(amount[2]*mesh.horizontal).reshape(mass.shape)/dt
    theta_error = float((mass*(new_theta-theta)).sum(0).mean())
    return water, energy, wd, ed, work, changes, theta_error
