param(
    [Parameter(Mandatory = $true)][string]$MapRoot
)

$ErrorActionPreference = 'Stop'
$inventoryPath = Join-Path $MapRoot 'font_inventory.csv'
$exportsPath = Join-Path $MapRoot 'export_json'
$inventory = Import-Csv -LiteralPath $inventoryPath
$fontMetadata = @{}

Get-ChildItem -LiteralPath $exportsPath -Filter '*.json' | ForEach-Object {
    $exports = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
    foreach ($export in $exports) {
        $faces = @($export.Properties.CompositeFont.DefaultTypeface.Fonts | ForEach-Object { $_.Name }) -join ','
        $fontMetadata[$_.BaseName] = [pscustomobject]@{
            AssetClass = $export.Class
            AssetType = $export.Type
            TypefaceNames = $faces
        }
    }
}

$enriched = foreach ($row in $inventory) {
    $baseName = [IO.Path]::GetFileNameWithoutExtension($row.InternalPath)
    $metadata = $fontMetadata[$baseName]
    [pscustomobject]@{
        InternalPath = $row.InternalPath
        Extension = $row.Extension
        AssetClass = if ($row.Extension -eq '.ufont') { 'raw SFNT payload (resolved by matching UFontFace asset where present)' } elseif ($row.Extension -eq '.uexp') { 'export payload sidecar' } elseif ($metadata) { $metadata.AssetClass } else { 'not parsed' }
        AssetType = if ($row.Extension -eq '.ufont') { 'raw font payload' } elseif ($row.Extension -eq '.uexp') { 'sidecar' } elseif ($metadata) { $metadata.AssetType } else { '' }
        TypefaceNames = if ($row.Extension -in @('.ufont', '.uexp')) { '' } elseif ($metadata) { $metadata.TypefaceNames } else { '' }
        UpdateSize = $row.UpdateSize
        UpdateSha256 = $row.UpdateSha256
        BasePresence = 'YES (same 88 font-entry paths in Base and Update inventories)'
        UpdatePresence = 'YES'
        ThaiOverride = $row.ThaiOverride
        ThaiSize = $row.ThaiSize
        ThaiSha256 = $row.ThaiSha256
        SameBytes = $row.SameBytes
    }
}
$enriched | Export-Csv -LiteralPath $inventoryPath -NoTypeInformation -Encoding utf8

$usage = @(
    [pscustomobject]@{
        Context = 'Opening WorldMap narration'
        WidgetOrPresentation = 'WB_WorldMap_Narration / RichTextBlock ItemText'
        StyleOrTextSource = 'TBL_WorldMap_Narration, row Default'
        FontObject = 'FOT-ModeMinALargeStd_Font'
        Typeface = 'M'
        BackingFont = 'FOT-ModeMinALargeStd-M.ufont'
        EvidenceCategory = 'PROVEN DIRECT'
        Evidence = 'Resolved asset chain documented in docs/opening-narration-font-resolver.md'
    }
    [pscustomobject]@{
        Context = 'Title Start Menu'
        WidgetOrPresentation = 'WB_Title_StartMenu_Button / TextBlock ItemText'
        StyleOrTextSource = 'Widget property FontObject and Typeface'
        FontObject = 'FOT-ModeMinALargeStd_Font'
        Typeface = 'M'
        BackingFont = 'FOT-ModeMinALargeStd-M.ufont'
        EvidenceCategory = 'PROVEN DIRECT'
        Evidence = 'Resolved asset chain documented in docs/title-menu-selected-background-investigation.md; runtime A/B result documented in docs/font-only-selected-menu-background-poc.md'
    }
    [pscustomobject]@{ Context='Normal story dialogue'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='No complete text-source-to-widget-to-font chain was established in the read-only evidence set.' }
    [pscustomobject]@{ Context='Cutscene/Event dialogue'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='No complete voiced event presentation chain was established in the read-only evidence set.' }
    [pscustomobject]@{ Context='Battle voiced text'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='No evidence that a battle widget is a subtitle/voice presentation was established.' }
    [pscustomobject]@{ Context='System UI'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='Not traced; it must not be treated as excluded from any candidate font slot.' }
    [pscustomobject]@{ Context='Settings/Options'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='Not traced; it must not be treated as excluded from any candidate font slot.' }
    [pscustomobject]@{ Context='Save/Load'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='Not traced; it must not be treated as excluded from any candidate font slot.' }
    [pscustomobject]@{ Context='Tutorial/help'; WidgetOrPresentation=''; StyleOrTextSource=''; FontObject=''; Typeface=''; BackingFont=''; EvidenceCategory='UNKNOWN'; Evidence='Not traced; it must not be treated as excluded from any candidate font slot.' }
)
$usage | Export-Csv -LiteralPath (Join-Path $MapRoot 'font_usage.csv') -NoTypeInformation -Encoding utf8
