param(
    [string]$OutputDirectory = "work/first_thai_voice_poc/opening_audio_resolver"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $repoRoot 'work/tools/repak/v0.2.3/repak.exe'
$pak = Join-Path $repoRoot 'TRIANGLE STRATEGY [0100CC80140F8000][v0][BASE]/Program #0/1/Newera/Content/Paks/Newera-Switch.pak'
$out = Join-Path $repoRoot $OutputDirectory
$paths = @(
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/Progress/WorldMapSound.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/WorldMap/ClassWorldMapBase.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/WorldMap/WorldMapFL.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/WorldMap/WorldMapMain.lub',
    'Newera/Content/LuaScriptBin/Src/Newera_Handling/WorldMap/WorldMapUI.lub'
)

if (-not (Test-Path -LiteralPath $repak)) { throw "repak not found: $repak" }
if (-not (Test-Path -LiteralPath $pak)) { throw "Base PAK not found: $pak" }

New-Item -ItemType Directory -Force -Path $out | Out-Null
$arguments = @('unpack', $pak, '--output', $out, '--force', '--quiet')
foreach ($path in $paths) { $arguments += @('--include', $path) }
& $repak @arguments
if ($LASTEXITCODE -ne 0) { throw 'Resolver asset extraction failed.' }

Get-ChildItem -LiteralPath $out -Recurse -File | Select-Object FullName,Length | Format-Table -AutoSize
