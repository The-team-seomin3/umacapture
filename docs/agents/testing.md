# Targeted PoC and MVP verification

## Native verification

Match checks to the issue's authorized delivery and affected code. Use current-session
binaries and preserved inputs; do not require every product workflow for a bounded
PoC, duplicate existing assertions or substitute a huge general suite for evidence.
Detailed suite mechanics are in the [native test manual](../../native/test/README.md).

| Issue | Evidence needed for its claim |
| --- | --- |
| [#2 capture](https://github.com/The-team-seomin3/umacapture/issues/2) | Actual Korean window identity, fresh revision/environment/command, readable unmodified full-client factor image; distinguish target, pixels and save failures. Without live access provide the minimal owner-run procedure and mark runtime Not Tested |
| [#3 factors](https://github.com/The-team-seomin3/umacapture/issues/3) | Real input inventory/reference observations, top-to-bottom scroll and self/parent boundaries, actual ID/star predictions; classify layout, stitch, name/ID, star, grouping and incomplete-input failures. Fake-predictor tests are separate evidence |
| [#4 JSON](https://github.com/The-team-seomin3/umacapture/issues/4) | Producer/consumer and required-field mapping, non-destructive representative round-trip, actual consumer parse and equivalent factor semantics; judge FactorSet, full record and app export separately. Static inspection need not wait for #3 |
| [#5 MVP](https://github.com/The-team-seomin3/umacapture/issues/5) | Real authorized Korean input through complete acquisition, correct factors/groups and safely saved JSON parsed by its required consumer; no target/incomplete scroll/character-switch/save failures reported as success; explicit Japanese DMM/Steam regression evidence or untested limits |

## Find and run the relevant checks

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
These instructions do not claim the PoCs, Korean model quality or MVP already work.
