"""Check harvest/fertility_regimes.py (vectorised, monthly bucket) against the scalar round-2 model
(daily dual ledger) on Rothamsted climatology for five regimes. Output recorded in
reports/FERTILITY_INTEGRATION_20261106.md."""
import sys, json, numpy as np
from calendar import monthrange
from pathlib import Path; ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import soil_fertility_common as C
from harvest.soil_fertility import Params, Season, simulate
from harvest.soil_water_dual import dual_soil_water
from harvest.fertility_regimes import equilibrium_yield, WHEAT_CURVE
sel=json.load(open(ROOT/'output/soil_fertility_round2_20261106/selection.json'))
base=Params(**sel['parameters'])
_,_,clim=C.monthly()
T=np.array([clim[m]['T'] for m in range(1,13)]); P=np.array([clim[m]['rain'] for m in range(1,13)]); E=np.array([clim[m]['et'] for m in range(1,13)])
A0=C.a0_mean('wheat'); YEARS=300
start=C.start_pools('rothamsted',0.0,28.8)
st=dict(dpm=start.dpm,rpm=start.rpm,bio=start.bio,hum=start.hum,dpm_n=start.dpm_n,rpm_n=start.rpm_n)
def scalar(seq, I, manure=0.0):
    # daily climatology weather -> dual ledger drainage, repeated
    days=[];rain=[];et=[];yrs=[]
    for y in range(YEARS):
        for m in range(12):
            nd=monthrange(2001,m+1)[1]; ev=[d for d in range(nd) if d%3==1]
            for d in range(nd): rain.append(P[m]/len(ev) if d in ev else 0.0); et.append(E[m]/nd); yrs.append((y,m+1))
    kcb=np.zeros(len(rain)); from harvest.soil_water_dual import kcb_curve
    idx={}; 
    for i,(y,m) in enumerate(yrs): idx.setdefault((y,m),i)
    ar=np.arange(len(rain))
    for y in range(1,YEARS):
        k=seq[y%len(seq)]
        if k=='crop':
            s=idx[(y-1,10)]+14; h=idx[(y,8)]+14; kcb=np.maximum(kcb,kcb_curve(ar,s,h))
        elif k=='clover':
            for mm in range(1,13):
                a=idx[(y,mm)]; nd=monthrange(2001,mm)[1]; kcb[a:a+nd]=np.maximum(kcb[a:a+nd],0.8 if 3<=mm<=10 else 0.3)
    led=dual_soil_water(np.array(rain),np.array(et),kcb,total_available=195.0,depletion_fraction=0.55,total_evaporable=1000*(0.335-0.1025)*0.1,readily_evaporable=9.5,initial_depletion=0.0)
    drain={}
    for i,(y,m) in enumerate(yrs): drain[(y,m)]=drain.get((y,m),0.0)+led.drainage[i]
    forcing=[dict(year=y,month=m,T=T[m-1],rain=P[m-1],et=E[m-1],drainage=drain[(y,m)]) for y in range(YEARS) for m in range(1,13)]
    seasons=[];events={}
    for y in range(1,YEARS):
        k=seq[y%len(seq)]
        if k=='crop':
            veg=C.months_between((y-1,10),(y,7))
            seasons.append(Season('cereal',(y,8),frozenset(C.months_between((y,3),(y,7))),frozenset(veg),A0,'w',C._curve(veg,C.CURVES['wheat'])))
            if manure>0: events.setdefault((y-1,10),[]).append(('fym',manure*C.FYM_C_PER_T,manure*C.FYM_N_PER_T))
        elif k=='clover':
            seasons.append(Season('clover',(y,12),frozenset(),frozenset(C.months_between((y,1),(y,12))),None,'c'))
            events.setdefault((y,10),[]).append(('residue',0.8,20.0))
            if seq[(y+1)%len(seq)]!='clover': events.setdefault((y,10),[]).append(('residue',2.0,19.0))
    p=Params(input_n=I,uptake_rate=base.uptake_rate,kappa=base.kappa,thermal_uptake=True,demand_curve=True)
    res=simulate(forcing,seasons,p,23.4,502.5,start=start,events=events)
    last=[s for s in res['seasons'] if s['harvest'][0]>=YEARS-30]
    g=[s['grain_t_ha'] for s in last if s['grain_t_ha'] is not None]
    return float(np.mean(g)), float(np.sum(g)/30), float(np.mean([v for (y,m),v in drain.items() if y>=YEARS-30])*12)
for name,seq,I,man in [('continuous I52.4',['crop'],52.4,0),('continuous I27.5',['crop'],27.5,0),('3-field fallow I27.5',['crop','crop','fallow'],27.5,0),('3-field clover I27.5',['crop','crop','clover'],27.5,0),('cont +5t FYM I27.5',['crop'],27.5,5.0)]:
    sc=scalar(seq,I,man)
    em=equilibrium_yield(T[:,None],P[:,None],E[:,None],np.array([7]),np.array([A0]),regime=seq,manure_t=man,input_n=I,uptake_rate=base.uptake_rate,kappa=base.kappa,season_bins=10,curve=WHEAT_CURVE,years=YEARS,report_years=30 if len(seq)!=2 else 30,start=st)
    print(f"{name:24s} scalar crop {sc[0]:.3f} land {sc[1]:.3f} (drain {sc[2]:.0f}) | emulator crop {em['per_cropped_ha'][0]:.3f} land {em['per_rotation_ha'][0]:.3f}")
