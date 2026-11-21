"""
测试工具集成模块
提供统一的测试工具集成接口和管理功能
"""

from .allure_integration import (
    AllureConfig,
    AllureIntegration,
    AllureSeverity,
    AllureStatus,
    AllureTestResult,
    AttachmentType,
)
from .cicd_integration import (
    BuildInfo,
    BuildStatus,
    CICDIntegration,
    CIConfig,
    CIPlatform,
    TestTriggerConfig,
    TriggerType,
    WebhookPayload,
)
from .jmeter_integration import (
    HttpRequest,
    JMeterConfig,
    JMeterIntegration,
    LoadModel,
    LoadPattern,
    PerformanceMetrics,
)
from .jmeter_integration import TestResult as JMeterTestResult
from .jmeter_integration import TestType
from .playwright_integration import BrowserType
from .playwright_integration import ExecutionResult as PlaywrightExecutionResult
from .playwright_integration import ExecutionStatus as PlaywrightExecutionStatus
from .playwright_integration import PlaywrightConfig, PlaywrightIntegration
from .playwright_integration import TestCase as PlaywrightTestCase
from .playwright_integration import TestStep
from .security_tools import (
    ScanResult,
    ScanType,
    SecurityConfig,
    SecurityTestIntegration,
    SeverityLevel,
    Vulnerability,
    VulnerabilityType,
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