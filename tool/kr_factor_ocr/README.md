# Korean factor OCR and reviewed full-record export

For representative character and outfit evidence for Evaluator, see the
[offline representative identity tool](../kr_representative_identity/README.md).

This optional Windows offline workflow processes a completed original three-tab
capture. It keeps the original Japanese capture/recognizer/exporter and
`record.json`, then writes a separate full `record-kr.json` **only after every
observed factor and the capture coverage have been independently reviewed**.
Only factor IDs/stars and existing `metadata.region = "KR"` change. KR denotes
the Korean game source, adopted by the owner on October 31, 2026. Copied
non-factor values remain unverified for Korean-client accuracy.

## Portable CLI publication and CI

The Python adapter, configuration/preflight helper and tests run on Linux using
saved captures. See the [KR review app guide](../../docs/kr-factor-app.md) and
[Windows variant builds](../../docs/windows-ocr-variants.md) for the desktop
workflow. Windows runtime acceptance requires checks of the packaged app.

PR CI first classifies the complete diff. The narrow allowlist in
`tool/ci/pr_scope.py` runs routing regressions and the pinned Python suite on Linux;
unknown, nonportable mixed, and other App/native/Windows changes retain the Windows lane. Routing-only
edits to `ci.yml` or `warm-caches.yml` qualify only when the Windows execution
contracts are preserved. The exact legacy `develop` to `master` event targets
and corresponding contribution-rule branch reference can migrate on Linux.
Other event/header changes and Windows step/runner/matrix changes require the
Windows lane.

Ordinary non-executable Markdown manuals under `docs/` use the Linux documentation
lane. This includes new manuals and moves between eligible paths. The lightweight
job runs the routing tests and checks document content, local links and affected
references when a manual moves or disappears. Both ends of a move must qualify.
Scripts, evidence under `docs/validation/`, policy files, the #42 companion
document and the root README retain their existing routing. When introducing a
build, package or test dependency on a manual, update the classifier in the same change.

The bounded sections in `docs/agents/contracts.md`, `docs/agents/teams.md` and
`AGENTS.md` retain their guidance checks. The root agent guide also admits simple
document-link rows in its “Find the needed document” table. Changes to other
policy text retain the conservative route. Specialist review still applies.
Eligible manuals mixed with portable CLI or CI-support changes run the portable
suite. Unknown or nonportable changes select Windows.

The existing native/Flutter required check names are always-run routing gates.
For guidance changes they require successful lightweight checks and explicit
CLI/Windows skips. For portable changes they require successful Linux tests and
identify Windows jobs as not applicable; for Windows changes they require the corresponding
Windows jobs. Missing, failed, cancelled or unexpectedly skipped applicable work
fails the gate. There is no workflow-level path skip or automatic approval/merge.

After a push to `master`, `Warm caches` compares the previous and new commit
trees on Linux. An eligible guidance, portable, or admitted Flutter push skips the Windows
cache job. Nonportable pushes still refresh the Windows dependency caches. A scope
check error fails the workflow before allocating a Windows runner.

### Scoped Linux Flutter validation

