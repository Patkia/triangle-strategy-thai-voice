param(
    [string]$PakPath = "subthai/THAI-Newera-Switch_P.pak",
    [string]$OutputDirectory = "work/first_thai_voice_poc/subthai_text_assets"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $repoRoot 'work/tools/repak/v0.2.3/repak.exe'
$pak = Join-Path $repoRoot $PakPath
$out = Join-Path $repoRoot $OutputDirectory

if (-not (Test-Path -LiteralPath $repak)) { throw "repak not found: $repak" }
if (-not (Test-Path -LiteralPath $pak)) { throw "PAK not found: $pak" }

New-Item -ItemType Directory -Force -Path $out | Out-Null
& $repak unpack $pak --output $out --force --quiet --include 'Newera/Content/Newera/Data/DataTables/Text' --include 'Newera/Content/Newera/Data/DataTables/Scenario/Text'
if ($LASTEXITCODE -ne 0) { throw 'Text asset extraction failed.' }

$count = (Get-ChildItem -LiteralPath $out -Recurse -File -Filter '*.uexp').Count
Write-Output "Extracted uexp files: $count"
