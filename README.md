<div align="center"><img src="logo.png" width="400" alt="umacapture_logo"/></div>

# umacapture

<div align="center">

[![License](https://img.shields.io/github/license/The-team-seomin3/umacapture)](LICENSE)
![platform](https://img.shields.io/badge/platform-Windows-blue)

</div>

umacapture is a software that extracts in-game information from the game [ウマ娘](https://umamusume.jp/) using only image recognition.
This software is designed not to interfere with the game client or server and is not intended to violate the terms of use.

NOTE: Currently, only supports the game client for the Japanese market.


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

Application UI: [Korean localization and validation](docs/korean-ui-localization.md).
Windows desktop starts in Korean; game-client recognition support is separate.
Windows local delivery: [install-free build and verification](docs/windows-portable.md), with [#15 integration validation](docs/validation/windows-isolation-integration-2026-10-31.md).

PoC/MVP development guidance: [AGENTS.md](AGENTS.md), with links to contracts, tooling, verification and native architecture.


## Community

Fork issues: https://github.com/The-team-seomin3/umacapture/issues

This fork derives from [umasagashi/umacapture](https://github.com/umasagashi/umacapture). Upstream attribution and MIT notices are retained.

Reporting and application updates are disabled; their existing controls remain crossed out and locked. See [fork network policy](docs/fork-network-policy.md) for permitted module downloads and validation limits.

## Licence

MIT License
