# Factor contracts and research evidence

## Scope and contracts

The target is a selected Korean Windows Hall-of-Fame character's **complete factors**
saved locally as JSON. Manual opening/scrolling is allowed initially; automatic
navigation, full Korean UI, skills/races/campaign recognition, new GUI, broad model
retraining and cloud deployment are not assumed requirements. Follow the current
scope/authorization in [#2](https://github.com/The-team-seomin3/umacapture/issues/2),
[#3](https://github.com/The-team-seomin3/umacapture/issues/3),
[#4](https://github.com/The-team-seomin3/umacapture/issues/4) and
[#5](https://github.com/The-team-seomin3/umacapture/issues/5).

- **Capture:** prove the actual Korean window class/title and readable unmodified
  full-client pixels with the existing screenshot path first. An ANSI API observation,
  guessed title, file existence or exit 0 is not a successful real-screen capture.
  Avoid broad Unity-class matching that can select another app. Report missing/wrong
  target, acquisition/pixel failure and output failure separately.
- **Factors:** a screenshot or live `visibleSelfPrefix` is not full scroll coverage.
  Verify beginning/end, missing/duplicate rows, character switches and boundaries
  of `self`, `parent1`, `parent2`. Compare real `factor`/`factor_rank` predictions
  with independently checked Korean observations; fake predictors do not prove
  model accuracy. Do not assume every model is reusable or needs retraining.
- **JSON:** preserve `Factor.id`, 1-based `star`, and `FactorSet`'s three groups.
  The full native/Dart record requires more than factors; `JsonExportData` exports
  whole `chara_detail` records plus `labels`. A FactorSet round-trip is not proof
  of full-record/export compatibility. Identify the actual consumer and required
  fields; never invent unknown non-factor values, IDs or a new top-level schema.
  If factor-only data cannot satisfy that consumer, stop the affected decision
  and present legitimate-data/accepted-existing-boundary/contract-change options
  to the owner. Static contract inspection can proceed without Korean runtime data.
- **MVP outcome:** only report success after complete, verified ID/star/group data
  is safely written and the required consumer parses it with equivalent meaning.
  Missing target, incomplete scroll, mixed-character input or failed save must not
  replace a good result with an incomplete success.

## Shared pipeline safeguards

Read the [existing architecture](../native-recognition-backend.md) before changes.
At the inspected baseline, `SceneScrapingBox::ready` and the full recognizer still
require non-factor inputs; a factor-only completion path must be established rather
than assumed. Edit layout in [C++ builders](../../native/tool/builder), rebuild, then
regenerate tracked scene JSON from the same tree; do not hand-edit generated layout.

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
   is optional, needs authorization and must not be assumed connected. An optional
   compact index can add case/model version and evidence pointers; hash only when
   identity/integrity needs it.
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
