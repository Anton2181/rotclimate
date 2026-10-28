"""Publish verified isolated regional circulation and native-face tracer checks."""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from demo_regional_baroclinic import audit
from local_benchmark_protocol import file_hash,write_json
from rotclimate.regional_baroclinic import RegionalMode


def verify(out):
    dry=json.loads((out/'verification.json').read_text())
    tracer=json.loads((out/'tracer_verification.json').read_text())
    for receipt in [dry,tracer]:
        if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
                or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False):
            raise ValueError('Need isolated non-adopted scope')
        for name,sha in receipt['sources'].items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Changed verified source: '+name)
    if file_hash(out/'verification.json')!=tracer['dry_receipt_sha256']:
        raise ValueError('Tracer uses another dry circulation receipt')
    dx=dry['configuration']['cell_m'];heating=np.asarray(dry['forcing_m2_s3'])
    for name,case in dry['cases'].items():
        a={key:np.asarray(value) for key,value in case['arrays'].items()}
        mode=RegionalMode(a['u_east'],a['v_south'],a['geopotential'],a['divergence_per_s'],case['certificate'])
        recomputed=audit(mode,a['mass'],heating,dx)
        if recomputed!=case['independent']:raise ValueError('Changed independent dry budget: '+name)
    water_errors={}
    for name,case in tracer['arrays'].items():
        a={key:np.asarray(value) for key,value in case.items()}
        source=np.zeros_like(a['water']);source[0]=2/86400.
        np.testing.assert_allclose(a['removal'],a['water']/(10*86400.),rtol=5e-16,atol=0)
        raw=dry['cases'][name]['arrays'];mass=a['mass_kg_m2']
        np.testing.assert_array_equal(mass,10000.*np.asarray(raw['mass']))
        mixing=a['water']/np.stack([.25*mass,.75*mass])
        mu=np.column_stack((mass[:,0],.5*(mass[:,:-1]+mass[:,1:]),mass[:,-1]))
        mv=np.vstack((mass[0],.5*(mass[:-1]+mass[1:]),mass[-1]))
        low_x=-.25*.75*mu*np.asarray(raw['u_east'])
        low_y=-.25*.75*mv*np.asarray(raw['v_south'])
        fx,fy=np.stack([low_x,-low_x]),np.stack([low_y,-low_y])
        ext=np.broadcast_to(np.array([.009,.0025])[:,None,None],mixing.shape)
        qx=np.concatenate((ext[:,:,:1],mixing,ext[:,:,-1:]),axis=2)
        qy=np.concatenate((ext[:,:1],mixing,ext[:,-1:]),axis=1)
        np.testing.assert_allclose(a['east_water_flux'],fx*np.where(fx>=0,qx[:,:,:-1],qx[:,:,1:]),rtol=1e-12,atol=1e-14)
        np.testing.assert_allclose(a['south_water_flux'],fy*np.where(fy>=0,qy[:,:-1],qy[:,1:]),rtol=1e-12,atol=1e-14)
        upward=.25*.75*mass*np.asarray(raw['divergence_per_s'])
        np.testing.assert_allclose(a['upward_water_flux'],upward*np.where(upward>=0,mixing[0],mixing[1]),rtol=1e-12,atol=1e-14)
        horizontal=(np.diff(a['east_water_flux'],axis=2)+np.diff(a['south_water_flux'],axis=1))/dx
        vertical=np.stack([a['upward_water_flux'],-a['upward_water_flux']])
        residual=source-a['removal']-horizontal-vertical
        error=float(np.abs(residual).max())
        if error>1e-14 or a['water'].min()<0:raise ValueError('Changed actual donor face budget')
        water_errors[name]=error
    images={name:dry['images_sha256'][name] for name in ['regional_baroclinic_response.png','regional_baroclinic_budgets.png']}
    images['regional_mode_water.png']=tracer['image_sha256']
    for name,sha in images.items():
        if file_hash(out/name)!=sha:raise ValueError('Changed image: '+name)
    return dry,tracer,images,water_errors


