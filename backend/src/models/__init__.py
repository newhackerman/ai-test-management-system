"""
模型初始化文件
"""
from .base import Base
from .user import User, UserRole, UserSession, UserLog, UserStatus, Gender
from .role import Role
from .permission import (
    Permission, PermissionType, RolePermission, UserPermission,
    PermissionGroup, PermissionGroupItem, DataPermission, UserDataPermission,
    PermissionEffect
)
from .config import (
    SystemConfig, ConfigGroup, ConfigHistory, ConfigAudit, 
    SystemEnvironment, ConfigPermission, ConfigType, Environment
)
from .config_template import ConfigTemplate
from .advanced_permissions import (
    AdvancedPermissionRule, TemporaryPermission, ScheduledPermission,
    RowLevelPermission, ColumnLevelPermission, PermissionAuditLog,
    PermissionApproval
)
from .ai_chat_session import AIChatSession, SessionStatus
from .ai_chat_message import AIChatMessage, MessageRole, ContentType
from .ai_model_config import AIModelConfig
from .ai_prompt_template import AIPromptTemplate, AIPromptTemplateUsage, TemplateCategory, TemplateVisibility
from .ai_usage_stats import AIUsageStats, AISystemStats
from .ai_suggestion import (
    AISuggestion, AIRequirementsAnalysis, AIRequirementsSuggestion,
    SuggestionType, SuggestionStatus, SuggestionPriority, SuggestionCategory
)
from .ai_file_storage import (
    AIFileStorage, AIFileShare, AIFileAccessLog,
    FileType, FileCategory, StorageProvider, FileStatus
)
from .ai_alert_config import (
    AIAlertConfig, AIAlertHistory, AIAlertSuppression,
    AlertType, AlertLevel, AlertStatus, NotificationChannel
)
from .ai_operation_log import (
    AIOperationLog, AIOperationLogSummary,
    AIOperationType, AIOperationResult, AIOperationPriority
)
from .system_notification import SystemNotification
from .project import (
    Project, ProjectMember, Task, Milestone, WorkLog, ProjectRisk,
    ProjectMetrics, ProjectChangeHistory, ProjectStatistics
)
from .requirement import (
    Requirement, RequirementStatusHistory, RequirementDependency,
    RequirementReview, RequirementReviewComment, RequirementChangeRequest,
    RequirementTraceabilityLink, RequirementType, RequirementStatus,
    Priority, BusinessValue, Complexity, DependencyType, ReviewType,
    ReviewStatus, ReviewDecision, CommentType, CommentSeverity,
    CommentStatus, ChangeType, ChangeStatus, ChangePriority,
    TraceabilityLinkType
)
from .test_plan import (
    TestPlan, TestPhase, TestResource,
    TestType, TestPlanStatus, TestPhaseStatus
)
from .test_case import (
    TestCase, TestExecution, Defect, TestCoverage, AutomationScript,
    TestCaseType, TestCasePriority, TestCaseStatus, ExecutionStatus,
    DefectSeverity, DefectStatus, DefectType, DefectResolution
)
from .test_report import (
    TestReportRecord, TestReportTemplate, TestReportSchedule, TestReportShare, TestReportComment
)
from .test_report_subscription import (
    TestReportSubscription, TestReportDistribution, TestReportVersion, TestReportAccessLog,
    SubscriptionType, DeliveryChannel, SubscriptionStatus
)
from .test_environment import (
    TestEnvironment, EnvironmentReservation, EnvironmentDeployment, TestData,
    EnvironmentStatus, EnvironmentType, ReservationStatus
)
from .defect_comment import DefectComment
from .requirement_classification import (
    RequirementClassificationDimension, RequirementClassificationCategory,
    RequirementClassification, RequirementClassificationSuggestion,
    RequirementTag, RequirementTagAssignment,
    ClassificationDimension, ClassificationStatus, ClassificationSuggestionStatus
)
# Dashboard management models
from .dashboard_config import (
    DashboardConfig, RoleType
)
from .widget_definition import (
    WidgetDefinition, WidgetCategory, DataSourceType
)
from .color_scheme import (
    ColorScheme, UserColorPreference, SchemeType, SchemeCategory
)
from .dashboard_data_cache import (
    DashboardDataCache, CacheStatistics, CacheDataType, CacheStatus
)
from .websocket_connection import (
    WebSocketConnection, WebSocketEvent, ConnectionPool,
    ConnectionStatus, EventType, ClientType
)
from .requirement_priority import (
    RequirementPriorityConfig, RequirementPriorityEvaluation,
    RequirementPriorityConflict, RequirementPriorityHistory,
    PriorityCalculationMethod, PriorityFactorType, ConflictResolutionStrategy,
    PriorityConflictStatus
)
from .requirement_permission import (
    RequirementRolePermission, RequirementUserPermission, RequirementResourcePermission,
    RequirementAuditLog, RequirementPermissionTemplate,
    RequirementPermissionType, RequirementDataScope, RequirementPermissionEffect,
    RequirementAuditAction, RequirementAuditResult
)
from .meeting import (
    Meeting, MeetingParticipant, MeetingRecording, MeetingMinutes,
    MeetingChat, MeetingFile, MeetingAnalytics, MeetingTemplate,
    MeetingType, MeetingStatus, ParticipantRole, InvitationStatus,
    AttendanceStatus, RecordingType, RecordingStatus, FileFormat,
    MinuteType, GenerationMethod, MinuteStatus, MessageType,
    FileShareStatus, TemplateCategory
)

