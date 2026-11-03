# Application process protocol v1

`kr_factor_app.py` is the stable process boundary for the Korean-factor Windows
application. It reuses the existing pinned OCR, source-pixel validation, review
bindings and full-record exporter. It does not change the native Japanese
recognizer, run optional candidate improvements, download assets, or call an
external AI service.

Use an explicitly configured Python 3.12+ interpreter with the dependencies from
`kr_factor_app.py`'s inline block. Supply an argument list, not a shell command:

```text
python kr_factor_app.py run --request C:/private/new-request.json
```

A completed original three-tab capture, compatible module, local pinned model and
read-only pinned master are still required. See [README.md](README.md) for those
inputs and the review/export contract. The adapter does not ship a private master
or install its runtime. The host application configures its interpreter/script
paths and displays process errors; no separate manual producer invocation is
required when the application orchestrates this protocol.

## Transport and status

The request is one UTF-8 JSON object. Duplicate keys, non-finite numbers, unsupported
schema versions and invalid field types fail. Paths in request fields must be
explicit absolute local paths. Omitted `schema_version` means version 1.

Each command writes exactly one UTF-8 JSON object to stdout; producer progress and
runtime logging go to stderr. Do not decide success from stderr text. Process
cancellation does not generate an artificial success response. CLI `--help` is
ordinary human-readable help and is not a protocol command.

