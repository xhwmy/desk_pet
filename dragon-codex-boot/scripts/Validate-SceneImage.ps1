param([Parameter(Mandatory=$true)][string]$ImagePath)
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Drawing
    $image = [Drawing.Image]::FromFile((Resolve-Path -LiteralPath $ImagePath).Path)
    try {
        if ($image.Width -gt 8192 -or $image.Height -gt 8192 -or $image.Width * [long]$image.Height -gt 32000000) { throw 'Image dimensions exceed the supported limit.' }
        # Drawing forces pixel decoding rather than accepting a header-only image.
        $bitmap = New-Object Drawing.Bitmap $image.Width,$image.Height
        try {
            $graphics = [Drawing.Graphics]::FromImage($bitmap)
            try { $graphics.DrawImage($image, 0, 0, $image.Width, $image.Height) }
            finally { $graphics.Dispose() }
        } finally { $bitmap.Dispose() }
    } finally { $image.Dispose() }
    Write-Output 'Image decoded.'
} catch {
    [Console]::Error.WriteLine('Image decode failed: ' + $_.Exception.Message)
    exit 1
}
