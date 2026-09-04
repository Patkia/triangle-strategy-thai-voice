<#
Read-only search of exported/loose metadata for CS02 audio references.
It deliberately excludes the 6 GiB original PAK unless -IncludePak is supplied.
Results are written under work/, never into game files.
#>
[CmdletBinding()]
param([switch]$IncludePak)

$root = Split-Path -Parent $PSScriptRoot
$patterns = 'CS02_EN','CS02','SoundAtomCueSheet','\.awb','\.acb','VOICE','cue','voice'
$exports = Join-Path $root 'Output/Exports'
$dump = Join-Path $root 'TRIANGLE STRATEGY 1.1.1 [0100CC80140F8800][v262144][UPD]'
$files = @()
if (Test-Path -LiteralPath $exports) {
    $files += Get-ChildItem -LiteralPath $exports -Recurse -File | Where-Object {
        $_.Extension -in '.uasset','.uexp','.json','.txt','.ini','.csv','.xml','.locres'
    }
}
# Loose text/configuration files are cheap to search; packaged game data is not
# silently scanned. FModel exports are the preferred source for UE metadata.
$files += Get-ChildItem -LiteralPath $dump -Recurse -File | Where-Object {
    $_.Extension -in '.txt','.ini','.json','.csv','.xml','.locres'
}
if ($IncludePak) { $files += Get-ChildItem -LiteralPath $dump -Recurse -File -Filter '*.pak' }
$matches = @($(foreach ($file in $files) {
    Select-String -LiteralPath $file.FullName -Pattern $patterns -AllMatches -ErrorAction SilentlyContinue |
        ForEach-Object { [PSCustomObject]@{ path=$_.Path.Substring($root.Length + 1); line=$_.LineNumber; text=$_.Line.Trim() } }
}))
$out = Join-Path $root 'work/cs02-reference-search.csv'
New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
$matches | Export-Csv -NoTypeInformation -Encoding utf8 $out
Write-Output "Wrote $($matches.Count) matches: work/cs02-reference-search.csv"
