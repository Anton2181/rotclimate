"""Export every destination-provider/accounting row,including unscored sources."""
import argparse,csv,gzip,io,json,sys
from math import fsum
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_filled_destination_20261113'

def main(out=OUT):
    out.mkdir(parents=True,exist_ok=True);r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json');b=io.StringIO(newline='');writer=None;count=0
    for row in r['rows']:
        fields=dict(np.load(OUT/(row['case']+'_fields.npz')));account=row['accounting'];names=[n.removeprefix(account+'__') for n in fields if n.startswith(account+'__')]
        for j in range(len(fields['people'])):
            record=dict(case=row['case'],accounting=account,provider=j,actor=int(fields['actor'][j]),scored=bool(fields['active'][j]),people=float(fields['people'][j]),staff=float(fields['staff'][j]),capacity=float(fields['capacity'][j]),mandatory_complete=bool(fields['mandatory_complete'][j]),source_rural_food_pass=bool(fields['source_rural_food_pass'][j]),source_export_request_pass=bool(fields['source_export_request_pass'][j]),source_both_pass=bool(fields['source_both_pass'][j]))
            record.update({name:fields[account+'__'+name][j].item() for name in names})
            if writer is None:writer=csv.DictWriter(b,fieldnames=list(record));writer.writeheader()
            writer.writerow(record);count+=1
    path=out/'providers.csv.gz';path.write_bytes(gzip.compress(b.getvalue().encode(),mtime=0));transport=[]
    for row in (v for v in r['rows'] if v['accounting']=='B'):
        case=row['case'];d=dict(np.load(OUT/(case+'_fields.npz')));s=dict(np.load(ROOT/'output/source_food_events_20261113'/(case+'_fields.npz')))
        requested=float(s['pickup__requested'].sum());withdrawn=float(s['pickup__withdrawn'].sum());unfilled=float(s['pickup__unfilled'].sum());retained=float(d['B__harvested'].sum());loss=withdrawn*.05
        assert abs(retained-withdrawn*.95)<=1e-10*max(1.,withdrawn)
        terms={name:float(s[name].sum()) for name in ['rural__initial_stock','export__initial_stock','rural__harvested','rural__final_stock','export__final_stock','rural__consumed','rural__spoiled','export__spoiled','uncollected']}
        terms.update({name:float(d['B__'+name].sum()) for name in ['initial_stock','final_stock','consumed','spoiled','overflow']})
        residual=fsum([terms[n] for n in ['rural__initial_stock','export__initial_stock','rural__harvested','initial_stock']]+[-terms[n] for n in ['rural__final_stock','export__final_stock','rural__consumed','rural__spoiled','export__spoiled','uncollected','final_stock','consumed','spoiled','overflow']]+[-loss])
        assert abs(residual)<=1e-9*max(1.,terms['rural__harvested'])
        transport.append(dict(case=case,raw_packed_request=requested,raw_source_withdrawn=withdrawn,raw_source_unfilled=unfilled,diagnostic_transport_loss_on_withdrawn_only=loss,retained_destination_B=retained,counterfactual_retained_unfilled_potential=unfilled*.95,source_and_active_destination_ledger_residual=residual,terms=terms,scope='All local rural/export sources and scored active destinations;inactive destination meals/outside cells unscored. Source rural deficits remain,so this is conservation rather than complete provisioning qualification.'))
    write(out/'transport_and_chain_mass.json',transport)
    write(out/'exports.json',dict(status='exported_every_matched_destination_provider',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),files_sha256={path.name:sha(path),'transport_and_chain_mass.json':sha(out/'transport_and_chain_mass.json')},provider_rows=count,scope='All A/B provider food and source/mandatory flags separate;inactive explicitly unscored. Destination B is a diagnostic,not certified source provisioning.'));print('Exported',count,'destination-provider rows')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
