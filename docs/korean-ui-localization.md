# Korean application UI

Issue: https://github.com/The-team-seomin3/umacapture/issues/10

Source localization was merged in [PR #12](https://github.com/The-team-seomin3/umacapture/pull/12).
See [implementation status](implementation-status.md) for the distinction between
merged UI code, local Windows packaging and remaining native acceptance.

## Startup and resources

Windows desktop starts in Korean. Both the normal application and the app-instance
waiting surface use `AppLocalization`; saved Japanese preferences cannot override
this policy. Other platforms start in Japanese. Japanese remains the fallback
resource. There is no runtime language picker.

`assets/translations/ko.json` mirrors the Japanese key hierarchy. Preserve named
and positional placeholders, linked translation references, meaningful line breaks,
and intentional empty strings when maintaining either locale. Empty strings are
intentional omissions, not missing translations. The addon copy-placeholder hint
uses a localized bracketed example; its caller supplies no named argument. The Japanese resource is unchanged.
Translate the approved semantics in [wording decisions](wording-decisions.md),
including quarantine contents, recovery outcomes and capture retry instructions.

The Korean theme and waiting screen use bundled Nanum Gothic 400/700/800, selected
by the owner on 2026-10-31. The unmodified official font files and SIL OFL license
are included; source provenance is in assets/fonts/nanum_gothic/SOURCE.md. Japanese
keeps its existing theme. The toast close action uses Flutter's
Material localization. Filled-toast text/icons/dismissal choose a contrasting
foreground from existing theme roles; all four types in light/dark have regression
coverage for at least 4.5:1 contrast. The missing-file hint in record reports uses the existing
localized missing-file sentence. Product names, developer-only theme gallery text
and unused dummy-page text are retained. Navigation labels resolve when read so they cannot retain
a previous localization table.

Recognition modules, game names/data supplied by modules, external news/Markdown,
and license originals keep their upstream content. UI translation does not provide
Korean game recognition or a Windows release package.

## Verification and packaging handoff

With the SDK pinned by `.fvmrc` provisioned in the dedicated worktree:

```powershell
.fvm/flutter_sdk/bin/flutter.bat test test/korean_localization_test.dart test/app_instance_startup_test.dart test/app_navigation_surfaces_test.dart
.fvm/flutter_sdk/bin/flutter.bat analyze --no-fatal-infos
```

The Korean suite checks key/placeholder/blank/newline parity, platform policy,
saved Japanese preference override, waiting text and narrow navigation. Existing
Japanese wording tests keep their Japanese default. CI runs the normal unit/widget,
static and browser checks against the PR source.

Before final Windows packaging, build from the reviewed source and inspect light
and dark themes at normal and narrow widths: navigation, capture controls, record
management, settings, notifications, delete confirmations and error dialogs. Check
Hangul glyphs, wrapping, truncation and button reachability. A widget test does not
prove Windows font rendering or complete page layout.

Local validation on 2026-10-31 used Flutter 3.44.4 / Dart 3.12.2, installed
from the official Windows archive after SHA-256 verification. The user-level SDK
can be shared across dedicated worktrees; connect each worktree's ignored
`.fvm/flutter_sdk` to that same SDK version without upgrading it in place.

The three targeted test files above passed all 18 tests. Changed Dart files pass
120-column formatting. Full `flutter analyze --no-pub --no-fatal-infos` exits 0,
with eight pre-existing deprecated-member informational notices in other tests.
The startup widget test waits for real asset I/O and uses Flutter's Windows platform
variant, covering saved Japanese preferences before rendering Korean UI.

Resource checks passed for all 1,295 leaves (9 intentional blanks). Bundled Nanum
Gothic covers all 477 distinct Hangul syllables used in the translation. The opt-in
[visual harness](../tool/visual/README.md) rendered 60 real-font widget images in
light/dark at 1280x900 and 480x900; all had no framework layout errors and were
visually reviewed. See the [image report](validation/korean-ui-preview/README.md).
The review exposed and corrected toast foreground contrast and missing Korean
spacing before a settings link. Local contrast/Korean/storage tests pass 52/52.

These previews are production-widget evidence with synthetic providers; their
historical [image report](validation/korean-ui-preview/README.md) remains unchanged.
They do not by themselves establish native Windows behavior.

## Subsequent native Windows evidence — 2026-10-31

The [initial #11 package result](https://github.com/The-team-seomin3/umacapture/issues/11#issuecomment-6541108516)
and [return handoff to #10](https://github.com/The-team-seomin3/umacapture/issues/10#issuecomment-6541112643)
report a fresh Release build from the historical pre-migration source `d2f69e6`
plus the CMake runtime-bundling fix. First-launch executable path/PID/hash and selected
Korean dashboard/capture/empty-record/settings/dialog states were verified.
That initial smoke used telemetry-deny fixtures; restart and narrow acceptance were
not tested at that time.

[PR #19's later integrated report](https://github.com/The-team-seomin3/umacapture/blob/39590f2778a040f3da42807775885e61caa43b14/docs/validation/windows-isolation-integration-2026-10-31.md)
supersedes those restart/narrow gaps for its tested source: the complete #15-isolated
Release ZIP was extracted, launched and normally restarted with EXE/AOT provenance
and fixture preservation checks. Selected native Korean navigation/stopped-capture/
settings and disabled reporting/updater controls were inspected, including a requested
640x700 window and light/dark settings. Required first-run Japanese modules downloaded
and installed. This is bounded native execution evidence, separate from the widget
preview matrix; it is not a Korean game-recognition test.

Full page/dialog/DPI, populated-record/game workflows and native accessibility/
keyboard acceptance remain incomplete. Accessibility inspection logged AXTree errors;
the report records that limitation. No game capture or real user-record workflow
was exercised. App-PID TCP observations are bounded and do not establish a complete
network audit. Later #18 test-only corrections do not become new binary evidence.

#10/#11 remain open for their acceptance remainder. #18's source isolation is merged;
#19's packaging changes remain in an open PR. #19 publishes instructions and reports;
the ZIP remains
local and no public fork binary release is established. Use each current PR for
its HEAD/check status, and the pinned reports for historical execution evidence.
