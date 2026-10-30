# Repository guidance for coding agents

## Start here

umacapture extracts Japanese Umamusume character-detail records from images, without
interfering with the game. Flutter/Dart owns the UI, records and export; shared C++
owns capture-frame geometry, scraping, stitching and recognition, including the wasm
core used by web. See the [native overview](docs/native-recognition-backend.md).

Read the issue, current owner decisions and affected contracts before editing. Locate
symbols/callers, read relevant spans and tests, then expand for cross-platform effects
and counter-evidence. Prefer `native/tool/builder/` to whole generated layout JSON
files; inspect disputed generated fields when needed. Avoid routine vendor/unrelated
platform dumps, but inspect them when evidence requires it. For PR reviews start from
the exact diff and check affected contracts, callers, tests and decisions; a review
is advice, not merge permission. Do not trade verification for context savings.

## Rules for every task

- Converse in the user's language. Code, comments, docs, commits, issues and PRs are
  English; localized runtime strings follow the app's localization.
- Commit or push only on the user's explicit request (a requested implementation PR
  includes its publication). Never commit/push directly to `develop`; PRs target
  `develop`. Use the prepared non-`develop` branch; create a branch only from
  `develop` or when requested, based on the checked-out branch unless told otherwise.
  See [Git details](docs/agents/development.md#git-and-publication).
- **Build every executable/output used for running, measuring or diagnosis in the
  current session from the current tree.** Rebuild after source changes, checkout,
  pull, stash or branch switches. Do not trust old CLI/app/wasm binaries or outputs
  emitted by them. Check actual compilation/linking and provenance, not exit 0 alone.
- Check prerequisites; do not install/upgrade host tools or access/publish to external
  services without authorization. Machine paths and historical measurements are
  examples, never proof of this machine's toolchains, models or test inputs.
- Prefer correct representation and platform parity before diff size. Represent
  dependencies as data; measure call-site costs before claiming risk. Once a guard
  is warranted, assert its invariant directly; do not add duplicate tests. Explain
  necessary platform constraints at the divergence in code.
- Preserve Windows x64 and web workflows and Japanese **DMM and Steam** clients.
  Shared recognition/shaping belongs in `native/src/`. Follow the intentional live
  versus offline producer differences in [contracts](docs/agents/contracts.md).
  Korean capture/factor/JSON issues do not by themselves expand supported scope.
- **Never delete, move, truncate, rename or re-encode `testdata/` material without
  an explicit instruction naming it.** Do not empty harness run history. `.notes/`
  is disposable scratch, never a dependency of tests or shipped code.
- Use the FVM SDK at `.fvm/flutter_sdk/bin/{flutter,dart}` (`.bat` on Windows), pinned
  by `.fvmrc`. After annotated-source/codegen-package changes run
  `.fvm/flutter_sdk/bin/dart run build_runner build --force-jit`; do not assume a
  tool or package resolver regenerates outputs. Format explicit paths only, never
  `dart format .`; the configured width is 120 and `testdata/` must be preserved.
- Dart uses the existing `lib/src/` areas, Riverpod 3 providers/`ref` for state/DI,
  `logger` from `lib/src/core/app_logger.dart`, and `expect` assertions. New colors
  come from theme roles/extensions, not literals (except `Colors.transparent`).
  See [Dart and UI conventions](docs/agents/development.md#dart-and-flutter).
- New comments describe current behavior, not change history, and must not point
  outside the checked-in repository (including ignored paths or external URLs).
  Existing violations are grandfathered until their lines are touched.
- When asked to visualize an artifact as evidence, show and inspect its real pixels;
  correct claims they contradict. Schematics may accompany, never replace, evidence.
  Magnify with nearest-neighbor for pixel work; save diagnostic images under
  `.notes/analysis/<topic>/` and give the user the path.
- Report actual tests, skips and missing coverage. A skipped golden is not a pass;
  CLI goldens do not prove Windows GPU capture or browser behavior. Read
  [testing](docs/agents/testing.md) before designing tests or verifying native changes.

## Load the reference for the task

| Task | Required reading / first files |
| --- | --- |
| Setup, native CLI build/run/debug, generated layout updates | [Operations](docs/agents/operations.md#setup-and-build); [builder workflow](docs/native-recognition-backend.md#builder-workflow) |
| Supported inputs, persisted-data risks, producer shaping, test material | [Contracts and material](docs/agents/contracts.md) |
| Test changes; native recognition/capture verification | [Testing](docs/agents/testing.md); [native test manual](native/test/README.md); [live harness](docs/live-capture-harness.md) where applicable |
| UI/text/theme changes | [UI and gallery](docs/agents/development.md#ui-text-and-theme-gallery); refresh gallery after any UI change under `lib/` |
| Final pre-PR suite explicitly requested by the user | [Final check](docs/agents/pre-pr.md); creation of a PR alone does not trigger this suite |
| Local web builds / wasm pin changes | [Operations](docs/agents/operations.md#web-builds-and-pins); [wasm manual](native/wasm/README.md) |
| Release, Sentry diagnostics, upstream-rule refresh | Relevant [maintenance procedure](docs/agents/maintenance.md); these routes grant no external-action authority |

## Navigation for capture, factors and JSON

| Concern | Start here; expand along callers and matching tests |
| --- | --- |
| Window discovery / Korean capture PoC #2 | `windows/runner/window_capturer.h` (`findWindow`), `window_recorder.h` in the same directory; `native/src/core/cli.cpp` (`screenshotFromScreen`); `assets/config/platform.json` |
| Scene/tab completion, scroll, stitch / factor PoC #3 | `native/src/core/native_api.cpp`; `native/src/chara_detail/chara_detail_scene_{context,scraper,stitcher}.cpp`; `native/tool/builder/` |
| Factor names, ranks and model wiring | `native/src/chara_detail/chara_detail_recognizer.cpp` (`FactorRowReader`, `FactorTabRecognizer`); `chara_detail_recognizer_models.cpp` in the same directory; `native/src/cv/model.h`; recognizer builder/config |
| JSON contract PoC #4 | `native/src/chara_detail/chara_detail_record.h`; `lib/src/chara_detail/chara_detail_record.dart`; `lib/src/chara_detail/exporter.dart` (`JsonExportData`, `JsonExporter`) |
| Staged factor-only MVP #5 | Combine the above routes; read `SceneScrapingBox::ready`, `CharaDetailRecognizer::recognize`, and actual export consumers before proposing a factor-only path |
| Verification | `native/test/chara_detail/`, `native/test/integration/cases.json`, `native/test/README.md`, matching `test/` Dart suites; real Windows/browser checks when the change reaches those paths |

A screenshot or `visibleSelfPrefix` is not a complete factor list. `FactorSet`
contains `self`/`parent1`/`parent2` with `id` and 1-based `star`; the JSON exporter
contains whole records plus labels, not an assumed standalone factor document.
Do not fabricate missing full-record fields. Investigate and obtain any necessary
consumer/scope decision under the actual authorized issue.

## Guidance ownership

This entry and the linked neutral references own the migrated portable requirements.
Existing architecture/test/manual documents retain their technical detail; current
source/config owns pins, generated outputs and registries. No Claude loader or skill
installation is required. Historical `.claude/` instructions are retained intact;
[migration coverage and explicit exceptions](docs/agents/migration-audit.md) record
provenance and the owner-resolved command conflict. Update the neutral owning section
when a shared invariant changes; keep historical consumer guidance aligned as needed
without creating another full parallel manual. Escalate unresolved material policy
conflicts rather than silently choosing a new rule.
