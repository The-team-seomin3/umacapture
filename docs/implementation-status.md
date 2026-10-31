# Implementation status — 2026-10-31

Documentation cleanup: [#17](https://github.com/The-team-seomin3/umacapture/issues/17).
Source baseline: `develop` `b619240729072119e010443d3272952eec23728e`.
This is a dated navigation snapshot; read the owning issue/PR's latest updates before
continuing work. Merged source, open PRs, local builds and accepted real-use behavior
are different evidence. Results below are attributed to their owning reports, not
rerun by this documentation change.

## Current workflow

Owner-confirmed status (2026-10-31): automatic Korean factor OCR currently has low
recognition accuracy, and AI models are being used to supplement recognition. This
workflow is still being refined; factors require verification or explicit confirmation
before final export.

Current saved-input progress: **14 captures**, **1,234 factor rows**, and
**255 unresolved OCR cases**. The [store assessment](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542493060)
also reports 979 candidate-only rows; these are lookup states, not verified accuracy.
The 13 additional stored images do not by themselves prove distinct characters or
complete acquisition. Independent pixel/group/coverage acceptance remains incomplete.

1. Use the existing app's ordinary **three-tab capture**. The owner operates the
   game; agent-direct game control/capture and anti-cheat probing are excluded.
   Preserve original `factor.png`, geometry/predictions and `record.json`.
2. The separate offline Korean factor tool reads those saved inputs and pinned
   OCR, module and read-only Scout master identities. Uncertain names/symbols need
   independent pixel review or explicit confirmation; candidates alone are not verified IDs.
3. After complete review, derive **`record-kr.json` with the same full record
   structure**. Change only verified factor IDs/stars and `metadata.region="KR"`;
   preserve original `record.json`, every other value and a previous valid output
   on failure. Copied non-factor values remain unverified Korean-client facts.
4. Compare same-capture JP/KR factors by group/order/coordinates against pixels and
   master data. Independent-capture evidence and explicit owner acceptance precede
   routine KR-only consumption. The Evaluator owned-instance adapter is separate
   and remains Not Implemented in the current handoff.

The built-in recognizer remains Japanese. Korean application UI does not imply
Korean game OCR. No native factor-tab-only completion or schema redesign is needed
for this approved workflow. See [factor contracts](agents/contracts.md#scope-and-contracts).

## Delivery and evidence

| Area | Delivery at this snapshot | Evidence and limits |
| --- | --- | --- |
| Capture PoC A [#2](https://github.com/The-team-seomin3/umacapture/issues/2) | Closed, bounded research accepted | [Owner-operated upstream v0.3.0 capture](https://github.com/The-team-seomin3/umacapture/issues/2#issuecomment-6538218942) supplied readable preview and stitched output. Raw screenshot CLI, live Win32 class and JP runtime regression were not tested; no capture rewrite is justified by this case |
| Factor feasibility PoC B [#3](https://github.com/The-team-seomin3/umacapture/issues/3) | Closed, one-capture study | 95 rows (31/33/31), 95 checked stars and reference-ID mappings. [Strict OCR study](https://github.com/The-team-seomin3/umacapture/issues/3#issuecomment-6538877856): 79 exact candidates / 16 requiring review. [Master mapping](https://github.com/The-team-seomin3/umacapture/issues/3#issuecomment-6539003891) is not automatic OCR accuracy or freshness certification |
| Record compatibility PoC C [#4](https://github.com/The-team-seomin3/umacapture/issues/4) | Closed, synthetic contract investigation | [Executed handoff](https://github.com/The-team-seomin3/umacapture/issues/4#issuecomment-6540079527): 12 Dart tests, fresh native codec and isolated structure/file checks. Full-record/KR parsing works for tested inputs; GUI export wrapper and app filename behavior remain distinct from Evaluator import |
| Reviewed factor MVP [#5](https://github.com/The-team-seomin3/umacapture/issues/5) | Uncommitted local implementation; issue open | [Reviewed-output result](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6540427803): diagnostics, private review receipt, safe full-record writer and paired comparison; 32 Python / 9 Dart tests plus fresh native codec. Historical reviewed sample: 1 matched / 94 corrected against JP after all 95 pixel/reference reviews. [Later 14-capture assessment](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542493060) adds inputs/diagnostics, not new final exports or complete independent acceptance |
| Korean application UI [#10](https://github.com/The-team-seomin3/umacapture/issues/10) | [PR #12 merged](https://github.com/The-team-seomin3/umacapture/pull/12); issue open | Korean Windows startup, Japanese fallback and bundled Nanum Gothic. [60 widget previews](validation/korean-ui-preview/README.md), [initial native handoff](https://github.com/The-team-seomin3/umacapture/issues/10#issuecomment-6541112643), then [#19 integrated narrow/restart evidence](https://github.com/The-team-seomin3/umacapture/pull/19). Full native page/dialog/DPI acceptance remains incomplete |
| Windows portable package [#11](https://github.com/The-team-seomin3/umacapture/issues/11) | [PR #19 open](https://github.com/The-team-seomin3/umacapture/pull/19), includes earlier #18 source; local ZIP validated for bounded use | Fresh Release, all 119 extracted files, launch/restart provenance, selected Korean narrow/light/dark states and first-run module download verified in its report. App-PID TCP snapshots matched module-host addresses; not a TLS/packet/UDP/child-process audit. No public binary release or universal clean-machine guarantee |
| Upstream isolation [#15](https://github.com/The-team-seomin3/umacapture/issues/15) | [PR #18 merged](https://github.com/The-team-seomin3/umacapture/pull/18); source in develop | Reporting/app updates disabled, layout retained with unavailable struck-through controls, required module fetches preserved. Latest bounded review correction reports 209 tests. The standalone bundle failure is historical; #19 reports a successful integrated build/smoke using earlier #18 source, not every later HEAD |
| CI compatibility [#13](https://github.com/The-team-seomin3/umacapture/issues/13) | [PR #14 merged](https://github.com/The-team-seomin3/umacapture/pull/14); issue closed | Historical nine-job CI pass; exact action allowlist is in [operations](agents/operations.md#existing-ci-action-allowlist). It does not prove current-HEAD CI or runtime acceptance of other tasks |

The historical #3/#5 OCR partitions concern the same preserved capture and different
dated runs/reporting boundaries; neither means 95 automatic successes. New aggregate
counts and test totals do not certify corrected-factor accuracy or generalization.
Current-HEAD CI/review/merge status must be read from each PR, not inferred here.

## Remaining work and boundaries

| Remainder | Current disposition / revisit trigger |
| --- | --- |
| #5 independent-capture/operational acceptance | Tracked in #5; assess per-capture references, group/coverage and reviewed outputs for the additional saved captures. Fifty readable unresolved-string representatives do not verify all corresponding instances |
| KR-only routine consumption | Owner decision after sufficient independent evidence; paired validation remains the approved path |
| Native UI and portable acceptance | Tracked in #10/#11; full page/dialog/DPI, native accessibility/keyboard, real-record/game behavior and clean-machine coverage remain outside the demonstrated subset |
| Integration and external distribution | #18 is merged; #19 remains open. #19's bounded ZIP evidence does not certify subsequent source changes or current CI. Reassess/rebuild when final product inputs change; packaging merge/public release/distribution need their applicable authorization |
| Full Korean non-factor record accuracy | Deferred Backlog B, overlapping broad [#1](https://github.com/The-team-seomin3/umacapture/issues/1); copying values does not certify them |
| Evaluator owned-instance importer | Separate scope, Not Implemented; existing Dart/C++ parsing is not an importer |
| Scout master freshness | Separately tracked in [Scout #69](https://github.com/The-team-seomin3/uma-parent-scout/issues/69); do not reopen completed PoCs merely to update the master |
| Fork reporting/diagnostic facilities | [#16 backlog](https://github.com/The-team-seomin3/umacapture/issues/16), outside the current MVP. Optional telemetry needs its own later decision |

## Find the right manual

- [Korean UI](korean-ui-localization.md): locale/font behavior, widget evidence and
  subsequent native handoff.
- [Agent entrypoint](../AGENTS.md), [contracts](agents/contracts.md),
  [operations](agents/operations.md) and [verification](agents/testing.md):
  current task boundaries and existing tooling.
- [Native architecture](native-recognition-backend.md): the unchanged capture,
  stitch and Japanese recognition pipeline.
- #5's tool README remains in its local implementation checkout; use the issue handoff.
  The merged [network policy](fork-network-policy.md) describes reporting/update isolation.
  #19 publishes the [packaging manual](https://github.com/The-team-seomin3/umacapture/blob/39590f2778a040f3da42807775885e61caa43b14/docs/windows-portable.md)
  and [integrated validation report](https://github.com/The-team-seomin3/umacapture/blob/39590f2778a040f3da42807775885e61caa43b14/docs/validation/windows-isolation-integration-2026-10-31.md).
  These are PR-source links because the files are absent from this develop baseline.

Historical reports remain tied to their source/run. [Metadata migration #20](https://github.com/The-team-seomin3/umacapture/issues/20)
changed commit identities/SHAs while preserving file trees; the pre-isolation baseline
`d2f69e6` maps to the identical tree at `2b43220`. The current baseline also includes
merged #18. The metadata migration did not rerun runtime tests.
Public summaries exclude raw game/account material and private absolute paths.
