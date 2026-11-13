"""Pre-production controls for fixed source meal/calendar reconstruction."""
import numpy as np
from harvest.field_support import fixed_rural_food
from harvest.continuous_food_stocks import periodic_continuous_food_year
from harvest.event_food_stocks import periodic_event_food_year

def test_one_year_capacity_cannot_cover_one_year_meals_plus_decay():
    q=np.zeros(12);q[0]=1000.;need=np.full(12,365/12)
    y=periodic_continuous_food_year(q,need,365.,loss_fraction_year=.05,step_days=365/12)
    assert y.unmet>0 and y.overflow==635. and y.periodic_converged
    assert abs(y.harvested-y.consumed-y.spoiled-y.overflow)<1e-9

def test_old_meals_before_capacity_clip_preserved_exactly():
    r=fixed_rural_food(np.array([1000.]),np.array([1],'u2'),np.array([365.]))
    assert r.year.unmet[0]==0 and r.harvest[0,0]==1000. and r.harvest[1:].sum()==0

def test_calendar_first_eligible_boundary_and_zero_production():
    r=fixed_rural_food(np.array([1000.,0.]),np.array([0b101000,0],'u2'),np.array([365.,0.]))
    assert r.harvest[3,0]==1000. and r.harvest.sum()==1000.

def test_zero_loss_and_empty_contexts():
    q=np.zeros((12,3));q[0]=[1000.,0.,0.];need=np.broadcast_to([365/12,0.,1.],q.shape)
    y=periodic_continuous_food_year(q,need,[365.,0.,0.],step_days=365/12)
    np.testing.assert_allclose(y.unmet,[0.,0.,12.],atol=1e-10);np.testing.assert_allclose(y.overflow,[635.,0.,0.])

def test_annual_channels_phase_invariant_but_stock_path_changes():
    q=np.zeros(12);q[0]=1000.;need=np.full(12,365/12)
    a=periodic_continuous_food_year(q,need,365.,loss_fraction_year=.05,step_days=365/12,record=True)
    b=periodic_continuous_food_year(np.roll(q,5),need,365.,loss_fraction_year=.05,step_days=365/12,record=True)
    for name in ('consumed','unmet','spoiled','overflow','shortfall_days'):np.testing.assert_allclose(getattr(a,name),getattr(b,name),atol=1e-9)
    assert not np.array_equal(a.stock_path,b.stock_path)

def test_vector_bin_supply_matches_independent_event_primitive():
    q=np.zeros((12,2));q[2,0]=1000.;q[7,1]=200.;need=np.full((12,2),365/12)
    a=periodic_continuous_food_year(q,need,[365.,365.],loss_fraction_year=.05,step_days=365/12)
    for j in range(2):
        e=periodic_event_food_year(np.arange(12)*365/12,q[:,j],demand_rate=1.,capacity=365.,loss_fraction_year=.05)
        for name in ('initial_stock','final_stock','consumed','unmet','spoiled','overflow'):np.testing.assert_allclose(getattr(a,name)[j],getattr(e,name),atol=1e-8)
