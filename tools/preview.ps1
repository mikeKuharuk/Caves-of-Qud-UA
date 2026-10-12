# Makes the mod's pictures from an artwork, both under Steam's 1 MB limit for a Workshop preview:
#   mod/preview.jpg - 1024x1024 JPEG: the preview Steam gets (workshop.json ImagePath), the game's mod list, README.md;
#   mod/preview.png - 512x512 PNG: what the game's Workshop uploader shows, which always reads that file name
#                     (SteamWorkshopUploaderView.UpdatePreview); a PNG of the full size would be over 1 MB.
# Run: powershell -File tools/preview.ps1 <artwork> (a square picture; a wider one is cut to its middle square)
param([Parameter(Mandatory = $true)][string]$Source)
Add-Type -AssemblyName System.Drawing
$mod = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\mod"))
$art = [System.Drawing.Image]::FromFile((Resolve-Path $Source).Path)

function Save-Square($side, $path, $codec, $params) {
    $cut = [Math]::Min($art.Width, $art.Height)
    $from = New-Object System.Drawing.Rectangle -ArgumentList ([int](($art.Width - $cut) / 2)), ([int](($art.Height - $cut) / 2)), $cut, $cut
    $to = New-Object System.Drawing.Rectangle -ArgumentList 0, 0, $side, $side
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList $side, $side
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($art, $to, $from, [System.Drawing.GraphicsUnit]::Pixel)
    $bmp.Save($path, $codec, $params)
    $g.Dispose()
    $bmp.Dispose()
    $bytes = (Get-Item $path).Length
    "wrote $path ($side x $side, $bytes bytes)"
    if ($bytes -ge 1MB) { throw "$path is over Steam's 1 MB" }
}

try {
    $jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    $jpegParams = New-Object System.Drawing.Imaging.EncoderParameters -ArgumentList 1
    $jpegParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter -ArgumentList ([System.Drawing.Imaging.Encoder]::Quality), 90L
    Save-Square 1024 (Join-Path $mod "preview.jpg") $jpeg $jpegParams
    $png = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/png" }
    Save-Square 512 (Join-Path $mod "preview.png") $png $null
} finally {
    $art.Dispose()
}
