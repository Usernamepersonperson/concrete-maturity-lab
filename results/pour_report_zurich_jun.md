# Pour report: Zurich slab, 10 Jun 2024

SIMULATED pour (1-D slab heat model) driven by real air temperature (Open-Meteo archive (CC BY 4.0, reanalysis), 2024-01 and 2024-06, hourly 2 m air temperature). Not a measurement of a real structure.

## Setup
- Site: zurich; pour start (UTC): 2024-06-10T07:00; fresh concrete 20 C
- Member: 0.3 m slab; sensors at 2 cm, 15 cm, 28 cm depth; surface conductance top 12, bottom 4 W/m2K
- Maturity index: arrhenius_40; strength model: hyperbolic (lab fit RMSE 1.22 MPa, leave-one-age-out 1.68 MPa, 24 specimens)
- Governing sensor at end of window: #0 (least mature sensor sets the strength)

## Decisions
| Milestone | Strength | Best estimate | Conservative (lower 90% bound) | Optimistic |
|---|---|---|---|---|
| strip | 15 MPa | 21.1 h | 21.9 h | 20.4 h |
| post tension | 25 MPa | 42.2 h | 46.1 h | 40.0 h |

Compared with a fixed 7-day rule: strip 147 h earlier (simulated).

## Strength vs time
| Hours | Strength (MPa) | 90% band |
|---|---|---|
| 12 | 5.3 | 4.3 to 6.2 |
| 24 | 17.2 | 16.5 to 17.8 |
| 48 | 26.3 | 25.4 to 26.8 |
| 72 | 30.0 | 29.2 to 30.5 |
| 168 | 36.3 | 35.7 to 36.9 |

## Temperatures
- Peak sensor temperature 32.7 C; minimum in first 72 h 14.6 C
- Peak core-surface difference 6.2 K (index 0.31 of the 20 K guide limit)

## Alerts
- none

## Limits
- Maturity numbers are not valid once concrete freezes; an alarm replaces the estimate.
- The strength curve comes from simulated lab cylinders; calibrate your own mix before use.
- Thresholds (15 / 25 MPa) are example values; use the project specification.
