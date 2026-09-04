$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $root 'work\tools\repak\v0.2.3\repak.exe'
$pak = Join-Path $root 'TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]\Program #0\1\Newera\Content\Paks\Newera-Switch.pak'
$paths = Join-Path $root 'work\opening_voice_candidates\voice_en_paths.txt'
$outDir = Join-Path $root 'work\opening_trace_phase2\awb'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$awbPaths = Get-Content -LiteralPath $paths | Where-Object { $_ -match '^Newera/Content/Newera/Sound/Stream/VOICE/EN/.+\.awb$' }
if ($awbPaths.Count -ne 125) { throw "Expected 125 AWBs, found $($awbPaths.Count)" }
foreach ($assetPath in $awbPaths) {
    $name = Split-Path $assetPath -Leaf
    $output = Join-Path $outDir $name
    if ((Test-Path -LiteralPath $output) -and (Get-Item -LiteralPath $output).Length -gt 0) { continue }
    $arguments = 'get "' + $pak + '" "' + $assetPath + '"'
    $process = Start-Process -FilePath $repak -ArgumentList $arguments -RedirectStandardOutput $output -RedirectStandardError ($output + '.log') -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "repak get failed for $assetPath (exit $($process.ExitCode))" }
}
Write-Output "Extracted $($awbPaths.Count) AWBs to $outDir"
