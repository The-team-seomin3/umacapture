# Portable guidance migration audit

Issue: [#6](https://github.com/The-team-seomin3/umacapture/issues/6).
Audited source baseline: `develop` at `cc1c0d165f8739891cb33fe78641843d7e061691`,
2026-10-31. Inventory: **17 sources** (one project entry, eight rules, eight skill
entries). Every entry was read; classifications below apply to independent rules,
not a blanket verdict on a whole file. No `.claude/` file is modified by this change.

The owner requested a concise English, provider-neutral root guide that makes all
portable requirements discoverable without automatic Claude loading. The owner's
2026-10-31 implementation/PR request supersedes the earlier registration-only
readiness text. This delivery is guidance/audit only: no capture/model/JSON behavior,
fixtures, services, releases or Korean PoC/MVP implementation.

## Reading the matrix

**A** = portable always-applicable core (root states it; details may be routed).
**C** = portable conditional/detailed requirement (root routes to neutral owner).
**X** = provider/host-specific, obsolete example or explicitly superseded instruction.
Each target is the **owning neutral section**, not another required Claude read.
Existing native/wasm/test/harness manuals keep their technical detail. Source links
are provenance only. Future shared-rule edits belong at the neutral owner, with
legacy consumer alignment when relevant; do not maintain two full independent manuals.

## Coverage and exceptions

| Source | Independent rule group | Class | Target / treatment |
| --- | --- | --- | --- |
| [CLAUDE.md](../../.claude/CLAUDE.md) | English artifacts; localized strings exempt; user's chat language | A/X | [Root rules](../../AGENTS.md#rules-for-every-task); fixed Japanese assumption excluded as directed by #6 |
| CLAUDE.md | Fresh current-session binaries/output; rebuild after tree changes; provenance | A | Root rules; [build/run mechanics](operations.md#native-cli) |
| CLAUDE.md | FVM, `--force-jit`, manual codegen after annotations/packages; no tool implicitly generates | A/C | Root rules; [Dart](development.md#dart-and-flutter), [setup](operations.md#setup-and-build); MCP-specific negative capability generalized |
| CLAUDE.md | Existing layout, Riverpod/ref DI, central scrubbed logging, `expect`, Flex construction | A/C | Root core; [Dart](development.md#dart-and-flutter), [UI](development.md#ui-text-and-theme-gallery) |
| CLAUDE.md | Standard 120-column format, explicit paths, hook and blame setup | A/C | Root core; development Dart and operations setup |
| CLAUDE.md | All literal spellings, transparent/role-alpha exception, touched-line grandfathering, hook allowlist | A/C | Root core; development UI |
| CLAUDE.md | Current-only comments, no ignored/external links, touched-line grandfathering | A | Root rules; [Git derivation distinction](development.md#git-and-publication) |
| CLAUDE.md | Real pixels, falsifiable inspected evidence, nearest-neighbor, diagnostic path | A | Root rules; schematic accompaniment does not replace evidence |
| [git-workflow.md](../../.claude/rules/git-workflow.md) | Explicit commit/push, prepared branch, new branch base, PR to develop | A | Root rules; [Git](development.md#git-and-publication) |
| git-workflow.md | Conventional types/scope/summary and PR sections; multiline-message fidelity | C | Development Git; acting-agent attribution still applies |
| git-workflow.md | Generated EOL authority, scoped renormalization, excluded-path publication exception | C | Development Git; [material](contracts.md#test-material-and-evidence) |
| git-workflow.md | Bash-only tool syntax; branded Claude footer | X | Shell-appropriate file/stdin rule retained; provider footer omitted per owner requirement |
| [design-priorities.md](../../.claude/rules/design-priorities.md) | Correct representation, data over timing, parity before diff size, measured costs; warranted invariant directly asserted | A/C | Root rules; contracts shaping; [test proportionality](testing.md#proportionate-tests); option consequences precede size/cost |
| [platform-parity.md](../../.claude/rules/platform-parity.md) | Shared core; named constraints at divergence; live/offline snapshot/anchor/original-size/Gecko/FFV1 rules | A/C | Root core; [shared shaping](contracts.md#shared-frame-shaping) |
| platform-parity.md | CLI preview exception; five producers; no one-path shape drift | C | Contracts shaping; CLI lacks display, offline producers deliberately unshaped |
| platform-parity.md | Actual per-suite registry/conditional skips/coverage; Windows/browser gaps | A/C | Root warning; [per-case evidence](testing.md#per-case-evidence), [uncovered paths](testing.md#falsification-and-paths-outside-goldens); native test manual |
| [supported-scope.md](../../.claude/rules/supported-scope.md) | All platform/client/capture/input limits and web-lock accepted risks | A/C | Root support core; [full scope table](contracts.md#supported-scope), including Steam and Android video-only |
| supported-scope.md | Data/quarantine/crash/quota/old-record/concurrent-operation/user-script promises | C | Contracts scope table; unchanged accepted limits, external reads distinguished from writes |
| [test-material.md](../../.claude/rules/test-material.md) | No destructive material changes; named roles, calibration graduation, runs/history and evidence naming; scratch/build distinction | A/C | Root prohibition; [material table](contracts.md#test-material-and-evidence); grid route in testing |
| [writing-tests.md](../../.claude/rules/writing-tests.md) | Active proportionality rule, product harm readings, entry-driven representatives; defaults and permanent-harm exceptions | C | [Proportionate tests](testing.md#proportionate-tests); no invented numeric cap or mandatory redundant tests |
| writing-tests.md | Existing-file placement, waits/real I/O/gates, negative windows, heavy measurement/concurrency/split/name-set preservation | C | [Placement/waits](testing.md#placement-waits-and-execution-cost), existing settling helpers and test-selection authority |
| [ui-places-and-roles.md](../../.claude/rules/ui-places-and-roles.md) | New-location approval, existing role/detail, minimal text/style, no persisted explanation-only data | C | [UI and gallery](development.md#ui-text-and-theme-gallery) |
| [flutter-ai-rules.md](../../.claude/rules/flutter-ai-rules.md) | Layers/SOLID/state distinction, naming, concision, null safety/async/errors/logging, pure builds/performance/composition | C | [Dart](development.md#dart-and-flutter), compatible principles rephrased rather than vendored-body duplication |
| flutter-ai-rules.md | Custom Material appearance/light-dark/type/layout/tokens, accessibility | C | Development UI; target-platform checks, no new mobile product scope |
| flutter-ai-rules.md | AAA, fakes/sparing mocks, widget/E2E test intent | C | Testing proportionality plus retained guidance below; no Mockito dependency mandate |
| flutter-ai-rules.md | Persona, exact MCP tool names and their mandatory invocation | X | Use available equivalent pinned format/analyze/package/test tools, preserving actual checks; persona/tool availability not portable |
| [native-cli-dev/SKILL.md](../../.claude/skills/native-cli-dev/SKILL.md) | MSVC/Ninja/setup, dependency layouts, process-local env, shell/path/cache/header-dependency traps | C | [Setup](operations.md#setup-and-build), [native CLI](operations.md#native-cli) |
| native-cli-dev/SKILL.md | Cwd/options/subcommands, fresh generated config, smoke destination, drain/graceful stop, exits/summary/logging/debug | C | Operations CLI; existing [builder](../native-recognition-backend.md#builder-workflow) / native test manuals reused |
| native-cli-dev/SKILL.md | Live/offline differences, pre-shaping FFV1, legacy replay, private old input availability | C/X | Contracts shaping and operations CLI; old machine paths/UUIDs are examples, no checkout-fixture claim |
| native-cli-dev/SKILL.md | Permission to run an old prebuilt CLion exe | X | Superseded by confirmed fresh-session rebuild requirement; no stale-output exception imported |
| [native-change-verification/SKILL.md](../../.claude/skills/native-change-verification/SKILL.md) | Resize band/fire point/geometry evidence, nominal 540 floor and excluded upscale/tiny-input work | C | [Resize](testing.md#resize-band-and-supported-floor), source constants remain authority |
| native-change-verification/SKILL.md | Fresh Release ctest, per-case registration/skip reasons/high-water semantics, approved golden changes | C | [Per-case evidence](testing.md#per-case-evidence), native test manual; no historic count as contract |
| native-change-verification/SKILL.md | Eleven-rung mapping, explicit band, leaf comparisons, 109-leaf exception, no quality sweeps | C | [Encode/scale grid](testing.md#encode-and-scale-grid); historical measurements identified |
| native-change-verification/SKILL.md | Five switch cases, verdict vs discard/loss counts, sole end-of-input cover | C | [Switch checks](testing.md#switch-loss-and-end-of-input-checks) and current manifest assertions |
| native-change-verification/SKILL.md | Falsification/named failures/byte restore, uncovered Windows/browser paths, partial-import text test, timing/baselines | C | [Falsification/gaps](testing.md#falsification-and-paths-outside-goldens), live harness manual |
| native-change-verification/SKILL.md | Wasm digest exclusions vs true rebuild, same-tree config/key-unit rename, per-state builds/link safety | C | [Coupling](testing.md#source-wasm-and-generated-config-coupling), existing wasm manual |
| [pre-pr-test/SKILL.md](../../.claude/skills/pre-pr-test/SKILL.md) | Explicit once-only trigger, union stage selection, command order/results, coverage semantics | C | [Final check](pre-pr.md), CI and test selection; no automatic invocation from PR creation |
| pre-pr-test/SKILL.md | GUI run permission/preflight/seriality, driver/player freshness, scenario/code/status/retry/falsification/report/gaps | C | [Live stages](pre-pr.md#live-harness-stages-4-and-5), existing harness scenario tables; tool-specific background APIs generalized |
| pre-pr-test/SKILL.md | Direct local web build in stage 1.7 | X/C | Owner-resolved wrapper rule below; CI compile-only exception preserved |
| [project-setup/SKILL.md](../../.claude/skills/project-setup/SKILL.md) | Prerequisite check/no unprompted host installs, ordered project setup, dependency pin/cache coupling, poisoned install cache | C | [Setup](operations.md#setup-and-build); external cache writes surfaced when relevant |
| project-setup/SKILL.md | Broad "app Windows-only" wording; prior machine versions/availability | X | Windows desktop/native **toolchain** only; current supported web workflow retained, pins read from config |
| [release/SKILL.md](../../.claude/skills/release/SKILL.md) | Preflight/tool pins/credential presence, full derived codegen output set, web/license gate, PR merge-commit/tag/package/latest flow | C | [Release](maintenance.md#release), [web gate](operations.md#web-builds-and-pins); upstream publication target explicitly visible |
| release/SKILL.md | Matching PDB+PE symbols, read-back, version asset, web sourcemap injection/exact deployed tree | C | Maintenance release; existing upload scripts retain implementation authority |
| release/SKILL.md | Claude trailers/footer, bare authentication assumption, automatic install/reactivation/deletion/merge examples | X/C | No provider identity import; no credential fallback/secret display; host/external actions retain explicit authority, phase instructions do not grant permission |
| [sentry-issues/SKILL.md](../../.claude/skills/sentry-issues/SKILL.md) | Production/latest-release scope, optional widening, read scopes/helper/queries/raw payload handling | C | [Diagnostics](maintenance.md#sentry-diagnostics); standalone script is usable without provider host |
| sentry-issues/SKILL.md | Trust/unwind vs symbol names, old-version stamping, retention and accepted plugin-symbol gaps | C/X | Maintenance diagnostics; service state is source-reported historical evidence, token write scope and installed parsers are not assumed |
| [theme-gallery-refresh/SKILL.md](../../.claude/skills/theme-gallery-refresh/SKILL.md) | Any-UI trigger, three snapshots vs live sections, real-use descriptions/blends, verification/light-dark presentation | C | [UI/gallery](development.md#ui-text-and-theme-gallery); optional standalone scanner/manual equivalent, no skill loader or silent user-process kill |
| [flutter-ai-rules-sync/SKILL.md](../../.claude/skills/flutter-ai-rules-sync/SKILL.md) | On-request fetch/variants/provenance, fresh conflict survey/prune-not-annotate, no manual vendored edits, reporting | C | [Upstream refresh](maintenance.md#refreshing-vendored-flutter-guidance); compatible non-conflicts and current project authority retained |
| flutter-ai-rules-sync/SKILL.md | Claude auto-load/global-file/tool assumptions | X | Provider hosting omitted; active applicable user/project conventions still consulted |

Retained test-style details from the vendored guidance: use Arrange-Act-Assert;
prefer fakes and use mocks sparingly; widget tests use `flutter_test`, E2E uses
`integration_test` where appropriate under proportionality. This does not create
an unconditional new test obligation. The owning location is [testing](testing.md#proportionate-tests).

## Resolved and excluded instructions

- **Owner decision 2026-10-31:** local web builds, including final pre-PR stage 1.7,
  use `tool/build_web.sh`; existing CI direct builds remain compile-only exceptions.
  [Published decision](https://github.com/The-team-seomin3/umacapture/issues/6#issuecomment-6526474407).
  This supersedes the local direct-build command in pre-pr-test, which conflicts
  with release's "Never run flutter build web directly". The legacy files and CI
  are deliberately retained, not silently edited.
- #6 explicitly excludes fixed Japanese chat language, provider persona/tool names
  and the Claude PR footer. English repository artifacts/localization remain intact.
- Fresh-session build prohibition is explicit in CLAUDE.md and owner-confirmed #6;
  old CLion binary-reuse examples cannot waive it. Historical paths, UUIDs, tool
  versions/timings and "already installed" assertions are not current-host facts.
- Windows-only setup/native build text does not repeal supported-scope's web app;
  the current CMake desktop path and wasm/manual/CI distinguish those contexts.
- Broad "anything" final-suite defaults yield to its specific documentation-only
  row. An invariant needs direct assertion **when a guard is warranted**; test
  proportionality/permanent-harm exceptions decide whether and how heavy it is.
- Normal targeted verification uses non-focus-stealing instrumentation where feasible;
  the explicit final suite's visible app/player requires its separate run permission.
  Neither procedure silently authorizes killing a user's process or changing host tools.

No unresolved material project-policy disagreement remains in this migration.

## Navigation and validation contract

Check local links/anchors and every concrete route against the actual tree; compare
source inventory to this matrix. Validate #2 capture through discovery/recorder/CLI
and platform targets; #3 through scene completion, prefix/full-list distinction,
models/builders and native tests; #4 through native/Dart factor and exporter contracts;
#5 by combining those routes without assuming a factor-only completed record.
On 2026-10-31 an ad-hoc read-only Node check passed for all eight new documents:
112 local links/anchors, all 17 inventoried sources, 21 concrete navigation paths
across capture/factors/JSON/verification, and ten named entry symbols. The root
entry is approximately 1,000 words; detailed procedures are selectively routed.
Targeted source inspection confirmed screenshot has no recognition event loop,
`SceneScrapingBox::ready` still requires non-factor tabs, factor stars are 1-based,
and `JsonExporter` wraps whole records with labels. These are navigation/source
checks, not game/model/runtime verification or a second agent's independent review.
The PR records final scope/whitespace checks and per-criterion acceptance. No input-token savings
percentage is claimed. Real Korean capture, model accuracy, builds and full end-to-end
runtime behavior are outside this documentation delivery and are not reported as passed.
