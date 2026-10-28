"""Serialization normalization must neither reject tuples nor hide real changes."""
import pytest
import scripts.recover_transport_diagnosis as recovery


def test_canonicalization_only_changes_json_representation(monkeypatch):
    def compare(row,*_):
        assert row==dict(params=dict(cycle=[1.,2.]))
        return True
    monkeypatch.setattr(recovery,'verify_exact',compare)
    assert recovery.canonical_exact(dict(params=dict(cycle=(1.,2.))),{},None)
    with pytest.raises(AssertionError):
        recovery.canonical_exact(dict(params=dict(cycle=(1.,3.))),{},None)
