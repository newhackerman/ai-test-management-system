param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [int]$Reruns = 0,
    [int]$TimeoutSeconds = 15,
    [int]$PreferredPort = 8089
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runAllure = Join-Path $PSScriptRoot "run_allure_tests.ps1"
$rebuildHistory = Join-Path $PSScriptRoot "rebuild_allure_history.ps1"
$reportRoot = Join-Path $repoRoot "reports\allure-report"

function Get-LatestAllureReport {
    param([string]$Root)

    return Get-ChildItem -Directory $Root |
        Where-Object { Test-Path (Join-Path $_.FullName "index.html") } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-FreePort {
    param([int]$StartPort)

    foreach ($port in $StartPort..($StartPort + 20)) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $port)
            $listener.Start()
            return $port
        } catch {
            continue
        } finally {
            if ($listener) {
                $listener.Stop()
            }
        }
    }

    throw "No free local port found from $StartPort to $($StartPort + 20)."
}

Set-Location $repoRoot

Write-Host "Running full pytest suite and generating Allure report..."
Write-Host "Base URL:     $BaseUrl"
Write-Host "Frontend URL: $FrontendUrl"
Write-Host "Reruns:       $Reruns"
Write-Host "Timeout:      $TimeoutSeconds seconds"
Write-Host ""

& $runAllure `
    -BaseUrl $BaseUrl `
    -FrontendUrl $FrontendUrl `
    -Reruns $Reruns `
    -TimeoutSeconds $TimeoutSeconds

$pytestExit = $LASTEXITCODE

$latest = Get-LatestAllureReport -Root $reportRoot
if (-not $latest) {
    throw "Allure report was not generated under $reportRoot."
}

Write-Host ""
Write-Host "Rebuilding Allure trend history for latest report..."
& $rebuildHistory -ReportRoot $reportRoot -TargetReport $latest.FullName

$port = Get-FreePort -StartPort $PreferredPort
$url = "http://127.0.0.1:$port/"

Write-Host ""
Write-Host "Allure report: $($latest.FullName)"
Write-Host "Opening:       $url"
Write-Host "Close this window to stop the report server."
Write-Host ""

cmd.exe /c start "" $url
python -m http.server $port --bind 127.0.0.1 --directory $latest.FullName

exit $pytestExit
