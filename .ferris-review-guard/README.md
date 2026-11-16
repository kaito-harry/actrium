# Review submission guard: validated prototype, NOT enabled

## Deployment boundary
The scheduled task is still read-only. No automatic review was started, no GitHub review/comment submitted, no automation changed by this implementation.

The implementation consists of a tool-neutral submission gate and a connector adapter. The coordinator still needs to supply the normalized live `inspect` function; it must fetch the actual current requested reviewer, current head, author, open/draft state, latest review_requested timeline event ID, full paginated review history, and release classification. It must not treat absence of fields as negative evidence. Unknown classification or incomplete pagination means blocked, not eligible. Missing event ID means blocked. Existing unresolved findings must be compared semantically with the proposed REQUEST_CHANGES after reading author replies.

## Durable state and concurrency
State is GitHub refs in the user's fork `kaito-harry/actrium`, not local SQLite, shared notes or Library. A dedicated permanent ref `ferris-review-tickets/v1/pr-N/HEAD` is a consumed submission ticket. Only an explicit successful create-only ref response permits that caller to send. Existing ref, timeout, ambiguous response or auth failure never grants ownership. GitHub rejected a second concurrent create with 422 Reference already exists in the real probe. No ref updates are used for locking.

Use a separate work ref `ferris-review-work/v1/pr-N/HEAD/REQUEST_EVENT_ID` for compute deduplication if desired. It distinguishes same-head re-requests. The permanent per-head submission ticket is intentionally stronger: same-head re-requests may receive read-only analysis but cannot automatically post a second verdict. They need manual coordination. Do not delete or expire tickets, because the old worker may still submit later. Do not mint an event-specific submission ticket to bypass this restriction.

## Operational flow
1. Search review-requested:kaito-harry, exclude releases (#352 and other automated release PRs).
2. Fetch and normalize live metadata, timeline and reviews. Fully read author replies; inspect unresolved threads. Re-request identity is a verified timeline event ID, not PR updated_at.
3. Start a read-only review worker using collaboration.spawn_agent(model='gpt-6-astra', reasoning_effort='high', fork_turns='none') with a complete brief, exact head, author replies, static review and feasible dynamic tests, no CI wait and NO submission authority. Root owns posting. A user-selected model override requires fork_turns none.
4. Worker returns verdict and evidence tied to the exact SHA. Reject unverifiable/incomplete results. Never equate CI green with review complete.
5. Coordinator uses submitOnce. It checks current request/head, existing same-head reviews and duplicate unresolved findings, atomically consumes the permanent ticket, checks again, sends once with explicit commit_id and marker, then reconciles against GitHub reviews.
6. Reconciliation reads are retryable. Submission is NOT retryable. Unknown submission leaves ticket forever consumed and notifies root/user for manual investigation. Other PR/head jobs can continue independently.
7. Root may update the existing automation only after it can supply a fully validated inspector and has communicated the conservative same-head/uncertain-outcome behavior. No separate overlapping submitter, Gmail flow or manual worker may bypass this gate. Existing historical reviews must be honored even when no ticket exists.

## Failure handling and exact guarantees
* Claim accepted but response lost: closed; never infer ownership from existing ref.
* Worker dies after claim: new worker sees existing ref and does not submit. Availability sacrificed for no duplicates.
* Review accepted but response lost: marker+author+head reconciliation recovers the submitted review ID.
* Unknown timeout with no visible review: remains unknown. Lack of a visible review is NOT proof no delayed send can arrive.
* Head/request changes before final validation: consume ticket but do not post. New head can be reviewed independently.
* Head/request changes between last check and GitHub submission cannot be made transactional with available APIs. Explicit commit_id anchors the review to reviewed code; it does not guarantee the PR head is unchanged at acceptance time. Reconcile/report any such race, do not claim a distributed exactly-once transaction.
* User or other apps posting outside this protocol are not fenced. Only compliant workers share this guarantee.
* Local processes, credential/session persistence and macOS/cloud reset were not used for durability. CLI is unauthenticated in the currently selected cloud environment.

## Verification evidence
2026-11-16: real GitHub connector concurrent create on `ferris-review-probe/claim-20261116-atomic-01`: contender 0 succeeded, contender 1 returned 422 Reference already exists. Root independently read the branch via its connector. A probe record is remotely persisted at `.ferris-review-probe.json` on that branch. A second ref `ferris-review-probe/crash-after-claim-20261116` represents crash-after-claim and must not be taken over.

Run `node --test test.mjs`: 10 passed, including 50 independent simulated workers, restart with no local state, lost claim response, accepted/lost submission response, unaccepted/unknown submission, head change, re-request change, release/draft/self/request exclusion, duplicate findings and marker spoofing. These submission failure tests are simulations; no live GitHub review was sent to test them. No claim of real server-side timeout injection or physical cloud-replacement experiment is made.

## Remaining acceptance gates
The adapter and gate are NOT by themselves a deployed automated reviewer. Full live inspector integration, verification of timeline/review pagination, production trigger integration, and explicit handling/reporting of same-head re-request/manual recovery remain. Do not enable unattended posting merely because the unit tests pass.


## Follow-up verification 2026-11-16
`live-inspector.mjs` now implements paginated raw GitHub REST reads via github.fetch: PR metadata twice, issue timeline, reviews, issue comments, and inline comments. It checks metadata stability and rejects malformed/incomplete responses, repeated pages, excessive pages, or provider errors. It ran against PR #450: head 59a07ef79edb72d74d088842336e6fdc27f279b9, request event 36231522413, 10 timeline entries, 4 reviews, 2 inline comments including the author reply, 0 issue comments. Current requested_reviewers was empty after another executor posted approval 5914539449 at 02:58:44Z with marker actrium-review-v3. A read-only end-to-end gate check returned ineligible with ZERO claim/submit calls.

The earlier missing-inspector gate is now resolved for this provider shape; 14 tests pass including pagination, repeated-page rejection, rate-limit failure and metadata races. Full unattended deployment remains BLOCKED because an uncoordinated external submission source is unidentified. Local macOS current process/launchd/native-automation/task inspection did not identify it; that negative search does not exclude prior processes or another server. Do not enable a second submitter until that source is accounted for. The cloud Dot automation was independently confirmed by root as read-only and Gmail review disabled.
