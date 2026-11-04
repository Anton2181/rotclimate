import numpy as np
from scipy import ndimage as ndi
from polity.administration import named_markers,match_commanderies,name_key,legion_markers,commandery_key


def test_diacritics_compose_but_distinct_names_and_directions_stay_distinct():
    assert name_key('Gerênôi')==name_key('Gere\u0302no\u0302i')
    assert name_key('Dars Northern')!=name_key('Dars Southern')
    assert name_key('Uγra')!=name_key('Uyra')


def test_touching_named_circles_keep_two_anchors_and_roles():
    rgba=np.zeros((30,50,4),np.uint8)
    rgba[8:22,5:19]=255;rgba[10:20,19:29]=255
    assert ndi.label(rgba[...,3]>0)[1]==1
    markers=named_markers(rgba,[dict(name='City',x=12,y=15),dict(name='Town',x=24,y=15)],50,30)
    assert [m['kind'] for m in markers]==['fortified city','fortified town']


def test_no_symbol_does_not_become_a_fortified_town():
    m=named_markers(np.zeros((20,20,4),np.uint8),[dict(name='Village',x=10,y=10)],20,20)[0]
    assert not m['symbol_verified'] and m['kind']=='unclassified'


def test_sheet_alias_never_overrides_exact_map_name_or_adds_ambiguity():
    markers=[dict(id='A',name='Tašar',x=10,y=10,kind='fortified city'),dict(id='B',name='Daras',x=20,y=20,kind='fortified town')]
    sheet=dict(towns=[[1,'Tašar','Town','Province']],anchors={'1':[20,20]})
    match=match_commanderies([dict(name='Tašar Commandery',centre_name='Tašar')],markers,sheet)[0]
    assert match['marker_id']=='A'


def test_split_regions_do_not_reuse_one_centre():
    marker=dict(id='A',name='Dars',x=10,y=10,kind='fortified city')
    result=match_commanderies([dict(name='Dars Northern Commandery',centre_name='Dars Northern')],[marker],dict(towns=[],anchors={}))
    assert result[0]['status']=='unlocated' and result[0]['x'] is None


def test_legion_location_does_not_infer_manpower_or_founding_number():
    pixels=np.zeros((10,10,4),np.uint8);pixels[3:7,3:7]=[178,0,255,255]
    legion=legion_markers(pixels,100,100)[0]
    assert legion['founding_number'] is None and legion['strength'] is None
    assert legion['x']==50 and legion['y']==50


def test_commandery_ids_join_known_workbook_formats():
    assert commandery_key('Capital')=='CAPITAL'
    assert commandery_key('Capital Com 1')==commandery_key('CC1')
    assert commandery_key('IC4 Com 5')==commandery_key('IC4C5')
    assert commandery_key('IF2 Com 3')!=commandery_key('IF2 Com 4')


def test_id_links_differently_named_seat_and_retains_name_conflict():
    commandery=dict(name='Nivāiti Commandery',centre_name='Nivāiti')
    marker=dict(id='M',name='Artāvan Temple',x=10,y=20,kind='imperial monastery',symbol_verified=True)
    evidence=dict(commanderies=[dict(name=commandery['name'],id='IC2C1',region='R')],
        towns=[dict(commandery_id='IC2C1',commandery_seat=True,name='Artāvan Temple',
            commandery_name='Typo Commandery',hex=1927,province='Vašna',provincial_seat=False)])
    c=match_commanderies([commandery],[marker],dict(towns=[],anchors={}),evidence)[0]
    assert c['status']=='matched' and c['marker_id']=='M' and c['discrepancies']


def test_conflicting_named_centre_and_flag_are_not_silently_resolved():
    commandery=dict(name='Thalamâtâs Commandery',centre_name='Thalamâtâs')
    markers=[dict(id=str(i),name=n,x=i*10,y=20,kind='fortified town') for i,n in enumerate(['Thalamâtâs','Pitané'])]
    evidence=dict(commanderies=[dict(name=commandery['name'],id='IP4C4',region='R')],
        towns=[dict(commandery_id='IP4C4',commandery_seat=True,name='Pitané',
            commandery_name=commandery['name'],hex=2497,province='Daiva',provincial_seat=False)])
    c=match_commanderies([commandery],markers,dict(towns=[],anchors={}),evidence)[0]
    assert c['status']=='ambiguous' and c['x'] is None
    assert {m['name'] for m in c['candidate_markers']}=={'Thalamâtâs','Pitané'}
