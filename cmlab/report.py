"""Pour report (markdown) for one simulated or logged pour."""
from __future__ import annotations

import numpy as np

from . import pipeline as P
from . import weather

REPORT_HOURS = (12, 24, 48, 72, 168)


def _fmt(v, unit="h"):
    return "not reached in window" if v is None else f"{v:.1f} {unit}"


def pour_report(sim: P.PourSim, ev: P.PourEval, cal) -> str:
    sc = sim.scenario
    lines = [
        f"# Pour report: {sc.name}",
        "",
        "SIMULATED pour (1-D slab heat model) driven by real air temperature "
        f"({weather.SOURCE}). Not a measurement of a real structure.",
        "",
        "## Setup",
        f"- Site: {sc.site}; pour start (UTC): {sc.start_utc}; fresh concrete {sc.t_place_c:g} C",
        f"- Member: {sc.slab.thickness_m:g} m slab; sensors at {', '.join(f'{d * 100:.0f} cm' for d in sim.depths_m)} depth"
        f"; surface conductance top {sc.slab.h_top:g}, bottom {sc.slab.h_bot:g} W/m2K",
        f"- Maturity index: {ev.method}; strength model: {cal.model} "
        f"(lab fit RMSE {cal.rmse:.2f} MPa, leave-one-age-out {cal.loo_rmse:.2f} MPa, {cal.n} specimens)",
        f"- Governing sensor at end of window: #{ev.governing_sensor} "
        "(least mature sensor sets the strength)",
        "",
        "## Decisions",
        "| Milestone | Strength | Best estimate | Conservative (lower 90% bound) | Optimistic |",
        "|---|---|---|---|---|",
    ]
    for name, c in ev.cross.items():
        lines.append(f"| {name.replace('_', ' ')} | {c['threshold_mpa']:g} MPa | {_fmt(c['mid'])} | "
                     f"{_fmt(c['lo'])} | {_fmt(c['hi'])} |")
    fixed = P.FIXED_RULE_H
    strip = ev.cross["strip"]["mid"]
    if strip is not None:
        lines += ["", f"Compared with a fixed {fixed / 24:.0f}-day rule: strip {fixed - strip:.0f} h "
                      "earlier (simulated)."]
    lines += ["", "## Strength vs time", "| Hours | Strength (MPa) | 90% band |", "|---|---|---|"]
    for h in REPORT_HOURS:
        if h <= sim.t_h[-1]:
            m = float(np.interp(h, sim.t_h, ev.s_mid))
            lo = float(np.interp(h, sim.t_h, ev.s_lo))
            hi = float(np.interp(h, sim.t_h, ev.s_hi))
            lines.append(f"| {h} | {m:.1f} | {lo:.1f} to {hi:.1f} |")
    lines += ["", "## Temperatures",
              f"- Peak sensor temperature {sim.sensors_c.max():.1f} C; minimum in first 72 h "
              f"{sim.sensors_c[sim.t_h <= 72].min():.1f} C",
              f"- Peak core-surface difference {ev.dt_k.max():.1f} K "
              f"(index {ev.crack_index:.2f} of the 20 K guide limit)",
              "", "## Alerts"]
    if not ev.alerts:
        lines.append("- none")
    for a in ev.alerts:
        lines.append(f"- [{a.level.upper()}] {a.kind} {a.t_start_h:.1f}-{a.t_end_h:.1f} h: {a.message}")
    lines += ["", "## Limits",
              "- Maturity numbers are not valid once concrete freezes; an alarm replaces the estimate.",
              "- The strength curve comes from simulated lab cylinders; calibrate your own mix before use.",
              "- Thresholds (15 / 25 MPa) are example values; use the project specification.",
              ""]
    return "\n".join(lines)
