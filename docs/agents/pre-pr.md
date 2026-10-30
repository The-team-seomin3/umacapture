# Explicitly requested final pre-PR check

Run this five-stage procedure **once, only when the user explicitly requests this
final check**, including a delegation explicitly conveying that request. Do not
invoke it for work in progress, plan stages or an automatic completion condition.
A generic "run all tests" request is ambiguous: clarify whether this final check
is meant. An implementation/PR request alone is not its trigger. Ordinary targeted
validation remains required under [testing](testing.md).

This document owns stage selection, ordering and reporting. [Operations](operations.md)
owns build mechanics; [testing](testing.md#native-verification) owns recognition
verdicts; the [live harness manual](../live-capture-harness.md) owns scenario/schema/
timing details. Current [CI](../../.github/workflows/ci.yml) and
[test selection](../../tool/test_selection.dart) own executable lists.

## Select stages before running

Refresh the intended base and inspect `git diff --stat` / changed paths against
`origin/develop...HEAD`, plus any intended uncommitted delivery. Take the union of
applicable rows and record R (required), r (recommended, may skip with reason),
or skip before execution. A recommendation is not an unconditional mandate.

| Changed area | 1 CI parity | 2 local builds/pins | 3 native | 4 single-clip live | 5 multi-clip live |
| --- | --- | --- | --- | --- | --- |
| General executable/config changes | R | R (Windows build + verified pins) | r | | |
| `native/src/`, `native/vendor/`, `native/wasm/` | R | R + applicable wasm rebuild comparison | R | R | r; R if factors, duplicate probe or record identity can move |
| `native/test/integration/`, `native/CMakeLists.txt`, `assets/config/`, models | R | R | R | r | |
| `windows/runner/` | R | R | | R | r |
| `lib/` capture page/state, native-start settings, platform controller | R | R | | R | r |
| `lib/` record store, duplicate refusal, factor enhancement, merge, parent links (including relevant capture UI) | R | R | | R | R |
| Other `lib/`, `test/` | R | R | | r | |
| `test_driver/`, `tool/live_capture_test/`, `native/tool/mimic_player/` | R | R | | R | R |
| `web/`, `tool/*.mjs` | R | R | | | |
| `tool/cloudflare/` | R | R + publish sandbox test | | | |
| Documentation/instructions only (`docs/`, `.claude/`, root guide) | R | | | | |

Native stage 3 is recommended generally to notice lost local clips; a Dart-only
diff cannot change the native golden pipeline. A covered wasm-source edit needs
its rebuild comparison; read digest exclusions rather than rebuilding excluded-only
files. Documentation migration does not require Korean client runtime tests.

Across all stages: build everything used this session, do not path-checkout/restore/
stash to rewind, preserve test material and all harness history, run GUI scenarios
strictly serially. Keep one stage's measurements free of competing work when reporting
comparable durations. Do not fix, regenerate goldens or repin inside this checking
procedure: report findings to the implementation task.

## Stage 1: CI parity

Use the pinned SDK and PowerShell for Flutter/Dart on Windows (append `.bat`).
Check each command's exit independently; a later successful command must not mask
an earlier failure. In this order:

1. `dart run build_runner build --force-jit` through the FVM SDK; require exit 0.
2. Immediately inspect status: no generated changes or new generated files. CI
   checks generated outputs under `lib/` and `test/` are committed.
3. `flutter analyze --no-fatal-infos`: no errors/warnings, exit 0.
4. `dart format --output=none --set-exit-if-changed lib test tool`: exit 0.
5. `flutter test -j 4 --reporter github test`: exit 0, no failures.
6. Derive browser files using pinned `dart tool/test_selection.dart browser`, fail
   on selection error, then pinned `dart test --platform chrome --reporter expanded`
   with **that list**. Count distinct files in the execution log against selection;
   do not hand-copy suite names or run with empty arguments. `@TestOn('browser')`,
   not a filename suffix, routes suites. This is headless `package:test`, not
   `flutter test --platform chrome`. No Chrome launch/no tests is not a pass.
7. `bash tool/build_web.sh --release --pwa-strategy=none`: exit 0 and newly written
   `build/web/main.dart.js`. This **owner-approved local wrapper** supersedes the
   old direct command; see [web build policy](operations.md#web-builds-and-pins).
8. `bash tool/hooks/test_pre_commit.sh`: exit 0.
9. Run **each** `node tool/test_web_*.mjs` entry actually named in current CI,
   retaining CI's provisioning prerequisites/order for demux. Require every exit
   and real test execution; absent mediabunny can skip demux and is not coverage.

Codegen precedes analyze/tests/builds. Local license checking is stage 2's
`--licenses --require-verified`, **not** CI's `--licenses --ci-artifact`; CI's partial
provisioning assertions are intentionally wrong for a fully provisioned local tree.
Do not copy CI's subsequent asset checkout into the working tree.

## Stage 2: what CI cannot establish

- Pinned `flutter build windows --release`: require exit 0, actual relink and a new
  `build/windows/x64/runner/Release/umacapture.exe`. If incremental build skips it,
  remove only the verified local Release exe/runner object build outputs before
  rebuilding, not source or data. CI does not build the Windows runner.
- For an applicable native/wasm diff, `uv run native/wasm/check_sources.py`, then
  `SKIP_SOURCE_CHECK=1 bash native/wasm/build.sh` if the emsdk PATH trap requires
  separating the check. Hash the newly built JS/wasm in its reported output
  directory against `tool/web_deps.json`; do not substitute the old provisioned
  files or repin a mismatch. Excluded-only diffs owe no rebuild.
- Pinned `dart run tool/check_web_pins.dart --licenses --require-verified`: all
  pinned files verified, none missing. This checks provisioned bytes, not the
  just-built module comparison above.
- For Cloudflare changes, `bash tool/cloudflare/test/publish_modules_test.sh`:
  exit 0/no failures. It runs with stubbed wrangler/curl in a sandbox and contacts
  no service; it is not in CI.

## Stage 3: native suites

Configure a **new** `native/cmake-build-<session>` with MSVC/Ninja, `VSLANG=1033`,
Release, explicit command failure propagation and compilation/link proof. Build
all default targets (CLI, both test executables, mimic player), then:

```text
ctest --test-dir native/cmake-build-<session> -N
ctest --test-dir native/cmake-build-<session> -R "^(umacapture_tests|umacapture_ffv1_tests)$" --output-on-failure
ctest --test-dir native/cmake-build-<session> -E "^(umacapture_tests|umacapture_ffv1_tests)$" --output-on-failure
```

Interpret registry, each skip, coverage high-water mark, golden diffs and named
selftests using [native verification](testing.md#per-case-evidence). No hardcoded
historical test total. This new player's build is **not** the fixed-path player
that the live harness runs.

## Live harness stages 4 and 5

**Before builds or launches for these stages**, obtain this run's permission: two
visible windows (app/player) repeatedly take focus; the PC must be left alone.
Historical reference was about 15 minutes of scenarios, about 17 including builds;
state an appropriate estimate, never assume the owner is away. A delegated worker
must have that explicit run authorization or stop after stage 3 and report pending
permission. Once allowed, do not interact with the windows or launch other GUI work.

Read-only preflight: no `umacapture.exe`, no `umamusume` window, VM-service port
57391 free, all scenario clips/sidecars/goldens present and ONNX modules in the
app's module directory. Ask the owner to close their app, never kill it. The app's
single-instance behavior can raise an existing window; the player impersonates
the real game, so neither may already be running. Run
`uv run tool/live_capture_test/test_stops_validation.py` with bytecode writing
disabled; this pure check needs no app/clip. Shared port/scratch root require serial runs.

Build the pinned debug driver app (`flutter build windows --debug -t test_driver/app.dart`)
and verify relink/timestamp, removing only its local exe/runner objects when needed.
A sporadic `LNK1163` on the recognizer object was historically repaired by deleting
that object and rebuilding; it is not proof of a source defect. The scenario runner
never builds it. Rebuild the player's **actual configured path** from `BUILD` in
`app_drive_run.py` / `run_mimic.cmd` (currently `native/cmake-build-release`), with
vcvars matching that cache; force clean the player target and confirm source compile
and link. Do not blindly copy an old machine's VS18/14.51 paths; inspect the cache.

Run one scenario at a time with a unique tag:
`uv run tool/live_capture_test/scenario_run.py tool/live_capture_test/scenarios/<name>.json --tag <unique-tag>`.
Use the [manual's committed scenario table](../live-capture-harness.md#the-committed-multi-clip-scenarios)
and these expected checks:

| Stage / scenario | Expected result |
| --- | --- |
| 4: `player_standard_5` | exit 0, one matching record, capture `succeeded` |
| 4: `falsify_wrong_golden` | exit 1, actual record mismatch only, capture `succeeded`, no per-clip finding |
| 4: `falsify_truncated_input` | exit 2, sole `outcome_unobserved`, last state capturing, no capture outcome, `match:false`, `harness_status:no-record`; this expected inconclusive case is not retried |
| 5: C1, C2, C3, C4 positive scenarios | exit 0, both clips `succeeded` |
| 5: `c5_same_clip_twice` | exit 0, `succeeded` / `alreadyCaptured` |
| 5: `c6_merge_hopstep` | exit 0, both `succeeded`, second merge `completed:true`; 2/3 holds can be a retry while apply was disabled |
| 5: `falsify_c1_expects_no_candidate` | exit 1, `candidate_unexpected` only, records still match |
| 5: `falsify_c3_expects_candidate` | exit 1, `candidate_mismatch` only, records still match |
| 5: `falsify_c4_wrong_slot` | exit 1, `link_mismatch` only, records still match |
| 5: `falsify_c5_expects_succeeded` | exit 1, **both** `status_mismatch` and `probe_mismatch`, records still match |

Full C1-C4 filenames and expected per-clip identity are in the manual/scenario JSON;
run all positives before their falsifications, in documented order. A falsification
is interpretable only beside a green positive sibling. Read reason codes, records
and **each clip's capture.status**, not exit alone. In general exit 0 is a matched,
observed valid run; exit 1 is an actual contradiction; exit 2 is unjudged. Retry an
unexpected exit 2 **exactly once**, whole scenario/new tag; a second is unverified,
never passed/failed or retried a third time. Run-level synchronization errors can
have no bracketed reason code and may follow JSON on the same line: search for
`FAIL`/`ERROR` anywhere, not just line starts.

Long scenarios can outlive one tool call. Keep the process/log and an explicit
completion/exit marker, wait until completion and do not abandon a running scenario.
For a background sequence use a stop file **between** scenarios; killing its wrapper
can leave the child running. Prefer tool-managed sessions or hidden redirected
processes, not `Start-Job` assumed to outlive a call. Preserve all results under
`testdata/harness/runs/`, read JSON explicitly as UTF-8, and use a separate disposable
log directory for loop bookkeeping. Afterwards preflight again; stop only surviving
processes **this run owns**, by PID.

If the harness itself changed, rerun its pure tests and any player fidelity check
required by [the manual](../live-capture-harness.md#parts). For `app_drive_run.py`
merge-hold changes, temporarily replace the hold with a tap: C6 must fail with
`merge_incomplete`, a two-record mismatch, harness status `ok`, three holds and
`completed:false`. For per-clip signal changes, deliberately retain prior
`ClipSignals`: C5 must exit 2 with the run-level marker-before-arm synchronization
error and `marker_after_arm:false`. Each needs its green positive in this session;
keep binary copies, restore byte-exactly, checksum, check status and rerun pure tests.

## Report and known limits

Report each selected/skipped stage and deciding path, then step, result, counts,
registered total where relevant, skipped case names/reasons, wall duration (including
competing work) and completion (finished/timed out/retried/not started with reason).
Every finding includes command, case, diff/log excerpt and revision. Historical
machine timings are estimates, not acceptance thresholds.

This suite does not prove real wasm capture in a browser (Node/storage browser tests
are narrower), full-screen GPU capture (the mimic is captioned), events missing from
recordings, app appearance/layout/theme/text, Windows import driver behavior,
Release/Profile record correctness (driver is Debug), or GPU timing on another host.
Report those limits; targeted real-use verification belongs to the affected task.
For shell/PATH/cache/encoding traps use [operations](operations.md#native-cli).
