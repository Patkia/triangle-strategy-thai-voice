param(
    [Parameter(Mandatory = $true)][string]$CandidatesCsv,
    [Parameter(Mandatory = $true)][string]$FontPath,
    [Parameter(Mandatory = $true)][string]$OutputDir
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$privateFonts = [System.Drawing.Text.PrivateFontCollection]::new()
$privateFonts.AddFontFile((Resolve-Path -LiteralPath $FontPath))
$family = $privateFonts.Families | Select-Object -First 1

function Save-ClusterPng([string]$Text, [string]$Path) {
    $bitmap = [System.Drawing.Bitmap]::new(800, 180, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
        $font = [System.Drawing.Font]::new($family, 112, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        try {
            # GDI+ บน Windows ใช้ complex-script shaping ของระบบสำหรับข้อความ Thai Unicode.
            $graphics.DrawString($Text, $font, [System.Drawing.Brushes]::White, 60, 30)
        } finally { $font.Dispose() }
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

$i = 0
Import-Csv -LiteralPath $CandidatesCsv | ForEach-Object {
    $i++
    $tag = '{0:D2}_{1}' -f $i, $_.PUACodepoint.Replace('+','')
    Save-ClusterPng $_.RawCluster (Join-Path $OutputDir "${tag}_raw.png")
    Save-ClusterPng $_.ExpectedUnicodeSequenceCandidate (Join-Path $OutputDir "${tag}_expected.png")
}
