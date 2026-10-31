# Windows install-free bundle

Issue: https://github.com/The-team-seomin3/umacapture/issues/11

Use a dedicated worktree and the Flutter SDK pinned by `.fvmrc`. Record the
exact source commit and any source changes before building. The Korean UI handoff
is [korean-ui-localization.md](korean-ui-localization.md).

## Build prerequisites and command

Use Visual Studio's Desktop development with C++ tools, Windows SDK and CMake.
Provision OpenCV and ONNX Runtime with the SHA-256 pins and layout defined in
`tool/fetch_deps.py`. FFmpeg's separate SDK is needed by the CLI, not the Windows
runner; the runner needs OpenCV's videoio FFmpeg plugin DLL.

The locked `sentry_flutter` dependency includes the Windows `jni` FFI plugin.
Its CMake configuration requires JDK headers and JVM import library, even for
an application build that does not intentionally invoke Java. A missing JDK
fails configuration with `Could NOT find JNI`. Use an existing portable JDK 17
and set `JAVA_HOME` only in the build shell; do not modify system settings or
install host prerequisites without authorization. Shared user SDKs can be reused
across worktrees without upgrading them in place.

```powershell
$env:JAVA_HOME = 'C:\Users\kjahy\sdks\temurin-17.0.20.1\jdk-17.0.20.1+1'
.fvm/flutter_sdk/bin/flutter.bat pub get
.fvm/flutter_sdk/bin/flutter.bat build windows --release -v
```

Release/Profile VC++ runtimes are discovered from the selected MSVC toolchain via
CMake's `InstallRequiredSystemLibraries`, rather than copied from `System32`.
Debug retains its existing system debug-runtime path and was not validated here.
If an initial configure failed before bundle setup, the CMake cache may retain a
`Program Files` install prefix. Reconfigure that build directory with
`-DCMAKE_INSTALL_PREFIX=<absolute Release bundle directory>` before retrying;
do not run the build as an administrator to install into `Program Files`.

Check the exit code and actual MSBuild compile/link/install output. Preserve
verbose logs with the local artifact. A successful configure, old executable or
successful CI is insufficient evidence for a fresh Windows release.

## Bundle and extraction

Archive every file under `build/windows/x64/runner/Release/`, with the EXE at
the ZIP root. Preserve subdirectories and all DLLs/assets, including plugins,
`data/icudtl.dat`, `data/app.so`, Flutter assets and bundled fonts/licenses.
Do not add the build worktree, captures, account material or test-data directory.
Record a sorted relative-path/size/SHA-256 inventory and ZIP SHA-256 next to the
ZIP. Extract into a new directory outside the worktree and compare every file
against the inventory before launch. Neither a JDK on the build host nor DLL
names alone proves runtime dependency completeness; inspect the actual imports
and verify the extracted application on Windows.

Portable here means install-free binaries, not a self-contained user profile.
The original #11 ZIP retains upstream update behavior. The #15-integrated ZIP disables
reporting and application updates; see the integration validation record.

## Safe runtime verification

1. Check for an existing running `umacapture` instance. Its fixed native mutex
   can foreground an old window and exit the new process. Coordinate normal
   shutdown; do not terminate a user's process.
2. Prepare controlled synthetic settings/records and a valid writable directory.
   Set process-scoped `UMACAPTURE_DATA_ROOT`. Verify the app's effective settings,
   storage, modules and scratch paths before storage interactions. An unusable
   override falls back to native defaults. The override does not relocate all
   SharedPreferences, font cache, crash support or other OS-managed state.
3. Record the launched process PID, absolute executable path and hash. Match
   that hash to the extracted inventory; repeat on restart. Launch from the
   extracted directory with no developer/JDK directories added to the runtime
   PATH. Record relevant pre-existing shared state and any observed changes.
4. Inspect Korean startup, navigation, capture controls without starting game
   capture, records/empty or error state, settings, notifications and dialogs.
   Inspect light/dark and normal/narrow layouts. Retain bounded app screenshots
   and return native UI findings to #10. Avoid changing actual user records.
5. Exit normally and restart the same extracted executable with the same fixture
   directory. Verify fixture preservation and process provenance again. Report
   each acceptance criterion as Passed, Failed or Not Tested, with its limits.

A Windows UI smoke test does not establish Korean OCR accuracy, live game capture,
universal clean-machine compatibility or complete DPI/accessibility coverage.
No installer, updater redesign, CI pipeline or public release is required here.

Latest local delivery: [#11 + #15 integration validation](validation/windows-isolation-integration-2026-10-31.md).

## Runtime inventory and disclosure

Release/Profile runtime names are generated from the actual
`InstallRequiredSystemLibraries` result into
`windows/runner/msvc_runtime_dlls.cmake`. Every Windows configure compares that
inventory with the resolved copy set and fails on drift. The distribution builder
classifies this set as MSVC toolchain redistributables, separately from System32
and native third-party components, in `assets/additional_license_info.json`.

When an intentionally selected toolchain changes the set, use the same CMake
executable used by Flutter (with process JAVA_HOME still set), after provisioning
the worktree and initializing its Flutter build directory:

```text
cmake -S windows -B build/windows/x64 -DUMACAPTURE_REFRESH_MSVC_RUNTIME_INVENTORY=ON
.fvm/flutter_sdk/bin/dart.bat run build_runner build --force-jit
.fvm/flutter_sdk/bin/flutter.bat test --no-pub test/licence_disclosure_windows_test.dart
```

The refresh option resets itself to OFF after generation; subsequent configurations
verify the checked-in receipt. Review and commit both the inventory and regenerated
disclosure. Do not bypass a mismatch by deleting the positive licence assertions.