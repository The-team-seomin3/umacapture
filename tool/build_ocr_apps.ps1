[CmdletBinding()]
param([Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$destination = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $destination) { throw 'OutputDirectory must be new; existing outputs are preserved.' }
$flutter = Join-Path $repoRoot '.fvm/flutter_sdk/bin/flutter.bat'
if (!(Test-Path -LiteralPath $flutter)) { throw 'Provision the SDK pinned by .fvmrc at .fvm/flutter_sdk first.' }
$adapter = Join-Path $repoRoot 'tool/kr_factor_ocr/kr_factor_app.py'
if (!(Test-Path -LiteralPath $adapter)) { throw 'The Korean application adapter is required before packaging.' }
if (!(Test-Path -LiteralPath (Join-Path $env:JAVA_HOME 'include/jni.h'))) { throw 'Set JAVA_HOME to an existing JDK with JNI headers.' }
Push-Location $repoRoot
try {
    $pin = (Get-Content .fvmrc -Raw | ConvertFrom-Json).flutter
    $versionText = & $flutter --version --machine
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify Flutter SDK.' }
    if (($versionText | ConvertFrom-Json).frameworkVersion -ne $pin) { throw "Flutter SDK must match $pin." }
    New-Item -ItemType Directory -Path $destination | Out-Null
    $head = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source HEAD.' }
    $log = Join-Path $destination 'build-kr.log'
    & $flutter build windows --release --no-pub '--dart-define=UMACAPTURE_VARIANT=kr' *> $log
    if ($LASTEXITCODE -ne 0) { throw "Build failed; see $log. Partial output retained." }
    $release = Join-Path $repoRoot 'build/windows/x64/runner/Release'
    $exeName = 'umacapture_kr.exe'
    $binary = Join-Path $release $exeName
    if (!(Test-Path -LiteralPath $binary)) { throw "Expected executable missing: $binary" }
    $solution = Get-Content (Join-Path $repoRoot 'build/windows/x64/umacapture.sln') -Raw
    if (!$solution.Contains('runner\umacapture_kr.vcxproj')) { throw 'Native target does not match the KR variant.' }
    if ((Get-Item -LiteralPath $binary).VersionInfo.OriginalFilename -ne $exeName) { throw 'Executable resource identity does not match the KR variant.' }

    $package = Join-Path $destination 'kr'
    New-Item -ItemType Directory -Path $package | Out-Null
    # A reused release tree can still contain the JP binary and symbols.
    Get-ChildItem -LiteralPath $release | Where-Object {
        $_.Name -notmatch '^umacapture\.(exe|pdb)$'
    } | Copy-Item -Destination $package -Recurse
    $tools = Join-Path $package 'tool/kr_factor_ocr'
    New-Item -ItemType Directory -Path $tools -Force | Out-Null
    Get-ChildItem (Join-Path $repoRoot 'tool/kr_factor_ocr') -File | Where-Object { $_.Extension -eq '.py' -or $_.Name -eq 'README.md' } | Copy-Item -Destination $tools

    $files = Get-ChildItem -LiteralPath $package -Recurse -File | ForEach-Object {
        [ordered]@{path=[IO.Path]::GetRelativePath($package,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash;bytes=$_.Length}
    }
    $sourceFiles = @(git ls-files --cached --others --exclude-standard windows lib native/src native/CMakeLists.txt assets/config pubspec.yaml pubspec.lock .fvmrc tool/kr_factor_ocr tool/build_ocr_apps.ps1) | Sort-Object -Unique | ForEach-Object {
        if (Test-Path -LiteralPath $_ -PathType Leaf) { [ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash} }
    }
    [ordered]@{variant='kr';source_head=$head;source_files=$sourceFiles;flutter=$pin;built_utc=[DateTime]::UtcNow.ToString('o');executable=$exeName;files=$files;limits='Local build only. Configure local Python/model/master in KR UI. No private master/model bundled. No game capture or release acceptance implied.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package 'build-manifest.json') -Encoding utf8
} finally { Pop-Location }
