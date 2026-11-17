"""Independent HTML/PDF transcription and Decimal source-column diagnostics."""
import csv
from decimal import Decimal
from html import unescape
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_ostia_store import OUT,sha,read,write


def plain(value):return unescape(re.sub('<[^>]+>','',value))
def compact(value):return re.sub(r'\s+','',unicodedata.normalize('NFKC',value)).replace('.',',')


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed review'
    r=read(OUT/'results.json');assert r['status'].startswith('completed_one_complex_Ostia')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name,digest in r['local_source_sha256'].items():assert sha(OUT/name)==digest,name
    html=(OUT/'source/chapter.html').read_text()
    fragments=re.findall(r'<p class="texte">(.*?)</p>',html,re.S)
    paragraphs={int(m.group(1)):fragment for fragment in fragments if (m:=re.search(r'id="para-(\d+)"',fragment))}
    assert set(paragraphs)==set(range(1,82))
    notes={int(m.group(1)):fragment for fragment in re.findall(r'<p class="notesbaspage">(.*?)</p>',html,re.S)
           if (m:=re.search(r'id="ftn(\d+)"',fragment))}
    pdf=OUT/'source/halshs-01441802-mirror.pdf'
    pages=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True).split('\f')
    table_fragment=re.search(r'<table id="Table1".*?</table>',html,re.S).group(0)
    table_rows=[[' '.join(plain(cell).split()) for cell in re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)] for row in re.findall(r'<tr>(.*?)</tr>',table_fragment,re.S)]
    published=list(csv.DictReader((OUT/'capacity_estimates.csv').open()));assert len(published)==7
    for row,cells in zip(published,table_rows[1:]):
        assert [row[key] for key in ['group','volume_m3','modii','estimated_tonnes']]==cells
        for value in cells[1:]:
            for endpoint in value.split(' - '):assert compact(endpoint.replace('ca.','')) in compact(pages[217-171])
        assert row['adopt']=='False'
    numerical=list(csv.DictReader((OUT/'numeric_claims.csv').open()));assert len(numerical)==61
    failures=[];checks=0
    for row in numerical:
        fragment=paragraphs[int(row['paragraph'])]
        footnotes=[notes[int(n)] for n in re.findall(r'id="bodyftn(\d+)"',fragment)]
        text=compact(plain(fragment+' '.join(footnotes)))
        tokens=row['source_value'].split('|')
        for token in tokens:
            aliases=[compact(token)]
            if row['field']=='chosen_pile_width_fraction':aliases=['deuxtiers']
            elif row['field']=='unloading_time_example':aliases=['unesemaine']
            elif row['field']=='Rome_demand_denominator':aliases=['50millions']
            elif row['field']=='outbound_cycle_parts' and token=='0,5':aliases=['demi-journée']
            if not any(alias in text for alias in aliases):failures.append([row['field'],'HTML',token])
            checks+=1
        assert row['source_claim_only']=='True' and row['model_parameter_adopted']=='False'
    assert not failures,failures
    # Recompute diagnostics from published raw strings without sharing producer
    # parsing/arithmetic;there is no repaired table or fitted density here.
    checks_csv=list(csv.DictReader((OUT/'source_column_checks.csv').open()));assert len(checks_csv)==10
    for row in checks_csv:
        volume=Decimal(row['reported_volume_m3']);modii=Decimal(row['reported_modii'])
        expected=modii*Decimal('8.76')/1000
        assert Decimal(row['implied_volume_from_source_modius_m3'])==expected
        assert Decimal(row['reported_minus_implied_volume_m3'])==volume-expected
        assert Decimal(row['mass_from_reported_volume_and_source_density_tonnes'])==volume*Decimal('740')/1000
    north=next(row for row in checks_csv if row['group']=='Nord')
    central=next(row for row in checks_csv if row['group']=='Pièces centrales' and row['endpoint']=='1')
    assert Decimal(north['reported_minus_implied_volume_m3'])==Decimal('79.43728')
    assert Decimal(central['reported_minus_implied_volume_m3'])==Decimal('18.00096')
    # Original PDF page and publisher footnote both retain the problematic
    # dimensional expression. Visual inspection of p217 is recorded separately.
    assert 'l²' in unicodedata.normalize('NFC',pages[217-171]) or 'l2' in pages[217-171]
    assert 'l<sup>2</sup>)/4' in notes[114]
    issues=read(OUT/'source_issues.json');assert issues['printed_formula_term_length_exponents']==[3,2]
    assert issues['source_table_not_reconciled'] and issues['source_formula_not_implemented_or_corrected']
    interface=read(OUT/'interface.json');assert interface['conversion_result']['geometric_net_energy_kcal'] is None
    assert not interface['conversion_result']['empirically_qualified'] and not interface['model_origin_or_city_crossing_performed']
    coverage=list(csv.DictReader((OUT/'coverage.csv').open()));assert [int(row['paragraph']) for row in coverage]==list(range(1,82))
    identity=read(OUT/'source_identity.json');assert identity['chapter_doi']=='10.4000/books.efr.32815'
    assert identity['collection']==522 and identity['printed_pages']==[177,226]
    receipt=dict(status='passed_Ostia_source_transcription_with_unresolved_numeric_consistency',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),publisher_paragraphs=81,numeric_source_claims=61,numeric_token_checks=checks,
        capacity_estimate_rows=7,independent_source_column_checks=10,north_volume_residual_m3='79.43728',
        central_sack_volume_residual_m3='18.00096',printed_dimensional_issue_retained=True,source_capacities_reconciled=False,
        historical_operational_capacities_qualified=0,geometric_net_energy_computed=False,network_attachments=0,
        food_kernel_calls=0,new_food_scenarios=0,new_fit=False,new_validation_claim=False,adopt=False)
    write(OUT/'review.json',receipt);print(receipt,flush=True)


if __name__=='__main__':main()
