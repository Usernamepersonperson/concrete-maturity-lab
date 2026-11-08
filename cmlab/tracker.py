"""Streaming maturity tracker: the logic a gateway or cloud function runs per uplink.

Feed it one decoded reading at a time (time since pour in hours + temperatures at 1-3 depths).
It integrates the equivalent age per sensor incrementally (trapezoid, same as the batch code),
tracks the governing (least mature) sensor and reports strength, threshold crossings and alerts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import maturity, risks, strength


@dataclass
class Status:
    t_h: float
    strength_mpa: float
    strength_lo_mpa: float
    crossed: dict
    frost_alarm: bool
    delta_t_k: float | None
    crack_alarm: bool


@dataclass
class MaturityTracker:
    cal: strength.Calibration
    ea_j_mol: float | None = maturity.EA_DEFAULT
    thresholds: dict = field(default_factory=lambda: {"strip": 15.0, "post_tension": 25.0})
    frost_crit_mpa: float = risks.FROST_CRIT_MPA
    dt_limit_k: float = risks.DT_LIMIT_K
    level: float = 0.90

    def __post_init__(self):
        self._t: float | None = None
        self._temps: np.ndarray | None = None
        self._te: np.ndarray | None = None
        self.crossings: dict[str, float] = {}
        self.history: list[Status] = []

    def _rate(self, temps):
        if self.ea_j_mol is None:
            return maturity.hp_rate(temps)
        return maturity.arrhenius_rate(temps, self.ea_j_mol)

    def update(self, t_h: float, temps_c) -> Status:
        temps = np.asarray([np.nan if v is None else v for v in temps_c], dtype=float)
        if self._t is not None and t_h <= self._t:
            raise ValueError("readings must arrive in increasing time order")
        if self._temps is not None and temps.size != self._temps.size:
            raise ValueError("number of channels changed")
        if self._t is None:
            self._te = np.zeros(temps.size)
        else:
            # a faulty channel (NaN) keeps its last good temperature
            use = np.where(np.isnan(temps), self._temps, temps)
            if np.any(np.isnan(use)):
                raise ValueError("channel has never reported a valid temperature")
            prev = self._temps
            dt = t_h - self._t
            self._te = self._te + 0.5 * (self._rate(use) + self._rate(prev)) * dt
            temps = use
        if np.any(np.isnan(temps)):
            raise ValueError("first reading must have valid temperatures")
        self._t, self._temps = t_h, temps
        x = float(self._te.min())
        s = float(self.cal.predict(x))
        lo = float(self.cal.band(np.array([x]), self.level)[0][0])
        lo = min(lo, s)
        for name, thr in self.thresholds.items():
            if name not in self.crossings and lo >= thr:
                self.crossings[name] = t_h
        dtk = None
        crack = False
        if temps.size == 3:
            dtk = float(risks.delta_t(temps[1], temps[0], temps[2]))
            crack = dtk >= self.dt_limit_k
        st = Status(t_h, s, lo, dict(self.crossings),
                    bool(temps.min() <= 0.0 and lo < self.frost_crit_mpa), dtk, crack)
        self.history.append(st)
        return st
