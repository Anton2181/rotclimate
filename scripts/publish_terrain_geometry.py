"""Expose the static terrain-geometry audit; no current climate changes."""
from pathlib import Path
import argparse,json,shutil,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def publish(source,apertures=None,pressure_gradient=None,pressure_work=None):
    source=source.resolve();r=json.loads((source/'verification.json').read_text())
    assert r['actual_integrations_started']==0 and r['physics_adoption'] is False
    assert file_hash(ROOT/'rotclimate/terrain_hydrostatics.py')==r['geometry_source_sha256']
    for name,key in [('terrain_geometry.png','figure_sha256'),('terrain_geometry.npz','fields_sha256')]:assert file_hash(source/name)==r[key]
    dest=ROOT/'atlases/climate_accuracy/data'
    for name in ['terrain_geometry.png','terrain_geometry.npz']:shutil.copyfile(source/name,dest/name)
    write_json(dest/'terrain_geometry.json',r)
    with Image.open(source/'terrain_geometry.png') as im:w,h=im.size
    rows=''
    for name,v in r['regions'].items():
        m=v['fixed_score_footprints'];rows+=f'<tr><td>{name.replace("_"," ")}</td><td>{m["area_weighted_mean_elevation_m"]:.0f}</td><td>{m["area_weighted_reference_pressure_pa"]/100:.1f}</td><td>{100*m["area_weighted_flat_column_mass_excess_fraction"]:.2f}%</td></tr>'
    aperture_note=''
    if apertures:
        audit=json.loads((apertures/'verification.json').read_text());assert audit['geometry_fields_sha256']==r['fields_sha256'];assert audit['actual_climate_integrations_started']==0;assert file_hash(apertures/'terrain_apertures.npz')==audit['fields_sha256'];assert file_hash(ROOT/'rotclimate/terrain_apertures.py')==audit['aperture_source_sha256']
        shutil.copyfile(apertures/'terrain_apertures.npz',dest/'terrain_apertures.npz');write_json(dest/'terrain_apertures.json',audit)
        aperture_note='<p>Horizontal passages now use every shared pressure interval between neighboring columns, including cross-level connections. Below-ground paths are closed. Seven additional tests check the flat limit, a step mountain, neighbor symmetry, and exact pairwise dry-mass cancellation. A static audit verifies all three real regional geometries with synthetic velocities; it is not a weather run.</p><p><a href="data/terrain_apertures.json">Static terrain-port checks</a> · <a href="data/terrain_apertures.npz">Common-pressure openings and synthetic mass-divergence fields</a></p>'
    if pressure_gradient:
        audit=json.loads((pressure_gradient/'verification.json').read_text());assert audit['actual_climate_integrations_started']==0;assert file_hash(pressure_gradient/'pressure_forces.npz')==audit['fields_sha256']
        shutil.copyfile(pressure_gradient/'pressure_forces.npz',dest/'terrain_pressure_forces.npz');write_json(dest/'terrain_pressure_gradient.json',audit)
        maximum=max(row['hydrostatic_rest_on_all_native_terrain_cells']['maximum_horizontal_acceleration_ms2'] for row in audit['regions'].values())
        aperture_note+=f'<p>The common-pressure gradient now passes native-terrain hydrostatic-rest and thermal-response probes in all three regions. Maximum residual rest acceleration is {maximum:.2e} m/s²; the declared1K thermal probe generates nonzero forces. Seven independent tests include pressure-integral comparisons and thin intervals. <a href="data/terrain_pressure_gradient.json">Static pressure-force checks</a> · <a href="data/terrain_pressure_forces.npz">Native pressure-force fields</a></p>'
    if pressure_work:
        audit=json.loads((pressure_work/'verification.json').read_text());assert audit['actual_climate_integrations_started']==0;assert file_hash(pressure_work/'pressure_work.npz')==audit['fields_sha256']
        shutil.copyfile(pressure_work/'pressure_work.npz',dest/'terrain_pressure_work.npz');write_json(dest/'terrain_pressure_work.json',audit)
        maximum=max(abs(row['actual_signed_work_residual_w_m2_sum']) for rows in audit['regions'].values() for row in rows)
        aperture_note+=f'<p>All nine declared static work controls pass. Native horizontal fluxes independently reconstruct vertical pressure motion and compression/expansion heating; their summed power cancels mechanical pressure work with maximum absolute residual {maximum:.2e} W/m² summed over cells. The initial column-mass projection reports its signed kinetic change and adds no hidden heat. These synthetic closed-domain controls are not weather simulations. <a href="data/terrain_pressure_work.json">Work and mass checks</a> · <a href="data/terrain_pressure_work.npz">Native flux, anomaly, omega and compression fields</a></p>'
    section=f'''<!--terrain-geometry-start--><section aria-labelledby="terrain-geometry-h"><h2 id="terrain-geometry-h">Toward terrain-following atmospheric physics</h2><p>The current regional core has a flat lower boundary and common pressure levels. A new independent geometry module integrates dry hydrostatic pressure over the existing source heights and builds positive, horizontally varying dry layer masses. This is a tested building block; it is not inserted into the current forecasts.</p><figure><a href="data/terrain_geometry.png"><img src="data/terrain_geometry.png" width="{w}" height="{h}" loading="lazy" alt="Static source elevation, dry reference surface pressure, and flat-column mass difference for India, Mexico and Pacific Northwest"></a><figcaption>Same declared source lapse and sea-level pressure as the prototype. These dry reference pressures are not observed pressure measurements. Circles mark the frozen rainfall scoring cells.</figcaption></figure><div class="table"><table><caption>Area-weighted means on fixed scoring footprints</caption><thead><tr><th>Region</th><th>Source height m</th><th>Reference pressure hPa</th><th>Flat-column mass excess / flat model mass</th></tr></thead><tbody>{rows}</tbody></table></div><p>The denominator is the current partial atmosphere from its fixed bottom pressure to380hPa. These percentages are not full observed-atmosphere pressure errors. The audit starts zero climate integrations. Fifteen new geometry tests pass; the related pressure/remapping/rainfall stack passes34 tests.</p>{aperture_note}<p class="note">Variable masses cannot simply replace the current model masses. Before weather integration, this needs compatible dry-mass continuity, transport, native thermodynamic transport, pressure-work-compatible time integration, open boundary fluxes, and explicit lower-boundary kinematics. The current port geometry represents a pressure-coordinate staircase, not a smooth terrain metric. No rainfall improvement, calibration, physics adoption or normal-atlas climate change is claimed.</p><p><a href="data/terrain_geometry.json">Static geometry checks</a> · <a href="data/terrain_geometry.npz">Native geometry fields</a> · <a href="../../reports/TERRAIN_GEOMETRY_20261029.md">Derivation, validation and next implementation gate</a></p></section><!--terrain-geometry-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--terrain-geometry-start-->','<!--terrain-geometry-end-->'
    if start in text:before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--apertures',type=Path);p.add_argument('--pressure-gradient',type=Path);p.add_argument('--pressure-work',type=Path);a=p.parse_args();publish(a.source,a.apertures,a.pressure_gradient,a.pressure_work)
