"""Bounded damping retries for the coupled temperature/wind fixed point."""
from dataclasses import dataclass

import numpy as np


def temperature_update(previous, solved, fraction):
    """Damp the state without shrinking the full convergence error."""
    error=np.abs(solved-previous)
    state=solved if fraction==1. else previous+fraction*(solved-previous)
    return state,error


@dataclass
class TemperatureSolution:
    temperature: np.ndarray
    update: np.ndarray
    iterations: int
    converged: bool
    stages: list


def iterate_temperature(solve, initial, max_iter, relaxation, retries=0, tolerance=.05,on_retry=None):
    """Continue failed steps with half damping and twice the stage cap.

    solve(state, first_iteration) must recompute winds and solve temperature.
    The first stage exactly preserves the legacy loop. Later stages continue
    from the damped state; they never weaken the full-update tolerance.
    """
    if retries not in (0,1,2):
        raise ValueError('Temperature retries must be 0, 1 or 2')
    state=initial
    total=0
    stages=[]
    for stage in range(int(retries)+1):
        fraction=relaxation/(2**stage)
        cap=max(1,max_iter)*(2**stage)
        if stage and on_retry is not None:
            on_retry(dict(stage=stage+1,relaxation=fraction,cap=cap,
                          previous_update_c=stages[-1]['final_update_c']))
        history=[]
        done=False
        for it in range(cap):
            solved=solve(state,total==0)
            next_state,update=temperature_update(state,solved,fraction)
            maximum=float(update.max())
            if not np.isfinite(maximum):
                raise FloatingPointError('Nonfinite temperature fixed-point update')
            total+=1
            history.append(maximum)
            done=total>1 and maximum<tolerance
            state=solved if done else next_state
            if done:
                break
        stages.append(dict(relaxation=fraction,cap=cap,iterations=it+1,
                           converged=done,final_update_c=maximum,update_history_c=history))
        if done:
            break
    return TemperatureSolution(solved,update,total,done,stages)


class TemperatureConvergenceError(RuntimeError):
    def __init__(self,step,day,solution,inmap_update):
        self.details=dict(seasonal_step=step,day=float(day),iterations=solution.iterations,
                          final_update_max_c=float(solution.update.max()),
                          final_update_inmap_max_c=float(inmap_update),stages=solution.stages)
        super().__init__(f'Temperature/wind failed at seasonal step {step} (day {day:.1f}): '
                         f'{solution.iterations} iterations over {len(solution.stages)} stages, '
                         f'full update {solution.update.max():.6g} C exceeds 0.05 C')
