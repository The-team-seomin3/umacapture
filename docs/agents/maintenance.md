# Conditional maintenance workflows

These procedures are discoverable from [AGENTS.md](../../AGENTS.md) and apply only
to the requested task. Reading them does not authorize installs, credentials,
releases, external uploads, merges or branch deletion. Use the current owner's
target/authorization and applicable GitHub authentication policy. Older upstream
account names and host-specific paths are not authority over this fork.

## Release

Release has two phases: version/codegen PR **merged to `develop`**, then tag that
merge commit and package/publish. Current [distribute_options.yaml](../../distribute_options.yaml)
targets **`umasagashi/umacapture`**, not this fork, and defaults to pre-release;
verify the intended destination with the actual release authorization before acting.
The installer/zip configuration, `pubspec.yaml`, `build.yaml`,
`lib/distribution_info.dart`, packaging templates and current CI are authoritative.
Do not add a vestigial msix step.

Preflight the pinned FVM SDK, PATH `flutter` (distributor shells out to it), Windows
C++ dependencies and Inno Setup **6.7.3** on the accepted 6.x line. Verify actual
registry version/pin, not ISCC's generic "6" banner. No reason to move to 7.x was
accepted: changing installer defaults would require revalidation; neither old
hardcoded path assumptions nor licensing are reasons to mandate a migration.
Do not silently install/downgrade/pin tools. Probe
`.fvm/flutter_sdk/bin/dart pub global run flutter_distributor:main --version`;
reactivation is only a repair for a broken kernel-version snapshot and needs host
change approval, not a routine step. Verify publisher credential presence without
printing it or falling back to another identity. Sentry CLI/token availability
matters for symbols; missing symbols are reported and historically not release-blocking,
but upload whenever possible under authorization. Do not assume a stored read
token has write scope.

1. Agree semver with the owner (no leading `v` in `pubspec.yaml`), edit its version.
2. Derive **every** `distribution_info` output from `build.yaml`'s
   `builders.distribution_info.build_extensions.pubspec.yaml`. Delete only those
   generated outputs deliberately to force the builder: version-only changes may
   otherwise skip it. Use path-safe, CRLF-aware handling, not a copied filename list.
3. Run unfiltered pinned `dart run build_runner build --force-jit`. Filtering can
   silently omit distribution/license generation. Stop on rejected licenses or
   web-pin mismatch; restore verified bytes or resolve the authorized dependency
   change, never weaken the gate.
4. Confirm all deleted outputs returned and `assets/version_info.json` is the new
   version. Review license outputs and refreshed `assets/license/*.txt`; absence
   is failure. Never commit a `verified` disclosure downgraded to `not_provisioned`.
   Windows-only packaging can operate without web wasm; web shipping cannot.
5. On the authorized release branch (`release/v<version>` is the release convention),
   stage pubspec, the **derived complete output set** and license texts; unchanged
   paths are harmless. Publish an English Conventional Commits PR to `develop`.
   Observe the prepared-branch rule and any acting-agent branch/attribution policy.
6. Check current required reviews/CI/merge gates. Use a **merge commit**, not squash,
   so the reviewed release history is retained; no direct `develop` push. Merge,
   branch deletion and subsequent publication still need their own authorization.
7. Resolve the merged `develop` commit without using another agent's primary tree.
   Annotate/push `v<version>` on that merge commit, not the pre-merge branch tip,
   only when tag/release publication is authorized.
8. Run pinned `dart pub global run flutter_distributor:main release --name windows`.
   Confirm freshly built `dist/umacapture-v<version>-windows.exe` and `.zip`, attached
   to the intended GitHub tag/pre-release. `dist/` is ignored; never commit binaries.
9. Before cleaning that exact build, run `tool/upload_symbols.sh` with
   `SENTRY_AUTH_TOKEN` supplied secretly. Do not hand-roll a reduced upload: it needs
   `umacapture.pdb`, `flutter_windows.dll.pdb` **and** `umacapture.exe`,
   `flutter_windows.dll` for unwind data. Debug IDs must match the packaged binaries.
   The script rejects missing ID/unwind and confirms both server objects; two `ok:`
   lines and `==> done` are success. "Already uploaded" still runs verification.
   Third-party DLLs without PDBs remain unsymbolicated by design.
10. Upload the generated `assets/version_info.json` alongside installer/zip, then
    read back all three assets, tag, draft/pre-release status. Replacing an existing
    asset is not implicit permission to clobber unrelated content.
11. Only when this tag is actually **Latest** (non-pre-release), and authorized,
    fast-forward `main` to its commit with a normal push, verify equality. A
    pre-release leaves `main` unchanged. Stop on non-fast-forward; never force it.
    Promotion to Latest has the same synchronization obligation.