[#42](https://github.com/The-team-seomin3/umacapture/issues/42) admits the exact
reviewed [#23](https://github.com/The-team-seomin3/umacapture/issues/23) five-file
delta by before/after SHA-256 and regular-file mode. It requires all five changes,
including the addition of the reviewed strategy test. Changed bytes, modes, or
missing companion files require reassessment. Other product changes and changes
to the admission code or workflows alongside the App delta select Windows.
Already eligible guidance or Python changes retain their applicable checks.

The Ubuntu job uses the pinned SDK from `.fvmrc`, Linux-specific SDK/pub caches,
locked dependency resolution, the strategy and Korean localization suites,
scoped analysis and 120-column formatting. It verifies the required suites ran
without skips. The Flutter gate requires the Linux job to succeed and the
Windows jobs to be skipped. The native gate reports native non-applicability.
The pinned Python suite remains applicable. The CI-support rollout itself
requires the existing Korean localization suite to validate the Linux setup
before the strategy test is published. Linux tests cover this source change;
Windows native, browser and package behavior require their own checks.

Warm caches uses the same admission against the complete master push.
Linux caching uses the PR job and keeps separate keys from Windows caches.

## Application process adapter

For the Phase-1 Korean-factor application, use the [JSON process protocol](APP_PROTOCOL.md)
via `kr_factor_app.py`. It orchestrates actual diagnostics, pinned-master lookup,
explicit review drafts and the same safe exporter. The original manual CLIs below
remain supported. The adapter alone is not the complete Windows application or
a change to Japanese capture/recognition.

For explicit reuse of existing App settings, aggregated read-only prerequisite
checks and optional private hash/error receipts, use the adapter's `--config`,
`preflight --for COMMAND` and `--report` options described in
[the CLI protocol](APP_PROTOCOL.md#explicit-cli-settings-reuse-and-read-only-preflight).
Direct `--request` calls remain compatible. Preflight does not create a run or
accept OCR; config/output identities must be supplied explicitly. This local
source change has not updated an existing Windows package.

## Inputs and runtime

Use Python 3.12+ with the versions in each script's inline dependency block.
The pinned NumPy 2.5.4 requires Python 3.12 or newer.
Tested: Windows Python 3.14.6, RapidOCR 3.10.0, ONNX Runtime 1.31.1 CPU,
opencv-python-headless 4.13.0.92 and NumPy 2.5.4. The export command needs only
the declared OpenCV/NumPy dependencies; it does not run or download an OCR model.
With uv already available the examples provision an isolated script environment.
An existing interpreter with the dependencies can run the same scripts directly.

Supply local files explicitly; the tools do not fetch models or update masters:

- A completed capture directory containing `factor.png`, `factor.json`,
  `prediction.json` and the original complete `record.json`.
- Its matching module's `factor_info.json` and `version_info.json`. Module
  region/recognizer version must match the original record. Pin factor metadata.
- An owner-held Scout normalized SQLite master with `factor` and
  `master_snapshot` tables. Pin its SHA256. Use a stable snapshot with no
  pending/nonempty WAL. Queries open a verified temporary byte copy read-only;
  they never open/checkpoint the original DB. No master corpus is bundled.
- For OCR only: local `korean_PP-OCRv5_rec_mobile.onnx`, SHA256
  `cd6e2ea50f6943ca7271eb8c56a877a5a90720b7047fe9c41a2e541a25773c9b`.
  [Pinned RapidOCR model artifact](https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv5/rec/korean_PP-OCRv5_rec_mobile.onnx).
  Its embedded character dictionary lacks the factor circle marker.

## 1. Produce candidate diagnostics

From the dedicated worktree in PowerShell; replace these private placeholders:

```powershell
$captureInputs = @(
  '--capture', 'C:/private/completed-record',
  '--master', 'C:/private/master/game_master.sqlite3',
  '--master-sha256', '<master-sha256>',
  '--factor-info', 'C:/private/module/factor_info.json',
  '--factor-info-sha256', '<factor-info-sha256>',
  '--module-version', 'C:/private/module/version_info.json'
)
uv run tool/kr_factor_ocr/kr_factor_ocr.py @captureInputs `
  --model C:/private/models/korean_PP-OCRv5_rec_mobile.onnx `
  --output C:/private/ocr/new-run
```

The new destination must be outside all input directories. It contains private
`diagnostic.json` and original-pixel name/star PNG crops. Inspect raw OCR, score,
group/index, rectangles, candidate namespaces and unresolved cases. This command
always leaves `completed: false`, `verified_rows: 0` and each row unaccepted.
Exit **2** means incomplete diagnostics were saved and read back; **1** means
failure. Exit 2 is expected here, rather than an export success.

Initial lookup uses the recorded star and stops at the first stage with
matches: whole name, prefix, or fuzzy. Whole-name and prefix keys use NFC,
whitespace removal and case folding, ignore one terminal `○`, and treat
`・` and `·` alike. They retain plus signs, parentheses and all other punctuation.
The fuzzy fallback keeps the original scorer and punctuation. An empty key
produces no initial suggestion. Raw OCR and master spelling remain unchanged.
The diagnostic retains ordered recommendations and counts all distinct matching
master IDs before checking SID selectability. SID 0 is valid. A unique
selectable whole-name candidate still requires explicit review.

## 2. Prepare and complete a private review file

```powershell
uv run tool/kr_factor_ocr/kr_factor_export.py prepare-review @captureInputs `
  --diagnostics C:/private/ocr/new-run `
  --review C:/private/review/new-review.json
```

This creates a fresh unreviewed JSON template and exits **2**. Existing review
files are refused. It verifies original input identities, diagnostic alignment
and that every saved crop equals its source pixels. The template binds source,
diagnostic, model, master, module, tool and crop hashes plus ordered coordinates.
New tool bytes, changed inputs or different diagnostic bytes require a new
template/review. Git LF/CRLF checkout conversion also changes these byte bindings;
prepare a fresh template after checkout and keep the original diagnostic and
review. Resuming shows the original candidates even when the reviewer selected
another identity. Version 1 diagnostics retain their saved candidates with
stage `legacy`. Use a new run when a new recommendation is needed.

Compare the actual name/star pixels and full capture with an independently
checked reference and pinned master. Complete these fields in a **copy of the
template for that exact run**; do not fill decisions from OCR candidates or JP
agreement alone:

| Review field | Required observation |
| --- | --- |
| `owner_handoff` | Record explicit source-bound questions and owner answers. Set `agent_review_complete` explicitly when agent review is complete. Export requires every question answered and the usual row and coverage checks. See the [save-review contract](APP_PROTOCOL.md#save-review). |
| `reviewer` | Nonempty attribution for the independent pixel observations or explicit confirmation. |
| `coverage` | Set `complete_capture`, `group_boundaries`, and `no_missing_or_duplicate_rows` to true only after reviewing acquisition beginning/end, group transitions and row coverage. Explain the evidence. |
| Each row's `decision` | `verified` for independently checked evidence, or `confirmed` for an explicit confirmation; `unreviewed` blocks export. |
| `observed_name`, `master_name` | Actual displayed text and the selected pinned-master name. Preserve punctuation. |
| `star` | Independently observed rank 1–3. It may correct a wrong saved rank. |
| `app_sid`, `factor_id`, `factor_group_id` | Actual unique linked identities for that name/star. Do not interchange namespaces or compute them by arithmetic alone. |
| `evidence` | Per-row reason/source for the observation or explicit confirmation. |
| `name_difference_reason` | Required whenever displayed and master names differ, such as a specifically inspected middle-dot typography difference. This is one reviewed observation, not a global automatic alias policy. |

Keep group/index, coordinates, crop hashes and bindings unchanged. Export
rechecks every selected name/star/ID against the current pinned master and
module. It rejects missing, extra, duplicated, reordered, unreviewed or stale
rows. A local review receipt is an auditable statement by its reviewer, not a
cryptographic proof or an automatic pixel/coverage detector. If a pixel remains
ambiguous, leave it unreviewed and ask only for that unresolved observation.

## 3. Export a verified full record and paired comparison

```powershell
uv run tool/kr_factor_ocr/kr_factor_export.py export @captureInputs `
  --diagnostics C:/private/ocr/new-run `
  --review C:/private/review/new-review.json `
  --output C:/private/derived/record-kr.json `
  --evidence-output C:/private/export/new-run
```

Exit **0** and `completed: true` mean the reviewed derived bytes were staged,
read back, checked and published. **1** and `status: error` mean failure.
There is no partial final-record success. The output name must be
`record-kr.json`; it can be the exact sibling of the original or a separate
output outside protected input directories. Evidence requires a fresh directory
outside inputs. Do not put review/export evidence inside capture/module/master
or diagnostic inputs.

Standalone export checks each review row against the bound diagnostic before writing
the record or evidence. The original OCR text, source star and source SID must
retain their values and JSON types. Corrections belong in the reviewed fields.

The writer deep-copies the full source JSON tree, changes only reviewed factor
`id`/`star` values and existing region, and checks exact types, keys, array
lengths and allowed-path differences. It preserves `format_version`, copied
unknown fields and all other values. It never calls Dart `upgradeFormat`,
which deliberately changes some legacy skill/support values.

Before preparing a review or exporting, it checks required nested source fields
and JSON types against the existing native/Dart record contracts. An empty
`trainee`, missing status/aptitude/family/race fields or mistyped entries are
refused before output replacement. Legacy optional fields may remain absent or
null; unknown extensions are retained. These structure checks do not certify the
copied non-factor values for Korean accuracy or fill in missing values.

An existing derived file is refused unless `--replace-sha256 <current-hash>`
matches its exact bytes. Writers serialize through a sibling exclusive lock.
Staging uses the target directory, flushes bytes, reads/validates them, writes
and reads back private evidence, then rechecks inputs/review/master/previous
output before `os.replace`. Any validation, staging, evidence-save or replace
failure before that commit preserves the previous output. A partial evidence
directory may remain; retry with a fresh directory. A stale lock requires
checking the writer's state, not automatic lock bypass. Non-cooperating external
writers and filesystem/power-loss durability are not covered guarantees.

`comparison.json` keeps source metadata/module provenance, bindings, review
identity, allowed-output hash and rows aligned by **group + screen order +
coordinates**, with JP/KR IDs/stars and independently evidenced `matched` or
`corrected` results. A template is `unresolved`; failed export reports `error`.
All unresolved/error counts must be zero in a successful final export. The
immutable receipt validates the candidate bytes named by its hash; receipt
presence alone does not prove final-path publication after a failed replace.
Match the actual derived-file hash. Original diagnostics remain incomplete;
the separate receipt records their reviewed outcome. Its
`recommendation_comparison` records the first diagnostic candidate and compares
its identity to the final selection. Spelling changes are tracked separately.
A row without an initial candidate can still be confirmed through manual lookup.

Keep all these artifacts private: source metadata may contain trainer/instance
identifiers, and crops contain game material. This workflow does not upload or
change sharing. Detailed provenance remains outside the existing record schema.

## Validation and supported boundary

```powershell
python -m unittest discover -s tool/kr_factor_ocr -v
```

**36 deterministic tests passed:** the original 13 diagnostic checks and 23
review/export tests. These cover SID 0, range/master identity, source/crop/review
binding, group/order/count and coverage refusals, legacy/source-field preservation,
previous-output pins, lock collision, final input/output race checks, and injected
flush, stage-readback, evidence-write and replace failures. Nested source completeness,
wrong types/enums and optional/legacy/unknown-field preservation are covered,
including refusal before replacing a prior output. Their pixels/OCR are
synthetic and are not an OCR-accuracy measurement.

The actual workflow was executed on one preserved Korean capture, groups
**31/33/31, 95 rows**. Fresh recognition reproduced **78 unique candidates and
17 unresolved**, with network connection entry points blocked. All 95 names and
stars were visually compared with the existing reference, including the 17
uncertain OCR cases at 4x nearest-neighbor; group transitions and the final
boundary were inspected. Explicit read-only master/module chains agree for all
95. A reviewed `record-kr.json` was produced: **1 matched / 94 corrected /
0 unresolved / 0 error** against the original Japanese-model result. An actual
unreviewed-row rejection preserved that derived file's hash. Source bytes stayed
unchanged. This is independently reviewed sample output, not 95/95 automatic OCR.

The actual derived record passed **five research Dart reader/loader/wrapper
checks plus four existing round-trip tests**, using the pinned Flutter 3.44.4 /
Dart 3.12.2 SDK, and a **freshly compiled MSVC C++ production-codec probe**.
They retained the factor semantics, KR, SID 0, format and copied non-factor
semantics. Research inputs/logs are retained in the issue-local private index;
they are not test dependencies or bundled account data. See the completed
[#4 contract handoff](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6540078651).

The subsequent [14-file delivery](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542817561)
includes that baseline and **13 additional distinct saved captures**, totaling
**1,234 individually reviewed names/stars and pinned identity chains**. The
reviewed comparison is **14 matched / 1,220 corrected / 0 unresolved / 0 error**.
All 14 actual outputs passed Dart reader/loader/wrapper tests and a freshly
compiled native codec probe; SID 0 is retained in 29 rows. Automatic diagnostics
still contain **979 candidate-only / 255 unresolved** rows, not accepted OCR
accuracy. Proposed captions were visible during agent pixel review; this is not
a blinded benchmark or certification of unrecorded live frames.

The [private evidence-preservation handoff](https://github.com/The-team-seomin3/umacapture/issues/5#issuecomment-6542958301)
retains all 1,234 original name/star pixel pairs and reviewed labels, raw OCR,
capture identity, namespaces and provenance through existing durable research
assets. All 2,468 crops and 2,624 referenced assets were reopened and checked;
no required data depends on a worktree. The handoff is an index over retained
assets, not a bundled dataset or adopted model-training pipeline. Future
training/evaluation must preserve capture identity when choosing its split.

The original app loads literal `record.json`; it does not automatically discover
the new derived filename. The GUI export remains the distinct
`chara_detail`/`labels` wrapper. No new importer or app workflow is implied.
Layouts outside this saved corpus, current-patch master completeness, full
Japanese DMM/Steam application regression and packaged release remain untested.
The Evaluator owned-instance adapter is **Not Implemented**, separately scoped.
Routine KR-only consumption still requires later owner acceptance of sufficient
independent capture evidence. No native/Dart product behavior or original
exporter is changed by these optional scripts.
