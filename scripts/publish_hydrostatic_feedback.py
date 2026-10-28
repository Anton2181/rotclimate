"""Verify/publish state-derived pressure and transient hydrostatic wind feedback."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from audit_box_mode_coupling import audit


def publish(out):
    receipt=json.loads((out/'verification.json').read_text())
    if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
            or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False
            or receipt.get('linear_dry_feedback_connected') is not True):raise ValueError('Need explicit linear-dry-only scope')
    for name,sha in receipt['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed verified source: '+name)
    for name,sha in receipt['images_sha256'].items():
        if file_hash(out/name)!=sha:raise ValueError('Changed image: '+name)
    box=audit()
    if box!=receipt['box_coupling_audit']:raise ValueError('Changed independently repeated old-box coupling audit')
    a={key:np.asarray(value) for key,value in receipt['arrays'].items() if key!='final_states'}
    edges=a['vertical_edges_m'];centers=.5*(edges[:-1]+edges[1:]);mass=a['cell_mass_kg_m2']
    f=a['first_pressure_mode'];b=a['first_buoyancy_mode'];weight=a['interface_energy_weight']
    c=receipt['configuration']['wave_speed_ms'];c2=c*c
    np.testing.assert_allclose(np.diff(f)/np.diff(centers),b,rtol=1e-13,atol=1e-15)
    if abs(np.dot(mass,f))>1e-8:raise ValueError('Vertical mass gauge failed')
    np.testing.assert_allclose(np.dot(mass,f*f)/mass.sum(),1.,rtol=1e-12)
    np.testing.assert_allclose(np.dot(weight,b*b)/mass.sum(),1/c2,rtol=1e-12)
    initial_b=9.80665*(a['initial_interface_temperature_k']/a['reference_interface_temperature_k'][:,None,None]-1)
    np.testing.assert_allclose(initial_b,a['initial_buoyancy_m_s2'],rtol=1e-10,atol=1e-13)
    # Independent hydrostatic cumulative integration and modal projection.
    p=np.concatenate([np.zeros_like(initial_b[:1]),np.cumsum(initial_b*np.diff(centers)[:,None,None],axis=0)],axis=0)
    p-=np.sum(mass[:,None,None]*p,axis=0)/mass.sum()
    amplitude=np.sum(mass[:,None,None]*f[:,None,None]*p,axis=0)/mass.sum()
    initial_energy=float(.5*np.mean(amplitude**2/c2));checks={}
    for label,case in receipt['arrays']['final_states'].items():
        phi,u,v=[np.asarray(case[key]) for key in ['pressure_amplitude','u_east','v_south']]
        if np.any(u[:,[0,-1]]) or np.any(v[[0,-1]]):raise ValueError('Closed boundary changed')
        ny,nx=phi.shape
        kinetic=float(.5*(np.sum(u[:,1:-1]**2)+np.sum(v[1:-1]**2))/(ny*nx))
        available=float(.5*np.sum(weight[:,None,None]*(b[:,None,None]*phi)**2)/(mass.sum()*ny*nx))
        run=receipt['runs'][label];damping=run['cumulative_damping_m2_s2']
        relative=abs(kinetic+available+damping-initial_energy)/initial_energy
        if relative>1e-10:raise ValueError('Independent final kinetic/vertical energy plus damping failed')
        for item in receipt['histories'][label]:
            if abs(item['kinetic_m2_s2']+item['available_m2_s2']+item['cumulative_damping_m2_s2']-initial_energy)>1e-10*initial_energy:
                raise ValueError('Recorded transient energy history changed')
        checks[label]=dict(independent_kinetic_m2_s2=kinetic,independent_available_m2_s2=available,
            relative_total_plus_damping_error=relative)
    errs=receipt['time_refinement']
    if not errs['free15']['rms_pressure_amplitude_m2_s2']<errs['free30']['rms_pressure_amplitude_m2_s2']<errs['free60']['rms_pressure_amplitude_m2_s2']:raise ValueError('Refinement changed')
    data=ROOT/'atlases/climate_accuracy/data';figures=[]
    for name,caption in [('hydrostatic_feedback_maps.png','An actual initial thermal anomaly sets hydrostatic pressure and generates evolving mode winds; free and damped24-hour dry tests'),
        ('hydrostatic_feedback_energy.png','Independent vertical available energy and face kinetic energy, timestep refinement and the reference-density vertical mode')]:
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as im:w,h=im.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}. Arrows are mode-amplitude velocities; physical velocity at a level multiplies its vertical mode shape.</figcaption></figure>')
    write_json(data/'hydrostatic_feedback.json',dict(receipt=receipt,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    rows=''.join(f'<tr><td>{minutes}</td><td>{errs[label]["rms_pressure_amplitude_m2_s2"]:.6f}</td><td>{errs[label]["rms_u_ms"]:.6f}</td></tr>' for label,minutes in [('free60',60),('free30',30),('free15',15)])
    section=f'''<!--hydrostatic-feedback-start--><section aria-labelledby="hydrostatic-feedback-h"><h2 id="hydrostatic-feedback-h">Shared thermal state, hydrostatic pressure and evolving winds</h2>
<p><strong>A consistent linear dry feedback now replaces prescribed winds in this prototype.</strong> Initial virtual-potential-temperature buoyancy determines pressure hydrostatically. Winds and pressure/buoyancy then evolve together on energy-paired grids: pressure work creates kinetic energy while the same continuity changes buoyancy. The vertical eigenproblem supplies wave speed. No second adiabatic tendency is added to the earlier moist-box solver; that model remains separate.</p>
<p>A manufactured consistency audit explains why direct wiring would have been unsafe: infinitesimal donor transport of the two-box background gives0.512312 of the smooth first mode’s ascent response and0.263697 of its descent response. Reducing the timestep does not remove that mismatch. Independent one-sided limits agree. This does not invalidate the old fixed-wind water/energy budgets or establish the cause of Earth rainfall errors; it identifies two different vertical representations that cannot be treated as one.</p>
<p>The new hydrostatic reference has theta_surface300K, surface pressure101325Pa, constant N=0.01/s and depth15km. Reference T,p and density follow analytic dry hydrostatics. With64 vertical cells and that density, the first internal speed is45.503 m/s;8/16/32/64-level results converge45.700/45.550/45.512/45.503 m/s. These are model-consistency values, not accuracy against Earth observations. Neutral/unstable backgrounds are rejected without stability clipping.</p>
{figures[0]}
<p>The initial wind is zero. Free and5/20-day damped runs evolve for24 hours in a closed4800×4000km domain with Earth rotation about30°N. The free run conserves kinetic plus actual vertically integrated available energy; damping loss is explicitly recorded in the other run. Time refinement against7.5-minute steps gives:</p>
<div class="table"><table><caption>Same24-hour dry problem; differences against7.5-minute timesteps, not Earth climate errors</caption><thead><tr><th>Timestep min</th><th>RMS pressure-mode difference m²/s²</th><th>RMS east-wind difference m/s</th></tr></thead><tbody>{rows}</tbody></table></div>
{figures[1]}
<p>Twenty-five new tests verify reference hydrostatics, discrete cosine modes, variable-density work and continuity, state-derived pressure, analytic transient wave dispersion, physical heating work and energy. The wider focused suite passes199 tests. Independent publication checks reconstruct initial buoyancy/pressure and final vertical available energy and face kinetic energy from raw arrays. The retained and excluded initial/source modal energy norms are explicit.</p>
<p class="note">This is one linear dry anelastic mode about a maintained reference, with reflecting walls. It is not compressible terrain physics, predicted radiation, a moist feedback loop or a new Earth forecast. The earlier moist two-box state is not attached until it can share a consistent vertical thermodynamic/momentum discretization. Existing Earthr39 and normal world/biome/population climates remain unchanged. Zero Earth integrations are added; counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption. Neither this structural audit nor unique linear solves establishes a global calibration optimum.</p>
<p><a href="data/hydrostatic_feedback.json" download>Download thermal state, vertical modes, transient winds and independent checks</a> · <a href="../../reports/VERTICAL_STATE_20261028.md">Shared vertical state and box-coupling audit</a> · <a href="../../reports/HYDROSTATIC_FEEDBACK_20261028.md">Transient feedback equations, tests and limits</a></p></section><!--hydrostatic-feedback-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--hydrostatic-feedback-start-->' in text:
        before,tail=text.split('<!--hydrostatic-feedback-start-->',1);_,after=tail.split('<!--hydrostatic-feedback-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_dry_state_feedback',actual_earth_integrations=0,
        physics_or_atlas_adoption=False,linear_dry_feedback_connected=True,metadata_sha256=file_hash(data/'hydrostatic_feedback.json'),
        images_sha256=receipt['images_sha256'],independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
