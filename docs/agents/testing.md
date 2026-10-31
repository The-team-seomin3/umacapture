# Targeted PoC and MVP verification

## Native verification

Match checks to the issue's authorized delivery and affected code. Use current-session
binaries and preserved inputs; do not require every product workflow for a bounded
PoC, duplicate existing assertions or substitute a huge general suite for evidence.
Detailed suite mechanics are in the [native test manual](../../native/test/README.md).

| Issue | Evidence needed for its claim |
| --- | --- |
| [#2 capture](https://github.com/The-team-seomin3/umacapture/issues/2) | Completed bounded acceptance of owner-operated existing-release GUI capture and saved stitched output. Raw screenshot CLI, live class and JP runtime regressions remain Not Tested; do not reimpose them as intake gates or request agent-direct game capture |
| [#3 factors](https://github.com/The-team-seomin3/umacapture/issues/3) | Completed one-capture feasibility study: group/row/star/reference mapping evidence is distinct from automatic Korean name recognition. Reuse its result; unseen inputs and symbol correction remain unverified |
| [#4 JSON](https://github.com/The-team-seomin3/umacapture/issues/4) | Completed synthetic full-record compatibility investigation with actual Dart/native reader checks. Preserve its limits; neither a FactorSet round-trip nor GUI-wrapper parsing is Evaluator import acceptance |
| [#5 MVP](https://github.com/The-team-seomin3/umacapture/issues/5) | Saved inputs through offline OCR, complete explicit review, source-preserving full record-kr.json and paired comparison. Verify source/output/review bindings, allowed-path changes, SID 0, stars 1–3, safe failure and actual reader semantics. Track independent-capture/KR-only acceptance separately |

The [status page](../implementation-status.md) distinguishes issue/PR execution
evidence from merged source. Native checks below apply when their behavior is
actually affected, not as a mandatory native rebuild for offline Python work.
No Evaluator implementation or new confirmation GUI is implied.

## Find and run the relevant checks

- For #5 use the [reviewed-output handoff](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6540427803)
  and the tool README in its confirmed delivery checkout; that uncommitted tool is
  absent from this baseline. Reuse existing tests/results proportionately; verify
  new writer/validation changes with focused normal, ambiguous, stale-input and
  failed-replacement cases. The original app's Japanese paths stay unchanged;
  report unrun runtime regressions without claiming they passed.
- For scene/scraper/stitch/model behavior, start in [native factor tests](../../native/test/chara_detail)
  and the [integration manifest](../../native/test/integration/cases.json). For serialization
  and export follow the [native schema](../../native/src/chara_detail/chara_detail_record.h),
  [Dart model](../../lib/src/chara_detail/chara_detail_record.dart) and
  [exporter](../../lib/src/chara_detail/exporter.dart) to their matching [tests](../../test).
- Configure/build the relevant targets with [CLI guidance](operations.md#native-cli),
  then inspect `ctest --test-dir native/cmake-build-<session> -N` and run the selected
  cases with `--output-on-failure`. Read Passed/Failed/Skipped **per case**, not only
  the aggregate. Goldens need local clips, models and the CLI; CI's unit jobs do not
  establish that they ran. A coverage high-water mark is not absolute coverage.
- Pick cases that actually assert the changed claim. Empty records alone do not
  prove reset/error handling; read declared errors/discards/factor verdicts and the
  CLI summary. For end-of-input changes check
  `integration_golden.player_standard_factor_only_1` actually ran. Do not regenerate
  changed goldens or lower a coverage baseline without explicit approval.
- Native goldens drive offline CLI input, not Windows GPU capture, the app's import
  driver, or browser copy/codec behavior. Check an affected producer directly and
  report the gap. If app-level capture/record integration needs the existing harness,
  read [its manual](../live-capture-harness.md); request this run's permission before
  visible app/player windows steal focus, run them serially, and preserve real timing.
  Browser/wasm checks apply only when existing shared behavior is affected.
- Preserve shipped resize/anchor semantics and supported inputs. Read constants/config
  rather than copying old numbers; below-540 rescue and compression-quality sweeps
  are not new PoC requirements. Geometry changes need real-pixel/anchor evidence;
  a green record golden alone may not exercise the resize arm.
- For actual Dart changes, use pinned format/analyze and focused tests. Add tests for
  meaningful behavior/data risk where existing assertions do not cover it. Reuse
  [settling helpers](../../test/support/settling.dart) for condition waits instead of
  fixed sleeps. New artifacts/comments remain English; no unrelated UI test project.

## Report and preserve evidence

State tested source/model/input scope, actual commands and outcomes, affected-case
results/skips, observed versus expected values and meaningful gaps. Use
`Verified / Failed / Not Tested`; unavailable data/environment is not a pass.
For temporary probes keep byte-exact copies, restore and checksum, then rebuild;
never rewind other work with path checkout/restore/stash. Preserve private raw
material and issue handoffs as described in [contracts](contracts.md#research-handoffs).
These procedures do not broaden the bounded results linked above into general
Korean recognition, distribution readiness or downstream importer acceptance.
