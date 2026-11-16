// Generated from guard.mjs + live-inspector.mjs + connector-adapter.mjs.
// Does not start workers or submit on load. Keep upstream code under review.
// Tool-neutral, fail-closed review submission gate. No credentials or filesystem state.
// github adapter methods MUST reject on transport errors and provider isError=true.
const POLICY = Object.freeze({ repo: 'Actrium/actrium', reviewer: 'kaito-harry', ledger: 'kaito-harry/actrium' });
function ticketFor(candidate) {
  if (!Number.isSafeInteger(candidate.pr) || candidate.pr <= 0 || !/^[0-9a-f]{40}$/.test(candidate.head)) throw new Error('invalid PR/head');
  return `ferris-review-tickets/v1/pr-${candidate.pr}/${candidate.head}`;
}
function workTicketFor(candidate) {
  ticketFor(candidate);
  if (typeof candidate.requestEventId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(candidate.requestEventId)) throw new Error('missing verified request event identity');
  return `ferris-review-work/v1/pr-${candidate.pr}/${candidate.head}/${candidate.requestEventId}`;
}
function markerFor(candidate) { return `<!-- ferris-review:v1:${candidate.pr}:${candidate.head} -->`; }
function eligible(snapshot, candidate) {
  return snapshot.repository === POLICY.repo && snapshot.pr === candidate.pr && snapshot.head === candidate.head &&
    snapshot.requestEventId === candidate.requestEventId && typeof candidate.requestEventId === 'string' &&
    snapshot.open === true && snapshot.draft === false && snapshot.release === false && snapshot.pr !== 352 &&
    snapshot.requestedReviewers?.includes(POLICY.reviewer) && snapshot.author !== POLICY.reviewer;
}
// Only the caller that receives an unambiguous SUCCESS for create-only ref is
// allowed to invoke submit. Never infer ownership by finding an existing ref.
// There is deliberately NO TTL, lease takeover, ticket deletion, or blind retry.
async function submitOnce(github, candidate, verdict) {
  workTicketFor(candidate);
  const ticket = ticketFor(candidate), marker = markerFor(candidate);
  if (!['APPROVE', 'REQUEST_CHANGES'].includes(verdict.event) || typeof verdict.body !== 'string') throw new Error('invalid verdict');
  if (verdict.reviewedHead !== candidate.head || verdict.verified !== true) return {status:'unverified'};
  const before = await github.inspect(candidate.pr); // includes ALL review pages and current requests
  if (!eligible(before, candidate)) return {status:'ineligible'};
  // An already handled same head is not posted twice, including genuine re-requests.
  // Re-review may be done read-only; changing the verdict needs explicit manual handling.
  if (before.reviews.some(r => r.author === POLICY.reviewer && r.head === candidate.head && ['APPROVED','CHANGES_REQUESTED'].includes(r.state))) return {status:'already-reviewed'};
  if (verdict.event === 'REQUEST_CHANGES' && verdict.duplicatesUnresolved === true) return {status:'duplicate-findings'};
  if (verdict.event === 'REQUEST_CHANGES' && verdict.duplicatesUnresolved !== false) return {status:'unverified-findings'};
  let claimed;
  try { claimed = await github.createTicket(ticket); }
  catch (error) { return {status:'claim-unknown', ticket, error:String(error)}; }
  if (claimed !== 'created') return {status:claimed === 'exists' ? 'ticket-exists' : 'claim-unknown', ticket};
  // Ticket is consumed even when revalidation fails. Safety wins over availability.
  const after = await github.inspect(candidate.pr);
  if (!eligible(after,candidate)) return {status:'changed-after-claim',ticket};
  if (after.reviews.some(r => r.author === POLICY.reviewer && r.head === candidate.head && ['APPROVED','CHANGES_REQUESTED'].includes(r.state))) return {status:'reviewed-after-claim',ticket};
  try {
    await github.submit({pr:candidate.pr, commit_id:candidate.head, event:verdict.event, body:`${verdict.body}\n\n${marker}`});
  } catch (error) {
    // Timeout may have happened AFTER GitHub accepted it. Never submit again.
    return await reconcile(github,candidate,{error:String(error)});
  }
  return await reconcile(github,candidate);
}
async function reconcile(github,candidate,extra={}) {
  try {
    const current = await github.inspect(candidate.pr);
    const match = current.reviews.find(r => r.author === POLICY.reviewer && r.head === candidate.head && r.body?.includes(markerFor(candidate)) && ['APPROVED','CHANGES_REQUESTED'].includes(r.state));
    return match ? {status:'submitted',reviewId:match.id,ticket:ticketFor(candidate),...extra} : {status:'submission-unknown',ticket:ticketFor(candidate),...extra};
  } catch(error) { return {status:'submission-unknown',ticket:ticketFor(candidate),...extra,reconcileError:String(error)}; }
}

