"""Audit tied crop calendars on a fixed systematic sample of the raw r43 atlas."""
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
    from harvest.export import climate_arrays,geometry,surface_months
    from harvest.models import specification
    from harvest.calendar_audit import calendar_origin_audit
    from scripts.land_people import analyse,bucket,hargreaves,sunlight_top
    from local_benchmark_protocol import file_hash,write_json
    data=ROOT/'atlases/earth_fit/data'
    meta=json.loads((data/'atlas.json').read_text())
    if meta.get('physics_profile')!='r43':
        raise ValueError('This dated audit is declared for the raw r43 atlas')
    arrays=climate_arrays(data,meta)
    geo,geo_key=geometry(meta,arrays['elev'].shape)
    land=np.flatnonzero(geo['land_fraction']>0)
    selected=land[np.linspace(0,len(land)-1,min(4096,len(land)),dtype=int)]
    t,p,d,latitude=surface_months(meta,arrays)
    shape=geo['land_fraction'].shape
    t,p,d=[a.reshape(12,-1)[:,selected].copy() for a in (t,p,d)]
    latitude=latitude.ravel()[selected]
    irr=geo['irr'].ravel()[selected];arable=geo['arable'].ravel()[selected]
    margin=specification()['margin_reliability']
    cold=tuple(margin['cold_mean_temperature_c']);dry=tuple(margin['dry_rain_over_evaporation'])
    baseline,_=analyse(t,p,latitude,meta['world']['tilt'],0,irr,arable,d,margins=(cold,dry))
    pet=hargreaves(t,d,sunlight_top(latitude,meta['world']['tilt'],0));soil=bucket(p,pet)
    keep=np.clip((t.mean(0)-cold[0])/(cold[1]-cold[0]),0,1)
    rain_keep=np.clip((baseline['aridity']-dry[0])/(dry[1]-dry[0]),0,1)
    can_double=(irr>=.5)|(baseline['lgp_days']>=300)
    audit=calendar_origin_audit(t,p,pet,soil,irr,can_double,keep=keep,rain_keep=rain_keep,
                               perennial_kcal=baseline['kcal_dates'])
    np.testing.assert_allclose(audit.original_total,baseline['kcal_ha'],rtol=1e-12,atol=1e-7)
    tolerance=np.maximum(audit.original_total,1)*1e-9
    changed=audit.rotation_maximum-audit.rotation_minimum>tolerance
    improved=audit.attainable_tied_total-audit.original_total>tolerance
    assert np.all(audit.attainable_tied_total+tolerance>=audit.rotation_maximum)
    positive=audit.original_total>0
    gain=np.zeros_like(audit.original_total)
    np.divide(audit.attainable_tied_total-audit.original_total,audit.original_total,out=gain,where=positive)
    print(json.dumps(dict(sample=len(selected),rotation_changes=int(changed.sum()),
                         attainable_improvements=int(improved.sum()))),flush=True)
    out=ROOT/'output/crop_calendar_audit_20261103';out.mkdir(parents=True,exist_ok=True)
    names=list(audit.crop_mask_varies)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    axes[0].bar(names,[100*np.mean(audit.crop_mask_varies[n]) for n in names],color='#3f8278')
    axes[0].set(ylabel='Sample cells with a different tied-best season (%)',ylim=(0,100),
                title='Individual annual crop yields remain the same')
    axes[1].hist(100*gain[improved],bins=np.linspace(0,50,26),color='#b78341',edgecolor='white')
    axes[1].set(xlabel='Attainable annual crop-mix energy increase (%)',ylabel='Improved sample cells (other cells omitted)',
                title=f'{int(improved.sum())} / {len(selected)} cells have a missed feasible pair')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Crop-calendar tie audit · raw Earth-fit r43 fantasy geography\n4,096 systematic land-cell samples · existing crop, irrigation and second-crop rules retained',fontsize=12)
    image=out/'crop_calendar_ties.png';fig.savefig(image,dpi=135);plt.close(fig)
    write_json(out/'receipt.json',dict(status='diagnostic_only',production_atlas_changed=False,
        input_atlas='raw Earth-fit r43 fantasy geography; not an Earth observation comparison',
        sampling='4096 equally spaced indices in row-major land cells, no random selection; sample proportions are not whole-map area estimates',
        sample_cells=len(selected),land_cells=len(land),sample_grid_shape=list(shape),
        individually_viable_cells=int(positive.sum()),rotation_changed_mix_cells=int(changed.sum()),
        alternative_tied_calendar_pair_cells=int(improved.sum()),maximum_relative_attainable_gain=float(gain.max()),
        original_energy_sum=float(audit.original_total.sum()),attainable_energy_sum=float(audit.attainable_tied_total.sum()),
        tied_season_mask_cells={n:int(v.sum()) for n,v in audit.crop_mask_varies.items()},
        maximum_annual_crop_yield_drift=audit.maximum_crop_yield_drift,
        production_original_total_reproduced=True,perennial_second_crop_excluded=True,same_crop_second_harvest_excluded=True,
        scope='Attainable lower bound from best-season masks selected under twelve calendar relabellings. Not exhaustive crop scheduling, actual harvest dates, food stocks, population, independent agronomic validation or an adoption. Soil states rolled without recomputing spin-up; radiation and climate held fixed.',
        inputs_sha256={str(path.relative_to(ROOT)):file_hash(path) for path in [data/'atlas.json',data/'atlas.bin',ROOT/'data/harvest_model.json']},
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/calendar_audit.py','harvest/export.py','scripts/land_people.py','scripts/audit_crop_calendars.py']},
        geography_inputs=geo_key,figure_sha256=file_hash(image)))


if __name__=='__main__':main()
