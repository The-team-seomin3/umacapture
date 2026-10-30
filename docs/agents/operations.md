# Setup, CLI and web operations

Load only the section needed for the task. [AGENTS.md](../../AGENTS.md) governs
provenance/authorization; no example asserts that this host has the prerequisites.

## Setup and build

Desktop/native setup targets Windows MSVC; the product also has a web build.
Check Git, FVM, `uv`, and Visual Studio 2022+ Desktop C++ workload first. Optional
7-Zip speeds OpenCV extraction; the dependency fetcher has a self-extractor fallback.
Use Python through `uv run`, not bare Python. Do not install/upgrade host SDKs,
package managers/global packages, Visual Studio, emsdk or other external tools
unprompted. Explain a missing prerequisite or obtain explicit installation approval.
FVM/uv may download into global caches; surface that when relevant to the user's
constraints. Project-scoped setup, once prerequisites/authorization are satisfied:

```text
fvm install
git config core.hooksPath tool/hooks
git config blame.ignoreRevsFile .git-blame-ignore-revs
uv run tool/fetch_deps.py
.fvm/flutter_sdk/bin/flutter pub get
.fvm/flutter_sdk/bin/dart run build_runner build --force-jit
```

Use `.bat` for the SDK commands in PowerShell. `.fvmrc` is the sole Flutter pin;
CI installs it via `.github/actions/setup-flutter`, not a copied version. Get packages
before codegen and dependencies before native configure/build. Fetching verifies
pinned SHA-256 and writes ignored `windows/{opencv,onnxruntime,ffmpeg}`. The current
versions/layout authority is [tool/fetch_deps.py](../../tool/fetch_deps.py) and CMake,
not a machine example. `windows/clip` is committed MIT source; no fetch is needed.
OpenCV provisioning needs Windows. Default extraction preserves the official tree;
`--slim` (CI) removes unused parts; `--only` selects a dependency, `--force` re-fetches.

