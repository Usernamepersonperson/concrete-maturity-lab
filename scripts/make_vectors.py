"""Regenerate tests/vectors.json (shared by the Python and JavaScript decoder tests)."""
import json
from pathlib import Path

from cmlab import payload

CASES = [
    ("three_depths", 1, [18.25, 24.5, 17.0], 3100),
    ("negative_temps", 65535, [-5.5, -3.25, -12.0], 2950),
    ("two_depths", 300, [10.0, 12.34], 3300),
    ("one_depth", 0, [0.0], 3000),
    ("low_battery", 7, [20.0, 21.0, 19.5], 2500),
    ("sensor_fault", 42, [20.0, None, 19.5], 3000),
]


def main() -> None:
    out = []
    for name, seq, temps, mv in CASES:
        data = payload.encode(seq, temps, mv)
        out.append({"name": name, "hex": data.hex(), "seq": seq, "temps_c": temps,
                    "battery_mv": mv, "low_battery": mv < payload.LOW_BATT_MV})
    good = payload.encode(5, [1.0, 2.0, 3.0], 3000)
    bad_crc = bytearray(good)
    bad_crc[-1] ^= 0xFF
    out.append({"name": "bad_crc", "hex": bytes(bad_crc).hex(), "error": True})
    out.append({"name": "truncated", "hex": good[:-3].hex(), "error": True})
    bad_ver = bytearray(good)
    bad_ver[0] = (2 << 4) | (3 << 2)
    bad_ver[-1] = payload.crc8(bytes(bad_ver[:-1]))
    out.append({"name": "bad_version", "hex": bytes(bad_ver).hex(), "error": True})
    Path("tests/vectors.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {len(out)} vectors")


if __name__ == "__main__":
    main()
