# Supported contracts and local material

This is the portable authority for the supported-scope, producer-parity and material
requirements migrated in [the audit](migration-audit.md). Rate findings against
these promises; unsupported input is not a defect unless it destroys protected data.
An issue proposal does not silently change these promises.

## Supported scope

| Area | Promise and intentional limits |
| --- | --- |
| Windows | x86-64 desktop app, one instance per session via the single-instance mutex |
| Web | One tab per origin via a page-lifetime Web Lock; a second waits for the first to close. Requires wasm SIMD, `SharedArrayBuffer` and cross-origin isolation; otherwise the worker refuses the session. Desktop Chromium/Firefox are normal. Android Chrome is supported for video import only. iOS is unmeasured/not promised; embedded chat-client browsers cannot nest workers and are not promised |
| Web accepted limits | Without `navigator.locks`, multiple tabs are not excluded and settings are last-write-wins. A pre-lock older build is not excluded across an update |
| Game / CLI | Japanese DMM **and Steam** Windows clients. CLI is a developer tool; its output/golden suite is a promise to developers |
| Capture | Portrait window, landscape window, full screen and web screen share must not regress. Below 540 px is not promised; upscaling is best-effort rescue, not a verification target |
| Video | H.264 in MP4. Refuse other codecs/containers with a stated reason. A clip whose every frame reports zero is unsupported. Windows, desktop web and Android Chrome web import are supported |
| Data directory | App is the only writer. External reads are normal (add-on programs receive IDs/paths); external writes, synced folders, other volumes, UNC paths, OS locks and a directory shared between accounts are not promised |
| Damaged records / crash | Quarantine unreadable/half-written records, never delete them. On crash/power loss the in-flight record may be lost, listed records survive, and damaged records are quarantined |
| Full disk / browser quota | A failed write under exhausted disk/OPFS/IndexedDB quota is not promised, but must not destroy listed records or their saved ratings/memos |
| Old records | Before the module's minimum recognition date: viewing, export, deletion and merge remain normal. Re-recognition is a warned long-press rescue, not a verification target |
| Concurrent UI operations | Overlap is normal; refuse while busy. A timing window a person cannot aim for is coincidental reachability |
| User-authored tasks/scripts | Manual-documented runtime semantics, responsiveness and displayed errors are promised. Script/task correctness and external program behavior are not. See [add-ons](../addon-manual.md) and [script columns](../script-column-manual.md) |

## Shared frame shaping

Windows, web and CLI front ends feed one C++ recognition pipeline. Put shared
behavior in `native/src/`, also compiled to wasm; hand-porting logic into Dart or
`web/worker.js` is a last resort. Keep capture/frame shaping converged and explain
each necessary divergence **at its implementation** with the concrete platform
constraint. Refer to symbols, not stale line numbers: `platformConfigLoader` and
`frameResizeConfig` in `lib/src/core/platform_controller.dart` illustrate shared
configuration authority. Correct representation/parity ranks ahead of diff size;
an unexplained omission on one platform is a gap.

| Producer | Deliberate contract |
| --- | --- |
| Windows live (`windows/runner/window_capturer.h`) | Query shared pane shaping using full captured size; carry the resolved pane snapshot |
| Web live (`web/worker.js` into `native/wasm/wasm_api.cpp`) | Same; shared core plans browser-required copy alignment |
| `VideoLoader` (`native/src/cv/video_loader.h`) | Full decoded pixels, default anchor, **no pane snapshot**; used by CLI and Windows import driver |
| FFV1 replay (`native/src/cv/ffv1_reader.{h,cpp}`) | Full decoded raw pixels, default anchor, no snapshot; reproduce detection/calibration |
| Web video import (`web/video_import.mjs`, `pushOfflineFrame`) | Full decoded frame in its own pixel format; shared core converts color; default anchor, no snapshot |

Only the two live producers crop. Offline producer-side shaping would race the
consumer's latch and vary refused frames by scheduling; clip plus model set must
determine the result. `DetailCropTracker::beginFrame` applies the latched pane to
frames with no snapshot on the consumer side. Snapshot presence means the producer
already shaped the frame and its anchor must be preserved. Cropping and setting
or reanchoring the `Frame` to the pane intersection in the sent pixels are one
operation. A missing pane rect means send the full frame.

`NativeApi::updateFrame(frame, original_size)` receives the **pre-crop** captured
size, never the shaped size, or the latch may release/oscillate. Gecko's pixel-copy
rectangle may be outward-even-aligned only if it contains the pane and stays within
visible bounds; otherwise copy the full visible frame. The `Frame` anchor remains
the exact pane intersection relative to the actual copied origin. See
`outwardEvenCropRect` in `native/src/core/frame_shaping.h`. Pixel alignment must
not change recognition geometry.

Do not add crop, resize or normalization to just one applicable path. Record any
justified producer-specific constraint. `capture --record` tees **before** shaping:
FFV1 retains pixels/timestamps, not an anchor or format marker. Replay normally
recalibrates; `--no-calibrate` is a documented escape for indistinguishable legacy
recordings already cropped. CLI lacks preview because it has no display surface;
Windows method-channel/web worker UI can request it. That does not relax shaping
parity or anchor-relative downstream geometry.

## Test material and evidence

`testdata/` is ignored but irreplaceable, addressed by name from cases, sidecars
and harness scenarios. No deletion, movement, truncation, rename or re-encode
without explicit instruction naming the material, even after a task finishes.

| Location under `testdata/` | Role / preservation detail |
| --- | --- |
| `clips/golden/` | Real session input clips and live harness `*.stops.json` sidecars; most cannot be recorded again |
| `clips/ladder/` | Costly `_540w`/`_404w` threshold-calibration derivatives; not the regression grid |
| `clips/grid/` | Pristine `screen-20260802-214946.mp4` plus ten documented encode/scale derivatives; preserve pristine, re-derive a missing derivative before the grid using [the mapping](testing.md#encode-and-scale-grid), report it and never overwrite existing material |
| `clips/source/` | Primary recordings from which others were cut; cannot be re-derived |
| `clips/calibration/` | New constant-calibration sources; empty at migration baseline intentionally. `friend_standard_many_rental.mp4` graduated to `golden/`, backing scroll-guess veto half-width and `friend_common.viewport` in the scraper builder; move new calibration material to goldens only when a case asserts it |
| `models/` | Recognizer module sets retained for comparison |
| `harness/` | Isolated scratch app data root plus measurement history in `runs/`; **never empty `runs/`**, compare a new run with prior measurements. `firefox-live-capture/` holds a procedure/checklist and baseline measurements, not a past-measurement evidence entry |
| `evidence/` | Primary derivation material for shipped constants/thresholds/behavior, retained rather than left in disposable scratch |

`.notes/` is temporary analysis, probes and diagnostic images; it may be swept.
Nothing tests or shipped code depend on may live there. Promote a dependency into
`testdata/` (or the repo if small/stable). Evidence naming drops an `analysis/`
level: `.notes/analysis/<topic>/` or older `.notes/<topic>/` becomes
`testdata/evidence/<topic>/`; the reverse mapping has two possibilities.
Comments state derivations inline, without ignored paths. Commit/PR derivation
references have the narrow exception in [Git guidance](development.md#git-and-publication).
Disposable build outputs (`native/cmake-build-*`, `build/`) may be removed when
needed; verify exact targets and never recursively follow dependency junctions.
