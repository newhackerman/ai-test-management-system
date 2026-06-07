#!/usr/bin/env python3
"""
配置管理CLI工具
用于管理和验证系统配置
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..utils.config_manager import get_config_manager
from ..core.config import get_settings


def validate_config():
    """验证配置"""
    print("🔍 验证系统配置...")
    
    config_manager = get_config_manager()
    settings = get_settings()
    
    # 验证必需的配置项
    required_configs = [
        ("DATABASE_URL", "数据库连接URL"),
        ("JWT_SECRET_KEY", "JWT密钥"),
        ("HOST", "服务器主机"),
        ("PORT", "服务器端口")
    ]
    
    missing_configs = []
    for config_key, description in required_configs:
        value = config_manager.get_config(config_key)
        if not value:
            missing_configs.append(f"  ❌ {config_key}: {description}")
        else:
            print(f"  ✅ {config_key}: {description}")
    
    if missing_configs:
        print("\n❌ 缺少必需的配置项:")
        for config in missing_configs:
            print(config)
        return False
    
    print("\n✅ 所有必需的配置项都已设置")
    return True


def show_config():
    """显示当前配置"""
    print("📋 当前系统配置:")
    
    config_manager = get_config_manager()
    
    configs = {
        "服务器配置": config_manager.get_server_config(),
        "数据库配置": {
            k: v for k, v in config_manager.get_database_config().items()
            if k not in ["password"]  # 隐藏敏感信息
        },
        "Redis配置": {
            k: v for k, v in config_manager.get_redis_config().items()
            if k not in ["password"]  # 隐藏敏感信息
        },
        "JWT配置": {
            k: v for k, v in config_manager.get_jwt_config().items()
            if k not in ["secret_key"]  # 隐藏敏感信息
        },
        "CORS配置": config_manager.get_cors_config(),
        "API配置": config_manager.get_api_config(),
        "安全配置": {
            k: v for k, v in config_manager.get_security_config().items()
            if k not in ["secret_key"]  # 隐藏敏感信息
        },
        "文件配置": config_manager.get_file_config(),
        "邮件配置": {
            k: v for k, v in config_manager.get_email_config().items()
            if k not in ["smtp_password"]  # 隐藏敏感信息
        }
    }
    
    for section, config in configs.items():
        print(f"\n📁 {section}:")
        for key, value in config.items():
            print(f"  {key}: {value}")


def export_config(output_file: str):
    """导出配置到文件"""
    print(f"📤 导出配置到文件: {output_file}")
    
    config_manager = get_config_manager()
    
    # 收集所有配置（隐藏敏感信息）
    all_configs = {
        "server": config_manager.get_server_config(),
        "database": {
            k: v for k, v in config_manager.get_database_config().items()
            if k not in ["password"]
        },
        "redis": {
            k: v for k, v in config_manager.get_redis_config().items()
            if k not in ["password"]
        },
        "jwt": {
            k: v for k, v in config_manager.get_jwt_config().items()
            if k not in ["secret_key"]
        },
        "cors": config_manager.get_cors_config(),
        "api": config_manager.get_api_config(),
        "security": {
            k: v for k, v in config_manager.get_security_config().items()
            if k not in ["secret_key"]
        },
        "file": config_manager.get_file_config(),
        "email": {
            k: v for k, v in config_manager.get_email_config().items()
            if k not in ["smtp_password"]
        },
        "ai": {
            "openai": {
                k: v for k, v in config_manager.get_ai_config()["openai"].items()
                if k not in ["api_key"]
            },
            "anthropic": {
                k: v for k, v in config_manager.get_ai_config()["anthropic"].items()
                if k not in ["api_key"]
            },
            "gemini": {
                k: v for k, v in config_manager.get_ai_config()["gemini"].items()
                if k not in ["api_key"]
            }
        }
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_configs, f, indent=2, ensure_ascii=False)
        print(f"✅ 配置已导出到: {output_file}")
    except Exception as e:
        print(f"❌ 导出配置失败: {e}")


def check_env_file():
    """检查环境文件"""
    print("🔍 检查环境配置文件...")
    
    env_files = [".env", "backend/.env", ".env.example", "backend/.env.example"]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"  ✅ 找到环境文件: {env_file}")
            
            # 读取并分析环境文件
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                config_count = 0
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        config_count += 1
                
                print(f"    📊 包含 {config_count} 个配置项")
                
            except Exception as e:
                print(f"    ❌ 读取文件失败: {e}")
        else:
            print(f"  ❌ 未找到环境文件: {env_file}")


def generate_env_template():
    """生成环境变量模板"""
    print("📝 生成环境变量模板...")
    
    template = """# =============================================================================
