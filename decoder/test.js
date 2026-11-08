// Run: node decoder/test.js   (checks the JS decoder against the Python-generated vectors)
const fs = require("fs");
const path = require("path");
const { decodeUplink } = require("./decoder.js");

const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "tests", "vectors.json"), "utf8"));
let failed = 0;
for (const v of vectors) {
  const bytes = Buffer.from(v.hex, "hex");
  const res = decodeUplink({ bytes: Array.from(bytes), fPort: 1 });
  let ok;
  if (v.error) {
    ok = res.errors.length > 0;
  } else {
    ok = res.errors.length === 0 &&
      res.data.seq === v.seq &&
      res.data.battery_mv === v.battery_mv &&
      res.data.low_battery === v.low_battery &&
      JSON.stringify(res.data.temps_c) === JSON.stringify(v.temps_c);
  }
  if (!ok) {
    failed++;
    console.error("FAIL", v.name, JSON.stringify(res));
  }
}
console.log(`${vectors.length - failed}/${vectors.length} vectors passed`);
process.exit(failed ? 1 : 0);
