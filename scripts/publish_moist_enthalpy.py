"""Publish verified water-capacity and precipitation-enthalpy comparison."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def publish(out):
    path=out/'verification.json';receipt=json.loads(path.read_text())
    if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
            or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False):
        raise ValueError('Need isolated manufactured scope')
    previous=ROOT/'output/latent_circulation_20261028/verification.json'
    if file_hash(previous)!=receipt['previous_receipt_sha256']:raise ValueError('Changed comparison receipt')
    for n,sha in dict(json.loads(previous.read_text())['sources'],**receipt['sources']).items():
        if file_hash(ROOT/n)!=sha:raise ValueError('Changed verified source: '+n)
    picture=out/'moist_enthalpy_budget.png'
    if file_hash(picture)!=receipt['image_sha256']:raise ValueError('Changed image')
    shared={n:np.asarray(v) for n,v in receipt['shared_arrays'].items()}
    masses=shared['layer_mass_kg_m2'];mass=masses.sum(0);t=shared['initial_temperature_k'];verified={}
    cp=1004.;cpv=1850.;cpl=4186.;lv=2.5e6;ref=273.15;dt=86400.;g=9.80665
    scale=np.sin(np.pi*.25)/(np.pi*.25*.75);c=.01*15000/np.pi;factor=1/(2*scale**2)
    dx=receipt['configuration']['cell_m']
    for name,case in receipt['cases'].items():
        a={n:np.asarray(v) for n,v in case['arrays'].items()}
        before=(cp*masses+cpv*a['initial_vapor_kg_m2'])*(t-ref)+lv*a['initial_vapor_kg_m2']
        after=(cp*masses+cpv*a['vapor_kg_m2'])*(a['temperature_k']-ref)+lv*a['vapor_kg_m2']
        rain_energy=cpl*a['ground_rain_kg_m2']*(a['temperature_k'][0]-ref)
        water_error=a['initial_vapor_kg_m2'].sum(0)-a['vapor_kg_m2'].sum(0)-a['ground_rain_kg_m2']
        energy_error=after.sum(0)+rain_energy-before.sum(0)
        if np.abs(energy_error).max()>1e-5 or np.abs(water_error).max()>1e-10:raise ValueError('Changed actual moist water/enthalpy budget')
        np.testing.assert_allclose(a['rain_enthalpy_j_m2'],rain_energy,rtol=1e-13,atol=1e-8)
        np.testing.assert_allclose(a['gas_enthalpy_change_j_m2'],after-before,rtol=1e-13,atol=1e-8)
        np.testing.assert_allclose(a['dry_equivalent_heat_w_m2'],cp*masses*(a['temperature_k']-t)/dt,rtol=1e-13,atol=1e-12)
        tendency=(a['temperature_k']-t)/dt
        source=g/275.*tendency
        integrals=np.array([(1-np.cos(np.pi*.25))/np.pi,(np.cos(np.pi*.25)+1)/np.pi])[:,None,None]
        q=scale*2*np.sum(integrals*source,axis=0)/(np.pi/15000.)
        np.testing.assert_allclose(a['projected_forcing'],q,rtol=1e-12,atol=1e-15)
        phi,u,v=a['geopotential'],a['u_east'],a['v_south']
        mu=np.column_stack((mass[:,0],.5*(mass[:,:-1]+mass[:,1:]),mass[:,-1]))
        mv=np.vstack((mass[0],.5*(mass[:-1]+mass[1:]),mass[-1]))
        div=(np.diff(mu*u,axis=1)+np.diff(mv*v,axis=0))/(mass*dx)
        np.testing.assert_allclose(c*c*div+phi/(20*86400.),q,rtol=1e-9,atol=1e-13)
        work=factor*np.sum(mass*phi*q/c**2)/mass.sum()
        loss=factor*((np.sum(mu[:,1:-1]*u[:,1:-1]**2)+np.sum(mv[1:-1]*v[1:-1]**2))/(5*86400.)
                     +np.sum(mass*(phi/c)**2)/(20*86400.))/mass.sum()
        relative=float(abs(work-loss)/max(abs(work),1e-30))
        if relative>1e-10:raise ValueError('Changed actual mode work balance')
        verified[name]=dict(maximum_water_error_kg_m2=float(np.abs(water_error).max()),
            maximum_moist_enthalpy_error_j_m2=float(np.abs(energy_error).max()),relative_mode_work_error=relative)
    data=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(picture,data/picture.name)
    with Image.open(picture) as im:w,h=im.size
    write_json(data/'moist_enthalpy.json',dict(receipt=receipt,independent_publication_checks=verified,publisher_sha256=file_hash(Path(__file__))))
    rows=[]
    for name,case in receipt['cases'].items():
        s=case['statistics']
        rows.append(f'<tr><td>{name}</td><td>{s["previous_maximum_ground_rain_kg_m2"]:.4f}</td><td>{s["maximum_ground_rain_kg_m2"]:.4f}</td><td>{s["maximum_rain_enthalpy_export_w_m2"]:.3f}</td><td>{s["maximum_column_enthalpy_error_j_m2"]:.2e}</td></tr>')
    section=f'''<!--moist-enthalpy-start--><section aria-labelledby="moist-enthalpy-h"><h2 id="moist-enthalpy-h">Water heat capacities and precipitation enthalpy</h2>
<p><strong>The phase model now includes vapor/liquid heat capacities and the energy carried by falling rain.</strong> Upper condensate enters the lower box at its actual adjusted upper temperature. Surviving rain leaves at the lower temperature and exports liquid sensible enthalpy. The new conservative root balances gas plus liquid enthalpy while preserving nonnegative water. The earlier dilute model remains available as the reproducible comparison.</p>
<p>The same two manufactured moisture pulses are reused without tuning. Initial gas enthalpy equals final gas enthalpy plus exported precipitation enthalpy. Rain energy is relative to liquid at0°C; freezing is not modeled. The net gas-energy change and the dry-equivalent temperature forcing are recorded separately. Once water heat capacities are included, summing cp_d·Md·ΔT is not the moist column’s net thermodynamic heat source.</p>
<div class="table"><table><caption>Fixed-pulse comparison; rainfall maxima may occur at different cells, not Earth accuracy measurements</caption><thead><tr><th>Case</th><th>Prior ground rain maximum mm</th><th>Full-capacity ground rain maximum mm</th><th>Maximum rain energy export W/m²</th><th>Maximum column enthalpy error J/m²</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><a href="data/{picture.name}"><img src="data/{picture.name}" width="{w}" height="{h}" loading="lazy" alt="Manufactured ground rain, exported precipitation enthalpy and dry-equivalent temperature forcing, with separate conserved gas/rain enthalpy ledger"></a></figure>
<p>Actual phase temperature change is projected onto the same specified constant-stability first mode; it is not reinterpreted as unaccounted external heat. Two isolated regional responses add zero Earth integrations. Ten new tests cover independent enthalpy roots, cold versus warm incoming rain, exported rain energy, complete reevaporation and invalid states. The full focused suite passes156 tests. The real calibration count remains1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p class="note">This is still a forward manufactured test, not a coupled moist climate integration or rainfall gain. It includes fixed-pressure liquid-only enthalpy, with no ice, convection, finite cloud/fall time, precipitation mechanical/gravitational energy, prognostic moist heat transport or radiation. The vertical circulation mode is a maintained constant-N Boussinesq approximation. Existing Earth r39 and normal world/biome/population climates remain unchanged.</p>
<p><a href="data/moist_enthalpy.json" download>Download full-capacity phase fields, actual energy ledger and mode verification</a> · <a href="../../reports/MOIST_ENTHALPY_20261028.md">Moist enthalpy equations, comparison and remaining physics</a></p></section><!--moist-enthalpy-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--moist-enthalpy-start-->' in text:
        before,tail=text.split('<!--moist-enthalpy-start-->',1);_,after=tail.split('<!--moist-enthalpy-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_moist_enthalpy',actual_earth_integrations=0,
        physics_or_atlas_adoption=False,metadata_sha256=file_hash(data/'moist_enthalpy.json'),
        image_sha256=receipt['image_sha256'],independent_publication_checks=verified,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    publish(parser.parse_args().out.resolve())
