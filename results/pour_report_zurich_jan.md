# Pour report: Zurich slab, 8 Jan 2024 (protected)

SIMULATED pour (1-D slab heat model) driven by real air temperature (Open-Meteo archive (CC BY 4.0, reanalysis), 2024-01 and 2024-06, hourly 2 m air temperature). Not a measurement of a real structure.

## Setup
- Site: zurich; pour start (UTC): 2024-01-08T07:00; fresh concrete 10 C
- Member: 0.3 m slab; sensors at 2 cm, 15 cm, 28 cm depth; surface conductance top 1.5, bottom 2 W/m2K
- Maturity index: arrhenius_40; strength model: hyperbolic (lab fit RMSE 1.22 MPa, leave-one-age-out 1.68 MPa, 24 specimens)
- Governing sensor at end of window: #2 (least mature sensor sets the strength)

## Decisions
| Milestone | Strength | Best estimate | Conservative (lower 90% bound) | Optimistic |
|---|---|---|---|---|
| strip | 15 MPa | 39.5 h | 40.6 h | 38.5 h |
| post tension | 25 MPa | 60.9 h | 63.9 h | 59.2 h |

Compared with a fixed 7-day rule: strip 129 h earlier (simulated).

## Strength vs time
| Hours | Strength (MPa) | 90% band |
|---|---|---|
| 12 | 0.0 | 0.0 to 0.0 |
| 24 | 5.5 | 4.5 to 6.4 |
| 48 | 19.7 | 18.9 to 20.3 |
| 72 | 27.9 | 27.0 to 28.4 |
| 168 | 34.8 | 34.2 to 35.3 |

## Temperatures
- Peak sensor temperature 25.6 C; minimum in first 72 h 7.8 C
- Peak core-surface difference 1.4 K (index 0.07 of the 20 K guide limit)

## Alerts
- [WARN] frost_protect 0.0-24.5 h: Cover / heat the pour: air <= 0 C within 24 h and strength < 5 MPa

## Limits
- Maturity numbers are not valid once concrete freezes; an alarm replaces the estimate.
- The strength curve comes from simulated lab cylinders; calibrate your own mix before use.
- Thresholds (15 / 25 MPa) are example values; use the project specification.
