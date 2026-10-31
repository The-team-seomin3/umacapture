# Windows #11 + #15 local integration — 2026-10-31

Owner initially authorized local integration, a new Release ZIP and safe native validation.
The later PR request authorizes scoped source/document commit, push and PR publication;
no ZIP upload, merge or release is included. Requirements/result consumed:
https://github.com/The-team-seomin3/umacapture/issues/15#issuecomment-6541398440

## Source and preservation

Builder: `codex/issue-11-windows-portable`, HEAD
`d2f69e621130154caaf364fabb3a418eccebc3bf`, with local changes.
The #15 worktree was inspected read-only and its modified/untracked files copied
into this builder. README was combined with #11's existing delivery link. The
original #11 documents and VC++ runtime-copy repair were retained.

During validation, separate #15 work published commit
`681597337bb388ca4dfd815b8c55636aaed29c83`. Its differences from the initial
snapshot were comments and publication-history documentation, with no executable
logic changes. Those latest files were integrated and rebuilt; tests and final
ZIP execution/restart were repeated. The source worktree was never edited by
this integration. Its final input hashes were rechecked successfully.

The retained #11 CMake SHA-256 is
`571f1be424dc0c69cc5c2a321d54bae0d520ec1577c4a41e2d8f59a008c113ae`.
Its Release/Profile copy rules discover compiler redistributables through
`InstallRequiredSystemLibraries`, rather than System32. Shared pinned Flutter
3.44.4 / Dart 3.12.2 and Temurin JDK 17 were reused; JAVA_HOME was build-only.
No system PATH, registry, firewall, TLS validation or managed-runtime change.

## Final artifact and provenance

Final ZIP: `dist/issue11-isolation/umacapture-ko-isolated-6815973-20261031-windows-x64.zip`.
Size: 91,085,758 bytes.
SHA-256: `5142b147b93c60afe75d6d5cb94fcfbae527a047d58f2436be65f23fce80a495`.

EXE SHA-256: `9a9a1378f4566c241c2e3503661d95933bed7dd0495e8c823055e0583c74fee1`.
AOT `data/app.so` SHA-256:
`57158e3846f1af3e631714d50493ca32784cbb791732654bf63f48cac60fed14`.
The native EXE matches the earlier build because no native source changed; Dart
behavior is in the newly rebuilt AOT. Checking EXE alone would miss this change.

All 119 files in the complete Release bundle matched the final extracted manifest.
Extraction: `%LOCALAPPDATA%/Temp/umacapture-isolated-6815973-final/`.
Final first launch PID 84488; normal restart PID 78304. Both paths and EXE/AOT
hashes match the final manifest, with no JDK in runtime JAVA_HOME/PATH. Both
processes exited normally. The earlier ZIP and the first integration ZIP remain
preserved. Original #11 ZIP SHA-256 remains
`d9da46028fa9fc15692a1ad698cd112fa8a0a13616f71d5f4e40c94b5614d77f`.

## Validation

| Check | Result and limit |
| --- | --- |
| Final Release build | Passed, exit 0, zero MSBuild errors; current source regenerated AOT and completed bundle installation |
| Final integrated regression checks | Passed, 163 tests: fork policy, consent, module compatibility/fetch, reporting payload/refusal, localization/navigation, capture/preview/export |
| Normal restart | Passed, final ZIP PID/path/EXE/AOT checked on both launches; saved window size and Korean UI retained |
| Narrow native UI | Passed in inspected states at requested 640x700, captured window region 626x693. Dashboard, navigation, stopped capture and light/dark settings were readable; wrapping/scrolling gave access to lower controls |
| Disabled report/update presentation | Passed: crossed-out app-update and capture-report text, disabled title feedback entry, unavailable tooltip. Pointer attempts on updater/title feedback/capture-report control did not open a dialog, download or launch another application |
| Consent UI | Passed display check: off/disabled even with saved legacy allow=true. The saved value stayed true. No native privacy-setting click was performed; pointer/keyboard mutation prevention is covered by regression fixtures |
| Stale updater cache | Passed: latestAppVersion=99.0.0 fixture remained stored but could not activate upstream updates. Local app version 0.3.0 remained visible |
| Required model traffic | Passed on final first launch with no installed model: runtime logged module version lookup, immutable archive download (10,427,117 bytes), verification and install; 25 ONNX files and module metadata appeared. Installed JPN module version 2026-10-26 was displayed in app settings |
| Data preservation | Passed synthetic settings/window/cache/sentinel checks after normal restart, and no telemetry ID was created. Final marker SHA-256 d49c4fb0386fd72781b4589be53fd49ff94b8293010df161b10a67c597e9677c |
| Source/diff checks | Passed, #15 snapshot hashes, original ZIP hash, retained CMake hash and git diff --check |

