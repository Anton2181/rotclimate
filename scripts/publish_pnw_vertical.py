"""Publish the verified zero-run PNW vertical audit inside its westerly study."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image
from local_benchmark_protocol import file_hash,identity,write_json

SCIENTIFIC_SOURCE_COMMIT='a012505'


def verified_audit(out):
    """Check every source, raw native array and existing figure before copying."""
    protocol_path=out/'protocol.json';review_path=out/'review.json'
    protocol=json.loads(protocol_path.read_text());review=json.loads(review_path.read_text())
    if (review.get('complete') is not True or review.get('status')!='passed'
            or review.get('climate_integrations')!=0 or review.get('physics_or_atlas_adoption') is not False
            or review.get('identity')!=identity(protocol)
            or review.get('provenance',{}).get('protocol_sha256')!=file_hash(protocol_path)):
        raise ValueError('Need a completed, unchanged zero-integration PNW vertical audit')
    plan=protocol['plan']
    if plan.get('climate_integrations')!=0 or plan.get('physics_or_atlas_adoption') is not False:
        raise ValueError('PNW diagnostic scope changed')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed PNW vertical scientific epoch: '+name)
    arrays=out/'native_profiles.npz';picture=out/'native_profiles.png'
    if file_hash(arrays)!=review['provenance']['arrays_sha256']:raise ValueError('Changed native PNW profile arrays')
    if file_hash(picture)!=review['image_sha256']:raise ValueError('Changed PNW profile image')
    geometry=review['geometry']
    if (geometry['native_ocean_cells']!=4 or geometry['pressure_hpa']!=[925,850,700,600,500,400,300]
            or set(review['profiles'])!={'lapse','moist'}):raise ValueError('Changed PNW reference design')
    with np.load(arrays,allow_pickle=False) as saved:
        for key in ['native_flat_indices','native_area_km2','native_latitude','native_longitude','pressure_hpa','month_days']:
            if not np.array_equal(saved[key],np.asarray(geometry[key])):
                raise ValueError('Raw/JSON PNW native geometry differs: '+key)
        mask=saved['native_ocean_mask'];area=saved['native_full_area_km2']
        if (mask.dtype!=np.dtype(bool) or int(mask.sum())!=4
                or not np.array_equal(np.flatnonzero(mask),saved['native_flat_indices'])
                or not np.array_equal(area[mask],saved['native_area_km2'])
                or float(saved['native_area_km2'].sum())!=geometry['total_area_km2']):
            raise ValueError('Changed PNW mask/physical-area accounting')
        expected={'native_flat_indices','native_ocean_mask','native_full_area_km2','native_area_km2',
            'native_latitude','native_longitude','pressure_hpa','month_days'}
        groups=[('observed',review['observed']),*review['profiles'].items()]
        for label,group in groups:
            for key,value in group['native'].items():
                name=label+'_'+key;expected.add(name)
                if not np.array_equal(saved[name],np.asarray(value)):
                    raise ValueError('Raw/JSON PNW monthly profile differs: '+name)
        if set(saved.files)!=expected:raise ValueError('Changed PNW raw-array field set')
    return protocol,review,picture


def publish(out):
    protocol,review,picture=verified_audit(out)
    # Verify the existing parent and insertion point before changing its assets.
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    parent_start='<!--westerly-fit-start-->';parent_end='<!--westerly-fit-end-->'
    if content.count(parent_start)!=1 or content.count(parent_end)!=1:
        raise ValueError('Publish the existing westerly study first')
    before,tail=content.split(parent_start,1);parent,after=tail.split(parent_end,1)
    anchor='<p><a href="data/westerly_fit.json" download>'
    start='<!--pnw-vertical-start-->';end='<!--pnw-vertical-end-->'
    if start in parent:
        if parent.count(start)!=1 or parent.count(end)!=1:raise ValueError('Ambiguous existing nested PNW vertical audit')
    elif parent.count(anchor)!=1:raise ValueError('Missing unique parent westerly-results link')
    data=ROOT/'atlases/climate_accuracy/data';data.mkdir(parents=True,exist_ok=True)
    target=data/'pnw_vertical.png';shutil.copyfile(picture,target)
    if file_hash(target)!=review['image_sha256']:raise ValueError('Published PNW figure copy differs')
    with Image.open(target) as image:width,height=image.size
    metadata=dict(review,plan=protocol['plan'],frozen_protocol=protocol,
        scientific_source_commit=SCIENTIFIC_SOURCE_COMMIT,
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),published_images_sha256={target.name:file_hash(target)})
    write_json(data/'pnw_vertical.json',metadata)
    observed=review['observed']['seasons']['annual'];lapse=review['profiles']['lapse']['seasons']['annual']
    moist=review['profiles']['moist']['seasons']['annual']
    table=[]
    for label,row in [('Observed temperature',observed),('Fixed environmental lapse',lapse),('Saturated moist profile',moist)]:
        error=row.get('withheld_850_300_temperature_shape_mae_c')
        shown='—' if error is None else f'{error:.3f}'
        table.append(f'<tr><td>{label}</td><td>{row["partial_saturation_capacity_mm"]:.3f}</td>'
            f'<td>{row["upper_lower_mean_saturation_q_ratio"]:.3f}</td><td>{shown}</td></tr>')
    section=f'''{start}<div data-pnw-vertical><h3>Pacific Northwest: distinguish thermal capacity from actual humidity</h3>
<p><strong>Separate reference diagnostic; zero additional Earth integrations and no fitted profile.</strong> The same four PNW ocean footprints cover {review['geometry']['total_area_km2']:,.0f} km². Both predicted profiles start from observed 925 hPa temperature, with higher temperatures and all humidity withheld. The lapse remains the fixed r39 value; no humidity multiplier is fitted.</p>
<figure><a href="data/{target.name}"><img src="data/{target.name}" width="{width}" height="{height}" loading="lazy" alt="Four fixed Pacific Northwest ocean footprints: winter and summer temperature profiles, observed dry potential temperature and specific-humidity saturation fraction, monthly water and capacity, and actual versus saturation humidity-shape ratios"></a><figcaption>Actual water, saturation capacity and their vertical shapes are distinct. All quantities use the same seven pressure nodes, native physical areas and Gregorian month weights. Dry theta above 925 hPa does not diagnose a marine inversion below that level.</figcaption></figure>
<p>Observed partial water is {observed['partial_water_mm']:.3f} mm and the actual upper/lower q ratio is {observed['upper_lower_mean_actual_q_ratio']:.3f}. Saturation at the observed temperature profile gives a different ratio, {observed['upper_lower_mean_saturation_q_ratio']:.3f}. The anchored lapse and moist capacities give {lapse['upper_lower_mean_saturation_q_ratio']:.3f} and {moist['upper_lower_mean_saturation_q_ratio']:.3f}; a capacity ratio closer to actual humidity does not establish a better thermal profile.</p>
<div class="table"><table><caption>Annual native-area/day means; saturation is capacity, not predicted actual water</caption><thead><tr><th>Temperature profile</th><th>Saturated 925–300 hPa capacity mm</th><th>Partial saturation q ratio</th><th>Withheld 850–300 hPa temperature MAE K</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Actual lower/upper water-to-capacity fractions are {observed['lower_water_over_saturation_capacity']:.3f}/{observed['upper_water_over_saturation_capacity']:.3f}, using saturation at observed temperatures. These fractions are calculated per footprint and month before averaging. Thermal capacity and actual humidity both shape the vertical contrast; the result does not justify imposing one universal q ratio or resetting solved moisture.</p>
<p class="note">This tiny sample contains no accepted land footprint. Model-assisted NCEP/NCAR 1981–2010 monthly normals differ from the WorldClim 1970–2000 rainfall period. The 925–300 hPa window omits the near-surface marine layer and transient covariance. The observed anchor, liquid-only saturation, constant heat capacities, prescribed temperature floor and absence of cloud/latent-energy feedback remain explicit approximations. No rainfall attribution, global validation, fit selection or atlas-climate replacement follows.</p>
<p><a href="data/pnw_vertical.json" download>Download all native, monthly and seasonal PNW thermal/humidity profiles</a> · <a href="../../reports/PNW_VERTICAL_20261027.md">Equations, measured results and limitations</a></p></div>{end}'''
    if start in parent:
        head,rest=parent.split(start,1);_,foot=rest.split(end,1);parent=head+section+foot
    else:parent=parent.replace(anchor,section+'\n'+anchor)
    updated=before+parent_start+parent+parent_end+after
    if updated.count(start)!=1 or updated.count('data/pnw_vertical.png')!=2:
        raise ValueError('Unexpected nested PNW figure insertion')
    page.write_text(updated)
    write_json(out/'publication.json',dict(scope='Nested PNW reference diagnostic; zero additional Earth integrations',
        scientific_source_commit=SCIENTIFIC_SOURCE_COMMIT,page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'pnw_vertical.json'),images_sha256={target.name:file_hash(target)},
        publisher_sha256=file_hash(Path(__file__)),climate_integrations=0,physics_or_atlas_adoption=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'output/pnw_vertical_20261027')
    publish(parser.parse_args().out.resolve())
