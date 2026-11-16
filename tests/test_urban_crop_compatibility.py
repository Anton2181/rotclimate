import pytest
from scripts.restore_urban_population_inputs import old_world_default_adapter


@pytest.mark.parametrize('extra',[None,{}])
def test_default_keywords_only_removed(extra):
    token=object();seen=[]
    def legacy(*args,**kwargs):seen.append((args,kwargs));return token
    adapted=old_world_default_adapter(legacy)
    assert adapted(1,token,margins=token,extra_crops=extra,old_world=True) is token
    assert seen==[((1,token),{'margins':token})]


@pytest.mark.parametrize('extra,world',[({'maize':object()},True),(None,False),(None,None),(None,1)])
def test_nondefault_world_or_crops_rejected_before_call(extra,world):
    def forbidden(*args,**kwargs):raise AssertionError('Underlying old crop function must not be called')
    with pytest.raises(ValueError):old_world_default_adapter(forbidden)(extra_crops=extra,old_world=world)
