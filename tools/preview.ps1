# Makes the mod's picture from an artwork: mod/preview.jpg, 1024x1024, a JPEG under Steam's 1 MB limit for a Workshop
# preview. The game shows it in the mod list, Steam on the item's page, and README.md at its top.
# Run: powershell -File tools/preview.ps1 <artwork> (a square picture; a wider one is cut to its middle square)
param([Parameter(Mandatory = $true)][string]$Source)
Add-Type -AssemblyName System.Drawing
$out = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\mod\preview.jpg"))
$side = 1024
$quality = 90L
$art = [System.Drawing.Image]::FromFile((Resolve-Path $Source).Path)
try {
    $cut = [Math]::Min($art.Width, $art.Height)
    $from = New-Object System.Drawing.Rectangle -ArgumentList ([int](($art.Width - $cut) / 2)), ([int](($art.Height - $cut) / 2)), $cut, $cut
    $to = New-Object System.Drawing.Rectangle -ArgumentList 0, 0, $side, $side
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList $side, $side
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($art, $to, $from, [System.Drawing.GraphicsUnit]::Pixel)
    $jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    $params = New-Object System.Drawing.Imaging.EncoderParameters -ArgumentList 1
    $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter -ArgumentList ([System.Drawing.Imaging.Encoder]::Quality), $quality
    $bmp.Save($out, $jpeg, $params)
    $g.Dispose()
    $bmp.Dispose()
} finally {
    $art.Dispose()
}
$bytes = (Get-Item $out).Length
"wrote $out ($side x $side, $bytes bytes)"
if ($bytes -ge 1MB) { throw "the preview is over Steam's 1 MB: lower the quality" }
