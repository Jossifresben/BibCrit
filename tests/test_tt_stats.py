import pytest
from translation_technique.stats import chi2_sf, chi_square, cramers_v


def test_chi2_sf_known_values():
    assert chi2_sf(3.841, 1) == pytest.approx(0.05, abs=0.001)
    assert chi2_sf(5.991, 2) == pytest.approx(0.05, abs=0.001)
    assert chi2_sf(0.0, 3) == pytest.approx(1.0)
    assert chi2_sf(100.0, 3) < 1e-10


def test_chi_square_2x2_hand_computed():
    # [[20, 10], [5, 25]] → expected row1: 12.5, 17.5; row2: 12.5, 17.5
    r = chi_square([[20, 10], [5, 25]])
    assert r['dof'] == 1
    assert r['stat'] == pytest.approx(15.43, abs=0.01)
    assert r['p'] < 0.001
    assert r['unreliable'] is False


def test_chi_square_flags_small_expected():
    r = chi_square([[3, 1], [1, 3]])
    assert r['unreliable'] is True


def test_chi_square_degenerate_matrix():
    r = chi_square([[5, 0], [0, 0]])
    assert r['stat'] == 0.0 and r['p'] == 1.0 and r['unreliable'] is True


def test_cramers_v_range():
    m = [[20, 10], [5, 25]]
    v = cramers_v(m, chi_square(m)['stat'])
    assert 0.5 < v < 0.6
