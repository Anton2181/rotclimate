"""Check every provider CSV field and the source-to-destination grain ledger."""
import csv,gzip,json,sys
from math import fsum
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_filled_destination_20261113'

def main():
    e=json.loads((OUT/'exports.json').read_text());r=json.loads((OUT/'results.json').read_text());assert e['results_sha256']==sha(OUT/'results.json') and e['producer_sha256']==sha(ROOT/'scripts/export_source_filled_destination.py')
    for n,d in e['files_sha256'].items():assert sha(OUT/n)==d
    count=0;cache={};seen=set()
    with gzip.open(OUT/'providers.csv.gz','rt',newline='') as stream:
        for v in csv.DictReader(stream):
            case=v['case'];a=v['accounting'];j=int(v['provider']);identity=(case,a,j);assert identity not in seen;seen.add(identity)
            if case not in cache:cache={case:dict(np.load(OUT/(case+'_fields.npz')))}
            f=cache[case];expected={n:f[field][j].item() for n,field in [('actor','actor'),('scored','active'),('people','people'),('staff','staff'),('capacity','capacity'),('mandatory_complete','mandatory_complete'),('source_rural_food_pass','source_rural_food_pass'),('source_export_request_pass','source_export_request_pass'),('source_both_pass','source_both_pass')]};expected.update({n.removeprefix(a+'__'):q[j].item() for n,q in f.items() if n.startswith(a+'__')});assert set(v)==set(expected)|{'case','accounting','provider'}
            for n,q in expected.items():assert v[n]==str(q) if isinstance(q,bool) else float(v[n])==q,(case,a,j,n)
            count+=1
    assert count==e['provider_rows']==sum(len(np.load(OUT/(v['case']+'_fields.npz'))['people']) for v in r['rows'])
    records=json.loads((OUT/'transport_and_chain_mass.json').read_text());assert len(records)==24;largest=0.
    for v in records:
        case=v['case'];d=dict(np.load(OUT/(case+'_fields.npz')));s=dict(np.load(ROOT/'output/source_food_events_20261113'/(case+'_fields.npz')))
        for field,key in [('raw_packed_request','pickup__requested'),('raw_source_withdrawn','pickup__withdrawn'),('raw_source_unfilled','pickup__unfilled')]:assert v[field]==float(s[key].sum())
        assert v['diagnostic_transport_loss_on_withdrawn_only']==v['raw_source_withdrawn']*.05 and v['counterfactual_retained_unfilled_potential']==v['raw_source_unfilled']*.95
        np.testing.assert_allclose(v['raw_source_withdrawn']+v['raw_source_unfilled'],v['raw_packed_request'],rtol=1e-12)
        assert v['retained_destination_B']==float(d['B__harvested'].sum());np.testing.assert_allclose(v['retained_destination_B']+v['diagnostic_transport_loss_on_withdrawn_only'],v['raw_source_withdrawn'],rtol=1e-12)
        t=v['terms']
        for n,value in t.items():assert value==float((s[n] if n in s else d['B__'+n]).sum())
        incoming=fsum((t['rural__initial_stock'],t['export__initial_stock'],t['initial_stock'],t['rural__harvested']));outgoing=fsum(t[n] for n in ['rural__final_stock','export__final_stock','final_stock','rural__consumed','consumed','rural__spoiled','export__spoiled','spoiled','uncollected','overflow'])+v['diagnostic_transport_loss_on_withdrawn_only'];scale=max(1.,incoming);assert abs(incoming-outgoing)<=1e-9*scale;assert abs(v['source_and_active_destination_ledger_residual'])<=1e-9*scale;largest=max(largest,abs(incoming-outgoing)/scale)
        assert not d['source_both_pass'].any() and not d['B__all_gates_pass'].any()
    write(OUT/'export_review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),exports_sha256=sha(OUT/'exports.json'),reviewer_sha256=sha(Path(__file__)),provider_rows_checked=count,source_and_destination_chain_ledgers_checked=24,largest_combined_mass_error_per_incoming_energy=largest,transport_loss_only_on_source_withdrawn_raw=True,all_source_rural_failures_retained=True));print('Destination export review passed',count,'provider rows and24source/destination mass ledgers')
if __name__=='__main__':main()
