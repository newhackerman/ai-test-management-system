param(
    [string]$TargetRoot = "D:\pythonTtest\ai-test-management-system",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [switch]$WithLive
)

$ErrorActionPreference = "Stop"

$marker = "not live and not e2e"
if ($WithLive) {
    $marker = "not e2e"
}

python -m pytest `
    "$PSScriptRoot\..\tests" `
    -c "$PSScriptRoot\..\pytest.ini" `
    --aitms-target-root $TargetRoot `
    --aitms-base-url $BaseUrl `
    --aitms-frontend-url $FrontendUrl `
    -m $marker `
    --html reports/pytest-report.html `
    --self-contained-html `
    --junitxml reports/junit.xml

exit $LASTEXITCODE
