// Run: node moon-south-pole-atlas/web/test_units.js
const assert = require("assert"), fs = require("fs"), path = require("path");
const U = require("./units.js");
assert.strictEqual(U.kText(203), "203 K \u00b7 \u221270 \u00b0C \u00b7 \u221294 \u00b0F");
assert.strictEqual(U.kText(110), "110 K \u00b7 \u2212163 \u00b0C \u00b7 \u2212262 \u00b0F");
assert.strictEqual(U.kText(273.15), "273 K \u00b7 0 \u00b0C \u00b7 32 \u00b0F");
assert.strictEqual(U.kText(300), "300 K \u00b7 27 \u00b0C \u00b7 80 \u00b0F");
assert.ok(!U.kText(273.4).includes("\u22120"));
// every kelvin value in the exported data converts and round-trips within rounding
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "data/regions.json"), "utf8"));
let n = 0;
for (const r of data.regions) {
  const k = r.query ? r.query.summer_max_temperature_k : r.summer_max_temperature_k;
  if (k == null) continue; n++;
  assert.ok(Math.abs(U.toC(k) + 273.15 - k) < 1e-9);
  assert.ok(Math.abs(U.toF(k) - (k - 273.15) * 1.8 - 32) < 1e-9);
}
// data files stay kelvin only
for (const f of ["regions.json", "regions.js", "nr101.json", "nr101.js"])
  assert.ok(!/celsius|fahrenheit|_degc|_degf|_c"|_f"/i.test(fs.readFileSync(path.join(__dirname, "data", f), "utf8")), f);
console.log("units ok (" + n + " region temperatures checked)");