# AI测试管理系统 - 环境配置文件
# =============================================================================
# 请根据实际环境修改以下配置项

# =============================================================================
# 服务器配置
# =============================================================================
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# =============================================================================
# 数据库配置
# =============================================================================
DATABASE_URL=mysql+asyncmy://username:password@localhost:3306/database_name
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=aitestdb
DATABASE_USER=aitest
DATABASE_PASSWORD=your_password_here
DATABASE_DRIVER=mysql+asyncmy
DATABASE_CHARSET=utf8mb4

# =============================================================================
# Redis配置
# =============================================================================
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# =============================================================================
# JWT配置
# =============================================================================
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_HOURS=1
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# =============================================================================
# CORS配置
# =============================================================================
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# =============================================================================
# API配置
# =============================================================================
API_V1_STR=/api/v1
PROJECT_NAME=AI测试管理系统

# =============================================================================
# 安全配置
# =============================================================================
SECRET_KEY=your-super-secret-key-change-in-production
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
SESSION_TIMEOUT_MINUTES=60
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SYMBOLS=true

# =============================================================================
# 文件上传配置
# =============================================================================
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600

# =============================================================================
# 邮件配置
# =============================================================================
EMAIL_ENABLED=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_TLS=true

# =============================================================================
# AI服务配置
# =============================================================================
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_MODEL=gemini-pro

# =============================================================================
# 百度文心一言配置
# =============================================================================
BAIDU_API_KEY=your_baidu_api_key_here
BAIDU_SECRET_KEY=your_baidu_secret_key_here
BAIDU_BASE_URL=https://aip.baidubce.com

# =============================================================================
# 阿里通义千问配置
# =============================================================================
ALIYUN_API_KEY=your_aliyun_api_key_here
ALIYUN_API_ENDPOINT=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
"""
    
    output_file = ".env.template"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"✅ 环境变量模板已生成: {output_file}")
        print("💡 请复制此文件为 .env 并修改相应的配置值")
    except Exception as e:
        print(f"❌ 生成模板失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置管理CLI工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 验证配置命令
    subparsers.add_parser("validate", help="验证系统配置")
    
    # 显示配置命令
    subparsers.add_parser("show", help="显示当前配置")
    
    # 导出配置命令
    export_parser = subparsers.add_parser("export", help="导出配置到文件")
    export_parser.add_argument("--output", "-o", default="config_export.json", help="输出文件路径")
    
    # 检查环境文件命令
    subparsers.add_parser("check-env", help="检查环境配置文件")
    
    # 生成环境变量模板命令
    subparsers.add_parser("generate-template", help="生成环境变量模板")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🚀 配置管理工具 - {args.command}")
    print("=" * 50)
    
    try:
        if args.command == "validate":
            success = validate_config()
            sys.exit(0 if success else 1)
        elif args.command == "show":
            show_config()
        elif args.command == "export":
            export_config(args.output)
        elif args.command == "check-env":
            check_env_file()
        elif args.command == "generate-template":
            generate_env_template()
        else:
            print(f"❌ 未知命令: {args.command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 执行命令失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()