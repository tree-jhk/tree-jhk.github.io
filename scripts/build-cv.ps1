$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$htmlPath = Join-Path $repoRoot "cv.html"
$pdfPath = Join-Path $repoRoot "assets\pdf\CV.pdf"
$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)
$browser = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $browser) {
    throw "Google Chrome or Microsoft Edge was not found."
}

$fileUrl = "file:///" + ($htmlPath -replace '\\', '/')
& $browser --headless=new --disable-gpu --no-pdf-header-footer "--print-to-pdf=$pdfPath" $fileUrl

if (-not (Test-Path $pdfPath)) {
    throw "CV generation failed: $pdfPath"
}

Write-Host "Generated $pdfPath"
