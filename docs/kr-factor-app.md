# Korean factor application workflow (Phase 1)

The KR Windows build selects `UMACAPTURE_VARIANT=kr`. Its home screen is **한국어
인자 OCR**, rather than the ordinary dashboard. It invokes the local Korean
PP-OCRv5 producer through `tool/kr_factor_ocr/kr_factor_app.py`; translating the UI
does not change the native Japanese recognizer. The default build retains the JP
workflow. Windows executable/window identity and package validation are owned by
the variant build/package integration; a source change alone is not a release or
proof of end-to-end Windows operation.

## First launch and local configuration

The KR bootstrap is `data_root_kr.json` in the application-support directory,
separate from JP's `data_root.json`. By default all KR settings, temporary data,
storage and capture modules live in `kr-factor-app/` under application support.
`UMACAPTURE_KR_DATA_ROOT` selects an existing absolute KR root; the shared JP
`UMACAPTURE_DATA_ROOT` is not inherited. Startup rejects known JP-root overlap and
unavailable/malformed KR settings before opening Hive or startup maintenance.
The recovery screen can save an existing root or restore the KR default, then
retry; it never migrates files. An environment override takes precedence and must
be corrected in the launching environment. The generic JP data-migration UI is
not offered in the KR app.

The home screen shows the actual executable, data/settings/capture/module paths.
Configure the local Python executable (with the producer's pinned dependencies),
adapter script, completed three-tab capture folder, Korean ONNX model, read-only
Scout normalized master and SHA256, matching `factor_info.json` and SHA256, and
matching `version_info.json`. Set a fresh OCR work directory and result directory
outside protected inputs. The default script is relative to the executable's
package directory; a development checkout can be explicitly selected instead.
**KR 경로 설정 저장** stores only this app's configuration under its KR data root.
No runtime, Korean model or master is automatically installed or downloaded.
See the [producer manual](../tool/kr_factor_ocr/README.md) for exact pins and
input/namespace contracts.

**기존 3탭 캡처 화면** retains ordinary owner-operated capture. A fresh KR root
needs its existing capture module installed using the settings screen's local
module-ZIP import. KR reads its local capture module and does not automatically
update it; this keeps review/module byte bindings stable. Capturing still creates
the baseline `record.json` using the unchanged native Japanese path. Complete all
three tabs; this phase adds no factor-tab-only or agent-operated game control.
Preserved compatible captures can be selected directly in the KR workflow.

## OCR, review and export

1. Select **한국어 OCR 실행**. The app runs the adapter with an explicit interpreter
   and argument list, without a shell. Exit 2 is **검토 필요**, not failure or
   completed export. **기존 작업 재개** reloads and revalidates a saved session.
2. Open the complete `factor.png` and check capture beginning/end, group boundaries
   and missing/duplicate rows. Record the reviewer, three coverage confirmations
   and the coverage evidence; none is pre-accepted.
3. Open every factor row. Name/star crops use nearest-neighbor enlargement and
   support pan/zoom. Inspect actual pixels, raw OCR and the JP baseline. Select a
   candidate or search the pinned master (empty query allows paged browsing).
   Search accepts an observed star 1–3; ambiguous/missing module mappings cannot
   be selected. Module SID **0** is valid and distinct from Scout group and
   star-specific factor IDs. Enter the observed name, any displayed/master name
   difference reason, and row evidence. Explicitly confirm that individual row.
   Selecting a candidate or changing its observation does not confirm it.
4. **검토 초안 저장** saves an incomplete draft using its last review hash;
   a concurrent change is rejected without replacing that draft. **저장 후 전체
   검증** checks every saved row and coverage binding against the producer.
   Immutable source/crop/tool/master/module bindings are preserved. Editing paths
   clears the in-memory session; editing a review disables export until rechecked.
5. **검토된 record-kr.json 내보내기** is enabled only after a saved validated review.
   Each attempt uses a new result subdirectory. The adapter validates and publishes
   the full-shape derived file and paired JP/KR comparison/evidence. The app checks
   the final path and SHA256 against the actual bytes before showing completion.
   It displays the output, hash and evidence paths. It never replaces the original
   `record.json`, auto-loads the KR result into statistics, or serializes it through
   Dart `upgradeFormat`. Copied non-factor values remain unverified for Korean
   accuracy. No downstream import is implied.

Cancel waits for the local OCR process to settle. Failed/cancelled run artifacts
and writer locks are not automatically removed; use a new work directory for a
fresh attempt or resume a valid saved session. A previous valid result is retained.
Do not reuse one run across captures, bypass stale locks or edit immutable review
bindings. No external AI, upload, global install or public release is added.

## App validation

Use `.fvmrc`'s SDK. The App contract suites are:

```powershell
.fvm/flutter_sdk/bin/flutter.bat test test/kr_bootstrap_test.dart test/kr_factor_workflow_test.dart test/kr_factor_workflow_widget_test.dart
.fvm/flutter_sdk/bin/flutter.bat test --dart-define=UMACAPTURE_VARIANT=kr test/kr_variant_startup_test.dart
```

These use synthetic files and process/response fixtures, plus a local SDK Dart
process for cancellation. They cover path isolation/failure, exit-state handling,
immutable review fields, SID 0, final-byte hash verification, explicit row review,
manual lookup and the capture/recovery UI entries. They do not establish real
Korean inference, game capture, Windows native identity/packaging, downstream import
or OCR accuracy. General/Recognition integration must record those checks with
fresh artifacts and the authorized inputs actually used. The earlier unusable KR
artifact remains unidentified unless separate evidence identifies its stage.

For explicit CLI reuse of saved App settings, read-only preflight and opt-in local
receipts, see the [adapter protocol](../tool/kr_factor_ocr/APP_PROTOCOL.md#explicit-cli-settings-reuse-and-read-only-preflight).
These are CLI options; the Flutter settings and UI are unchanged.
