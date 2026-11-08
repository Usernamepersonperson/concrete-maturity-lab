// Uplink decoder for the concrete maturity logger payload (see cmlab/payload.py for the layout).
// Works as a LoRaWAN network-server payload formatter (decodeUplink) and as a plain Node module.

function crc8(bytes) {
  var crc = 0;
  for (var i = 0; i < bytes.length; i++) {
    crc ^= bytes[i];
    for (var b = 0; b < 8; b++) {
      crc = (crc & 0x80) ? (((crc << 1) ^ 0x07) & 0xff) : ((crc << 1) & 0xff);
    }
  }
  return crc;
}

function decodeUplink(input) {
  var bytes = input.bytes;
  var warnings = [];
  if (!bytes || bytes.length < 8) {
    return { data: {}, warnings: warnings, errors: ["payload too short"] };
  }
  var ver = bytes[0] >> 4;
  var n = (bytes[0] >> 2) & 0x3;
  if (ver !== 1) {
    return { data: {}, warnings: warnings, errors: ["unsupported version " + ver] };
  }
  if (n < 1 || n > 3) {
    return { data: {}, warnings: warnings, errors: ["bad channel count " + n] };
  }
  if (bytes.length !== 6 + 2 * n) {
    return { data: {}, warnings: warnings, errors: ["length " + bytes.length + " does not match " + n + " channels"] };
  }
  if (crc8(bytes.slice(0, bytes.length - 1)) !== bytes[bytes.length - 1]) {
    return { data: {}, warnings: warnings, errors: ["CRC mismatch"] };
  }
  var seq = (bytes[1] << 8) | bytes[2];
  var temps = [];
  for (var i = 0; i < n; i++) {
    var raw = (bytes[3 + 2 * i] << 8) | bytes[4 + 2 * i];
    if (raw & 0x8000) { raw -= 0x10000; }
    if (raw === -32768) {
      temps.push(null);
      warnings.push("sensor " + i + " fault");
    } else {
      temps.push(raw / 100);
    }
  }
  var mv = (bytes[3 + 2 * n] << 8) | bytes[4 + 2 * n];
  var low = (bytes[0] & 1) === 1;
  if (low) { warnings.push("low battery"); }
  return {
    data: { seq: seq, temps_c: temps, battery_mv: mv, battery_v: mv / 1000, low_battery: low },
    warnings: warnings,
    errors: []
  };
}

if (typeof module !== "undefined") {
  module.exports = { decodeUplink: decodeUplink, crc8: crc8 };
}
