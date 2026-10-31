# Fork reporting and application update policy

Issue: [#15](https://github.com/The-team-seomin3/umacapture/issues/15).

This fork keeps existing unavailable controls in place to preserve UI layout.
Reporting links, the privacy option and the application updater are crossed out
and disabled. The privacy option displays off without deleting or changing a
legacy saved preference. Pointer and keyboard input cannot activate the retired
controls. Local version information, logging, capture, records and exports remain.

## Outbound destinations

| Purpose | Policy / implementation |
| --- | --- |
| Upstream Sentry exceptions, sessions, feedback and attachments | Disabled. The upstream DSN and all SDK initialization paths are removed. Production availability is always false, default senders refuse, and the breadcrumb sink is inert. |
| Sentry rate-limit/sample resources | Disabled. The configuration loader returns null without a request; the sample link is removed. |
| Original application version metadata and EXE/ZIP updater | Disabled. No cache/network lookup; local version provider only. Download/open callback is inert even if called directly. |
| `https://data.umacapture.com/umacapture/version_info.json` and the verified module archive it names | Retained for recognition. Existing archive SHA-256/size and application compatibility checks remain. No screenshot/record upload is part of these fetches. |
| Manual module alias download | Retained in the module installation dialog; intentionally distinct from application updates. |
| Upstream news | Not fetched. Existing card remains as a disabled placeholder. |
| Support/community | Active GitHub link and issue-template contact identify this fork. Original Discord/X destinations and release badge are removed. README/LICENSE retain original attribution. |
| User-configured addon webhooks | Existing, explicit user configuration remains; no preset upstream reporting destination is introduced. |
| Fonts | Existing Google Fonts calls and bundled assets are unchanged. Their runtime fallback is outside the upstream-reporting routes; this is not a claim of zero networking. |
| Dependency/source/license URLs and XML namespaces | Build-time provisioning, attribution, comments or identifiers; not automatic telemetry routes. |

When the newest remote module requires a newer app, Windows retains a readable
installed module only if its application-version requirement is met. Without a
usable installed module the existing failure banner opens the manual module
installation workflow. Incompatible remote modules are never force-installed.

The reporting SDK dependency and payload/privacy helpers remain to avoid a broad
refactor. Explicitly injected test hubs exercise old payload transformations in
isolation; application callbacks never inject a hub or initialize a transport.
Future fork reporting belongs to #16 and requires separate authorization.

## Validation and delivery

See [the implementation validation record](validation/fork-isolation-2026-10-31.md).
Use the pinned Flutter SDK and `dart run build_runner build --force-jit` after
annotated/codegen changes. This change does not package or replace the #11 ZIP.
Before external distribution, build the final source, record EXE/ZIP hashes,
verify the actual process path on launch/restart and observe forbidden outbound
routes with controlled settings/data. Do not send test reports upstream.
Not Tested never establishes distribution readiness. A speculative old reporting
queue exercise is needed only if concrete residual-send evidence warrants it.
