# Pour report: Zurich slab, 8 Jan 2024 (bare)

SIMULATED pour (1-D slab heat model) driven by real air temperature (Open-Meteo archive (CC BY 4.0, reanalysis), 2024-01 and 2024-06, hourly 2 m air temperature). Not a measurement of a real structure.

## Setup
- Site: zurich; pour start (UTC): 2024-01-08T07:00; fresh concrete 10 C
- Member: 0.3 m slab; sensors at 2 cm, 15 cm, 28 cm depth; surface conductance top 12, bottom 4 W/m2K
- Maturity index: arrhenius_40; strength model: hyperbolic (lab fit RMSE 1.22 MPa, leave-one-age-out 1.68 MPa, 24 specimens)
- Governing sensor at end of window: #0 (least mature sensor sets the strength)

## Decisions
| Milestone | Strength | Best estimate | Conservative (lower 90% bound) | Optimistic |
|---|---|---|---|---|
| strip | 15 MPa | 78.2 h | 82.0 h | 75.2 h |
| post tension | 25 MPa | 165.9 h | 177.0 h | 159.2 h |

Compared with a fixed 7-day rule: strip 90 h earlier (simulated).

## Strength vs time
| Hours | Strength (MPa) | 90% band |
|---|---|---|
| 12 | 0.0 | 0.0 to 0.0 |
| 24 | 1.3 | 0.0 to 2.7 |
| 48 | 8.5 | 7.8 to 9.2 |
| 72 | 13.9 | 13.2 to 14.4 |
| 168 | 25.2 | 24.3 to 25.7 |

## Temperatures
- Peak sensor temperature 10.0 C; minimum in first 72 h -1.3 C
- Peak core-surface difference 3.0 K (index 0.15 of the 20 K guide limit)

## Alerts
- [WARN] frost_protect 0.0-38.0 h: Cover / heat the pour: air <= 0 C within 24 h and strength < 5 MPa
- [WARN] frost_warn 12.8-24.2 h: Concrete within 2 K of freezing, strength < 5 MPa
- [ALARM] frost_alarm 24.5-27.8 h: Concrete at/below 0 C with strength < 5 MPa (min -0.1 C)
- [WARN] frost_warn 28.0-30.0 h: Concrete within 2 K of freezing, strength < 5 MPa
- [ALARM] frost_alarm 30.2-38.0 h: Concrete at/below 0 C with strength < 5 MPa (min -0.7 C)

## Limits
- Maturity numbers are not valid once concrete freezes; an alarm replaces the estimate.
- The strength curve comes from simulated lab cylinders; calibrate your own mix before use.
- Thresholds (15 / 25 MPa) are example values; use the project specification.
