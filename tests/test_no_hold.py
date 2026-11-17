import numpy as np
import pytest

from polity.no_hold import NoHoldLedger


def args():
    return dict(ids=['funded-1'],origin=np.array([10]),destination=np.array([20]),sent=np.array([100.]),
        delivered=np.array([70.]),departure_bin=np.array([11]),arrival_bin=np.array([0]),
        event_labels=('stop-a','stop-b','endpoint'),charge_allocation=np.array([[10.],[5.],[15.]]))


@pytest.mark.parametrize('sent,delivered,charges',[(100,100,[0,0,0]),(100,0,[10,20,70]),(100,70,[10,5,15]),(0,0,[0,0,0])])
def test_funded_grain_conserved_with_no_extra_arrival_delay(sent,delivered,charges):
    a=args();a.update(sent=np.array([sent]),delivered=np.array([delivered]),charge_allocation=np.array(charges)[:,None])
    ledger=NoHoldLedger();b=ledger.record(**a)
    assert b.sent[0]==b.delivered[0]+sum(b.charges[:,0])
    assert b.remaining_after_charge[-1,0]==delivered and b.arrival_bin[0]==0
    assert ledger.summary()['event_funding_kcal']==0


def test_event_partition_does_not_change_endpoint_grain_or_year_wrap():
    a=args();first=NoHoldLedger().record(**a)
    a['charge_allocation']=np.array([[0.],[15.],[15.]])
    second=NoHoldLedger().record(**a)
    np.testing.assert_array_equal(first.delivered,second.delivered)
    np.testing.assert_array_equal(first.arrival_bin,second.arrival_bin)


def test_independent_subleg_retention_would_invent_five_units():
    a=args();a.update(delivered=np.array([55.]),charge_allocation=np.array([[25.],[20.],[0.]]))
    b=NoHoldLedger().record(**a)
    assert b.delivered[0]==55 and 100*(1-.25)*(1-.20)>b.delivered[0]


def test_whole_leg_without_events_preserves_original_rounded_delivery():
    a=args();a.pop('event_labels');a.pop('charge_allocation');a['delivered']=np.nextafter(a['delivered'],0)
    b=NoHoldLedger().record(**a);np.testing.assert_array_equal(b.delivered,a['delivered'])


def test_duplicate_across_calls_cannot_fund_additional_events():
    ledger=NoHoldLedger();ledger.record(**args());before=ledger.summary()
    with pytest.raises(ValueError,match='Duplicate'):ledger.record(**args())
    assert ledger.summary()==before


def test_duplicate_within_batch_is_rejected():
    a=args();a={k:np.repeat(v,2,axis=-1) if isinstance(v,np.ndarray) else v for k,v in a.items()};a['ids']=['x','x']
    with pytest.raises(ValueError,match='Duplicate'):NoHoldLedger().record(**a)


@pytest.mark.parametrize('ids',[[''],[' '],[4],'funded-1'])
def test_invalid_funding_ids_rejected(ids):
    a=args();a['ids']=ids
    with pytest.raises(ValueError):NoHoldLedger().record(**a)


@pytest.mark.parametrize('key,value',[('sent',[-1.]),('sent',[np.inf]),('delivered',[np.nan]),('delivered',[101.]),
    ('origin',[-1]),('destination',[20.]),('departure_bin',[12]),('arrival_bin',[0.]),('arrival_bin',[1])])
def test_invalid_grain_endpoints_and_timing_rejected_atomically(key,value):
    a=args();a[key]=np.array(value);ledger=NoHoldLedger()
    with pytest.raises(ValueError):ledger.record(**a)
    assert ledger.summary()['consignments']==0
    ledger.record(**args());assert ledger.summary()['consignments']==1


@pytest.mark.parametrize('hold',[1,-1,0.,False])
def test_unsupported_holding_rejected(hold):
    a=args();a['hold_bins']=hold
    with pytest.raises(ValueError,match='zero hold'):NoHoldLedger().record(**a)


@pytest.mark.parametrize('charges',[np.array([[-1.],[16.],[15.]]),np.array([[np.inf],[5.],[15.]]),
    np.array([[1.],[2.],[3.]]),np.array([[101.],[0.],[0.]]),np.zeros((2,1))])
def test_unfunded_or_mismatched_charge_allocation_rejected(charges):
    a=args();a['charge_allocation']=charges
    with pytest.raises(ValueError):NoHoldLedger().record(**a)


def test_event_labels_and_charges_are_explicit():
    a=args();a['event_labels']=('same','same','last')
    with pytest.raises(ValueError):NoHoldLedger().record(**a)
    a=args();a['charge_allocation']=None
    with pytest.raises(ValueError):NoHoldLedger().record(**a)


def test_receipts_do_not_alias_input_arrays():
    a=args();b=NoHoldLedger().record(**a);a['sent'][0]=900
    assert b.sent[0]==100 and not b.delivered.flags.writeable


def test_unsigned_physical_ids_and_empty_batch_supported():
    a=args();a['origin']=a['origin'].astype(np.uint64)
    assert NoHoldLedger().record(**a).origin[0]==10
    a={k:v[..., :0] if isinstance(v,np.ndarray) else v for k,v in args().items()};a['ids']=[]
    ledger=NoHoldLedger();ledger.record(**a);assert ledger.summary()['sent_kcal']==0
