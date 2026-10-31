# Fork isolation implementation validation — 2026-10-31

Baseline: `develop` `d2f69e621130154caaf364fabb3a418eccebc3bf`.
Branch: `codex/issue-15-upstream-isolation`; publication snapshot is identified by the PR HEAD.
Owner authorization: issue #15 implementation and corrected review publication
in the Codex chat, including the later instruction to retain crossed-out,
locked controls to preserve layout. The owner subsequently requested a PR for independent review, authorizing commit/push/PR publication.

## Results

| Check | Result | Evidence / limit |
| --- | --- | --- |
| Pinned dependency preparation | Passed | Flutter 3.44.4; pub get. OpenCV 4.13.0, ONNX Runtime 1.27.0 and both experimental headers match `tool/fetch_deps.py` SHA-256 pins. `uv` is absent; existing PowerShell performed the pinned downloads/extraction without a host installation. Existing shared JDK 17 was set only for the build process. |
| Code generation | Passed | `dart run build_runner build --force-jit`, completed in 41s. The environment-dependent web license inventory rewrite was discarded, preserving the existing tracked inventory. |
| Focused policy/privacy/version/payload/Korean/navigation tests | Passed | 112 tests. Fresh/allow/deny settings, repeated startup and synthetic exception paths make no Dart HTTP request or telemetry ID; stale updater metadata cannot re-enable actions; required module compatibility is checked; actual localized unavailable text is asserted. |
| Capture, preview, export and module regression | Passed | 51 tests in `capture_toggle_reason_test`, `capture_preview_toggle_test`, `exporter_bytes_test`, `module_archive_fetch_test`, `module_update_guard_startup_test`. Module fetch tests use controlled fixtures, not upstream uploads. |
| UI fixture layout/input | Passed | Included in the 112 tests: Japanese/Korean, light/dark, 540px/1000px. Controls remain, privacy switch shows off and is disabled, saved consent is preserved, pointer/Tab/Enter/Space cannot activate the guarded control. No framework layout exceptions. |
| UI fixture raster preview | Passed | Korean narrow light/dark images generated with bundled Nanum Gothic by `--dart-define=FORK_UI_PREVIEW=true`. The light preview was visually inspected. These are isolated widget fixtures, not screenshots of the running Windows app. |
| Dart analysis | Completed, with existing informational findings | No errors/warnings; eight deprecated `hasFlag` infos in unchanged test files. Default analyzer exit is 1 for those infos; it is not a clean exit-0 result. |
| `git diff --check` | Passed | No whitespace errors. |
| Source destination audit | Passed for inspected application routes | No upstream DSN or app-update URL remains in `lib/`; required model source and fork repository link remain. See policy classification. This is not a packet trace. |
| Release compilation/link | Observed | New `umacapture.exe` and Release AOT `build/windows/app.so` produced by current-session builds. Forbidden upstream project/installer URL byte strings absent in these products. `<format>`/C++20 warnings remain. |
| Full Windows Release bundle | Failed | Existing runner POST_BUILD copies VC++ runtimes from `C:/Windows/System32`; `vcruntime140_1.dll` copy fails (MSB3073), reproducing #11's known prerequisite. No runner/CMake packaging changes were made here; #11's separate patch is not silently incorporated. |
| Fixed Release ZIP launch/restart and outbound traffic | Not Tested | No complete fixed ZIP and no app launch. Requires the #11 packaging prerequisite and a fresh final-source build. No old executable was used as evidence. |
| Actual game capture/recognition and stored-data persistence | Not Tested | No game automation or real user records touched. Focused source/fixture regression tests are not proof of live capture. |

## Local reproduction

Use `.fvm/flutter_sdk/bin/flutter.bat` and `dart.bat` on Windows (omit `.bat`
on other hosts). This task does not expand Korean support to another platform.

```text
dart run build_runner build --force-jit
flutter test --no-pub --dart-define=FORK_UI_PREVIEW=true test/fork_network_policy_test.dart test/privacy_setting_test.dart test/module_update_verdict_test.dart test/report_send_failure_test.dart test/app_update_payload_test.dart test/sentry_scrub_event_test.dart test/korean_localization_test.dart test/app_navigation_surfaces_test.dart
flutter test --no-pub test/capture_toggle_reason_test.dart test/capture_preview_toggle_test.dart test/exporter_bytes_test.dart test/module_archive_fetch_test.dart test/module_update_guard_startup_test.dart
flutter analyze --no-pub
flutter build windows --release --no-pub
git diff --check
```

Local logs/previews and the pre-publication source hash manifest are under
`.notes/issue15-*` in this dedicated worktree; tests and this record remain the
durable reproduction contract. No private game/account data was uploaded.

## Delivery boundary

Source implementation and focused validation are complete; full bundle/runtime
and distribution acceptance remain incomplete. Rebuild the final integrated
source after #11's packaging fix, identify the extracted process by path/hash,
exercise reporting/updater suppression with controlled settings, and observe
outbound behavior before sharing or releasing a ZIP. Existing #11 ZIP evidence
does not validate this change. Commit/push/PR publication is authorized for independent review; no merge, deployment, public release or installed-settings change is included.
