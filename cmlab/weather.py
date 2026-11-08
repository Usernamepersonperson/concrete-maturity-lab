"""Hourly air temperature fixtures (Open-Meteo historical archive, CC BY 4.0, reanalysis based).

Source: Open-Meteo.com Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api),
2 m temperature, hourly, UTC, grid points near Zurich (47.37 N, 8.54 E, 422 m) and Davos
(46.80 N, 9.84 E, model elevation ~1546 m). Periods: 2024-01-01..31 and 2024-06-01..30.
This is gridded reanalysis, not a MeteoSwiss station record.
"""
from __future__ import annotations

from importlib import resources
from io import StringIO

import pandas as pd

SOURCE = "Open-Meteo archive (CC BY 4.0, reanalysis), 2024-01 and 2024-06, hourly 2 m air temperature"


def load_weather() -> pd.DataFrame:
    text = resources.files("cmlab").joinpath("data/weather_hourly.csv").read_text()
    df = pd.read_csv(StringIO(text), parse_dates=["time_utc"])
    return df


def air_series(site: str, start: str, days: float = 14.0, df: pd.DataFrame | None = None):
    """Hourly air temperature (deg C) from ``start`` (UTC ISO timestamp) for ``days`` days."""
    df = load_weather() if df is None else df
    d = df[df["site"] == site]
    if d.empty:
        raise ValueError(f"unknown site {site!r}; have {sorted(df['site'].unique())}")
    t0 = pd.Timestamp(start)
    n = int(round(days * 24)) + 1
    sel = d[(d["time_utc"] >= t0) & (d["time_utc"] <= t0 + pd.Timedelta(hours=n - 1))]
    if len(sel) < n:
        raise ValueError(f"weather data for {site} does not cover {n} h from {start}")
    return sel["temp_c"].to_numpy(dtype=float)
