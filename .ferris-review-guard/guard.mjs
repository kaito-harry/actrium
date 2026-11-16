// Tool-neutral, fail-closed review submission gate. No credentials or filesystem state.
// github adapter methods MUST reject on transport errors and provider isError=true.
export const POLICY = Object.freeze({ repo: 'Actrium/actrium', reviewer: 'kaito-harry', ledger: 'kaito-harry/actrium' });
export function ticketFor(candidate) {
  if (!Number.isSafeInteger(candidate.pr) || candidate.pr <= 0 || !/^[0-9a-f]{40}$/.test(candidate.head)) throw new Error('invalid PR/head');
  return `ferris-review-tickets/v1/pr-${candidate.pr}/${candidate.head}`;
}
export function workTicketFor(candidate) {
  ticketFor(candidate);
  if (typeof candidate.requestEventId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(candidate.requestEventId)) throw new Error('missing verified request event identity');
  return `ferris-review-work/v1/pr-${candidate.pr}/${candidate.head}/${candidate.requestEventId}`;
}
export function markerFor(candidate) { return `<!-- ferris-review:v1:${candidate.pr}:${candidate.head} -->`; }
function eligible(snapshot, candidate) {
  return snapshot.repository === POLICY.repo && snapshot.pr === candidate.pr && snapshot.head === candidate.head &&
    snapshot.requestEventId === candidate.requestEventId && typeof candidate.requestEventId === 'string' &&
    snapshot.open === true && snapshot.draft === false && snapshot.release === false && snapshot.pr !== 352 &&
    snapshot.requestedReviewers?.includes(POLICY.reviewer) && snapshot.author !== POLICY.reviewer;
}
// Only the caller that receives an unambiguous SUCCESS for create-only ref is
// allowed to invoke submit. Never infer ownership by finding an existing ref.
// There is deliberately NO TTL, lease takeover, ticket deletion, or blind retry.
export async function submitOnce(github, candidate, verdict) {
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
export async function reconcile(github,candidate,extra={}) {
  try {
    const current = await github.inspect(candidate.pr);
    const match = current.reviews.find(r => r.author === POLICY.reviewer && r.head === candidate.head && r.body?.includes(markerFor(candidate)) && ['APPROVED','CHANGES_REQUESTED'].includes(r.state));
    return match ? {status:'submitted',reviewId:match.id,ticket:ticketFor(candidate),...extra} : {status:'submission-unknown',ticket:ticketFor(candidate),...extra};
  } catch(error) { return {status:'submission-unknown',ticket:ticketFor(candidate),...extra,reconcileError:String(error)}; }
}
