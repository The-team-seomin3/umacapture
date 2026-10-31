# Factor contracts and research evidence

## Scope and contracts

The approved [MVP #5](https://github.com/The-team-seomin3/umacapture/issues/5) reads
a completed Korean Windows Hall-of-Fame capture through an **independent offline
postprocessor**. Ordinary three-tab capture, Japanese recognition and the original
writer remain unchanged. Full Korean non-factor recognition is deferred; application
UI localization and Windows packaging have separate scopes. See the dated
[implementation status](../implementation-status.md) and current issue comments.

- **Capture intake:** [PoC A #2](https://github.com/The-team-seomin3/umacapture/issues/2)
  accepted the owner's existing-release GUI capture and saved stitched image for the
  supplied case. Live window class, fresh screenshot CLI and Japanese runtime
  regression remain Not Tested; they are not prerequisites to reuse this evidence.
  Do not require another capture to re-prove this accepted case or probe/control
  the game under the current owner boundary. Reopen capture investigation only
  for a material observed failure or new owner request.
- **Factors:** preserve group, screen order and geometry for `self`, `parent1`,
  `parent2`; check beginning/end, missing/duplicated acquisition and mixed captures.
  Compare names/stars with source pixels and the pinned read-only Scout KR master.
  `Factor.id` is the app module SID (**0 is valid**), not Scout's factor-group or
  star-specific factor ID; require an evidenced namespace mapping and stars **1–3**.
  Neither parser success, JP/KR agreement nor reference-ID mapping proves OCR
  accuracy. Ambiguous symbols/names stay unresolved without independent verification
  or explicit confirmation; no unverified automatic correction.
- **Derived record:** preserve original `record.json`. Copy its complete
  `CharaDetailRecord` structure into a separate `record-kr.json`, changing only
  verified factor IDs/stars and the owner-adopted `metadata.region = "KR"`.
  All other values, including `format_version` and `recognizer_version`, stay
  unchanged and are **not certified Korean-client facts**. Do not fabricate missing
  fields or invoke legacy `upgradeFormat` while copying; it changes non-factor
  values. Keep JP/module, OCR/master and review provenance in private diagnostics,
  without adding JSON fields. This accepted workflow uses a complete source record;
  the earlier incompatibility finding still applies to factor-only input. It adds
  no new schema.
- **Output and comparison:** emit only after all captured factors are verified or
  confirmed. Validate schema/allowed differences, semantic SID/star/group values,
  readback and source non-mutation; failed/incomplete runs preserve prior valid
  output. Pair JP/KR rows by group/order/coordinates, not predicted SID, and report
  matched/corrected/unresolved/error against pixels/master. Repeating one sample
  is not independent-capture evidence; KR-only routine use needs later owner acceptance.
- **Consumer boundary:** the original app reads literal `record.json`; it does not
  automatically discover `record-kr.json`. Its GUI `JsonExportData` wrapper uses
  `chara_detail` plus `labels`, distinct from a record file. The owned-instance
  Evaluator adapter remains separately scoped and Not Implemented in the linked
  handoff. Existing-reader tests do not establish end-to-end Evaluator import.

## Shared pipeline safeguards

Read the [existing architecture](../native-recognition-backend.md) before changes.
The existing full pipeline consumes non-factor inputs; factor-tab-only completion
is outside the approved MVP. Native layout/model edits are not needed for the
current postprocessor path. If separately authorized shared changes become necessary,
edit layout in [C++ builders](../../native/tool/builder), rebuild, then regenerate
tracked scene JSON from the same tree; do not hand-edit generated layout.

Preserve Japanese DMM/Steam behavior. For shared-core changes also preserve existing
web/CLI contracts, without requiring Korean web/mobile support. Live Windows/web
producers may shape/crop; offline VideoLoader, FFV1 replay and web import send full
frames with no pane snapshot so consumer-side calibration is deterministic. A cropped
Frame needs its matching anchor, and `updateFrame` receives the pre-crop captured
size. FFV1 recording tees before shaping. Keep platform differences deliberate and
explain the concrete constraint at the divergence; CLI preview is absent by design.
Use [targeted verification](testing.md#native-verification) for the actual affected path.

## Research handoffs

This repository-local procedure carries #2-#4 PoC results into #5; it adds no global
policy, required researcher, storage infrastructure or implementation authorization.

1. **Publish once:** put material findings in the relevant issue's consolidated result
   comment: question, tested revision, input/method scope, concise expected/observed
   result, `Verified / Failed / Not Tested`, assumptions, accessible evidence, limits
   and remaining decisions. PRs deliver authorized tracked changes, not research-only
   reports; do not duplicate the full investigation in repository docs.
2. **Preserve private evidence:** keep screenshots/clips, predictions, logs and fixtures
   in authorized durable storage under the existing `testdata/` non-destructive rule.
   `.notes/` alone is temporary; an inaccessible local path is not independent evidence.
   Do not publish account identifiers or private filesystem paths. Cloud/Drive sharing
   is optional, needs authorization and must not be assumed connected. Reusable
   substantive results need the [local index below](#local-storage-and-worktree-handoff);
   transient observations do not. Hash only when identity/integrity needs it.
3. **Verify what matters:** refresh issues/comments, code, owner decisions and overlap.
   Any agent's report is a claim, not a proven fact or binding decision. Check source,
   revision/freshness, methodology and input scope; reproduce critical capture (#2),
   factor/group/model behavior (#3) or real consumer parsing (#4) when feasible.
   Reuse reliable inventories/measurements rather than rerunning everything. Separate
   source-supported facts, observed execution, inference, unknowns and proposed design;
   absent models/clips/environment mean Not Tested, never Passed.
4. **Keep authority clear:** publication/status/labels/suggestions grant no new scope.
   Continue authorized work without unnecessary reapproval; hold only decisions affected
   by unapproved scope or inaccessible/contradictory evidence and escalate concrete
   options. Briefly link findings used, actual verification and consequential adopted,
   partially adopted, deferred, already resolved or insufficient-evidence dispositions.
5. **Delegate only when useful:** compare research + coordination/handoff + verification
   + expected rework with direct investigation or a deterministic script. Use measured
   cost when available, otherwise qualitative judgment, never invented savings.
   Antigravity can supply reusable observations/reference data, otherwise inaccessible
   inputs or substantive repeatable comparison. Prefer direct work for trivial lookups,
   small schema lists, tightly coupled design or research needing full repetition.
   A comment does not start/wake an idle agent, and a researcher is not a mandatory gate.

## Local storage and worktree handoff

For reusable substantive research, use `~/.agents/research/umacapture/issue-<N>/`;
`~` is the current user's home. Keep its resolved location outside every worktree,
not a link into one. It is private local data, not committed repo content or a new
service. A same-user agent derives this location from the issue number; another
account/machine needs a separately authorized accessible handoff, not a guessed pass.

- **Layout:** `INDEX.md` lists completed runs; each new run gets a unique
  `YYYYMMDDTHHMMSSZ-<agent>-<suffix>/` with `SUMMARY.md` and any needed `evidence/`.
  Never overwrite an existing run. Serialize same-index updates, reread before
  writing, preserve other entries, and record corrections as a new run.
- **Minimum index row:** run ID, tested commit, input/model scope (or Unknown),
  `Verified / Failed / Not Tested`, relative SUMMARY link and issue-result permalink
  (Pending until published). A compact form is:

  ```text
  | Run | Commit; inputs/models | Status | Summary | Issue result |
  | <run-id> | <sha>; <scope or Unknown> | <status> | [summary](<run-id>/SUMMARY.md) | <permalink or Pending> |
  ```

- **Summary:** record the question, environment/commands, expected vs observed result,
  limits/remaining decisions and needed evidence as paths relative to the run.
  Missing evidence is Not Tested or insufficient evidence, never silently Verified.
  A receiver reads the index/summary first and opens only implementation-critical,
  authorized inputs, checking source freshness as above. An unreadable index is an
  unavailable handoff, not a reason to scan private trees. Public issue comments use
  the logical issue/run ID plus a sanitized result, never expanded private paths or
  raw account data; add the published permalink to the local index afterward.
- **Before authorized worktree cleanup:** identify this task's reusable results and
  dependencies still inside it (including ignored scratch, captures and build output).
  Copy needed files into a new durable run, not a symlink/reference back to the tree;
  preserve originals. Compare copied files' hashes, then open the index, summary and
  required evidence from the receiving location and confirm no required link resolves
  into the tree being removed. Complete the local handoff before cleanup; if issue
  publication is unavailable, record Pending and the next action in the index. If copy,
  access or verification fails, stop cleanup that would lose that result and report
  the missing item/next action; unrelated authorized work can continue. This rule
  grants no cleanup permission and does not waive `testdata/` non-deletion rules.
