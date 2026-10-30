# Development conventions

This document owns portable Git, Dart and UI conventions, reached from [AGENTS.md](../../AGENTS.md).

## Git and publication

Commit/push requires the user's explicit request. An implementation PR request
covers its scoped commits/push/publication; it does not authorize merge, release,
branch deletion or an unrelated action. Never commit or push directly to `develop`.
Use an already prepared non-`develop` branch. Create a branch only while on
`develop` or when explicitly asked; base it on the checked-out branch unless the
owner specifies otherwise. Feature/fix branches land through PRs to `develop`.
Applicable agent identity/authentication policies still apply.

Commit and PR prose is English. Use Conventional Commits `type(scope): summary`:
`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`; scope is optional, kebab-case and names an area. Summary is lowercase,
imperative, without a trailing period. Apply any acting-agent attribution prefix.
PR bodies use `## Summary` (one or two sentences), `## What changed` (bold-led
bullets or numbered subsections) and `## Testing` (actual commands/results).
Add design, risk/scope or follow-up sections only when informative. Provide bodies
and multiline messages via files/stdin suitable for the actual shell, preserving
literal backticks and newlines. No provider-branded footer is required.

Read `.gitattributes` for generated-output `eol=lf` entries; add new generated
outputs there instead of committing EOL churn. Do not broadly run
`git add --renormalize .`; limit any normalization to intended paths and review
the staged set. Do not rewind a working tree with path checkout/restore/stash
when testing or restoring probes: keep byte copies and restore those exactly.

Do not cite excluded/local-only paths in commits or PR bodies; state the rationale
inline. The sole project exception is `testdata/evidence/<topic>/` as the derivation
source of a shipped constant, threshold or behavior: explain the value and reasoning
in prose as well, since a reader may not have that material. Scratch notes and
host-private paths are not publication references. Code comments have **no** such
exception: they state the fact inline and point only to checked-in material.

## Design choices

When presenting options, lead with what each leaves represented, which future
changes would break it, and what is merely implied by timing/order/global state.
Correct representation and parity decide before size/effort. State measured costs
afterward; count affected callers before claiming a shared change is risky. A
platform constraint must be named at the divergence, rather than using omitted
behavior as a cost-saving option. Warranted invariant tests assert the invariant,
with proportionality deciding whether a guard is needed at all.

## Dart and Flutter

The layout is `lib/main.dart` and `lib/src/{app,core,gui,chara_detail,preference,addon}`,
not a new `lib/features/`. Separate presentation, logic and data responsibilities;
apply SOLID within the established architecture. Distinguish ephemeral widget state
from app state. Riverpod 3 providers and `ref` own app state and DI, not manual
constructor-passing or `ChangeNotifier`. The latter's existing widget notification
channel in `lib/src/chara_detail/spec/base.dart` is an intentional different use.
Routing/serialization follow `auto_route`/`dart_mappable`, not competing packages.
Explain a dependency's need and inspect `pubspec.yaml` before adding it.

Use `PascalCase` for types, `camelCase` for members and `snake_case` filenames.
Keep functions concise (the retained upstream guideline is under 20 lines), do not introduce
the `!` operator: use null checks/flow analysis instead. Use `async`/`await` for
futures and catch errors with `try`/`catch`.
Keep build methods pure, fast and free of network calls/side effects; use `compute`
for heavy work such as JSON parsing, lazy list/sliver builders for long lists,
`const` constructors where valid and small `StatelessWidget` classes to compose
complex UI. Explain language features to the user when helpful, not as a persona.

Diagnostics use `logger` in `lib/src/core/app_logger.dart`, never `print` or
`dart:developer.log`. That shared route supplies Sentry breadcrumbs for every
`d/i/w/e/wtf` line and scrubs filesystem paths (`<app>` / `<redacted>`).
Do not copy older logging exceptions. Tests assert with `expect` from
`flutter_test`/`package:test`; `package:checks` is not a dependency.

