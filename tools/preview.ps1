# Draws the Workshop preview, mod/preview.png (512×512): the game's dark teal, a yellow frame, the Ukrainian flag's
# colours, and the mod's name. Our own picture, no game art. Run: powershell -File tools/preview.ps1
Add-Type -AssemblyName System.Drawing
$out = Join-Path $PSScriptRoot "..\mod\preview.png"
$size = 512
$bmp = New-Object System.Drawing.Bitmap $size, $size
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
function Color($hex) { [System.Drawing.ColorTranslator]::FromHtml($hex) }
$g.Clear((Color "#0D1F1C"))
$frame = New-Object System.Drawing.Pen (Color "#CFC041"), 4
$g.DrawRectangle($frame, 14, 14, $size - 28, $size - 28)
$thin = New-Object System.Drawing.Pen (Color "#155352"), 2
$g.DrawRectangle($thin, 26, 26, $size - 52, $size - 52)
$center = New-Object System.Drawing.StringFormat
$center.Alignment = [System.Drawing.StringAlignment]::Center
$center.LineAlignment = [System.Drawing.StringAlignment]::Center
function Text($s, $font, $px, $style, $hex, $y, $h) {
    $f = New-Object System.Drawing.Font -ArgumentList $font, $px, $style, ([System.Drawing.GraphicsUnit]::Pixel)
    $b = New-Object System.Drawing.SolidBrush -ArgumentList (Color $hex)
    $box = New-Object System.Drawing.RectangleF -ArgumentList 0, $y, 512, $h
    $g.DrawString($s, $f, $b, $box, $center)
}
Text "CAVES OF QUD" "Consolas" 44 ([System.Drawing.FontStyle]::Bold) "#B1C9C3" 70 70
$g.FillRectangle((New-Object System.Drawing.SolidBrush (Color "#0057B7")), 106, 165, 300, 48)
$g.FillRectangle((New-Object System.Drawing.SolidBrush (Color "#FFD700")), 106, 213, 300, 48)
Text "Українська" "Segoe UI" 66 ([System.Drawing.FontStyle]::Bold) "#FFFFFF" 278 96
Text "переклад гри · Ukrainian translation" "Segoe UI" 21 ([System.Drawing.FontStyle]::Regular) "#B1C9C3" 372 40
Text "lang-experimental 2.0.212+" "Consolas" 18 ([System.Drawing.FontStyle]::Regular) "#77BFCF" 430 32
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
"wrote $out"
