import numpy as np
from scripts.plot_pnw_transport import monthly_component


def test_native_component_keeps_twelve_months_and_does_not_mix_vector_axis():
    vectors=np.zeros((12,2,3));vectors[:,0]=np.arange(12)[:,None]+np.array([0,2,50])
    vectors[:,1]=-100
    actual=monthly_component(vectors,np.array([True,True,False]),np.array([1,3,9]))
    assert actual.shape==(12,)
    np.testing.assert_allclose(actual,np.arange(12)+1.5)
    np.testing.assert_array_equal(monthly_component(vectors,np.array([True,True,False]),np.array([1,3,9]),1),-100.)
