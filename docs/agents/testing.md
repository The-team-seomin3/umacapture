# Tests and recognition verification

Read [supported scope](contracts.md#supported-scope) before rating reachability.
These requirements apply to Dart, native doctest and web harnesses unless a section
specifies Dart. Existing suite mechanics remain in the [native test manual](../../native/test/README.md),
[live harness manual](../live-capture-harness.md) and current CI/configuration.
The explicitly requested final pre-PR run is a separate [procedure](pre-pr.md).

## Proportionate tests

Apply the active user-level proportionate-defense rule (reachability and harm,
including any cap); no numeric cap is invented here. Optimize **wall time** to
finish local final checks and required CI, not line count or test count.

Permanent harm includes: web unusable until reload (a restart); wrong persisted
recognition; leaked claim/lock/busy state; a shipped-input/pin/license/golden
verifier accepting wrong data; row filters/resets feeding bulk delete or export;
private data transmitted externally; stale state later written back; a persisted
derivation; omitted notification of a lost capture; and a safeguard for destructive
actions. A duplicate record or ordinary single-setting save/read/default is temporary;
settings migrations/decodes that lose built presets/notations are permanent. A
recomputed-on-read derivation is temporary. A refusal notice without loss is temporary.
Developer diagnostic shape/count/breadcrumbs without user data has no harm; **privacy
of transmitted data** still needs protection.

Use Arrange-Act-Assert, prefer fakes and use mocks sparingly; Mockito is not a
required dependency. Widget tests use `flutter_test` and E2E uses
`integration_test` where appropriate under this proportionality rule.

Prefer one entry-driven representative per warranted concept: native message,
platform-channel command, real widget interaction/store/bytes or user script source.
Constructing internal state by hand is not an entry. Assert the invariant itself;
an existing/same-change entry test **already asserting** that claim avoids duplication,
whereas one that could be extended does not. Add a new behavior as a case beside its
representative; a real output widget test can pair with an input-entry test.

For temporary/no harm, do not default to: an already entry-covered unit; entry x
blocker x item x timing combinations; twins per path/field; exhaustive wording or
translation sentinels; automated visual-detail checks (color/alignment/hover/focus/
width/font scale); developer diagnostics; environment facts; test-infrastructure tests
including hang guards; source/structure/internal-lock/cache/call-shape tests; or a
web-only internal unit merely because the VM cannot compile it.
**Every exclusion yields for permanent harm** within the active rating's cap when no
entry test asserts the same claim. This includes combinations, environment facts,
structure tests and browser-only units. Keep positive controls proving a retained
verifier rejects wrong input. A browser-only concept with no VM entry may be represented
by its permanent-harm unit under `@TestOn('browser')`. No-harm concepts need no test.

### Placement, waits and execution cost

Reuse the concept/code's existing test file, with groups/setup for different fixtures.
New files are justified by a different runner (browser annotation applies to a whole
library), no file covering the concept, or the heavy-file rule below. Flutter compiles
every file separately; do not split for tidiness alone.

For Dart waits read [test/support/settling.dart](../../test/support/settling.dart).
Reuse its correct helper, timeout and negative-assertion window instead of copying
loops. Hold arrival as data on the fake (for example `entered` at a gate), not inferred
absence before the action has landed. Let a frame pass or await a positive fact;
use `settleStorageRows` for storage rows. Wait for a notification, then assert its
count/text. Await a returned completion/drain (join independent futures) before
asserting effect counts. Only a claim with no arrival/completion gets a window:
`pumpRealTimeWindow` under `WidgetTester`; first await the first effect if real I/O
is needed. Plain `test()` awaits its futures. Do not shorten a documented deliberate
window. Real I/O, decodes and channels in `testWidgets` need `runAsync`; condition
waits beat fixed delay loops. Give fakes `Completer` gates, not real-time delays.

Register heavy execution using `measuredExecutionSeconds` and its measurement/threshold
comments in [tool/test_selection.dart](../../tool/test_selection.dart). Missing/stale
entries affect shard balance, not selection. A file that finishes last in its CI shard
or after all local suites needs attention, measured from logs rather than guessed time
bounds. First run independent real-I/O scenarios concurrently, each with its own
directory, preserving within-scenario ordering and `Future.wait(eagerError: false)`
so cleanup waits for all writers even on failure. Split only if it still ends the run,
along the suite's axis with shared helpers in `test/support/`; compare the exact before/
after test-name sets using the JSON reporter. Do not split a file that does not end the run.

## Native verification

Applies to recognition/capture behavior changes under `native/src/`, including scraper,
latches, frame geometry and config semantics. Follow [build mechanics](operations.md#native-cli)
and [producer parity](contracts.md#shared-frame-shaping). Never label a partial run
fully verified. Do not regenerate a failed golden to hide a finding: report case,
diff and judgment; change a golden only for an intended behavior change **after approval**.

### Resize band and supported floor

Read `kDefaultFrameResizeMinUnit` / `kDefaultFrameResizeMaxUnit` in
`native/src/core/pipeline_config.h`, `Frame::kShrinkDeadband`, `kUnitTolerance` and
`isWorthShrinkingTo` in `native/src/cv/frame.h`. The consumer applies the band after
condition detection/calibration, on the **anchor intersection width**. At the audited
baseline defaults are 540/720, the shrink threshold is `max_unit * kShrinkDeadband`
(1.5, hence 1080), and upscale alone has a 3 px tolerance. Thus 537..1079 is effectively
untouched: 810 remains 810, not 720. Derive these numbers if constants change.
Config is `enabled/min_unit/max_unit`; old `unit` warns and uses defaults.
The app defaults the band on, CLI `video`/`replay` accept `--frame-resize` /
`--no-frame-resize`, and live `capture` always uses it with no flag.

540 is a nominal support commitment, **not** a model tensor-size derivation. Failures
at supported sizes are defects subject to the accepted input limits below. Upscale
below 540 is best-effort, not a gap to test/close; do not add `_404w` goldens. Frames
of tens of pixels for which no person could recognize content are not a product defect:
do not add detection, refusal/errors or coverage for that hypothetical input. If a
future owner decision supports it, silent discard is the recorded design direction,
not an instruction to implement now.

### Per-case evidence

Configure a fresh session build directory and use a **Release CLI** for unattended
integration runs: Debug `assert_` may open a modal abort dialog. Run `ctest -N` and
plain ctest; count the current registry, never a historical literal. Golden cases
register only with `golden` or `expect_records`; dual-decode registers every case.
`landscape_2pane_ps5` intentionally has only dual-decode coverage. Read current
`native/CMakeLists.txt` and `native/test/integration/cases.json`.

Match PASS + FAIL + Skipped to the registry, report results **per case and suite**,
and give each skip's reason. Every golden needs its clip under `testdata/clips/golden/`,
ONNX data under `sandbox/modules/`, and a freshly built CLI. CI builds test targets,
not that CLI, and cannot exercise goldens. Dual-decode deliberately skips replay
(FFV1 has no YUV matrix) and zero-record expectations (empty equality is vacuous).
Other skips mean unavailable coverage, not success. Manifest `frame_resize` and
`anchor_unit` are required, but a missing-input skip occurs before validating them.

`integration_golden_coverage` is a per-machine high-water mark, **not an absolute
floor**. Read how many actually ran. Never lower/reset it silently, including a
damaged baseline; `--accept-coverage` needs an explicit request. Harness selftests
`integration_coverage_selftest`, `integration_check_selftest` and the wasm source-check
selftest need no model/clip/CLI and must pass wherever registered; do not equate their
success with recognition coverage.

The geometry assertions read `forwarded_frames`, `anchor_unit_min/max` from stderr's
`UMACAPTURE_RUN_SUMMARY`. Zero forwarded frames means no measurement; absent keys
mean an old CLI to rebuild, not zero. Current golden units lie inside the untouched
arm, so a green `anchor_unit` does **not** show the resize band ran. Shrink coverage
comes from 1080-wide grid rungs and named doctest edges. Both integration runners
reject the token `frame_resize` in output because current occurrences are warnings;
a new healthy log with that token can falsely trip the judge. Check the common
`frame_resize_complaint` in `run.py`, used by dual-decode too.

### Encode and scale grid

Run each configuration with `video`, explicitly passing the resize flag; do not mix
band-on results with older band-off width-ladder measurements. Material is under
`testdata/clips/grid/` (not the must-fire clips' directory):

| Configuration | File |
| --- | --- |
| Pristine reference | `screen-20260802-214946.mp4` |
| CRF 5 / 18 / 30 at 1080-wide | `reenc_1080p_crf5.mp4`, `reenc_1080p_crf18.mp4`, `reenc_1080p_crf30.mp4` |
| CRF 23 at 1080-wide | `screen-20260802-214946_1080p.mp4` |
| CRF 12 at 1080 / 810 / 674 / 540-wide | `hq_1080p.mp4`, `hq_810p.mp4`, `hq_674p.mp4`, `hq_540p.mp4` |
| CRF 23 at 810 / 540-wide | `screen-20260802-214946_810p.mp4`, `screen-20260802-214946_540p.mp4` |

These eleven configurations are **widths**, not video-height labels. Pristine is
1080x2520; corresponding 810/674/540 rungs are 810x1890, 674x1574, 540x1260. If a
derivative is absent, re-derive it from pristine at the stated width/CRF and report
the derivation; never replace an existing file or invent an equivalent to pristine.
The separate must-fire `_540w`/`_404w` ladder derives from differently shaped captures
(for example 736x1308 to 540x960 / 404x718), so thresholds do not transfer by name.
With shipped band on, the six 1080-wide configurations shrink to 720; the rest stay
810/674/540. Use summary geometry, not the filename, as the measurement.

Report each rung's records, factor resets **and all four verdict counts**, factor
total (reference 108; degraded grouping can read 65), anchor unit, and leaf diff to
pristine after dropping volatile record/capture/trainer IDs. Every rung producing a
record both before/after must remain leaf-identical to its own prior record.
Historical accepted exception: CRF23@540 differs from pristine by **109 leaves**,
108 under `.races` (14 to 2 races) plus `factors.parent2[38].id` (615 to 670).
Its own before/after pair must still match. This is heavy compression at 540, not
540 alone: high-quality 540 material matched pristine. The project defines no
compression-quality parameter/target; do not propose tolerance sweeps/quality
thresholds as a new gap. The source also observed 887 forwarded frames on that rung
versus 893 elsewhere, with cause uninvestigated; do not invent an explanation.

### Switch, loss and end-of-input checks

These five inputs live under `testdata/clips/golden/`. Use their ctests rather than
hand-running the three zero-record cases, and check actual manifest assertions:

| Clip basename | Required reset / records / ending |
| --- | --- |
| `player_standard_factor_only_1` | 1 `different`, 0 records, `closed_before_completed` |
| `player_standard_switch_at_factor_top` | 1 `different`, 1 record (B) |
| `player_standard_factor_tiny_scroll_switch` | 2 `different`, 0 records, `closed_before_completed` |
| `player_standard_factor_tiny_scroll_switch_2` | 4 `different`, 0 records, `closed_before_completed` |
| `player_inheritance_switch_with_tiny_scroll` | 1 `different`, 1 record (B) |

Other required verdict counts are zero. The three zero-record cases assert records,
errors and discard count (1/2/4); record-producing goldens do **not** assert reset
counts. All-four-key `expect_factor_switch_verdicts` asserts verdicts only where
declared; an undeclared case asserts nothing. Rule 3 reads the visible factor prefix:
`same` retains and refreshes its witness; `different/empty/unreadable` reset fail-closed.
An always-empty/throwing reader can preserve reset counts while being broken, so
report `same/different/empty/unreadable` beside counts. `discarded` includes record-type
resets as well; distinguish INFO `factor reset` from DEBUG `record type changed`.
Use `discarded_incomplete`, derived from the notification's `completed` bit, for
lost partial sessions; a legitimate completed switch can increment `discarded`
without loss. Missing `completed` counts as incomplete, not silence.

Only `integration_golden.player_standard_factor_only_1` covers end-of-input: its
clip runs out while the scene stays open; the other zero-record clips close the
scene in their footage. For `NativeApi::endOfInput`, `on_end_of_input`, `onIdle` or
sending drivers, check that case actually ran and quote it. A break loses the
expected tag (exit 0/empty errors instead of exit 2), not a different tag.

### Falsification and paths outside goldens

Break the changed behavior temporarily and show **named ordinary test failures**
or named grid failures; compile failure, abort/throw or an unrelated nonzero exit
proves nothing. Pair each deliberate break with the test/rung it defeats, including
breaks nothing detects. Capture stdout logs **and** stderr summary. CLI 0 means
completed without terminal error, 1 threw (no conclusion), 2 completed with terminal
error; zero records alone is not a verdict. Counts are per invocation, not per clip.
Keep byte copies before probes, restore exactly by copying, verify SHA-256, rebuild
and rerun. No path checkout/restore/stash or text rewrite that changes CRLF.

Goldens cannot establish Windows live GPU capture, the Windows import driver's
thread/session/drain/cancel, runner video-frame-grab service round trips, real
browser codec/copy behavior, or web live capture. Use direct live CLI plus the
[app/player harness](../live-capture-harness.md) for producer/UI, actual Windows
method-channel import with leaf comparison to CLI for import, and a fresh wasm/web
build and real browser in a throwaway profile for web. `/metadata/recognizer_version`
may legitimately differ in web/CLI comparisons. Pure Node geometry tests do not
exercise Gecko. For web live use the existing local
`testdata/harness/firefox-live-capture/playtest-checklist.md` and compare its baseline
measurements; if absent, report unavailable procedure/evidence rather than inventing
past success. Goldens share `VideoLoader` decode, not the Windows driver around it.

For changes to record count, discard payload, `videoImportIsPartial` or result-key
resolution, run `test/capture_event_test.dart`'s named test
`a partial import states its count and asks for a check, never a loss`.
It checks rendered count, lost sessions and the request to check. The sibling
sentence-not-key test cannot catch fallback to a misleading full-success sentence
when `pages.capture.video_import.result.completed_partial` is missing/mistyped.

Coordinate live/app runs on this shared PC. Non-focus-stealing instrumentation for
a targeted manual check must be marked, restored byte-exactly and checksummed.
The final suite's visible-window harness instead has its explicit permission gate
in [pre-PR guidance](pre-pr.md#live-harness-stages-4-and-5).
Preserve real-time stationary/factor dwell: no fast-forward, global slow motion or
shortened latch values. Follow the harness's scoped per-tab stretch timing model.
Poll real conditions, cut irrelevant clip time, and reuse launches where isolation
allows. Size static holds to measure a rate, state window/frame count/rationale,
and compare the same scenario against unmodified code. Do not inherit a historical
60-second hold as a required endurance threshold.

## Source, wasm and generated config coupling

See [the wasm manual](../../native/wasm/README.md#repin-the-result).
`tool/web_deps.json`'s `build.sources.roots/exclude` and `build.sh` own the digest
selection; check them instead of repeating a stale list. Excluded-only changes
owe no wasm rebuild/repin; exclusion does not exempt other changed files. A digest
match proves the recorded selection matches the tree, not what the binary contains.
When a covered source changes, rebuild, verify determinism and characterize the
string-table delta before repinning. Regenerate scene config from the **same tree**
and commit it with the matching wasm pin. A config field whose meaning/unit changes
must be **renamed in the same commit**; permissive numeric conversion can silently
pair incompatible config/core. Use separate session-configured build directories
per tree state. If dependency junctions are needed, remove only the verified link,
never recursively traverse the target.
