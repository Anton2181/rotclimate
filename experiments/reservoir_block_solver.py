"""Monotone two-by-two block sweeps for the existing reservoir operator.

Pure numerical backend; no sources, boundary values or physical coefficients
are changed. The original sparse operator remains the independent recovery
and equation certificate. Not yet selected by the seasonal ClimateModel.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _sweep(w,coeff,lower_out,upper_out,source,tolerance,limit):
    ny,nx=w.shape[1:]
    for iteration in range(limit):
        maximum=0.
        for order in range(4):
            for ii in range(1,ny-1):
                i=ii if order<2 else ny-1-ii
                for jj in range(1,nx-1):
                    j=jj if order%2==0 else nx-1-jj
                    a=lower_out[i,j];b=upper_out[i,j]
                    d0=coeff[0,4,i,j]+a;d1=coeff[1,4,i,j]+b
                    rhs0=source[0,i,j]-(coeff[0,0,i,j]*w[0,i,j+1]+coeff[0,1,i,j]*w[0,i,j-1]+coeff[0,2,i,j]*w[0,i+1,j]+coeff[0,3,i,j]*w[0,i-1,j])
                    rhs1=source[1,i,j]-(coeff[1,0,i,j]*w[1,i,j+1]+coeff[1,1,i,j]*w[1,i,j-1]+coeff[1,2,i,j]*w[1,i+1,j]+coeff[1,3,i,j]*w[1,i-1,j])
                    determinant=d0*d1-a*b
                    new0=(rhs0*d1+b*rhs1)/determinant
                    new1=(rhs1*d0+a*rhs0)/determinant
                    maximum=max(maximum,abs(new0-w[0,i,j]),abs(new1-w[1,i,j]))
                    w[0,i,j]=new0;w[1,i,j]=new1
        if maximum<tolerance:return iteration+1
    return limit


def solve_block(operator,source,reaction,boundary,*,diffusion=0.,guess=None,rtol=1e-7,max_iter=400,recover=True):
    """Solve the unchanged matrix, then check its actual equation and borders."""
    source=operator._field(source,'source');boundary=operator._field(boundary,'boundary')
    reaction=np.broadcast_to(np.asarray(reaction,float),source.shape)
    if (not np.isfinite(reaction).all() or (reaction<0).any() or (source<0).any() or (boundary<0).any()
            or not np.isfinite(rtol) or rtol<=0 or not isinstance(max_iter,int) or max_iter<1
            or np.ndim(diffusion)!=0 or not np.isfinite(diffusion) or diffusion<0):
        raise ValueError('Need finite nonnegative water equations and strict positive iteration settings')
    coefficients=np.stack([np.stack([np.broadcast_to(a,operator.shape) for a in
        operator.horizontal.mass_coefficients(u,v,diffusion,reaction[i])]) for i,(u,v) in enumerate(operator.winds)])
    d0=coefficients[0,4]+operator.lower_out;d1=coefficients[1,4]+operator.upper_out
    determinant=d0*d1-operator.lower_out*operator.upper_out
    if not np.isfinite(determinant).all() or (determinant[1:-1,1:-1]<=0).any():raise ValueError('Singular/nonpositive local reservoir block')
    water=boundary.copy() if guess is None else operator._field(guess,'guess').copy()
    if (water<0).any():raise ValueError('Need nonnegative linear guess')
    water[:,operator.border]=boundary[:,operator.border]
    tolerance=rtol*max(float(np.abs(boundary).max()),1e-12)
    iterations=_sweep(water,coefficients,operator.lower_out,operator.upper_out,source,tolerance,max_iter)
    matrix=operator.matrix(reaction,diffusion);rhs=source.copy();rhs[:,operator.border]=boundary[:,operator.border]
    def error(w):
        if not np.isfinite(w).all() or (w<0).any():return float('inf')
        residual=np.abs(matrix@w.ravel()-rhs.ravel())
        return float(np.max(residual/np.maximum(matrix.diagonal(),1e-30)))
    scaled=error(water);method='block_gauss_seidel'
    roundoff=50*np.finfo(float).eps*max(1.,float(np.max(np.abs(water))))
    if scaled>tolerance+roundoff and recover:
        water,_=operator.solve(source,reaction,boundary,diffusion=diffusion)
        scaled=error(water);method='sparse_recovery'
    roundoff=50*np.finfo(float).eps*max(1.,float(np.max(np.abs(water))))
    if not np.isfinite(scaled) or scaled>tolerance+roundoff:raise RuntimeError('Reservoir block solve failed actual equation/boundary tolerance')
    return water,dict(method=method,iterations=iterations,diagonal_scaled_residual_mm=scaled,tolerance_mm=tolerance,
        max_scaled_dry_column_residual=operator.dry_residual,minimum_water_mm=float(water.min()),
        scope='Unchanged independent sparse-matrix equation checked after coupled block sweeps')
