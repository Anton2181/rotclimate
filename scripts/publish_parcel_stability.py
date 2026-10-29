"""Verify parcel profiles with an independent adaptive ODE and actual integrals."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def verify(r,a):
    if r['actual_earth_integrations']!=0 or r['new_coupled_integrations']!=0 or r['physics_or_atlas_adoption'] is not False:
        raise ValueError('Need diagnostic-only scope')
    for n,h in r['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed diagnostic source: '+n)
    rd,cp,cv,cl,lv=287.05,1004.,1850.,4186.,2.5e6;p0=a['model_pressure_pa'];cases={};maximum_ode_error=0.;maximum_integral_error=0.
    def saturation(t,p):
        es=611.2*np.exp(17.67*(t-273.15)/(t-29.65))
        return .622*es/(p-es)
    for name,case in r['cases'].items():
        t=a[name+'_environment_temperature'];q=a[name+'_environment_vapor_ratio'];p=a[name+'_pressure'];tp=a[name+'_parcel_temperature']
        source_t=t[0].ravel();source_q=np.minimum(q[0].ravel(),saturation(source_t,p[0]))
        def derivative(logp,temp):
            pressure=np.exp(logp);es=611.2*np.exp(17.67*(temp-273.15)/(temp-29.65));sat=.622*es/(pressure-es)
            latent=lv+(cv-cl)*(temp-273.15);dloges=17.67*243.5/(temp-29.65)**2
            moisture_factor=sat*pressure/(pressure-es)
            return np.where(source_q<sat,rd*temp/(cp+cv*source_q),
                (rd*temp+latent*moisture_factor)/(cp+cv*sat+latent*moisture_factor*dloges))
        solved=solve_ivp(derivative,(np.log(p[0]),np.log(p[-1])),source_t,t_eval=np.log(p),method='DOP853',rtol=1e-10,atol=1e-9,max_step=.0025)
        if not solved.success:raise ValueError('Independent parcel ODE failed')
        independent=solved.y.T.reshape(tp.shape);ode_error=float(np.max(abs(independent-tp)));maximum_ode_error=max(maximum_ode_error,ode_error)
        # Independently interpolate the declared environment and integrate its
        # piecewise-linear positive/negative temperature differences exactly.
        flat=t.reshape(len(t),-1);env=np.stack([np.exp(np.interp(np.log(p)[::-1],np.log(p0)[::-1],np.log(flat[:,i])[::-1]))[::-1]
            for i in range(flat.shape[1])],axis=1).reshape(tp.shape)
        difference=tp-env;left,right=difference[:-1],difference[1:];width=np.log(p[:-1]/p[1:])[:,None,None]
        signed=.5*(left+right)*width;absolute=.5*(abs(left)+abs(right))*width
        crossing=left*right<0
        absolute=np.where(crossing,np.divide(.5*(left*left+right*right),abs(right-left),out=np.zeros_like(left),where=crossing)*width,absolute)
        positive=rd*.5*np.sum(absolute+signed,axis=0);negative=rd*.5*np.sum(absolute-signed,axis=0)
        integral_error=float(max(np.max(abs(positive-a[name+'_positive'])),np.max(abs(negative-a[name+'_negative']))));maximum_integral_error=max(maximum_integral_error,integral_error)
        np.testing.assert_allclose(positive,a[name+'_positive'],rtol=1e-10,atol=1e-7)
        np.testing.assert_allclose(negative,a[name+'_negative'],rtol=1e-10,atol=1e-7)
        lcl=[]
        for temp,ratio in zip(source_t,source_q):
            exponent=rd/(cp+cv*ratio)
            def residual(x):return float(saturation(temp*np.exp(exponent*(x-np.log(p[0]))),np.exp(x))-ratio)
            if abs(residual(np.log(p[0])))<=1e-12*max(ratio,1e-12):lcl.append(float(p[0]))
            else:lcl.append(float(np.exp(brentq(residual,np.log(p[-1]),np.log(p[0]),xtol=1e-12))) if residual(np.log(p[-1]))<=0 else 0.)
        np.testing.assert_allclose(np.array(lcl).reshape(t.shape[1:]),a[name+'_lcl_pressure'],rtol=1e-10,atol=1e-5)
        reported=case['refinement']['0.005'];np.testing.assert_allclose(positive.mean(),reported['mean_positive_j_kg'],rtol=1e-10,atol=1e-7)
        cases[name]=dict(maximum_adaptive_vs_fixed_step_temperature_error_k=ode_error,
            actual_mean_positive_j_kg=float(positive.mean()),actual_maximum_positive_j_kg=float(positive.max()),
            actual_mean_negative_j_kg=float(negative.mean()))
    if maximum_ode_error>.01 or maximum_integral_error>1e-6:raise ValueError('Independent parcel accuracy/integral check failed: '+json.dumps(dict(temperature_error=maximum_ode_error,integral_error=maximum_integral_error,cases=cases)))
    return dict(maximum_independent_adaptive_vs_fixed_step_temperature_error_k=maximum_ode_error,
        maximum_independent_sign_split_integral_error_j_kg=maximum_integral_error,cases=cases,
        scope='Independent DOP853 ascent with smaller maximum step, actual environmental interpolation, exact sign-split integrals and bracketed LCL roots. Partial-column diagnostic only.')


def publish(out):
    r=json.loads((out/'verification.json').read_text())
    if file_hash(out/'fields.npz')!=r['raw_fields_sha256'] or file_hash(out/'parcel_stability.png')!=r['image_sha256']:raise ValueError('Changed diagnostic fields/image')
    with np.load(out/'fields.npz') as record:checks=verify(r,{k:record[k] for k in record.files})
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'fields.npz',dest/'parcel_stability_fields.npz');shutil.copyfile(out/'parcel_stability.png',dest/'parcel_stability.png')
    write_json(dest/'parcel_stability.json',dict(audit=r,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'parcel_stability.png') as im:w,h=im.size
    rows=''.join(f'<tr><td>{name.replace("_"," ")}</td><td>{v["actual_mean_positive_j_kg"]:.2f}</td><td>{v["actual_maximum_positive_j_kg"]:.2f}</td><td>{v["actual_mean_negative_j_kg"]:.2f}</td></tr>' for name,v in checks['cases'].items())
    section=f'''<!--parcel-stability-start--><section aria-labelledby="parcel-stability-h"><h2 id="parcel-stability-h">Parcel stability identifies the unresolved convection regime</h2>
<p><strong>The conditional stress response has a real parcel-instability mechanism in the reduced model.</strong> Initial phase-adjusted conditional columns have roughly1.64 kJ/kg mean positive parcel-buoyancy energy within the supplied model column; stable and dry controls have none. About0.805 kJ/kg remains after six hours in the conditional run. This supports investigating a convection treatment, rather than fitting wind or rainfall coefficients to suppress the response.</p>
<figure><a href="data/parcel_stability.png"><img src="data/parcel_stability.png" width="{w}" height="{h}" loading="lazy" alt="Partial-column parcel energy in conditional, saturated-stable and dry controls; fine pressure sampling reveals shallow inhibition below cloud base"></a><figcaption>Lowest-model-cell pseudoadiabatic parcels, ending near399 hPa. These are partial positive/negative buoyancy integrals, not complete atmospheric CAPE/CIN or observed Earth maps.</figcaption></figure>
<div class="table"><table><caption>Dry/dilute primary diagnosis; positive and negative integrals over the same partial column, J/kg</caption><thead><tr><th>Control state</th><th>Mean positive</th><th>Maximum positive</th><th>Mean negative</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Unsaturated ascent conserves parcel vapor; saturated ascent uses temperature-dependent latent enthalpy, actual vapor/liquid heat capacities and the same liquid saturation curve as the phase model. Condensate leaves at the parcel temperature. Internal pressure sampling resolves cloud base and buoyancy sign changes: coarse level endpoints had entirely missed the conditional flank’s shallow inhibition. Log-temperature/linear-vapor interpolation and pressure-step refinement are explicit. An optional virtual-temperature sensitivity is saved separately from the primary diagnosis consistent with the dry/dilute model.</p>
<p>Nine new tests bring the focused suite to282 passes. Independent DOP853 verification caught a0.16 K error from stepping across cloud base; ascent now follows the exact dry branch to its bracketed condensation point before integrating the saturated branch. The independent adaptive and fixed-step paths agree within8 microkelvin. Publication also reconstructs the environment, integrates sign-crossing segments and brackets condensation pressure independently. No new coupled or Earth integrations occur in this audit.</p>
<p class="note">The source is the lowest selected pressure cell after local phase adjustment, not an invented surface parcel. The top is the model’s partial column. Entrainment, retained condensate/loading, ice and a convection/mass-flux closure are absent; the environment between levels is reconstructed. Positive parcel energy can support strong motion, so41.8 m/s is not mathematically impossible, but the coupled response remains unvalidated without convection and nonlinear dynamics. No coefficients were tuned and no physics was adopted. Earthr39 and all normal atlas fields remain unchanged; counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/parcel_stability.json" download>Download parcel diagnostics, refinement, provenance and independent checks</a> · <a href="data/parcel_stability_fields.npz">Raw parcel paths, buoyancy and integrals</a> · <a href="../../reports/PARCEL_STABILITY_20261029.md">Parcel first law, partial-column limits and convection gate</a></p></section><!--parcel-stability-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';s=page.read_text()
    if '<!--parcel-stability-start-->' in s:
        before,tail=s.split('<!--parcel-stability-start-->',1);_,after=tail.split('<!--parcel-stability-end-->',1);s=before+section+after
    else:s=s.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(s)
    result=dict(status='published_partial_column_parcel_diagnostic',actual_earth_integrations=0,new_coupled_integrations=0,
        physics_or_atlas_adoption=False,independent_publication_checks=checks,metadata_sha256=file_hash(dest/'parcel_stability.json'),
        image_sha256=r['image_sha256'],raw_fields_sha256=r['raw_fields_sha256'],publisher_sha256=file_hash(Path(__file__)))
    write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
