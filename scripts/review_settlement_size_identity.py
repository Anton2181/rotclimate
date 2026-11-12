"""Independent review of the housing/catalogue key join from raw workbook XML."""
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
from xml.etree import ElementTree as ET
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from settlement_locations_earth import sha,write

OUT=ROOT/'output/settlement_size_identity_20261112'
CACHE=ROOT/'data/cache/hanson2016'
M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
FIELDS=['Primary Key','Ancient Toponym','Modern Toponym','Province','Country','Barrington Atlas Rank',
    'Barrington Atlas Reference','Start Date','End Date','Longitude (X)','Latitude (Y)','Select Bibliography']


def sheets(path):
    """Read cell text straight from the zip parts; no spreadsheet library."""
    with zipfile.ZipFile(path) as z:
        # Plain <t> or rich-text <r><t> runs only; phonetic <rPh> hints are not cell text.
        strings=[''.join(t.text or '' for part in si if part.tag in (M+'t',M+'r')
                         for t in ([part] if part.tag==M+'t' else part.findall(M+'t')))
                 for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M+'si')] \
            if 'xl/sharedStrings.xml' in z.namelist() else []
        targets={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result={}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).find(M+'sheets'):
            target=targets[sheet.get(R+'id')].lstrip('/')
            root=ET.fromstring(z.read(target if target.startswith('xl/') else 'xl/'+target));table=[]
            for row in root.iter(M+'row'):
                values={}
                for c in row.findall(M+'c'):
                    letters=re.match(r'[A-Z]+',c.get('r')).group(0);column=0
                    for ch in letters:column=column*26+ord(ch)-64
                    kind=c.get('t');v=c.find(M+'v')
                    if kind=='s':value=strings[int(v.text)]
                    elif kind=='inlineStr':value=''.join(t.text or '' for t in c.iter(M+'t'))
                    elif v is None:value=None
                    elif kind in ('str','e'):value=v.text
                    else:value=Fraction(v.text) if re.fullmatch(r'-?\d+(\.\d+)?',v.text) else Fraction(float(v.text))
                    values[column-1]=value
                table.append([values.get(i) for i in range(max(values)+1)] if values else [])
            result[sheet.get('name')]=table
    return result


def numeric(v):return isinstance(v,Fraction)


def squash(text):
    decomposed=unicodedata.normalize('NFKD',str(text))
    return ''.join(ch for ch in decomposed.casefold() if ch.isascii() and ch.isalnum())


def klass(a,b):
    return 'exact' if a==b else 'equal_after_normalisation' if squash(a)==squash(b) else 'different'


def ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i]);out=[0.]*len(values);i=0
    while i<len(order):
        j=i
        while j+1<len(order) and values[order[j+1]]==values[order[i]]:j+=1
        for k in order[i:j+1]:out[k]=(i+j)/2+1
        i=j+1
    return out


def pearson(a,b):
    ma,mb=sum(a)/len(a),sum(b)/len(b)
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))


def close(a,b,tolerance=1e-12):
    assert abs(a-b)<=tolerance*max(1,abs(a),abs(b)),(a,b)


