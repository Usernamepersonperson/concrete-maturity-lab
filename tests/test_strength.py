import numpy as np
import pytest

from cmlab import pipeline as P
from cmlab import strength as s


def test_exp_model_known_value():
    # Su exp(-(tau/x)^alpha) at x = tau -> Su / e
    assert s.exp_model(30.0, 48.0, 30.0, 0.85) == pytest.approx(48.0 / np.e)


def test_hyperbolic_model_known_values():
    assert s.hyperbolic_model(10.0, 40.0, 0.1, 10.0) == 0.0     # at x0
    assert s.hyperbolic_model(110.0, 40.0, 0.1, 10.0) == pytest.approx(40 * 10 / 11)


def test_log_model_known_value_and_floor():
    assert s.log_model(np.e, 5.0, 10.0) == pytest.approx(15.0)
    assert s.log_model(1e-12, 0.0, 1.0) == 0.0


@pytest.mark.parametrize("model", ["log", "hyperbolic", "exp"])
def test_models_monotone_nondecreasing(model):
    x, y = P.lab_specimens()
    c = s.calibrate(x, y, model)
    g = np.linspace(10, 700, 200)
    assert np.all(np.diff(c.predict(g)) >= -1e-9)


def test_exp_calibration_recovers_noiseless_truth():
    x = np.repeat(np.array(P.LAB_AGES_H, dtype=float), 2)
    y = P.true_strength(x)
    c = s.calibrate(x, y, "exp")
    assert c.params == pytest.approx([48.0, 30.0, 0.85], rel=1e-3)
    assert c.rmse < 1e-4


def test_hyperbolic_calibration_recovers_own_curve():
    x = np.repeat(np.array(P.LAB_AGES_H, dtype=float), 2)
    y = s.hyperbolic_model(x, 45.0, 0.03, 6.0)
    c = s.calibrate(x, y, "hyperbolic")
    assert c.rmse < 1e-3
    assert c.predict(100.0) == pytest.approx(s.hyperbolic_model(100.0, 45.0, 0.03, 6.0), rel=1e-3)


def test_log_calibration_is_linear_regression():
    x = np.array([10, 20, 40, 80, 160, 320.0])
    y = 3.0 + 6.0 * np.log(x)
    c = s.calibrate(x, y, "log")
    assert c.params == pytest.approx([3.0, 6.0], rel=1e-6)


def test_noisy_calibration_error_is_bounded():
    x, y = P.lab_specimens(seed=7)
    for model in ("hyperbolic", "exp"):
        c = s.calibrate(x, y, model)
        assert c.rmse < 2.5          # 5% noise on up to 45 MPa
        assert c.loo_rmse >= c.rmse * 0.8
        assert np.isfinite(c.loo_rmse)


def test_log_model_fits_worse_than_sigmoidal_on_wide_age_range():
    x, y = P.lab_specimens(seed=7)
    assert s.calibrate(x, y, "log").rmse > 1.5 * s.calibrate(x, y, "exp").rmse


def test_best_model_prefers_a_non_log_model():
    x, y = P.lab_specimens(seed=7)
    assert s.best_model(x, y).model in ("hyperbolic", "exp")


def test_confidence_band_brackets_prediction_mostly():
    x, y = P.lab_specimens(seed=7)
    c = s.calibrate(x, y, "exp")
    g = np.linspace(20, 600, 50)
    lo, hi = c.band(g, level=0.9)
    mid = c.predict(g)
    assert np.all(lo <= hi)
    assert np.mean((lo <= mid + 1e-6) & (mid <= hi + 1e-6)) > 0.9


def test_band_is_reproducible():
    x, y = P.lab_specimens(seed=7)
    c = s.calibrate(x, y, "exp")
    g = np.array([24.0, 72.0])
    assert np.allclose(c.band(g, seed=3)[0], c.band(g, seed=3)[0])


def test_prediction_interval_wider_than_confidence_band():
    x, y = P.lab_specimens(seed=7)
    c = s.calibrate(x, y, "exp")
    g = np.array([72.0])
    plo, phi = s.prediction_interval(c, g)
    clo, chi = c.band(g)
    assert (phi - plo)[0] > (chi - clo)[0]


def test_prediction_interval_covers_most_specimens():
    x, y = P.lab_specimens(seed=7)
    c = s.calibrate(x, y, "exp")
    lo, hi = s.prediction_interval(c, x, 0.9)
    assert np.mean((y >= lo) & (y <= hi)) >= 0.8


@pytest.mark.parametrize("x,y", [
    ([1, 2, 3], [1, 2]),
    ([1, 2, 3, 4], [1, 2, float("nan"), 4]),
    ([0, 1, 2, 3], [1, 2, 3, 4]),
    ([1, 2, 3, 4], [-1, 2, 3, 4]),
])
def test_calibrate_rejects_bad_input(x, y):
    with pytest.raises(ValueError):
        s.calibrate(x, y, "exp")


def test_calibrate_needs_enough_distinct_ages():
    with pytest.raises(ValueError):
        s.calibrate([10, 10, 10, 20], [5, 5, 5, 8], "exp")


def test_calibrate_rejects_unknown_model():
    with pytest.raises(ValueError):
        s.calibrate([1, 2, 3, 4], [1, 2, 3, 4], "cubic")


def test_crossing_time_interpolates():
    assert s.crossing_time([0, 10, 20], [0, 10, 30], 20.0) == pytest.approx(15.0)


def test_crossing_time_none_when_not_reached():
    assert s.crossing_time([0, 1], [0, 1], 5.0) is None


def test_crossing_time_at_start():
    assert s.crossing_time([3, 4], [10, 11], 5.0) == 3.0
