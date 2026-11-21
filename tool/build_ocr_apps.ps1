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
    foreach ($variant in @('jp', 'kr')) {
        $log = Join-Path $destination "build-$variant.log"
        & $flutter build windows --release --no-pub "--dart-define=UMACAPTURE_VARIANT=$variant" *> $log
        if ($LASTEXITCODE -ne 0) { throw "Build failed; see $log. Partial output retained." }
        $release = Join-Path $repoRoot 'build/windows/x64/runner/Release'
        $exeName = if ($variant -eq 'kr') { 'umacapture_kr.exe' } else { 'umacapture.exe' }
        $binary = Join-Path $release $exeName
        if (!(Test-Path -LiteralPath $binary)) { throw "Expected executable missing: $binary" }
        $solution = Get-Content (Join-Path $repoRoot 'build/windows/x64/umacapture.sln') -Raw
        if (!$solution.Contains(('runner\' + ($exeName -replace '\.exe$', '.vcxproj')))) { throw 'Native target does not match requested variant.' }
        if ((Get-Item -LiteralPath $binary).VersionInfo.OriginalFilename -ne $exeName) { throw 'Executable resource identity does not match requested variant.' }
        $package = Join-Path $destination $variant
        New-Item -ItemType Directory -Path $package | Out-Null
        # Copy the install tree. Exclude the other variant's stale executable/PDB.
        Get-ChildItem -LiteralPath $release | Where-Object {
            $_.Name -notmatch '^umacapture(_kr)?\.(exe|pdb)$' -or $_.Name -eq $exeName -or $_.Name -eq ($exeName -replace '\.exe$', '.pdb')
        } | Copy-Item -Destination $package -Recurse
        if ($variant -eq 'kr') {
            $tools = Join-Path $package 'tool/kr_factor_ocr'
            New-Item -ItemType Directory -Path $tools -Force | Out-Null
            Get-ChildItem (Join-Path $repoRoot 'tool/kr_factor_ocr') -File | Where-Object { $_.Extension -eq '.py' -or $_.Name -eq 'README.md' } | Copy-Item -Destination $tools
        }
        $files = Get-ChildItem -LiteralPath $package -Recurse -File | ForEach-Object {
            [ordered]@{path=[IO.Path]::GetRelativePath($package,$_.FullName);sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash;bytes=$_.Length}
        }
        $sourceFiles = @(git ls-files --cached --others --exclude-standard windows lib native/src native/CMakeLists.txt assets/config pubspec.yaml pubspec.lock .fvmrc tool/kr_factor_ocr tool/build_ocr_apps.ps1) | Sort-Object -Unique | ForEach-Object {
            if (Test-Path -LiteralPath $_ -PathType Leaf) { [ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash} }
        }
        [ordered]@{variant=$variant;source_head=$head;source_files=$sourceFiles;flutter=$pin;built_utc=[DateTime]::UtcNow.ToString('o');executable=$exeName;files=$files;limits='Local build only. Configure local Python/model/master in KR UI. No private master/model bundled. No game capture or release acceptance implied.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package 'build-manifest.json') -Encoding utf8
    }
} finally { Pop-Location }