Every response includes:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1`. |
| `command` | Requested command, or null if argument parsing failed. |
| `status` | `needs_review`, `ok`, `completed` or `error`. |
| `completed` | True **only** after successful reviewed export and published-byte readback. |

| Exit | Meaning |
| --- | --- |
| `0` | Successful command. Only export may report `completed: true`. |
| `2` | Valid operation requiring review; show **Needs review**, not Failed/Completed. |
| `1` | Error, with `error_type` and `message`; no successful result. |

Messages and detailed file paths remain local; logs/responses may contain private
OCR/capture information and must not be uploaded by default.

## Shared request

```json
{
  "schema_version": 1,
  "capture": "C:/private/capture",
  "master": "C:/private/master/game_master.sqlite3",
  "master_sha256": "<64 hex characters>",
  "factor_info": "C:/private/module/factor_info.json",
  "factor_info_sha256": "<64 hex characters>",
  "module_version": "C:/private/module/version_info.json",
  "model": "C:/private/models/korean_PP-OCRv5_rec_mobile.onnx",
  "working_dir": "C:/private/kr-runs/new-run"
}
```

`working_dir` must be separate from capture, master, module and model input
locations. It owns fixed `diagnostics/` and `review.json` paths; callers cannot
redirect those files into source inputs. Writable run/output paths must not use
symlinks or junctions. A fresh run is reserved before inference; an error or forced
cancellation may leave partial evidence. Preserve it and choose a new run instead
of deleting locks or reusing a partial destination.

### `run`

Require a nonexistent `working_dir`. Run actual OCR with the existing fixed model,
then prepare an entirely unreviewed receipt. Return the session DTO and exit 2.
Repeated use of the same run fails. Input/model/module/master failures return 1;
no candidates are silently accepted.

### `load` and `validate-review`

Use the shared request to resume or validate a saved session. Both recheck source,
model/module/master, diagnostic/crop identities, tool bindings and the saved
review. Return the session DTO: exit 2 for an incomplete review, exit 0 for a valid
fully reviewed draft. Neither exports a record.

### `lookup`

Only `master`, `master_sha256`, `factor_info` and `factor_info_sha256` from the shared
request are required. Additional fields:

| Field | Meaning |
| --- | --- |
| `query` | Text substring; default empty allows browsing. Existing NFC/whitespace/case normalization only; punctuation stays significant. |
| `star` | Optional integer 1–3, or null for all stars. |
| `offset` | Nonnegative integer, default 0. |
| `limit` | Integer 1–200, default 50. |

The successful response adds `matches`, `total`, `offset`, `limit`. Each match has
`name_ko`, `factor_id`, `factor_group_id`, `star`, `app_sids`, `selectable`.
`selectable` means exactly one module SID; **SID 0 is valid**. Missing/ambiguous
edges remain visible but unselectable. A lookup does not verify an identity or
change a review. It permits manual correction when OCR produces no useful result.

### `save-review`

Add `review` (the complete review object returned by run/load) and
`expected_review_sha256` (the last returned review hash) to the shared request.
Preserve every immutable binding, row/group/order, crop hash, original OCR and
baseline value. Only these fields are editable:

- Top-level `reviewer`.
- `coverage.complete_capture`, `coverage.group_boundaries`,
  `coverage.no_missing_or_duplicate_rows`, and `coverage.evidence`.
- Per-row `decision`, `observed_name`, `master_name`, `star`, `app_sid`, `factor_id`,
  `factor_group_id`, `name_difference_reason`, and `evidence`.

A `decision` is `unreviewed`, `verified` (independent pixel observation) or
`confirmed` (explicit confirmation). Do not prefill a verified/confirmed decision
from candidate agreement or confidence. A selected row must have a complete valid
name/star/namespace/SID chain and nonempty evidence. Different displayed/master
spelling requires its specific `name_difference_reason`; this never creates a
global alias policy.

Atomic draft saving uses an owned lock and exact previous hash. A stale hash,
invalid selected identity or changed immutable value fails before replacement.
Partial drafts return exit 2; fully reviewed valid drafts return exit 0. The result
includes the new `review_sha256`. Keep that hash for the next save. A draft hash is
not an export receipt.

### `export`

Add absolute `output` (filename must be `record-kr.json`) and fresh absolute
`evidence_output`; optional `replace_sha256` is the exact hash of an existing valid
output explicitly selected for replacement. Prefer a separate per-run output
folder, for example `working_dir/result/record-kr.json` and
`working_dir/export-evidence`.

An incomplete review returns the session DTO and exit 2 without writing an output.
A complete review is passed to the existing authoritative exporter. Existing
output replacement without its exact pin fails. Source `record.json` and all other
inputs are preserved; the full JSON tree retains its types, keys and non-factor
values. Only verified factor IDs/stars and `metadata.region = "KR"` change.

Success is exit 0 with `status: "completed"`, `completed: true`, `output`,
`evidence_output`, `output_sha256`, `verified_rows`, `comparison_counts`. The adapter
reopens the published output and paired receipt and checks their hashes and the
allowed-path contract. Output bytes are authoritative: do not round-trip them
through a serializer that upgrades or discards source fields. Non-factor values
remain unverified for Korean accuracy.

The existing lock/replacement/staging behavior is retained. An interrupted writer
can leave a stale lock; cancellation never authorizes removing another writer's
lock or guessing a replacement pin.

## Session DTO

`run`, `load`, `save-review`, `validate-review`, and incomplete `export` add:

| Field | Meaning |
| --- | --- |
| `working_dir`, `diagnostics`, `review_path` | Absolute effective run paths. |
| `review_sha256` | Hash bound to the returned saved review snapshot. |
| `source_image` | Original full factor PNG for capture/group/coverage review. |
| `rows` | Ordered diagnostic rows (see below). |
| `review` | Existing full exporter review object, including immutable `bindings`. |
| `review_issues` | List of strings describing missing confirmations/coverage. |
| `ready_to_export` | Fully reviewed draft passed existing review validation. |
| `limitations` | Factor-only and explicit-review boundaries for display. |

Each diagnostic row contains `group`, one-based `index`, `baseline_sid`, `star`,
`name_rect`, `star_rect`, absolute `name_crop`/`star_crop`, `raw_text`, `score`,
`candidates`, `status` and `verified: false`. Diagnostic status is `candidate_only`
or `unresolved` and is distinct from the response status. Selected decisions are
in `review.rows`; diagnostic `verified` never promotes an OCR suggestion.

Candidates retain `name_ko`, `factor_id`, `factor_group_id`, `star`, `app_sids`, and
`match`. Module SID, Scout group ID and selected-star factor ID are separate
namespaces. Correcting a star requires selecting the corresponding pinned-master
factor ID, rather than reusing the previous star's identity.

## Validation and integration boundary

```text
python -B -m unittest discover -s tool/kr_factor_ocr -q
```

The adapter tests exercise real saved draft/output bytes with synthetic pixels and
mocked inference: no synthetic result is an OCR accuracy claim. They cover JSON
transport, needs-review status, all three groups, SID 0, empty-candidate manual
selection, immutable/stale review rejection, coverage gates, lookup pins and
paging, full-record preservation, and exact-hash replacement.

Recognition owns this process contract; App owns the review UI/configuration and
General owns Windows executable/package integration. The adapter alone does not
establish a usable second application, live game capture, downstream import,
release readiness or simultaneous execution. #29 candidate changes remain outside
this Phase-1 adapter.
