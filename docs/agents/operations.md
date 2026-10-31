# Build and run the PoC tooling

## Setup and build

Start with the [current workflow and delivery status](../implementation-status.md).
For #5 reuse authorized saved capture/record/geometry and pinned OCR/master/module
inputs; native capture changes or live game access are not required for this offline
path. Its uncommitted tool and README are reached through the issue handoff, not an
absent file in this baseline. The commands below describe existing native tooling,
not a Korean postprocessor installation procedure.

Check inputs for the actual task. Source inspection can proceed without runtime
access; missing tools or data are Not Tested, not permission to install or fabricate
them. The current owner boundary excludes agent-direct game capture/control and
anti-cheat probing; existing live CLI commands do not override it.

Native CLI builds require Windows MSVC/CMake/Ninja and provisioned OpenCV/ONNX/FFmpeg.
Use [tool/fetch_deps.py](../../tool/fetch_deps.py) for current hash-pinned dependency
layout and [native/CMakeLists.txt](../../native/CMakeLists.txt) for target requirements.
Do not assume this host has them or install host tools unprompted. Python tooling
uses `uv run`. For Dart changes use `.fvmrc`'s SDK at `.fvm/flutter_sdk/bin/`:
packages before codegen, then `dart run build_runner build --force-jit` (`.bat` on
Windows). Keep generated EOL handling in `.gitattributes`; no whole-tree formatting
or normalization. Existing Git hooks remain applicable; do not bypass failed checks.

## Existing CI action allowlist

The existing workflows use GitHub-authored actions plus these external references:

```text
ilammy/msvc-dev-cmd@v1
astral-sh/setup-uv@v10.3.3
subosito/flutter-action@v2
```

For a selected-actions repository policy, allow GitHub-authored actions and these
exact references. `setup-uv` has no `v10` major shorthand at this update; the
published `v10.3.3` tag is used in both CI and the provisioning composite actions.
Allowlist version patterns match the concrete reference: `@v10` does not permit
`@v10.3.3`. After correcting a blocked-action policy, a run that failed before
job creation may not be retryable; a new applicable PR event is then required.
The v10 action uses Node 24 on the existing GitHub-hosted `windows-2022` runners.
Provisioning steps retain `enable-cache: false`; the unconditional native setup
keeps upstream defaults (v9 changed default cache pruning to false, and v10 changes
automatic caching for sensitive events). Current triggers are `pull_request` and
`push`; runtime behavior still needs an actual workflow run.

A listed workflow state of `active` does not prove repository Actions activation
or a successful run. Repository/organization policy and fork activation are
separate from source configuration. Keep token and branch-check permissions
unchanged; do not weaken them to obtain a passing check.

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
| Separately authorized raw screenshot investigation | `screenshot --output <private.png>`; inspect actual full pixels and save outcome, no recognition loop |
| #3 recorded input | `video --video_path_list <clip>`; or `replay --record <ffv1.mkv>` for full recorded frames |
| #3 isolated pipeline stages | `stitch --id <uuid>`, `recognize --id <uuid>`; use isolated record copies, since predictions are rewritten |
| Separately owner-authorized live investigation | `capture [--record <private.mkv>] [--duration <seconds>] [--stop-file <path>]`; graceful stop finalizes recordings |
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
