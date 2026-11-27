"""Pure decomposition of the existing single-column rainfall coefficient."""
import numpy as np
DAY=86400.


def components(W, saturation, dynamics, instability, threshold, tau_days, closure):
    """Return actual-state mm/day terms; does not mutate inputs or a model."""
    rh=W/saturation
    gate=np.clip((rh-threshold)/(1-threshold),0,2)**1.5
    base=dynamics*gate*instability/(tau_days*DAY)
    conv=closure['conv']*np.exp(11.4*(np.minimum(rh,1.5)-closure['r0']))*closure['fT']
    uncapped=conv.copy()
    cap=closure['cap']
    conv=np.where(cap>0,cap*np.tanh(conv/np.maximum(cap,1e-9)),conv)
    conv_rate=conv/(np.maximum(W,.1)*DAY)
    z_lcl=(20+closure['T']/5)*(100-100*np.clip(rh,0,1))
    attenuation=np.exp(-closure['evap']*np.maximum(z_lcl,0)/3000)
    overflow=np.divide(np.maximum(rh-1,0),rh,out=np.zeros_like(rh),where=rh>0)/DAY
    return dict(base=base*attenuation*W*DAY,convective=conv_rate*attenuation*W*DAY,
        overflow=overflow*W*DAY,RH=rh,humidity_gate=gate,evaporation_factor=attenuation,
        uncapped_convective_mm_day=uncapped,capped_convective_mm_day=conv)
