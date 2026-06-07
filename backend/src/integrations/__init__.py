"""
测试工具集成模块
提供统一的测试工具集成接口和管理功能
"""

from .playwright_integration import (
    PlaywrightIntegration,
    PlaywrightConfig,
    TestCase as PlaywrightTestCase,
    TestStep,
    ExecutionResult as PlaywrightExecutionResult,
    BrowserType,
    ExecutionStatus as PlaywrightExecutionStatus
)

from .jmeter_integration import (
    JMeterIntegration,
    JMeterConfig,
    HttpRequest,
    LoadModel,
    LoadPattern,
    TestType,
    PerformanceMetrics,
    TestResult as JMeterTestResult
)

from .security_tools import (
    SecurityTestIntegration,
    SecurityConfig,
    Vulnerability,
    ScanResult,
    SeverityLevel,
    ScanType,
    VulnerabilityType
)

from .allure_integration import (
    AllureIntegration,
    AllureConfig,
    AllureTestResult,
    AllureStatus,
    AllureSeverity,
    AttachmentType
)

from .cicd_integration import (
    CICDIntegration,
    CIConfig,
    TestTriggerConfig,
    BuildInfo,
    WebhookPayload,
    CIPlatform,
    BuildStatus,
    TriggerType
)

__all__ = [
    # Playwright
    "PlaywrightIntegration",
    "PlaywrightConfig",
    "PlaywrightTestCase",
    "TestStep",
    "PlaywrightExecutionResult",
    "BrowserType",
    "PlaywrightExecutionStatus",
    
    # JMeter
    "JMeterIntegration",
    "JMeterConfig",
    "HttpRequest",
    "LoadModel",
    "LoadPattern",
    "TestType",
    "PerformanceMetrics",
    "JMeterTestResult",
    
    # Security Tools
    "SecurityTestIntegration",
    "SecurityConfig",
    "Vulnerability",
    "ScanResult",
    "SeverityLevel",
    "ScanType",
    "VulnerabilityType",
    
    # Allure
    "AllureIntegration",
    "AllureConfig",
    "AllureTestResult",
    "AllureStatus",
    "AllureSeverity",
    "AttachmentType",
    
    # CI/CD
    "CICDIntegration",
    "CIConfig",
    "TestTriggerConfig",
    "BuildInfo",
    "WebhookPayload",
    "CIPlatform",
    "BuildStatus",
    "TriggerType"
]