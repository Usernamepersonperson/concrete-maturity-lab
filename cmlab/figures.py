"""Figures: README figure (1600x900), phone-sized post figure (960x700), alert figure."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import pipeline as P  # noqa: E402
from . import strength  # noqa: E402

BG = "#16213A"
GRID = "#2A3750"
TEXT = "#F8FAFC"
MUTED = "#A9B6CB"
ACCENT = "#38BDF8"
GREEN = "#34D399"
AMBER = "#FBBF24"
RED = "#F87171"
GREY = "#64748B"
VIOLET = "#A78BFA"

CAPTION = "Simulated pours on real air temperature: Open-Meteo archive (CC BY 4.0), 2024"


def _style():
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"],
        "text.color": TEXT, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": GRID, "axes.facecolor": BG, "figure.facecolor": BG,
        "savefig.facecolor": BG, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def _title(fig, title, sub, size=19):
    fig.text(0.04, 0.955, title, fontsize=size * 0.72, fontweight="bold", color=TEXT, va="top")
    fig.text(0.04, 0.90, sub, fontsize=11.5, color=MUTED, va="top")


def _pair(cal, key_jan="zurich_jan", key_jun="zurich_jun", method="arrhenius_40"):
    sc = P.standard_scenarios()
    out = {}
    for tag, key in (("jan", key_jan), ("jun", key_jun)):
        sim = P.simulate_pour(sc[key])
        out[tag] = (sim, P.evaluate_pour(sim, cal, method))
    return out


def _curve(ax, sim, ev, color, label, tmax):
    m = sim.t_h <= tmax
    ax.fill_between(sim.t_h[m], ev.s_lo[m], ev.s_hi[m], color=color, alpha=0.25, lw=0)
    ax.plot(sim.t_h[m], ev.s_mid[m], color=color, lw=3.2, label=label)


def _cross_marker(ax, t, thr, color, text, dy, dx=0):
    ax.plot([t, t], [0, thr], color=color, lw=1.4, ls="--")
    ax.scatter([t], [thr], s=90, color=color, zorder=5, edgecolor=BG, linewidth=1.5)
    ax.annotate(text, (t, thr), xytext=(t + dx, thr + dy), color=color, fontsize=13,
                fontweight="bold", ha="left")


def post_figure(path: Path, cal=None, data=None):
    _style()
    cal = cal or P.calibrated()
    d = data or _pair(cal)
    (sj, ej), (su, eu) = d["jan"], d["jun"]
    tj, tu = ej.cross["strip"]["mid"], eu.cross["strip"]["mid"]
    thr = P.THRESHOLDS["strip"]
    fig = plt.figure(figsize=(9.6, 7.0), dpi=100, facecolor=BG)
    ax = fig.add_axes([0.10, 0.12, 0.86, 0.69])
    _curve(ax, su, eu, AMBER, "June pour", 72)
    _curve(ax, sj, ej, ACCENT, "January pour (protected)", 72)
    ax.axhline(thr, color=GREEN, lw=1.8)
    ax.text(71, thr + 0.8, f"strip at {thr:g} MPa", color=GREEN, fontsize=13, ha="right")
    _cross_marker(ax, tu, thr, AMBER, f"June: {tu:.0f} h", -3.6, 1.2)
    _cross_marker(ax, tj, thr, ACCENT, f"January: {tj:.0f} h", -3.6, 1.2)
    ax.set_xlim(0, 72)
    ax.set_ylim(0, 33)
    ax.set_xticks(range(0, 73, 12))
    ax.set_xlabel("hours since pour", fontsize=13)
    ax.set_ylabel("in-place strength (MPa)", fontsize=13)
    ax.tick_params(labelsize=13)
    ax.legend(loc="upper left", frameon=False, fontsize=13, labelcolor=TEXT)
    _title(fig, f"Same slab, same mix: strip {tj - tu:.0f} h later in January", CAPTION + "; band = 90% calibration CI")
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main_figure(path: Path, cal=None, data=None):
    from . import experiments as E

    _style()
    cal = cal or P.calibrated()
    d = data or _pair(cal)
    (sj, ej), (su, eu) = d["jan"], d["jun"]
    fig, axs = plt.subplots(2, 2, figsize=(16, 9), dpi=100, facecolor=BG)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.08, hspace=0.38, wspace=0.18)
    thr, pt = P.THRESHOLDS["strip"], P.THRESHOLDS["post_tension"]

    ax = axs[0, 0]
    _curve(ax, su, eu, AMBER, "June", 120)
    _curve(ax, sj, ej, ACCENT, "January (protected)", 120)
    ax.axhline(thr, color=GREEN, lw=1.5)
    ax.axhline(pt, color=VIOLET, lw=1.5)
    ax.text(119, thr + 0.7, "strip 15 MPa", color=GREEN, fontsize=11, ha="right")
    ax.text(119, pt + 0.7, "post-tension 25 MPa", color=VIOLET, fontsize=11, ha="right")
    for e, c in ((eu, AMBER), (ej, ACCENT)):
        ax.scatter([e.cross["strip"]["mid"]], [thr], s=60, color=c, zorder=5)
        ax.scatter([e.cross["post_tension"]["mid"]], [pt], s=60, color=c, zorder=5)
    ax.set_title("Strength vs time, Zurich (band = 90% CI)", loc="left", color=TEXT, fontsize=13)
    ax.set_xlabel("hours since pour")
    ax.set_ylabel("MPa")
    ax.legend(loc="lower right", frameon=False, labelcolor=TEXT)
    ax.set_xlim(0, 120)

    ax = axs[0, 1]
    for sim, ls, tag in ((sj, "-", "Jan"), (su, "--", "Jun")):
        m = sim.t_h <= 96
        ax.plot(sim.t_h[m], sim.air_c[m], color=GREY, lw=1.6, ls=ls)
        ax.plot(sim.t_h[m], sim.sensors_c[m, 0], color=ACCENT if tag == "Jan" else AMBER, lw=2,
                ls=ls, label=f"{tag} top 2 cm")
        ax.plot(sim.t_h[m], sim.sensors_c[m, 1], color=GREEN if tag == "Jan" else RED, lw=2,
                ls=ls, label=f"{tag} core")
    ax.plot([], [], color=GREY, label="air")
    ax.set_title("Simulated embedded sensors (30 cm slab), grey = air", loc="left", color=TEXT, fontsize=13)
    ax.set_xlabel("hours since pour")
    ax.set_ylabel("deg C")
    ax.legend(loc="upper right", frameon=False, ncol=3, fontsize=9.5, labelcolor=TEXT)
    ax.set_xlim(0, 96)

    ax = axs[1, 0]
    x, s = P.lab_specimens()
    grid = np.linspace(8, 700, 300)
    ax.scatter(x, s, s=22, color=TEXT, alpha=0.85, label="simulated lab cylinders", zorder=4)
    for m, c in (("log", RED), ("hyperbolic", ACCENT), ("exp", GREEN)):
        cm = strength.calibrate(x, s, m)
        ax.plot(grid, cm.predict(grid), color=c, lw=2, label=f"{m}: LOO {cm.loo_rmse:.1f} MPa")
    ax.set_xscale("log")
    ax.set_title("Calibration from lab tests (24 specimens)", loc="left", color=TEXT, fontsize=13)
    ax.set_xlabel("age at 20 C (h, log scale)")
    ax.set_ylabel("MPa")
    ax.legend(loc="lower right", frameon=False, labelcolor=TEXT, fontsize=10)

    ax = axs[1, 1]
    sens = E.sensitivity(cal, ("zurich_jan", "zurich_jun"))
    methods = ["arrhenius_30", "arrhenius_40", "arrhenius_50", "nurse_saul_T0=-10",
               "nurse_saul_T0=0", "nurse_saul_T0=5", "hansen_pedersen"]
    labels = ["Ea 30", "Ea 40", "Ea 50", "NS -10", "NS 0", "NS 5", "Ea(T)"]
    xs = np.arange(len(methods))
    for off, key, c, lab in ((-0.2, "zurich_jan", ACCENT, "Jan"), (0.2, "zurich_jun", AMBER, "Jun")):
        vals = [sens[key][m]["strip_h"] for m in methods]
        ax.bar(xs + off, vals, width=0.38, color=c, label=lab)
        ax.axhline(sens[key]["truth_strip_h"], color=c, lw=1.3, ls=":")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title("Strip time by index choice (dotted = simulated truth)", loc="left", color=TEXT, fontsize=13)
    ax.set_ylabel("hours to 15 MPa")
    ax.set_ylim(0, 62)
    ax.legend(loc="upper left", frameon=False, labelcolor=TEXT, ncol=2)
    _title(fig, "Concrete maturity lab: temperature in, strip time out", CAPTION, size=24)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def alerts_figure(path: Path, cal=None):
    _style()
    cal = cal or P.calibrated()
    sc = P.standard_scenarios()
    fig, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=100, facecolor=BG)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.10, wspace=0.18)
    sim = P.simulate_pour(sc["zurich_jan_bare"])
    ev = P.evaluate_pour(sim, cal, "hansen_pedersen")
    ax = axs[0]
    m = sim.t_h <= 72
    ax.plot(sim.t_h[m], sim.sensors_c[m, 0], color=ACCENT, lw=2.4, label="top sensor")
    ax.plot(sim.t_h[m], sim.air_c[m], color=GREY, lw=1.6, label="air")
    ax.axhline(0, color=TEXT, lw=0.8)
    for a in ev.alerts:
        if a.kind == "frost_alarm":
            ax.axvspan(a.t_start_h, min(a.t_end_h, 72), color=RED, alpha=0.3)
        elif a.kind == "frost_warn":
            ax.axvspan(a.t_start_h, min(a.t_end_h, 72), color=AMBER, alpha=0.25)
    ax.set_ylabel("deg C")
    ax.set_xlabel("hours since pour")
    ax.set_title("Frost risk: bare January slab (red = alarm, amber = warn, strength < 5 MPa)",
                 loc="left", color=TEXT, fontsize=12)
    ax.legend(loc="upper right", frameon=False, labelcolor=TEXT)
    ax2 = axs[1]
    for key, c, lab in (("raft_jun_bare", RED, "bare"), ("raft_jun_blanket", GREEN, "blanket")):
        s2 = P.simulate_pour(sc[key])
        e2 = P.evaluate_pour(s2, cal)
        mm = s2.t_h <= 240
        ax2.plot(s2.t_h[mm], e2.dt_k[mm], color=c, lw=2.6, label=f"1.2 m raft, {lab}")
    ax2.axhline(20, color=AMBER, lw=1.6, ls="--")
    ax2.text(236, 20.8, "20 K guide limit", color=AMBER, fontsize=12, ha="right")
    ax2.set_xlabel("hours since pour")
    ax2.set_ylabel("core minus coldest surface (K)")
    ax2.set_title("Thermal-crack indicator, June raft", loc="left", color=TEXT, fontsize=12)
    ax2.legend(loc="upper right", frameon=False, labelcolor=TEXT)
    _title(fig, "Alerts from the same sensor stream", CAPTION, size=24)
    fig.savefig(path, dpi=100)
    plt.close(fig)
