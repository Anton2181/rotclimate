const test=require('node:test'),assert=require('node:assert/strict');
const {allocate}=require('../atlas/population.js');
test('Attractive land saturates but every supplied person remains accounted for',()=>{
  const a=allocate([2,6],[3,1],6);assert.ok(Math.abs(a.people[0]-2)<1e-9);assert.ok(Math.abs(a.people[1]-4)<1e-9);
  assert.ok(Math.abs(a.allocated+a.unallocated-6)<1e-9);
});
test('Excess census and zero population do not create unsupported residents',()=>{
  const a=allocate([2,6,10],[3,1,0],12);assert.deepEqual([...a.people],[2,6,0]);assert.equal(a.unallocated,4);
  assert.equal(allocate([2,6],[1,1],0).allocated,0);
});
test('Uniform occupation preserves area weighted capacity ratios',()=>{
  const a=allocate([2,8,10],[1,1,1],7);[.7,2.8,3.5].forEach((x,i)=>assert.ok(Math.abs(a.people[i]-x)<1e-9));
});
test('Nonfinite or negative data cannot silently corrupt the population budget',()=>{
  for(const args of [[[1],[1],NaN],[[1],[-1],2],[[Infinity],[1],2]])assert.throws(()=>allocate(...args));
});
