param(
    [Parameter(Mandatory = $true)][string]$UpdatePak,
    [Parameter(Mandatory = $true)][string]$ThaiPak,
    [Parameter(Mandatory = $true)][string]$Repak,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

$ErrorActionPreference = 'Stop'

function Export-PakFile {
    param([string]$Pak, [string]$InternalPath, [string]$Destination)
    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if ((-not (Test-Path -LiteralPath $Destination)) -or ((Get-Item -LiteralPath $Destination).Length -eq 0)) {
        $info = [System.Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $Repak
        $info.UseShellExecute = $false
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.Arguments = 'get "{0}" "{1}"' -f $Pak, $InternalPath
        $proc = [System.Diagnostics.Process]::Start($info)
        $output = [IO.File]::Open($Destination, [IO.FileMode]::Create, [IO.FileAccess]::Write)
        $proc.StandardOutput.BaseStream.CopyTo($output)
        $output.Dispose()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "repak get failed ($($proc.ExitCode)): $InternalPath $stderr" }
    }
}

$updatePaths = & $Repak list $UpdatePak
$thaiPaths = & $Repak list $ThaiPak
$fontPaths = $updatePaths | Where-Object { $_ -match '^Newera/Content/Newera/UI/Font/' }
$thaiFontPaths = $thaiPaths | Where-Object { $_ -match '^Newera/Content/Newera/UI/Font/' }

foreach ($path in $fontPaths) {
    Export-PakFile -Pak $UpdatePak -InternalPath $path -Destination (Join-Path $OutputRoot ('update\' + $path))
}
foreach ($path in $thaiFontPaths) {
    Export-PakFile -Pak $ThaiPak -InternalPath $path -Destination (Join-Path $OutputRoot ('thai\' + $path))
}

$rows = foreach ($path in $fontPaths) {
    $updateFile = Join-Path $OutputRoot ('update\' + $path)
    $thaiFile = Join-Path $OutputRoot ('thai\' + $path)
    $isThaiOverride = Test-Path -LiteralPath $thaiFile
    [pscustomobject]@{
        InternalPath = $path
        Extension = [IO.Path]::GetExtension($path)
        UpdateSize = (Get-Item -LiteralPath $updateFile).Length
        UpdateSha256 = (Get-FileHash -LiteralPath $updateFile -Algorithm SHA256).Hash.ToLowerInvariant()
        ThaiOverride = if ($isThaiOverride) { 'YES' } else { 'NO' }
        ThaiSize = if ($isThaiOverride) { (Get-Item -LiteralPath $thaiFile).Length } else { '' }
        ThaiSha256 = if ($isThaiOverride) { (Get-FileHash -LiteralPath $thaiFile -Algorithm SHA256).Hash.ToLowerInvariant() } else { '' }
        SameBytes = if ($isThaiOverride) { if ((Get-FileHash -LiteralPath $updateFile -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $thaiFile -Algorithm SHA256).Hash) { 'YES' } else { 'NO' } } else { '' }
    }
}
$rows | Export-Csv -LiteralPath (Join-Path $OutputRoot 'font_inventory.csv') -NoTypeInformation -Encoding utf8
