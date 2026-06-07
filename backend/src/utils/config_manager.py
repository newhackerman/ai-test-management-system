"""
配置管理工具
提供动态配置管理功能，避免硬编码
"""
import os
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
from ..core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self._config_cache = {}
        self._load_config_files()
    
    def _load_config_files(self):
        """加载配置文件"""
        config_dir = Path("config")
        if config_dir.exists():
            for config_file in config_dir.glob("*.json"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        self._config_cache[config_file.stem] = config_data
                        logger.info(f"已加载配置文件: {config_file}")
                except Exception as e:
                    logger.error(f"加载配置文件失败 {config_file}: {e}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 首先尝试从环境变量获取
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return self._convert_env_value(env_value)
        
        # 然后从settings获取
        if hasattr(self.settings, key.upper()):
            return getattr(self.settings, key.upper())
        
        # 最后从配置文件缓存获取
        for config_name, config_data in self._config_cache.items():
            if key in config_data:
                return config_data[key]
        
        return default
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool, list]:
        """转换环境变量值为适当的类型"""
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # 列表（逗号分隔）
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        return value
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return {
            "host": self.get_config("HOST", "0.0.0.0"),
            "port": self.get_config("PORT", 8000),
            "debug": self.get_config("DEBUG", False),
            "log_level": self.get_config("LOG_LEVEL", "INFO")
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return {
            "url": self.get_config("DATABASE_URL"),
            "host": self.get_config("DATABASE_HOST", "localhost"),
            "port": self.get_config("DATABASE_PORT", 3306),
            "name": self.get_config("DATABASE_NAME", "aitestdb"),
            "user": self.get_config("DATABASE_USER", "aitest"),
            "password": self.get_config("DATABASE_PASSWORD"),
            "driver": self.get_config("DATABASE_DRIVER", "mysql+asyncmy"),
            "charset": self.get_config("DATABASE_CHARSET", "utf8mb4"),
            "pool_size": self.get_config("DATABASE_POOL_SIZE", 10),
            "max_overflow": self.get_config("DATABASE_MAX_OVERFLOW", 20),
            "pool_pre_ping": self.get_config("DATABASE_POOL_PRE_PING", True),
            "pool_recycle": self.get_config("DATABASE_POOL_RECYCLE", 3600),
            "echo": self.get_config("DATABASE_ECHO", False)
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        return {
            "url": self.get_config("REDIS_URL"),
            "host": self.get_config("REDIS_HOST", "localhost"),
            "port": self.get_config("REDIS_PORT", 6379),
            "db": self.get_config("REDIS_DB", 0),
            "password": self.get_config("REDIS_PASSWORD"),
            "timeout": self.get_config("REDIS_TIMEOUT", 30),
            "max_connections": self.get_config("REDIS_MAX_CONNECTIONS", 100)
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """获取JWT配置"""
        return {
            "secret_key": self.get_config("JWT_SECRET_KEY"),
            "algorithm": self.get_config("JWT_ALGORITHM", "HS256"),
            "access_token_expire_minutes": self.get_config("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30),
            "access_token_expire_hours": self.get_config("JWT_ACCESS_TOKEN_EXPIRE_HOURS", 1),
            "refresh_token_expire_days": self.get_config("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """获取CORS配置"""
        origins = self.get_config("CORS_ORIGINS", "http://localhost:3000")
        if isinstance(origins, str):
            origins = [origin.strip() for origin in origins.split(',')]
        
        return {
            "origins": origins,
            "allow_credentials": self.get_config("CORS_ALLOW_CREDENTIALS", True),
            "allow_methods": self.get_config("CORS_ALLOW_METHODS", ["*"]),
            "allow_headers": self.get_config("CORS_ALLOW_HEADERS", ["*"])
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return {
            "v1_str": self.get_config("API_V1_STR", "/api/v1"),
            "project_name": self.get_config("PROJECT_NAME", "AI测试管理系统"),
            "timeout": self.get_config("API_TIMEOUT", 30),
            "rate_limit_per_minute": self.get_config("RATE_LIMIT_PER_MINUTE", 60)
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """获取AI服务配置"""
        return {
            "openai": {
                "api_key": self.get_config("OPENAI_API_KEY"),
                "base_url": self.get_config("OPENAI_BASE_URL"),
                "model": self.get_config("OPENAI_MODEL", "gpt-3.5-turbo"),
                "timeout": self.get_config("OPENAI_TIMEOUT", 30),
                "max_retries": self.get_config("OPENAI_MAX_RETRIES", 3)
            },
            "anthropic": {
                "api_key": self.get_config("ANTHROPIC_API_KEY"),
                "base_url": self.get_config("ANTHROPIC_BASE_URL"),
                "model": self.get_config("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                "timeout": self.get_config("ANTHROPIC_TIMEOUT", 30),
                "max_retries": self.get_config("ANTHROPIC_MAX_RETRIES", 3)
            },
            "gemini": {
                "api_key": self.get_config("GEMINI_API_KEY"),
                "base_url": self.get_config("GEMINI_BASE_URL"),
                "model": self.get_config("GEMINI_MODEL", "gemini-pro"),
                "timeout": self.get_config("GEMINI_TIMEOUT", 30),
                "max_retries": self.get_config("GEMINI_MAX_RETRIES", 3)
            }
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return {
            "secret_key": self.get_config("SECRET_KEY"),
            "allowed_hosts": self.get_config("ALLOWED_HOSTS", ["localhost", "127.0.0.1"]),
            "max_login_attempts": self.get_config("MAX_LOGIN_ATTEMPTS", 5),
            "account_lockout_duration_minutes": self.get_config("ACCOUNT_LOCKOUT_DURATION_MINUTES", 30),
            "session_timeout_minutes": self.get_config("SESSION_TIMEOUT_MINUTES", 60),
            "password_min_length": self.get_config("PASSWORD_MIN_LENGTH", 8),
            "password_require_uppercase": self.get_config("PASSWORD_REQUIRE_UPPERCASE", True),
            "password_require_lowercase": self.get_config("PASSWORD_REQUIRE_LOWERCASE", True),
            "password_require_numbers": self.get_config("PASSWORD_REQUIRE_NUMBERS", True),
            "password_require_symbols": self.get_config("PASSWORD_REQUIRE_SYMBOLS", True),
            "password_max_age_days": self.get_config("PASSWORD_MAX_AGE_DAYS", 90)
        }
    
    def get_file_config(self) -> Dict[str, Any]:
        """获取文件配置"""
        return {
            "upload_dir": self.get_config("UPLOAD_DIR", "uploads"),
            "max_file_size": self.get_config("MAX_FILE_SIZE", 104857600),  # 100MB
            "allowed_extensions": self.get_config("ALLOWED_EXTENSIONS", [
                ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", ".xls", ".xlsx"
            ])
        }
    
    def get_email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        return {
            "enabled": self.get_config("EMAIL_ENABLED", False),
            "smtp_host": self.get_config("SMTP_HOST"),
            "smtp_port": self.get_config("SMTP_PORT", 587),
            "smtp_username": self.get_config("SMTP_USERNAME"),
            "smtp_password": self.get_config("SMTP_PASSWORD"),
            "smtp_tls": self.get_config("SMTP_TLS", True),
            "from_email": self.get_config("EMAILS_FROM_EMAIL"),
            "from_name": self.get_config("EMAILS_FROM_NAME", "AI测试管理系统")
        }
    
    def reload_config(self):
        """重新加载配置"""
        self._config_cache.clear()
        self.settings = get_settings()
        self._load_config_files()
        logger.info("配置已重新加载")


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager