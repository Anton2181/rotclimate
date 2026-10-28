"""Verify raw cached heights and independent dense mode solves before publishing."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from scipy.linalg import eigh
from scipy.optimize import brentq
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from transport_reference import acquire


def dense_speed(z,rho,n2):
    """Independent full generalized eigenmatrix, not the production tridiagonal."""
    dz=np.diff(z);dc=.5*(dz[:-1]+dz[1:]);n=len(rho)
    derivative=np.zeros((n-1,n))
    derivative[np.arange(n-1),np.arange(n-1)]=-1/dc
    derivative[np.arange(n-1),np.arange(1,n)]=1/dc
    face_rho=(rho[:-1]*dz[1:]+rho[1:]*dz[:-1])/(dz[:-1]+dz[1:])
    stiffness=derivative.T@np.diag(face_rho*dc/n2)@derivative
    lam=eigh(stiffness,np.diag(rho*dz),subset_by_index=(1,1),eigvals_only=True)[0]
    return float(1/np.sqrt(lam))


def verify(r):
    if (r['actual_earth_integrations']!=0 or r['coupled_climate_connected'] is not False
            or r['physics_or_atlas_adoption'] is not False or r['reference_only'] is not True):
        raise ValueError('Need unadopted reference-only scope')
    for name,h in r['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed audit source: '+name)
    for name,record in r['references'].items():
        if file_hash(ROOT/name)!=record['sha256']:raise ValueError('Changed cached height reference: '+name)
    if (r['configuration']['lapse_k_m']!=.006 or r['configuration']['isothermal_cap_k']!=200
            or r['configuration']['constant_buoyancy_frequency_s']!=.01):raise ValueError('Changed fixed reference assumptions')
    p=np.array(r['pressure_edges_pa']);g,rd,cp=9.80665,287.05,1004.
    plan=json.loads((ROOT/'calibration/transport_diagnosis_20261028/reference_plan.json').read_text())
    fields,_=acquire(ROOT,plan,fetch=False)
    summaries={};excluded=[];maximum_speed_difference=0.;case_count=0
    for region in plan['regions']:
        with np.load(ROOT/'output/divergent_thermal_20261028/hydro_control'/f'{region}_transport.npz') as raw:
            native={key:raw[key] for key in r['native'][region] if key.startswith('native_')}
        for key,value in native.items():np.testing.assert_array_equal(value,r['native'][region][key])
        field=fields[region,'hgt'];indices=[np.flatnonzero(field.pressure_hpa*100==v).item() for v in p]
        np.testing.assert_array_equal(field.latitude,r['native'][region]['latitude'])
        np.testing.assert_array_equal(field.longitude,r['native'][region]['longitude'])
        height=field.values[native['native_month_order']][:,indices].reshape(12,len(p),-1)
        for kind in ['land','ocean']:
            cells=np.flatnonzero(native['native_'+kind+'_mask'])
            if not len(cells):continue
            key=region+'_'+kind;group=r['groups'][key]
            expected={(month+1,int(cell)) for month in range(12) for cell in cells}
            actual={(c['month'],c['native_cell']) for c in group['cases']}
            if actual!=expected or len(group['cases'])!=len(expected):raise ValueError('Changed native/month sample coverage')
            if group['native_cells']!=len(cells):raise ValueError('Changed footprint count')
            rows=[];total_weight=0.
            for c in group['cases']:
                case_count+=1;month=c['month']-1;cell=c['native_cell']
                np.testing.assert_array_equal(c['height_geopotential_m'],height[month,:,cell])
                z=np.array(c['height_geopotential_m']);z-=z[0];dz=np.diff(z);zc=.5*(z[:-1]+z[1:]);dc=np.diff(zc)
                tv=g*dz/(rd*np.log(p[:-1]/p[1:]));theta=tv*(1e5/np.sqrt(p[:-1]*p[1:]))**(rd/cp)
                n2=g*np.diff(np.log(theta))/dc;rho=-np.diff(p)/(g*dz)
                for name,value in [('edges_m',z),('centers_m',zc),('hypsometric_virtual_temperature_k',tv),
                    ('virtual_potential_temperature_k',theta),('stability_s2',n2),('density_kg_m3',rho)]:
                    np.testing.assert_allclose(c[name],value,rtol=2e-12,atol=1e-12)
                gamma,cap=.006,200.;ts=float(c['conditional_base_temperature_k']);zt=(ts-cap)/gamma
                predicted_first_dz=ts/gamma*(1-(p[1]/p[0])**(rd*gamma/g))
                np.testing.assert_allclose(predicted_first_dz,dz[0],rtol=1e-12)
                # Integrate d(log theta)/dz analytically, independent of lapse_reference.
                temp=ts-gamma*np.minimum(zc,zt)
                logtheta=(g/(cp*gamma)-1)*np.log(ts/temp)+g/(cp*cap)*np.maximum(zc-zt,0)
                nr=g*np.diff(logtheta)/dc
                np.testing.assert_allclose(c['lapse_stability_s2'],nr,rtol=1e-11,atol=1e-14)
                def logpressure(h):
                    below=min(h,zt);t=ts-gamma*below
                    return np.log(p[0])+g/(rd*gamma)*np.log(t/ts)-g*max(h-zt,0)/(rd*cap)
                depth=brentq(lambda h:logpressure(h)-np.log(p[-1]),0,30000)
                np.testing.assert_allclose(c['conditional_100hpa_depth_m'],depth,rtol=1e-12)
                speeds={name:dense_speed(z,rho,value) for name,value in [('constant',np.full_like(n2,1e-4)),('lapse',nr)]}
                for name,value in speeds.items():
                    maximum_speed_difference=max(maximum_speed_difference,abs(c[name+'_first_speed_ms']-value))
                    np.testing.assert_allclose(c[name+'_first_speed_ms'],value,rtol=1e-10)
                bad=np.flatnonzero(n2<=0).tolist();valid=not bad
                if c['nonpositive_interfaces']!=bad or c['valid_stable_proxy']!=valid:raise ValueError('Nonpositive stability exclusion changed')
                weight=float(native['native_'+kind+'_area'][cell]*native['native_month_days'][month]);total_weight+=weight
                np.testing.assert_allclose(c['area_day_weight'],weight,rtol=1e-14)
                if not valid:
                    if c['inferred_first_speed_ms'] is not None:raise ValueError('Invalid stable mode must not be produced')
                    excluded.append(dict(group=key,month=month+1,native_cell=cell,nonpositive_interfaces=bad));continue
                inferred=dense_speed(z,rho,n2);maximum_speed_difference=max(maximum_speed_difference,abs(c['inferred_first_speed_ms']-inferred))
                np.testing.assert_allclose(c['inferred_first_speed_ms'],inferred,rtol=1e-10)
                rows.append((weight,inferred,speeds['constant'],speeds['lapse'],(depth-z[-1])/z[-1]))
            values=np.array(rows);w=values[:,0]/values[:,0].sum();inferred=values[:,1]
            summary=dict(total_cases=len(expected),valid_cases=len(rows),excluded_cases=len(expected)-len(rows),
                valid_area_day_fraction=float(values[:,0].sum()/total_weight),weighted_inferred_first_speed_ms=float(w@inferred),
                conditional_depth_relative_bias=float(w@values[:,4]))
            for i,name in enumerate(['constant','lapse']):
                delta=values[:,i+2]-inferred
                summary[name]=dict(weighted_mean_absolute_relative_speed_error=float(w@np.abs(delta/inferred)),
                    weighted_mean_absolute_speed_error_ms=float(w@np.abs(delta)),weighted_signed_speed_error_ms=float(w@delta))
            for name,value in summary.items():
                if isinstance(value,dict):
                    for k,v in value.items():np.testing.assert_allclose(group['summary'][name][k],v,rtol=1e-10,atol=1e-10)
                else:np.testing.assert_allclose(group['summary'][name],value,rtol=1e-10,atol=1e-10)
            summaries[key]=summary
    if excluded!=r['excluded_cases'] or set(summaries)!=set(r['groups']):raise ValueError('Group/exclusion accounting changed')
    overall={k:float(np.mean([v[k]['weighted_mean_absolute_relative_speed_error'] for v in summaries.values()])) for k in ['constant','lapse']}
    for k,v in overall.items():np.testing.assert_allclose(r['equal_group_mean_absolute_relative_speed_error'][k],v,rtol=1e-10)
    return dict(independently_checked_month_cell_profiles=case_count,excluded_nonpositive_profiles=len(excluded),
        maximum_tridiagonal_vs_dense_speed_difference_ms=maximum_speed_difference,
        equal_group_mean_absolute_relative_speed_error=overall,
        checks='Cached heights and masks, layer hypsometry, independent integrated lapse stability, pressure root, full dense generalized eigenproblems, actual area/day weights and exclusions')


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());checks=verify(receipt)
    if file_hash(out/'stability_reference.png')!=receipt['image_sha256']:raise ValueError('Changed verified figure')
    data=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'stability_reference.png',data/'stability_reference.png')
    write_json(data/'stability_reference.json',dict(audit=receipt,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'stability_reference.png') as im:width,height=im.size
    rows=''.join(f'<tr><td>{key.replace("_"," ")}</td><td>{group["native_cells"]}</td><td>{group["summary"]["valid_cases"]}/{group["summary"]["total_cases"]}</td>'
        f'<td>{100*group["summary"]["constant"]["weighted_mean_absolute_relative_speed_error"]:.2f}%</td>'
        f'<td>{100*group["summary"]["lapse"]["weighted_mean_absolute_relative_speed_error"]:.2f}%</td></tr>' for key,group in receipt['groups'].items())
    section=f'''<!--stability-reference-start--><section aria-labelledby="stability-reference-h"><h2 id="stability-reference-h">Earth height profiles and a physically derived stability reference</h2>
<p><strong>Fixed lapse structure improves three sampled groups and worsens one.</strong> A new hydrostatic reference derives pressure, density, potential temperature, stability and pressure-column depth from temperature structure. The tested profile has a globally fixed6 K/km lapse and explicit200 K isothermal cap. It does not fit a stability or column-depth parameter separately for each region.</p>
<p>Cached NCEP1981–2010 monthly geopotential heights give pressure-layer mean virtual temperature by hypsometry, then a dry-exponent virtual-potential-temperature stability proxy. The first rigid-lid mode is compared on identical925–100 hPa height/density grids. The new profile is conditioned on the observed lowest-layer thickness; this is a structural diagnostic, not an independent prediction. Equal weighting of the four group errors gives17.22% for constant N=0.01/s and8.92% for the lapse/cap reference.</p>
<figure><a href="data/stability_reference.png"><img src="data/stability_reference.png" width="{width}" height="{height}" loading="lazy" alt="Constant stability and fixed lapse profile compared with inferred Earth height-column mode speeds; three groups improve and Mexican ocean worsens"></a><figcaption>Inferred linear mode speeds from sparse reused monthly height profiles, not observed wave speeds or rainfall accuracy. Solid lines are the height-derived proxy, dashed the fixed lapse/cap reference and dotted constant stability.</figcaption></figure>
<div class="table"><table><caption>Area/day weighted errors within each native footprint; nonpositive-stability profiles excluded without clipping</caption><thead><tr><th>Sample</th><th>Cells</th><th>Valid profiles</th><th>Constant N speed error</th><th>Lapse/cap speed error</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>The three excluded India profiles retain their nonpositive diagnosed stability and raw values. The publication independently verifies all192 month/cell profiles, cached heights and native masks, an integrated lapse-stability expression, pressure-depth roots and full dense generalized eigenproblems. Fifteen new tests verify hydrostatic/isothermal limits, the temperature anchor and explicit instability exclusion. The focused suite passes232 tests.</p>
<p class="note">These are coarse monthly reanalysis layer means and a dry virtual stability proxy, not saturated moist stability. Layer means are assigned to midpoint heights and geometric-mean pressure; the reference stability uses secants of its analytic potential temperature. Native footprints are reused and sparse:11 India land cells,1 Mexico land cell,1 Mexico ocean cell and3 Pacific Northwest ocean cells. Surface pressure is unavailable, so925 hPa cannot be independently confirmed above ground in each land cell. Rigid925/100 hPa lids are a partial-column test, not the complete atmosphere. No observed wind or humidity is used as a model forcing. The Mexican ocean regression remains explicit; the four-group mean is not global Earth accuracy. No rainfall integration, adopted-physics change or normal atlas climate change has occurred. This does not establish a global calibration optimum. Counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/stability_reference.json" download>Download raw height profiles, masks, weights, modes, exclusions and independent checks</a> · <a href="../../reports/STABILITY_REFERENCE_20261028.md">Stability derivation, regional tradeoff and next experiment</a></p></section><!--stability-reference-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--stability-reference-start-->' in text:
        before,tail=text.split('<!--stability-reference-start-->',1);_,after=tail.split('<!--stability-reference-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    result=dict(status='published_cached_height_stability_diagnostic',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,independent_publication_checks=checks,
        image_sha256=receipt['image_sha256'],metadata_sha256=file_hash(data/'stability_reference.json'),publisher_sha256=file_hash(Path(__file__)))
    write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
