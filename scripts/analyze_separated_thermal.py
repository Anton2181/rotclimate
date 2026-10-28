"""Verify actual thermal shear and rainfall-first outcomes of the fixed pilot."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,identity,write_json
from separated_thermal_pilot import check_row,score
from analyze_transport_diagnosis import check_sidecar,summarize,pressure_level_comparison,FOCUS,SEASONS
from transport_native import diagnose
from rotclimate import earth
from rotclimate.model import gauss
from benchmark_local import DEV12_SPECS
from earth_calendar import observation_weights


from analyze_thermal_wind_pilot import check_shear as check_single_shear
from verify_separated_shear import check as check_separated_shear


def verify(out):
    protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text());plan=protocol['plan']
    if not review['complete'] or review['identity']!=identity(protocol) or review['actual_integrations']!=18 or review['pending_integrations']:
        raise ValueError('Need complete eighteen-case pilot')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed frozen source/input: '+name)
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()));fresh={};checks=[];data={};maps={}
    for row in review['records']:
        name,region=row['name'],row['region'];fresh[name+'/'+region]=check_row(row,plan,out)
        if fresh[name+'/'+region]!=review['checks'][name+'/'+region]:raise ValueError('Changed actual physical/control outcome')
        if row['status']!='passed':
            checks.append(dict(profile=name,region=region,status='failed',error=row['error']));continue
        path=out/name/(region+'_transport.npz')
        with np.load(path,allow_pickle=False) as src:a={k:src[k] for k in src.files}
        water=check_sidecar(a,row);thermal=check_separated_shear(a,row) if name.endswith('_thermal') else (check_single_shear(a,row) if name.endswith('_single') else None)
        case=earth.region_case(region,plan['cell_km']);report,native=diagnose(case,SimpleNamespace(**row['params']),a,plan)
        if report!=row['matched_native']:raise ValueError('Changed matched native metrics')
        for key,value in native.items():np.testing.assert_array_equal(a[key],value)
        data.setdefault(region,{})[name]=dict(full_land=summarize(a,case),native=report,
            pressure_levels=pressure_level_comparison(a,case,plan),rain=row['rain'],temperature=row['temperature'],
            thermal_certificate=row['numerics'].get('thermal_layer_winds'))
        checks.append(dict(profile=name,region=region,status='passed',water=water,thermal=thermal))
        if name.endswith('_thermal'):
            from audit_separated_structure import audit
            data[region][name]['thermal_structure']=audit(a,row,case,plan)
        if name in ('hydro_control','hydro_single','hydro_thermal'):
            # Keep only map fields needed by plotting, not hundreds of MB of faces.
            idx=a['scored_indices'];weights,durations,_=observation_weights(a['days']);months=SEASONS[FOCUS[region]]
            coeff=(weights[months]*durations[months,None]).sum(0)
            rain=np.tensordot(coeff,a['rain'][idx].sum(1),axes=(0,0))
            maps[region,name]=dict(rain=rain,observed=np.nan_to_num(case.obs_P[months]).sum(0),mask=a['score_land'],lat=a['latitude'],lon=a['longitude'])
    scores=score(review['records'],fresh,plan)
    if scores!=review['scores']:raise ValueError('Changed rainfall-first outcomes')
    receipt=dict(status='passed',sources_verified=len(protocol['sources']),actual_integrations=18,
        strictly_passed=review['strictly_passed'],failed_integrations=review['failed_integrations'],
        cumulative_attempts=review['cumulative_attempts'],cumulative_strict_passes=review['cumulative_strict_passes'],
        cumulative_failures_or_interruptions=review['cumulative_failures_or_interruptions'],cases=checks,
        independent_analysis_integrations=0,physics_or_atlas_adoption=False)
    report=dict(scores=scores,regions=data,verification=receipt,plan=plan,
        source_protocol_sha256=file_hash(out/'protocol.json'),source_review_sha256=file_hash(out/'review.json'),
        interpretation='Fixed development-region mechanism test. Native improvements do not substitute for rainfall gains. No independent validation, global optimum claim or atlas climate adoption.',
        limitations=['Three reused development regions; native925hPa masks sparse/empty over mountains.',
            'Two-box winds; prescribed dry hydrostatic profile and common-pressure interpretation of modeled Tsl; modeled zonal thermal background proxy; no resolved momentum/vertical energy.',
            'Existing10degree Coriolis regularization damps shear; provisional fixed-q diagnostics retained until actual water solve.',
            'Fixed observed cloud/remote-monsoon backgrounds; conditional regional model.',
            'NCEP monthly flux misses submonthly covariance; WorldClim period differs.'])
    return receipt,report,maps


def plot(out,report,maps):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    months=np.arange(12)
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    for i,base in enumerate(('legacy','hydro')):
        score=report['scores'][base]
        if 'regional' not in score:continue
        for col,key in enumerate(('rain_loss_ratio','temperature_mae_change_C')):
            values=[score['regional'][r][key] for r in FOCUS];axes[col].bar(np.arange(3)+(i-.5)*.32,values,.3,label=base+' ocean',color=['#8d6937','#28849a'][i])
    for ax in axes:ax.set_xticks(np.arange(3),['North India','Mexico','Pacific NW']);ax.grid(axis='y',alpha=.2);ax.legend()
    axes[0].axhline(1,color='#333',lw=.8);axes[0].set(title='Actual location/month rainfall error',ylabel='Paired rainfall-loss ratio (lower better)')
    axes[1].axhline(0,color='#333',lw=.8);axes[1].set(title='Temperature tradeoffs',ylabel='Monthly MAE change °C (lower better)')
    fig.suptitle('Stable thermal separation — fixed mechanism test',fontsize=15)
    fig.savefig(out/'separated_thermal_scorecard.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for row,region in enumerate(FOCUS):
        for col,base in enumerate(('legacy','hydro')):
            ax=axes[row,col]
            for suffix,color,label in [('control','#9d793e','Old wind closure'),('single','#a6a6a6','Single-pattern closure'),('thermal','#1c8490','Separated closure')]:
                if base+'_'+suffix not in report['regions'][region]:continue
                m=report['regions'][region][base+'_'+suffix]['full_land']['monthly']
                ax.plot(months,-np.array(m['rain']).sum(1),color=color,label=label,lw=2)
            ax.plot(months,m['observed_rain'],color='#252930',label='Observed',lw=2)
            ax.set(title=region.replace('_',' ').title()+' · '+base+' ocean',xticks=months,xticklabels=list('JFMAMJJASOND'),ylabel='Rain mm/month');ax.grid(alpha=.2)
            if row==0 and col==0:ax.legend(fontsize=9)
    fig.suptitle('Seasonal rainfall: all three regions and both ocean settings\nSame full scoring land masks, true area and Gregorian months',fontsize=14)
    fig.savefig(out/'separated_thermal_rainfall.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for row,(region,kind) in enumerate([('north_india','land'),('mexico','land'),('pacific_nw','ocean')]):
        for col,level in enumerate(('925','700')):
            ax=axes[row,col]
            for comp,style in [(0,'-'),(1,'--')]:
                for name,color,label in [('hydro_control','#9d793e','Old'),('hydro_single','#a6a6a6','Single'),('hydro_thermal','#1c8490','Separated')]:
                    d=report['regions'][region][name]['pressure_levels'][kind][level]
                    ax.plot(months,np.array(d['monthly_model'])[:,comp],style,color=color,label=label+' '+['east','north'][comp])
                ax.plot(months,np.array(d['monthly_reference'])[:,comp],style,color='#252930',label='NCEP '+['east','north'][comp])
            ax.axhline(0,color='#777',lw=.7);ax.grid(alpha=.2);ax.set(title=f"{region.replace('_',' ').title()} · {kind} · {level} hPa",ylabel='Wind m/s',xticks=months,xticklabels=list('JFMAMJJASOND'))
            if row==0 and col==0:ax.legend(ncol=3,fontsize=8)
    fig.suptitle('Circulation at matched pressure levels — hydrostatic-half ocean\nIdentical native925hPa-valid footprints; model two-box representation',fontsize=14)
    fig.savefig(out/'separated_thermal_pressure_levels.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,4,figsize=(17,12),layout='constrained')
    for row,region in enumerate(FOCUS):
        control=maps[region,'hydro_control'];candidate=maps[region,'hydro_thermal'];single=maps[region,'hydro_single'];mask=control['mask']
        values=[control['observed'],control['rain'],single['rain'],candidate['rain']];limit=max(float(np.percentile(v[mask],98)) for v in values)
        for col,value in enumerate(values):
            ax=axes[row,col];ax.set_facecolor('#dceaf2');im=ax.pcolormesh(control['lon'],control['lat'],np.ma.masked_where(~mask,value),vmin=0,vmax=limit,cmap='YlGnBu',shading='auto')
            ax.set(title=f"{region.replace('_',' ').title()} · {FOCUS[region]}\n"+['Observed','Original wind closure','Single-pattern closure','Separated closure'][col],xlabel='Longitude',ylabel='Latitude')
            ax.set_xlim(control['lon'][mask].min(),control['lon'][mask].max());ax.set_ylim(control['lat'][mask].min(),control['lat'][mask].max())
            fig.colorbar(im,ax=ax,shrink=.75,label='mm/season')
    fig.suptitle('Where rainfall changes — fixed hydrostatic-half ocean setting\nRegional color scales shared, clipped at98th percentile; experimental climate, not adopted atlas',fontsize=14)
    fig.savefig(out/'separated_thermal_rain_maps.png',dpi=150);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve()
    receipt,report,maps=verify(out);plot(out,report,maps)
    from audit_separated_structure import plot as plot_structure
    plot_structure(out,report['regions'])
    report['thermal_auditor_sha256']=file_hash(ROOT/'scripts/audit_separated_structure.py')
    report['shear_verifier_sha256']=file_hash(ROOT/'scripts/verify_separated_shear.py')
    report['analyzer_sha256']=file_hash(Path(__file__));report['images_sha256']={p.name:file_hash(p) for p in sorted(out.glob('separated_thermal_*.png'))}
    write_json(out/'scientific_verification.json',receipt);write_json(out/'analysis.json',report)
    print(json.dumps(report['scores'],indent=2))


if __name__=='__main__':main()
