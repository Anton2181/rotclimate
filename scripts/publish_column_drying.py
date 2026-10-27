"""Publish verified archived drying budgets inside the environmental study."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image
from audit_column_drying import (check_source_closure,check_layer_water,effective_sink_rates,
    summarize,verify_parent)
from local_benchmark_protocol import file_hash,identity,write_json

PREDECLARED_SOURCE_COMMIT='0c2a705'
SCIENTIFIC_SOURCE_COMMIT='255ac32'


def verify_completed_audit(out):
    """Verify hashes, all112 raw fields and every bin against the frozen archive."""
    out=Path(out)
    protocol_path=out/'protocol.json';review_path=out/'review.json'
    protocol=json.loads(protocol_path.read_text());review=json.loads(review_path.read_text())
    if (review.get('complete') is not True or review.get('status')!='passed'
            or review.get('climate_integrations')!=0 or review.get('physics_or_atlas_adoption') is not False
            or review.get('identity')!=identity(protocol)
            or review.get('protocol_sha256')!=file_hash(protocol_path)):
        raise ValueError('Need a completed unchanged zero-integration drying audit')
    plan=protocol['plan'];limits=plan['numerical_limits']
    if (plan.get('climate_integrations')!=0 or plan.get('physics_or_atlas_adoption') is not False
            or review.get('regions')!=plan['regions'] or set(review.get('profiles',{}))!=set(plan['profiles'])
            or review.get('donor_vertical_overlap',{}).get('available') is not False
            or review.get('unavailable')!=plan['unavailable'] or review.get('interpretation')!=plan['decision']):
        raise ValueError('Changed drying audit scope, design or limitations')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed drying audit source: '+name)
    parent_protocol,_,cases,rows,_=verify_parent(plan)
    if protocol['parent_identity']!=identity(parent_protocol) or review['parent_identity']!=identity(parent_protocol):
        raise ValueError('Changed linked parent experiment')
    raw=out/'monthly_sink_rates.npz'
    if file_hash(raw)!=review['arrays_sha256']:raise ValueError('Changed derived monthly drying arrays')
    if set(review['images_sha256'])!={'column_drying_budgets.png','column_drying_changes.png'}:
        raise ValueError('Changed declared drying figure set')
    pictures=[]
    for filename in ['column_drying_budgets.png','column_drying_changes.png']:
        sha=review['images_sha256'][filename]
        picture=out/filename
        if file_hash(picture)!=sha:raise ValueError('Changed drying figure: '+filename)
        pictures.append(picture)
    expected=set()
    with np.load(raw,allow_pickle=False) as derived:
        for name in plan['profiles']:
            if set(review['profiles'][name])!=set(plan['regions']):raise ValueError('Missing regional drying result')
            for region in plan['regions']:
                row=rows[name][region];g=cases[region].grid;sl=g.map_slice()
                result=review['profiles'][name][region]
                with np.load(ROOT/plan['parent']/name/(region+'.npz'),allow_pickle=False) as saved:
                    fields={k:saved[k] for k in saved.files}
                    mask=fields['valid'];elev=fields['elev'];duration=row['params']['year_days']/12.
                    certificate=check_source_closure(fields,mask,
                        atol_mm_month=limits['closure_atol_mm_model_month'],rtol=limits['closure_rtol_sum_abs'])
                    geometry=dict(cropped_shape=list(mask.shape),cropped_diagnostic_cells=int(mask.sum()),
                        full_original_scoring_cells=row['rain']['scored_land_cells'],
                        cropped_omits_scoring_cells=row['rain']['scored_land_cells']-int(mask.sum()),
                        map_slice=[[int(s.start),int(s.stop)] for s in sl],case_identity=row['case_identity'])
                    if (result['closure']!=certificate or result['geometry']!=geometry
                            or result['original_full_score_rain']!=row['rain']):
                        raise ValueError('Published drying certificates/geometry/old scores differ')
                    water=None;water_check=None
                    if name in plan['water_profiles']:
                        water_check=check_layer_water(fields['column_water'],fields['layer_water'],
                            atol_mm=limits['layer_sum_atol_mm'],rtol=limits['layer_sum_rtol'])
                        water=fields['column_water'][(slice(None),)+sl]
                        rate,tau=effective_sink_rates(fields['column_drying'][:,mask],water[:,mask],duration)
                        arrays=dict(column_water_mm=water[:,mask],effective_rate_per_day=rate,
                            effective_timescale_days=tau,valid_flat_indices=np.flatnonzero(mask))
                        for key,value in arrays.items():
                            field=name+'_'+region+'_'+key;expected.add(field)
                            if not np.array_equal(derived[field],value,equal_nan=True):
                                raise ValueError('Derived drying arrays differ: '+field)
                    if result['layer_water_check']!=water_check:
                        raise ValueError('Changed archived layer-sum check')
                    bins=dict(all_land=mask,lowland=mask&(elev<1000),upland=mask&(elev>=1000))
                    if set(result['bins'])!=set(bins):raise ValueError('Changed fixed elevation bins')
                    for label,own in bins.items():
                        if result['bins'][label]!=summarize(fields,own,duration,water):
                            raise ValueError('Drying JSON differs from native archive: '+name+'/'+region+'/'+label)
        if set(derived.files)!=expected:raise ValueError('Changed complete derived-field set')
    own,base=plan['paired_change']['candidate'],plan['paired_change']['control']
    if set(review['paired_changes'])!=set(plan['regions']):raise ValueError('Missing paired drying changes')
    for region in plan['regions']:
        paired=review['paired_changes'][region]
        if paired['candidate']!=own or paired['control']!=base or set(paired['bins'])!=set(plan['bins']):
            raise ValueError('Changed paired change definition')
        for label in plan['bins']:
            a,b=(review['profiles'][name][region]['bins'][label] for name in (own,base))
            result=dict(cells=a['cells'],monthly=None,annual=None)
            if a['cells']:
                result.update(monthly={k:(np.array(a['monthly'][k])-b['monthly'][k]).tolist() for k in a['monthly']},
                    annual={k:a['annual'][k]-b['annual'][k] for k in a['monthly']})
            if paired['bins'][label]!=result:raise ValueError('Changed paired signed-budget differences')
    return protocol,review,pictures


def publish(out):
    out=Path(out)
    protocol,review,pictures=verify_completed_audit(out)
    parent=ROOT/protocol['plan']['parent'];data=ROOT/'atlases/climate_accuracy/data'
    parent_metadata=json.loads((data/'environmental_partition.json').read_text())
    if (parent_metadata.get('complete') is not True or parent_metadata.get('physics_or_atlas_adoption') is not False
            or parent_metadata['provenance']['protocol_sha256']!=file_hash(parent/'protocol.json')
            or parent_metadata['provenance']['review_sha256']!=file_hash(parent/'review.json')):
        raise ValueError('Need the matching published environmental parent')
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    parent_start='<!--environmental-partition-start-->';parent_end='<!--environmental-partition-end-->'
    if content.count(parent_start)!=1 or content.count(parent_end)!=1:
        raise ValueError('Missing unique environmental parent study')
    before,tail=content.split(parent_start,1);section,after=tail.split(parent_end,1)
    start='<!--column-drying-start-->';end='<!--column-drying-end-->'
    anchor='<p><a href="data/environmental_partition.json" download>'
    if start in section:
        if section.count(start)!=1 or section.count(end)!=1:raise ValueError('Ambiguous nested drying audit')
    elif section.count(anchor)!=1:raise ValueError('Missing unique parent download insertion point')
    images=[]
    for source in pictures:
        target=data/source.name;shutil.copyfile(source,target)
        if file_hash(target)!=review['images_sha256'][source.name]:raise ValueError('Published drying figure differs')
        with Image.open(target) as picture:width,height=picture.size
        images.append((target,width,height))
    failed=ROOT/'output/column_drying_20261027/failure.json'
    setup_failure=json.loads(failed.read_text())
    if setup_failure.get('climate_integrations')!=0 or setup_failure.get('physics_or_atlas_adoption') is not False:
        raise ValueError('Preserved failed setup scope differs')
    metadata=dict(review,plan=protocol['plan'],frozen_protocol=protocol,
        predeclared_source_commit=PREDECLARED_SOURCE_COMMIT,
        scientific_source_commit=SCIENTIFIC_SOURCE_COMMIT,
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),published_images_sha256={p.name:file_hash(p) for p,_,_ in images},
        preserved_failed_attempt=dict(path=str(failed.relative_to(ROOT)),sha256=file_hash(failed),record=setup_failure))
    write_json(data/'column_drying.json',metadata)
    figures=[]
    alts=['Signed annual water equation terms across seven fixed cropped regional land samples',
          'Environmental6.0 minus same-wind moist signed budget changes and explicit drying burden for every profile']
    captions=['The original archived equation supplies and exports are shown on identical cropped cells. Monsoon drying is already part of total drying and is stacked only once. The r39 concentration-form advection is not a conservative moisture flux.',
        'Changes are exact differences in archived equation terms, not causal shares or predicted rain after removing the sink. All six profiles remain in the download; the small missing East Australia crop fringe is explicitly counted.']
    for (target,width,height),alt,caption in zip(images,alts,captions):
        figures.append(f'<figure><a href="data/{target.name}"><img src="data/{target.name}" width="{width}" height="{height}" loading="lazy" alt="{alt}"></a><figcaption>{caption}</figcaption></figure>')
    block=f'''{start}<div data-column-drying><h3>Where does explicit column drying enter the water equation?</h3>
<p><strong>Archived equation audit; zero climate integrations, fits or adoption.</strong> The independent layers now carry donor water vertically, and the retained legacy drying closure separately removes water from the column. Internal donor exchange cancels in the total column. This audit measures the additional removal without proving that it duplicates unresolved atmospheric transport.</p>
{''.join(figures)}
<p>Every saved monthly cell equation is checked before averaging. The complete results retain all six profiles, seven regions, lowland/upland bins and the original full-score rainfall measurements. Budget means use the original cropped diagnostic masks: East Australia has 347 cropped cells versus 358 in the full score. Its cropped budgets must not be read as the full-score means.</p>
<p>For the four profiles with saved column water, the removal coefficient is <code>−drying / (month duration × water)</code>: a water-weighted monthly rate, not a mean prescribed parameter or instantaneous rate. Bin and annual rates use ratios of summed loss to water exposure. Zero loss with positive water has infinite reciprocal timescale; zero water gives an unavailable rate. The two older controls did not save water, so their rates remain unavailable.</p>
<p class="note">Branch winds, donor vertical flux, layer rain and step water were not saved. Their overlap with the drying closure and the rain response to removing it cannot be inferred from monthly means. This is neither proof of double counting nor new climate validation. The first audit attempt reached serialization after its checks and figures but failed on a NumPy integer in geometry metadata; that zero-integration attempt remains preserved, and the corrected attempt uses a separate directory. Normal climate, economy, settlement and headline measurements remain unchanged.</p>
<p><a href="data/column_drying.json" download>Download all signed drying budgets, paired differences and water-weighted rates</a> · <a href="../../reports/COLUMN_DRYING_20261027.md">Equation audit and limitations</a></p></div>{end}'''
    if start in section:
        head,rest=section.split(start,1);_,foot=rest.split(end,1);section=head+block+foot
    else:section=section.replace(anchor,block+'\n'+anchor)
    updated=before+parent_start+section+parent_end+after
    if updated.count(start)!=1 or any(updated.count('data/'+p.name)!=2 for p,_,_ in images):
        raise ValueError('Unexpected nested drying insertion')
    page.write_text(updated)
    write_json(out/'publication.json',dict(scope='Nested signed-column-drying audit; zero climate integrations',
        page_sha256=file_hash(page),metadata_sha256=file_hash(data/'column_drying.json'),
        images_sha256={p.name:file_hash(p) for p,_,_ in images},publisher_sha256=file_hash(Path(__file__)),
        climate_integrations=0,physics_or_atlas_adoption=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'output/column_drying_20261027_verified')
    publish(parser.parse_args().out.resolve())
