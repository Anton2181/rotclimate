"""Nest the verified zero-run environmental reference inside its coupled study."""
from pathlib import Path
import argparse
import html
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image
from local_benchmark_protocol import file_hash,identity,write_json


def verified_audit(out):
    """Verify the frozen identity, sources, complete native arrays and image."""
    out=Path(out)
    protocol_path=out/'protocol.json';review_path=out/'review.json'
    protocol=json.loads(protocol_path.read_text());review=json.loads(review_path.read_text())
    if (review.get('complete') is not True or review.get('status')!='passed'
            or review.get('climate_integrations')!=0 or review.get('physics_or_atlas_adoption') is not False
            or review.get('identity')!=identity(protocol)
            or review.get('protocol_sha256')!=file_hash(protocol_path)):
        raise ValueError('Need a completed, unchanged zero-integration environmental reference')
    plan=protocol['plan']
    expected_regions={'pacific_nw':4,'iberia':20,'california':3}
    expected_profiles={'moist','environmental_6','environmental_6.5'}
    if (plan.get('climate_integrations')!=0 or plan.get('physics_or_atlas_adoption') is not False
            or set(plan['regions'])!=set(expected_regions) or set(review['regions'])!=set(expected_regions)
            or set(plan['profiles'])!=expected_profiles
            or plan['pressure_hpa']!=[925,850,700,600,500,400,300]
            or plan['profiles']['environmental_6']!={'profile':'lapse','lapse_k_km':6.}
            or plan['profiles']['environmental_6.5']!={'profile':'lapse','lapse_k_km':6.5}):
        raise ValueError('Changed environmental reference design or scope')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed environmental reference source epoch: '+name)
    arrays=out/'native_profiles.npz';picture=out/'environmental_profiles.png'
    if file_hash(arrays)!=review['arrays_sha256']:raise ValueError('Changed environmental native arrays')
    if (set(review['images_sha256'])!={picture.name}
            or file_hash(picture)!=review['images_sha256'][picture.name]):
        raise ValueError('Changed environmental reference image')
    for name,row in review['reviews'].items():
        if (name not in expected_profiles-{'moist'} or row['thresholds']!=plan['qualification']
                or row['qualifies']!=(not bool(row['failures']))):
            raise ValueError('Changed environmental reference qualification: '+name)
    if set(review['reviews'])!=expected_profiles-{'moist'}:
        raise ValueError('Missing environmental reference qualification')
    geometry_keys={'native_flat_indices','native_ocean_mask','native_full_area_km2','native_area_km2',
        'native_latitude','native_longitude','pressure_hpa','month_days'}
    with np.load(arrays,allow_pickle=False) as saved:
        expected=set()
        for region,count in expected_regions.items():
            row=review['regions'][region];geometry=row['geometry']
            if (geometry['native_ocean_cells']!=count or set(row['profiles'])!=expected_profiles
                    or geometry['pressure_hpa']!=plan['pressure_hpa']
                    or geometry['month_days']!=[31,28,31,30,31,30,31,31,30,31,30,31]):
                raise ValueError('Changed environmental native geometry: '+region)
            for key in geometry_keys:
                name=region+'_'+key;expected.add(name)
                if not np.array_equal(saved[name],np.asarray(geometry[key])):
                    raise ValueError('Environmental raw/JSON geometry differs: '+name)
            mask=saved[region+'_native_ocean_mask'];area=saved[region+'_native_full_area_km2']
            native_area=saved[region+'_native_area_km2']
            if (mask.dtype!=np.dtype(bool) or int(mask.sum())!=count
                    or not np.array_equal(np.flatnonzero(mask),saved[region+'_native_flat_indices'])
                    or not np.array_equal(area[mask],native_area)
                    or not np.isfinite(native_area).all() or (native_area<=0).any()
                    or float(native_area.sum())!=geometry['total_area_km2']):
                raise ValueError('Changed environmental native mask/area accounting: '+region)
            for label,group in [('observed',row['observed']),*row['profiles'].items()]:
                for key,value in group['native'].items():
                    name=region+'_'+label+'_'+key;expected.add(name)
                    if not np.array_equal(saved[name],np.asarray(value)):
                        raise ValueError('Environmental raw/JSON native profile differs: '+name)
        if set(saved.files)!=expected:raise ValueError('Changed environmental raw-array field set')
    return protocol,review,picture


