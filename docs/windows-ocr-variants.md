# Japanese and Korean-factor Windows variants

Issue [#30](https://github.com/The-team-seomin3/umacapture/issues/30) adds a
factor-first Korean application alongside the existing Japanese recognizer.
Both use the ordinary complete three-tab, owner-operated capture. The Korean
application additionally orchestrates local Korean factor candidates, explicit
pixel/coverage review and safe full-shape `record-kr.json` export. Copied
non-factor values remain unverified for Korean accuracy.

## Local builds

Use the Flutter version in `.fvmrc` at `.fvm/flutter_sdk`, provisioned MSVC,
CMake, the existing native dependencies documented in [Windows portable
builds](windows-portable.md), and a JDK with JNI headers. Set `JAVA_HOME` for
this shell to the already installed JDK; no global environment change is needed.
Run `flutter pub get` with the pinned SDK before packaging.

```powershell
.fvm/flutter_sdk/bin/flutter.bat pub get
./tool/build_ocr_apps.ps1 -OutputDirectory C:/private/new-ocr-app-build
```

The destination must not exist. Failed/partial builds are retained. The script
builds JP and KR sequentially from the current tree and creates `jp/` and `kr/`
packages with build logs, source file hashes and package manifests. It neither
publishes a release nor includes private capture/master files. Configure an
existing local Python runtime with the pinned OCR dependencies, local Korean
ONNX model and pinned normalized master/module in the KR workflow. Packaging
includes the Python adapter source; it does not install Python or download
models. See the [producer runtime and review contract](../tool/kr_factor_ocr/README.md).

For a single compile:

```powershell
.fvm/flutter_sdk/bin/flutter.bat build windows --release --no-pub --dart-define=UMACAPTURE_VARIANT=jp
.fvm/flutter_sdk/bin/flutter.bat build windows --release --no-pub --dart-define=UMACAPTURE_VARIANT=kr
```

The release tree is reused by Flutter. Copy the complete output for one variant
before building the other; use the packaging script to exclude stale executables.
JP keeps `umacapture.exe` and window `umacapture`. KR uses `umacapture_kr.exe` and
window `umacapture (Korean Factor OCR)`. Native identity follows the same Dart
define as the UI, not a separate environment switch.

## Sequential application use and data safety

Close one variant before opening the other. The existing shared Windows startup
mutex remains the sequential-use boundary. A second same-variant launch focuses
its window; a different variant displays an explicit conflict instead of focusing
the wrong application. Failure to acquire the lock is an error. Simultaneous
operation/capture is not a supported guarantee.

KR startup must resolve its own effective data paths before maintenance or writes.
An unavailable configured KR root requires recovery rather than fallback into JP
storage. Confirm the effective paths in the application, especially when launching
through shortcuts or an environment override. Capture source selection is explicit;
never replace the original `record.json` with a derived record.

Successful OCR candidate generation means review is pending. The producer's exit
code 2 is displayed as Needs review. A final export requires complete per-row and
coverage confirmation, successful exporter validation and the published file hash.
Retain JP/KR comparison evidence and prior outputs on failure. The derived bytes
are not round-tripped through the original app's format-upgrading record writer.

## Verification boundary

A successful compile/package is not actual OCR, capture or release acceptance.
Record both variant executable paths/hashes, fresh source provenance, startup and
restart, KR inference/review/export and rejected incomplete/stale review or failed
output replacement. Use authorized preserved captures; do not automate the game.
Document Passed / Failed / Not Tested separately. Full non-factor Korean OCR,
#29 candidate improvements, external AI services, simultaneous capture and public
distribution are outside this Phase 1.
