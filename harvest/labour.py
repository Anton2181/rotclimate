"""Seasonal farm-operation scheduling with explicit land and work budgets.

Whole-farm activity budgeting follows FAO Farm Management for Asia, chapter9
(https://www.fao.org/4/w7365e/w7365e0c.htm). Operation windows and per-period
resource accounting are our adaptation. No ancient work rates are defaulted.
Activities are complete annual land-use sequences, not independent crops
that may each claim the same hectare. All inputs are supplied scenarios.
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


@dataclass(frozen=True)
class FarmOperation:
    name: str
    activity: int
    allowed: object  # boolean time steps, including explicitly wrapped windows
    hours_per_hectare: object  # resource vector: human hours, team-hours, ...


@dataclass
class FarmPlan:
    hectares: np.ndarray
    completed_hectares: np.ndarray  # time x operation, sums to selected activity area
    resource_hours_used: np.ndarray  # time x resource
    unused_resource_hours: np.ndarray
    output: float
    land_used: float
    land_output_marginal: float | None  # maximum-output objective only
    work_output_marginals: np.ndarray | None  # maximum-output objective only
    task_residual: np.ndarray
    minimized_resource: int | None = None
    required_output: float | None = None
    required_output_work_marginal: float | None = None


class InfeasibleFarmPlan(ValueError):
    """The supplied output target cannot meet the declared land/work limits."""


def plan_farm(output_per_hectare,operations,*,land_hectares,available_hours):
    """Maximize supplied net food output under seasonal work and land limits.

    Each operation must be completed once on every selected hectare of its
    annual activity. Work can be split within its allowed window. Its human
    and animal requirements are simultaneous; separate winter hours cannot
    substitute for harvest hours. No task precedence, whole-worker integer
    constraint, travel, overtime, labour exchange or food storage is inferred.
    Coefficients are linear scenario inputs, not an estimated yield response.
    Unused work availability is NOT leisure or a social-development score.
    """
    return _solve_farm(output_per_hectare,operations,land_hectares=land_hectares,
        available_hours=available_hours,required_output=None,minimized_resource=None)


def minimum_farm_work(output_per_hectare,operations,*,required_output,
                      land_hectares,available_hours,resource_index=0):
    """Minimize one supplied work resource while meeting a fixed output need.

    Output may be net food energy only when the caller supplies validated net
    food coefficients. All other resources remain bounded; they are not free
    substitutes. A failure raises InfeasibleFarmPlan rather than reducing need
    or allowing work outside its window. This is not total subsistence labour.
    """
    if not np.isfinite(required_output) or required_output<0:
        raise ValueError('Finite nonnegative required output needed')
    if isinstance(resource_index,bool) or not isinstance(resource_index,(int,np.integer)):
        raise ValueError('Integer work-resource index required')
    return _solve_farm(output_per_hectare,operations,land_hectares=land_hectares,
        available_hours=available_hours,required_output=float(required_output),minimized_resource=int(resource_index))


def _solve_farm(output_per_hectare,operations,*,land_hectares,available_hours,required_output,minimized_resource):
    output=np.asarray(output_per_hectare,float);availability=np.asarray(available_hours,float)
    operations=tuple(operations)
    if output.ndim!=1 or not len(output) or not np.isfinite(output).all() or np.any(output<0):
        raise ValueError('Finite nonnegative per-hectare outputs required')
    if availability.ndim!=2 or not all(availability.shape) or not np.isfinite(availability).all() or np.any(availability<0):
        raise ValueError('Finite nonnegative time-by-resource work hours required')
    if not np.isfinite(land_hectares) or land_hectares<0:
        raise ValueError('Finite nonnegative land required')
    T,R=availability.shape;A=len(output);Q=len(operations)
    if minimized_resource is not None and not 0<=minimized_resource<R:
        raise ValueError('Work-resource index outside supplied resources')
    masks=[];requirements=[];owners=[]
    for op in operations:
        if isinstance(op.activity,bool) or not isinstance(op.activity,(int,np.integer)) or not 0<=op.activity<A:
            raise ValueError('Valid activity index required')
        mask=np.asarray(op.allowed);hours=np.asarray(op.hours_per_hectare,float)
        if mask.dtype.kind!='b' or mask.shape!=(T,) or not np.any(mask):
            raise ValueError('Nonempty boolean operation window required')
        if hours.shape!=(R,) or not np.isfinite(hours).all() or np.any(hours<0) or not np.any(hours>0):
            raise ValueError('Positive operation work and aligned resource types required')
        masks.append(mask);requirements.append(hours);owners.append(op.activity)
    if set(owners)!=set(range(A)):
        raise ValueError('Every annual activity needs at least one explicit operation')
    # Decision x_a: hectares of complete annual activity a. Decision z_qt:
    # hectares on which operation q is executed during permitted time step t.
    pairs=[(q,int(t)) for q,mask in enumerate(masks) for t in np.flatnonzero(mask)]
    size=A+len(pairs);eqrow=[];eqcol=[];eqval=[]
    for q,a in enumerate(owners):eqrow.append(q);eqcol.append(a);eqval.append(-1.)
    rows=[0]*A;cols=list(range(A));values=[1.]*A
    for k,(q,t) in enumerate(pairs,start=A):
        eqrow.append(q);eqcol.append(k);eqval.append(1.)
        for r,hours in enumerate(requirements[q]):
            if hours:rows.append(1+t*R+r);cols.append(k);values.append(hours)
    equality=coo_matrix((eqval,(eqrow,eqcol)),shape=(Q,size)).tocsr()
    limits=np.r_[land_hectares,availability.ravel()]
    objective=np.r_[-output,np.zeros(len(pairs))]
    if required_output is not None:
        target_row=1+T*R
        for a,value in enumerate(output):
            if value:rows.append(target_row);cols.append(a);values.append(-value)
        limits=np.r_[limits,-required_output]
        objective=np.r_[np.zeros(A),[requirements[q][minimized_resource] for q,t in pairs]]
    inequalities=coo_matrix((values,(rows,cols)),shape=(len(limits),size)).tocsr()
    solution=linprog(objective,A_ub=inequalities,b_ub=limits,
        A_eq=equality,b_eq=np.zeros(Q),bounds=(0,None),method='highs')
    if required_output is not None and solution.status==2:
        raise InfeasibleFarmPlan('Required output exceeds the supplied seasonal work/land limits')
    if not solution.success:raise RuntimeError('Farm-operation planning failed: '+solution.message)
    area=solution.x[:A];completed=np.zeros((T,Q))
    for k,(q,t) in enumerate(pairs,start=A):completed[t,q]=solution.x[k]
    requirements=np.asarray(requirements)
    used=completed@requirements;residual=completed.sum(axis=0)-area[np.asarray(owners)]
    area_tolerance=1e-7*max(1.,land_hectares);work_tolerance=1e-7*max(1.,float(availability.max()))
    if np.max(np.abs(residual))>area_tolerance or np.max(used-availability)>work_tolerance or area.sum()>land_hectares+area_tolerance:
        raise RuntimeError('Farm work/land budget failed')
    produced=float(output@area)
    if required_output is not None and produced<required_output-1e-7*max(1.,required_output):
        raise RuntimeError('Farm output requirement failed')
    marginals=-solution.ineqlin.marginals
    return FarmPlan(area,completed,used,np.maximum(availability-used,0),produced,float(area.sum()),
        float(marginals[0]) if required_output is None else None,
        marginals[1:].reshape(T,R) if required_output is None else None,residual,
        minimized_resource,required_output,None if required_output is None else float(marginals[-1]))
