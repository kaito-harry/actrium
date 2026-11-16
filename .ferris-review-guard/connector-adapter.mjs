import {POLICY} from './guard.mjs';
// `inspect` is deliberately supplied by the coordinator: it must fully page
// current PR metadata, review timeline and review requests and normalize them.
// This module does not infer current requests from email or stale search results.
export function connectorAdapter(tools, inspect) {
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
