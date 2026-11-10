def solve_moisture(solver, p, u, v, lamE, ocean_water, land_source, saturation,
                   dynamics, instability, boundary, guess, exchange=0., mix=None, sink=None, closure=None,
                   gain=None, condensate=None):
    """Legacy fixed sweeps unless moisture_residual_tol > 0.

    The optional criterion is max |equation residual| / max(P+|E|,0.1)
    on the full interior, with all rates in mm/day. This is an actual local
    equation check, not the size of the artificially damped update.

    `sink` (1/s, optional): water removed from the column without raining
    (subsidence drying); it enters the equation check as negative evaporation.
    `gain` (1/s, optional): water brought in by converging air, gain * W, taken
    from the current iterate as a source so the linear solve stays well posed.
    `condensate` (optional): storm condensate in mm per exchange event. `mix`
    then returns only surviving vapor. The solve already loses this water via
    the smaller incoming target; add it to diagnosed rain, not to lamP again.
    Equation diagnostics use vapor + condensate as the balanced transport
    target and total rain as the sink, counting condensation exactly once.
    """
    if condensate is not None and mix is None:
        raise ValueError('Storm condensate requires a vapor exchange target')
    if getattr(solver,'form','concentration') == 'flux' and gain is not None:
        raise ValueError('Flux transport already includes convergence; do not add positive-only import')
    W = guess
    converged = None if p.moisture_residual_tol == 0 else False
    residual = None
    lamE_all = lamE
    previous_mixed = None
    for n in range(p.picard_iters):
        lamE = ocean_rate(p, lamE_all, W, ocean_water)
        lamP = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure,
                                spread=p.rh_spread)
        if sink is not None:
            lamP = lamP + sink
        source = land_source if gain is None else land_source + gain * W
        if mix is not None:
            mixed = mix(W) if previous_mixed is None else previous_mixed
            new = solver.solve(u, v, p.moisture_diffusion, lamE + lamP + exchange,
                               lamE * ocean_water + source + exchange * mixed, boundary, guess=W)
        else:
            new = solver.solve(u, v, p.moisture_diffusion, lamE + lamP,
                               lamE * ocean_water + source, boundary, guess=W)
        if p.moisture_relaxation == 0.5:
            W = 0.5 * (W + np.maximum(new, 0))  # exact legacy arithmetic
        else:
            W = (1-p.moisture_relaxation) * W + p.moisture_relaxation * np.maximum(new, 0)
        if p.moisture_residual_tol > 0:
            W[solver.border] = boundary[solver.border]
            P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure,
                                spread=p.rh_spread) * W * DAY
            E = (lamE * (ocean_water - W) + land_source) * DAY
            if sink is not None:
                E = E - sink * W * DAY
            if gain is not None:
                E = E + gain * W * DAY
            mixed = mix(W) if mix is not None else W
            previous_mixed = mixed if mix is not None else None
            if condensate is not None:
                condensed = condensate(W)
                P = P + exchange * condensed * DAY
                mixed = mixed + condensed
            terms = moisture_terms(W, u, v, solver.dx, p.moisture_diffusion, E, P,
                                   exchange, mixed,form=getattr(solver,'form','concentration'),layers=getattr(solver,'layers',None),
                                   mass=getattr(solver,'column_mass',None),
                                   scheme=getattr(solver,'scheme','upwind') if getattr(solver,'form','concentration') == 'flux' else 'upwind')
            residual = float(np.max((terms['absolute_residual'] / np.maximum(P + np.abs(E), 0.1))[1:-1, 1:-1]))
            if not np.isfinite(residual):
                raise FloatingPointError('Nonfinite moisture-equation residual')
            converged = residual <= p.moisture_residual_tol
            if converged:
                break
    P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure,
                                spread=p.rh_spread) * W * DAY
    if condensate is not None:
        P = P + exchange * condensate(W) * DAY
    return MoistureSolution(W, P, n+1, converged, residual)
