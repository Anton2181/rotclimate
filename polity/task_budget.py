"""One supplied physical workforce budget across baseline and additional roles.

Complete baseline timing and task hours are explicit scenario inputs. A budget
check does not establish historical staffing, task intensity or physical access.
"""
import numpy as np


def _ids(values,label):
    if isinstance(values,(str,bytes)):raise ValueError(f'Explicit {label} IDs required')
    values=tuple(values)
    if any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values):
        raise ValueError(f'Unique nonempty {label} IDs required')
    return values


class TaskBudget:
    def __init__(self,workforce_ids,annual_capacity,monthly_capacity,baseline_annual,baseline_monthly,*,baseline_task_ids,baseline_complete):
        self._ids=_ids(workforce_ids,'physical workforce');k=len(self._ids)
        if not k:raise ValueError('At least one physical workforce required')
        if not isinstance(baseline_complete,(bool,np.bool_)) or not baseline_complete:
            raise ValueError('Explicit complete baseline monthly schedule required')
        annual,monthly,base_annual,base_monthly=[np.array(v,float,copy=True) for v in [annual_capacity,monthly_capacity,baseline_annual,baseline_monthly]]
        if annual.shape!=(k,) or monthly.shape!=(12,k) or base_annual.shape!=(k,) or base_monthly.shape!=(12,k):
            raise ValueError('Explicit annual and twelve-bin monthly capacities/baseline required')
        if any(not np.isfinite(v).all() or (v<0).any() for v in [annual,monthly,base_annual,base_monthly]):
            raise ValueError('Finite nonnegative supplied hours required')
        self._annual=annual;self._monthly=monthly;self._base_annual=base_annual;self._base_monthly=base_monthly
        self._base_ids=_ids(baseline_task_ids,'baseline task')
        if np.any(base_annual>0) and not self._base_ids:raise ValueError('Named already-charged baseline tasks required')
        self._schedule_residual=base_annual-base_monthly.sum(0)
        if np.any(abs(self._schedule_residual)>1e-8*np.maximum(1,annual)):
            raise ValueError('Baseline annual use inconsistent with complete monthly schedule')
        self._check(base_annual,base_monthly)
        self._added=np.zeros((12,k));self._seen=set(self._base_ids);self._role_hours={};self.reserve_calls=0

    def _check(self,annual,monthly):
        if np.any(annual>self._annual+1e-8*np.maximum(1,self._annual)):
            raise ValueError('Shared annual workforce budget exceeded')
        if np.any(monthly>self._monthly+1e-8*np.maximum(1,self._monthly)):
            raise ValueError('Shared monthly workforce budget exceeded')

    def reserve(self,task_ids,workforce,month,role,hours):
        ids=_ids(task_ids,'additional task');n=len(ids);k=len(self._ids)
        if self._seen.intersection(ids):raise ValueError('Duplicate baseline/additional task debit')
        workforce=np.asarray(workforce);month=np.asarray(month);hours=np.asarray(hours,float)
        if workforce.shape!=(n,) or workforce.dtype.kind not in 'iu' or np.any((workforce<0)|(workforce>=k)):
            raise ValueError('Each task requires one physical workforce')
        if month.shape!=(n,) or month.dtype.kind not in 'iu' or np.any((month<0)|(month>=12)):
            raise ValueError('Each task requires an explicit monthly bin')
        if isinstance(role,(str,bytes)):raise ValueError('One supplied role label per task required')
        roles=tuple(role)
        if len(roles)!=n or any(not isinstance(v,str) or not v.strip() for v in roles):raise ValueError('Nonempty task role labels required')
        if hours.shape!=(n,) or not np.isfinite(hours).all() or (hours<0).any():raise ValueError('Finite nonnegative supplied task hours required')
        workforce=workforce.astype(np.intp);month=month.astype(np.intp)
        proposed=self._added.copy();np.add.at(proposed,(month,workforce),hours)
        self._check(self._base_annual+proposed.sum(0),self._base_monthly+proposed)
        # Commit only after all checks; a failed batch cannot claim IDs or hours.
        self._added=proposed;self._seen.update(ids);self.reserve_calls+=1
        for i,label in enumerate(roles):
            if label not in self._role_hours:self._role_hours[label]=np.zeros_like(proposed)
            self._role_hours[label][month[i],workforce[i]]+=hours[i]
        return self.certificate()

    def certificate(self):
        annual=self._base_annual+self._added.sum(0);monthly=self._base_monthly+self._added
        return dict(workforce_ids=self._ids,annual_capacity=self._annual.copy(),monthly_capacity=self._monthly.copy(),
            baseline_task_ids=self._base_ids,baseline_annual=self._base_annual.copy(),baseline_monthly=self._base_monthly.copy(),
            baseline_schedule_residual=self._schedule_residual.copy(),additional_monthly=self._added.copy(),
            annual_used=annual,monthly_used=monthly,annual_remaining=self._annual-annual,monthly_remaining=self._monthly-monthly,
            additional_task_ids=tuple(sorted(self._seen-set(self._base_ids))),reserve_calls=self.reserve_calls,
            additional_by_role={label:hours.copy() for label,hours in self._role_hours.items()},
            complete_supplied_schedule=True,empirical_staffing_qualified=False,handling_rate_inferred=False,
            source_affiliation_inferred=False,physical_travel_qualified=False)
