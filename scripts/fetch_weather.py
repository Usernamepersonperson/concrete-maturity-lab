"""Download hourly 2 m air temperature from the Open-Meteo archive and write cmlab/data/weather_hourly.csv.

Source: Open-Meteo Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api),
CC BY 4.0, reanalysis based (ERA5 family), NOT a MeteoSwiss station record.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SITES = {"zurich": (47.37, 8.54), "davos": (46.80, 9.84)}
PERIODS = [("2024-01-01", "2024-01-31"), ("2024-06-01", "2024-06-30")]
URL = (
    "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
    "&start_date={a}&end_date={b}&hourly=temperature_2m&timezone=UTC"
)


def main(out: Path) -> None:
    lines = ["site,time_utc,temp_c"]
    for site, (lat, lon) in SITES.items():
        for a, b in PERIODS:
            with urllib.request.urlopen(URL.format(lat=lat, lon=lon, a=a, b=b), timeout=60) as r:
                d = json.load(r)
            for t, v in zip(d["hourly"]["time"], d["hourly"]["temperature_2m"], strict=True):
                lines.append(f"{site},{t},{v}")
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines) - 1} rows)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cmlab/data/weather_hourly.csv"))
