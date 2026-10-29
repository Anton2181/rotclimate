"""Verify actual parent/fine phase conservation and common-grid source work."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def verify(r,a):
    if r['actual_earth_integrations']!=0 or r['interactive_moist_feedback'] is not False or r['physics_or_atlas_adoption'] is not False:
        raise ValueError('Need isolated non-adopted phase-grid comparison')
    for n,h in r['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed verified source: '+n)
    g,cp,cv,lv,tzero=9.80665,1004.,1850.,2.5e6,273.15
    m=a['coarse_mass'];edges=a['coarse_edges_m'];z=.5*(edges[:-1]+edges[1:]);dz=np.diff(edges);cells=int(np.prod(m.shape[1:]));total=m[:,0,0].sum()
    def energy(t,w,m,z):return (cp*m+cv*w)*(t-tzero)+lv*w+g*(m+w)*z[:,None,None]
    before=energy(a['initial_temperature'],a['initial_vapor'],m,z);weight=m/a['coarse_stability'][:,None,None]
    # Independent original 512-layer profile and its actual parent energy/water.
    f=np.linspace(0,8000,513);zf=.5*(f[:-1]+f[1:]);tf=300-.006*zf
    pf=101325*(1-.006*f/300)**(g/(287.05*.006));mf=np.broadcast_to((-np.diff(pf)/g)[:,None,None],(512,)+m.shape[1:])
    p=101325*(tf/300)**(g/(287.05*.006));es=611.2*np.exp(17.67*(tf-273.15)/(tf-29.65))
    y,x=np.mgrid[:m.shape[1],:m.shape[2]];pulse=np.exp(-((x-(m.shape[2]-1)/2)/3)**2-((y-(m.shape[1]-1)/2)/2.5)**2)
    rh=.8+.28*np.exp(-((zf-3500)/1800)**2)[:,None,None]*pulse
    wf=mf*(.622*es/(p-es))[:,None,None]*rh;tf=np.broadcast_to(tf[:,None,None],mf.shape)
    aggregate=lambda v:v.reshape((16,32)+m.shape[1:]).sum(1)
    np.testing.assert_allclose(m,aggregate(mf),rtol=1e-12,atol=1e-10)
    np.testing.assert_allclose(a['initial_vapor'],aggregate(wf),rtol=1e-12,atol=1e-10)
    np.testing.assert_allclose(before,aggregate(energy(tf,wf,mf,zf)),rtol=1e-12,atol=1e-6)
    virtual=lambda t,w,m:t*(1+w/(.622*m))/(1+w/m)
    max_parent_e=0.;max_phase_e=0.;max_water=0.;wave_work=0.;case_checks={}
    null=(-1.)**np.arange(16)*dz;null*=np.sqrt(total/np.dot(weight[:,0,0],null**2))
    for key,case in r['cases'].items():
        factor=int(key);prefix='f'+key+'_';fm=a[prefix+'fine_mass'];fe=a[prefix+'fine_edges'];fz=.5*(fe[:-1]+fe[1:])
        fi_t,fi_w=a[prefix+'fine_initial_temperature'],a[prefix+'fine_initial_vapor'];ft,fw=a[prefix+'fine_temperature'],a[prefix+'fine_vapor']
        ag=lambda v:v.reshape((16,factor)+m.shape[1:]).sum(1)
        np.testing.assert_allclose(ag(fm),m,rtol=1e-12,atol=1e-10)
        parent_error=float(np.max(abs(ag(energy(fi_t,fi_w,fm,fz))-before))/np.max(abs(before)));max_parent_e=max(max_parent_e,parent_error)
        np.testing.assert_allclose(ag(fi_w),a['initial_vapor'],rtol=1e-12,atol=1e-10)
        current=energy(a[prefix+'temperature'],a[prefix+'vapor'],m,z)
        np.testing.assert_allclose(current,ag(energy(ft,fw,fm,fz)),rtol=1e-12,atol=1e-6)
        np.testing.assert_allclose(a[prefix+'vapor'],ag(fw),rtol=1e-12,atol=1e-10)
        column_e=current.sum(0)+a[prefix+'ground_rain_enthalpy']-before.sum(0)
        column_w=a[prefix+'vapor'].sum(0)+a[prefix+'ground_rain']-a['initial_vapor'].sum(0)
        phase_error=float(np.max(abs(column_e))/np.max(abs(before.sum(0))));water_error=float(np.max(abs(column_w))/np.max(a['initial_vapor'].sum(0)))
        max_phase_e=max(max_phase_e,phase_error);max_water=max(max_water,water_error)
        p=a[prefix+'fine_pressure'];es=611.2*np.exp(17.67*(ft-273.15)/(ft-29.65));saturation=fm*.622*es/(p-es)
        if np.any(fw>saturation*(1+1e-9)):raise ValueError('Actual fine phase saturation failed')
        db=g*(virtual(a[prefix+'temperature'],a[prefix+'vapor'],m)-virtual(a['initial_temperature'],a['initial_vapor'],m))/(300-.006*z)[:,None,None]
        np.testing.assert_allclose(a[prefix+'buoyancy_increment'],db,rtol=1e-10,atol=1e-14)
        ape=float(.5*np.sum(weight*db**2)/(total*cells));amplitude=np.sum(weight*null[:,None,None]*db,axis=0)/total
        invisible=float(.5*np.mean(amplitude**2))
        np.testing.assert_allclose(case['coarse_source_available_energy']['total_thermal_available_energy_m2_s2'],ape,rtol=1e-11)
        np.testing.assert_allclose(case['coarse_source_available_energy']['pressure_invisible_available_energy_m2_s2'],invisible,rtol=1e-10)
        case_checks[key]=dict(actual_parent_relative_energy_error=parent_error,actual_phase_relative_energy_error=phase_error,
            actual_column_relative_water_error=water_error,actual_coarse_source_available_energy_m2_s2=ape)
        if factor!=32:
            for field,label in [('temperature','rms_coarse_temperature_k'),('vapor','rms_coarse_vapor_kg_m2')]:
                rms=float(np.sqrt(np.mean((a[prefix+field]-a['f32_'+field])**2)))
                np.testing.assert_allclose(case['difference_vs_factor32'][label],rms,rtol=1e-12)
    for key,wave in r['waves'].items():
        u,v,b=a['wave'+key+'_u'],a['wave'+key+'_v'],a['wave'+key+'_b']
        if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Wave walls changed')
        face_b=.5*(b[:-1]+b[1:]);pressure=np.concatenate([np.zeros_like(b[:1]),np.cumsum(face_b*np.diff(z)[:,None,None],axis=0)])
        pressure-=np.sum(m*pressure,axis=0,keepdims=True)/total
        np.testing.assert_allclose(a['wave'+key+'_pressure'],pressure,rtol=1e-10,atol=1e-12)
        face_mass=m[:,0,0,None,None]
        mechanical=float(.5*(np.sum(face_mass*u[:,:,1:-1]**2)+np.sum(face_mass*v[:,1:-1]**2)+np.sum(weight*b*b))/(total*cells))
        q=a['f'+key+'_buoyancy_increment']/r['configuration']['source_duration_s']
        work=float(np.sum(weight*q*a['wave'+key+'_source_integral'])/(total*cells))
        wave_work=max(wave_work,abs(mechanical-work)/max(abs(work),abs(mechanical),1e-30))
        np.testing.assert_allclose(wave['history'][-1]['kinetic_plus_thermal_available_energy_m2_s2'],mechanical,rtol=1e-12)
        if key!='32':
            for field in ['u','v','pressure','b']:
                rms=float(np.sqrt(np.mean((a['wave'+key+'_'+field]-a['wave32_'+field])**2)))
                np.testing.assert_allclose(wave['difference_vs_factor32'][field],rms,rtol=1e-12)
    if max(max_parent_e,max_phase_e,max_water,wave_work)>1e-10:raise ValueError('Actual nested/source-work budget failed')
    return dict(maximum_parent_relative_static_energy_error=max_parent_e,maximum_phase_relative_column_energy_error=max_phase_e,
        maximum_phase_relative_column_water_error=max_water,maximum_dry_energy_vs_actual_source_work_relative_error=wave_work,
        cases=case_checks,scope='Separate conservative nested phase and dry quadratic source/work ledgers, not a full coupled moist energy law')


def publish(out):
    r=json.loads((out/'verification.json').read_text())
    if file_hash(out/'fields.npz')!=r['raw_fields_sha256'] or file_hash(out/'sublayer_phase.png')!=r['image_sha256']:raise ValueError('Changed raw fields or image')
    with np.load(out/'fields.npz') as data:checks=verify(r,{k:data[k] for k in data.files})
    dest=ROOT/'atlases/climate_accuracy/data'
    shutil.copyfile(out/'sublayer_phase.png',dest/'sublayer_phase.png');shutil.copyfile(out/'fields.npz',dest/'sublayer_phase_fields.npz')
    write_json(dest/'sublayer_phase.json',dict(experiment=r,independent_publication_checks=checks,raw_fields='sublayer_phase_fields.npz',publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'sublayer_phase.png') as im:width,height=im.size
    rows=''.join(f'<tr><td>{k}</td><td>{v["fine_levels"]}</td><td>{v["difference_vs_factor32"]["rms_coarse_temperature_k"]:.8f}</td><td>{v["coarse_source_available_energy"]["total_thermal_available_energy_m2_s2"]:.8f}</td></tr>' for k,v in r['cases'].items() if k!='32')
    section=f'''<!--sublayer-phase-start--><section aria-labelledby="sublayer-phase-h"><h2 id="sublayer-phase-h">Conservative phase sublayers on a fixed circulation grid</h2>
<p><strong>Fine condensation and rain evaporation can be resolved without adding momentum levels.</strong> The new nested operator reconstructs fine temperature/vapor while preserving every parent cell’s dry mass, water and gas-plus-potential energy. Fine liquid phase and rain enthalpy use the existing conservative kernel. Restriction diagnoses an energy-equivalent coarse temperature and returns the complete fine state for retention.</p>
<p>A fixed16-cell parent column is tested with1/2/4/8/16/32 phase sublayers per cell. On the same coarse observables, the RMS temperature difference against32 sublayers falls from0.002984 K for one phase cell to0.0000342 K with eight sublayers. The represented source available-energy difference falls from about12.19% to0.095%. These are numerical comparisons within one declared reconstruction, not Earth errors or proof that the512-layer comparison is exact.</p>
<figure><a href="data/sublayer_phase.png"><img src="data/sublayer_phase.png" width="{width}" height="{height}" loading="lazy" alt="Conservative phase sublayer convergence on a common16-cell parent column, retained coarse temperature profiles and six-hour dry pressure difference"></a><figcaption>One common parent water/energy state; limited-linear sublayer shapes; unchanged16-level dry circulation. Subgrid structure is a stated reconstruction assumption.</figcaption></figure>
<div class="table"><table><caption>Common coarse temperature differences versus32 sublayers, with source available energy on the same16 cells</caption><thead><tr><th>Sublayers</th><th>Fine phase levels</th><th>RMS T difference K</th><th>Coarse source APE m²/s²</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Three otherwise identical six-hour dry runs apply the1/8/32-sublayer virtual-buoyancy pulses for one hour. All use2.5-minute timesteps and the same16-level dynamics, for432 dry steps. Independent publication reconstructs original parent water/energy, fine/coarse phase budgets, saturation, virtual forcing, pressure and actual source-work integrals from raw arrays. Ten new tests bring the focused suite to259 passes.</p>
<p class="note">The earlier16% change in native-grid source available energy includes newly represented vertical variance; it must not all be interpreted as phase-solver error. This comparison uses fixed coarse observables. Energy-equivalent means can exceed a single-cell saturation curve even when all retained fine cells are valid: coarse humidity is not clipped and no second coarse condensation is imposed. Retain the fine state; reconstructing it every timestep introduces mixing. This is fixed-pressure warm/supercooled liquid-only phase and a prescribed source for dry dynamics, with separate static-energy and quadratic available-energy ledgers. Interactive moist transport/circulation, ice, radiation, terrain and compressible dynamics remain absent. Earthr39 and all normal world/biome/population fields remain unchanged; zero new Earth integrations or rainfall gain. Counters remain1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/sublayer_phase.json" download>Download nested-phase results, provenance and independent checks</a> · <a href="data/sublayer_phase_fields.npz">Raw fine/coarse fields and dry source-work integrals (NumPy)</a> · <a href="../../reports/SUBLAYER_PHASE_20261029.md">Conservative reconstruction, retained state and remaining coupling</a></p></section><!--sublayer-phase-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';s=page.read_text()
    if '<!--sublayer-phase-start-->' in s:
        before,tail=s.split('<!--sublayer-phase-start-->',1);_,after=tail.split('<!--sublayer-phase-end-->',1);s=before+section+after
    else:s=s.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(s)
    result=dict(status='published_isolated_conservative_phase_sublayers',actual_earth_integrations=0,interactive_moist_feedback=False,
        physics_or_atlas_adoption=False,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__)),
        metadata_sha256=file_hash(dest/'sublayer_phase.json'),image_sha256=r['image_sha256'],raw_fields_sha256=r['raw_fields_sha256'])
    write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
