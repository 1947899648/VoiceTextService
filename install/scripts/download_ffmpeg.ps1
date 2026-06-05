$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
$zip = "ffmpeg_temp.zip"
$tempDir = "ffmpeg_temp"

try {
    Write-Host "Downloading FFmpeg (~80 MB) from GitHub ..."
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

    Write-Host "Extracting ..."
    Expand-Archive -Path $zip -DestinationPath $tempDir -Force

    $extracted = Get-ChildItem $tempDir -Directory | Select-Object -First 1
    if (-not $extracted) {
        throw "Failed to find extracted directory"
    }

    $binSource = Join-Path $extracted.FullName "bin"
    if (-not (Test-Path $binSource)) {
        throw "bin/ not found in extracted archive"
    }

    New-Item -ItemType Directory -Path "ffmpeg\bin" -Force | Out-Null
    Move-Item -Path "$binSource\*" -Destination "ffmpeg\bin" -Force

    Write-Host "FFmpeg installed to ffmpeg\bin\"
} finally {
    if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path $zip) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
}
