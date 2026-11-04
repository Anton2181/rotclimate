import numpy as np
from scipy.sparse import csr_matrix
from polity.coverage_audit import source_inventory,node_memberships,site_codes,merge_site,seasonal_mask,aggregate_words


def test_return_cannot_use_a_different_nearby_site():
    # A→X and X→B exist, but neither A nor B provides both directions.
    g=csr_matrix(([1.,1.,1.,2.],([0,2,0,3],[2,1,3,0])),shape=(4,4))
    month=np.zeros((3,1,2,4),np.uint8);unknown=np.zeros((2,4),np.uint8)
    for source in [0,1]:
        result=site_codes(g,g.T.tocsr(),source,np.arange(4))
        merge_site(month,unknown,dict(memberships={(0,0)},unknown=False),result)
    assert month[0,0,0,2]==3 and month[0,0,1,2]==0
    assert month[0,0,0,3]==3 and month[0,0,1,3]==2


def test_two_bit_classes_do_not_combine_into_fictitious_faster_coverage():
    words=np.array([[1],[2]],np.uint32)
    merged=aggregate_words(words)
    assert merged[0]==2  # bitwise OR would incorrectly produce3 (≤1day)
    assert seasonal_mask(merged,0)[0]==0 and seasonal_mask(merged,1)[0]==1


def test_packed_year_thresholds_and_cross_year_gap():
    from polity.seasonal_access import cyclic_isolation
    codes=np.array([0]+[3]*10+[0],np.uint32)
    word=np.sum(codes<<(2*np.arange(12)),dtype=np.uint32)
    mask=seasonal_mask(word,0)
    assert int(mask).bit_count()==10
    assert cyclic_isolation(np.array([bool(mask&(1<<m)) for m in range(12)]))==2
    assert seasonal_mask(np.uint32(0xFFFFFF),2)==4095


def test_unknown_or_conflicting_affiliation_is_not_assigned_by_icon_proximity():
    markers=[dict(id='A',name='Village',x=0,y=0,kind='fortified town',symbol_verified=True,datasheet_records=[]),
        dict(id='B',name='Fort',x=1,y=0,kind='imperial fort',symbol_verified=True,datasheet_records=[dict(province='Other',commandery_id=None)])]
    inv=dict(markers=markers,commanderies=[])
    records=source_inventory(inv,dict(owner_aliases={'Other':'Other realm'}),['Other realm','Xšāça'])
    assert records[0]['actor'] is None and records[1]['actor'] is None
    assert records[1]['status']=='affiliation_conflict'


def test_nested_source_cases_keep_unknown_evidence_separate_from_generated_sources():
    records=[dict(id='A',name='A',x=0,y=0,symbol_verified=True,actor='P'),
        dict(id='B',name='B',x=1,y=0,symbol_verified=True,actor=None)]
    nodes,counts,rows=node_memberships(records,[2],lambda n:'P',lambda x,y:x,['P'])
    assert counts[:,0].tolist()==[1,2,3]
    assert nodes[1]['unknown'] and (0,0) not in nodes[1]['memberships']
    assert nodes[2]['unknown'] is False and nodes[2]['memberships']=={(2,0)}
    assert rows[1]['scenario_basis']=='painted claim only'


def test_directional_subset_and_more_sources_are_monotone():
    rng=np.random.default_rng(7);a=rng.uniform(.1,6,(7,7));np.fill_diagonal(a,0);g=csr_matrix(a)
    month=np.zeros((3,1,2,7),np.uint8);unknown=np.zeros((2,7),np.uint8)
    for n in range(7):
        merge_site(month,unknown,dict(memberships={(1,0),(2,0)} if n else {(0,0),(1,0),(2,0)},unknown=False),site_codes(g,g.T.tocsr(),n,np.arange(7)))
    assert np.all(month[:,:,1]<=month[:,:,0])
    assert np.all(month[1]>=month[0]) and np.all(month[2]>=month[1])
