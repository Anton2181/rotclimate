"""Exact scoped LU reuse for the prototype's repeated scalar transport matrix.

Vapor and enthalpy have identical transport coefficients at a given iterate.
Every CSC shape, index and value must match exactly before reusing a factor.
The cache lives for one model.advance call; original module globals and all
transport/physics code bodies remain unchanged.
"""
from dataclasses import replace
import numpy as np
from scipy.sparse.linalg import splu,spsolve
from rotclimate.phase_backend import make_phase_backend,bind_dependencies
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.multilevel_transport import solve_multilevel


class ScopedTransportFactors:
    def __init__(self,*,reuse=True):
        if not isinstance(reuse,bool):raise ValueError('Need an explicit reuse flag')
        self.reuse=reuse;self.key=None;self.factor=None;self.solves=0;self.factorizations=0;self.hits=0

    def solve(self,matrix,rhs):
        self.solves+=1
        if not self.reuse:
            self.factorizations+=1
            return spsolve(matrix,rhs)
        if matrix.format!='csc':raise ValueError('Scoped transport factor expects the frozen CSC operator')
        same=self.key is not None and matrix.shape==self.key[0] and matrix.dtype==self.key[1]
        same=same and np.array_equal(matrix.indptr,self.key[2]) and np.array_equal(matrix.indices,self.key[3]) and np.array_equal(matrix.data,self.key[4])
        if same:self.hits+=1
        else:
            key=(matrix.shape,matrix.dtype,matrix.indptr.copy(),matrix.indices.copy(),matrix.data.copy())
            factor=splu(matrix.copy())
            # A failed factorization must not pair a new key with an old factor.
            self.key,self.factor=key,factor;self.factorizations+=1
        return self.factor.solve(np.asarray(rhs))

    def certificate(self):
        return dict(solves=self.solves,factorizations=self.factorizations,exact_matrix_reuses=self.hits,reuse_enabled=self.reuse,
            scope='One advance call only; exact CSC shape/index/value matching, no approximate or stale factor reuse.')


def make_shared_transport_backend(*,reuse=True,phase=enthalpy_phase_fast,name='shared_transport'):
    base=make_phase_backend(phase,name=name)
    def advance(self,state,dt_s,**kwargs):
        factors=ScopedTransportFactors(reuse=reuse)
        transport=bind_dependencies(solve_multilevel,spsolve=factors.solve)
        dynamics=bind_dependencies(base.model_type.advance,solve_multilevel=transport)
        result=dynamics(self,state,dt_s,**kwargs)
        result.certificate['transport_factor_reuse']=factors.certificate()
        return result
    model=type('SharedTransportOpenMeanModel',(base.model_type,),dict(advance=advance,transport_reuse_enabled=reuse,__module__=__name__))
    probe=bind_dependencies(solve_multilevel,spsolve=ScopedTransportFactors(reuse=reuse).solve)
    sources=dict(base.body_sources,transport=dict(module=solve_multilevel.__module__,function=solve_multilevel.__qualname__,same_code_object=probe.__code__ is solve_multilevel.__code__))
    return replace(base,model_type=model,body_sources=sources)
