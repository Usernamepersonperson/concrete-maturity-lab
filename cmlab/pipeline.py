"""End-to-end pipeline: weather -> simulated embedded sensors -> maturity -> strength -> alerts.

The simulated "truth" concrete follows the exponential strength law ``TRUE_MIX`` with the
temperature dependent activation energy of Hansen & Pedersen. The estimators only see (a) noisy
lab cylinder results at 20 C and (b) the sensor temperatures, exactly as a site system would.
Everything here is simulated; nothing is measured on a real pour.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from . import maturity, risks, strength, thermal, weather

# Simulated reference mix (strength in MPa vs equivalent age in h at 20 C): CEM II / C30/37-like.
TRUE_MIX = {"su": 48.0, "tau": 30.0, "alpha": 0.85}
LAB_AGES_H = (12, 18, 24, 48, 72, 168, 336, 672)
THRESHOLDS = {"strip": 15.0, "post_tension": 25.0}   # MPa, example project values
DEPTHS_M = (0.02, None, None)                      # top, mid, bottom filled from thickness
FIXED_RULE_H = 7 * 24.0

METHODS = {
    "arrhenius_40": ("arrhenius", 40_000.0),
    "arrhenius_30": ("arrhenius", 30_000.0),
    "arrhenius_50": ("arrhenius", 50_000.0),
    "nurse_saul_T0=-10": ("nurse_saul", -10.0),
    "nurse_saul_T0=0": ("nurse_saul", 0.0),
    "nurse_saul_T0=5": ("nurse_saul", 5.0),
    "hansen_pedersen": ("hp", None),
}


def true_strength(te_h):
    return strength.exp_model(te_h, TRUE_MIX["su"], TRUE_MIX["tau"], TRUE_MIX["alpha"])


def lab_specimens(seed: int = 7, per_age: int = 3, cv: float = 0.05):
    """Simulated cylinder results at 20 C: truth x (1 + N(0, cv))."""
    rng = np.random.default_rng(seed)
    ages = np.repeat(np.array(LAB_AGES_H, dtype=float), per_age)
    s = true_strength(ages) * (1 + rng.normal(0, cv, ages.size))
    return ages, np.maximum(s, 0.0)


def equivalent_age_matrix(t_h, temps, method: str):
    """Equivalent age (nt, ns) for a method key from ``METHODS``."""
    kind, par = METHODS[method]
    temps = np.asarray(temps, dtype=float)
    cols = []
    for j in range(temps.shape[1]):
        if kind == "arrhenius":
            cols.append(maturity.equivalent_age(t_h, temps[:, j], par))
        elif kind == "nurse_saul":
            cols.append(maturity.nurse_saul_equivalent_age(t_h, temps[:, j], par))
        else:
            cols.append(maturity.equivalent_age(t_h, temps[:, j], None))
    return np.column_stack(cols)


@dataclass(frozen=True)
class Scenario:
    name: str
    site: str
    start_utc: str
    t_place_c: float
    slab: thermal.SlabParams = field(default_factory=thermal.SlabParams)
    days: float = 14.0
    covered: bool = False

    def depths(self):
        h = self.slab.thickness_m
        return (0.02, h / 2, h - 0.02)


def covered(s: Scenario) -> Scenario:
    """Winter protection: insulating blanket on top (h 12 -> 1.5) and insulated formwork (4 -> 2 W/m2K)."""
    return replace(s, name=s.name + " (protected)", covered=True,
                   slab=replace(s.slab, h_top=1.5, h_bot=min(s.slab.h_bot, 2.0)))


RAFT = thermal.SlabParams(thickness_m=1.2, n_cells=48, h_bot=1.0)


def standard_scenarios():
    """Slabs (0.30 m): January pours are protected (standard winter practice), June pours are not.

    ``*_jan_bare`` is the same January pour left uncovered (frost alert demo). The 1.2 m rafts are the
    thermal-crack demo.
    """
    jan = dict(start_utc="2024-01-08T07:00", t_place_c=10.0)
    jun = dict(start_utc="2024-06-10T07:00", t_place_c=20.0)
    sc = {
        "zurich_jan": covered(Scenario("Zurich slab, 8 Jan 2024", "zurich", **jan)),
        "zurich_jun": Scenario("Zurich slab, 10 Jun 2024", "zurich", **jun),
        "davos_jan": covered(Scenario("Davos slab, 8 Jan 2024", "davos", **jan)),
        "davos_jun": Scenario("Davos slab, 10 Jun 2024", "davos", **jun),
        "zurich_jan_bare": Scenario("Zurich slab, 8 Jan 2024 (bare)", "zurich", **jan),
        "davos_jan_bare": Scenario("Davos slab, 8 Jan 2024 (bare)", "davos", **jan),
        "raft_jun_bare": Scenario("Zurich raft 1.2 m, 10 Jun 2024 (bare)", "zurich", slab=RAFT, **jun),
    }
    sc["raft_jun_blanket"] = replace(
        covered(sc["raft_jun_bare"]), name="Zurich raft 1.2 m, 10 Jun 2024 (blanket)",
        slab=replace(RAFT, h_top=1.5))
    return sc


@dataclass
class PourSim:
    scenario: Scenario
    t_h: np.ndarray
    air_c: np.ndarray
    sensors_c: np.ndarray        # (nt, 3) top, mid, bottom
    depths_m: tuple[float, float, float]
    slab: thermal.SlabResult
    te_true: np.ndarray          # (nt, 3)


def simulate_pour(sc: Scenario) -> PourSim:
    air = weather.air_series(sc.site, sc.start_utc, sc.days)
    res = thermal.simulate_slab(air, sc.t_place_c, sc.slab)
    depths = sc.depths()
    cols = [res.sensor(d) for d in depths]
    sensors = np.column_stack(cols)
    # round to the logger resolution (0.01 C) as the payload would
    sensors = np.round(sensors, 2)
    te_true = np.column_stack([maturity.equivalent_age(res.t_h, sensors[:, j], None)
                               for j in range(3)])
    return PourSim(sc, res.t_h, res.air_c, sensors, depths, res, te_true)


@dataclass
class PourEval:
    method: str
    t_h: np.ndarray
    te_h: np.ndarray             # governing (minimum over sensors)
    s_mid: np.ndarray
    s_lo: np.ndarray
    s_hi: np.ndarray
    s_true: np.ndarray
    cross: dict                  # name -> {"mid","lo","hi","true"} hours or None
    alerts: list
    dt_k: np.ndarray
    crack_index: float
    governing_sensor: int


def _x(v):
    return None if v is None else float(v)


def evaluate_pour(sim: PourSim, cal: strength.Calibration, method: str = "arrhenius_40",
                  thresholds: dict | None = None, level: float = 0.90,
                  frost_crit: float = risks.FROST_CRIT_MPA,
                  dt_limit: float = risks.DT_LIMIT_K) -> PourEval:
    thresholds = THRESHOLDS if thresholds is None else thresholds
    te = equivalent_age_matrix(sim.t_h, sim.sensors_c, method)
    gov = np.min(te, axis=1)
    gov_sensor = int(np.argmin(te[-1]))
    s_mid = cal.predict(gov)
    s_lo, s_hi = cal.band(gov, level=level)
    s_lo = np.minimum(s_lo, s_mid)
    s_hi = np.maximum(s_hi, s_mid)
    s_true = true_strength(np.min(sim.te_true, axis=1))
    cross = {}
    for name, thr in thresholds.items():
        cross[name] = {
            "threshold_mpa": thr,
            "mid": _x(strength.crossing_time(sim.t_h, s_mid, thr)),
            "lo": _x(strength.crossing_time(sim.t_h, s_lo, thr)),   # conservative (late)
            "hi": _x(strength.crossing_time(sim.t_h, s_hi, thr)),   # optimistic (early)
            "true": _x(strength.crossing_time(sim.t_h, s_true, thr)),
        }
    alerts = risks.frost_alerts(sim.t_h, sim.sensors_c, s_lo, frost_crit)
    alerts += risks.frost_protection_needed(sim.t_h, sim.air_c, s_lo, frost_crit)
    dtk = risks.delta_t(sim.sensors_c[:, 1], sim.sensors_c[:, 0], sim.sensors_c[:, 2])
    alerts += risks.crack_alerts(sim.t_h, dtk, dt_limit)
    alerts.sort(key=lambda a: a.t_start_h)
    return PourEval(method, sim.t_h, gov, s_mid, s_lo, s_hi, s_true, cross, alerts, dtk,
                    risks.crack_risk_index(dtk, dt_limit), gov_sensor)


def calibrated(seed: int = 7, model: str | None = None) -> strength.Calibration:
    x, s = lab_specimens(seed)
    return strength.best_model(x, s) if model is None else strength.calibrate(x, s, model)
