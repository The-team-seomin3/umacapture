<div align="center"><img src="logo.png" width="400" alt="umacapture_logo"/></div>

# umacapture

<div align="center">

[![License](https://img.shields.io/github/license/The-team-seomin3/umacapture)](LICENSE)
![platform](https://img.shields.io/badge/platform-Windows-blue)

</div>

umacapture is a software that extracts in-game information from the game [ウマ娘](https://umamusume.jp/) using only image recognition.
This software is designed not to interfere with the game client or server and is not intended to violate the terms of use.

This fork starts the Windows application UI in Korean, with Japanese resources retained.
The built-in game recognizer remains Japanese. Korean factor extraction uses a separate
offline postprocessor after the ordinary three-tab capture; its current implementation
is local work, not part of this source baseline or a published fork release.
Automatic Korean factor OCR currently has low recognition accuracy. AI models are
being used to supplement recognition while this workflow is being refined.
Current progress: **14 captures**, **1,234 factor rows**, and **255 unresolved OCR cases**.
Factors still require verification or explicit confirmation before final export.
See [implementation status and remaining acceptance](docs/implementation-status.md)
for delivery and validation details.


## System requirements

The Windows build imposes no CPU requirement beyond the x86-64 baseline. No `/arch:` switch appears anywhere in
this repository's build files, so every first-party translation unit is compiled for MSVC's default x64 baseline,
and the bundled native libraries select wider instruction sets at run time rather than requiring them: the shipped
`opencv_world4130.dll` records `Baseline: SSE SSE2 SSE3`, with SSE4.1 / SSE4.2 / AVX / AVX2 / AVX-512 built as
runtime-dispatched code paths, and ONNX Runtime likewise chooses its kernels from a CPU-feature probe.

The web build is the stricter of the two. The recognition core is compiled with WebAssembly SIMD (`-msimd128`) and
pthreads, and ONNX Runtime is loaded as its SIMD + threaded build, so the browser must support both WebAssembly
SIMD and `SharedArrayBuffer`. Browsers gate `SharedArrayBuffer` behind cross-origin isolation, so the page has to
be served with `COOP: same-origin` and `COEP: require-corp`; without it the worker refuses the session rather than
falling back to a slower path.


## Docs

| Need | Start here |
| --- | --- |
| Current delivery, evidence and remaining work | [Implementation status](docs/implementation-status.md) |
| Korean application UI and its validation | [Korean localization](docs/korean-ui-localization.md) |
| Approved factor workflow, contracts and task entrypoints | [AGENTS.md](AGENTS.md) |
| Native capture/recognition architecture | [Native backend overview](docs/native-recognition-backend.md) |
| Reporting/update isolation and permitted module traffic | [Fork network policy](docs/fork-network-policy.md) |

The status page links the local OCR result and open Windows delivery PR;
the OCR tool and packaging manuals are not yet included in this baseline.


## Support and upstream

Fork issues: [The-team-seomin3/umacapture](https://github.com/The-team-seomin3/umacapture/issues).

This fork derives from [umasagashi/umacapture](https://github.com/umasagashi/umacapture).
Upstream attribution and MIT notices are retained.

Reporting and application updates are disabled; their existing controls remain
crossed out and locked. See [fork network policy](docs/fork-network-policy.md)
for permitted module downloads and validation limits.

## Licence

MIT License