# 导出所有模型
__all__ = [
    "Base",
    "User",
    "UserRole",
    "UserSession",
    "UserLog",
    "UserStatus",
    "Gender",
    "Role",
    "Permission",
    "PermissionType",
    "PermissionEffect",
    "RolePermission",
    "UserPermission",
    "PermissionGroup",
    "PermissionGroupItem",
    "DataPermission",
    "UserDataPermission",
    "SystemConfig",
    "ConfigGroup",
    "ConfigHistory",
    "ConfigAudit",
    "SystemEnvironment",
    "ConfigPermission",
    "ConfigType",
    "Environment",
    "ConfigTemplate",
    "AdvancedPermissionRule",
    "TemporaryPermission",
    "ScheduledPermission",
    "RowLevelPermission",
    "ColumnLevelPermission",
    "PermissionAuditLog",
    "PermissionApproval",
    "AIChatSession",
    "SessionStatus",
    "AIChatMessage",
    "MessageRole",
    "ContentType",
    "AIModelConfig",
    "AIPromptTemplate",
    "AIPromptTemplateUsage",
    "TemplateCategory",
    "TemplateVisibility",
    "AIUsageStats",
    "AISystemStats",
    "AISuggestion",
    "AIRequirementsAnalysis", 
    "AIRequirementsSuggestion",
    "SuggestionType",
    "SuggestionStatus",
    "SuggestionPriority",
    "SuggestionCategory",
    "AIFileStorage",
    "AIFileShare",
    "AIFileAccessLog",
    "FileType",
    "FileCategory",
    "StorageProvider",
    "FileStatus",
    "AIAlertConfig",
    "AIAlertHistory",
    "AIAlertSuppression",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "NotificationChannel",
    "AIOperationLog",
    "AIOperationLogSummary",
    "AIOperationType",
    "AIOperationResult",
    "AIOperationPriority",
    "SystemNotification",
    "Project",
    "ProjectMember",
    "Task",
    "Milestone",
    "WorkLog",
    "ProjectRisk",
    "Requirement",
    "RequirementStatusHistory",
    "RequirementDependency",
    "RequirementReview",
    "RequirementReviewComment",
    "RequirementChangeRequest",
    "RequirementTraceabilityLink",
    "RequirementType",
    "RequirementStatus",
    "Priority",
    "BusinessValue",
    "Complexity",
    "DependencyType",
    "ReviewType",
    "ReviewStatus",
    "ReviewDecision",
    "CommentType",
    "CommentSeverity",
    "CommentStatus",
    "ChangeType",
    "ChangeStatus",
    "ChangePriority",
    "TraceabilityLinkType",
    # Classification models
    "RequirementClassificationDimension",
    "RequirementClassificationCategory",
    "RequirementClassification",
    "RequirementClassificationSuggestion",
    "RequirementTag",
    "RequirementTagAssignment",
    "ClassificationDimension",
    "ClassificationStatus",
    "ClassificationSuggestionStatus",
    # Priority models
    "RequirementPriorityConfig",
    "RequirementPriorityEvaluation",
    "RequirementPriorityConflict",
    "RequirementPriorityHistory",
    "PriorityCalculationMethod",
    "PriorityFactorType",
    "ConflictResolutionStrategy",
    "PriorityConflictStatus",
    # Permission models
    "RequirementRolePermission",
    "RequirementUserPermission",
    "RequirementResourcePermission",
    "RequirementAuditLog",
    "RequirementPermissionTemplate",
    "RequirementPermissionType",
    "RequirementDataScope",
    "RequirementPermissionEffect",
    "RequirementAuditAction",
    "RequirementAuditResult",
    "ProjectMetrics",
    "ProjectChangeHistory",
    "ProjectStatistics",
    # Test management models
    "TestPlan",
    "TestPhase", 
    "TestResource",
    "TestType",
    "TestPlanStatus",
    "TestPhaseStatus",
    "TestCase",
    "TestExecution",
    "Defect",
    "TestCoverage",
    "AutomationScript",
    "TestCaseType",
    "TestCasePriority",
    "TestCaseStatus",
    "ExecutionStatus",
    "DefectSeverity",
    "DefectStatus",
    "DefectType",
    "DefectResolution",
    "TestReportRecord",
    "TestReportTemplate",
    "TestReportSchedule",
    "TestReportShare",
    "TestReportComment",
    "TestReportSubscription",
    "TestReportDistribution", 
    "TestReportVersion",
    "TestReportAccessLog",
    "SubscriptionType",
    "DeliveryChannel",
    "SubscriptionStatus",
    "TestEnvironment",
    "EnvironmentReservation",
    "EnvironmentDeployment",
    "TestData",
    "EnvironmentStatus",
    "EnvironmentType",
    "ReservationStatus",
    "DefectComment",
    # Dashboard management models
    "DashboardConfig",
    "DashboardTemplate", 
    "UserDashboardPreference",
    "RoleType",
    "WidgetDefinition",
    "WidgetDataSource",
    "WidgetPermission",
    "WidgetUsageLog",
    "WidgetRating",
    "WidgetCategory",
    "WidgetType",
    "DataSourceType",
    "ColorScheme",
    "UserColorPreference",
    "ColorSchemeRating",
    "ColorSchemeUsageLog",
    "EnterpriseColorScheme",
    "SchemeType",
    "SchemeCategory",
    "DashboardDataCache",
    "CachePerformanceMetric",
    "CacheCleanupLog",
    "CacheConfiguration",
    "CacheDataType",
    "CacheStatus",
    "WebSocketConnection",
    "WebSocketMessage",
    "WebSocketEvent",
    "ConnectionPool",
    "ConnectionStatus",
    "EventType",
    # Meeting models
    "Meeting",
    "MeetingParticipant", 
    "MeetingRecording",
    "MeetingMinutes",
    "MeetingChat",
    "MeetingFile",
    "MeetingAnalytics",
    "MeetingTemplate",
    "MeetingType",
    "MeetingStatus",
    "ParticipantRole",
    "InvitationStatus",
    "AttendanceStatus",
    "RecordingType",
    "RecordingStatus",
    "FileFormat",
    "MinuteType",
    "GenerationMethod",
    "MinuteStatus",
    "MessageType",
    "FileShareStatus",
    "TemplateCategory"
]
