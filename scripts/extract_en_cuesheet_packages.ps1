$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $root 'work\tools\repak\v0.2.3\repak.exe'
$pak = Join-Path $root 'TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]\Program #0\1\Newera\Content\Paks\Newera-Switch.pak'
$pathsFile = Join-Path $root 'work\opening_voice_candidates\voice_en_paths.txt'
$outDir = Join-Path $root 'work\opening_trace_phase3\cuesheet_packages'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$paths = Get-Content -LiteralPath $pathsFile | Where-Object { $_ -match '^Newera/Content/Newera/Sound/VOICE/EN/.+\.(uasset|uexp)$' }
if ($paths.Count -ne 250) { throw "Expected 250 CueSheet package files, found $($paths.Count)" }
foreach ($assetPath in $paths) {
    $output = Join-Path $outDir (Split-Path $assetPath -Leaf)
    if ((Test-Path -LiteralPath $output) -and (Get-Item -LiteralPath $output).Length -gt 0) { continue }
    $arguments = 'get "' + $pak + '" "' + $assetPath + '"'
    $process = Start-Process -FilePath $repak -ArgumentList $arguments -RedirectStandardOutput $output -RedirectStandardError ($output + '.log') -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "repak get failed for $assetPath" }
}
Write-Output "Extracted $($paths.Count) targeted CueSheet package files to $outDir"
