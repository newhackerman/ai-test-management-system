"""
配置验证规则管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from ..utils.advanced_validator import AdvancedConfigValidator, ValidationRuleBuilder, CommonValidationRules
from ..schemas.base import ApiResponse
from ..core.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/validation-rules", tags=["配置验证规则"])


class ValidationRuleRequest(BaseModel):
    """验证规则请求"""
    config_key: str
    rule_type: str  # basic, regex, range, length, enum, dependency, business
    rule_config: Dict[str, Any]
    description: Optional[str] = None


class ValidationRuleResponse(BaseModel):
    """验证规则响应"""
    id: str
    config_key: str
    rule_type: str
    rule_config: Dict[str, Any]
    description: Optional[str]
    is_active: bool = True


class ValidationTestRequest(BaseModel):
    """验证测试请求"""
    config_key: str
    config_value: Any
    config_type: str
    environment: str
    validation_rules: Optional[Dict[str, Any]] = None


@router.get("/common-rules", response_model=ApiResponse[Dict[str, Any]])
async def get_common_validation_rules():
    """获取常用验证规则模板"""
    try:
        common_rules = {
            "database_host": CommonValidationRules.database_host(),
            "database_port": CommonValidationRules.database_port(),
            "api_key": CommonValidationRules.api_key(),
            "email_settings": CommonValidationRules.email_settings(),
            "url_endpoint": CommonValidationRules.url_endpoint()
        }
        
        return ApiResponse(
            success=True,
            data=common_rules,
            message="获取常用验证规则成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取常用验证规则失败: {str(e)}")


@router.post("/test", response_model=ApiResponse[Dict[str, Any]])
async def test_validation_rule(
    request: ValidationTestRequest,
    current_user: User = Depends(get_current_user)
):
    """测试验证规则"""
    try:
        # 创建高级验证器实例
        validator = AdvancedConfigValidator()
        
        # 执行验证
        is_valid, error_message = await validator.validate_with_dependencies(
            request.config_key,
            request.config_value,
            request.config_type,
            request.environment,
            request.validation_rules
        )
        
        result = {
            "is_valid": is_valid,
            "error_message": error_message,
            "config_key": request.config_key,
            "config_value": request.config_value,
            "config_type": request.config_type,
            "environment": request.environment
        }
        
        return ApiResponse(
            success=True,
            data=result,
            message="验证规则测试完成"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证规则测试失败: {str(e)}")


@router.post("/build-rule", response_model=ApiResponse[Dict[str, Any]])
async def build_validation_rule(
    rule_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """构建验证规则"""
    try:
        builder = ValidationRuleBuilder()
        
        # 根据配置构建规则
        if "regex" in rule_config:
            builder.regex(rule_config["regex"])
        
        if "range" in rule_config:
            range_config = rule_config["range"]
            builder.range(
                range_config.get("min"),
                range_config.get("max")
            )
        
        if "length" in rule_config:
            length_config = rule_config["length"]
            builder.length(
                length_config.get("min"),
                length_config.get("max")
            )
        
        if "enum" in rule_config:
            builder.enum(rule_config["enum"])
        
        if "dependencies" in rule_config:
            for dep in rule_config["dependencies"]:
                if dep["type"] == "required_if":
                    builder.required_if(dep["config_key"], dep["condition"])
                elif dep["type"] == "exclusive_with":
                    builder.exclusive_with(dep["config_key"])
        
        if "business_rules" in rule_config:
            for rule in rule_config["business_rules"]:
                if rule["type"] == "database_connection":
                    builder.database_connection_test(rule.get("timeout", 5))
                elif rule["type"] == "url_accessibility":
                    builder.url_accessibility_test(rule.get("timeout", 5))
        
        # 构建最终规则
        validation_rule = builder.build()
        
        return ApiResponse(
            success=True,
            data=validation_rule,
            message="验证规则构建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证规则构建失败: {str(e)}")


@router.get("/rule-templates", response_model=ApiResponse[List[Dict[str, Any]]])
async def get_validation_rule_templates():
    """获取验证规则模板"""
    try:
        templates = [
            {
                "name": "基础字符串验证",
                "type": "string",
                "template": {
                    "regex": "^[a-zA-Z0-9_-]+$",
                    "length": {"min": 1, "max": 100}
                },
                "description": "验证字符串只包含字母、数字、下划线和连字符"
            },
            {
                "name": "数据库端口验证",
                "type": "integer",
                "template": {
                    "range": {"min": 1, "max": 65535}
                },
                "description": "验证数据库端口号范围"
            },
            {
                "name": "邮箱地址验证",
                "type": "email",
                "template": {
                    "regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                },
                "description": "验证邮箱地址格式"
            },
            {
                "name": "URL可访问性验证",
                "type": "url",
                "template": {
                    "regex": "^https?://[^\\s/$.?#].[^\\s]*$",
                    "business_rules": [
                        {
                            "type": "url_accessibility",
                            "timeout": 10
                        }
                    ]
                },
                "description": "验证URL格式并测试可访问性"
            },
            {
                "name": "依赖配置验证",
                "type": "dependency",
                "template": {
                    "dependencies": [
                        {
                            "type": "required_if",
                            "config_key": "database.enabled",
                            "condition": {"operator": "eq", "value": "true"}
                        }
                    ]
                },
                "description": "当数据库启用时此配置为必填"
            },
            {
                "name": "互斥配置验证",
                "type": "dependency",
                "template": {
                    "dependencies": [
                        {
                            "type": "exclusive_with",
                            "config_key": "cache.redis.enabled"
                        }
                    ]
                },
                "description": "与Redis缓存配置互斥"
            },
            {
                "name": "数据库连接验证",
                "type": "business",
                "template": {
                    "business_rules": [
                        {
                            "type": "database_connection",
                            "timeout": 5
                        }
                    ]
                },
                "description": "测试数据库连接字符串有效性"
            }
        ]
        
        return ApiResponse(
            success=True,
            data=templates,
            message="获取验证规则模板成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取验证规则模板失败: {str(e)}")


@router.post("/validate-complex", response_model=ApiResponse[Dict[str, Any]])
async def validate_complex_rule(
    config_key: str,
    config_value: Any,
    config_type: str,
    environment: str,
    validation_rules: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """复杂验证规则测试"""
    try:
        # 模拟配置服务
        from ..services.config import ConfigService
        config_service = ConfigService()
        
        # 创建高级验证器
        validator = AdvancedConfigValidator(config_service)
        
        # 执行验证
        is_valid, error_message = await validator.validate_with_dependencies(
            config_key,
            config_value,
            config_type,
            environment,
            validation_rules
        )
        
        # 分析验证结果
        validation_details = {
            "is_valid": is_valid,
            "error_message": error_message,
            "validation_steps": []
        }
        
        # 如果有依赖验证规则，分析每个步骤
        if "dependencies" in validation_rules:
            for dep in validation_rules["dependencies"]:
                validation_details["validation_steps"].append({
                    "step": f"依赖验证: {dep['type']}",
                    "target_config": dep.get("config_key"),
                    "condition": dep.get("condition"),
                    "status": "passed" if is_valid else "failed"
                })
        
        if "business_rules" in validation_rules:
            for rule in validation_rules["business_rules"]:
                validation_details["validation_steps"].append({
                    "step": f"业务验证: {rule['type']}",
                    "config": rule,
                    "status": "passed" if is_valid else "failed"
                })
        
        return ApiResponse(
            success=True,
            data=validation_details,
            message="复杂验证规则测试完成"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"复杂验证规则测试失败: {str(e)}")