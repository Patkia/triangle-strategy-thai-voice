param(
    [string]$ThaiPak = "subthai\THAI-Newera-Switch_P.pak",
    [string]$OutputRoot = "work\full_game_text_index"
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$repak = Join-Path $workspace 'work\tools\repak\v0.2.3\repak.exe'
$dotnet = Join-Path $workspace 'work\tools\dotnet-sdk\dotnet.exe'
$project = Join-Path $workspace 'work\fmodel_datatable_exporter\FmodelDatatableExporter.csproj'
$pakPath = (Resolve-Path -LiteralPath (Join-Path $workspace $ThaiPak)).Path
$outputPath = Join-Path $workspace $OutputRoot
$loosePath = Join-Path $outputPath 'thai_loose_assets'

if (-not (Test-Path -LiteralPath $repak) -or -not (Test-Path -LiteralPath $dotnet) -or -not (Test-Path -LiteralPath $project)) {
    throw 'ไม่พบ repak, local .NET SDK หรือ CUE4Parse POC project'
}

New-Item -ItemType Directory -Force -Path $loosePath | Out-Null

# อ่าน Thai PAK เท่านั้น และ extract เฉพาะ path Text/en/ ที่ mod ใช้เก็บ Thai payload.
& $repak unpack $pakPath --output $loosePath --force --quiet --include 'Newera/Content/Newera/Data/DataTables/Scenario/Text/en/'
if ($LASTEXITCODE -ne 0) { throw "repak unpack failed: $LASTEXITCODE" }

$env:DOTNET_CLI_HOME = Join-Path $workspace 'work\tools\dotnet-home'
$env:NUGET_PACKAGES = Join-Path $workspace 'work\tools\nuget-packages'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
& $dotnet run --project $project --no-restore -- --batch $loosePath $outputPath thai
if ($LASTEXITCODE -ne 0) { throw "CUE4Parse Thai batch failed: $LASTEXITCODE" }

Write-Host "สร้าง Thai raw index แล้ว: $outputPath"