def main():
    result=json.loads((OUT/'results.json').read_text())
    plan=json.loads((ROOT/'calibration/settlement_size_identity_20261112/plan.json').read_text())
    workbook=CACHE/'cities.xlsx';legacy=CACHE/'cities_legacy_export.csv'
    assert sha(workbook)==plan['source_recovery']['pinned_workbook']['sha256']==result['workbook_sha256']
    assert sha(legacy)==plan['source_recovery']['legacy_csv_export']['sha256']
    for path,digest in result['sources_sha256'].items():assert sha(ROOT/path)==digest,path
    book=sheets(workbook);head=book['Cities'][0];assert head==FIELDS
    cities=[dict(zip(head,row+[None]*(len(head)-len(row)))) for row in book['Cities'][1:] if row and row[0]]
    areas=defaultdict(list)
    for row in book['Areas'][1:]:
        if row and row[0]:areas[row[0]].append(row+[None]*(3-len(row)))
    for keys in ([c['Primary Key'] for c in cities],list(areas)):
        assert all(re.fullmatch(r'Hanson2016_[1-9][0-9]*',k) for k in keys) and len(set(keys))==len(keys)

    def standing(c):
        return numeric(c['Start Date']) and c['Start Date']<=150 and (not numeric(c['End Date']) or c['End Date']>=150)

    def measured(c):
        v=areas[c['Primary Key']];return len(v)==1 and numeric(v[0][1]) and v[0][1]>0
    cohort=[c for c in cities if standing(c)]
    gate=dict(cities=len(cities),cities_single_positive_area=sum(map(measured,cities)),
        cities_without_area_record=sum(not areas[c['Primary Key']] for c in cities),AD150_cohort=len(cohort),
        AD150_single_positive_area=sum(map(measured,cohort)),
        AD150_without_area_record=sum(not areas[c['Primary Key']] for c in cohort))
    assert gate==result['recovery_consistency_gate']['counts']
    assert gate==dict(cities=1388,cities_single_positive_area=885,cities_without_area_record=503,AD150_cohort=1354,
        AD150_single_positive_area=862,AD150_without_area_record=492)

    index={c['Primary Key']:c for c in cities}
    with (ROOT/'data/source/roman_housing_2023/table2.csv').open() as f:table={r['city_key']:r for r in csv.DictReader(f)}
    assert len(table)==len(result['rows'])==50 and {r['city_key'] for r in result['rows']}==set(table)
    tallies=Counter();points=defaultdict(list);names=defaultdict(list)
    for r in result['rows']:
        source=table[r['city_key']];c=index['Hanson2016_'+r['city_key']]
        assert r['identity_status']=='catalogue_key_joined' and r['catalogue_primary_key']==c['Primary Key'] and r['catalogue_rows']==1
        assert r['catalogue_ancient_toponym']==c['Ancient Toponym'] and r['catalogue_province']==c['Province']
        assert r['name_agreement']==klass(source['ancient_name'],c['Ancient Toponym'])
        assert r['province_agreement']==klass(source['province'],c['Province'])
        tallies['name_'+r['name_agreement']]+=1;tallies['province_'+r['province_agreement']]+=1
        for field,value in (('catalogue_start',c['Start Date']),('catalogue_end',c['End Date'])):
            assert (Fraction(r[field])==value) if numeric(value) else r[field]==value
        s,e=c['Start Date'],c['End Date']
        date='covers' if numeric(s) and numeric(e) and s<=150<=e else \
             'excludes' if (numeric(s) and s>150) or (numeric(e) and e<150) else 'open_or_nonnumeric'
        assert r['catalogue_AD150']==date and r['catalogue_dates_are_sample_phase'] is False;tallies['date_'+date]+=1
        records=areas[c['Primary Key']];assert r['area_records']==len(records)==1 and numeric(records[0][1]) and records[0][1]>0
        stated=Fraction(source['site_area_ha']);decimals=len(source['site_area_ha'].partition('.')[2])
        state='equal' if abs(records[0][1]-stated)<=Fraction(1,2*10**decimals) else 'different'
        assert r['area_agreement']==state and Fraction(r['catalogue_area_ha'])==records[0][1];tallies['area_'+state]+=1
        close(r['table_over_catalogue_area'],float(stated/records[0][1]))
        assert r['catalogue_estimate_basis']==records[0][2]
        located=numeric(c['Longitude (X)']) and numeric(c['Latitude (Y)'])
        assert r['exposure']['count_audit_AD150_cohort']==bool(standing(c))
        assert r['exposure']['legacy_placement_loader_AD150']==bool(standing(c) and located)
        assert r['exposure']['legacy_loader_area']=='catalogue_area'
        tallies['cohort']+=bool(standing(c));tallies['loader']+=bool(standing(c) and located)
        if located:points[(c['Longitude (X)'],c['Latitude (Y)'])].append(r['city_key'])
        names[squash(c['Ancient Toponym'])].append(r['city_key'])
        n,sample=Fraction(source['properties']),Fraction(source['sample_area_ha'])
        close(r['properties_per_sampled_ha'],float(n/sample));close(r['sample_fraction'],float(sample/stated))
        f=sample/stated
        assert r['sample_fraction_class']==('whole_stated_extent' if f==1 else 'below_1_percent' if f<Fraction(1,100)
            else '1_to_below_10_percent' if f<Fraction(1,10) else '10_to_below_100_percent')
        # No date or area agreement may clear a year-specific gate.
        assert r['AD150_blockers'] and 'site_representativeness_unresolved' in r['AD150_blockers'] \
            and 'contemporaneous_extent_unresolved' in r['AD150_blockers']
    s=result['summary']
    assert s['joined_by_author_key']==50 and s['unjoined']==0 and s['AD150_eligible']==0
    assert s['name_agreement']=={k:tallies['name_'+k] for k in ('exact','equal_after_normalisation','different')}
    assert s['province_agreement']=={k:tallies['province_'+k] for k in ('exact','equal_after_normalisation','different')}
    assert s['area_agreement']=={k[5:]:v for k,v in tallies.items() if k.startswith('area_')}
    assert s['catalogue_AD150']=={k[5:]:v for k,v in tallies.items() if k.startswith('date_')}
    assert s['exposed_in_count_audit_AD150_cohort']==tallies['cohort'] and s['exposed_in_legacy_placement_loader']==tallies['loader']
    assert not result['duplicate_places'] and all(len(v)==1 for v in points.values()) and all(len(v)==1 for v in names.values())
    assert result['place_groups']=={'Hanson2016_'+k:[k] for k in table} and s['place_groups']==50

    rows=result['rows'];density=[r['properties_per_sampled_ha'] for r in rows]
    for name,stats in result['sampling_classes'].items():
        values=sorted(d for d,r in zip(density,rows) if r['sample_fraction_class']==name)
        assert stats['rows']==len(values);middle=len(values)//2
        close(stats['median_properties_per_sampled_ha'],values[middle] if len(values)%2 else (values[middle-1]+values[middle])/2)
        close(stats['min_properties_per_sampled_ha'],values[0]);close(stats['max_properties_per_sampled_ha'],values[-1])
    assert sum(v['rows'] for v in result['sampling_classes'].values())==50
    assert result['permutation']==dict(seed=20261112,shuffles=20000)
    subsets={'all_rows':lambda r:True,'excluding_whole_extent_samples':lambda r:r['sample_fraction']!=1,
        'Britannia':lambda r:r['table_province']=='Britannia','other_provinces':lambda r:r['table_province']!='Britannia'}
    columns={'density_vs_sampled_fraction':'sample_fraction','density_vs_stated_site_area':'table_site_area_ha',
        'density_vs_investigated_area':'sample_area_ha'}
    checked=0;assert set(result['associations'])==set(subsets)
    for label,keep in subsets.items():
        chosen=[r for r in rows if keep(r)];assert set(result['associations'][label])==set(columns)
        for name,column in columns.items():
            stats=result['associations'][label][name];assert stats['n']==len(chosen)
            rx=ranks([r[column] for r in chosen]);ry=ranks([r['properties_per_sampled_ha'] for r in chosen])
            rho=pearson(rx,ry);close(stats['spearman_rho'],rho,1e-10)
            # Same declared seed and shuffle order; correlation recomputed by this reviewer's own routine.
            rng=np.random.default_rng(20261112);a=np.array(rx);a=a-a.mean();hits=0
            for _ in range(20000):
                p=rng.permutation(np.array(ry));p=p-p.mean()
                if abs(float(a@p/math.sqrt(float(a@a)*float(p@p))))>=abs(rho)-1e-12:hits+=1
            close(stats['permutation_p_two_sided'],(hits+1)/20001);checked+=1

    # Cross-check of the Cities sheet against the separately exported legacy CSV.
    with legacy.open(encoding='latin-1',newline='') as f:exported={r['Primary Key']:r for r in csv.DictReader(f)}
    fields=Counter();differences=[]
    for key in table:
        c=index['Hanson2016_'+key];e=exported['Hanson2016_'+key]
        for field in FIELDS:
            a,b=c[field],e[field]
            if numeric(a):
                try:same=Fraction(b.strip())==a or abs(float(b)-float(a))<=1e-9*max(1,abs(float(a)))
                except (ValueError,ZeroDivisionError):same=False
            else:same=('' if a is None else str(a).strip())==b.strip()
            fields[field]+=same
            if not same:differences.append(dict(city_key=key,field=field))
    decisive=['Primary Key','Ancient Toponym','Province','Start Date','End Date']
    assert all(fields[f]==50 for f in decisive),{f:fields[f] for f in decisive}
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),workbook_sha256=sha(workbook),
        legacy_csv_sha256=sha(legacy),reviewer_sha256=sha(Path(__file__)),raw_xml_reader_without_spreadsheet_library=True,
        recovery_gate_counts_recomputed=gate,rows_checked=50,join_classes_recomputed=True,
        associations_recomputed=checked,sampling_classes_recomputed=len(result['sampling_classes']),
        legacy_csv_field_agreement_of_50={f:fields[f] for f in FIELDS},legacy_csv_differences=differences,
        legacy_csv_differences_resolved=False,AD150_eligible=0,gates_changed_by_catalogue_dates_or_area=False,
        reviewer_scope='Independent raw-XML reading, key join, agreement classes, counts and rank correlations; not an archaeological certification of phases, extents or representativeness.'))
    print('Reviewed 50 key joins from raw XML, %d associations and the legacy CSV cross-check (%d field differences reported).'%(checked,len(differences)))


if __name__=='__main__':main()