const BASE='https://api.github.com/repos/Actrium/actrium';
function createInspector(tools) {
  async function get(path) {
    const r=await tools.mcp__codex_apps__github_fetch({url:`${BASE}/${path}`});
    if(r.isError) throw Error(r.structuredContent?.error || 'GitHub fetch failed');
    const raw=r.structuredContent?.content;
    if(typeof raw !== 'string') throw Error('missing raw JSON');
    return JSON.parse(raw);
  }
  async function all(path) {
    const rows=[],seen=new Set();
    for(let page=1;page<=100;page++) {
      const batch=await get(`${path}?per_page=100&page=${page}`);
      if(!Array.isArray(batch)) throw Error('invalid pagination response');
      const signature=JSON.stringify(batch);
      if(batch.length && seen.has(signature)) throw Error('repeated page; pagination not proven');
      seen.add(signature); rows.push(...batch);
      if(batch.length<100) return rows;
    }
    throw Error('pagination cap exceeded');
  }
  function identity(p) {
    if(p.base?.repo?.full_name!==POLICY.repo || !Number.isInteger(p.number) || !/^[0-9a-f]{40}$/.test(p.head?.sha) || typeof p.draft!=='boolean' || !['open','closed'].includes(p.state) || !p.user?.login || !Array.isArray(p.requested_reviewers) || typeof p.title!=='string' || !p.head?.ref) throw Error('incomplete PR metadata');
    return JSON.stringify([p.number,p.head.sha,p.state,p.draft,p.user.login,p.requested_reviewers.map(x=>x.login).sort(),p.title,p.head.ref]);
  }
  return async function inspect(pr) {
    if(!Number.isSafeInteger(pr)||pr<=0) throw Error('invalid PR');
    const first=await get(`pulls/${pr}`); const firstIdentity=identity(first);
    const timeline=await all(`issues/${pr}/timeline`);
    const reviews=await all(`pulls/${pr}/reviews`);
    const inlineComments=await all(`pulls/${pr}/comments`);
    const issueComments=await all(`issues/${pr}/comments`);
    const last=await get(`pulls/${pr}`);
    if(identity(last)!==firstIdentity) throw Error('PR changed during inspection');
    const requests=timeline.filter(x=>x.event==='review_requested'&&x.requested_reviewer?.login===POLICY.reviewer);
    requests.sort((a,b)=>Date.parse(a.created_at)-Date.parse(b.created_at)||Number(a.id)-Number(b.id));
    const event=requests.at(-1);
    if(event && (!event.id || !Number.isFinite(Date.parse(event.created_at)))) throw Error('invalid request event');
    const release=pr===352 || /^(release-please|dependabot)/i.test(last.user.login) || last.user.type==='Bot' || /^release(?:[-/ ]|$)/i.test(last.head.ref) || /^(?:chore(?:\([^)]*\))?:\s*)?release(?:\b|\()/i.test(last.title);
    return {repository:POLICY.repo,pr,head:last.head.sha,open:last.state==='open',draft:last.draft,author:last.user.login,requestedReviewers:last.requested_reviewers.map(x=>x.login),requestEventId:event?String(event.id):null,requestCreatedAt:event?.created_at??null,release,
      reviews:reviews.map(r=>{if(!r.id||!r.user?.login||!r.commit_id||!r.state) throw Error('incomplete review');return {id:r.id,author:r.user.login,head:r.commit_id,state:r.state.toUpperCase(),body:r.body??'',submittedAt:r.submitted_at};}),
      discussion:timeline.filter(x=>['commented','reviewed'].includes(x.event)), inlineComments, issueComments,
      provenance:{timelineCount:timeline.length,reviewCount:reviews.length,inlineCommentCount:inlineComments.length,issueCommentCount:issueComments.length,paginationComplete:true,stableMetadataRead:true}};
  };
}

// `inspect` is deliberately supplied by the coordinator: it must fully page
// current PR metadata, review timeline and review requests and normalize them.
// This module does not infer current requests from email or stale search results.
function connectorAdapter(tools, inspect) {
  return {
    inspect,
    async createTicket(branch_name) {
      const r = await tools.mcp__codex_apps__github_create_branch({repository_full_name:POLICY.ledger,branch_name,base_ref:'main'});
      const error = r.structuredContent?.error;
      if (r.isError) {
        if (r.structuredContent?.error_data?.status === '422' && r.structuredContent?.error_data?.message === 'Reference already exists') return 'exists';
        throw Error(error || 'unclassified claim failure');
      }
      if (r.structuredContent?.branch !== branch_name) throw Error('claim response not proven');
      return 'created';
    },
    async submit({pr,commit_id,event,body}) {
      const r = await tools.mcp__codex_apps__github_add_review_to_pr({repo_full_name:POLICY.repo,pr_number:pr,commit_id,action:event,review:body});
      if (r.isError) throw Error(r.structuredContent?.error || 'submission failure');
      return r;
    }
  };
}

function makeReviewerRuntime(tools) {
 const inspect=createInspector(tools);
 const github=connectorAdapter(tools,inspect);
 return {inspect,submitReviewed:(candidate,verdict)=>submitOnce(github,candidate,verdict),reconcile:(candidate)=>reconcile(github,candidate)};
}
