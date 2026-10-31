# Korean visual preview

Run from a dedicated worktree with the pinned Flutter SDK and resolved packages:

```powershell
$out = Join-Path $env:TEMP 'umacapture-korean-preview'
.fvm/flutter_sdk/bin/flutter.bat test --no-pub --reporter expanded --dart-define=KOREAN_VISUAL_OUTPUT=$out tool/visual/korean_preview_test.dart
```

This opt-in harness renders 15 production-widget surfaces at 1280x900 and 480x900,
light and dark, device pixel ratio 1 (60 PNGs plus JSON metadata). It loads the
actual bundled fonts declared in FontManifest.json, including Nanum Gothic
400/700/800 and the shipped icon fonts. An absent family/license fails setup.
It uses the production theme modifier, default bold preference and the existing
storage/localization/Riverpod test fixtures. No replacement product UI is authored.

The lightweight fixture shell hosts actual navigation, capture controls, record
management empty-state widgets, settings, storage tree, delete confirmation,
error display and toast components. The record/module bootstrap is bypassed;
records are empty and paths are under newly-created temporary directories.
Capture/import state and error text are synthetic. No capture, module download,
network version request, clipboard write, delete confirmation or user-data access
is performed. The waiting body is rendered without the fixture shell under injected
light/dark ThemeData; this is not a test of native startup/theme selection.

The harness asserts drawer/notification presence, settles synthetic storage totals,
collects Flutter exceptions and saves each actual rendered frame. Scrolling settings
are sampled at top/middle/bottom. It is outside test/ to avoid generating screenshot
artifacts in ordinary CI. Visual review is still required; passing the harness alone
does not establish pixel quality or complete application acceptance.

Native Windows window chrome, OS file dialogs, DPI scaling beyond 1, populated
module-backed record grids, real capture/recognition and the full app lifecycle
remain outside this preview. Use the packaging issue for a current-source native run.
