/* Shared, pure climate-comparison calculations for the atlas and its checks. */
const ClimateComparison = (() => {
  function weightedDistance(temperatureDistance, precipitationDistance, temperatureWeight = 0.5) {
    const weight = Math.max(0, Math.min(1, temperatureWeight));
    return 2 * weight * temperatureDistance + 2 * (1 - weight) * precipitationDistance;
  }

  function compare(T12, P12, r, D12, temperatureWeight = 0.5) {
    const hasD = !!(D12 && r.D);
    let dt = 0, dhi = 0, dlo = 0, dp = 0, dmm = 0;
    for (let i = 0; i < 12; i++) {
      const dm = T12[i] - r.T[i], ds = hasD ? D12[i] - r.D[i] : 0;
      dt += dm * dm + ds * ds / 4;
      dhi += (dm + ds / 2) ** 2; dlo += (dm - ds / 2) ** 2;
      dp += (Math.sqrt(Math.max(P12[i], 0)) - Math.sqrt(Math.max(r.P[i], 0))) ** 2;
      dmm += (P12[i] - r.P[i]) ** 2;
    }
    // The midpoint exactly preserves the original distance and match percentage.
    const d = weightedDistance(Math.sqrt(dt / 12) / 2.5, Math.sqrt(dp / 12) / 2, temperatureWeight);
    return { r, d, sim: 100 * Math.exp(-d / 2), dT: Math.sqrt(dt / 12), dmm: Math.sqrt(dmm / 12),
      hasD, dHi: Math.sqrt(dhi / 12), dLo: Math.sqrt(dlo / 12) };
  }

  function localRain(P12, months, solsticeDay, yearDays = 365) {
    // Reference values are totals in equal, solstice-aligned months. Integrate
    // their daily rates over each local month, including the 15 Holy Days.
    const binDays = yearDays / 12;
    let start = -solsticeDay;
    return months.map(({ days }) => {
      const end = start + days;
      let total = 0;
      for (let bin = Math.floor(start / binDays); bin * binDays < end; bin++) {
        const overlap = Math.max(0, Math.min(end, (bin + 1) * binDays) - Math.max(start, bin * binDays));
        total += P12[((bin % 12) + 12) % 12] * overlap / binDays;
      }
      start = end;
      return total;
    });
  }
  return { compare, localRain, weightedDistance };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = ClimateComparison;
