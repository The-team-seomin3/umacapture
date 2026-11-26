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
| General Team | Coordinate approved priorities, integration, shared contracts, project guidance and documentation, and hosted CI policy. | Coordinate #11/#15 and separately approved #16 work. Domain teams maintain documentation and validation for their own changes. Coordination does not require General approval of every routine implementation choice. |
| Recognition Team | Capture, scene scraping/stitching, recognition, the independent Korean-factor postprocessor, factor ID/star/group correctness and native record production. | Own producer behavior such as #24 and technical acceptance of capture evidence. Preserve Japanese paths, the accepted #5 offline boundary and separately managed deliveries such as PR #26. |
| Capture Data Team (Windows, under Recognition) | Verify Windows source evidence within existing authorizations, including capture/version bindings, hashes and correspondence to original records or images. | Preserve authorized originals and prepare evidence for Recognition. Recognition owns the technical verdict. Collabo coordinates authorized transfers and intake. Route package verification to Windows Build Team. |
| App Team | Flutter UI/localization, settings/presets, statistics/filters, local storage and consumer/export behavior. | Own display and aggregation work such as #10/#21/#22/#23. Coordinate record semantics with Recognition and final Windows packaging with Windows Build Team. |
| Windows Build Team | Build and package authorized Windows desktop variants, verify package readiness, perform scoped Windows-only checks and deliver the verified package to the owner. | Record requests and results on the work issue. The owner approves local activation and retains actual-use acceptance. |
| Collabo Team | Coordinate Scout/Evaluator requests, bounded source availability checks, authorized private artifact designation/transfer, and source/version/hash/intake-state records. | Retain existing handoffs. Recognition/App or the receiving repository's responsible team validates technical meaning; successful transfer is not validation, acceptance or feature completion. |

Issue references illustrate routing, not implementation authorization or current
completion. Refresh the relevant issue, latest owner corrections, active PR and
source before acting. A dated status page or an open issue alone is insufficient.
These domains do not give one team exclusive ownership of whole directories.

The [owner decision on Windows evidence support](https://github.com/The-team-seomin3/global-agent-settings/issues/170#issuecomment-7058176097)
records Capture Data Team's placement under Recognition. The
[#74 owner decision](https://github.com/The-team-seomin3/umacapture/issues/74)
transfers Windows desktop delivery from General to the existing Windows Build Team.

## General Team manager

- Identify the primary team and affected interfaces for approved work, reconcile
  overlaps and coordinate integration without taking over another active context.
- Keep guidance and work-status references consistent when the authorized change
  affects them. Distinguish source publication/merge, actual runtime evidence,
  artifact delivery and owner acceptance; do not convert one into another.
- Apply the app-global delegation policy within existing team responsibilities,
  retaining bounded tasks, isolated editing and manager verification before
  integration. Each team remains responsible for its own validation.
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
   submitted PR. Use the issue-based procedure below for Windows build requests and source evidence.
   For other authorized development-team handoffs, verify the existing
   destination chat and repository, then transmit the bounded task under applicable
   standing/user authorization. Do not create a chat without an explicit request.
   If no destination is established, ask for that target rather than inventing one.
3. **Make the handoff self-contained.** Include owner goal, authorized scope,
   issue/PR links, verified state, relevant HEAD/base, remaining work, acceptance
   criteria and limits. Use the actual sender team in `Role`, separate from
   `Activity`, and retain the acting application identity in `Agent`.
   Write authorized agent-to-agent chat handoffs and ready-to-send fallback
   drafts in English unless the user explicitly requests otherwise, regardless
   of the user-facing conversation language. Preserve exact team/chat names, IDs,
   paths, code, schema keys and KR/JP quotations/data; keep localized runtime
   strings and user-facing discussion/status in their existing language.
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

### Windows desktop build handoff

1. The requesting team posts the exact source commit, Windows variant, expected
   deliverable and authorized checks on the relevant work issue.
2. Windows Build Team reports on that issue the revision and variant actually
   built, the package identifier and digest (or verified manifest), the readiness
   checks and their results, and any failure or unrun check. A verified and
   authorized Windows-to-Linux chat may carry the result permalink.
3. When the owner authorizes local activation, follow the
   [KR package delivery procedure](../windows-ocr-variants.md#deliver-the-windows-kr-app-to-the-owner)
   for the KR variant. The owner performs actual-use acceptance.

### Linux and Windows source-evidence handoff

1. Linux Recognition Team posts the request on the relevant umacapture work
   issue. Include the batch or artifact, the evidence needed and the expected
   outcome. Mark the Windows-dependent work as waiting and continue independent
   Linux work.
2. Windows Capture Data Team checks pending issues when the owner returns home
   and Windows is available. Verify the authorized source evidence and report
   the scope checked, findings and any missing evidence on the same issue. Use
   the established private handoff for any separately authorized data transfer.
3. Capture Data Team may send a Windows-to-Linux completion notification with
   the result permalink if the existing destination chat is verified, authorized
   and available. Linux-to-Windows chat is unavailable. The issue records the
   handoff even without a chat notification. No wake-up, polling or retry is
   required.
4. Recognition verifies the received evidence and records technical acceptance
   or any remaining work on the same issue.

## Validation and staffing

Domain teams validate their own changes, including compilation for tests, and
report Passed / Failed / Not Tested with source and run provenance. General
coordinates integration and hosted CI policy. Windows Build Team verifies the
desktop package and reports the scope exercised. Independent PR review and
owner actual-use acceptance remain separate. This structure requires no separate
standing QA or Data & Research team.
