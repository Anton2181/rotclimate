"""Independent manufactured annual ledger checks, without climate or foraging runs."""
import numpy as np
import pytest
from scripts.check_foraging_ledgers import balance,fat_bounds


def test_annual_meat_renewal_books_unused_prey_once():
    # Start5 + supply10 = decay1 + harvest6 + discarded5 + endpoint3.
    balance([np.array([5.]),np.array([10.]),np.array([-1.]),np.array([-6.]),np.array([-5.]),np.array([-3.])],label='meat')
    with pytest.raises(ValueError):
        balance([np.array([5.]),np.array([10.]),np.array([-1.]),np.array([-6.]),np.array([-3.])],label='missing annual reset')


def test_asymmetric_fat_bounds_accept_feasible_path_and_reject_impossible_endpoint():
    # Gain2kg, lose3kg, reproduction costs1kg catabolic equivalent.
    # Endpoint5+2-3-1=3kg; energetic balance=2*54.6-3*39.3-39.3=-48MJ.
    fat_bounds(np.array([-48.]),np.array([5.]),np.array([3.]),39.3,54.6)
    with pytest.raises(ValueError):
        fat_bounds(np.array([-100.]),np.array([5.]),np.array([3.]),39.3,54.6)