Dependency bumps update URLs/hashes (including ONNX's two source-only experimental
header pins). An OpenCV bump also updates version/runtime/DLL paths in **both**
`native/CMakeLists.txt` and `windows/runner/CMakeLists.txt`, plus the OpenCV action
cache key. FFmpeg bumps also update `.github/actions/provision-ffmpeg/action.yml`'s
cache key. CLI/FFV1 tests require libav; the Flutter app does not link it. ONNX is
linked by CLI/app, not dependency-light test targets; CI provisions OpenCV/FFmpeg
but intentionally not ONNX. See [native tests](../../native/test/README.md#build--run).

Verify setup with pinned Flutter tests and `flutter build windows` as appropriate;
a native CLI/tests build is separate. If Windows INSTALL tries to write to
`C:/Program Files/umacapture` after interrupted configure, inspect the poisoned
`CMAKE_INSTALL_PREFIX` cache: the default-prefix override only runs on first configure,
and sentry-native FetchContent can fail earlier. Remove the **verified local
`build/windows` build-output directory**, not just `_deps`, and rebuild uninterrupted;
INSTALL should populate the bundle's `data/`, not require administrator rights.
Coordinate running instances/build locks instead of killing a user's app.

## Native CLI

Read the [architecture and builders](../native-recognition-backend.md) for pipeline
meaning; use [native tests](../../native/test/README.md) for suite definitions and
[verification](testing.md#native-verification) for evidence obligations.

Locate Visual Studio using `vswhere` at the standard VS Installer path. In a single
`.cmd`, call the discovered `VC/Auxiliary/Build/vcvars64.bat`, set `VSLANG=1033`,
then configure/build with its MSVC/CMake/Ninja environment. Sourced environments do
not persist between tool calls. Adapt absolute paths to **this worktree**:

```bat
@echo off
set VSLANG=1033
call "<VS-install>\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d <worktree>\native
cmake -G Ninja -S . -B cmake-build-<session> -DCMAKE_BUILD_TYPE=Release || exit /b 1
cmake --build cmake-build-<session> || exit /b 1
```

Launch with `cmd /c <absolute-script.cmd>` from PowerShell. From Git Bash scope
`MSYS2_ARG_CONV_EXCL='*'` to that literal `cmd /c` hop (or direct Windows executable),
or use `cmd //c`; otherwise MSYS can rewrite `/c`, return 0 and do nothing. Do not
prefix a plain bash script such as `native/wasm/build.sh` with that flag: its child
`uv` path resolution can fail. Use `.\umacapture_cli.exe` or an absolute executable
path, not a bare name relying on current-directory lookup. Verify compile/link output
and timestamps, not the wrapper's final exit alone.

Use session-fresh `native/cmake-build-*` directories, ignored by Git; do not configure
old CLion build trees that pin incompatible Ninja/compiler caches. Keep temporary
scripts in an ignored build directory or remove them when done. Incremental builds
still need the matching vcvars environment and proof headers recompiled; Japanese
include notes can lose Ninja header dependencies, hence `VSLANG=1033` and checking
`ninja -t deps` for suspect `#deps 0`. Lingering compiler services can lock build
outputs; coordinate owned processes or wait before cleanup.

Run from `native/<build-dir>/`: defaults are `../../assets/config`,
`../../sandbox/modules`, `./temp` and `./storage`. `video/replay/stitch/recognize`
accept absolute `--assets_dir`, `--modules_dir`, `--output_dir` to remove that cwd
dependency; `build` takes `--assets_dir`. Current CLI11 options in
`native/src/core/cli.cpp` and the fresh executable's help are authoritative.

| Command | Purpose / precautions |
| --- | --- |
| `build --assets_dir <dir>` | Generate four chara-detail scene JSONs; use throwaway output for smoke tests. Only intentionally target tracked assets after builder changes, then commit regenerated output |
| `screenshot --output <png>` | Single raw client capture, no recognition loop; success is file/pixel evidence, not factor recognition |
| `capture [--record <mkv>] [--duration <seconds>] [--stop-file <path>]` | Live recognition loop; full pre-shaping frames/timestamps tee to lossless FFV1 when recording. No resize-disable flag |
| `video --video_path_list <clip>...` | Offline decode, full frames/no producer pane snapshot |
| `replay --record <mkv> [--no-calibrate]` | Full raw-frame replay with detection/calibration by default; legacy pre-cropped files may need the escape flag |
| `stitch --id <uuid>` | Rebuild tall images from scraped record fragments |
| `recognize --id <uuid>...` | Re-read stitched inputs; writes predictions, so use isolated copies of material |

`build`/`screenshot` return directly. Offline pipeline commands drain all in-flight
stages, join and exit; do not kill them when an artifact first appears. A drain
deadline throws (five minutes in current code). Live `capture` runs until Ctrl-C,
duration or stop file; graceful teardown finalizes FFV1 and flushes logs, while a
hard kill can lose both. For shutdown/logging changes, run through teardown and
check exit. Stitched inputs in old machine build directories are not checkout
fixtures; generate them from authorized video/stitch or isolated copies, always
with this session's binaries.

Pipeline exit 0 means completed with no terminal `onError`, 1 means threw/no verdict,
2 means completed with terminal error; 77 is never returned because ctest calls it
Skipped. `build`/`screenshot` use only 0/1, with no pipeline summary. Capture both
stdout (spdlog) and stderr (`UMACAPTURE_RUN_SUMMARY`, fatal message). Summary key
semantics come from `RunReport::summaryLine` in `native/src/core/cli_run_report.h`.
Counts are per invocation, not per input clip. End-of-input and on-screen incomplete
closure deliberately share `closed_before_completed`; do not infer which from the tag.
Record artifacts are under `storage/chara_detail/active/<uuid>/`; completion notification
and record contents matter, not exit 0 alone.

Native logs use `native/src/util/logger_util.{h,cpp}`; there is no default file sink.
Use `log_*`/`vlog_*`; TRACE macros are compiled out by the DEBUG compile-time floor
unless deliberately toggled/rebuilt. WARN flushes immediately; DEBUG/INFO may wait
five seconds and vanish under hard kill. Debug builds provide PDBs and active
`assert_`; Release disables `assert_`, including builder round-trip checks. Use a
separate Debug build for assertion/debugger work and Release for unattended integration.
The POST_BUILD steps copy matching OpenCV/ONNX/videoio/libav runtime DLLs. If a Debug
video decode stops early, check its expected `d`-suffix videoio DLL rather than
assuming bad recognition. `cdb` is optional SDK tooling: verify availability, use
the build dir as cwd and absolute exe path; `-lines`, `bm`, `g`, `kn`, `x`, `dv`,
`p/t`, `??` inspect the fresh PDB-enabled process. `q` kills its child, so use a
self-terminating throwaway `build` target for debugger smoke work.

## Shell diagnostics

Historical host traps are diagnostic leads, not assumptions about this PC:

- An `app.asar/node_modules` entry injected by a desktop host into Git Bash PATH
  can truncate the PATH reaching `cmd`, hiding PowerShell/System32/`rc.exe`/`uv`.
  Prefer PowerShell for Windows SDK commands, or remove only that injected entry
  from the current process PATH before retrying; do not rewrite persistent PATH.
- Verify vcvars matches a reused **owned** cache; fresh configuration avoids stale
  toolset/Ninja paths. For the harness's fixed player path, inspect its cache and
  force target compile/link rather than assuming incremental header tracking.
- Avoid `sed -i` on tracked CRLF files: Git's normalization may hide byte changes.
  Binary backup/restore and hashes are required for temporary instrumentation.
- Windows PowerShell native redirection can produce UTF-16LE or wrap stderr as
  `NativeCommandError`. Choose explicit UTF-8 output or redirect inside the command
  process; detect encoding/BOM when reading existing logs. Always retain both streams.
- Use process handles/tool sessions and completion markers for long commands;
  `Start-Job` may die with its host call. Start background helpers hidden unless a
  specifically authorized GUI test requires visible windows.

## Web builds and pins

For local builds use `bash tool/build_web.sh --release --pwa-strategy=none`, never
a direct Flutter web build bypassing its pin/license gate. This includes the final
pre-PR suite. The owner resolved that historical command conflict on 2026-10-31;
see [audit](migration-audit.md#resolved-and-excluded-instructions). Current CI's
direct Flutter build is a **compile-only exception**: it lacks the in-tree wasm
module and explicitly checks a partially provisioned license artifact. Do not copy
its `--ci-artifact` or `git checkout -- assets` cleanup into a local provisioned tree.

Read [native/wasm/README.md](../../native/wasm/README.md) for external emsdk/wasm-OpenCV
prerequisites, drift checks, build/provision/repin commands and disclosure. No assumed
host installation. Use `uv run native/wasm/check_sources.py`; if sourcing emsdk hides
`uv`, run it separately before `SKIP_SOURCE_CHECK=1 bash native/wasm/build.sh`.
This relocates the check, never removes it. Hash **newly rebuilt** JS/wasm from the
build's reported output directory against the pins; checking the old `web/wasm/`
copies cannot establish rebuild equivalence. Rebuild/repin covered changes with the
same-tree generated config as required by [testing](testing.md#source-wasm-and-generated-config-coupling).
CI/wrapper fail on stale source digest; the commit hook only warns because rebuilding
needs external tools. A recorded digest does not prove binary contents.

Unfiltered `build_runner --force-jit` regenerates license assets and enforces pins.
A GPL/EUPL/MPL rejection in the **pub-license builder** is a stop, not permission to
weaken the check. The pinned, unmodified MPL mediabunny web bundle has a separate,
documented source-disclosure acceptance in `tool/web_deps.json`. On mismatch restore
pinned web bytes using `uv run tool/fetch_web_deps.py`, or deliberately update pins
under the authorized dependency task and regenerate. A gate can delete its output;
Flutter's directory assets can still compile, so do not continue after a failed gate.
`not_provisioned` is valid for Windows-only operation but must not downgrade an
existing committed `verified` disclosure. Web delivery needs `verified` and must
use the checked wrapper; do not bypass it to manufacture a local pass.
