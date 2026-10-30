# Build and run the PoC tooling

## Setup and build

Check the required inputs before the task: Windows/Korean client access for live
capture, real Korean material/models for recognition, and an identified consumer
for JSON compatibility. Source inspection can proceed without runtime access;
missing tools or data are Not Tested, not permission to install or fabricate them.

Native CLI builds require Windows MSVC/CMake/Ninja and provisioned OpenCV/ONNX/FFmpeg.
Use [tool/fetch_deps.py](../../tool/fetch_deps.py) for current hash-pinned dependency
layout and [native/CMakeLists.txt](../../native/CMakeLists.txt) for target requirements.
Do not assume this host has them or install host tools unprompted. Python tooling
uses `uv run`. For Dart changes use `.fvmrc`'s SDK at `.fvm/flutter_sdk/bin/`:
packages before codegen, then `dart run build_runner build --force-jit` (`.bat` on
Windows). Keep generated EOL handling in `.gitattributes`; no whole-tree formatting
or normalization. Existing Git hooks remain applicable; do not bypass failed checks.

## Native CLI

Build every executable used from the current tree this session. Locate Visual Studio
using `vswhere`; call its `VC/Auxiliary/Build/vcvars64.bat` and CMake in the **same**
`.cmd` process. Adapt placeholders to this dedicated worktree/toolchain:

```bat
@echo off
set VSLANG=1033
call "<VS-install>\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d <worktree>\native
cmake -G Ninja -S . -B cmake-build-<session> -DCMAKE_BUILD_TYPE=Release || exit /b 1
cmake --build cmake-build-<session> || exit /b 1
```

From PowerShell launch `cmd /c <absolute-script.cmd>`. Do not reuse another toolchain's
old CLion cache. Confirm compiler/link output and current artifact provenance, not
exit 0 alone. Use Release for unattended integration; Debug enables `assert_` and
its possible modal abort dialog. For a builder round-trip assertion use a fresh
Debug build deliberately. Never kill a user-owned app or interfere with the game.

Run from `native/<build-dir>/`; use `.\umacapture_cli.exe`, not a bare name. Defaults
resolve assets/models/output relative to that directory. Read current options in
[cli.cpp](../../native/src/core/cli.cpp) and the freshly built executable's help.

| Task | CLI entry / meaningful result |
| --- | --- |
| #2 raw factor screenshot | `screenshot --output <private.png>`; inspect actual full pixels and save outcome, no recognition loop |
| #3 recorded input | `video --video_path_list <clip>`; or `replay --record <ffv1.mkv>` for full recorded frames |
| #3 isolated pipeline stages | `stitch --id <uuid>`, `recognize --id <uuid>`; use isolated record copies, since predictions are rewritten |
| Authorized live investigation | `capture [--record <private.mkv>] [--duration <seconds>] [--stop-file <path>]`; graceful stop finalizes recordings |
| Builder changes | `build --assets_dir <dir>`; use throwaway output for smoke work and tracked assets only for intended regeneration |

Offline pipeline commands accept absolute `--assets_dir`, `--modules_dir`,
`--output_dir` and drain/join before exiting; do not hard-kill when the first artifact
appears. Capture runs until stopped. Capture stdout logs **and** stderr
`UMACAPTURE_RUN_SUMMARY`. Pipeline exits: 0 completed without terminal error,
1 threw/no usable verdict, 2 completed with terminal error. `build`/`screenshot`
return 0/1 only; their exit is not proof of correct pixels or recognition.
For pixel/geometry meaning use the [native overview](../native-recognition-backend.md).

## Shared-core web consequences

Only when the authorized change affects the existing shared web path, read the
[wasm build/repin manual](../../native/wasm/README.md). Use current digest roots/
exclusions from `tool/web_deps.json`; excluded-only edits owe no wasm rebuild.
Covered changes require actual rebuild, matching source digest/pins and same-tree
config, not a hand-edited digest pretending an old binary is fresh. A config field
whose meaning/unit changes must be renamed in that change. Run source drift checks
and report unavailable external wasm tooling rather than bypassing the gate.

The owner-approved local web command is `bash tool/build_web.sh --release --pwa-strategy=none`;
it checks pins/licenses. Current CI direct builds are compile-only exceptions for
its partially provisioned tree. This preserves existing consumers, not a requirement
to deliver Korean web support or deploy anything.
