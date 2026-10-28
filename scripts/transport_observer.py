"""Read-only per-solve diagnostics, outside the physical equation path.

All water fluxes are computed from the actual simultaneous solved fields,
never from products of monthly averages. Array axes: step, layer, y, x;
wind has an additional component axis (projected right/up). Border balances
are undefined: equation residuals and divergence have interior shape.
"""
import numpy as np
from rotclimate.moisture import rain_coefficient
from rotclimate.transport import vapor_face_fluxes, diffusion_face_fluxes, face_divergence

DAY=86400.


def rain_components(fields, closure, p):
    if p.moisture_reservoir_rain_scheme!='column-convection':
        raise ValueError('This diagnostic requires the declared column-convection scheme')
    w=fields['water'];sat=fields['saturation'];rh=w/fields['fractions']/sat
    overflow=np.divide(np.maximum(rh-1,0),rh,out=np.zeros_like(rh),where=rh>0)/DAY
    dynamic=rain_coefficient(w/fields['fractions'],sat,fields['dynamics'],fields['instability'],
        p.rh_threshold,p.precip_tau_days,spread=p.rh_spread)-overflow
    convective=0.;survival=1.
    if closure is not None:
        if closure['conv']>0:
            total=w.sum(0)
            convective=closure['conv']*np.exp(11.4*(np.minimum(total/sat,1.5)-closure['r0']))*closure['fT']/(np.maximum(total,.1)*DAY)
        if closure['evap']>0:
            lcl=(20+closure['T']/5)*(100-100*np.clip(rh[0],0,1))
            survival=np.exp(-closure['evap']*np.maximum(lcl,0)/3000)
    return dict(rain_dynamic=dynamic*survival*w*DAY,
        rain_convective=convective*survival*w*DAY,rain_overflow=overflow*w*DAY)


class TransportObserver:
    def __init__(self,params):
        self.params=params;self.steps=[]

    def __call__(self,payload):
        f=payload['fields'];w=f['water'];dx=payload['dx'];faces=[];diff=[]
        for amount,mass,wind in zip(w,f['layer_mass'],f['winds']):
            faces.append(vapor_face_fluxes(amount,*wind,mass=mass))
            diff.append(diffusion_face_fluxes(amount,payload['diffusion'],dx,mass=mass))
        f.update(vapor_face_x=np.stack([a[0] for a in faces]),vapor_face_south=np.stack([a[1] for a in faces]),
            diffusion_face_x=np.stack([a[0] for a in diff]),diffusion_face_south=np.stack([a[1] for a in diff]),
            advection=np.stack([-DAY*face_divergence(*a,dx) for a in faces]),
            diffusion=np.stack([-DAY*face_divergence(*a,dx) for a in diff]),
            vertical_water=(f['lower_out']*w[0]-f['upper_out']*w[1])*DAY,
            drying=f['drying_rate']*w*DAY)
        f.update(rain_components(f,payload['closure'],self.params))
        if payload['closure'] is not None:
            f.update({'closure_'+key:value for key,value in payload['closure'].items()})
        np.testing.assert_allclose(f['rain'],f['rain_dynamic']+f['rain_convective']+f['rain_overflow'],rtol=3e-14,atol=3e-14)
        vertical=f['vertical_water'][1:-1,1:-1]
        recycled=np.stack([f['recycled'],-f['recycled']])
        equation=(f['evaporation']-f['drying']+f['storm']+recycled-f['rain'])[:,1:-1,1:-1]+f['advection']+f['diffusion']+np.stack([-vertical,vertical])
        np.testing.assert_allclose(equation,f['residual'],rtol=0,atol=2e-12)
        self.steps.append(f)

    def export(self,result):
        certificates=result.numerics['moisture_reservoirs']['steps'];n=len(result.days)
        if len(certificates)!=len(self.steps) or len(self.steps)!=n+max(8,int(round(117/(365/n)))):
            raise ValueError('Missing or extra primer/scored observations')
        arrays={key:np.stack([step[key] for step in self.steps]) for key in self.steps[0]}
        np.testing.assert_array_equal(arrays['water'][-n:].astype(np.float32),result.layer_water)
        np.testing.assert_array_equal(arrays['water'][-n:].sum(1).astype(np.float32),result.W)
        np.testing.assert_array_equal(arrays['rain'][-n:].sum(1).astype(np.float32),result.P)
        np.testing.assert_array_equal(np.array([step['day'] for step in certificates[-n:]]),result.days)
        arrays['solved_days']=np.array([step['day'] for step in certificates])
        arrays['days']=result.days.copy();arrays['scored_indices']=np.arange(len(self.steps)-n,len(self.steps))
        return arrays,dict(solved_steps=len(self.steps),scored_steps=n,primer_steps=len(self.steps)-n,
            layer_equations_reconstructed=True,rain_components_reconstructed=True,
            result_float32_exact=True,maximum_absolute_residual_mm_day=float(np.abs(arrays['residual']).max()),
            units=dict(water='mm',layer_mass='relative dry column mass (reference101325Pa/g)',
                winds='m/s, projected right/up',upward_air='relative dry column mass/s, positive upward',
                lower_out='1/s',upper_out='1/s',vapor_face='mm*m/s, rightward/southward',
                rates='evaporation,drying,storm,rain,recycled,vertical_water,advection,diffusion,residual: mm/day'),
            scope='Actual simultaneous solved fields, all primer and scored steps; no transient storage equation')
