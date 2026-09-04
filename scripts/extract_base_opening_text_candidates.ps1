$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $root 'work\tools\repak\v0.2.3\repak.exe'
$pak = Join-Path $root 'TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]\Program #0\1\Newera\Content\Paks\Newera-Switch.pak'
$outDir = Join-Path $root 'work\first_thai_voice_poc\base_assets'
$assetPaths = @(
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01/Text_ms01_x01_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01/Text_ms01_x01_wd_0010.uexp',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01_old/Text_ms01_x01_old_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01_old/Text_ms01_x01_old_wd_0010.uexp',
    'Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.uasset',
    'Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.uexp',
    'Newera/Content/Newera/Sound/Stream/VOICE/EN/MS01_EN.awb'
)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
foreach ($assetPath in $assetPaths) {
    $output = Join-Path $outDir (Split-Path $assetPath -Leaf)
    if ((Test-Path -LiteralPath $output) -and (Get-Item -LiteralPath $output).Length -gt 0) { continue }
    $arguments = 'get "' + $pak + '" "' + $assetPath + '"'
    $process = Start-Process -FilePath $repak -ArgumentList $arguments -RedirectStandardOutput $output -RedirectStandardError ($output + '.log') -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "repak get failed for $assetPath" }
}
Write-Output "Extracted $($assetPaths.Count) base text candidates to $outDir"
