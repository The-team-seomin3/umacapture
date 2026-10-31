# Implementation status — 2026-10-31

Documentation cleanup: [#17](https://github.com/The-team-seomin3/umacapture/issues/17).
Source baseline: `develop` `b619240729072119e010443d3272952eec23728e`.
This is a dated navigation snapshot; read the owning issue/PR's latest updates before
continuing work. Merged source, open PRs, local builds and accepted real-use behavior
are different evidence. Results below are attributed to their owning reports, not
rerun by this documentation change.

## Current workflow

**#5 source-delivery correction (2026-10-31):** the previously local reviewed-output
implementation is included in this change at [tool/kr_factor_ocr](../tool/kr_factor_ocr/README.md).
Commit/PR publication was requested after the saved-corpus delivery. Merge, release
and routine KR-only acceptance remain separate. Other areas below retain their dated evidence.

Owner-confirmed status (2026-10-31): automatic Korean factor OCR currently has low
recognition accuracy, and AI models are being used to supplement recognition. This
workflow is still being refined; factors require verification or explicit confirmation
before final export.

The [automatic OCR assessment](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542493060)
covered **14 captures** and **1,234 factor rows**, with **255 unresolved OCR cases**
and 979 candidate-only rows. These are diagnostic lookup states, not verified accuracy
or the current owner-confirmation queue.

The [subsequent source-pixel verification](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542693845)
checked every name/star and pinned master-to-module mapping for all **1,139 rows in
the additional 13 captures**, including their 238 unresolved diagnostic rows. All
**39 source-visible groups** and visible beginning/end contexts agree; no visible
missing/duplicate/unassigned card remained, and the owner-only confirmation queue is
**0**. Together with the prior reviewed 95-row baseline, source-visible references
are complete for this saved corpus. This is agent pixel/master verification, not a
blinded benchmark, distinct-character proof or reconstruction of live acquisition.

A [later, separate output delivery](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542817561)
then bound fresh reviews to the exact input/diagnostic/master context and exported
13 new full records plus the existing baseline: **14 record-kr.json files / 1,234
reviewed rows** delivered privately. All actual pairs passed the reported 14 Dart
tests and a freshly compiled native production-codec probe. Combined JP comparison:
**14 matched / 1,220 corrected / 0 unresolved / 0 error**. These are reviewed outputs,
not automatic OCR results. Research reference tables alone are not export-ready
receipts; the pixel-review task itself emitted no new records or reader checks.
Original active-store data and copied non-factor values were preserved; Korean
non-factor accuracy and routine KR-only acceptance remain separate.

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
| Reviewed factor MVP [#5](https://github.com/The-team-seomin3/umacapture/issues/5) | Reviewed offline implementation included in this source change; saved-corpus verification and outputs delivered; issue open | [Baseline implementation](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6540427803), [all 1,139 additional source-visible rows/groups verified](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542693845), then [14 full KR records / 1,234 reviewed rows exported and reader-checked](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542817561). Latest delivery: 14 actual-artifact Dart tests and a fresh native codec probe; 14 matched / 1,220 corrected against JP. Live/generalization/KR-only acceptance remains separate |
| Korean application UI [#10](https://github.com/The-team-seomin3/umacapture/issues/10) | [PR #12 merged](https://github.com/The-team-seomin3/umacapture/pull/12); issue open | Korean Windows startup, Japanese fallback and bundled Nanum Gothic. [60 widget previews](validation/korean-ui-preview/README.md), [initial native handoff](https://github.com/The-team-seomin3/umacapture/issues/10#issuecomment-6541112643), then [#19 integrated narrow/restart evidence](https://github.com/The-team-seomin3/umacapture/pull/19). Full native page/dialog/DPI acceptance remains incomplete |
| Windows portable package [#11](https://github.com/The-team-seomin3/umacapture/issues/11) | [PR #19 open](https://github.com/The-team-seomin3/umacapture/pull/19), includes earlier #18 source; local ZIP validated for bounded use | Fresh Release, all 119 extracted files, launch/restart provenance, selected Korean narrow/light/dark states and first-run module download verified in its report. App-PID TCP snapshots matched module-host addresses; not a TLS/packet/UDP/child-process audit. No public binary release or universal clean-machine guarantee |
| Upstream isolation [#15](https://github.com/The-team-seomin3/umacapture/issues/15) | [PR #18 merged](https://github.com/The-team-seomin3/umacapture/pull/18); source in develop | Reporting/app updates disabled, layout retained with unavailable struck-through controls, required module fetches preserved. Latest bounded review correction reports 209 tests. The standalone bundle failure is historical; #19 reports a successful integrated build/smoke using earlier #18 source, not every later HEAD |
| CI compatibility [#13](https://github.com/The-team-seomin3/umacapture/issues/13) | [PR #14 merged](https://github.com/The-team-seomin3/umacapture/pull/14); issue closed | Historical nine-job CI pass; exact action allowlist is in [operations](agents/operations.md#existing-ci-action-allowlist). It does not prove current-HEAD CI or runtime acceptance of other tasks |

The early #3/#5 OCR partitions concern the same preserved baseline capture and
different dated runs/reporting boundaries; neither means 95 automatic successes.
The later full-corpus review and output delivery are separate milestones linked
above. Reviewed corrections do not change the earlier 255 automatic OCR uncertainties
or establish unseen-input generalization. Current-HEAD CI/review/merge status must be
read from each PR, not inferred here.

## Remaining work and boundaries

| Remainder | Current disposition / revisit trigger |
| --- | --- |
| #5 remaining operational acceptance | Source-visible per-instance references/groups and all 14 saved-corpus exports/reader checks are complete in the linked reports; reuse them. Live acquisition completeness, full live-app/JP runtime regression, current-patch master freshness and unseen-input/distinct-character generalization remain unproven or separately scoped |
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
- [Korean offline factor tool](../tool/kr_factor_ocr/README.md): local inputs, candidate diagnostics,
  explicit review, source-preserving full-record export and safe failure. The
  [evidence-preservation handoff](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542958301)
  retains all 1,234 original pixel/label pairs privately; no account data is bundled.
  The merged [network policy](fork-network-policy.md) describes reporting/update isolation.
  #19 publishes the [packaging manual](https://github.com/The-team-seomin3/umacapture/blob/39590f2778a040f3da42807775885e61caa43b14/docs/windows-portable.md)
  and [integrated validation report](https://github.com/The-team-seomin3/umacapture/blob/39590f2778a040f3da42807775885e61caa43b14/docs/validation/windows-isolation-integration-2026-10-31.md).
  These are PR-source links because the files are absent from this develop baseline.

Historical reports remain tied to their source/run. [Metadata migration #20](https://github.com/The-team-seomin3/umacapture/issues/20)
changed commit identities/SHAs while preserving file trees; the pre-isolation baseline
`d2f69e6` maps to the identical tree at `2b43220`. The current baseline also includes
merged #18. The metadata migration did not rerun runtime tests.
Public summaries exclude raw game/account material and private absolute paths.
