import os
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, EmailStr, HttpUrl, field_validator
# Handle BaseSettings import for different Pydantic versions
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Fallback for older versions or missing pydantic-settings
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
from functools import lru_cache


class Settings(BaseSettings):
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI测试管理系统 - 用户管理模块"
    
    # API路由配置
    API_ROUTES: Dict[str, Dict[str, str]] = {
        "auth": {"prefix": "/auth", "tags": "认证管理"},
        "auth_permissions": {"prefix": "/auth-permissions", "tags": "认证权限"},
        "users": {"prefix": "/users", "tags": "用户管理"},
        "roles": {"prefix": "/roles", "tags": "角色管理"},
        "permissions": {"prefix": "/permissions", "tags": "权限管理"},
        "configs": {"prefix": "/configs", "tags": "配置管理"},
        "audit": {"prefix": "/configs", "tags": "配置审核"},
        "import_export": {"prefix": "/configs", "tags": "配置导入导出"},
        "websocket": {"prefix": "", "tags": "WebSocket实时通信"},
        "validation_rules": {"prefix": "/configs", "tags": "配置验证规则"},
        "advanced_permissions": {"prefix": "/configs", "tags": "高级权限管理"},
        "dashboards": {"prefix": "/dashboards", "tags": "仪表板管理"},
        "ai_assistant": {"prefix": "/ai-assistant", "tags": "AI助手"},
        "ai_queue": {"prefix": "/ai-queue", "tags": "AI请求队列"},
        "streaming": {"prefix": "/streaming", "tags": "流式响应"},
        "ai_websocket": {"prefix": "/ai-websocket", "tags": "AI WebSocket连接"},
        "cost_control": {"prefix": "/cost-control", "tags": "成本控制"},
        "ai_suggestions": {"prefix": "/ai-suggestions", "tags": "AI建议"},
        "prompt_templates": {"prefix": "/prompt-templates", "tags": "提示词模板"},
        "ai_model_config": {"prefix": "/ai-model-config", "tags": "AI模型配置"},
        "ai_alert_config": {"prefix": "/ai-alert-config", "tags": "AI告警配置"},
        "health_websocket": {"prefix": "/health-websocket", "tags": "健康监控WebSocket"},
        "ai_permissions": {"prefix": "/ai-permissions", "tags": "AI权限管理"},
        "ai_operation_logs": {"prefix": "", "tags": "AI操作日志"},
        "cache_preheating": {"prefix": "/cache-preheating", "tags": "缓存预热管理"},
        "baidu_wenxin": {"prefix": "/baidu-wenxin", "tags": "百度文心一言"},
        "aliyun_tongyi": {"prefix": "/aliyun-tongyi", "tags": "阿里通义千问"},
        "chinese_routing": {"prefix": "/chinese-routing", "tags": "中文内容优化路由"},
        "multilingual": {"prefix": "/multilingual", "tags": "多语言响应处理"},
        "projects": {"prefix": "/projects", "tags": "项目管理"},
        "teams": {"prefix": "", "tags": "团队管理"},
        "tasks": {"prefix": "", "tags": "任务管理"},
        "risks": {"prefix": "", "tags": "风险管理"},
        "milestones": {"prefix": "", "tags": "里程碑管理"},
        "progress": {"prefix": "", "tags": "进度管理"}
    }
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
    ]
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_backend_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    # JWT配置
    JWT_SECRET_KEY: str = os.urandom(32).hex()
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 1
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 数据库配置
    DATABASE_URL: str = "mysql+asyncmy://aitest:AItestdb123@localhost:3306/aitestdb"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API路由前缀配置（可从环境变量覆盖）
    API_AUTH_PREFIX: str = "/auth"
    API_USERS_PREFIX: str = "/users"
    API_ROLES_PREFIX: str = "/roles"
    API_PERMISSIONS_PREFIX: str = "/permissions"
    API_CONFIGS_PREFIX: str = "/configs"
    API_AI_ASSISTANT_PREFIX: str = "/ai-assistant"
    API_AI_QUEUE_PREFIX: str = "/ai-queue"
    API_STREAMING_PREFIX: str = "/streaming"
    API_AI_WEBSOCKET_PREFIX: str = "/ai-websocket"
    API_COST_CONTROL_PREFIX: str = "/cost-control"
    API_AI_SUGGESTIONS_PREFIX: str = "/ai-suggestions"
    API_PROMPT_TEMPLATES_PREFIX: str = "/prompt-templates"
    API_AI_MODEL_CONFIG_PREFIX: str = "/ai-model-config"
    API_AI_ALERT_CONFIG_PREFIX: str = "/ai-alert-config"
    API_HEALTH_WEBSOCKET_PREFIX: str = "/health-websocket"
    API_AI_PERMISSIONS_PREFIX: str = "/ai-permissions"
    API_AI_FILES_PREFIX: str = "/ai/files"
    API_CACHE_PREHEATING_PREFIX: str = "/cache-preheating"
    API_BAIDU_WENXIN_PREFIX: str = "/baidu-wenxin"
    API_ALIYUN_TONGYI_PREFIX: str = "/aliyun-tongyi"
    API_PROJECTS_PREFIX: str = "/projects"
    API_CHINESE_ROUTING_PREFIX: str = "/chinese-routing"
    API_MULTILINGUAL_PREFIX: str = "/multilingual"
    API_DASHBOARDS_PREFIX: str = "/dashboards"
    
    # API标签配置
    API_AUTH_TAGS: str = "认证管理"
    API_AUTH_PERMISSIONS_TAGS: str = "认证权限"
    API_USERS_TAGS: str = "用户管理"
    API_ROLES_TAGS: str = "角色管理"
    API_PERMISSIONS_TAGS: str = "权限管理"
    API_CONFIGS_TAGS: str = "配置管理"
    API_AUDIT_TAGS: str = "配置审核"
    API_IMPORT_EXPORT_TAGS: str = "配置导入导出"
    API_WEBSOCKET_TAGS: str = "WebSocket实时通信"
    API_VALIDATION_RULES_TAGS: str = "配置验证规则"
    API_ADVANCED_PERMISSIONS_TAGS: str = "高级权限管理"
    API_AI_ASSISTANT_TAGS: str = "AI助手"
    API_AI_QUEUE_TAGS: str = "AI请求队列"
    API_STREAMING_TAGS: str = "流式响应"
    API_AI_WEBSOCKET_TAGS: str = "AI WebSocket连接"
    API_COST_CONTROL_TAGS: str = "成本控制"
    API_AI_SUGGESTIONS_TAGS: str = "AI建议"
    API_PROMPT_TEMPLATES_TAGS: str = "提示词模板"
    API_AI_MODEL_CONFIG_TAGS: str = "AI模型配置"
    API_AI_ALERT_CONFIG_TAGS: str = "AI告警配置"
    API_HEALTH_WEBSOCKET_TAGS: str = "健康监控WebSocket"
    API_AI_PERMISSIONS_TAGS: str = "AI权限管理"
    API_AI_FILES_TAGS: str = "AI文件存储"
    API_AI_OPERATION_LOGS_TAGS: str = "AI操作日志"
    API_CACHE_PREHEATING_TAGS: str = "缓存预热管理"
    API_BAIDU_WENXIN_TAGS: str = "百度文心一言"
    API_ALIYUN_TONGYI_TAGS: str = "阿里通义千问"
    API_CHINESE_ROUTING_TAGS: str = "中文内容优化路由"
    API_MULTILINGUAL_TAGS: str = "多语言响应处理"
    API_PROJECTS_TAGS: str = "项目管理"
    API_DASHBOARDS_TAGS: str = "仪表板管理"
    
    # 调试模式
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # 允许的主机
    ALLOWED_HOSTS: str = "*"
    
    # 安全配置
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 60
    
    # 密码策略
    MIN_PASSWORD_LENGTH: int = 8
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_COMPLEXITY: bool = True
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SYMBOLS: bool = True
    PASSWORD_MAX_AGE_DAYS: int = 90
    
    # 邮件配置
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None
    EMAIL_ENABLED: bool = False
    SMTP_USERNAME: Optional[str] = None
    
    # 双因素认证
    TWO_FACTOR_AUTH_ENABLED: bool = True
    TWO_FACTOR_AUTH_ISSUER: str = "AI测试管理系统"
    
    # 短信配置
    SMS_ENABLED: bool = False
    SMS_PROVIDER: Optional[str] = None
    SMS_ACCESS_KEY: Optional[str] = None
    SMS_SECRET_KEY: Optional[str] = None
    
    # 文件上传
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 104857600  # 100MB
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 1 hour
    
    # 仪表板配置
    DASHBOARD_CACHE_TTL: int = 300  # 5分钟
    DASHBOARD_MAX_WIDGETS: int = 20
    DASHBOARD_MAX_CONFIGS_PER_USER: int = 10
    DASHBOARD_DEFAULT_REFRESH_INTERVAL: int = 30  # 30秒
    DASHBOARD_MIN_REFRESH_INTERVAL: int = 10      # 最小10秒
    DASHBOARD_MAX_REFRESH_INTERVAL: int = 3600    # 最大1小时
    
    # WebSocket配置
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # 30秒心跳
    WEBSOCKET_TIMEOUT: int = 300            # 5分钟超时
    MAX_WEBSOCKET_CONNECTIONS: int = 1000   # 最大连接数
    
    # 百度文心一言配置
    BAIDU_API_KEY: Optional[str] = None
    BAIDU_SECRET_KEY: Optional[str] = None
    BAIDU_BASE_URL: Optional[str] = "https://aip.baidubce.com"
    BAIDU_ENVIRONMENT: str = "production"  # production, sandbox, development
    BAIDU_TIMEOUT: float = 30.0
    BAIDU_MAX_CONCURRENT: int = 20
    BAIDU_DAILY_COST_LIMIT: Optional[float] = None
    BAIDU_MONTHLY_COST_LIMIT: Optional[float] = None
    BAIDU_ENABLE_STREAMING: bool = True
    BAIDU_ENABLE_CACHING: bool = True
    BAIDU_ENABLE_MONITORING: bool = True
    
    # 阿里通义千问配置
    ALIYUN_API_KEY: Optional[str] = None
    ALIYUN_API_ENDPOINT: Optional[str] = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    ALIYUN_ENVIRONMENT: str = "production"  # production, sandbox, development
    ALIYUN_TIMEOUT: float = 30.0
    ALIYUN_MAX_CONCURRENT: int = 20
    ALIYUN_MAX_RETRIES: int = 3
    ALIYUN_DAILY_COST_LIMIT: Optional[float] = None
    ALIYUN_MONTHLY_COST_LIMIT: Optional[float] = None
    ALIYUN_ENABLE_STREAMING: bool = True
    ALIYUN_ENABLE_CACHING: bool = True
    ALIYUN_ENABLE_MONITORING: bool = True
    ALIYUN_ENABLE_CONTEXT_ENHANCEMENT: bool = True
    ALIYUN_USE_CHINESE_PUNCTUATION: bool = True
    ALIYUN_OPTIMIZE_FOR_CHINESE_CULTURE: bool = True
    ALIYUN_ENABLE_IDIOM_USAGE: bool = True
    ALIYUN_ENHANCE_POLITENESS: bool = True
    ALIYUN_PREFER_FORMAL_LANGUAGE: bool = False
    
    # OpenAI配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None
    OPENAI_AUTH_SCHEME: str = "bearer"
    OPENAI_API_ENDPOINT: Optional[str] = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4"
    OPENAI_ENVIRONMENT: str = "production"  # production, sandbox, development
    OPENAI_TIMEOUT: float = 90.0
    OPENAI_MAX_CONCURRENT: int = 20
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_DAILY_COST_LIMIT: Optional[float] = None
    OPENAI_MONTHLY_COST_LIMIT: Optional[float] = None
    OPENAI_ENABLE_STREAMING: bool = True
    OPENAI_ENABLE_CACHING: bool = True
    OPENAI_ENABLE_MONITORING: bool = True
    OPENAI_ENABLE_FUNCTION_CALLING: bool = True
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 4000
    
    # Allure报告配置
    ALLURE_ENABLED: bool = True
    ALLURE_BASE_PATH: str = "reports/allure"
    ALLURE_COMMAND: str = "allure"
    ALLURE_RESULTS_DIR: str = "allure-results"
    ALLURE_REPORT_DIR: str = "allure-report"
    ALLURE_CLEAN_RESULTS: bool = True
    ALLURE_GENERATE_REPORT: bool = True
    ALLURE_OPEN_REPORT: bool = False
    ALLURE_HISTORY_TREND: bool = True
    ALLURE_SERVE_PORT: int = 0
    ALLURE_AUTO_CLEANUP: bool = True
    ALLURE_MAX_REPORT_AGE_DAYS: int = 30
    ALLURE_CATEGORIES_FILE: Optional[str] = None
    ALLURE_ENVIRONMENT_FILE: Optional[str] = None
    TEST_ENVIRONMENT: str = "QA"
    
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "allow",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_route_config(route_name: str) -> Dict[str, str]:
    """获取路由配置"""
    settings = get_settings()
    
    route_configs = {
        "auth": {
            "prefix": settings.API_AUTH_PREFIX,
            "tags": [settings.API_AUTH_TAGS]
        },
        "auth_permissions": {
            "prefix": "/auth-permissions",
            "tags": [settings.API_AUTH_PERMISSIONS_TAGS]
        },
        "users": {
            "prefix": settings.API_USERS_PREFIX,
            "tags": [settings.API_USERS_TAGS]
        },
        "roles": {
            "prefix": settings.API_ROLES_PREFIX,
            "tags": [settings.API_ROLES_TAGS]
        },
        "permissions": {
            "prefix": settings.API_PERMISSIONS_PREFIX,
            "tags": [settings.API_PERMISSIONS_TAGS]
        },
        "configs": {
            "prefix": settings.API_CONFIGS_PREFIX,
            "tags": [settings.API_CONFIGS_TAGS]
        },
        "audit": {
            "prefix": settings.API_CONFIGS_PREFIX,
            "tags": [settings.API_AUDIT_TAGS]
        },
        "import_export": {
            "prefix": settings.API_CONFIGS_PREFIX,
            "tags": [settings.API_IMPORT_EXPORT_TAGS]
        },
        "websocket": {
            "prefix": "",
            "tags": [settings.API_WEBSOCKET_TAGS]
        },
        "validation_rules": {
            "prefix": settings.API_CONFIGS_PREFIX,
            "tags": [settings.API_VALIDATION_RULES_TAGS]
        },
        "advanced_permissions": {
            "prefix": settings.API_CONFIGS_PREFIX,
            "tags": [settings.API_ADVANCED_PERMISSIONS_TAGS]
        },
        "ai_assistant": {
            "prefix": settings.API_AI_ASSISTANT_PREFIX,
            "tags": [settings.API_AI_ASSISTANT_TAGS]
        },
        "ai_queue": {
            "prefix": settings.API_AI_QUEUE_PREFIX,
            "tags": [settings.API_AI_QUEUE_TAGS]
        },
        "streaming": {
            "prefix": settings.API_STREAMING_PREFIX,
            "tags": [settings.API_STREAMING_TAGS]
        },
        "ai_websocket": {
            "prefix": settings.API_AI_WEBSOCKET_PREFIX,
            "tags": [settings.API_AI_WEBSOCKET_TAGS]
        },
        "cost_control": {
            "prefix": settings.API_COST_CONTROL_PREFIX,
            "tags": [settings.API_COST_CONTROL_TAGS]
        },
        "ai_suggestions": {
            "prefix": settings.API_AI_SUGGESTIONS_PREFIX,
            "tags": [settings.API_AI_SUGGESTIONS_TAGS]
        },
        "prompt_templates": {
            "prefix": settings.API_PROMPT_TEMPLATES_PREFIX,
            "tags": [settings.API_PROMPT_TEMPLATES_TAGS]
        },
        "ai_model_config": {
            "prefix": settings.API_AI_MODEL_CONFIG_PREFIX,
            "tags": [settings.API_AI_MODEL_CONFIG_TAGS]
        },
        "ai_alert_config": {
            "prefix": settings.API_AI_ALERT_CONFIG_PREFIX,
            "tags": [settings.API_AI_ALERT_CONFIG_TAGS]
        },
        "health_websocket": {
            "prefix": settings.API_HEALTH_WEBSOCKET_PREFIX,
            "tags": [settings.API_HEALTH_WEBSOCKET_TAGS]
        },
        "ai_permissions": {
            "prefix": settings.API_AI_PERMISSIONS_PREFIX,
            "tags": [settings.API_AI_PERMISSIONS_TAGS]
        },
        "ai_files": {
            "prefix": settings.API_AI_FILES_PREFIX,
            "tags": [settings.API_AI_FILES_TAGS]
        },
        "ai_operation_logs": {
            "prefix": "",
            "tags": [settings.API_AI_OPERATION_LOGS_TAGS]
        },
        "cache_preheating": {
            "prefix": settings.API_CACHE_PREHEATING_PREFIX,
            "tags": [settings.API_CACHE_PREHEATING_TAGS]
        },
        "baidu_wenxin": {
            "prefix": settings.API_BAIDU_WENXIN_PREFIX,
            "tags": [settings.API_BAIDU_WENXIN_TAGS]
        },
        "aliyun_tongyi": {
            "prefix": settings.API_ALIYUN_TONGYI_PREFIX,
            "tags": [settings.API_ALIYUN_TONGYI_TAGS]
        },
        "chinese_routing": {
            "prefix": settings.API_CHINESE_ROUTING_PREFIX,
            "tags": [settings.API_CHINESE_ROUTING_TAGS]
        },
        "multilingual": {
            "prefix": settings.API_MULTILINGUAL_PREFIX,
            "tags": [settings.API_MULTILINGUAL_TAGS]
        },
        "projects": {
            "prefix": settings.API_PROJECTS_PREFIX,
            "tags": [settings.API_PROJECTS_TAGS]
        },
        "teams": {
            "prefix": "",
            "tags": ["团队管理"]
        },
        "tasks": {
            "prefix": "",
            "tags": ["任务管理"]
        }
    }
    
    return route_configs.get(route_name, {"prefix": "", "tags": ["未分类"]})


settings = get_settings()