def publish(out):
    out=Path(out)
    protocol,review,picture=verified_audit(out)
    # The reference is nested only after the actual coupled parent is published.
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    parent_start='<!--environmental-partition-start-->';parent_end='<!--environmental-partition-end-->'
    if content.count(parent_start)!=1 or content.count(parent_end)!=1:
        raise ValueError('Publish the completed environmental partition study first')
    data=ROOT/'atlases/climate_accuracy/data'
    parent_metadata=json.loads((data/'environmental_partition.json').read_text())
    linked=parent_metadata.get('environmental_reference') or {}
    if (parent_metadata.get('complete') is not True or parent_metadata.get('physics_or_atlas_adoption') is not False
            or linked.get('identity')!=review['identity']
            or linked.get('review_sha256')!=file_hash(out/'review.json')
            or linked.get('protocol_sha256')!=file_hash(out/'protocol.json')
            or linked.get('reviews')!=review['reviews']):
        raise ValueError('Parent publication does not retain the frozen environmental reference')
    before,tail=content.split(parent_start,1);parent,after=tail.split(parent_end,1)
    anchor='<p><a href="data/environmental_partition.json" download>'
    start='<!--environmental-reference-start-->';end='<!--environmental-reference-end-->'
    if start in parent:
        if parent.count(start)!=1 or parent.count(end)!=1:
            raise ValueError('Ambiguous existing nested environmental reference')
    elif parent.count(anchor)!=1:raise ValueError('Missing unique parent environmental-results link')
    target=data/'environmental_reference.png';shutil.copyfile(picture,target)
    if file_hash(target)!=review['images_sha256'][picture.name]:raise ValueError('Published environmental image differs')
    with Image.open(target) as image:width,height=image.size
    metadata=dict(review,plan=protocol['plan'],frozen_protocol=protocol,
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),published_images_sha256={target.name:file_hash(target)})
    write_json(data/'environmental_reference.json',metadata)
    rows=[]
    for name in ['environmental_6','environmental_6.5']:
        result=review['reviews'][name];means=result['mean_regional']
        failures='; '.join(result['failures']) if result['failures'] else 'Passes all fixed reference checks'
        rows.append(f'<tr><td>{protocol["plan"]["profiles"][name]["lapse_k_km"]:g}</td>'
            f'<td>{means["thermal_mae_k"]:.3f}</td><td>{means["qsat_shape_mae"]:.5f}</td>'
            f'<td>{html.escape(failures)}</td></tr>')
    baseline=review['reviews']['environmental_6']['moist_mean_regional']
    section=f'''{start}<div data-environmental-reference><h3>Separate reference check: environmental temperature and saturation shape</h3>
<p><strong>Zero Earth integrations, fitted coefficients or humidity resets.</strong> The same four PNW, twenty Iberian and three Californian ocean footprints receive only observed 925 hPa temperature as an anchor. Temperatures at 850–300 hPa and all humidity are withheld from profile construction. Fixed 6.0/6.5 K/km environmental profiles and the saturated moist profile use identical pressure nodes, native physical areas and Gregorian month weights.</p>
<figure><a href="data/{target.name}"><img src="data/{target.name}" width="{width}" height="{height}" loading="lazy" alt="Monthly withheld temperature and observed-temperature saturation-shape errors for moist and both fixed environmental profiles in Pacific Northwest, Iberia and California"></a><figcaption>All three fixed profiles are shown. Saturation-shape errors compare predicted capacity with saturation at observed temperature, separately from actual humidity. The observed anchor, liquid saturation and prescribed 200 K floor do not solve environmental energy or saturated plume dynamics.</figcaption></figure>
<p>Equal-region mean withheld-temperature MAE for the moist hypothesis is {baseline['thermal_mae_k']:.3f} K, and its saturation-shape MAE is {baseline['qsat_shape_mae']:.5f}. The 6.0 K/km profile passes the fixed reference checks. The 6.5 K/km profile fails five checks, including the mean-temperature improvement guard. Every regional and aggregate failure remains below and in the complete download; neither profile is ranked or selected.</p>
<div class="table"><table><caption>Frozen reference qualification; mean of three regional native-area/day errors</caption><thead><tr><th>Environmental lapse K/km</th><th>Thermal MAE K</th><th>Saturation-shape MAE</th><th>All fixed checks</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note">These tiny reused ocean samples are model-assisted 1981–2010 reanalysis, externally anchored at 925 hPa. They omit the marine layer below 925 hPa, the atmosphere above 300 hPa and transient covariance. Liquid saturation, constant heat capacities and prescribed thermal floor remain approximations; ice, clouds, entrainment and latent environmental-energy feedback are absent. Capacity is separate from actual humidity and rainfall, and reference qualification cannot authorize adoption. The original archive-schema failure remains preserved as an unsuccessful zero-integration setup.</p>
<p><a href="data/environmental_reference.json" download>Download all native, monthly, seasonal and qualification reference results</a> · <a href="../../reports/ENVIRONMENTAL_REFERENCE_20261027.md">Equations, every outcome and limitations</a></p></div>{end}'''
    if start in parent:
        head,rest=parent.split(start,1);_,foot=rest.split(end,1);parent=head+section+foot
    else:parent=parent.replace(anchor,section+'\n'+anchor)
    updated=before+parent_start+parent+parent_end+after
    if updated.count(start)!=1 or updated.count('data/environmental_reference.png')!=2:
        raise ValueError('Unexpected nested environmental reference insertion')
    page.write_text(updated)
    write_json(out/'publication.json',dict(scope='Nested environmental reference; zero Earth integrations',
        reference_identity=review['identity'],page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'environmental_reference.json'),images_sha256={target.name:file_hash(target)},
        publisher_sha256=file_hash(Path(__file__)),climate_integrations=0,physics_or_atlas_adoption=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'output/environmental_reference_20261027_verified')
    publish(parser.parse_args().out.resolve())
