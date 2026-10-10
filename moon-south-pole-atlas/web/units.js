/* Temperature display helper. Data files stay in kelvin; this only formats for display.
   C = K - 273.15, F = C*9/5 + 32, both rounded to whole degrees, with a true minus sign (U+2212). */
(function (root) {
  "use strict";
  const MINUS = "\u2212";
  const num = x => { const r = Math.round(x); return r === 0 ? "0" : (r < 0 ? MINUS + (-r) : String(r)); };
  const toC = k => k - 273.15;
  // Convert from the whole-kelvin value that is displayed, so the three numbers agree at a glance.
  const shown = k => Math.round(k);
  const toF = k => toC(k) * 9 / 5 + 32;
  // Plain text: "203 K · −70 °C · −94 °F"
  // A missing temperature (null / undefined / NaN / non-number) is "n/a", never Math.round(null) = 0 K.
  const has = k => typeof k === "number" && isFinite(k);
  const NA = "n/a";
  function kText(k, prefix) {
    if (!has(k)) return NA;
    return (prefix || "") + num(k) + " K \u00b7 " + num(toC(shown(k))) + " \u00b0C \u00b7 " + num(toF(shown(k))) + " \u00b0F";
  }
  // HTML: kelvin primary, Celsius/Fahrenheit in a muted .conv span.
  function kHTML(k, prefix) {
    if (!has(k)) return NA;
    return (prefix || "") + num(k) + "&nbsp;K<span class=\"conv\"> \u00b7 " + num(toC(shown(k))) + "&nbsp;\u00b0C \u00b7 " + num(toF(shown(k))) + "&nbsp;\u00b0F</span>";
  }
  const api = { has, shown, toC, toF, num, kText, kHTML };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Units = api;
})(typeof window !== "undefined" ? window : globalThis);
