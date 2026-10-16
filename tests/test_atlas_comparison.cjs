const test = require('node:test');
const assert = require('node:assert/strict');
const { compare, localRain } = require('../atlas/climate-comparison.js');
const fill = (v) => Array(12).fill(v);
const months = [...Array.from({length: 10}, () => ({days: 35})), {days: 15}];

test('balanced weighting retains the original score and day/night differences', () => {
  const ref = {T: fill(22), P: fill(144), D: fill(12)};
  const actual = compare(fill(20), fill(100), ref, fill(8));
  const expectedDistance = Math.sqrt(8) / 2.5 + 1;
  assert.ok(Math.abs(actual.d - expectedDistance) < 1e-12);
  assert.ok(Math.abs(actual.sim - 100 * Math.exp(-expectedDistance / 2)) < 1e-12);
  assert.equal(compare(ref.T, ref.P, ref, ref.D).sim, 100);
});

test('slider endpoints reverse ranking according to the preferred climate feature', () => {
  const temperatureMatch = {T: fill(20), P: fill(10)};
  const rainfallMatch = {T: fill(30), P: fill(100)};
  const distance = (ref, weight) => compare(fill(20), fill(100), ref, null, weight).d;
  assert.ok(distance(temperatureMatch, 1) < distance(rainfallMatch, 1));
  assert.ok(distance(rainfallMatch, 0) < distance(temperatureMatch, 0));
});

test('local precipitation preserves annual total across a shifted year boundary', () => {
  const rainfall = [15, 23, 47, 110, 214, 301, 218, 119, 55, 40, 25, 20];
  for (const solstice of [0, 22, 204.5, 364.9]) {
    const result = localRain(rainfall, months, solstice);
    assert.equal(result.length, 11);
    assert.ok(result.every(v => v >= 0 && Number.isFinite(v)));
    assert.ok(Math.abs(result.reduce((a,b) => a+b, 0) - rainfall.reduce((a,b) => a+b, 0)) < 1e-9);
  }
});

test('Holy Days receive 15 days of rain rather than a full reference month', () => {
  const result = localRain(fill(365 / 12 * 2), months, 22);
  result.slice(0, 10).forEach(v => assert.ok(Math.abs(v - 70) < 1e-9));
  assert.ok(Math.abs(result[10] - 30) < 1e-9);
});

test('cached map distances and city comparisons use identical weights', () => {
  const { weightedDistance } = require('../atlas/climate-comparison.js');
  const ref = {T: Array.from({length: 12}, (_, i) => i + 10),
               P: Array.from({length: 12}, (_, i) => i * 8), D: fill(12)};
  const T = fill(20), P = fill(60), D = fill(8);
  const temperatureOnly = compare(T, P, ref, D, 1).d / 2;
  const rainOnly = compare(T, P, ref, D, 0).d / 2;
  for (const weight of [0, 0.25, 0.5, 0.75, 1]) {
    assert.ok(Math.abs(weightedDistance(temperatureOnly, rainOnly, weight)
      - compare(T, P, ref, D, weight).d) < 1e-12);
  }
});