def publish(out):
    dry,tracer,images,water_errors=verify(out)
    data=ROOT/'atlases/climate_accuracy/data'
    figures=[]
    captions=['Manufactured regional circulation: identical forcing, closed walls and passive edges with variable column mass',
              'Independent modal energy accounting and fixed-domain mesh refinement, not measured climate skill',
              'Passive water on native circulation faces with independent lower/upper humidity and donor vertical exchange; not predicted rainfall']
    for (name,sha),caption in zip(images.items(),captions):
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as picture:w,h=picture.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}.</figcaption></figure>')
    write_json(data/'regional_baroclinic.json',dict(dry=dry,tracer=tracer,publisher_sha256=file_hash(Path(__file__)),
                                                 independent_tracer_face_errors_water_per_s=water_errors))
    rows=[]
    for name,case in dry['cases'].items():
        c=case['certificate']
        rows.append(f'<tr><td>{name}</td><td>{1e6*c["modal_energy_input_m2_s3"]:.5f}</td><td>{1e6*c["momentum_dissipation_m2_s3"]:.5f}</td><td>{1e6*c["thermal_dissipation_m2_s3"]:.5f}</td><td>{1e6*c["boundary_energy_export_m2_s3"]:.5f}</td><td>{case["independent"]["independent_relative_energy_error"]:.2e}</td></tr>')
    water_rows=[]
    for name,case in tracer['independent'].items():
        water_rows.append(f'<tr><td>{name}</td><td>{case["total_source_mm_day_cell_sum"]:.3f}</td><td>{case["total_removal_mm_day_cell_sum"]:.3f}</td><td>{sum(case["outward_boundary_mm_day_cell_sum"]):+.3f}</td><td>{case["column_budget_residual_mm_day_cell_sum"]:.2e}</td></tr>')
    section=f'''<!--regional-baroclinic-start--><section aria-labelledby="regional-baroclinic-h"><h2 id="regional-baroclinic-h">Regional dry circulation and native-face water</h2>
<p><strong>Physical foundation verified; not a new Earth climate or rainfall gain.</strong> The circulation prototype now handles regional walls, passive normal-wave boundaries and spatially varying dry-column mass. It solves momentum together with thermal-thickness adjustment. Mass-weighted pressure/transport adjoints and paired rotation keep its modal energy budget exact, including nonnegative energy exported through passive edges.</p>
<p>Seventeen regional tests verify analytic box waves, a resting atmosphere over a mass gradient, independent mass/energy budgets, changing mass units and convergence to a continuous Robin-boundary solution. Nine new tracer tests check exact native-face donor transport, independent humidity in each layer and exterior water budgets. Together with the earlier periodic operator there are 35 foundation tests; the wider focused suite passes 113 tests. These numerical checks add zero Earth integrations. The accumulated benchmark count stays 1934 attempts / 1929 strict passes / four historical failures / one historical interruption.</p>
<p>The fixed manufactured comparison uses a synthetic ridge only to set relative mass exp(−height/8000 m), Earth rotation across a domain centered at30°N, c=50 m/s, five-day momentum damping and twenty-day thermal relaxation. All three cases have identical prescribed modal heating. Mass weighting is one part of terrain treatment: it does not add mountain blocking or a terrain-dependent vertical mode.</p>
<div class="table"><table><caption>Modal energy rates in10⁻⁶ m²/s³ per reference mass; forcing = damping + boundary export</caption><thead><tr><th>Case</th><th>Forcing</th><th>Momentum</th><th>Thermal</th><th>Boundary export</th><th>Relative budget error</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{figures[0]}{figures[1]}
<p>On the same physical domain, refining from200 to100 km lowers RMS geopotential difference against the50 km solution from1.114 to0.379 m²/s². These are mesh-consistency measurements, not climate-accuracy percentages. The passive impedance uses adjacent-cell pressure and a zero incoming normal characteristic in the locally nonrotating one-dimensional limit. It is first order and does not transparently pass arbitrary rotating or oblique waves. Exterior normal velocities have no momentum degree of freedom and are excluded from rotation interpolation.</p>
<p>The water bridge retains the circulation’s staggered face fluxes. It embeds opposing lower/upper dry flow and diagnoses vertical exchange from continuity, then moves water from the actual lower or upper donor. Incoming external air has independently supplied layer mixing ratios; outgoing air carries local humidity. No fixed humidity ratio or saturation reset is applied. This demo prescribes2 mm/day lower water supply and10-day tracer removal. <strong>The sink is not predicted rainfall, and there is no latent-heating feedback.</strong></p>
<div class="table"><table><caption>Water budgets summed over equal-area cells in mm/day; multiply by cell area for integrated volume. Outward boundary flux is signed.</caption><thead><tr><th>Case</th><th>Source</th><th>Tracer removal</th><th>Boundary outflow</th><th>Column residual</th></tr></thead><tbody>{''.join(water_rows)}</tbody></table></div>
{figures[2]}
<p>Next requirements are physically budgeted atmospheric heating, actual incoming lateral states and background circulation, terrain geometry and conservative moist/latent coupling before a bounded Earth rainfall experiment. Each isolated positive-damping linear solve has a unique steady solution; this does not make the nonlinear climate calibration globally unique. Existing Earth r39 and all normal world/biome/population climates remain unchanged.</p>
<p><a href="data/regional_baroclinic.json" download>Download regional dry and tracer fields, budgets and verification</a> · <a href="../../reports/REGIONAL_BAROCLINIC_20261028.md">Regional equations and boundary limits</a> · <a href="../../reports/REGIONAL_MODE_TRACER_20261028.md">Native-face donor water equations and tests</a></p></section><!--regional-baroclinic-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--regional-baroclinic-start-->' in text:
        before,tail=text.split('<!--regional-baroclinic-start-->',1)
        _,after=tail.split('<!--regional-baroclinic-end-->',1)
        text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_foundations',actual_earth_integrations=0,
        physics_or_atlas_adoption=False,publisher_sha256=file_hash(Path(__file__)),
        metadata_sha256=file_hash(data/'regional_baroclinic.json'),images_sha256=images,
        independent_tracer_face_errors_water_per_s=water_errors))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    publish(parser.parse_args().out.resolve())
