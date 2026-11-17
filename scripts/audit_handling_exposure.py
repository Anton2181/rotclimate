"""Read-only handling quantities at all original Earth monthly town nodes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/urban_handling_exposure_20261117'
PLAN = ROOT/'calibration/urban_diagnosis_20261117/handling_exposure_release5_baseline.json'
PARENT_PLAN = ROOT/'calibration/urban_diagnosis_20261117/warehouse_handling_exposure.json'
MONTHLY = ROOT/'output/urban_earth_monthly_20261116'
PREPARED = ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'
R5 = ROOT/'output/settlement_provisional_release5_20261117'
KCAL = 912500.


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def verify_parents():
    """Resolve authorized historical publication differences, with exact hashes."""
    baseline=read(R5/'baseline.json');allowed=baseline['archived_live_sha256']
    current={};sources={};remapped={};checked=0
    for folder in [MONTHLY,ROOT/'output/urban_warehouse_no_hold_20261117',ROOT/'output/urban_original_work_map_20261117']:
        qpath=folder/'qualification.json';q=read(qpath)
        assert q['status'].startswith('passed_')
        sources[str(qpath.relative_to(ROOT))]=sha(qpath)
        for kind,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q.get(kind,{}).items():
                path=prefix/name;relative=str(path.relative_to(ROOT));live=sha(path)
                if live!=digest:
                    assert relative in allowed and allowed[relative]==digest,relative
                    archived=R5/'baseline'/relative;assert sha(archived)==digest
                    remapped[relative]=dict(expected_sha256=digest,live_sha256=live,archive=str(archived.relative_to(ROOT)))
                current[relative]=live;checked+=1
    publication=read(R5/'publication.json')
    for name,digest in publication['files_sha256'].items():
        assert sha(ROOT/name)==digest,name
        current[name]=digest
    for name in allowed:
        current[name]=sha(ROOT/name)
    for path in [R5/'baseline.json',R5/'publication.json',R5/'deployment.json']:
        current[str(path.relative_to(ROOT))]=sha(path)
    return sources,current,remapped,checked


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (out/'results.json').exists(),'Preserve completed audit; use --out for an isolated replay'
    sources,protected,remapped,checks=verify_parents()
    paths=[Path(__file__),PLAN,PARENT_PLAN]
    arrays={};rows=[];months=[];summaries=[];frames={};geometry=None
    for reading in ['central','low']:
        archive=MONTHLY/'cases'/reading/'fields.npz';prepared=PREPARED/f'low_{reading}.npz'
        paths.extend([archive,prepared])
        with np.load(archive) as z:
            a={k:z[k] for k in ['request','direct','inter_received','inter_exported','arrivals','shipments']}
        with np.load(prepared) as z:
            g={k:z[k] for k in ['nodes','residents','lat','grid_lon','land','cell_km']}
        np.testing.assert_array_equal(a['request'],g['residents'])
        nodes=g['nodes'];n=len(nodes);assert n==1085 and len(np.unique(nodes))==n
        assert nodes.dtype.kind in 'iu' and np.all(g['land'].ravel()[nodes])
        assert a['arrivals'].shape==(12,n) and a['inter_exported'].shape==(12,n)
        for key in a:
            assert np.isfinite(a[key]).all() and (a[key]>=0).all(),key
        np.testing.assert_array_equal(a['arrivals'],a['direct']+a['inter_received'])
        shipment=a['shipments'];assert shipment.shape[1]==5
        identifiers=shipment[:,:3].astype(int)
        np.testing.assert_array_equal(identifiers,shipment[:,:3])
        m,i,j=identifiers.T
        assert np.all((m>=0)&(m<12)&(i>=0)&(i<n)&(j>=0)&(j<n)&(i!=j))
        assert (shipment[:,4]<=shipment[:,3]).all()
        assert np.all(m[1:]>=m[:-1]),'Original chronological shipment order'
        sent=np.zeros((12,n));received=sent.copy()
        np.add.at(sent,(m,i),shipment[:,3]);np.add.at(received,((m+1)%12,j),shipment[:,4])
        np.testing.assert_array_equal(sent,a['inter_exported'])
        np.testing.assert_array_equal(received,a['inter_received'])
        qin=a['arrivals'].copy();qout=a['inter_exported'].copy();request=a['request'];defined=request>0
        annual_in=qin.sum(0);annual_out=qout.sum(0)
        peak_in=qin.max(0);peak_out=qout.max(0)
        ratios={}
        for direction,values in [('in',annual_in),('out',annual_out)]:
            ratios[direction]=np.divide(values,request*KCAL,out=np.full(n,np.nan),where=defined)
        for key,value in [('nodes',nodes),('request',request),('qin',qin),('qout',qout),('ratio_defined',defined),
                          ('annual_in_kcal',annual_in),('annual_out_kcal',annual_out),('peak_in_kcal',peak_in),('peak_out_kcal',peak_out),
                          ('annual_in_rations_per_request',ratios['in']),('annual_out_rations_per_request',ratios['out'])]:
            arrays[reading+'__'+key]=value
        lat=g['lat'].ravel()[nodes];lon=g['grid_lon'].ravel()[nodes]
        for k,node in enumerate(nodes):
            row=dict(reading=reading,town_index=k,node=int(node),latitude=float(lat[k]),longitude=float(lon[k]),fixed_requested_residents=float(request[k]),
                     incoming_annual_kcal=float(annual_in[k]),outgoing_annual_kcal=float(annual_out[k]),
                     incoming_peak_bin_kcal=float(peak_in[k]),outgoing_peak_bin_kcal=float(peak_out[k]),
                     incoming_peak_bins=json.dumps(np.flatnonzero(qin[:,k]==peak_in[k]).tolist()) if peak_in[k]>0 else '',
                     outgoing_peak_bins=json.dumps(np.flatnonzero(qout[:,k]==peak_out[k]).tolist()) if peak_out[k]>0 else '',
                     incoming_active_bins=int((qin[:,k]>0).sum()),outgoing_active_bins=int((qout[:,k]>0).sum()),
                     incoming_annual_rations_per_requested_resident=float(ratios['in'][k]) if defined[k] else '',
                     outgoing_annual_rations_per_requested_resident=float(ratios['out'][k]) if defined[k] else '',
                     incoming_peak_bin_kcal_per_requested_resident=float(peak_in[k]/request[k]) if defined[k] else '',
                     outgoing_peak_bin_kcal_per_requested_resident=float(peak_out[k]/request[k]) if defined[k] else '',
                     handling_rate_in_hours_per_kcal='UNKNOWN',handling_rate_out_hours_per_kcal='UNKNOWN',handling_hours='UNKNOWN')
            rows.append(row)
        for month in range(12):
            months.append(dict(reading=reading,bin=month,incoming_kcal=float(qin[month].sum()),outgoing_kcal=float(qout[month].sum()),
                               direct_arrivals_kcal=float(a['direct'][month].sum()),inter_arrivals_kcal=float(received[month].sum()),
                               outgoing_shipment_rows=int((m==month).sum()),incoming_shipment_rows=int(((m+1)%12==month).sum())))
        summary=dict(reading=reading,towns=n,fixed_requested_residents=float(request.sum()),undefined_ratio_towns=int((~defined).sum()),
                     incoming_annual_kcal=float(annual_in.sum()),outgoing_annual_kcal=float(annual_out.sum()),
                     incoming_zero_towns=int((annual_in==0).sum()),outgoing_zero_towns=int((annual_out==0).sum()),
                     incoming_positive_town_bins=int((qin>0).sum()),outgoing_positive_town_bins=int((qout>0).sum()),
                     ordered_shipments=len(shipment),year_wrap_shipment_rows=int((m==11).sum()),
                     year_wrap_sent_kcal=float(shipment[m==11,3].sum()),year_wrap_received_kcal=float(shipment[m==11,4].sum()),
                     handling_hours=None,handling_rates_qualified=False)
        for direction in ['in','out']:
            v=ratios[direction];summary[direction+'_map_positive_under_scale']=int((defined&(v>0)&(v<.01)).sum())
            summary[direction+'_map_positive_over_scale']=int((defined&(v>10)).sum())
        summaries.append(summary);frames[reading]=(lat,lon,ratios)
        if geometry is None:geometry={k:g[k] for k in ['land','lat','grid_lon','cell_km']}
        else:
            for key,value in geometry.items():np.testing.assert_array_equal(value,g[key])
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'exposure.npz',**arrays)
    table(out/'towns.csv',rows);table(out/'months.csv',months);write(out/'summary.json',summaries)
    write(out/'symbolic_work.json',dict(quantity_units='net edible kcal',rates=dict(h_in='UNKNOWN hours / net edible kcal',h_out='UNKNOWN hours / net edible kcal'),
        annual_hours='sum_m(qin[m])*h_in + sum_m(qout[m])*h_out',peak_bin_hours='max_m(qin[m]*h_in + qout[m]*h_out)',
        separate_peak_warning='Separate incoming and outgoing peaks need not be in the same bin. Preserve the paired monthly vectors.',
        incoming_export_double_count_warning='Incoming and outgoing are distinct hypothetical handling events on paid grain, not added grain or capacity.',
        request_denominator='Fixed original resident request; not observed, newly inferred or food-supported population.',
        field_work_slack_used=False,warehouse_staff_assigned=False,actual_warehouse_locations_inferred=False))
    fig,axes=plt.subplots(2,2,figsize=(14,10),sharex=True,sharey=True)
    dots=None
    for col,reading in enumerate(['central','low']):
        lat,lon,ratios=frames[reading]
        for row,direction in enumerate(['in','out']):
            ax=axes[row,col];land=geometry['land'];glat=geometry['lat'];glon=geometry['grid_lon']
            ax.contourf(glon,glat,land.astype(int),levels=[.5,1.5],colors=['#eeeee9'])
            ax.contour(glon,glat,land.astype(int),levels=[.5],colors=['#999e9b'],linewidths=.35)
            v=ratios[direction];zero=v==0;positive=np.isfinite(v)&(v>0)
            ax.scatter(lon[zero],lat[zero],s=8,c='#888d90',linewidths=0,zorder=3)
            dots=ax.scatter(lon[positive],lat[positive],s=9,c=v[positive],cmap='viridis',norm=LogNorm(.01,10),linewidths=0,zorder=4)
            ax.set(xlim=(-17,51),ylim=(23,56));ax.set_aspect(1/np.cos(np.deg2rad(38)));ax.grid(alpha=.15)
            ax.set_title(reading.capitalize()+' · annual '+('incoming' if direction=='in' else 'outgoing')+' quantity')
            if row==1:ax.set_xlabel('Longitude (°E)')
            if col==0:ax.set_ylabel('Latitude (°N)')
    fig.subplots_adjust(left=.06,right=.88,top=.86,bottom=.16,hspace=.2,wspace=.1)
    bar=fig.add_axes([.91,.24,.014,.5]);fig.colorbar(dots,cax=bar,extend='both',label='Annual ration equivalents / fixed requested resident')
    fig.suptitle('Original Earth town handling exposure · rates and staff unknown',fontsize=16,y=.97)
    fig.text(.5,.91,'All 1,085 original nodes per reading; identical scales. Incoming after freight, outgoing before freight.',ha='center',fontsize=10)
    fig.legend(handles=[Line2D([],[],marker='o',linestyle='',color='#888d90',label='Exactly zero movement')],loc='lower center',bbox_to_anchor=(.5,.085),frameon=False)
    fig.text(.5,.035,'Movement quantities only: no handling hours, warehouse capacity, staffing allocation or new food run.\nOriginal Earth portability scenarios; these are not the fantasy provisional-r5 towns.',ha='center',fontsize=9)
    fig.savefig(out/'handling_exposure.png',dpi=180);plt.close(fig)
    for path in paths:sources[str(path.relative_to(ROOT))]=sha(path)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    names=['exposure.npz','towns.csv','months.csv','summary.json','symbolic_work.json','handling_exposure.png']
    write(out/'results.json',dict(status='read_only_all_original_town_handling_exposure_pending_independent_review',sources_sha256=sources,
        protected_sha256=protected,historical_publication_remappings=remapped,historical_identity_checks=checks,files_sha256={n:sha(out/n) for n in names},
        cases=2,town_rows=len(rows),town_bins=26040,shipment_rows=sum(s['ordered_shipments'] for s in summaries),
        positive_map_scale=[.01,10],zero_map_separate=True,all_original_nodes_included=True,
        zero_request_ratios_undefined=True,grain_movements_changed=False,handling_rates_qualified=False,
        solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,actual_warehouse_mappings=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print('Audited',len(rows),'towns;',sum(s['ordered_shipments'] for s in summaries),'ordered shipments; no rates or staff inferred',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=OUT);main(parser.parse_args().out)
