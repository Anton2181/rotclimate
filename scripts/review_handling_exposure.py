"""Independent ordered scalar movement and all-node exposure review; no solver."""
import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'output/urban_handling_exposure_20261117'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116/cases'
PREPARED=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'
KCAL=912500.


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def table(p):
    with p.open() as f:return list(csv.DictReader(f))


def close(actual,expected):
    assert math.isclose(float(actual),float(expected),rel_tol=2e-14,abs_tol=1e-8),(actual,expected)


def main(out):
    assert not (out/'review.json').exists(),'Preserve independent review; use isolated --out'
    r=read(out/'results.json')
    assert r['status']=='read_only_all_original_town_handling_exposure_pending_independent_review'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(out/name)==digest,name
    for name,mapping in r['historical_publication_remappings'].items():
        assert sha(ROOT/name)==mapping['live_sha256']
        assert sha(ROOT/mapping['archive'])==mapping['expected_sha256']
    rows=table(out/'towns.csv');monthly=table(out/'months.csv');summaries=read(out/'summary.json')
    assert len(rows)==2170 and len(monthly)==24 and len(summaries)==2
    comparisons=town_bins=shipments=0;cases=[];maxannual=0.
    with np.load(out/'exposure.npz') as z:
        for reading,summary in zip(['central','low'],summaries):
            with np.load(MONTHLY/reading/'fields.npz') as a:
                request=a['request'];arrivals=a['arrivals'];direct=a['direct'];oldreceived=a['inter_received'];oldexported=a['inter_exported'];moves=a['shipments']
            with np.load(PREPARED/f'low_{reading}.npz') as p:
                nodes=p['nodes'];residents=p['residents'];lat=p['lat'].ravel()[nodes];lon=p['grid_lon'].ravel()[nodes]
            n=len(nodes);assert n==1085
            np.testing.assert_array_equal(z[reading+'__nodes'],nodes)
            np.testing.assert_array_equal(z[reading+'__request'],residents)
            np.testing.assert_array_equal(request,residents)
            outgoing=[[0.]*n for _ in range(12)];incoming=[[0.]*n for _ in range(12)]
            wrap_sent=[];wrap_received=[]
            for m,i,j,sent,got in moves:
                assert m==int(m) and i==int(i) and j==int(j)
                m,i,j=int(m),int(i),int(j)
                assert 0<=m<12 and 0<=i<n and 0<=j<n and i!=j and 0<=got<=sent
                outgoing[m][i]+=float(sent);incoming[(m+1)%12][j]+=float(got)
                if m==11:wrap_sent.append(float(sent));wrap_received.append(float(got))
                shipments+=1
            np.testing.assert_array_equal(outgoing,oldexported)
            np.testing.assert_array_equal(incoming,oldreceived)
            np.testing.assert_array_equal(arrivals,direct+oldreceived)
            np.testing.assert_array_equal(z[reading+'__qin'],arrivals)
            np.testing.assert_array_equal(z[reading+'__qout'],outgoing)
            selected=[row for row in rows if row['reading']==reading];assert len(selected)==n
            for i,row in enumerate(selected):
                assert int(row['town_index'])==i and int(row['node'])==int(nodes[i])
                assert float(row['latitude'])==float(lat[i]) and float(row['longitude'])==float(lon[i])
                assert float(row['fixed_requested_residents'])==request[i]
                known=request[i]>0;assert bool(z[reading+'__ratio_defined'][i])==known
                for direction,values,annual_key,peak_key in [('incoming',arrivals,'in','in'),('outgoing',outgoing,'out','out')]:
                    vector=[float(values[m][i]) for m in range(12)]
                    total=math.fsum(vector);peak=max(vector)
                    peak_bins=[m for m in range(12) if vector[m]==peak] if peak>0 else []
                    assert (json.loads(row[direction+'_peak_bins']) if row[direction+'_peak_bins'] else [])==peak_bins
                    close(row[direction+'_annual_kcal'],total);close(row[direction+'_peak_bin_kcal'],peak)
                    assert int(row[direction+'_active_bins'])==sum(v>0 for v in vector)
                    actual=float(z[reading+'__annual_'+annual_key+'_kcal'][i]);maxannual=max(maxannual,abs(actual-total));close(actual,total)
                    assert float(z[reading+'__peak_'+peak_key+'_kcal'][i])==peak
                    if known:
                        ratio=total/(float(request[i])*KCAL)
                        close(row[direction+'_annual_rations_per_requested_resident'],ratio)
                        close(z[reading+'__annual_'+annual_key+'_rations_per_request'][i],ratio)
                        close(row[direction+'_peak_bin_kcal_per_requested_resident'],peak/request[i])
                    else:
                        assert row[direction+'_annual_rations_per_requested_resident']==row[direction+'_peak_bin_kcal_per_requested_resident']==''
                        assert math.isnan(float(z[reading+'__annual_'+annual_key+'_rations_per_request'][i]))
                    comparisons+=12
                assert all(row[k]=='UNKNOWN' for k in ['handling_rate_in_hours_per_kcal','handling_rate_out_hours_per_kcal','handling_hours'])
                town_bins+=12
            for month,row in enumerate(v for v in monthly if v['reading']==reading):
                assert int(row['bin'])==month
                for column,values in [('incoming_kcal',arrivals),('outgoing_kcal',outgoing),('direct_arrivals_kcal',direct),('inter_arrivals_kcal',incoming)]:
                    close(row[column],math.fsum(float(v) for v in values[month]))
                assert int(row['outgoing_shipment_rows'])==sum(m[0]==month for m in moves)
                assert int(row['incoming_shipment_rows'])==sum((m[0]+1)%12==month for m in moves)
            assert summary['reading']==reading and summary['towns']==n and summary['handling_hours'] is None
            assert summary['handling_rates_qualified'] is False
            close(summary['fixed_requested_residents'],math.fsum(request))
            assert summary['undefined_ratio_towns']==sum(request<=0)
            for direction,values,key in [('incoming',arrivals,'in'),('outgoing',outgoing,'out')]:
                annual=[math.fsum(float(values[m][i]) for m in range(12)) for i in range(n)]
                close(summary[direction+'_annual_kcal'],math.fsum(annual))
                assert summary[direction+'_zero_towns']==sum(v==0 for v in annual)
                assert summary[direction+'_positive_town_bins']==sum(float(v)>0 for month in values for v in month)
                ratios=[value/(person*KCAL) for value,person in zip(annual,request) if person>0]
                assert summary[key+'_map_positive_under_scale']==sum(0<v<.01 for v in ratios)
                assert summary[key+'_map_positive_over_scale']==sum(v>10 for v in ratios)
            assert summary['ordered_shipments']==len(moves) and summary['year_wrap_shipment_rows']==len(wrap_sent)
            close(summary['year_wrap_sent_kcal'],math.fsum(wrap_sent));close(summary['year_wrap_received_kcal'],math.fsum(wrap_received))
            cases.append(dict(reading=reading,towns=n,exact_monthly_exposure_values=24*n,ordered_shipments=len(moves),year_wrap_rows=len(wrap_sent),all_zero_movement_nodes_retained=True))
    symbolic=read(out/'symbolic_work.json')
    assert all('UNKNOWN' in value for value in symbolic['rates'].values())
    assert symbolic['peak_bin_hours']=='max_m(qin[m]*h_in + qout[m]*h_out)'
    assert symbolic['field_work_slack_used'] is symbolic['warehouse_staff_assigned'] is symbolic['actual_warehouse_locations_inferred'] is False
    tree=ast.parse((ROOT/'scripts/audit_handling_exposure.py').read_text())
    modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):modules.extend(a.name.split('.')[0] for a in node.names)
        if isinstance(node,ast.ImportFrom):modules.append(node.module.split('.')[0])
    assert set(modules)<={'argparse','csv','hashlib','json','pathlib','subprocess','matplotlib','numpy'}
    for flag in ['solver_calls','new_Earth_food_scenarios','new_staff_allocations','actual_warehouse_mappings']:assert r[flag]==0
    for flag in ['actual_population_changed','new_fit','new_validation_claim','adopt','main_atlas_changed','grain_movements_changed','handling_rates_qualified']:assert r[flag] is False
    assert town_bins==r['town_bins']==26040 and shipments==r['shipment_rows']==15896
    assert comparisons==52080 and r['positive_map_scale']==[.01,10] and r['zero_map_separate']
    receipt=dict(status='passed_independent_all_node_ordered_shipments_exposures_ratios_and_plot_values',
                 reviewer_sha256=sha(Path(__file__)),results_sha256=sha(out/'results.json'),cases=cases,
                 monthly_quantities_checked=comparisons,town_bins=town_bins,ordered_shipments=shipments,
                 maximum_compensated_annual_sum_difference_kcal=maxannual,historical_publication_remappings=len(r['historical_publication_remappings']),
                 publication_unchanged=True,rate_free=True,solver_imports_absent=True,solver_calls=0,new_fit=False,new_validation_claim=False,adopt=False)
    (out/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Independent review passed:',comparisons,'monthly quantities;',shipments,'ordered shipments; fixed nodes/requests and symbolic rates',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=DEFAULT);main(parser.parse_args().out)
