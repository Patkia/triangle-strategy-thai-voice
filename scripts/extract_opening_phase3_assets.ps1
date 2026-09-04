$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $root 'work\tools\repak\v0.2.3\repak.exe'
$pak = Join-Path $root 'TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]\Program #0\1\Newera\Content\Paks\Newera-Switch.pak'
$outDir = Join-Path $root 'work\opening_trace_phase3\assets'
$assetPaths = @(
    'Newera/Content/Newera/Sequence/WorldMap/Story/ms01_x01/LS_WM_ms01_x01_wd_0010.uasset',
    'Newera/Content/Newera/Sequence/WorldMap/Story/ms01_x01/LS_WM_ms01_x01_wd_0010.uexp',
    'Newera/Content/Newera/Data/DataTables/Scenario/Main/ms01_x01/ms01_x01_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Main/ms01_x01/ms01_x01_wd_0010.uexp',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01/Text_ms01_x01_wd_0010.uasset',
    'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01/Text_ms01_x01_wd_0010.uexp',
    'Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.uasset',
    'Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.uexp',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/Scenario/Story/ms01_x01/Scene/ms01_x01_wd_0010.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/Scenario/CommonDef/SoundCommon.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/Scenario/CommonDef/EventCommon.lub',
    'Newera/Content/Newera/Data/DataTables/GOP_Sound_Voice.uasset',
    'Newera/Content/Newera/Data/DataTables/GOP_Sound_Voice.uexp',
    'Newera/Content/Newera/Data/DataAsset/SoundStatic.uasset',
    'Newera/Content/Newera/Data/DataAsset/SoundStatic.uexp'
)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
foreach ($assetPath in $assetPaths) {
    $output = Join-Path $outDir (Split-Path $assetPath -Leaf)
    if ((Test-Path -LiteralPath $output) -and (Get-Item -LiteralPath $output).Length -gt 0) { continue }
    $arguments = 'get "' + $pak + '" "' + $assetPath + '"'
    $process = Start-Process -FilePath $repak -ArgumentList $arguments -RedirectStandardOutput $output -RedirectStandardError ($output + '.log') -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "repak get failed for $assetPath" }
}
Write-Output "Extracted $($assetPaths.Count) targeted opening assets to $outDir"
