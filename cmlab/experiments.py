"""Reproducible experiments behind the README numbers (all simulated pours on real weather)."""
from __future__ import annotations

import numpy as np

from . import pipeline as P
from . import strength

SENS_METHODS = ["arrhenius_30", "arrhenius_40", "arrhenius_50",
                "nurse_saul_T0=-10", "nurse_saul_T0=0", "nurse_saul_T0=5", "hansen_pedersen"]


def _r(v, nd=1):
    return None if v is None else round(float(v), nd)


def calibration_stats(seed: int = 7):
    x, s = P.lab_specimens(seed)
    grid = np.linspace(12, 672, 200)
    truth = P.true_strength(grid)
    out = {}
    for m in strength.MODELS:
        c = strength.calibrate(x, s, m)
        err = c.predict(grid) - truth
        out[m] = {"rmse_mpa": _r(c.rmse, 2), "loo_rmse_mpa": _r(c.loo_rmse, 2),
                  "vs_truth_rmse_mpa": _r(np.sqrt(np.mean(err**2)), 2),
                  "vs_truth_max_abs_mpa": _r(np.max(np.abs(err)), 2),
                  "params": [_r(p, 4) for p in c.params]}
    best = strength.best_model(x, s)
    return {"n_specimens": int(x.size), "models": out, "selected": best.model}


def calibration_seed_spread(n_seeds: int = 60):
    """Strip-time error vs truth when the lab campaign is repeated with different noise draws."""
    sims = {k: P.simulate_pour(sc) for k, sc in P.standard_scenarios().items()
            if k in ("zurich_jan", "zurich_jun")}
    err = {k: [] for k in sims}
    for seed in range(100, 100 + n_seeds):
        cal = P.calibrated(seed)
        for k, sim in sims.items():
            ev = P.evaluate_pour(sim, cal, "hansen_pedersen")
            c = ev.cross["strip"]
            if c["mid"] is not None and c["true"] is not None:
                err[k].append(c["mid"] - c["true"])
    return {k: {"mean_h": _r(np.mean(v)), "sd_h": _r(np.std(v)), "p05_h": _r(np.quantile(v, 0.05)),
                "p95_h": _r(np.quantile(v, 0.95)), "n": len(v)} for k, v in err.items()}


def pour_table(cal):
    rows = {}
    for key, sc in P.standard_scenarios().items():
        sim = P.simulate_pour(sc)
        ev = P.evaluate_pour(sim, cal, "arrhenius_40")
        evt = P.evaluate_pour(sim, cal, "hansen_pedersen")
        gov = ev.governing_sensor
        rows[key] = {
            "name": sc.name,
            "tmax_c": _r(sim.sensors_c.max()),
            "tmin_c_first_72h": _r(sim.sensors_c[sim.t_h <= 72].min()),
            "air_mean_c_first_72h": _r(sim.air_c[sim.t_h <= 72].mean()),
            "crack_index": _r(ev.crack_index, 2),
            "max_dT_k": _r(ev.dt_k.max()),
            "governing_sensor": gov,
            "cross_arrhenius40": {n: {k: _r(v) for k, v in c.items()} for n, c in ev.cross.items()},
            "cross_hp": {n: {k: _r(v) for k, v in c.items()} for n, c in evt.cross.items()},
            "alerts": [(a.kind, _r(a.t_start_h), _r(a.t_end_h), _r(a.peak)) for a in ev.alerts],
            "strength_7d_arrhenius40": _r(np.interp(P.FIXED_RULE_H, sim.t_h, ev.s_mid)),
            "strength_7d_true": _r(np.interp(P.FIXED_RULE_H, sim.t_h, ev.s_true)),
        }
    return rows


def sensitivity(cal, scenarios=("zurich_jan", "zurich_jun", "davos_jan", "davos_jun")):
    out = {}
    for key in scenarios:
        sim = P.simulate_pour(P.standard_scenarios()[key])
        row = {}
        for m in SENS_METHODS:
            ev = P.evaluate_pour(sim, cal, m)
            row[m] = {"strip_h": _r(ev.cross["strip"]["mid"]),
                      "post_tension_h": _r(ev.cross["post_tension"]["mid"])}
        truth = P.evaluate_pour(sim, cal, "hansen_pedersen").cross["strip"]["true"]
        row["truth_strip_h"] = _r(truth)
        out[key] = row
    return out


def method_agreement(cal, key="zurich_jan"):
    """Equivalent age at 72 h of the pour for each method, Jan vs Jun, vs truth (HP) kinetics."""
    out = {}
    for k in (key, key.replace("jan", "jun")):
        sim = P.simulate_pour(P.standard_scenarios()[k])
        i = int(np.argmin(np.abs(sim.t_h - 72)))
        row = {}
        for m in SENS_METHODS:
            te = P.equivalent_age_matrix(sim.t_h, sim.sensors_c, m)
            row[m] = _r(te[i].min())
        row["truth"] = _r(sim.te_true[i].min())
        out[k] = row
    return out


def run_all():
    cal = P.calibrated()
    return {
        "calibration": calibration_stats(),
        "calibration_seed_spread": calibration_seed_spread(),
        "pours": pour_table(cal),
        "sensitivity": sensitivity(cal),
        "equivalent_age_72h": method_agreement(cal),
        "selected_model": cal.model,
        "thresholds_mpa": P.THRESHOLDS,
    }
