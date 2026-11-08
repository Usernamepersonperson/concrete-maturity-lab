"""Alerts: early-age frost risk and thermal-crack (core-surface temperature difference) risk.

Defaults are parameters, not code truths. Check them against the project specification:
- Frost: concrete must reach a minimum strength before it freezes. 5 MPa is the commonly quoted
  EN 13670 / EN 206 practice value (national annexes vary); ACI 306R uses about 3.5 MPa.
- Thermal cracking: a core-to-surface difference around 20 K is a commonly used guide limit
  (values of 15-25 K appear in national guidance depending on member and cement). The indicator
  here is only a screening ratio, not a crack-width prediction.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FROST_CRIT_MPA = 5.0
FROST_WARN_TEMP_C = 2.0
DT_LIMIT_K = 20.0
DT_WARN_FRACTION = 0.75


@dataclass(frozen=True)
class Alert:
    kind: str       # frost_protect | frost_warn | frost_alarm | crack_warn | crack_alarm
    level: str      # warn | alarm
    t_start_h: float
    t_end_h: float
    peak: float     # min temperature (frost) or max dT (crack)
    message: str


def _episodes(mask: np.ndarray, t: np.ndarray):
    """Contiguous True runs as (start_time, end_time, slice)."""
    out = []
    i = 0
    n = mask.size
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((float(t[i]), float(t[j]), slice(i, j + 1)))
            i = j + 1
        else:
            i += 1
    return out


def frost_alerts(t_h, sensor_temps, strength_mpa, crit_mpa: float = FROST_CRIT_MPA,
                 warn_temp_c: float = FROST_WARN_TEMP_C) -> list[Alert]:
    """Alarm when any sensor is at or below 0 C while strength is under ``crit_mpa``.

    Warn when any sensor is within ``warn_temp_c`` of freezing (but above 0 C) under the same condition.
    ``sensor_temps`` is (nt, ns); ``strength_mpa`` the governing (minimum) strength, shape (nt,).
    """
    t = np.asarray(t_h, dtype=float)
    temps = np.asarray(sensor_temps, dtype=float)
    if temps.ndim == 1:
        temps = temps[:, None]
    s = np.asarray(strength_mpa, dtype=float)
    if temps.shape[0] != t.size or s.size != t.size:
        raise ValueError("series length mismatch")
    tmin = temps.min(axis=1)
    weak = s < crit_mpa
    alerts = []
    for a, b, sl in _episodes(weak & (tmin <= 0.0), t):
        alerts.append(Alert("frost_alarm", "alarm", a, b, float(tmin[sl].min()),
                            f"Concrete at/below 0 C with strength < {crit_mpa:g} MPa "
                            f"(min {tmin[sl].min():.1f} C)"))
    for a, b, sl in _episodes(weak & (tmin > 0.0) & (tmin <= warn_temp_c), t):
        alerts.append(Alert("frost_warn", "warn", a, b, float(tmin[sl].min()),
                            f"Concrete within {warn_temp_c:g} K of freezing, strength < {crit_mpa:g} MPa"))
    return sorted(alerts, key=lambda x: x.t_start_h)


def frost_protection_needed(t_h, air_c, strength_mpa, crit_mpa: float = FROST_CRIT_MPA,
                            horizon_h: float = 24.0) -> list[Alert]:
    """Protect-now advisory: strength still below ``crit_mpa`` and air (or forecast) <= 0 C within horizon."""
    t = np.asarray(t_h, dtype=float)
    air = np.asarray(air_c, dtype=float)
    s = np.asarray(strength_mpa, dtype=float)
    if not (t.size == air.size == s.size):
        raise ValueError("series length mismatch")
    dt = np.median(np.diff(t)) if t.size > 1 else 1.0
    w = max(int(round(horizon_h / dt)), 1)
    fut_min = np.array([air[i:i + w + 1].min() for i in range(air.size)])
    mask = (s < crit_mpa) & (fut_min <= 0.0)
    return [Alert("frost_protect", "warn", a, b, float(fut_min[sl].min()),
                  f"Cover / heat the pour: air <= 0 C within {horizon_h:g} h and strength < {crit_mpa:g} MPa")
            for a, b, sl in _episodes(mask, t)]


def delta_t(sensor_core, sensor_surface_a, sensor_surface_b=None) -> np.ndarray:
    """Core minus the colder of the surface sensors (K)."""
    core = np.asarray(sensor_core, dtype=float)
    surf = np.asarray(sensor_surface_a, dtype=float)
    if sensor_surface_b is not None:
        surf = np.minimum(surf, np.asarray(sensor_surface_b, dtype=float))
    return core - surf


def crack_alerts(t_h, dt_k, limit_k: float = DT_LIMIT_K,
                 warn_fraction: float = DT_WARN_FRACTION) -> list[Alert]:
    """Warn at ``warn_fraction`` x limit, alarm at the limit (core-surface difference)."""
    t = np.asarray(t_h, dtype=float)
    d = np.asarray(dt_k, dtype=float)
    if t.size != d.size:
        raise ValueError("series length mismatch")
    if limit_k <= 0:
        raise ValueError("limit must be positive")
    alerts = []
    for a, b, sl in _episodes(d >= limit_k, t):
        alerts.append(Alert("crack_alarm", "alarm", a, b, float(d[sl].max()),
                            f"Core-surface difference {d[sl].max():.1f} K >= {limit_k:g} K"))
    warn_lvl = warn_fraction * limit_k
    for a, b, sl in _episodes((d >= warn_lvl) & (d < limit_k), t):
        alerts.append(Alert("crack_warn", "warn", a, b, float(d[sl].max()),
                            f"Core-surface difference {d[sl].max():.1f} K >= {warn_lvl:g} K"))
    return sorted(alerts, key=lambda x: x.t_start_h)


def crack_risk_index(dt_k, limit_k: float = DT_LIMIT_K) -> float:
    """Peak core-surface difference as a fraction of the limit (1.0 = at the limit)."""
    d = np.asarray(dt_k, dtype=float)
    return float(np.max(d) / limit_k) if d.size else 0.0
