<#
.SYNOPSIS
  Links the repo's mod/ folder into the game's offline Mods folder (directory junction), so the
  game loads the mod straight from the working tree. -Remove deletes only the link.

.DESCRIPTION
  A junction needs no admin rights. The script refuses to touch anything at the link path that is
  not a junction it can recognise, so a real folder there is never overwritten or deleted.
#>
param(
    [switch]$Remove,
    [string]$ModsDir = (Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud\Mods'),
    [string]$Name = 'CavesOfQudUA'
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path (Join-Path $PSScriptRoot '..\mod')).Path
$link = Join-Path $ModsDir $Name

function Get-LinkTarget($path) {
    $item = Get-Item -LiteralPath $path -Force
    if ($item.LinkType -eq 'Junction' -or $item.LinkType -eq 'SymbolicLink') { return $item.Target }
    return $null
}

if ($Remove) {
    if (-not (Test-Path -LiteralPath $link)) { Write-Host "Nothing to remove: $link"; exit 0 }
    if (-not (Get-LinkTarget $link)) { throw "$link is a real folder, not a link; refusing to delete it." }
    # Removing a junction with Remove-Item on PS 5.1 can recurse into the target; use cmd's rmdir.
    cmd /c rmdir "$link" | Out-Null
    Write-Host "Removed link $link"
    exit 0
}

if (-not (Test-Path -LiteralPath $ModsDir)) { New-Item -ItemType Directory -Path $ModsDir | Out-Null }
if (Test-Path -LiteralPath $link) {
    $target = Get-LinkTarget $link
    if (-not $target) { throw "$link already exists and is not a link; refusing to replace it." }
    if ((@($target)[0]).TrimEnd('\') -ieq $source.TrimEnd('\')) { Write-Host "Already linked: $link -> $source"; exit 0 }
    throw "$link links to '$target', not to $source. Remove it first with -Remove."
}
New-Item -ItemType Junction -Path $link -Target $source | Out-Null
Write-Host "Linked $link -> $source"
