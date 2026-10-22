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


def iterate_temperature(solve, initial, max_iter, relaxation, retries=0, tolerance=.05,on_retry=None,
                        acceleration=False):
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
        states=[]
        residuals=[]
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
            if acceleration and stage and not done:
                # Type-II Anderson mixing of the last five actual operator
                # residuals. It changes the path, never the stopping tolerance.
                residual=solved-state
                states.append(np.asarray(state, float).copy())
                residuals.append(residual.copy())
                states, residuals=states[-6:], residuals[-6:]
                if len(states)>1:
                    dx=np.column_stack([(b-a).ravel() for a,b in zip(states,states[1:])])
                    df=np.column_stack([(b-a).ravel() for a,b in zip(residuals,residuals[1:])])
                    try:
                        coefficients=np.linalg.lstsq(df,residual.ravel(),rcond=1e-10)[0]
                        proposal=state+fraction*residual-((dx+fraction*df)@coefficients).reshape(state.shape)
                        if np.isfinite(proposal).all() and np.max(np.abs(proposal-state))<=max(10.,50*maximum):
                            next_state=proposal
                        else:
                            states, residuals=[],[]
                    except np.linalg.LinAlgError:
                        states, residuals=[],[]
            state=solved if done else next_state
            if done:
                break
        stages.append(dict(relaxation=fraction,cap=cap,iterations=it+1,
                           converged=done,final_update_c=maximum,update_history_c=history,
                           method='anderson' if acceleration and stage else 'damped'))
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

    def __reduce__(self):
        # picklable for worker pools: rebuilt as a plain RuntimeError with the same message
        return (RuntimeError, (str(self),))
