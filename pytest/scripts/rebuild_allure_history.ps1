param(
    [string]$ReportRoot = "$PSScriptRoot\..\reports\allure-report",
    [string]$TargetReport = ""
)

$ErrorActionPreference = "Stop"

function Get-BuildOrder {
    param([string]$Name)

    $digitsOnly = ($Name -replace "[^0-9]", "")
    if ($digitsOnly) {
        return [int64]$digitsOnly
    }

    return [int64][DateTimeOffset]::Now.ToUnixTimeSeconds()
}

function Read-TrendEntry {
    param(
        [string]$ReportDir,
        [string]$FileName
    )

    $path = Join-Path $ReportDir "widgets\$FileName"
    if (-not (Test-Path $path)) {
        $path = Join-Path $ReportDir "history\$FileName"
    }
    if (-not (Test-Path $path)) {
        return $null
    }

    $items = Get-Content -Raw $path | ConvertFrom-Json
    if (-not $items) {
        return $null
    }

    if ($items -is [array]) {
        return $items[-1]
    }

    return $items
}

function New-TrendEntry {
    param(
        [object]$Source,
        [string]$ReportName,
        [int64]$BuildOrder
    )

    $entry = [ordered]@{
        buildOrder = $BuildOrder
        reportName = $ReportName
        data = $Source.data
    }

    return $entry
}

$reportRootPath = (Resolve-Path $ReportRoot).Path
$reports = Get-ChildItem -Directory $reportRootPath |
    Where-Object { Test-Path (Join-Path $_.FullName "index.html") } |
    Sort-Object Name

if (-not $reports) {
    throw "No Allure report directories found under $reportRootPath"
}

if ($TargetReport) {
    $target = Resolve-Path $TargetReport
    $targetDir = $target.Path
} else {
    $targetDir = ($reports | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

$trendFiles = @(
    "history-trend.json",
    "duration-trend.json",
    "retry-trend.json",
    "categories-trend.json"
)

foreach ($trendFile in $trendFiles) {
    $entries = @()
    foreach ($report in $reports) {
        $source = Read-TrendEntry -ReportDir $report.FullName -FileName $trendFile
        if (-not $source) {
            continue
        }

        $entries += New-TrendEntry `
            -Source $source `
            -ReportName $report.Name `
            -BuildOrder (Get-BuildOrder -Name $report.Name)
    }

    if (-not $entries) {
        continue
    }

    foreach ($folder in @("widgets", "history")) {
        $targetFolder = Join-Path $targetDir $folder
        New-Item -ItemType Directory -Force $targetFolder | Out-Null
        $targetPath = Join-Path $targetFolder $trendFile
        $json = $entries | ConvertTo-Json -Depth 8 -Compress
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($targetPath, $json, $utf8NoBom)
    }

    Write-Host "Rebuilt $trendFile with $($entries.Count) points."
}

Write-Host "Allure history rebuilt for $targetDir"
