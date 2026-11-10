import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_roman_rural_preparation import identifier,table,date_summary,role_summary


def test_typed_identifiers_do_not_modify_coordinate_text_or_fuzzy_match():
    rows,stats=table(b'ID,X_REF,Y_REF\n001.0,005000,002000\n',['ID','X_REF','Y_REF'])
    assert identifier(rows[0]['id'])=='1'
    assert rows[0]['xref']=='005000' and rows[0]['yref']=='002000'
    assert identifier('RRS-1')=='RRS-1' and identifier('1.5')=='1.5'
    assert identifier(0)=='0' and identifier(None)==''


def test_role_foreign_keys_repeat_without_being_duplicate_observation_keys():
    raw=b'STMID,ID,SITE_TYPE_MAJOR\n1,5,Rural settlement\n2,5,Military\n'
    rows,stats=table(raw,['STMID','ID','SITE_TYPE_MAJOR'],primary_key='STMID')
    assert stats['repeated_reference_id_rows']==1
    assert stats['duplicate_primary_key_rows']==0
    r=role_summary(rows,{'5'},['Rural settlement','Military'],'SITE_TYPE_MAJOR')
    assert r['records_with_roles']==1 and r['multi_role_records']==1 and r['orphan_rows']==0


def test_dates_keep_unknown_inverted_and_zero_valued_endpoints_separate():
    r=date_summary([{'datestart':'-50','dateend':'350'},{'datestart':'','dateend':'400'},
        {'datestart':'300','dateend':'100'},{'datestart':'0','dateend':'400'}])
    assert r['apparent_AD200_compatible']==2 and r['compatible_with_zero_endpoint']==1
    assert r['missing_or_nonnumeric_endpoint']==1 and r['inverted_interval']==1


def test_unknown_roles_and_orphans_are_not_coerced_to_known_classes():
    r=role_summary([{'id':'5','sitetypeminor':'farm'},{'id':'5','sitetypeminor':'farm'},
        {'id':'99','sitetypeminor':'unverified role'}],{'5'},['farm'],'SITE_TYPE_MINOR')
    assert r['duplicate_role_rows']==1 and r['unknown_label_rows']==1 and r['orphan_rows']==1


def test_malformed_csv_rows_are_flagged_for_later_quarantine():
    rows,stats=table(b'ID,AREA\n1,2,unlabelled\n2,3\n',['ID','AREA'])
    assert stats['malformed_rows']==1 and rows[0]['__malformed'] and not rows[1]['__malformed']


def test_unexpected_schema_fails_without_automatic_coordinate_alias():
    with pytest.raises(ValueError,match='Missing documented'):
        table(b'ID,X_REF_MAP,Y_REF_MAP\n1,1,2\n',['ID','X_REF','Y_REF'])
