"""Budget and restriction tests for the isolated seasonal wide network."""
import copy
import unittest
import numpy as np
from scipy.sparse import csr_matrix

from polity.seasonal_settlement_network import Inputs,CoupledNetwork,audit_network,food_year,route_towns,KCAL
from polity.settlement_residents import ResidentAllocation,audit_origin_food


def example():
    return CoupledNetwork(Inputs(np.array([100.,200.]),csr_matrix(np.diag([20.,30.])),
        np.array([300.,500.])*KCAL,np.array([1,1],np.uint16),np.ones(2)*10,np.ones(2)*2,
        np.tile([0,1],(4,1)),np.full((4,2),.95),np.zeros((4,2,2)),
        np.array([20.,30.]),np.array([True,True])),hours=600,marketed_share=.3371937035110408)


class SeasonalNetworkTests(unittest.TestCase):
    def test_fixed_source_shards_return_people_and_recalculate_work(self):
        m=example();a=m.evaluate(np.array([20.,30.]));b=m.evaluate(np.array([10.,15.]))
        np.testing.assert_array_equal(a['rural'],[80,170]);np.testing.assert_array_equal(b['rural'],[90,185])
        np.testing.assert_array_equal(b['work'].workers,b['rural']*.4)
        self.assertAlmostEqual(float(b['rural'].sum()+b['target'].sum()),300.)

    def test_one_owner_homogeneous_legacy_audit_accepts_network_subcase(self):
        m=example();r=m.evaluate(m.x.request);audit=audit_network(m,r)
        a=r['allocation'];old=ResidentAllocation(a.settlement,m.x.people,r['rural'],r['moved'],
            m.x.request,np.array([0,1]),r['arrivals'],2500.,365.,90.,.05)
        legacy=audit_origin_food(old,r['rural_food'].harvest,r['departures'],
            origin_capacity_kcal=r['rural']*KCAL+r['marketed'].sum(0),retention=.95,delay_bins=1)
        self.assertEqual(legacy['status'],'passed');self.assertTrue(audit['positive_towns_food_supported'])
        self.assertAlmostEqual(legacy['settlement_people'],float(r['target'].sum()))
        self.assertAlmostEqual(legacy['rural_people'],float(r['rural'].sum()))
        np.testing.assert_allclose(legacy['transport_loss_kcal'],audit['ledger']['source_transport_loss_kcal'],rtol=1e-12)

    def test_no_exports_from_seasonally_hungry_origin(self):
        m=example();m.x.potential[:]=KCAL
        r=m.evaluate(m.x.request)
        self.assertGreater(r['rural_food'].year.unmet.sum(),0)
        self.assertEqual(r['departures'].sum(),0)

    def test_repeating_capacity_cannot_invent_inherited_grain(self):
        r=food_year(np.zeros((12,2)),np.ones((12,2)),np.ones(2)*1e9)
        np.testing.assert_array_equal(r.initial_stock,[0,0]);np.testing.assert_array_equal(r.unmet,[12,12])

    def test_town_exports_use_actual_overflow_and_pay_link_loss(self):
        direct=np.tile([30*KCAL/12,0.],(12,1));target=np.array([10.,20.]);b=np.zeros((4,2,2));b[:,0,1]=.8
        r=route_towns(direct,target,b)
        self.assertGreater(r['inter_received'].sum(),0)
        np.testing.assert_allclose(r['inter_received'].sum(),r['inter_exported'].sum()*.8)
        self.assertTrue((r['inter_exported'][:,0]<=r['direct_food'].stock_path[:-1,0]+direct[:,0]-10*KCAL/12-10*2500*90+1e-5).all())
        self.assertEqual(r['inter_received'][:,0].sum(),0)

    def test_cohort_reserved_inside_finite_cap(self):
        m=example();m.x.request[:]=200;m.x.recruitment=csr_matrix(np.diag([200.,200.]));m.x.people[:]=1000;m.x.potential[:]=5000*KCAL
        r=m.evaluate(np.array([200.,200.]));p=r['allocation'].settlement
        np.testing.assert_array_equal(p.total_people,[200,200]);np.testing.assert_array_equal(p.institutional_people,[100,100])
        np.testing.assert_array_equal(p.civilian_people,[100,100])

    def test_duplicate_direct_arrivals_rejected(self):
        m=example();r=m.evaluate(m.x.request);r['direct']=r['direct']+KCAL
        with self.assertRaisesRegex(ValueError,'routes'):audit_network(m,r)

    def test_unfunded_origin_export_rejected(self):
        m=example();r=m.evaluate(m.x.request);r['departures']=r['departures']+KCAL
        with self.assertRaisesRegex(ValueError,'funding'):audit_network(m,r)

    def test_certification_rebuilds_actual_finite_population(self):
        m=example();r=m.solve(max_iterations=64)
        self.assertTrue(r['physical_certificate']);self.assertTrue(r['qualified'])
        np.testing.assert_array_equal(r['target'],r['allocation'].settlement.total_people)
        np.testing.assert_array_equal(r['allocation'].arrivals,r['arrivals'])
        np.testing.assert_array_equal(r['allocation'].settlement.food_year.unmet,r['town_food'].unmet)
        self.assertAlmostEqual(float(r['rural'].sum()+r['target'].sum()),300.)

    def test_roundoff_in_finite_column_budget_keeps_fraction_domain(self):
        m=example();m.x.request[:]=200;m.x.recruitment=csr_matrix(np.diag([200.,200.])*(1+1e-14))
        m.x.people[:]=1000;m.x.potential[:]=5000*KCAL
        proposal=m.evaluate(m.x.request)['allocation'].settlement.total_people
        r=m.evaluate(proposal)
        self.assertTrue(np.isfinite(r['rural']).all());self.assertTrue((r['rural']>=0).all())


if __name__=='__main__':unittest.main()
