import numpy as np
import pytest

from cmlab import maturity as m


def hours(n):
    return np.arange(n + 1, dtype=float)


def test_nurse_saul_constant_20c_datum0():
    # worked example: 24 h at 20 C, T0 = 0 C -> 20 * 24 = 480 C*h
    assert m.nurse_saul(hours(24), np.full(25, 20.0))[-1] == pytest.approx(480.0)


def test_nurse_saul_datum_minus10():
    assert m.nurse_saul(hours(24), np.full(25, 20.0), t0_c=-10.0)[-1] == pytest.approx(720.0)


def test_nurse_saul_hand_example_varying_temp():
    # hourly steps 10, 20, 30 C (trapezoid): (15 + 25) = 40 C*h
    assert m.nurse_saul([0, 1, 2], [10, 20, 30])[-1] == pytest.approx(40.0)


def test_nurse_saul_no_gain_below_datum():
    assert m.nurse_saul(hours(10), np.full(11, -5.0))[-1] == 0.0


def test_nurse_saul_monotone_and_starts_at_zero():
    t = hours(48)
    temp = 10 + 10 * np.sin(t / 5)
    out = m.nurse_saul(t, temp)
    assert out[0] == 0.0 and np.all(np.diff(out) >= 0)


def test_nurse_saul_equivalent_age_at_reference_equals_age():
    assert m.nurse_saul_equivalent_age(hours(24), np.full(25, 20.0), -10.0)[-1] == pytest.approx(24.0)


def test_nurse_saul_equivalent_age_rejects_bad_reference():
    with pytest.raises(ValueError):
        m.nurse_saul_equivalent_age(hours(2), [1, 2, 3], t0_c=25.0)


def test_arrhenius_rate_is_one_at_reference():
    assert m.arrhenius_rate(20.0) == pytest.approx(1.0)


@pytest.mark.parametrize("temp,expected", [(30.0, 1.71838), (10.0, 0.56011), (5.0, 0.41269)])
def test_arrhenius_rate_worked_values_ea40(temp, expected):
    # exp(-Ea/R (1/T - 1/293.15)) with Ea = 40 kJ/mol, R = 8.314, computed independently
    assert m.arrhenius_rate(temp, 40_000.0) == pytest.approx(expected, rel=1e-4)


def test_equivalent_age_constant_temp_scales_by_rate():
    out = m.equivalent_age(hours(10), np.full(11, 30.0), 40_000.0)
    assert out[-1] == pytest.approx(10 * 1.71838, rel=1e-4)


def test_equivalent_age_at_reference_equals_clock_time():
    assert m.equivalent_age(hours(72), np.full(73, 20.0))[-1] == pytest.approx(72.0)


def test_higher_ea_slows_cold_pour_more():
    t, temp = hours(48), np.full(49, 5.0)
    assert m.equivalent_age(t, temp, 50_000.0)[-1] < m.equivalent_age(t, temp, 30_000.0)[-1]


def test_hansen_pedersen_ea_values():
    assert m.activation_energy_hp(25.0) == pytest.approx(33_500.0)
    assert m.activation_energy_hp(20.0) == pytest.approx(33_500.0)
    assert m.activation_energy_hp(5.0) == pytest.approx(33_500.0 + 1_470.0 * 15)


def test_hp_equivalent_age_matches_constant_form_above_20c():
    t, temp = hours(24), np.full(25, 30.0)
    assert m.equivalent_age(t, temp, None)[-1] == pytest.approx(m.equivalent_age(t, temp, 33_500.0)[-1])


def test_methods_agree_near_reference_temperature():
    # within a few percent around 22 C: NS(T0=-10) vs Arrhenius(40 kJ/mol)
    t, temp = hours(48), np.full(49, 22.0)
    ns = m.nurse_saul_equivalent_age(t, temp, -10.0)[-1]
    ar = m.equivalent_age(t, temp, 40_000.0)[-1]
    assert abs(ns - ar) / ar < 0.05


def test_methods_diverge_in_the_cold():
    t, temp = hours(48), np.full(49, 2.0)
    ns = m.nurse_saul_equivalent_age(t, temp, -10.0)[-1]
    ar = m.equivalent_age(t, temp, 40_000.0)[-1]
    assert ns > 1.1 * ar


@pytest.mark.parametrize("bad", [
    ([0, 1, 1], [1, 2, 3]),          # non-increasing time
    ([0, 1], [1, 2, 3]),             # length mismatch
    ([0, 1], [1, float("nan")]),     # NaN
    ([], []),                        # empty
])
def test_input_validation(bad):
    with pytest.raises(ValueError):
        m.nurse_saul(*bad)


def test_arrhenius_rejects_bad_ea_and_absolute_zero():
    with pytest.raises(ValueError):
        m.arrhenius_rate(20.0, -1.0)
    with pytest.raises(ValueError):
        m.arrhenius_rate(-300.0)


def test_single_sample_returns_zero():
    assert m.equivalent_age([0.0], [20.0])[0] == 0.0