The FVM SDK and `--force-jit` codegen command are in the root guide. Run codegen
after changing annotated sources or introducing codegen packages; package-management
or analysis tools do not implicitly run it. Use standard `dart format`, width 120
from `analysis_options.yaml`, with explicit paths (`lib test tool` for a full
source-format check), never the repository root. Analyzer exclusions do not
protect files from the formatter. The pre-commit hook checks staged Dart format
and newly added color literals; setup enables it. `.git-blame-ignore-revs` records
the historical mechanical format change.

## UI text and theme gallery

Before adding explanatory text, identify the existing location's role and level
of detail. A **new location** needs user approval, including a tooltip where none
existed. Propose where, wording, why no existing location fits and implementation
cost. Text may be added to an existing location only after stating its role;
keep it minimal and at that role's concept/detail level. Main explanations use
body styling; supplementary-hint styling belongs to hints. Do not persist data
solely to select an explanation: derive it from existing data, or ask whether the
distinction warrants more data.

Themes are built with `FlexThemeData.light`/`.dark` in
`lib/src/gui/app_widget.dart` and selected by `ThemeMode`, including system mode;
do not introduce `ColorScheme.fromSeed`. Read widget colors from
`Theme.of(context).colorScheme` or `AppSemanticColors`, `AppChartColors`,
`CodeHighlightColors` in `lib/src/gui/theme_extensions.dart`. No new raw literals:
`Colors.*`, `Color(...)` (hex, decimal or uppercase hex), `Color.fromARGB`,
`Color.fromRGBO`, `Color.from`, `HSLColor.fromAHSL`, `HSVColor.fromAHSV`.
`Colors.transparent` is allowed. Alpha on a theme role is allowed when called for
by the design; alpha on a literal is not. The hook's allowlist is
`theme_extensions.dart` and `theme_gallery.dart`; existing literal debt is
grandfathered until touched. Favor the app's custom Material 3 appearance,
consistent typography/type scale (`google_fonts` is available), responsive
`LayoutBuilder` layouts, `OverlayPortal` popups and extensions for custom tokens.
Support light/dark, text contrast at least 4.5:1, specific interactive semantics,
font scaling up to 200% and screen-reader checks appropriate to the target platform.
Upstream TalkBack/VoiceOver examples do not expand this Windows/web product to
unsupported platforms. Visual checks follow [test proportionality](testing.md).

After **any** UI addition/change under `lib/` (widgets, screens, dialogs, restyling,
roles, tokens or alpha composites), refresh the debug-only gallery:

1. Inspect actual color usage. The existing standalone scanner can be run with
   `uv run .claude/skills/theme-gallery-refresh/scan_color_usage.py`; it needs no
   Claude host. Alternatively search theme-role, ThemeData-color, blend and literal
   sites under `lib/`, excluding the gallery itself and generated Dart.
2. Compare uses with `_roleUsages` and `_themeDataUsages` in
   `lib/src/gui/theme_gallery.dart`. Add first uses, remove vanished uses, and write
   concrete one-line English purpose descriptions after reading the callers, not
   file lists. Missing entries mean "not used", without dimming the swatch.
3. Align `_BlendSection` overlay, base, base label and purpose with actual
   `withValues(alpha:)` / `alphaBlend` sites. Add/drop composites as usage changes.
4. Do not hand-maintain live swatch values, the standard role list or the semantic,
   chart/code-highlight sections. New custom colors belong in the theme extension
   and its `app_widget.dart` registration; literal debt is separate migration work.
5. Format/analyze the changed file with the pinned CLI (a fresh temporary
   `DART_DATA_HOME` can avoid host analyzer hangs). No codegen is needed for plain
   gallery edits. Rebuild/relaunch the debug app and show Settings > Debug > Theme
   gallery in light and dark modes, reopening the dialog to check its brightness.
   Coordinate any existing user-owned process; never kill it silently. The gallery
   is `kDebugMode`-only and is not shipped in release builds.
