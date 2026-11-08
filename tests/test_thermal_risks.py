import numpy as np
import pytest

from cmlab import risks, thermal


def test_adiabatic_rise_matches_energy_balance():
    p = thermal.SlabParams(h_top=0.0, h_bot=0.0, thickness_m=0.3)
    res = thermal.simulate_slab(np.full(24 * 14 + 1, 20.0), 20.0, p)
    expected = p.q_total * thermal.alpha_hydration(res.te_h[-1, 0], p.tau_h, p.beta_h) / p.rho_c
    assert res.temp_c[-1].mean() - 20.0 == pytest.approx(expected, rel=1e-3)
    assert np.ptp(res.temp_c[-1]) < 1e-6      # uniform when insulated


def test_no_hydration_no_loss_stays_constant():
    p = thermal.SlabParams(h_top=0.0, h_bot=0.0, q_total=0.0)
    res = thermal.simulate_slab(np.full(49, -10.0), 15.0, p)
    assert np.allclose(res.temp_c, 15.0)


def test_cooling_slab_relaxes_to_air_temperature():
    p = thermal.SlabParams(q_total=0.0, h_top=10.0, h_bot=10.0)
    res = thermal.simulate_slab(np.full(24 * 10 + 1, 5.0), 25.0, p)
    assert res.temp_c[-1].max() < 5.5


def test_cooling_time_constant_order_of_magnitude():
    # lumped estimate tau = rho c H / (h_top + h_bot); check 1/e crossing within 25 %
    p = thermal.SlabParams(q_total=0.0, h_top=10.0, h_bot=10.0, thickness_m=0.2)
    res = thermal.simulate_slab(np.full(24 * 5 + 1, 0.0), 20.0, p)
    mean = res.temp_c.mean(axis=1)
    idx = int(np.argmax(mean <= 20.0 / np.e))
    tau_est = p.rho_c * p.thickness_m / (p.h_top + p.h_bot) / 3600.0
    assert res.t_h[idx] == pytest.approx(tau_est, rel=0.25)


def test_hydration_heat_warms_core_of_thick_slab():
    p = thermal.SlabParams(thickness_m=1.0, n_cells=40, h_bot=1.0)
    res = thermal.simulate_slab(np.full(24 * 5 + 1, 15.0), 15.0, p)
    assert res.temp_c.max() > 15.0 + 25.0
    mid = res.sensor(0.5)
    top = res.sensor(0.02)
    assert (mid - top).max() > 10.0


def test_symmetry_for_symmetric_boundaries():
    p = thermal.SlabParams(h_top=8.0, h_bot=8.0)
    res = thermal.simulate_slab(np.full(24 * 3 + 1, 10.0), 20.0, p)
    assert np.allclose(res.temp_c, res.temp_c[:, ::-1], atol=1e-9)


def test_alpha_hydration_bounds():
    a = thermal.alpha_hydration(np.array([0.0, 1.0, 1e5]), 20.0, 1.2)
    assert a[0] == 0.0 and 0 < a[1] < 1e-6 and a[2] > 0.999


@pytest.mark.parametrize("air", [[1.0], [1.0, float("nan")], [[1.0, 2.0]]])
def test_simulate_rejects_bad_air(air):
    with pytest.raises(ValueError):
        thermal.simulate_slab(air, 10.0)


def test_simulate_rejects_bad_params():
    with pytest.raises(ValueError):
        thermal.simulate_slab(np.ones(5), 10.0, thermal.SlabParams(thickness_m=0.0))


# --- risks -----------------------------------------------------------------

T = np.arange(0, 10.0)


def test_frost_alarm_when_cold_and_weak():
    temps = np.array([5, 3, 1, -1, -2, -1, 1, 3, 5, 6.0])
    s = np.full(10, 2.0)
    al = risks.frost_alerts(T, temps, s)
    assert "frost_alarm" in [a.kind for a in al]
    alarm = next(a for a in al if a.kind == "frost_alarm")
    assert alarm.t_start_h == 3.0 and alarm.t_end_h == 5.0 and alarm.peak == -2.0


def test_frost_no_alarm_when_strong_enough():
    assert risks.frost_alerts(T, np.full(10, -5.0), np.full(10, 6.0)) == []


def test_frost_alarm_boundary_exactly_critical_strength():
    assert risks.frost_alerts(T, np.full(10, -1.0), np.full(10, 5.0)) == []


def test_frost_warn_near_zero():
    al = risks.frost_alerts(T, np.full(10, 1.5), np.full(10, 1.0))
    assert [a.kind for a in al] == ["frost_warn"]


def test_frost_uses_coldest_sensor():
    temps = np.column_stack([np.full(10, 10.0), np.full(10, -1.0)])
    assert risks.frost_alerts(T, temps, np.full(10, 1.0))[0].kind == "frost_alarm"


def test_frost_length_mismatch_raises():
    with pytest.raises(ValueError):
        risks.frost_alerts(T, np.ones(5), np.ones(10))


def test_frost_protect_advisory_uses_horizon():
    air = np.array([5, 5, 5, 5, -3, -3, 5, 5, 5, 5.0])
    al = risks.frost_protection_needed(T, air, np.full(10, 1.0), horizon_h=2.0)
    assert len(al) == 1 and al[0].t_start_h == 2.0 and al[0].t_end_h == 5.0


def test_frost_protect_silent_when_strong():
    assert risks.frost_protection_needed(T, np.full(10, -9.0), np.full(10, 9.0)) == []


def test_crack_alarm_and_warn_levels():
    d = np.array([0, 5, 16, 21, 25, 18, 10, 0, 0, 0.0])
    al = risks.crack_alerts(T, d, limit_k=20.0)
    assert sorted(a.kind for a in al) == ["crack_alarm", "crack_warn", "crack_warn"]
    assert max(a.peak for a in al) == 25.0


def test_crack_no_alert_below_warn():
    assert risks.crack_alerts(T, np.full(10, 10.0), 20.0) == []


def test_crack_invalid_limit():
    with pytest.raises(ValueError):
        risks.crack_alerts(T, np.zeros(10), 0.0)


def test_crack_risk_index():
    assert risks.crack_risk_index([0, 10, 30], 20.0) == pytest.approx(1.5)
    assert risks.crack_risk_index([], 20.0) == 0.0


def test_delta_t_uses_colder_surface():
    assert risks.delta_t([50.0], [30.0], [20.0])[0] == 30.0
