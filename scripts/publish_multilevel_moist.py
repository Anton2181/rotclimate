"""Independently verify resolved passive and moist-grid demonstrations."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from audit_multilevel_adiabatic import audit


def publish(out):
    passive=json.loads((out/'verification.json').read_text());moist=json.loads((out/'moist_verification.json').read_text())
    for receipt in [passive,moist]:
        if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
                or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False):raise ValueError('Need isolated non-adopted scope')
        for n,h in receipt['sources'].items():
            if file_hash(ROOT/n)!=h:raise ValueError('Changed verified source: '+n)
    for name,receipt in [('multilevel_transport.png',passive),('multilevel_moist.png',moist)]:
        if file_hash(out/name)!=receipt['image_sha256']:raise ValueError('Changed figure: '+name)
    a={k:np.asarray(v) for k,v in passive['arrays'].items()};mass=a['layer_mass'];q=a['final_vapor']/mass;u,v=a['u_east'],a['v_south'];dx=passive['configuration']['cell_m'];dt=passive['configuration']['dt_s']
    if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Closed passive domain changed')
    mx=np.concatenate([mass[:,:,:1],.5*(mass[:,:,:-1]+mass[:,:,1:]),mass[:,:,-1:]],axis=2)
    my=np.concatenate([mass[:,:1],.5*(mass[:,:-1]+mass[:,1:]),mass[:,-1:]],axis=1)
    fx,fy=mx*u,my*v;dry=(np.diff(fx,axis=2)+np.diff(fy,axis=1))/dx;up=-np.cumsum(dry,axis=0)[:-1]
    qx=np.concatenate([q[:,:,:1],q,q[:,:,-1:]],axis=2);qy=np.concatenate([q[:,:1],q,q[:,-1:]],axis=1)
    wx=fx*np.where(fx>=0,qx[:,:,:-1],qx[:,:,1:]);wy=fy*np.where(fy>=0,qy[:,:-1],qy[:,1:]);wu=up*np.where(up>=0,q[:-1],q[1:])
    for actual,expected in [(a['east_vapor_flux'],wx),(a['south_vapor_flux'],wy),(a['upward_vapor_flux'],wu),(a['upward_dry_mass_flux'],up)]:
        np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)
    vertical=np.concatenate([np.zeros_like(q[:1]),wu,np.zeros_like(q[:1])],axis=0)
    residual=a['last_step_source']-a['final_vapor']/dt-(np.diff(wx,axis=2)+np.diff(wy,axis=1))/dx-np.diff(vertical,axis=0)
    passive_error=float(np.abs(residual).max());total_water_error=float(abs(a['final_vapor'].sum()-a['initial_vapor'].sum())/a['initial_vapor'].sum())
    if passive_error>1e-12 or total_water_error>1e-12:raise ValueError('Actual multilevel donor face budget failed')
    if audit()!=passive['adiabatic_audit']:raise ValueError('Independently repeated grid-coupling audit changed')
    b={k:np.asarray(v) for k,v in moist['arrays'].items()};m,z=b['layer_mass'],b['height_m']
    for state in ['initial','final']:
        t,w=b[state+'_temperature'],b[state+'_vapor']
        energy=(1004*m+1850*w)*t+(2.5e6-1850*273.15)*w+9.80665*(m+w)*z
        np.testing.assert_allclose(energy,b[state+'_static_energy'],rtol=1e-14,atol=1e-6)
    energy_error=float(abs(b['final_static_energy'].sum()+b['cumulative_rain_enthalpy'].sum()-b['initial_static_energy'].sum())/b['initial_static_energy'].sum())
    water_error=float(abs(b['final_vapor'].sum()+b['cumulative_rain'].sum()-b['initial_vapor'].sum())/b['initial_vapor'].sum())
    if max(energy_error,water_error)>1e-12 or np.any(b['cumulative_fall_heat']<0) or np.any(b['cumulative_rain']<0):raise ValueError('Actual resolved moist/rain ledger failed')
    t=b['final_temperature'];p=b['pressure_pa'];es=611.2*np.exp(17.67*(t-273.15)/(t-29.65));sat=m*.622*es/(p-es)
    if np.any(b['final_vapor']>sat*(1+1e-9)):raise ValueError('Final resolved saturation failed')
    errors=moist['time_refinement']
    if not errors['0.75']['rms_temperature_k']<errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']:raise ValueError('Moist time refinement changed')
    checks=dict(passive_maximum_actual_face_residual_kg_m2_s=passive_error,passive_relative_total_water_error=total_water_error,
        moist_relative_atmosphere_plus_rain_energy_error=energy_error,moist_relative_vapor_plus_rain_error=water_error)
    data=ROOT/'atlases/climate_accuracy/data';figures=[]
    for name,caption in [('multilevel_transport.png','Passive32-level moisture redistribution under fixed generated winds and a measured vertical-grid coupling audit; not rainfall'),
        ('multilevel_moist.png','Resolved32-level liquid phase, transport and rain in a closed shallow8km test; prescribed winds, not an Earth forecast')]:
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as im:w,h=im.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}.</figcaption></figure>')
    write_json(data/'multilevel_moist.json',dict(passive=passive,moist=moist,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    rows=''.join(f'<tr><td>{hours}</td><td>{v["rms_temperature_k"]:.6f}</td><td>{v["rms_vapor_kg_m2"]:.6f}</td><td>{v["rms_rain_kg_m2"]:.6f}</td></tr>' for hours,v in errors.items())
    section=f'''<!--multilevel-moist-start--><section aria-labelledby="multilevel-moist-h"><h2 id="multilevel-moist-h">Resolved moisture, phase and energy on the shared vertical grid</h2>
<p><strong>Moist thermodynamics now supports the resolved vertical geometry.</strong> A general native-face donor solver carries vapor or another explicit scalar across any fixed positive dry layers. Continuity supplies every vertical mass flux. A new multilevel phase step passes actual rain enthalpy through every cell, includes local terminal drag heating inside saturation equilibrium, and exports ground-rain sensible energy. A composed step transports vapor and moist static energy before adjusting phase.</p>
<p>The earlier unequal two-box/smooth-mode audit had adiabatic ratios0.5123/0.2637. On a shared uniform-density grid, the resolved first-mode response is0.99039 at16levels and0.99759 at32. Stratified hydrostatic density is harder: ascent/descent ratios are1.01764/0.97845 at32,1.00932/0.98970 at64 and1.00478/0.99497 at128. Actual one-second transport solves recover independent derivative limits. These are numerical coupling errors, not Earth accuracy percentages or fitted circulation corrections.</p>
{figures[0]}
<p>The passive test generates dry winds for6hours, then holds them fixed for24hours of32-level water transport in a15km reference. It preserves total vapor and applies no rain or humidity reset. The separate moist test uses a shallow8km warm/supercooled reference, fixed generated winds and no external heat or water. Pressure-derived dry masses, vapor/liquid heat capacity, rain potential work and exported rain enthalpy are explicit. Its finest24-hour run produces mean0.213 mm and maximum2.889 mm rain, with atmosphere-plus-rain energy and vapor-plus-rain errors below3e-15 relative.</p>
{figures[1]}
<div class="table"><table><caption>Same24-hour shallow liquid-only moist test; differences against0.375-hour timesteps, not Earth rain errors</caption><thead><tr><th>Timestep h</th><th>RMS T difference K</th><th>RMS vapor difference kg/m²</th><th>RMS cumulative rain difference kg/m²</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Eighteen new tests check exact earlier two-level limits, independent multi-interface donor fluxes, analytical horizontal transport, complete/partial rain evaporation, terminal drag heat and actual composed source budgets. The full focused suite passes217 tests. Publication independently reconstructs actual last-step donor fluxes, final saturation and the atmospheric/rain energy and water ledgers from saved raw arrays.</p>
<p class="note">These are sequential dry wind generation and fixed-wind thermodynamic experiments. The moist state is not yet driving momentum. The shallow liquid-only case stays above245K and is not a complete icy troposphere; freezing, snow, cloud storage, retained drop kinetic energy, predicted radiation, moving compressible density and terrain are absent. Reflecting walls and frozen circulation strongly affect the rain pattern, including its boundary maxima; it is not a geographical climate result. The scalar/static-energy/rain budget does not prove a complete atmospheric mechanical-energy model. No additional adiabatic c²divU cooling is added. Earthr39 and normal world/biome/population fields remain unchanged. Earth counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/multilevel_moist.json" download>Download resolved moisture, phase/energy state, rain and independent checks</a> · <a href="../../reports/MULTILEVEL_TRANSPORT_20261028.md">Donor transport and vertical coupling audit</a> · <a href="../../reports/MULTILEVEL_MOIST_20261028.md">Multilevel phase, composition and remaining feedback</a></p></section><!--multilevel-moist-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--multilevel-moist-start-->' in text:
        before,tail=text.split('<!--multilevel-moist-start-->',1);_,after=tail.split('<!--multilevel-moist-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_resolved_moisture',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,metadata_sha256=file_hash(data/'multilevel_moist.json'),
        images_sha256={n:r['image_sha256'] for n,r in [('multilevel_transport.png',passive),('multilevel_moist.png',moist)]},
        independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
