"""Conservative two-layer transport for opt-in independent moisture states.

The archived experimental sparse implementation remains an independent
reference. Dry-layer masses are fixed; vertical donor exchange is diagnosed
from continuity, without a prescribed humidity ratio.
"""
import warnings
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve, MatrixRankWarning
from rotclimate.layer_transport import LayerFluxSolver
from rotclimate.transport import vapor_face_fluxes, diffusion_face_fluxes, face_divergence, boundary_supply


class ReservoirTransport:
    """Steady two-layer donor transport, with conservative vertical exchange.

    Each layer has fixed dry mass eta*M or (1-eta)*M. Winds must balance the
    total dry column on the exact arithmetic faces. F=-div(eta*M*Ulower)
    is the lower-to-upper dry mass flux (relative column mass/s). Donor q
    moves with F, so horizontal plus vertical flow preserves a uniform q.
    Optional symmetric conductance rate*M*eta*(1-eta) mixes q vertically.
    Domain edges prescribe each layer's water independently. No surface or
    top mass flux, condensation, saturation, heat, time tendency or storm
    exchange is supplied by this isolated linear operator.
    """
    def __init__(self, mass, lower_wind, upper_wind, dx, *, lower_fraction=.25, mixing_rate=0.):
        self.mass=np.asarray(mass,float).copy();self.eta=float(lower_fraction);self.dx=float(dx)
        if (self.mass.ndim!=2 or min(self.mass.shape)<3 or not np.isfinite(self.mass).all()
                or (self.mass<=0).any() or not np.isfinite(self.dx) or self.dx<=0
                or not np.isfinite(self.eta) or not 0<self.eta<1):
            raise ValueError('Need positive finite matching dry mass, spacing and layer fraction')
        self.shape=self.mass.shape;self.winds=[]
        for wind in [lower_wind,upper_wind]:
            if len(wind)!=2:raise ValueError('Need east/north velocity in each layer')
            arrays=tuple(np.asarray(v,float).copy() for v in wind)
            if any(v.shape!=self.shape or not np.isfinite(v).all() for v in arrays):
                raise ValueError('Need finite matching two-dimensional winds')
            self.winds.append(arrays)
        mix=np.broadcast_to(np.asarray(mixing_rate,float),self.shape)
        if not np.isfinite(mix).all() or (mix<0).any():raise ValueError('Mixing rate must be finite and nonnegative')
        self.layer_mass=np.stack([self.eta*self.mass,(1-self.eta)*self.mass])
        dry_div=[]
        for m,(u,v) in zip(self.layer_mass,self.winds):
            # q=1 makes vapor_face_fluxes exactly the dry-air face flux.
            dry_div.append(face_divergence(*vapor_face_fluxes(m,u,v,mass=m),self.dx))
        speed=max(1.,*(float(np.hypot(*w).max()) for w in self.winds))
        scale=float(self.mass.max())*speed/self.dx
        self.dry_residual=float(np.max(np.abs(dry_div[0]+dry_div[1])))/scale
        if self.dry_residual>1e-10:raise ValueError('Layer winds do not balance stationary dry-column mass')
        self.upward_air=np.zeros(self.shape);self.upward_air[1:-1,1:-1]=-dry_div[0]
        conductance=mix*self.mass*self.eta*(1-self.eta)
        self.lower_out=(np.maximum(self.upward_air,0)+conductance)/self.layer_mass[0]
        self.upper_out=(np.maximum(-self.upward_air,0)+conductance)/self.layer_mass[1]
        self.horizontal=LayerFluxSolver(*self.shape,self.dx,column_mass=self.mass)
        self.border=self.horizontal.border;self.count=self.mass.size

    def vertical_water_flux(self,water):
        water=self._field(water,'water')
        return self.lower_out*water[0]-self.upper_out*water[1]

    def _field(self,value,name):
        value=np.asarray(value,float)
        if value.shape!=(2,)+self.shape or not np.isfinite(value).all():
            raise ValueError('Need finite matching two-layer '+name)
        return value

    def matrix(self,reaction,diffusion=0.):
        reaction=np.broadcast_to(np.asarray(reaction,float),(2,)+self.shape)
        if not np.isfinite(reaction).all() or (reaction<0).any():raise ValueError('Reaction must be finite and nonnegative')
        if np.ndim(diffusion)!=0 or not np.isfinite(diffusion) or diffusion<0:raise ValueError('Need finite nonnegative uniform diffusion')
        n=self.count;nx=self.shape[1];center=np.arange(n).reshape(self.shape)[1:-1,1:-1].ravel()
        edge=np.nonzero(self.border.ravel())[0];rows=[];cols=[];values=[]
        for layer,(u,v) in enumerate(self.winds):
            ce,cw,cs,cn,diag=self.horizontal.mass_coefficients(u,v,diffusion,reaction[layer])
            own,cross=(self.lower_out,self.upper_out) if layer==0 else (self.upper_out,self.lower_out)
            off=layer*n;index=off+center
            for neighbor,value in [(center+1,ce),(center-1,cw),(center+nx,cs),(center-nx,cn),(center,diag+own)]:
                rows.append(index);cols.append(off+neighbor);values.append(value[1:-1,1:-1].ravel())
            rows.append(index);cols.append((1-layer)*n+center);values.append(-cross[1:-1,1:-1].ravel())
            rows.append(off+edge);cols.append(off+edge);values.append(np.ones(len(edge)))
        return coo_matrix((np.concatenate(values),(np.concatenate(rows),np.concatenate(cols))),shape=(2*n,2*n)).tocsr()

    def solve(self,source,reaction,boundary,diffusion=0.):
        source=self._field(source,'source');boundary=self._field(boundary,'boundary')
        if (source<0).any() or (boundary<0).any():raise ValueError('Water supplies must be nonnegative')
        operator=self.matrix(reaction,diffusion)
        rhs=source.copy();rhs[:,self.border]=boundary[:,self.border]
        with warnings.catch_warnings():
            warnings.simplefilter('error',MatrixRankWarning)
            water=spsolve(operator,rhs.ravel()).reshape((2,)+self.shape)
        if not np.isfinite(water).all() or (water<0).any():raise FloatingPointError('Invalid two-layer water solution')
        error=np.abs(operator@water.ravel()-rhs.ravel())
        scaled=float(np.max(error/np.maximum(operator.diagonal(),1e-30)))
        tolerance=1e-10*max(1.,float(water.max()))
        if scaled>tolerance:raise RuntimeError('Two-layer equation failed its scaled residual')
        return water,dict(diagonal_scaled_residual_mm=scaled,tolerance_mm=tolerance,
                          max_scaled_dry_column_residual=self.dry_residual,minimum_water_mm=float(water.min()),
                          scope='Isolated steady transport operator; not a climate simulation')

    def terms(self,water,diffusion=0.):
        water=self._field(water,'water');horizontal=[];boundary=[]
        for amount,mass,(u,v) in zip(water,self.layer_mass,self.winds):
            faces=vapor_face_fluxes(amount,u,v,mass=mass)
            mixing=diffusion_face_fluxes(amount,diffusion,self.dx,mass=mass)
            horizontal.append(-face_divergence(*faces,self.dx)-face_divergence(*mixing,self.dx))
            boundary.append((boundary_supply(*faces,self.dx)+boundary_supply(*mixing,self.dx))/86400.)
        vertical=self.vertical_water_flux(water)[1:-1,1:-1]
        return np.stack(horizontal)+np.stack([-vertical,vertical]),np.array(boundary)


