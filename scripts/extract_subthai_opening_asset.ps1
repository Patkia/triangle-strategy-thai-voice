param(
    [string]$PakPath = "subthai/THAI-Newera-Switch_P.pak",
    [string]$OutputDirectory = "work/first_thai_voice_poc/subthai_opening_asset"
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$repak = Join-Path $repoRoot 'work/tools/repak/v0.2.3/repak.exe'
$pak = Join-Path $repoRoot $PakPath
$out = Join-Path $repoRoot $OutputDirectory
$assetBase = 'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/ms01_x01/Text_ms01_x01_wd_0010'

if (-not (Test-Path -LiteralPath $repak)) { throw "repak not found: $repak" }
if (-not (Test-Path -LiteralPath $pak)) { throw "PAK not found: $pak" }

New-Item -ItemType Directory -Force -Path $out | Out-Null
& $repak unpack $pak --output $out --force --quiet --include "$assetBase.uasset" --include "$assetBase.uexp"
if ($LASTEXITCODE -ne 0) { throw "Extraction failed: $assetBase" }

Get-ChildItem -LiteralPath $out -Recurse -File | ForEach-Object {
    [pscustomobject]@{
        relative_path = $_.FullName.Substring($out.Length).TrimStart('\\')
        bytes = $_.Length
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
} | Sort-Object relative_path | Format-Table -AutoSize
