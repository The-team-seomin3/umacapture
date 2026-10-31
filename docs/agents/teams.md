# Team responsibilities and collaboration

The owner adopted this structure on **2026-11-01 KST** in
[issue #27](https://github.com/The-team-seomin3/umacapture/issues/27) and appointed
Codex in that guidance context as **General Team manager**. Retain the existing
**Collabo Team** and its owner-appointed collaboration manager. Recognition Team
and App Team responsibilities are defined here; this does not itself create or
staff chats, replace existing task owners, or authorize their product backlogs.

## Responsibility map

| Team | Primary responsibility | Typical boundaries and coordination |
| --- | --- | --- |
| General Team | Coordinate approved priorities, integration, shared contracts, project guidance and documentation, CI, Windows builds/packages and release readiness. | Coordinate #11/#15 and separately approved #16 work. Domain teams maintain documentation and validation for their own changes. Coordination does not require General approval of every routine implementation choice. |
| Recognition Team | Capture, scene scraping/stitching, recognition, the independent Korean-factor postprocessor, factor ID/star/group correctness and native record production. | Own producer behavior such as #24. Preserve Japanese paths and the accepted #5 offline boundary; changing team structure does not transfer separately managed deliveries such as PR #26. |
| App Team | Flutter UI/localization, settings/presets, statistics/filters, local storage and consumer/export behavior. | Own display and aggregation work such as #10/#21/#22/#23. Coordinate record semantics with Recognition and final Windows packaging with General. |
| Collabo Team | Coordinate Scout/Evaluator requests, bounded source availability checks, authorized private artifact designation/transfer, and source/version/hash/intake-state records. | Retain existing handoffs. Recognition/App or the receiving repository's responsible team validates technical meaning; successful transfer is not validation, acceptance or feature completion. |

Issue references illustrate routing, not implementation authorization or current
completion. Refresh the relevant issue, latest owner corrections, active PR and
source before acting. A dated status page or an open issue alone is insufficient.
These domains do not give one team exclusive ownership of whole directories.

## General Team manager

- Identify the primary team and affected interfaces for approved work, reconcile
  overlaps and coordinate integration without taking over another active context.
- Keep guidance and work-status references consistent when the authorized change
  affects them. Distinguish source publication/merge, actual runtime evidence,
  artifact delivery and owner acceptance; do not convert one into another.
- Delegate bounded implementation or time-consuming validation when useful, with
  an independent task/agent worktree and clear outcome. Review worker evidence
  before integration; avoid concurrent edits to the same files. Simple work may
  be handled directly. Each team remains responsible for its own validation.
- Resolve routine in-scope choices and record material decisions in the linked
  issue under applicable policy. Escalate only missing authority or decisions
  that change approved scope, contracts or accepted risk. Team membership and
  manager appointment do not grant merge, release, service or security authority.

## Shared work and handoffs

1. **One primary team per change.** Choose by intended behavior, name affected
   producer/consumer contracts and reuse existing work. For example, Recognition
   leads producer-side strategy refresh (#24); App leads missing-strategy
   aggregation (#23) and display names (#22). Agree on semantics in the relevant
   issue before dependent cross-team edits; General coordinates unresolved overlap.
2. **Use the appropriate channel.** Design-team proposals, questions, evidence and
   decisions belong in the relevant GitHub issue; independent review uses a scoped
   submitted PR. For an authorized development-team handoff, verify the existing
   destination chat and repository, then transmit the bounded task under applicable
   standing/user authorization. Do not create a chat without an explicit request.
   If no destination is established, ask for that target rather than inventing one.
3. **Make the handoff self-contained.** Include owner goal, authorized scope,
   issue/PR links, verified state, relevant HEAD/base, remaining work, acceptance
   criteria and limits. Use the actual sender team in `Role`, separate from
   `Activity`, and retain the acting application identity in `Agent`.
4. **Separate transfer from validation.** Collabo records available/not available/
   not checked, designated/delivered, acknowledged and intake-verified states as
   supported. The relevant technical team validates identity and compatibility;
   the receiving team owns its consumer implementation/acceptance. Preserve
   namespace/order/version distinctions; an available list does not certify KR IDs.
5. **Preserve authority and privacy.** Team routing grants no additional data
   access, upload/sharing, game control, product scope, automated/background dispatch
   or monitoring. Reuse the [research handoff and storage rules](contracts.md#research-handoffs).
   Preserve existing publication, review/merge, deployment and installed-settings
   protections. Keep private paths and raw game/account material out of public posts.

## Validation and staffing

Each delivering team owns proportionate checks and reports Passed / Failed /
Not Tested with source/run provenance; independent PR review remains separate.
General coordinates integrated build/package evidence without treating CI as
runtime acceptance. No separate standing QA or Data & Research team is required
by this structure. Reconsider a Platform/Release split only when sustained
build/distribution work justifies it and the owner adopts the change.
