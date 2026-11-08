"""Maturity indices from a temperature history.

All functions take a temperature series ``temp_c`` (deg C) sampled at times ``t_h`` (hours)
and return a cumulative series (same length, starting at 0). Integration uses the trapezoid
rule between samples.

References (public):
- Nurse-Saul function: Saul, A.G.A. (1951) Magazine of Concrete Research 2(6); ASTM C1074
  "Estimating Concrete Strength by the Maturity Method" (datum temperature T0, default 0 C).
- Arrhenius equivalent age: Freiesleben Hansen & Pedersen (1977), Nordisk Betong 1; ASTM C1074.
  te = integral exp(-Ea/R (1/T - 1/Tr)) dt, reference temperature Tr = 20 C.
- Carino & Lew (2001) "The Maturity Method: From Theory to Application", NIST.
"""
from __future__ import annotations

import numpy as np

R_GAS = 8.314  # J/(mol K)
T_REF_C = 20.0
EA_DEFAULT = 40_000.0  # J/mol, order of magnitude for portland cement (ASTM C1074 gives 40-45 kJ/mol)


def _check(t_h, temp_c):
    t = np.asarray(t_h, dtype=float)
    temp = np.asarray(temp_c, dtype=float)
    if t.ndim != 1 or t.shape != temp.shape:
        raise ValueError("t_h and temp_c must be 1-D arrays of equal length")
    if t.size < 1:
        raise ValueError("empty series")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(temp))):
        raise ValueError("non-finite values in input")
    if np.any(np.diff(t) <= 0):
        raise ValueError("t_h must be strictly increasing")
    return t, temp


def _cumulative(t, rate):
    """Trapezoid cumulative integral of ``rate`` over ``t`` starting at 0."""
    out = np.zeros_like(rate)
    if t.size > 1:
        out[1:] = np.cumsum(0.5 * (rate[1:] + rate[:-1]) * np.diff(t))
    return out


def nurse_saul(t_h, temp_c, t0_c: float = 0.0):
    """Temperature-time factor M(t) in deg C * hours; no contribution below datum ``t0_c``."""
    t, temp = _check(t_h, temp_c)
    return _cumulative(t, np.maximum(temp - t0_c, 0.0))


def nurse_saul_equivalent_age(t_h, temp_c, t0_c: float = 0.0, t_ref_c: float = T_REF_C):
    """Nurse-Saul factor expressed as equivalent age (hours) at ``t_ref_c``."""
    if t_ref_c <= t0_c:
        raise ValueError("reference temperature must exceed datum temperature")
    return nurse_saul(t_h, temp_c, t0_c) / (t_ref_c - t0_c)


def arrhenius_rate(temp_c, ea_j_mol=EA_DEFAULT, t_ref_c: float = T_REF_C):
    """Age conversion factor k(T) = exp(-Ea/R (1/T - 1/Tr)), dimensionless (1 at Tr)."""
    if np.any(np.asarray(ea_j_mol) <= 0):
        raise ValueError("activation energy must be positive")
    tk = np.asarray(temp_c, dtype=float) + 273.15
    if np.any(tk <= 0):
        raise ValueError("temperature below absolute zero")
    return np.exp(-ea_j_mol / R_GAS * (1.0 / tk - 1.0 / (t_ref_c + 273.15)))


def activation_energy_hp(temp_c):
    """Temperature dependent Ea (J/mol), Freiesleben Hansen & Pedersen (1977).

    33.5 kJ/mol at and above 20 C, +1.47 kJ/mol per K below 20 C. Used as the "truth" kinetics in
    the simulations, so the constant-Ea and Nurse-Saul indices can be compared against it.
    """
    temp = np.asarray(temp_c, dtype=float)
    return 33_500.0 + 1_470.0 * np.maximum(20.0 - temp, 0.0)


def hp_rate(temp_c, t_ref_c: float = T_REF_C):
    """Age conversion factor with the temperature dependent Ea of ``activation_energy_hp``."""
    return arrhenius_rate(temp_c, activation_energy_hp(temp_c), t_ref_c)


def equivalent_age(t_h, temp_c, ea_j_mol: float | None = EA_DEFAULT, t_ref_c: float = T_REF_C):
    """Equivalent age (hours at ``t_ref_c``). ``ea_j_mol=None`` selects the Hansen-Pedersen Ea(T)."""
    t, temp = _check(t_h, temp_c)
    rate = hp_rate(temp, t_ref_c) if ea_j_mol is None else arrhenius_rate(temp, ea_j_mol, t_ref_c)
    return _cumulative(t, rate)
