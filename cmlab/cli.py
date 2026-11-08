"""Command line: demo, report, scenarios, decode."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import experiments, figures, payload, report
from . import pipeline as P


def cmd_demo(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cal = P.calibrated()
    res = experiments.run_all()
    (out / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    sc = P.standard_scenarios()
    for key in ("zurich_jan", "zurich_jun", "zurich_jan_bare", "raft_jun_bare"):
        sim = P.simulate_pour(sc[key])
        ev = P.evaluate_pour(sim, cal, "arrhenius_40")
        (out / f"pour_report_{key}.md").write_text(report.pour_report(sim, ev, cal))
    if not a.no_figures:
        docs = Path(a.docs)
        docs.mkdir(parents=True, exist_ok=True)
        figures.main_figure(docs / "figure.png", cal)
        figures.post_figure(docs / "post-figure.png", cal)
        figures.alerts_figure(docs / "alerts.png", cal)
    zj = res["pours"]["zurich_jan"]["cross_arrhenius40"]["strip"]
    zu = res["pours"]["zurich_jun"]["cross_arrhenius40"]["strip"]
    print(f"Calibration: selected {res['selected_model']}, models {list(res['calibration']['models'])}")
    for m, v in res["calibration"]["models"].items():
        print(f"  {m:11s} RMSE {v['rmse_mpa']} MPa  leave-one-age-out {v['loo_rmse_mpa']} MPa")
    print(f"Zurich strip 15 MPa: Jan {zj['mid']} h (truth {zj['true']}), Jun {zu['mid']} h (truth {zu['true']})")
    print(f"Wrote {out}/results.json and pour reports" + ("" if a.no_figures else f", figures in {a.docs}"))
    return 0


def cmd_report(a) -> int:
    scs = P.standard_scenarios()
    if a.scenario not in scs:
        print(f"unknown scenario {a.scenario!r}; choose from {', '.join(scs)}", file=sys.stderr)
        return 2
    cal = P.calibrated()
    sim = P.simulate_pour(scs[a.scenario])
    ev = P.evaluate_pour(sim, cal, a.method)
    text = report.pour_report(sim, ev, cal)
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)
    return 0


def cmd_scenarios(_a) -> int:
    for k, s in P.standard_scenarios().items():
        print(f"{k:18s} {s.name}")
    return 0


def cmd_decode(a) -> int:
    try:
        r = payload.decode(bytes.fromhex(a.hex))
    except (ValueError, payload.PayloadError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"seq": r.seq, "temps_c": list(r.temps_c), "battery_mv": r.battery_mv,
                      "low_battery": r.low_battery}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cmlab", description="Concrete maturity lab")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="reproduce all README numbers and figures")
    d.add_argument("--out", default="results")
    d.add_argument("--docs", default="docs")
    d.add_argument("--no-figures", action="store_true")
    d.set_defaults(fn=cmd_demo)
    r = sub.add_parser("report", help="markdown pour report for a scenario")
    r.add_argument("--scenario", default="zurich_jan")
    r.add_argument("--method", default="arrhenius_40", choices=sorted(P.METHODS))
    r.add_argument("--out")
    r.set_defaults(fn=cmd_report)
    s = sub.add_parser("scenarios", help="list built-in scenarios")
    s.set_defaults(fn=cmd_scenarios)
    x = sub.add_parser("decode", help="decode a logger payload (hex)")
    x.add_argument("hex")
    x.set_defaults(fn=cmd_decode)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
