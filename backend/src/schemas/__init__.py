"""
数据模型模块 - 包含所有API请求和响应的数据模型
"""
from .auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    RegisterRequest, RegisterResponse, ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, MFASetupRequest, MFASetupResponse, MFAVerifyRequest, MFAVerifyResponse,
    MFADisableRequest, CaptchaResponse, UserSessionsResponse, LogoutRequest, LogoutResponse,
    VerifyEmailRequest, VerifyEmailResponse, ResendVerificationEmailRequest, ResendVerificationEmailResponse
)
from .user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserPermissionsResponse, BatchUserOperation, BatchOperationResponse,
    PasswordChangeRequest, PasswordResetRequest, UserLockRequest, UserUnlockRequest,
    UserRoleAssignment, UserSearchParams, UserStats, UserProfileUpdate,
    UserStatus, Gender
)
from .ai_file_storage import (
    FileUploadResponse, FileInfoResponse, FileListResponse, FileShareRequest, FileShareResponse,
    StorageStatsResponse, FileAccessLogResponse, FileMetadata, FileUploadRequest, FileUpdateRequest,
    FileBatchUploadResponse, FileBatchDeleteResponse, FileSearchRequest, FileStorageConfig,
    FileCleanupConfig, FileSecurityConfig
)
from .permission import (
    PermissionType, PermissionEffect, PermissionCreate, PermissionUpdate,
    PermissionResponse, PermissionListResponse, UserPermissionAssignment,
    RolePermissionAssignment, PermissionCheckRequest, PermissionCheckResponse,
    PermissionTreeNode, PermissionGroupCreate, PermissionGroupUpdate,
    PermissionGroupResponse, DataPermissionCreate, DataPermissionUpdate,
    DataPermissionResponse
)
from .config import (
    ConfigCreateRequest, ConfigUpdateRequest, ConfigResponse, ConfigListResponse,
    ConfigSearchRequest, ConfigGroupCreateRequest, ConfigGroupUpdateRequest, ConfigGroupResponse,
    ConfigHistoryResponse, ConfigAuditCreateRequest, ConfigAuditResponse,
    ConfigBatchUpdateRequest, ConfigExportRequest, ConfigImportRequest,
    ConfigValidationRequest, ConfigValidationResponse, ApiResponse
)
from .conversation import (
    CreateConversationRequest, ConversationResponse, ConversationListResponse,
    UpdateConversationRequest, SendMessageRequest, MessageResponse, MessageListResponse,
    ConversationStatsResponse, SearchConversationsRequest, ConversationContextResponse,
    ConversationGroupEnum
)
from .prompt_template import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    PromptTemplateListResponse, TemplateRenderRequest, TemplateRenderResponse,
    TemplateUsageCreate, TemplateUsageResponse, TemplateSearchRequest,
    TemplateStatistics, TemplateVariable, TemplateCategory, TemplateVisibility
)
from .requirement_change import (
    ChangeTypeEnum, ChangeStatusEnum, ChangePriorityEnum,
    ChangeRequestCreate, ChangeRequestUpdate, ChangeRequestApproval,
    ChangeRequestResponse, ChangeRequestListResponse,
    ImpactAnalysisRequest, ImpactAnalysisResponse, ImpactItem,
    ChangeImplementationRequest, ChangeImplementationResponse
)

__all__ = [
    "LoginRequest", "LoginResponse", "RefreshTokenRequest", "RefreshTokenResponse",
    "RegisterRequest", "RegisterResponse", "ForgotPasswordRequest", "ResetPasswordRequest",
    "ChangePasswordRequest", "MFASetupRequest", "MFASetupResponse", "MFAVerifyRequest", "MFAVerifyResponse",
    "MFADisableRequest", "CaptchaResponse", "UserSessionsResponse", "LogoutRequest", "LogoutResponse",
    "VerifyEmailRequest", "VerifyEmailResponse", "ResendVerificationEmailRequest", "ResendVerificationEmailResponse",
    "UserCreate", "UserUpdate", "UserResponse", "UserListResponse",
    "UserPermissionsResponse", "BatchUserOperation", "BatchOperationResponse",
    "PasswordChangeRequest", "PasswordResetRequest", "UserLockRequest", "UserUnlockRequest",
    "UserRoleAssignment", "UserSearchParams", "UserStats", "UserProfileUpdate",
    "UserStatus", "Gender",
    "FileUploadResponse", "FileInfoResponse", "FileListResponse", "FileShareRequest", "FileShareResponse",
    "StorageStatsResponse", "FileAccessLogResponse", "FileMetadata", "FileUploadRequest", "FileUpdateRequest",
    "FileBatchUploadResponse", "FileBatchDeleteResponse", "FileSearchRequest", "FileStorageConfig",
    "FileCleanupConfig", "FileSecurityConfig",
    "PermissionType", "PermissionEffect", "PermissionCreate", "PermissionUpdate",
    "PermissionResponse", "PermissionListResponse", "UserPermissionAssignment",
    "RolePermissionAssignment", "PermissionCheckRequest", "PermissionCheckResponse",
    "PermissionTreeNode", "PermissionGroupCreate", "PermissionGroupUpdate",
    "PermissionGroupResponse", "DataPermissionCreate", "DataPermissionUpdate",
    "DataPermissionResponse",
    "ConfigCreateRequest", "ConfigUpdateRequest", "ConfigResponse", "ConfigListResponse",
    "ConfigSearchRequest", "ConfigGroupCreateRequest", "ConfigGroupUpdateRequest", "ConfigGroupResponse",
    "ConfigHistoryResponse", "ConfigAuditCreateRequest", "ConfigAuditResponse",
    "ConfigBatchUpdateRequest", "ConfigExportRequest", "ConfigImportRequest",
    "ConfigValidationRequest", "ConfigValidationResponse", "ApiResponse",
    "CreateConversationRequest", "ConversationResponse", "ConversationListResponse",
    "UpdateConversationRequest", "SendMessageRequest", "MessageResponse", "MessageListResponse",
    "ConversationStatsResponse", "SearchConversationsRequest", "ConversationContextResponse",
    "ConversationGroupEnum",
    "PromptTemplateCreate", "PromptTemplateUpdate", "PromptTemplateResponse",
    "PromptTemplateListResponse", "TemplateRenderRequest", "TemplateRenderResponse",
    "TemplateUsageCreate", "TemplateUsageResponse", "TemplateSearchRequest",
    "TemplateStatistics", "TemplateVariable", "TemplateCategory", "TemplateVisibility",
    "ChangeTypeEnum", "ChangeStatusEnum", "ChangePriorityEnum",
    "ChangeRequestCreate", "ChangeRequestUpdate", "ChangeRequestApproval",
    "ChangeRequestResponse", "ChangeRequestListResponse",
    "ImpactAnalysisRequest", "ImpactAnalysisResponse", "ImpactItem",
    "ChangeImplementationRequest", "ChangeImplementationResponse"
]