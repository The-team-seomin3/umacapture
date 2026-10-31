# Korean UI real-font preview — 2026-10-31

Source commit: `f75b287251bd5c0654866334c29bff88e581abd2` (PR #12).
Font: bundled official Nanum Gothic regular/bold/extra-bold, weights 400/700/800.
Renderer: Flutter 3.44.4 / Dart 3.12.2 widget test, Windows target-platform variant,
DPR 1. Matrices: 1280x900 and 480x900, light/dark; 15 surfaces × 4 = 60 PNGs.
[Manifest with per-image/font SHA-256](manifest.json).

## Findings and corrections

- PASS: 60 renders, no Flutter framework/layout exceptions; every PNG was visually
  reviewed by the implementer (normal width) or delegated visual reviewer (narrow).
  Changed toast/waiting images were rechecked after correction.
- PASS: Hangul is rendered with actual bundled font bytes rather than Ahem; the
  regular font cmap covers all 477 distinct Hangul syllables in ko.json. No missing
  glyphs, unintended text/control overlap or inaccessible dialog controls were
  observed in these states.
- Fixed the missing separator before the Korean privacy-settings sample link.
- Fixed filled-toast foreground contrast using existing theme roles without
  changing background colors or other semantic-role consumers. Representative
  rendered success/error text ratios changed as below; eight widget regression
  cases cover all four toast types in both themes with a >=4.5:1 threshold.

| Toast | Before | After | Final foreground / background |
| --- | ---: | ---: | --- |
| Light success | 4.116:1 | 4.588:1 | #111111 / #388E3C |
| Light error | 7.325:1 | 7.325:1 | #FFFFFF / #B00020 |
| Dark success | 2.012:1 | 9.662:1 | #0C0D0F / #81C784 |
| Dark error | 3.602:1 | 5.397:1 | #0C0D0F / #CF6679 |

Ratios use the actual opaque foreground/background colors and relative luminance;
this is a targeted toast check, not a full accessibility audit. Threshold reference:
[W3C contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

## Captured surfaces

The harness uses production widgets, the production theme modifier and default
bold preference. It supplies empty/synthetic records, controlled capture/import
states, temporary storage and local version/module results. It does not recreate
product widgets. The shell is a fixture, not the complete native window.

| Surface | Light normal | Light narrow | Dark normal | Dark narrow |
| --- | --- | --- | --- | --- |
| navigation | [light/normal](images/light_normal_navigation.png) | [light/narrow](images/light_narrow_navigation.png) | [dark/normal](images/dark_normal_navigation.png) | [dark/narrow](images/dark_narrow_navigation.png) |
| capture_unavailable | [light/normal](images/light_normal_capture_unavailable.png) | [light/narrow](images/light_narrow_capture_unavailable.png) | [dark/normal](images/dark_normal_capture_unavailable.png) | [dark/narrow](images/dark_narrow_capture_unavailable.png) |
| capture_ready | [light/normal](images/light_normal_capture_ready.png) | [light/narrow](images/light_narrow_capture_ready.png) | [dark/normal](images/dark_normal_capture_ready.png) | [dark/narrow](images/dark_narrow_capture_ready.png) |
| capture_waiting | [light/normal](images/light_normal_capture_waiting.png) | [light/narrow](images/light_narrow_capture_waiting.png) | [dark/normal](images/dark_normal_capture_waiting.png) | [dark/narrow](images/dark_narrow_capture_waiting.png) |
| capture_importing | [light/normal](images/light_normal_capture_importing.png) | [light/narrow](images/light_narrow_capture_importing.png) | [dark/normal](images/dark_normal_capture_importing.png) | [dark/narrow](images/dark_narrow_capture_importing.png) |
| records_empty | [light/normal](images/light_normal_records_empty.png) | [light/narrow](images/light_narrow_records_empty.png) | [dark/normal](images/dark_normal_records_empty.png) | [dark/narrow](images/dark_narrow_records_empty.png) |
| settings_top | [light/normal](images/light_normal_settings_top.png) | [light/narrow](images/light_narrow_settings_top.png) | [dark/normal](images/dark_normal_settings_top.png) | [dark/narrow](images/dark_narrow_settings_top.png) |
| settings_middle | [light/normal](images/light_normal_settings_middle.png) | [light/narrow](images/light_narrow_settings_middle.png) | [dark/normal](images/dark_normal_settings_middle.png) | [dark/narrow](images/dark_narrow_settings_middle.png) |
| settings_bottom | [light/normal](images/light_normal_settings_bottom.png) | [light/narrow](images/light_narrow_settings_bottom.png) | [dark/normal](images/dark_normal_settings_bottom.png) | [dark/narrow](images/dark_narrow_settings_bottom.png) |
| storage | [light/normal](images/light_normal_storage.png) | [light/narrow](images/light_narrow_storage.png) | [dark/normal](images/dark_normal_storage.png) | [dark/narrow](images/dark_narrow_storage.png) |
| delete_confirmation | [light/normal](images/light_normal_delete_confirmation.png) | [light/narrow](images/light_narrow_delete_confirmation.png) | [dark/normal](images/dark_normal_delete_confirmation.png) | [dark/narrow](images/dark_narrow_delete_confirmation.png) |
| error | [light/normal](images/light_normal_error.png) | [light/narrow](images/light_narrow_error.png) | [dark/normal](images/dark_normal_error.png) | [dark/narrow](images/dark_narrow_error.png) |
| notification_success | [light/normal](images/light_normal_notification_success.png) | [light/narrow](images/light_narrow_notification_success.png) | [dark/normal](images/dark_normal_notification_success.png) | [dark/narrow](images/dark_narrow_notification_success.png) |
| notification_error | [light/normal](images/light_normal_notification_error.png) | [light/narrow](images/light_narrow_notification_error.png) | [dark/normal](images/dark_normal_notification_error.png) | [dark/narrow](images/dark_narrow_notification_error.png) |
| waiting | [light/normal](images/light_normal_waiting.png) | [light/narrow](images/light_narrow_waiting.png) | [dark/normal](images/dark_normal_waiting.png) | [dark/narrow](images/dark_narrow_waiting.png) |

Settings are sampled at three scroll positions. Cropping at viewport scroll edges
is expected; narrow storage titles retain existing ellipsis while descriptions
remain visible. Storage sizes are settled 0 B, not unresolved loading indicators.
Drawer screenshots show the actual open drawer. Notification screenshots assert
an actual SnackBar in the viewport. Delete confirmation is opened for two synthetic
IDs and never confirmed. Error messages/video filenames are explicitly synthetic.
English in developer-only Theme gallery and diagnostic values is intentional.
The waiting body has no fixture appbar/navigation; its dark variant injects a theme
and does not prove that native startup selects dark mode.

## Reproduction and validation

See [harness instructions](../../../tool/visual/README.md). Its JSON metadata records
all framework errors (empty for each image). Font provenance and SIL OFL are
checked in with the application. No installed-font prerequisite or font download
at runtime is needed for Korean UI.

- Opt-in production-widget preview: 60/60 passed.
- Toast contrast + Korean locale + storage locale tests: 52/52 passed.
- Full analyzer: exits 0 with --no-fatal-infos; eight existing deprecated-member infos.
- Changed Dart formatting at 120 columns and git diff --check: pass.
- build_runner build --force-jit: exits 0, with existing SDK/analyzer-version warning.
  Its local web license inventory reflects absent local web provisioning, so that
  environment-only output was not included in this change.

## Evidence boundary / native handoff

This evidence covers real-font production-widget layouts with synthetic providers.
It is not a Windows executable run and does not prove native chrome, OS file dialogs,
DPI/scaling beyond 1, populated module-backed record tables, real account data,
capture/recognition, networking, restart/update behavior or complete app lifecycle.
Those remain part of the issue #11 current-source Windows handoff. Keep issue #10
open for its remaining native acceptance; do not infer a merge/deployment verdict
from these screenshots.
