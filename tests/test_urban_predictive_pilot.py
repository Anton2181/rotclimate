import numpy as np
import pytest
from polity.urban_predictive_pilot import nested_fit


def design():
    rng=np.random.default_rng(95);fold=np.repeat(np.arange(4),30)
    X=np.column_stack([np.ones(120),rng.normal(size=120)])
    y=X@np.array([2.,.4])+rng.normal(size=120)
    return X,y,fold,np.ones(120,bool)


def test_outer_labels_cannot_affect_mean_or_sigma():
    X,y,f,e=design();a=nested_fit(X,y,f,e,2)
    y[f==2]+=100000
    b=nested_fit(X,y,f,e,2)
    np.testing.assert_array_equal(a[0],b[0]);assert a[1:]==b[1:]


def test_ineligible_labels_cannot_affect_fit():
    X,y,f,e=design();e[::3]=False;a=nested_fit(X,y,f,e,0)
    y[~e]=-100000;b=nested_fit(X,y,f,e,0)
    np.testing.assert_array_equal(a[0],b[0]);assert a[1:]==b[1:]


def test_inner_scalar_mean_error_accounting():
    X,y,f,e=design();X=X[:,:1]
    coef,sigma,inner=nested_fit(X,y,f,e,0)
    expected=[]
    for held in [1,2,3]:
        mean=sum(y[(f!=0)&(f!=held)])/sum((f!=0)&(f!=held))
        expected.extend(v-mean for v in y[f==held])
    np.testing.assert_allclose(coef,[sum(y[f!=0])/90])
    assert abs(sigma-np.sqrt(sum(v*v for v in expected)/90))<1e-12
    assert sum(a['test_rows'] for a in inner)==90


def test_rank_deficient_or_missing_inner_support_rejected():
    X,y,f,e=design()
    with pytest.raises(ValueError):nested_fit(np.ones((120,2)),y,f,e,0)
    with pytest.raises(ValueError):nested_fit(X,y,f,f==1,0)
