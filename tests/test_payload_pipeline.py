import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from cmlab import payload, tracker, weather
from cmlab import pipeline as P
from cmlab.cli import main

ROOT = Path(__file__).resolve().parents[1]


# --- payload ---------------------------------------------------------------

def test_payload_roundtrip_three_channels():
    r = payload.decode(payload.encode(1234, [18.25, -3.5, 40.01], 3100))
    assert r.seq == 1234 and r.temps_c == (18.25, -3.5, 40.01) and r.battery_mv == 3100
    assert not r.low_battery and r.battery_v == pytest.approx(3.1)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_payload_length(n):
    assert len(payload.encode(1, [20.0] * n, 3000)) == 6 + 2 * n


def test_payload_low_battery_flag():
    assert payload.decode(payload.encode(1, [20.0], 2500)).low_battery


def test_payload_sensor_fault_is_none():
    assert payload.decode(payload.encode(1, [20.0, None], 3000)).temps_c == (20.0, None)


def test_payload_sequence_wraps():
    assert payload.decode(payload.encode(65536 + 5, [1.0], 3000)).seq == 5


def test_payload_bad_crc_rejected():
    b = bytearray(payload.encode(1, [20.0], 3000))
    b[3] ^= 0x01
    with pytest.raises(payload.PayloadError):
        payload.decode(bytes(b))


@pytest.mark.parametrize("data", [b"", b"\x10\x00", bytes(12)])
def test_payload_garbage_rejected(data):
    with pytest.raises(payload.PayloadError):
        payload.decode(data)


def test_payload_encode_range_checks():
    with pytest.raises(payload.PayloadError):
        payload.encode(1, [400.0], 3000)
    with pytest.raises(payload.PayloadError):
        payload.encode(1, [], 3000)
    with pytest.raises(payload.PayloadError):
        payload.encode(1, [1.0] * 4, 3000)


