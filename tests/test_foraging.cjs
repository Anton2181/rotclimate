const assert=require('node:assert/strict');
const {decodePacket,indexAt,describePoint}=require('../atlas/foraging.js');

// A 2×3 grid with distinct values exposes x/y or image-ratio mixups.
const values=new Float32Array([1,2,3,4,5,6]);
const land=new Float32Array([1,1,0,1,1,1]);
const flags=new Uint8Array([1,1,0,0,1,1]);
const buffer=new ArrayBuffer(54);
new Uint8Array(buffer).set(new Uint8Array(values.buffer),0);
new Uint8Array(buffer).set(new Uint8Array(land.buffer),24);
new Uint8Array(buffer).set(flags,48);
const descriptor=(dtype,offset_bytes)=>({dtype,offset_bytes,shape:[2,3],nodata:null,scale:1,offset:0});
const metadata={shape:[2,3],arrays:{density_people_km2:descriptor('float32',0),land_fraction:descriptor('float32',24),converged:descriptor('uint8',48)}};
const packet=decodePacket(metadata,buffer);
assert.equal(packet.at('density_people_km2',indexAt(399,99,600,200,packet.shape)),2);
assert.equal(packet.at('density_people_km2',indexAt(599,199,600,200,packet.shape)),6);
assert.equal(packet.at('converged',3),0);
assert.equal(packet.at('unavailable',0),null);
assert.equal(indexAt(-100,999,600,200,packet.shape),3);
assert.throws(()=>decodePacket({...metadata,shape:[3,2]},buffer),/mismatched/);
assert.throws(()=>decodePacket(metadata,buffer.slice(0,53)),/Incomplete/);
assert.throws(()=>decodePacket({...metadata,arrays:{...metadata.arrays,land_fraction:descriptor('float32',25)}},buffer),/mismatched/);
assert.throws(()=>indexAt(NaN,1,600,200,packet.shape),/coordinates/);
// A terminal floor hit must not erase a positive multiyear mean.
const cyclic=describePoint({density_people_km2:1.5,foraging_hours_day:4.25,meat_fraction:.3,
  scarcity_days_year:12,averaging_years_used:50,density_cv:1.2,converged:0,floor_limited:1,unsupported:0});
assert.equal(cyclic.rows[0][0],'1.5 /km²');
assert.match(cyclic.rows[0][1],/50-year mean/);
assert.match(cyclic.status,/not an annual equilibrium/);
assert.match(cyclic.status,/floor re-inoculation/);
assert(cyclic.rows.some(row=>row[0]==='120%'&&row[1].includes('variation')));
assert.equal(describePoint({unsupported:1,converged:0,density_people_km2:0}).rows.length,0);
assert.match(describePoint({unsupported:1}).message,/whole|window/);
console.log('Foraging packet, coordinate, finite-window and unsupported-state checks passed.');
