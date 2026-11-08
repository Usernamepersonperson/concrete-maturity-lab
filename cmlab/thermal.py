"""1-D heat model of a concrete slab with cement hydration heat.

Finite-volume, backward-Euler conduction through the thickness (top surface z=0 to soffit z=H).
Both faces exchange heat with the air through a surface conductance (top: open air or blanket,
bottom: formwork). The hydration heat source follows the degree of hydration

    alpha(te) = exp(-(tau_h / te)^beta_h)

(Freiesleben Hansen & Pedersen 1985 form) where te is the equivalent age of each cell, advanced with
the temperature dependent activation energy of ``maturity.activation_energy_hp``.
Heat per volume released is Q_total * d(alpha). This is a textbook-level model, not a substitute
for a calibrated FE tool; parameters are typical values for a CEM II type mix and are inputs.

Ref: Schindler & Folliard (2005) ACI Materials Journal 102(1), "Heat of hydration models for
cementitious materials" (degree-of-hydration form above); conduction constants are handbook values.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_banded

from .maturity import hp_rate


@dataclass(frozen=True)
class SlabParams:
    thickness_m: float = 0.30
    conductivity: float = 2.3         # W/(m K)
    rho_c: float = 2.4e6              # volumetric heat capacity, J/(m3 K)
    q_total: float = 115e6            # J/m3: ~330 kg/m3 cement x ~350 kJ/kg
    tau_h: float = 20.0               # h
    beta_h: float = 1.2
    h_top: float = 12.0               # W/(m2 K) bare surface with some wind
    h_bot: float = 4.0                # W/(m2 K) plywood formwork on props
    n_cells: int = 30
    dt_h: float = 0.25

    @property
    def adiabatic_rise_k(self) -> float:
        return self.q_total / self.rho_c


@dataclass
class SlabResult:
    t_h: np.ndarray          # (nt,) hours since pour
    air_c: np.ndarray        # (nt,)
    temp_c: np.ndarray       # (nt, ncells) top to bottom
    z_m: np.ndarray          # (ncells,) cell centre depth below top surface
    te_h: np.ndarray         # (nt, ncells) true equivalent age (HP kinetics)

    def sensor(self, depth_m: float) -> np.ndarray:
        j = int(np.argmin(np.abs(self.z_m - depth_m)))
        return self.temp_c[:, j]


def alpha_hydration(te_h, tau_h: float, beta_h: float):
    te = np.maximum(np.asarray(te_h, dtype=float), 1e-9)
    return np.exp(-((tau_h / te) ** beta_h))


def simulate_slab(air_c, t_place_c: float, p: SlabParams | None = None, hours: float | None = None,
                  air_dt_h: float = 1.0) -> SlabResult:
    """Simulate a pour. ``air_c`` is hourly (``air_dt_h``) air temperature starting at the pour time."""
    p = SlabParams() if p is None else p
    air = np.asarray(air_c, dtype=float)
    if air.ndim != 1 or air.size < 2:
        raise ValueError("air_c must be a 1-D series with at least 2 points")
    if not np.all(np.isfinite(air)):
        raise ValueError("non-finite air temperature")
    if p.thickness_m <= 0 or p.n_cells < 3 or p.dt_h <= 0:
        raise ValueError("invalid slab parameters")
    span = (air.size - 1) * air_dt_h
    hours = span if hours is None else min(hours, span)
    n = p.n_cells
    dz = p.thickness_m / n
    dt = p.dt_h * 3600.0
    nsteps = int(round(hours / p.dt_h))
    c_cell = p.rho_c * dz
    g_in = p.conductivity / dz
    g_top = 1.0 / (dz / (2 * p.conductivity) + 1.0 / p.h_top) if p.h_top > 0 else 0.0
    g_bot = 1.0 / (dz / (2 * p.conductivity) + 1.0 / p.h_bot) if p.h_bot > 0 else 0.0

    diag = np.full(n, c_cell / dt + 2 * g_in)
    diag[0] = c_cell / dt + g_in + g_top
    diag[-1] = c_cell / dt + g_in + g_bot
    ab = np.zeros((3, n))
    ab[0, 1:] = -g_in
    ab[1, :] = diag
    ab[2, :-1] = -g_in

    t_grid = np.arange(nsteps + 1) * p.dt_h
    air_i = np.interp(t_grid, np.arange(air.size) * air_dt_h, air)
    temp = np.empty((nsteps + 1, n))
    te = np.zeros((nsteps + 1, n))
    temp[0] = t_place_c
    for k in range(nsteps):
        te_new = te[k] + hp_rate(temp[k]) * p.dt_h
        d_alpha = (alpha_hydration(te_new, p.tau_h, p.beta_h)
                   - alpha_hydration(te[k], p.tau_h, p.beta_h))
        q_cell = p.q_total * d_alpha * dz / dt          # W/m2 per cell
        rhs = c_cell / dt * temp[k] + q_cell
        rhs[0] += g_top * air_i[k + 1]
        rhs[-1] += g_bot * air_i[k + 1]
        temp[k + 1] = solve_banded((1, 1), ab, rhs)
        te[k + 1] = te_new
    z = (np.arange(n) + 0.5) * dz
    return SlabResult(t_grid, air_i, temp, z, te)
