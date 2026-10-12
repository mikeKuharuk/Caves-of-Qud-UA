# Makes the mod's pictures, each under Steam's 1 MB limit for a Workshop preview:
#   from the square artwork (-Square; another shape is cut to its middle square) the Workshop preview, which Steam shows
#   in the Workshop's square tiles and the square box of the item page and never crops (a wide one gets black bars):
#     mod/preview.jpg - 1024x1024 JPEG: the preview Steam gets (workshop.json ImagePath) and the game's mod list;
#     mod/preview.png - 512x512 PNG: what the game's Workshop uploader shows, which always reads that file name
#                       (SteamWorkshopUploaderView.UpdatePreview); a larger PNG would be over 1 MB;
#   from the wide artwork (-Banner; cut to its middle 16:9) the banner of README.md, docs/images/banner.jpg, 1600x900.
# A wide picture for the item page goes into the item's gallery on the Steam site (Add/edit images & videos), which
# the game's uploader leaves alone.
# Run: powershell -File tools/preview.ps1 -Square <artwork> [-Banner <artwork>]
param([Parameter(Mandatory = $true)][string]$Square, [string]$Banner)
Add-Type -AssemblyName System.Drawing
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$limit = 1000000

# the middle of art in the proportion width:height, drawn at width x height
function Draw-Middle($art, $width, $height) {
    $w = $art.Width; $h = $art.Height
    if ($w * $height -gt $h * $width) { $cw = [int]($h * $width / $height); $ch = $h } else { $cw = $w; $ch = [int]($w * $height / $width) }
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

# a JPEG at the best quality under the limit
function Save-Jpeg($bmp, $path) {
    $jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
    foreach ($quality in 92, 90, 88, 85, 80) {
        $params = New-Object System.Drawing.Imaging.EncoderParameters -ArgumentList 1
        $params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter -ArgumentList ([System.Drawing.Imaging.Encoder]::Quality), ([long]$quality)
        $bmp.Save($path, $jpeg, $params)
        if ((Get-Item $path).Length -lt $limit) { break }
    }
}

function Report($path) {
    $bytes = (Get-Item $path).Length
    "wrote $path ($bytes bytes)"
    if ($bytes -ge $limit) { throw "$path is over Steam's 1 MB" }
}

$art = [System.Drawing.Image]::FromFile((Resolve-Path $Square).Path)
try {
    $bmp = Draw-Middle $art 1024 1024
    Save-Jpeg $bmp (Join-Path $root "mod\preview.jpg")
    $bmp.Dispose()
    Report (Join-Path $root "mod\preview.jpg")
    $bmp = Draw-Middle $art 512 512
    $bmp.Save((Join-Path $root "mod\preview.png"), [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Report (Join-Path $root "mod\preview.png")
} finally {
    $art.Dispose()
}

if ($Banner) {
    $art = [System.Drawing.Image]::FromFile((Resolve-Path $Banner).Path)
    try {
        $dir = Join-Path $root "docs\images"
        New-Item -ItemType Directory -Force $dir | Out-Null
        $bmp = Draw-Middle $art 1600 900
        Save-Jpeg $bmp (Join-Path $dir "banner.jpg")
        $bmp.Dispose()
        Report (Join-Path $dir "banner.jpg")
    } finally {
        $art.Dispose()
    }
}
