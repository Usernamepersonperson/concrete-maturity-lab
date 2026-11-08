# Pour report: Zurich raft 1.2 m, 10 Jun 2024 (bare)

SIMULATED pour (1-D slab heat model) driven by real air temperature (Open-Meteo archive (CC BY 4.0, reanalysis), 2024-01 and 2024-06, hourly 2 m air temperature). Not a measurement of a real structure.

## Setup
- Site: zurich; pour start (UTC): 2024-06-10T07:00; fresh concrete 20 C
- Member: 1.2 m slab; sensors at 2 cm, 60 cm, 118 cm depth; surface conductance top 12, bottom 1 W/m2K
- Maturity index: arrhenius_40; strength model: hyperbolic (lab fit RMSE 1.22 MPa, leave-one-age-out 1.68 MPa, 24 specimens)
- Governing sensor at end of window: #0 (least mature sensor sets the strength)

## Decisions
| Milestone | Strength | Best estimate | Conservative (lower 90% bound) | Optimistic |
|---|---|---|---|---|
| strip | 15 MPa | 20.4 h | 21.1 h | 19.8 h |
| post tension | 25 MPa | 35.2 h | 37.3 h | 34.0 h |

Compared with a fixed 7-day rule: strip 148 h earlier (simulated).

## Strength vs time
| Hours | Strength (MPa) | 90% band |
|---|---|---|
| 12 | 5.4 | 4.4 to 6.3 |
| 24 | 18.1 | 17.4 to 18.7 |
| 48 | 29.2 | 28.4 to 29.8 |
| 72 | 33.5 | 32.8 to 34.0 |
| 168 | 38.9 | 38.2 to 39.4 |

## Temperatures
- Peak sensor temperature 58.0 C; minimum in first 72 h 18.5 C
- Peak core-surface difference 29.6 K (index 1.48 of the 20 K guide limit)

## Alerts
- [WARN] crack_warn 18.8-22.0 h: Core-surface difference 19.9 K >= 15 K
- [ALARM] crack_alarm 22.2-103.5 h: Core-surface difference 29.6 K >= 20 K
- [WARN] crack_warn 103.8-111.2 h: Core-surface difference 20.0 K >= 15 K
- [ALARM] crack_alarm 111.5-116.2 h: Core-surface difference 20.3 K >= 20 K
- [WARN] crack_warn 116.5-149.2 h: Core-surface difference 20.0 K >= 15 K
- [WARN] crack_warn 165.0-165.0 h: Core-surface difference 15.0 K >= 15 K

## Limits
- Maturity numbers are not valid once concrete freezes; an alarm replaces the estimate.
- The strength curve comes from simulated lab cylinders; calibrate your own mix before use.
- Thresholds (15 / 25 MPa) are example values; use the project specification.
