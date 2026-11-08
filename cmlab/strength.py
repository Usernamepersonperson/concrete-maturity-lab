"""Strength-maturity relationships and calibration from lab specimens.

The argument ``x`` is always equivalent age at 20 C in hours (from ``maturity``), so a lab cube
stored at 20 C has x equal to its age.

Models
- ``log``        S = a + b ln(x)                          Plowman (1956), Mag. Concr. Res. 8(22)
- ``hyperbolic`` S = Su k (x - x0) / (1 + k (x - x0))     Carino (1984), NBSIR 84-2851 / ASTM C1074
- ``exp``        S = Su exp(-(tau / x)^alpha)             Freiesleben Hansen & Pedersen (1985)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import optimize, stats


def log_model(x, a, b):
    x = np.maximum(np.asarray(x, dtype=float), 1e-9)
    return np.maximum(a + b * np.log(x), 0.0)


def hyperbolic_model(x, su, k, x0):
    z = np.maximum(np.asarray(x, dtype=float) - x0, 0.0)
    return su * k * z / (1.0 + k * z)


def exp_model(x, su, tau, alpha):
    x = np.maximum(np.asarray(x, dtype=float), 1e-9)
    return su * np.exp(-((tau / x) ** alpha))


MODELS = {
    "log": (log_model, ["a", "b"]),
    "hyperbolic": (hyperbolic_model, ["su", "k", "x0"]),
    "exp": (exp_model, ["su", "tau", "alpha"]),
}


@dataclass
class Calibration:
    model: str
    params: np.ndarray
    cov: np.ndarray
    rmse: float          # MPa, in-sample
    loo_rmse: float      # MPa, leave-one-age-out cross-validation
    n: int
    resid_sd: float      # MPa, residual standard deviation (n - p dof)
    names: list[str] = field(default_factory=list)

    def predict(self, x):
        return MODELS[self.model][0](x, *self.params)

    def sample_params(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Draw parameter vectors from the fit covariance (multivariate normal)."""
        return rng.multivariate_normal(self.params, self.cov, size=n, check_valid="ignore")

    def band(self, x, level: float = 0.90, n: int = 400, seed: int = 0):
        """Confidence band (lower, upper) of the mean strength curve from parameter sampling."""
        rng = np.random.default_rng(seed)
        fn = MODELS[self.model][0]
        draws = self.sample_params(n, rng)
        curves = np.array([fn(x, *p) for p in draws])
        tail = (1 - level) / 2
        lo, hi = np.quantile(curves, [tail, 1 - tail], axis=0)
        return lo, hi


def _initial(model: str, x: np.ndarray, s: np.ndarray):
    smax = float(np.max(s))
    xmin = float(np.min(x))
    if model == "log":
        b, a = np.polyfit(np.log(x), s, 1)
        return [a, b], (-np.inf, np.inf)
    if model == "hyperbolic":
        return ([1.3 * smax, 0.02, 0.5 * xmin],
                ([smax * 0.5, 1e-5, 0.0], [5 * smax, 5.0, xmin]))
    if model == "exp":
        return ([1.3 * smax, 0.5 * float(np.median(x)), 0.8],
                ([smax * 0.5, 0.1, 0.2], [5 * smax, 1e4, 3.0]))
    raise ValueError(f"unknown model {model!r}")


def _fit(model, x, s):
    fn = MODELS[model][0]
    p0, bounds = _initial(model, x, s)
    if model == "log":
        return optimize.curve_fit(fn, x, s, p0=p0, maxfev=20000)
    return optimize.curve_fit(fn, x, s, p0=p0, bounds=bounds, maxfev=50000)


def calibrate(x_h, strength_mpa, model: str = "exp") -> Calibration:
    """Fit a strength-maturity relationship to lab results (one row per specimen)."""
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; choose from {sorted(MODELS)}")
    x = np.asarray(x_h, dtype=float)
    s = np.asarray(strength_mpa, dtype=float)
    if x.shape != s.shape or x.ndim != 1:
        raise ValueError("x_h and strength_mpa must be 1-D arrays of equal length")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(s))):
        raise ValueError("non-finite values in calibration data")
    if np.any(x <= 0) or np.any(s < 0):
        raise ValueError("ages must be positive and strengths non-negative")
    names = MODELS[model][1]
    p = len(names)
    if np.unique(x).size < p + 1:
        raise ValueError(f"need at least {p + 1} distinct ages to calibrate the {model} model")
    popt, pcov = _fit(model, x, s)
    fn = MODELS[model][0]
    res = s - fn(x, *popt)
    dof = max(x.size - p, 1)
    rmse = float(np.sqrt(np.mean(res**2)))
    # leave-one-age-out: drop all specimens of one age, refit, predict that age
    errs: list[float] = []
    for age in np.unique(x):
        keep = x != age
        if np.unique(x[keep]).size < p + 1:
            continue
        try:
            pp, _ = _fit(model, x[keep], s[keep])
        except (RuntimeError, ValueError):
            continue
        errs.extend((s[~keep] - fn(x[~keep], *pp)).tolist())
    loo = float(np.sqrt(np.mean(np.square(errs)))) if errs else float("nan")
    cov = np.where(np.isfinite(pcov), pcov, 0.0)
    return Calibration(model, popt, cov, rmse, loo, int(x.size),
                       float(np.sqrt(np.sum(res**2) / dof)), list(names))


def prediction_interval(cal: Calibration, x, level: float = 0.90):
    """Approximate prediction interval for a single new specimen: mean +/- t * resid_sd."""
    dof = max(cal.n - len(cal.params), 1)
    q = stats.t.ppf(0.5 + level / 2, dof)
    mu = cal.predict(x)
    return np.maximum(mu - q * cal.resid_sd, 0.0), mu + q * cal.resid_sd


def best_model(x_h, strength_mpa, models=("log", "hyperbolic", "exp")) -> Calibration:
    """Calibrate every model and return the one with the lowest leave-one-age-out error."""
    fits = [calibrate(x_h, strength_mpa, m) for m in models]
    return min(fits, key=lambda c: c.loo_rmse if np.isfinite(c.loo_rmse) else c.rmse)


def crossing_time(t_h, strength, threshold: float):
    """First time (hours, linearly interpolated) at which ``strength`` reaches ``threshold``.

    Returns None if the threshold is never reached.
    """
    t = np.asarray(t_h, dtype=float)
    s = np.asarray(strength, dtype=float)
    idx = np.nonzero(s >= threshold)[0]
    if idx.size == 0:
        return None
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    s0, s1 = s[i - 1], s[i]
    return float(t[i - 1] + (threshold - s0) / (s1 - s0) * (t[i] - t[i - 1]))