Detailed light/dark/settings/capture screenshots were taken on the first integrated
snapshot; the only subsequent source changes were comments. Final ZIP narrow
startup/restart, disabled updater and title feedback were rechecked and separately
captured after the final rebuild. No actual game capture, report submission,
user-record mutation, addon webhook or upstream application update was run.

## Actual outbound observation

A local read-only observer used Windows GetExtendedTcpTable (IPv4 and IPv6),
filtered to the launched app PID before retaining rows, with a nominal 20ms delay.
No proxy, TLS interception or machine-wide packet capture was enabled. Effective
sampling includes API/log overhead and can miss short-lived connections.

- Final PID 84488: 1,393 snapshots, 09:11:43–09:12:27 UTC (18:11:43–18:12:27 KST).
- Final restart PID 78304: 1,139 snapshots, 09:12:45–09:13:21 UTC.
- Observed remote destinations: 104.21.33.151:443 and 172.67.146.135:443. The DNS
  lookup for data.umacapture.com returned those two addresses. No other remote
  TCP destination was retained for these PIDs during the windows.
- Final runtime logs explicitly show the archive path
  `/umacapture/modules/df787e22e4c4c89bf346e65c9ebac8ca22dffa16f8a7dcf47ebe646840d0c39b.zip`
  and completion of verification/install. Restart logs identify the already
  installed/current model version. These are real execution results.

The TCP observation cannot distinguish encrypted HTTPS paths, shared-CDN services,
UDP/QUIC or DNS packets, child-process traffic, missed short connections, or traffic
outside the observation windows. Consequently it is not proof of universal network
silence or a packet-level proof that every prohibited URL was absent. Absence of
upstream DSN/init/app-update execution routes is separately supported by the
inspected source, payload audit and regression tests; those are not packet evidence.
No test report was sent upstream.

## Known limits and evidence

Flutter's native accessibility bridge repeatedly logged `Failed to update
ui::AXTree` during instrumented UI inspection. The captured visual layouts and
ordinary pointer actions worked; root cause and native assistive-technology /
keyboard behavior are not established. Do not describe this as full accessibility
acceptance. Full UI/theme/DPI matrices, OS dialog behavior, real game recognition,
real-record/export persistence and universal clean-machine compatibility remain
Not Tested. The downloaded default models are JPN; no Korean OCR claim is made.

All evidence is local under `dist/issue11-isolation/`: final manifest/source patch,
#15 input hashes, final build and 163-test logs, launch records, per-PID TCP
summaries/observer source, module metadata, console stderr/stdout and screenshots.
No evidence upload or GitHub mutation was performed during the local integration run.
The earlier standalone #15 source validation remains historical; this report
supplies the bounded rebuilt Windows runtime evidence. External distribution is
not authorized and no distribution-readiness verdict is asserted.

## Source publication and reproduction

The owner subsequently requested a PR. Delivery branch
`codex/issue-11-windows-delivery` inherits #15 PR #18 commit `681597337bb388ca4dfd815b8c55636aaed29c83`;
its own delivery commit adds the retained CMake fix and #11 documents only.
The original builder retains the ZIPs and raw local logs. Documentation publication
does not upload or release those binaries. No product source changed after the
final validated bundle; the CMake input hash above matches the delivery worktree.

Run in a provisioned dedicated Windows worktree, using `.fvmrc`'s SDK and the
shared JDK documented in the build manual:

```text
.fvm/flutter_sdk/bin/flutter.bat build windows --release -v
.fvm/flutter_sdk/bin/flutter.bat test --no-pub test/fork_network_policy_test.dart test/privacy_setting_test.dart test/module_update_verdict_test.dart test/report_send_failure_test.dart test/app_update_payload_test.dart test/sentry_scrub_event_test.dart test/korean_localization_test.dart test/app_navigation_surfaces_test.dart test/capture_toggle_reason_test.dart test/capture_preview_toggle_test.dart test/exporter_bytes_test.dart test/module_archive_fetch_test.dart test/module_update_guard_startup_test.dart
git diff --check
```

Actual final build/test output excerpts (raw logs remain with the local artifact):

```text
0 Error(s)
Time Elapsed 00:00:50.57
Built build/windows/x64/runner/Release/umacapture.exe
flutter windows took 56,409ms; exiting with code 0
00:05 +163: All tests passed!
```

The manual provides the extraction/provenance/fixture procedure. The TCP observer
was a local validation aid; it is not a product dependency or background monitor.