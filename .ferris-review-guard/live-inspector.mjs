import {POLICY} from './guard.mjs';
const BASE='https://api.github.com/repos/Actrium/actrium';
export function createInspector(tools) {
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
    const last=await get(`pulls/${pr}`);
    if(identity(last)!==firstIdentity) throw Error('PR changed during inspection');
    const requests=timeline.filter(x=>x.event==='review_requested'&&x.requested_reviewer?.login===POLICY.reviewer);
    requests.sort((a,b)=>Date.parse(a.created_at)-Date.parse(b.created_at)||Number(a.id)-Number(b.id));
    const event=requests.at(-1);
    if(event && (!event.id || !Number.isFinite(Date.parse(event.created_at)))) throw Error('invalid request event');
    const release=pr===352 || /^(release-please|dependabot)/i.test(last.user.login) || last.user.type==='Bot' || /^release(?:[-/ ]|$)/i.test(last.head.ref) || /^(?:chore(?:\([^)]*\))?:\s*)?release(?:\b|\()/i.test(last.title);
    return {repository:POLICY.repo,pr,head:last.head.sha,open:last.state==='open',draft:last.draft,author:last.user.login,requestedReviewers:last.requested_reviewers.map(x=>x.login),requestEventId:event?String(event.id):null,requestCreatedAt:event?.created_at??null,release,
      reviews:reviews.map(r=>{if(!r.id||!r.user?.login||!r.commit_id||!r.state) throw Error('incomplete review');return {id:r.id,author:r.user.login,head:r.commit_id,state:r.state.toUpperCase(),body:r.body??'',submittedAt:r.submitted_at};}),
      discussion:timeline.filter(x=>['commented','reviewed'].includes(x.event)),
      provenance:{timelineCount:timeline.length,reviewCount:reviews.length,paginationComplete:true,stableMetadataRead:true}};
  };
}
