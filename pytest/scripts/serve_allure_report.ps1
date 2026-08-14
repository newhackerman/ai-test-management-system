param(
    [int]$Port = 8088,
    [string]$ReportRoot = "$PSScriptRoot\..\reports\allure-report"
)

$ErrorActionPreference = "Stop"

$latest = Get-ChildItem -Directory $ReportRoot |
    Where-Object { Test-Path (Join-Path $_.FullName "index.html") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latest) {
    $reportDirectory = $latest.FullName
} else {
    if (Test-Path (Join-Path $ReportRoot "index.html")) {
        $reportDirectory = (Resolve-Path $ReportRoot).Path
    } else {
        throw "No Allure report directory found under $ReportRoot"
    }
}

Write-Host "Serving Allure report from $reportDirectory"
Write-Host "Open: http://127.0.0.1:$Port/"

python -m http.server $Port --bind 127.0.0.1 --directory $reportDirectory
