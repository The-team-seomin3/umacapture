# Local Korean Windows bundle validation — 2026-10-31

Issue: https://github.com/The-team-seomin3/umacapture/issues/11
Design disposition: https://github.com/The-team-seomin3/umacapture/issues/11#issuecomment-6540355580

## Built tree and tooling

Base/source snapshot: `d2f69e621130154caaf364fabb3a418eccebc3bf` (develop, including
merged Korean UI PR #12). Local uncommitted product-build change:
`windows/runner/CMakeLists.txt` uses the selected MSVC redistributable runtime set
for Release/Profile. No Dart/native recognition source was changed.

Flutter 3.44.4 (ad70ec4617), Dart 3.12.2; Visual Studio Build Tools 2022 17.14.44,
MSVC 14.44.35207; Windows SDK 10.0.26100.0; Windows 11 build 26300.9818.
Official Temurin 17.0.20.1+1 ZIP SHA-256:
`e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0`.
The owner requested a shared user SDK; it lives under `~/sdks/temurin-17.0.20.1/`.
Only the build process received JAVA_HOME. System PATH/registry were unchanged.

OpenCV 4.13.0, ONNX Runtime 1.27.0 and experimental headers matched the archive/
header hashes in `tool/fetch_deps.py`. uv was absent; existing PowerShell performed
the same pinned downloads/extraction without installing an extra tool. No
separate FFmpeg CLI SDK was needed; OpenCV's videoio plugin is included.

## Observed build failures and repair

1. Initial fresh configure: missing OpenCV; provisioned pinned native inputs.
2. Provisioned configure: missing JNI headers/JVM, from sentry_flutter 9.23.0 ->
   jni 0.14.2. Owner approved portable JDK 17, then requested a shared SDK location.
3. Compilation/link completed; POST_BUILD failed copying System32/vcruntime140_1.dll.
   The DLL was readable from PowerShell. The repair obtains Release/Profile
   redistributables from MSVC through CMake's standard module. The exact underlying
   filesystem-redirection cause was not independently proven.
4. Corrected a generator-expression list expansion during local implementation.
5. A prior failed configure left the install-prefix cache at Program Files;
   reconfigured it to the absolute Release bundle directory without system writes.

Final command: `.fvm/flutter_sdk/bin/flutter.bat build windows --release -v`, with
process JAVA_HOME set. Final result: exit 0, zero MSBuild errors. Actual runner
compile/link provenance is retained in the earlier full build log and the final
incremental build logs; unchanged compiled sources were reused after CMake-only
copy-rule repairs. Ten `<format>`/C++20 availability warnings occurred during the
full runner compile. These did not prevent compilation/linking.

## Local artifact and checks

ZIP: `dist/issue11/umacapture-ko-d2f69e6-windows-x64.zip` (91,570,189 bytes).
SHA-256: `d9da46028fa9fc15692a1ad698cd112fa8a0a13616f71d5f4e40c94b5614d77f`.
Executable SHA-256:
`9a9a1378f4566c241c2e3503661d95933bed7dd0495e8c823055e0583c74fee1`.

The archive contains the complete Release directory, including all DLLs, ICU/AOT
assets, locale assets and bundled Nanum Gothic. All 119 extracted files matched
the relative-path/size/SHA-256 inventory. Extraction was outside the worktree.
`dist/issue11/` retains the manifest, source patch, compile/build/tool/test logs,
DLL import inspection and local app screenshots; none was publicly uploaded.
The manifest and source patch identify the uncommitted CMake input precisely.

| Criterion | Result / actual evidence |
| --- | --- |
| Release build | Passed, current tree, compile/link and install succeeded |
| Bundle extraction | Passed, 119/119 hashes matched |
| Targeted UI regressions | Passed, 26 tests: Korean localization, app-instance startup, navigation surfaces and toast contrast |
| Executed ZIP provenance | Passed for first launch: PID 51920, absolute EXE path in the external extraction directory, matching executable hash; process path rechecked while running |
| JDK-free startup on this host | Passed: runtime JAVA_HOME unset, no JDK on runtime PATH; the native app window opened |
| Effective test root | Passed: settings screen visibly showed the dedicated temporary data root; settings, modules and scratch appeared under that root; storage path resolution was source-inspected (no record-storage mutation) |
| Native Korean UI | Passed in inspected states: dashboard, capture stopped controls, empty record view, settings, add-column dialog, light/dark settings; no missing Hangul/control overlap observed in these captures |
| Normal exit / fixture preservation | Passed: Alt+F4, process exit confirmed; synthetic telemetry-deny setting reread successfully and sentinel SHA-256 preserved |
| Restart provenance | Not Tested; user was ready to play, so further foreground/input testing stopped |
| Narrow native window | Not Tested; resize attempt did not change the captured width. A 640x700 saved-window fixture was prepared after normal exit, but not launched |
| Native notifications/error dialogs, full light/dark matrix | Not Tested; checked-in #10 widget previews remain separate evidence |
| Debug/Profile builds, clean-machine compatibility, other DPI | Not Tested |
| Live game capture / Korean OCR | Not Tested, outside this issue's UI build slice |

## Limits and handoff

The delivered local ZIP is usable on the tested host. Final #11 acceptance is
partial until restart provenance and remaining native visual checks are recorded.
The fixed application mutex remains unchanged. No game capture was started.
Only synthetic data was used; this run does not prove all real-record workflows.
The environment data-root override does not isolate all OS support state; the
pre-existing shared font cache was present and no bootstrap relocation was written.

`dartjni.dll` imports `jvm.dll`; successful app startup without a runtime JDK does
not prove arbitrary Java invocation works. No product Java feature was tested.
Upstream update URLs remain unchanged; no app update was applied. The dashboard's
external news displayed Japanese `準備中`, within #10's excluded external content.

No commit/push/PR, merge, installer, public release or installed-settings change
was performed. See [the reproducible procedure](../windows-portable.md).