def test_crc8_known_check_value():
    # CRC-8 (poly 0x07, init 0) of "123456789" is 0xF4
    assert payload.crc8(b"123456789") == 0xF4


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_decoder_matches_vectors():
    r = subprocess.run(["node", str(ROOT / "decoder" / "test.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_vectors_file_matches_python_decoder():
    vectors = json.loads((ROOT / "tests" / "vectors.json").read_text())
    assert len(vectors) >= 8
    for v in vectors:
        data = bytes.fromhex(v["hex"])
        if v.get("error"):
            with pytest.raises(payload.PayloadError):
                payload.decode(data)
        else:
            r = payload.decode(data)
            assert r.seq == v["seq"] and list(r.temps_c) == v["temps_c"]


# --- weather ---------------------------------------------------------------

def test_weather_fixture_coverage_and_ranges():
    df = weather.load_weather()
    assert set(df["site"]) == {"zurich", "davos"}
    assert len(df) == 2 * (744 + 720)
    assert df["temp_c"].between(-40, 45).all()


def test_weather_series_length_and_unknown_site():
    assert len(weather.air_series("zurich", "2024-01-08T07:00", 14)) == 14 * 24 + 1
    with pytest.raises(ValueError):
        weather.air_series("atlantis", "2024-01-08T07:00")
    with pytest.raises(ValueError):
        weather.air_series("zurich", "2024-01-30T07:00", 14)


def test_jan_colder_than_jun_at_both_sites():
    for site in ("zurich", "davos"):
        jan = weather.air_series(site, "2024-01-08T07:00", 3).mean()
        jun = weather.air_series(site, "2024-06-10T07:00", 3).mean()
        assert jan < jun - 8


# --- pipeline --------------------------------------------------------------

@pytest.fixture(scope="module")
def cal():
    return P.calibrated()


@pytest.fixture(scope="module")
def pours(cal):
    sc = P.standard_scenarios()
    out = {}
    for k in ("zurich_jan", "zurich_jun", "zurich_jan_bare", "raft_jun_bare", "raft_jun_blanket"):
        sim = P.simulate_pour(sc[k])
        out[k] = (sim, P.evaluate_pour(sim, cal))
    return out


def test_january_strip_later_than_june(pours):
    jan = pours["zurich_jan"][1].cross["strip"]["mid"]
    jun = pours["zurich_jun"][1].cross["strip"]["mid"]
    assert jan > jun + 10


def test_strip_estimate_close_to_simulated_truth(pours):
    for k in ("zurich_jan", "zurich_jun"):
        c = pours[k][1].cross["strip"]
        assert abs(c["mid"] - c["true"]) < 4.0


def test_conservative_bound_is_not_earlier_than_mid(pours):
    for ev in (pours["zurich_jan"][1], pours["zurich_jun"][1]):
        c = ev.cross["strip"]
        assert c["hi"] <= c["mid"] <= c["lo"]


def test_post_tension_after_strip(pours):
    c = pours["zurich_jun"][1].cross
    assert c["post_tension"]["mid"] > c["strip"]["mid"]


def test_bare_january_triggers_frost_alarm_protected_does_not(pours):
    assert any(a.kind == "frost_alarm" for a in pours["zurich_jan_bare"][1].alerts)
    assert not any(a.kind == "frost_alarm" for a in pours["zurich_jan"][1].alerts)


def test_raft_crack_alarm_bare_but_not_with_blanket(pours):
    assert any(a.kind == "crack_alarm" for a in pours["raft_jun_bare"][1].alerts)
    assert pours["raft_jun_blanket"][1].crack_index < 1.0


def test_hp_method_tracks_truth_in_equivalent_age(pours):
    sim = pours["zurich_jan"][0]
    te = P.equivalent_age_matrix(sim.t_h, sim.sensors_c, "hansen_pedersen")
    assert np.allclose(te, sim.te_true)


def test_unknown_method_key_raises(pours):
    sim = pours["zurich_jan"][0]
    with pytest.raises(KeyError):
        P.equivalent_age_matrix(sim.t_h, sim.sensors_c, "nope")


def test_lab_specimens_reproducible():
    a = P.lab_specimens(3)
    b = P.lab_specimens(3)
    assert np.array_equal(a[1], b[1]) and not np.array_equal(a[1], P.lab_specimens(4)[1])


# --- tracker ---------------------------------------------------------------

def test_tracker_matches_batch_equivalent_age(cal, pours):
    sim = pours["zurich_jun"][0]
    tr = tracker.MaturityTracker(cal, ea_j_mol=40_000.0)
    for t, row in zip(sim.t_h, sim.sensors_c, strict=True):
        st = tr.update(float(t), row)
    batch = P.equivalent_age_matrix(sim.t_h, sim.sensors_c, "arrhenius_40").min(axis=1)[-1]
    assert st.strength_mpa == pytest.approx(float(cal.predict(batch)), rel=1e-6)


def test_tracker_reports_strip_crossing_near_batch(cal, pours):
    sim, ev = pours["zurich_jun"]
    tr = tracker.MaturityTracker(cal, ea_j_mol=40_000.0)
    for t, row in zip(sim.t_h, sim.sensors_c, strict=True):
        tr.update(float(t), row)
    assert tr.crossings["strip"] == pytest.approx(ev.cross["strip"]["lo"], abs=0.5)


def test_tracker_frost_alarm_and_fault_handling(cal):
    tr = tracker.MaturityTracker(cal)
    tr.update(0.0, [10.0, 10.0, 10.0])
    st = tr.update(1.0, [-2.0, 8.0, None])       # bottom channel faulty -> reuse last value
    assert st.frost_alarm
    assert st.delta_t_k == pytest.approx(8.0 - (-2.0))


def test_tracker_crack_alarm(cal):
    tr = tracker.MaturityTracker(cal)
    tr.update(0.0, [20.0, 20.0, 20.0])
    assert tr.update(1.0, [20.0, 55.0, 25.0]).crack_alarm


def test_tracker_rejects_out_of_order_and_channel_change(cal):
    tr = tracker.MaturityTracker(cal)
    tr.update(1.0, [20.0, 20.0])
    with pytest.raises(ValueError):
        tr.update(1.0, [20.0, 20.0])
    with pytest.raises(ValueError):
        tr.update(2.0, [20.0])


def test_tracker_first_reading_fault_rejected(cal):
    with pytest.raises(ValueError):
        tracker.MaturityTracker(cal).update(0.0, [None, 20.0])


def test_payload_to_tracker_end_to_end(cal):
    tr = tracker.MaturityTracker(cal)
    for k in range(48):
        r = payload.decode(payload.encode(k, [20.0, 21.0, 19.0], 3000))
        st = tr.update(k * 1.0, r.temps_c)
    # ~47 h at about 19-21 C: well past the strip threshold
    assert "strip" in st.crossed


# --- CLI -------------------------------------------------------------------

def test_cli_scenarios_and_decode(capsys):
    assert main(["scenarios"]) == 0
    assert "zurich_jan" in capsys.readouterr().out
    hexs = payload.encode(9, [1.0, 2.0], 3000).hex()
    assert main(["decode", hexs]) == 0
    assert json.loads(capsys.readouterr().out)["seq"] == 9
    assert main(["decode", "zz"]) == 1


def test_cli_report_unknown_scenario():
    assert main(["report", "--scenario", "nope"]) == 2


def test_cli_report_text(capsys):
    assert main(["report", "--scenario", "zurich_jun"]) == 0
    out = capsys.readouterr().out
    assert "SIMULATED" in out and "strip" in out and "## Alerts" in out
