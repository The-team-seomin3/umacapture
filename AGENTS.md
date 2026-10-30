# Korean factor PoC and MVP guidance

This entry supports the Korean Kakao Games Windows Hall-of-Fame factor workflow:
raw capture [#2](https://github.com/The-team-seomin3/umacapture/issues/2), factor
coverage/recognition [#3](https://github.com/The-team-seomin3/umacapture/issues/3),
existing JSON compatibility [#4](https://github.com/The-team-seomin3/umacapture/issues/4),
then the staged factor-to-JSON [MVP #5](https://github.com/The-team-seomin3/umacapture/issues/5).
Read the relevant issue and latest comments first; task publication and research
assignments do not themselves authorize product implementation. Continue work
already authorized by the owner; stop only affected unapproved scope or decisions.

## Working rules

- Converse in the user's language; repository artifacts are English, except localized
  runtime strings. Use the prepared task branch and PR to `develop`; no direct
  `develop` commits/pushes. Commit/push only when requested, including a requested PR.
- Inspect symbols, callers and matching tests progressively. Read the C++ builders
  before generated layout JSON; inspect disputed generated fields when needed.
  A PR review starts with the exact diff and affected contracts, not a merge decision.
- Build any binary used for execution/measurement in this session from the current
  tree; rebuild after source/tree changes and confirm actual compile/link provenance.
  Never diagnose from an old executable or its output. Check tools/inputs first;
  no unprompted host installation, service access, evidence upload or game automation.
- Preserve existing Japanese DMM/Steam capture and existing stored/exported data.
  Shared recognition changes belong in `native/src/`; verify applicable existing
  Windows/web/CLI paths without expanding Korean MVP support to other platforms.
- Never delete, move, truncate, rename or re-encode `testdata/` without an explicit
  instruction naming the material. `.notes/` is scratch, never the sole durable
  evidence or test dependency. Keep raw game/account material private.
- Use the FVM SDK pinned by `.fvmrc`. After annotated Dart/codegen-package changes,
  run `.fvm/flutter_sdk/bin/dart run build_runner build --force-jit` (`.bat` on Windows).
  Format explicit source paths at the configured 120-column width, never `dart format .`.
  If Dart changes, follow existing `lib/src/`, Riverpod/ref, central `logger`, theme
  roles and `expect` conventions. Comments describe current behavior and point only
  to checked-in repository material; do not introduce unrelated UI or refactors.
- Separate source facts, real execution, inference and unknowns. Missing inputs or
  skipped tests are not passes. Show inspected real pixels when claiming capture
  or recognition evidence; use nearest-neighbor magnification for pixel checks.

## Find the needed document

| Need | Read next |
| --- | --- |
| Scope, factor/JSON boundaries, preserving shared paths | [Contracts](docs/agents/contracts.md#scope-and-contracts) |
| Consume or publish PoC research; decide whether to delegate | [Research handoffs](docs/agents/contracts.md#research-handoffs) |
| Build and run screenshot/video/recognition tooling | [Setup and CLI](docs/agents/operations.md#setup-and-build) |
| Validate the changed behavior and report actual coverage | [Targeted verification](docs/agents/testing.md#native-verification) |
| Understand pipeline, coordinates and generated layout | [Existing native overview](docs/native-recognition-backend.md) |

## Find the code for the issue

| Task | First files and symbols |
| --- | --- |
| #2: identify window and save full pixels | [window_capturer.h](windows/runner/window_capturer.h) (`findWindow`), [window_recorder.h](windows/runner/window_recorder.h) (`takeScreenshot`), [cli.cpp](native/src/core/cli.cpp) (`screenshotFromScreen`), [platform.json](assets/config/platform.json) |
| #3: scroll coverage, completion and factor recognition | [native_api.cpp](native/src/core/native_api.cpp); [scene scraper](native/src/chara_detail/chara_detail_scene_scraper.cpp) (`SceneScrapingBox::ready`); [stitcher](native/src/chara_detail/chara_detail_scene_stitcher.cpp); [recognizer](native/src/chara_detail/chara_detail_recognizer.cpp) (`FactorRowReader`, `visibleSelfPrefix`, `FactorTabRecognizer`); [builders](native/tool/builder) |
| #3: actual ONNX model wiring | [model.h](native/src/cv/model.h), [recognizer model factory](native/src/chara_detail/chara_detail_recognizer_models.cpp), recognizer builder/config; model inputs `factor` and `factor_rank` |
| #4: existing producer and consumer JSON | [native record](native/src/chara_detail/chara_detail_record.h), [Dart record](lib/src/chara_detail/chara_detail_record.dart), [exporter](lib/src/chara_detail/exporter.dart) (`JsonExportData`, `JsonExporter`) |
| #5: integrate only evidence-backed stages | Combine the above routes and [issue #5](https://github.com/The-team-seomin3/umacapture/issues/5); static #4 investigation need not wait for screenshots |
| Relevant tests and runtime limits | [native factor tests](native/test/chara_detail), [integration manifest](native/test/integration/cases.json), [native test manual](native/test/README.md), matching [Dart tests](test) |

These instructions cover this PoC/MVP work, not a general maintenance workflow.
Existing technical manuals supply their own detail; current source/config owns
pins and generated outputs. No Claude loader or skill installation is required.
