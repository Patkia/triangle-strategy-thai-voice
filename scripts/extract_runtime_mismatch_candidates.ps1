$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $root 'work\tools\repak\v0.2.3\repak.exe'
$pak = Join-Path $root 'TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]\Program #0\1\Newera\Content\Paks\Newera-Switch.pak'
$outDir = Join-Path $root 'work\runtime_opening_mismatch\assets'
$assetPaths = @(
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01_old/Text_ms01_x01_old_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01_old/Text_ms01_x01_old_wd_0010.uexp',
    'Newera/Content/Newera/Data/DataTables/Scenario/Main/ms01_x01_old/ms01_x01_old_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Main/ms01_x01_old/ms01_x01_old_wd_0010.uexp'
)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
foreach ($assetPath in $assetPaths) {
    $output = Join-Path $outDir (Split-Path $assetPath -Leaf)
    if ((Test-Path -LiteralPath $output) -and (Get-Item -LiteralPath $output).Length -gt 0) { continue }
    $arguments = 'get "' + $pak + '" "' + $assetPath + '"'
    $process = Start-Process -FilePath $repak -ArgumentList $arguments -RedirectStandardOutput $output -RedirectStandardError ($output + '.log') -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "repak get failed for $assetPath" }
}
Write-Output "Extracted $($assetPaths.Count) old-variant assets to $outDir"
