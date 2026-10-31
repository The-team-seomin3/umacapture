# Korean application UI

Issue: https://github.com/The-team-seomin3/umacapture/issues/10

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

The Korean theme uses Windows' built-in Malgun Gothic, including the waiting
screen; Japanese keeps its existing theme. The toast close action uses Flutter's
Material localization. The missing-file hint in record reports uses the existing
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

Local status on 2026-10-31: the pinned SDK and Flutter/FVM commands were unavailable,
so local Flutter tests, formatter, analyzer and Windows visual checks were Not Tested.
Resource checks passed for all 1,295 leaves (9 intentional blanks). The installed
Malgun Gothic cmap covers all 477 distinct Hangul syllables used in the translation;
this proves glyph availability, not rendered layout. Use the PR checks for current CI results;
no Windows binary or ZIP is delivered by this issue. Keep the issue open until the
remaining UI validation is recorded.
