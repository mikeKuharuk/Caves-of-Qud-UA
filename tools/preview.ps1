# Makes the mod's pictures from a 16:9 artwork, both under Steam's 1 MB limit for a Workshop preview (an artwork of
# another shape is cut to its middle 16:9; Steam itself crops the picture for its square tiles):
#   mod/preview.jpg - 1920x1080 JPEG, the best quality that fits: the preview Steam gets (workshop.json ImagePath), the
#                     game's mod list, and the banner of README.md;
#   mod/preview.png - 800x450 PNG: what the game's Workshop uploader shows, which always reads that file name
#                     (SteamWorkshopUploaderView.UpdatePreview); a larger PNG would be over 1 MB.
# Run: powershell -File tools/preview.ps1 <artwork>
param([Parameter(Mandatory = $true)][string]$Source)
Add-Type -AssemblyName System.Drawing
$mod = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\mod"))
$limit = 1000000
$art = [System.Drawing.Image]::FromFile((Resolve-Path $Source).Path)

# the artwork's middle 16:9, drawn at width x height
function Draw-Wide($width, $height) {
    $w = $art.Width; $h = $art.Height
    if ($w * 9 -gt $h * 16) { $cw = [int]($h * 16 / 9); $ch = $h } else { $cw = $w; $ch = [int]($w * 9 / 16) }
    $from = New-Object System.Drawing.Rectangle -ArgumentList ([int](($w - $cw) / 2)), ([int](($h - $ch) / 2)), $cw, $ch
    $to = New-Object System.Drawing.Rectangle -ArgumentList 0, 0, $width, $height
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList $width, $height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($art, $to, $from, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    $bmp
}

function Report($path) {
    $bytes = (Get-Item $path).Length
    "wrote $path ($bytes bytes)"
    if ($bytes -ge $limit) { throw "$path is over Steam's 1 MB" }
}

try {
    $jpg = Join-Path $mod "preview.jpg"
    $bmp = Draw-Wide 1920 1080
    $jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    foreach ($quality in 96, 94, 92, 90, 88, 85, 80) {
        $params = New-Object System.Drawing.Imaging.EncoderParameters -ArgumentList 1
        $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter -ArgumentList ([System.Drawing.Imaging.Encoder]::Quality), ([long]$quality)
        $bmp.Save($jpg, $jpeg, $params)
        if ((Get-Item $jpg).Length -lt $limit) { break }
    }
    $bmp.Dispose()
    Report $jpg
    $png = Join-Path $mod "preview.png"
    $bmp = Draw-Wide 800 450
    $bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Report $png
} finally {
    $art.Dispose()
}
