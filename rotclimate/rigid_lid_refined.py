"""Rowwise-refined saddle solve; retain the original rigid-lid failure record."""
import numpy as np
from scipy.sparse import bmat,csc_matrix
from scipy.sparse.linalg import splu
from .rigid_lid_moist import RigidLidMoistModel


class RefinedSaddleSolve:
    """Three residual-correction solves, with extended-precision residuals.

    Mixed momentum/constraint rows differ greatly in scale. A global residual
    can hide a poor zero-right-hand-side mass equation. Each row is checked
    against |rhs| + |matrix|*|solution|, without relaxing physical checks.
    """
    def __init__(self,matrix):
        self.matrix=matrix.tocsc();self.factor=splu(self.matrix)
        self.extended=self.matrix.astype(np.longdouble).tocsr();self.absolute=abs(self.extended)
        self.calls=[]

    def solve(self,rhs):
        rhs=np.asarray(rhs,float);x=self.factor.solve(rhs);extended_rhs=rhs.astype(np.longdouble)
        def residual():
            xe=x.astype(np.longdouble);r=extended_rhs-self.extended@xe
            scale=abs(extended_rhs)+self.absolute@abs(xe)
            backward=float(np.max(abs(r)/np.maximum(scale,np.finfo(np.longdouble).tiny)))
            return r,backward
        _,initial=residual()
        for _ in range(3):
            r,_=residual();x+=self.factor.solve(np.asarray(r,float))
        _,final=residual()
        if final>8*np.finfo(float).eps:raise RuntimeError('Refined saddle rowwise backward error exceeds8eps')
        self.calls.append(dict(initial_rowwise_backward_error=initial,final_rowwise_backward_error=final,refinement_rounds=3))
        return x


class RefinedRigidLidMoistModel(RigidLidMoistModel):
    def advance(self,state,dt_s,**kwargs):
        if not np.isfinite(dt_s) or dt_s<=0:raise ValueError('Need a finite positive timestep')
        dt=float(dt_s)
        if dt not in self.factors:
            block=bmat([[self.identity+.5*dt*self.momentum,dt*self.constraint_gradient],
                [self.constraint,csc_matrix((self.n-1,self.n-1))]],format='csc')
            self.factors[dt]=RefinedSaddleSolve(block)
        factor=self.factors[dt];factor.calls=[]
        result=super().advance(state,dt_s,**kwargs)
        result.certificate['saddle_refinement']=dict(coupling_solves=len(factor.calls),
            maximum_initial_rowwise_backward_error=max(c['initial_rowwise_backward_error'] for c in factor.calls),
            maximum_final_rowwise_backward_error=max(c['final_rowwise_backward_error'] for c in factor.calls),refinement_rounds_per_solve=3,
            scope='Same equations and native physical tolerances; extended-precision residuals with three LU corrections, not a new physics parameter.')
        return result
