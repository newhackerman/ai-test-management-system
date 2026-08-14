param(
    [string]$TargetRoot = "D:\pythonTtest\ai-test-management-system",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$TestPath = "$PSScriptRoot\..\tests",
    [string]$AllureHome = "D:\pythonTtest\allure-2.29.0",
    [int]$Reruns = 1,
    [int]$RerunsDelay = 5,
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"

$pytestIni = (Resolve-Path (Join-Path $PSScriptRoot "..\pytest.ini")).Path
$pytestRoot = Split-Path $pytestIni -Parent

function Get-PytestIniValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Default
    )

    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or $trimmed.StartsWith(";")) {
            continue
        }

        $match = [regex]::Match($trimmed, "^(?<key>[A-Za-z0-9_-]+)\s*=\s*(?<value>.*)$")
        if ($match.Success -and $match.Groups["key"].Value -eq $Name) {
            return $match.Groups["value"].Value.Trim()
        }
    }

    return $Default
}

function Resolve-PytestTemplatePath {
    param(
        [string]$Template,
        [string]$Timestamp,
        [string]$Root
    )

    $expanded = $Template.Replace("{timestamp}", $Timestamp)
    if ([System.IO.Path]::IsPathRooted($expanded)) {
        return $expanded
    }

    return Join-Path $Root $expanded
}

function Copy-PreviousAllureHistory {
    param(
        [string]$ReportParent,
        [string]$CurrentReportDir,
        [string]$ResultsDir
    )

    if (-not (Test-Path $ReportParent)) {
        Write-Host "Allure history: no previous report parent found."
        return
    }

    $currentFullPath = [System.IO.Path]::GetFullPath($CurrentReportDir)
    $previous = Get-ChildItem -Directory $ReportParent |
        Where-Object {
            [System.IO.Path]::GetFullPath($_.FullName) -ne $currentFullPath -and
            (Test-Path (Join-Path $_.FullName "history\history-trend.json"))
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $previous) {
        Write-Host "Allure history: no previous report history found."
        return
    }

    $source = Join-Path $previous.FullName "history"
    $target = Join-Path $ResultsDir "history"
    if (Test-Path $target) {
        Remove-Item -Path $target -Recurse -Force
    }

    Copy-Item -Path $source -Destination $target -Recurse -Force
    Write-Host "Allure history: copied from $($previous.FullName)"
}

function Write-AllureExecutor {
    param(
        [string]$ResultsDir,
        [string]$Timestamp
    )

    $digitsOnly = ($Timestamp -replace "[^0-9]", "")
    if ($digitsOnly) {
        $buildOrder = [int64]$digitsOnly
    } else {
        $buildOrder = [int64][DateTimeOffset]::Now.ToUnixTimeSeconds()
    }

    $executor = [ordered]@{
        name = "local"
        type = "local"
        buildName = $Timestamp
        buildOrder = $buildOrder
        reportName = "Allure Report $Timestamp"
    }

    $json = $executor | ConvertTo-Json -Depth 4
    $target = Join-Path $ResultsDir "executor.json"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($target, $json, $utf8NoBom)
}

$timestampFormat = Get-PytestIniValue -Path $pytestIni -Name "aitms_allure_timestamp_format" -Default "yyyyMMdd_HHmmss"
$resultsTemplate = Get-PytestIniValue -Path $pytestIni -Name "aitms_allure_results_template" -Default "reports/allure-results/{timestamp}"
$reportTemplate = Get-PytestIniValue -Path $pytestIni -Name "aitms_allure_report_template" -Default "reports/allure-report/{timestamp}"

$timestamp = Get-Date -Format $timestampFormat
$resultsDir = Resolve-PytestTemplatePath -Template $resultsTemplate -Timestamp $timestamp -Root $pytestRoot
$reportDir = Resolve-PytestTemplatePath -Template $reportTemplate -Timestamp $timestamp -Root $pytestRoot
$reportParent = Split-Path $reportDir -Parent
$allure = Join-Path $AllureHome "bin\allure.bat"

if (-not (Test-Path $allure)) {
    throw "Allure executable not found: $allure"
}

New-Item -ItemType Directory -Force $resultsDir | Out-Null
New-Item -ItemType Directory -Force $reportDir | Out-Null

python -m pytest `
    $TestPath `
    -c $pytestIni `
    --aitms-target-root $TargetRoot `
    --aitms-base-url $BaseUrl `
    --aitms-frontend-url $FrontendUrl `
    --reruns $Reruns `
    --reruns-delay $RerunsDelay `
    --timeout $TimeoutSeconds `
    --tb=short `
    --alluredir $resultsDir

$pytestExit = $LASTEXITCODE

Copy-PreviousAllureHistory -ReportParent $reportParent -CurrentReportDir $reportDir -ResultsDir $resultsDir
Write-AllureExecutor -ResultsDir $resultsDir -Timestamp $timestamp

& $allure generate $resultsDir -o $reportDir
$allureExit = $LASTEXITCODE

Write-Host "Allure results: $((Resolve-Path $resultsDir).Path)"
Write-Host "Allure report:  $((Resolve-Path $reportDir).Path)"
Write-Host "Serve report:   .\scripts\serve_allure_report.ps1 -Port 8088"
Write-Host "Open report:    http://127.0.0.1:8088/"

if ($allureExit -ne 0) {
    exit $allureExit
}

exit $pytestExit
