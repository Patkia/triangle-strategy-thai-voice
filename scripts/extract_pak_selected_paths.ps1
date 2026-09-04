param(
    [Parameter(Mandatory = $true)][string]$Pak,
    [Parameter(Mandatory = $true)][string]$Repak,
    [Parameter(Mandatory = $true)][string]$PathList,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
function Export-PakFile {
    param([string]$InternalPath)
    $destination = Join-Path $OutputRoot $InternalPath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Repak; $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $info.Arguments = 'get "{0}" "{1}"' -f $Pak, $InternalPath
    $process = [Diagnostics.Process]::Start($info)
    $stream = [IO.File]::Open($destination, [IO.FileMode]::Create, [IO.FileAccess]::Write)
    $process.StandardOutput.BaseStream.CopyTo($stream); $stream.Dispose()
    $stderr = $process.StandardError.ReadToEnd(); $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "repak get failed for $InternalPath : $stderr" }
}

Get-Content -LiteralPath $PathList | Where-Object { $_.Trim() } | ForEach-Object {
    $uasset = $_.Trim()
    Export-PakFile $uasset
    Export-PakFile ($uasset -replace '\.uasset$', '.uexp')
}
