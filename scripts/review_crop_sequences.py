"""Compare experimental joint windows with the frozen raw-r43 calendar sample."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import json
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from harvest.crop_sequences import CropCatalogue,CropWindow,crop_windows,optimize_sequences
    from harvest.export import climate_arrays,geometry,surface_months
    from harvest.models import specification
    from scripts.land_people import CROPS,analyse,bucket,hargreaves,sunlight_top
    from local_benchmark_protocol import file_hash,write_json
    source=ROOT/'output/crop_calendar_audit_20261103/receipt.json'
    previous=json.loads(source.read_text())
    for name,expected in previous['inputs_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Frozen diagnostic input changed: '+name)
    data=ROOT/'atlases/earth_fit/data';meta=json.loads((data/'atlas.json').read_text())
    arrays=climate_arrays(data,meta);geo,geo_key=geometry(meta,arrays['elev'].shape)
    if geo_key!=previous['geography_inputs']:
        # JSON object keys stringify terrain-tier integers.
        if json.loads(json.dumps(geo_key))!=previous['geography_inputs']:raise ValueError('Geography changed')
    land=np.flatnonzero(geo['land_fraction']>0)
    selected=land[np.linspace(0,len(land)-1,previous['sample_cells'],dtype=int)]
    t,p,d,latitude=surface_months(meta,arrays)
    t,p,d=[a.reshape(12,-1)[:,selected].copy() for a in (t,p,d)]
    latitude=latitude.ravel()[selected];irr=geo['irr'].ravel()[selected];arable=geo['arable'].ravel()[selected]
    margin=specification()['margin_reliability']
    cold=margin['cold_mean_temperature_c'];dry=margin['dry_rain_over_evaporation']
    baseline,_=analyse(t,p,latitude,meta['world']['tilt'],0,irr,arable,d,margins=(cold,dry))
    pet=hargreaves(t,d,sunlight_top(latitude,meta['world']['tilt'],0));soil=bucket(p,pet)
    keep=np.clip((t.mean(0)-cold[0])/(cold[1]-cold[0]),0,1)
    rain_keep=np.clip((baseline['aridity']-dry[0])/(dry[1]-dry[0]),0,1)
    cat=crop_windows(t,p,pet,soil,irr,keep=keep,rain_keep=rain_keep)
    for name in CROPS:
        actual=cat.energy[[w.crop==name for w in cat.windows]].max(0)
        np.testing.assert_array_equal(actual,baseline['kcal_'+name])
    print('All per-crop maxima exactly reproduce production',flush=True)
    can_double=(irr>=.5)|(baseline['lgp_days']>=300)
    results={}
    for gap in [0,1]:
        results[gap]=optimize_sequences(cat,can_double,turnaround=gap,perennial_energy=baseline['kcal_dates'])
        print('Complete turnaround scenario:',gap,flush=True)
    zero,one=results[0],results[1];original=baseline['kcal_ha']
    tol=np.maximum(original,1)*1e-9
    assert np.all(zero.energy+tol>=original) and np.all(zero.energy+tol>=one.energy)
    assert zero.energy.sum()+1e-5>=previous['attainable_energy_sum']
    # Regenerate all windows from jointly rolled climate/soil on fixed cells;
    # radiation and soil spin-up are not recomputed under a different phase.
    ix=np.arange(0,len(selected),16)
    reference=optimize_sequences(CropCatalogue(cat.windows,cat.energy[:,ix]),can_double[ix],perennial_energy=baseline['kcal_dates'][ix])
    for shift in range(12):
        climate=[np.roll(a[:,ix],shift,axis=0) for a in (t,p,pet,soil)]
        shifted=crop_windows(*climate,irr[ix],keep=keep[ix],rain_keep=rain_keep[ix])
        r=optimize_sequences(shifted,can_double[ix],perennial_energy=baseline['kcal_dates'][ix])
        np.testing.assert_array_equal(r.energy,reference.energy)
        np.testing.assert_array_equal(r.optimal_count,reference.optimal_count)
        np.testing.assert_array_equal(r.harvest_boundaries_possible,np.roll(reference.harvest_boundaries_possible,shift,axis=0))
    print('All twelve calendar origins agree on',len(ix),'fixed cells',flush=True)
    gain=(zero.energy-original)/np.maximum(original,1)
    counts={str(gap):dict(improved_cells=int(np.sum(r.energy>original+tol)),
        paired_cells=int(np.sum(r.second>=0)),ambiguous_cells=int(np.sum(r.optimal_count>1)),
        maximum_optimal_schedules=int(r.optimal_count.max()),unweighted_energy_sum=float(r.energy.sum()),
        example_choice_perennial_cells=int(np.sum(r.first==-2))) for gap,r in results.items()}
    out=ROOT/'output/crop_sequences_20261103';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    improved=gain>1e-9
    axes[0].hist(100*gain[improved],bins=np.linspace(0,50,26),color='#478d7d',edgecolor='white')
    axes[0].set(xlabel='Annual crop-mix energy increase (%)',ylabel='Improved sample cells',
                title=f'Joint windows: {int(improved.sum())} / {len(selected)} samples improve')
    values=[int(np.sum(can_double)),counts['0']['paired_cells'],counts['1']['paired_cells']]
    axes[1].bar(['Water gate\npermits a pair','No turnaround\nscenario','One-bin turnaround\nscenario'],values,color=['#879b98','#478d7d','#b68346'])
    axes[1].set(ylabel='Sample cells',title='Compatible seasons depend on time left between crops')
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Experimental joint crop sequences · the same fixed 4,096 raw-r43 fantasy samples\nExisting yield responses and half-weight second crop · no production adoption or population forecast',fontsize=12)
    image=out/'joint_crop_sequences.png';fig.savefig(image,dpi=135);plt.close(fig)
    write_json(out/'receipt.json',dict(status='experimental_comparison',production_atlas_changed=False,
        independent_agronomic_validation=False,crop_coefficients_fitted=False,sample_cells=len(selected),
        inherited_sample_receipt_sha256=file_hash(source),single_crop_maxima_exactly_reproduced=True,
        windows=len(cat.windows),water_gate_eligible_cells=int(can_double.sum()),scenarios=counts,
        baseline_unweighted_energy_sum=float(original.sum()),maximum_relative_gain=float(gain.max()),
        calendar_origin_check=dict(cells=len(ix),origins=12,climate_and_soil_rolled_windows_regenerated=True,energy_count_and_boundary_union_exact=True),
        inputs_sha256=previous['inputs_sha256'],geography_inputs=geo_key,
        literature_manifest_sha256=file_hash(ROOT/'research_notes/crop_sequences_20261103.json'),
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/crop_sequences.py','scripts/review_crop_sequences.py','harvest/export.py','scripts/land_people.py']},
        figure_sha256=file_hash(image),
        scope='All annual windows, at most two occupancy-compatible different crops. Existing second weight and water gate held fixed. Zero/one-bin turnaround are sensitivity scenarios, not ancient estimates. Reference soil buckets do not form a sequential crop-water ledger. Fantasy sample, not whole-map areas or Earth/historical validation. Example choices are arbitrary at ties; count and boundary union retain ambiguity. No perennial harvest dates assigned.'))
    print(json.dumps(counts,indent=2))


if __name__=='__main__':main()