try:
    from numba import njit
    HAVE_BLOCK_NUMBA=True
except ImportError:  # preserve the core model's optional-Numba behavior
    HAVE_BLOCK_NUMBA=False
    def njit(**kwargs):
        return lambda function:function


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
    if HAVE_BLOCK_NUMBA:
        iterations=_sweep(water,coefficients,operator.lower_out,operator.upper_out,source,tolerance,max_iter)
    else:
        water,_=operator.solve(source,reaction,boundary,diffusion=diffusion)
        iterations=0
    matrix=operator.matrix(reaction,diffusion);rhs=source.copy();rhs[:,operator.border]=boundary[:,operator.border]
    def error(w):
        if not np.isfinite(w).all() or (w<0).any():return float('inf')
        residual=np.abs(matrix@w.ravel()-rhs.ravel())
        return float(np.max(residual/np.maximum(matrix.diagonal(),1e-30)))
    scaled=error(water);method='block_gauss_seidel' if HAVE_BLOCK_NUMBA else 'sparse_no_numba'
    roundoff=50*np.finfo(float).eps*max(1.,float(np.max(np.abs(water))))
    if scaled>tolerance+roundoff and recover:
        water,_=operator.solve(source,reaction,boundary,diffusion=diffusion)
        scaled=error(water);method='sparse_recovery'
    roundoff=50*np.finfo(float).eps*max(1.,float(np.max(np.abs(water))))
    if not np.isfinite(scaled) or scaled>tolerance+roundoff:raise RuntimeError('Reservoir block solve failed actual equation/boundary tolerance')
    return water,dict(method=method,iterations=iterations,diagonal_scaled_residual_mm=scaled,tolerance_mm=tolerance,
        max_scaled_dry_column_residual=operator.dry_residual,minimum_water_mm=float(water.min()),
        scope='Unchanged independent sparse-matrix equation checked after coupled block sweeps')