For a web release use the [local wrapper](operations.md#web-builds-and-pins) with
`--pwa-strategy=none --source-maps`, after the version assets are finalized, then
`tool/upload_web_sourcemaps.sh` under authorized credentials. Its release string
comes from `assets/version_info.json`; injection rewrites `build/web` with debug
IDs and verifies the artifact bundle upload. Deploy **that exact tree**; rebuilding
requires reinjection/reupload. Any failed gate stops web publication. Confirm
current branch protection rather than assuming historical two-check names suffice.

## Sentry diagnostics

Use for an authorized request to inspect/triage error reports. Defaults at migration
baseline are US `sentry.io`, org ID `1367286`, production project `6670477`; legacy
debug `6668087` receives no new events because debug builds skip initialization.
Check `lib/src/core/sentry_util.dart`, `.sentryclirc` and the existing helper when
coordinates matter; do not access another service just because these are documented.

The standalone helper requires no Claude installation:

```text
uv run --no-project .claude/skills/sentry-issues/scripts/sentry_issues.py list
uv run --no-project .claude/skills/sentry-issues/scripts/sentry_issues.py list --sort new --links
uv run --no-project .claude/skills/sentry-issues/scripts/sentry_issues.py event <issue-id> --top 30
```

Read token from the existing secret mechanism (helper default `~/.sentry_token`),
never print it, put it on a command line or commit it. If missing/empty, ask the
owner to provision a read token (`event:read`, `project:read`; `org:read` only for
org-wide queries). Symbol upload needs `project:write`; never infer it from the
filename or old machine assertions.

Default `list` scopes to **latest release by Sentry creation date**, unresolved,
all-time so a fresh build is not hidden by the 14-day window. Broaden only on
request: `--all-releases`, `--release <version>` or explicit `release:` in `--query`.
Supported sort keys are `freq/date/new/user`; use `--links` for permalinks/IDs,
`--json` for raw event detail and help for current options. Queries can express
`is:unresolved`, `is:unhandled`, `level:fatal`, `firstSeen:-7d`. For ad-hoc REST,
`statsPeriod` accepts empty / `24h` / `14d`, not `90d`; combine explicit dates/releases
with empty period. Save large payloads and extract relevant fields locally instead
of dumping debug images/events inline. Use relative/native paths when a Windows
interpreter cannot resolve a Git Bash `/tmp` path; do not assume jq is installed.

Dart events are unobfuscated source frames. Native minidumps can be raw addresses:
PDB names and a source line are **not proof of a causal stack**. Inspect frame
`trust`: `context` is the register frame; `cfi` uses real unwind; `scan/fp` are guessed,
so do not reason from their ordering as calls. Inspect debugmeta image `unwind_status`
and event `native_missing_dsym` errors. PDB-only releases through 0.2.1 had missing
unwind; later PE+PDB uploads should support the app/engine, verified per event.
Pre-debug-ID builds cannot be fixed by a newly built PDB. The app's own stack
coverage is `umacapture.exe` and `flutter_windows.dll`; third-party/prebuilt modules
and stripped plugin/sentry-native targets are an accepted gap. Widening Release/
Profile debug flags and symbol sweeps is deferred until an actual crash needs it,
not a routine triage task. Do not re-diagnose that accepted gap without a trigger.

At migration, org `storeCrashReports=0`: no retained minidumps, attachment requests
404 and late uploads cannot reprocess old events. Treat it as source-reported
service state, verify only when relevant under authorized access. Release tagging
comes from Dart's generated version asset passed to native, not exe properties;
old binaries stamped `1.0.0` are not a reliable cross-check of event version.

## Refreshing vendored Flutter guidance

Only when asked to refresh/install/switch upstream guidance, regenerate
`.claude/rules/flutter-ai-rules.md`; do not hand-edit this vendored file. It is the
pruned upstream body, not a home for positive project-specific rules. No Claude
command/loader is needed to perform the following:

1. Select upstream `flutter/flutter` `docs/rules/` variant: default full `rules.md`,
   or `rules_10k.md`, `rules_4k.md`, `rules_1k.md` for requested size. Fetch the actual
   official body and preserve a header with source URL, variant and regeneration
   provenance; normalize LF, UTF-8 without BOM. Read the full fetched body.
2. Re-survey against **current** project rules (root and linked neutral references,
   retained applicable rule files), active user conventions, `pubspec.yaml` and
   `analysis_options.yaml`. Do not blindly replay historical pruning. Flag new and
   disappeared conflicts, including commands/examples as well as prose.
3. Delete or rewrite conflicting upstream passages, preferring deletion when the
   project owner already states the rule. Do not annotate with competing project
   notes. Keep the remaining body verbatim. Maintain portable positive guidance at
   its neutral owner and align legacy consumers as relevant without a second manual.
4. Report variant/character count, body change ignoring provenance header, removals/
   rewrites, newly appeared/disappeared conflicts and intentionally kept non-conflicts.

Known conflict classes are bare SDK/codegen/test invocations, alternate state/DI,
`lib/features`, `dart:developer` logging, `package:checks`, `ColorScheme.fromSeed`,
`go_router`, and competing serialization. Project uses FVM, Riverpod/ref, existing
`lib/src`, central logger, `expect`, Flex themes, auto_route and dart_mappable.
A `ChangeNotifier` notification usage does not make it an app-state/DI alternative.
Judge whether following a bullet produces acceptable code, not whether a class
name occurs. `google_fonts` is a compatible optional example; "prefer Fakes,
Mockito sparingly" is discouragement, not a mandate to install Mockito, and stays
unless a new actual conflict appears. Recheck source/versions rather than importing
an old machine's full/4k size, MCP tool inventory or package availability assumptions.
Retain `.gitattributes` LF handling and the normal Git authorization rules.
