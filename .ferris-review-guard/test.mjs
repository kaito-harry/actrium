import test from 'node:test';
import assert from 'node:assert/strict';
import {submitOnce,reconcile,markerFor} from './guard.mjs';
const candidate={pr:450,head:'a'.repeat(40),requestEventId:'event-123'};
const verdict={event:'APPROVE',body:'review result',reviewedHead:candidate.head,verified:true};
function fixture() {
 const state={repository:'Actrium/actrium',pr:450,head:candidate.head,requestEventId:candidate.requestEventId,open:true,draft:false,release:false,requestedReviewers:['kaito-harry'],author:'alinejun',reviews:[]};
 const remote={tickets:new Set(),posts:0};
 const adapter=()=>({inspect:async()=>structuredClone(state), createTicket:async t=>{if(remote.tickets.has(t))return 'exists';remote.tickets.add(t);return 'created';}, submit:async x=>{remote.posts++;state.reviews.push({id:1,head:x.commit_id,author:'kaito-harry',state:'APPROVED',body:x.body});}});
 return {state,remote,adapter};
}
test('50 independent workers, one durable ticket and one post',async()=>{const f=fixture();await Promise.all(Array.from({length:50},()=>submitOnce(f.adapter(),candidate,verdict)));assert.equal(f.remote.posts,1);assert.equal(f.remote.tickets.size,1);});
test('new worker with no local state sees prior submission',async()=>{const f=fixture();await submitOnce(f.adapter(),candidate,verdict);assert.equal((await submitOnce(f.adapter(),candidate,verdict)).status,'already-reviewed');assert.equal(f.remote.posts,1);});
test('claim accepted but response lost never posts or steals',async()=>{const f=fixture(),a=f.adapter(),original=a.createTicket;a.createTicket=async t=>{await original(t);throw Error('timeout');};assert.equal((await submitOnce(a,candidate,verdict)).status,'claim-unknown');assert.equal((await submitOnce(f.adapter(),candidate,verdict)).status,'ticket-exists');assert.equal(f.remote.posts,0);});
test('submit accepted but response lost reconciles, no repost',async()=>{const f=fixture(),a=f.adapter(),original=a.submit;a.submit=async x=>{await original(x);throw Error('timeout');};assert.equal((await submitOnce(a,candidate,verdict)).status,'submitted');await submitOnce(f.adapter(),candidate,verdict);assert.equal(f.remote.posts,1);});
test('submit unknown before acceptance remains blocked across restarts',async()=>{const f=fixture(),a=f.adapter();a.submit=async()=>{throw Error('timeout');};assert.equal((await submitOnce(a,candidate,verdict)).status,'submission-unknown');assert.equal((await submitOnce(f.adapter(),candidate,verdict)).status,'ticket-exists');});
test('head change after claim prevents stale submission',async()=>{const f=fixture(),a=f.adapter(),original=a.createTicket;a.createTicket=async t=>{let r=await original(t);f.state.head='b'.repeat(40);return r;};assert.equal((await submitOnce(a,candidate,verdict)).status,'changed-after-claim');assert.equal(f.remote.posts,0);});
test('release/draft/no request excluded',async()=>{for(const patch of [{release:true},{draft:true},{requestedReviewers:[]},{author:'kaito-harry'}]){const f=fixture();Object.assign(f.state,patch);assert.equal((await submitOnce(f.adapter(),candidate,verdict)).status,'ineligible');assert.equal(f.remote.tickets.size,0);}});
test('duplicate unresolved findings never post',async()=>{const f=fixture();assert.equal((await submitOnce(f.adapter(),candidate,{...verdict,event:'REQUEST_CHANGES',duplicatesUnresolved:true})).status,'duplicate-findings');});
test('reconcile rejects another author or head marker',async()=>{const f=fixture();f.state.reviews.push({author:'other',head:candidate.head,state:'APPROVED',body:markerFor(candidate)});assert.equal((await reconcile(f.adapter(),candidate)).status,'submission-unknown');});

test('new request event invalidates old worker',async()=>{const f=fixture();f.state.requestEventId='event-456';assert.equal((await submitOnce(f.adapter(),candidate,verdict)).status,'ineligible');assert.equal(f.remote.posts,0);});
