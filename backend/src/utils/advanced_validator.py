"""
高级配置验证器
支持复杂验证规则、依赖验证、格式检查等高级功能
"""
import re
import json
import ipaddress
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from datetime import datetime, time, date
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class AdvancedConfigValidator:
    """高级配置验证器"""
    
    def __init__(self, config_service=None):
        """
        初始化高级验证器
        
        Args:
            config_service: 配置服务实例，用于依赖验证
        """
        self.config_service = config_service
        
    async def validate_with_dependencies(
        self, 
        config_key: str,
        config_value: Any,
        config_type: str,
        environment: str,
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        带依赖关系的配置验证
        
        Args:
            config_key: 配置键名
            config_value: 配置值
            config_type: 配置类型
            environment: 环境
            validation_rules: 验证规则
            
        Returns:
            (是否有效, 错误消息)
        """
        if not validation_rules:
            return True, None
            
        # 1. 基础类型验证
        basic_valid, basic_error = self._basic_type_validation(config_value, config_type)
        if not basic_valid:
            return False, basic_error
        
        # 2. 复杂规则验证
        complex_valid, complex_error = await self._complex_rule_validation(
            config_key, config_value, validation_rules
        )
        if not complex_valid:
            return False, complex_error
        
        # 3. 依赖关系验证
        dependency_valid, dependency_error = await self._dependency_validation(
            config_key, config_value, environment, validation_rules
        )
        if not dependency_valid:
            return False, dependency_error
        
        # 4. 业务逻辑验证
        business_valid, business_error = await self._business_logic_validation(
            config_key, config_value, environment, validation_rules
        )
        if not business_valid:
            return False, business_error
        
        return True, None
    
    def _basic_type_validation(self, value: Any, config_type: str) -> Tuple[bool, Optional[str]]:
        """基础类型验证"""
        try:
            if config_type == 'INTEGER':
                int(value)
            elif config_type == 'FLOAT':
                float(value)
            elif config_type == 'BOOLEAN':
                if str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    return False, "布尔值格式不正确"
            elif config_type == 'JSON':
                json.loads(str(value))
            elif config_type == 'EMAIL':
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
                    return False, "邮箱格式不正确"
            elif config_type == 'URL':
                parsed = urlparse(str(value))
                if not parsed.scheme or not parsed.netloc:
                    return False, "URL格式不正确"
            return True, None
        except Exception as e:
            return False, f"类型验证失败: {str(e)}"
    
    async def _complex_rule_validation(
        self, 
        config_key: str, 
        config_value: Any, 
        validation_rules: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """复杂规则验证"""
        
        # 正则表达式验证
        regex_rule = validation_rules.get('regex')
        if regex_rule:
            if not re.match(regex_rule, str(config_value)):
                return False, f"值不符合正则表达式: {regex_rule}"
        
        # 数值范围验证
        range_rule = validation_rules.get('range')
        if range_rule and isinstance(config_value, (int, float)):
            min_val = range_rule.get('min')
            max_val = range_rule.get('max')
            if min_val is not None and config_value < min_val:
                return False, f"值不能小于 {min_val}"
            if max_val is not None and config_value > max_val:
                return False, f"值不能大于 {max_val}"
        
        # 长度验证
        length_rule = validation_rules.get('length')
        if length_rule:
            value_len = len(str(config_value))
            min_len = length_rule.get('min', 0)
            max_len = length_rule.get('max', float('inf'))
            if value_len < min_len:
                return False, f"长度不能少于 {min_len} 个字符"
            if value_len > max_len:
                return False, f"长度不能超过 {max_len} 个字符"
        
        # 枚举值验证
        enum_rule = validation_rules.get('enum')
        if enum_rule:
            if config_value not in enum_rule:
                return False, f"值必须是以下之一: {enum_rule}"
        
        # 自定义函数验证
        custom_validator = validation_rules.get('custom_validator')
        if custom_validator:
            try:
                if callable(custom_validator):
                    result = custom_validator(config_value)
                    if not result:
                        return False, "自定义验证规则失败"
            except Exception as e:
                return False, f"自定义验证执行失败: {str(e)}"
        
        return True, None
    
    async def _dependency_validation(
        self,
        config_key: str,
        config_value: Any,
        environment: str,
        validation_rules: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """依赖关系验证"""
        
        dependencies = validation_rules.get('dependencies', [])
        if not dependencies or not self.config_service:
            return True, None
        
        for dependency in dependencies:
            dep_type = dependency.get('type')
            dep_config = dependency.get('config_key')
            dep_condition = dependency.get('condition')
            
            if not dep_config:
                continue
            
            try:
                # 获取依赖配置的值
                dep_value = await self._get_dependency_value(dep_config, environment)
                
                if dep_type == 'required_if':
                    # 条件必填验证
                    if self._check_condition(dep_value, dep_condition):
                        if not config_value or str(config_value).strip() == '':
                            return False, f"当 {dep_config} 满足条件时，此配置项必填"
                
                elif dep_type == 'exclusive_with':
                    # 互斥验证
                    if dep_value and config_value:
                        return False, f"此配置项与 {dep_config} 不能同时设置"
                
                elif dep_type == 'same_as':
                    # 值相同验证
                    if config_value != dep_value:
                        return False, f"此配置项的值必须与 {dep_config} 相同"
                
                elif dep_type == 'different_from':
                    # 值不同验证
                    if config_value == dep_value:
                        return False, f"此配置项的值不能与 {dep_config} 相同"
                
                elif dep_type == 'format_match':
                    # 格式匹配验证
                    format_template = dependency.get('format_template', '')
                    if not self._check_format_match(config_value, dep_value, format_template):
                        return False, f"此配置项格式必须与 {dep_config} 匹配模板 {format_template}"
                
            except Exception as e:
                logger.error(f"依赖验证失败: {str(e)}")
                return False, f"依赖验证执行失败: {str(e)}"
        
        return True, None
    
    async def _business_logic_validation(
        self,
        config_key: str,
        config_value: Any,
        environment: str,
        validation_rules: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """业务逻辑验证"""
        
        business_rules = validation_rules.get('business_rules', [])
        if not business_rules:
            return True, None
        
        for rule in business_rules:
            rule_type = rule.get('type')
            
            if rule_type == 'database_connection':
                # 数据库连接验证
                valid, error = await self._validate_database_connection(config_value, rule)
                if not valid:
                    return False, error
            
            elif rule_type == 'url_accessibility':
                # URL可访问性验证
                valid, error = await self._validate_url_accessibility(config_value, rule)
                if not valid:
                    return False, error
            
            elif rule_type == 'file_existence':
                # 文件存在性验证
                valid, error = self._validate_file_existence(config_value, rule)
                if not valid:
                    return False, error
            
            elif rule_type == 'port_availability':
                # 端口可用性验证
                valid, error = await self._validate_port_availability(config_value, rule)
                if not valid:
                    return False, error
        
        return True, None
    
    async def _get_dependency_value(self, dep_config: str, environment: str) -> Any:
        """获取依赖配置的值"""
        if not self.config_service:
            return None
        
        try:
            config = await self.config_service.get_config(dep_config, environment)
            return config.config_value if config else None
        except Exception:
            return None
    
    def _check_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """检查条件是否满足"""
        if not condition:
            return True
        
        operator = condition.get('operator', 'eq')
        target_value = condition.get('value')
        
        if operator == 'eq':
            return value == target_value
        elif operator == 'ne':
            return value != target_value
        elif operator == 'gt':
            return value > target_value
        elif operator == 'gte':
            return value >= target_value
        elif operator == 'lt':
            return value < target_value
        elif operator == 'lte':
            return value <= target_value
        elif operator == 'in':
            return value in target_value
        elif operator == 'not_in':
            return value not in target_value
        elif operator == 'contains':
            return target_value in str(value)
        elif operator == 'regex':
            return bool(re.match(target_value, str(value)))
        
        return False
    
    def _check_format_match(self, value: Any, dep_value: Any, format_template: str) -> bool:
        """检查格式是否匹配"""
        try:
            # 简单的格式模板匹配，支持 {dep_value} 占位符
            expected_format = format_template.replace('{dep_value}', str(dep_value))
            return str(value) == expected_format
        except Exception:
            return False
    
    async def _validate_database_connection(self, connection_string: str, rule: Dict) -> Tuple[bool, Optional[str]]:
        """验证数据库连接"""
        # 这里可以实现实际的数据库连接测试
        # 为了演示，简单验证连接字符串格式
        try:
            # 基本格式验证
            if not connection_string or '://' not in connection_string:
                return False, "数据库连接字符串格式不正确"
            
            # 如果需要实际连接测试，可以在这里实现
            # 例如使用 sqlalchemy 测试连接
            return True, None
        except Exception as e:
            return False, f"数据库连接验证失败: {str(e)}"
    
    async def _validate_url_accessibility(self, url: str, rule: Dict) -> Tuple[bool, Optional[str]]:
        """验证URL可访问性"""
        try:
            import aiohttp
            timeout = rule.get('timeout', 5)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status >= 400:
                        return False, f"URL返回错误状态码: {response.status}"
            
            return True, None
        except Exception as e:
            return False, f"URL可访问性验证失败: {str(e)}"
    
    def _validate_file_existence(self, file_path: str, rule: Dict) -> Tuple[bool, Optional[str]]:
        """验证文件存在性"""
        try:
            import os
            
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"
            
            if rule.get('check_readable', False) and not os.access(file_path, os.R_OK):
                return False, f"文件不可读: {file_path}"
            
            if rule.get('check_writable', False) and not os.access(file_path, os.W_OK):
                return False, f"文件不可写: {file_path}"
            
            return True, None
        except Exception as e:
            return False, f"文件存在性验证失败: {str(e)}"
    
    async def _validate_port_availability(self, port: Any, rule: Dict) -> Tuple[bool, Optional[str]]:
        """验证端口可用性"""
        try:
            import socket
            import asyncio
            
            port_num = int(port)
            host = rule.get('host', 'localhost')
            
            # 检查端口是否被占用
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex((host, port_num))
                if result == 0:
                    return False, f"端口 {port_num} 已被占用"
            finally:
                sock.close()
            
            return True, None
        except Exception as e:
            return False, f"端口可用性验证失败: {str(e)}"


# 验证规则构建器
class ValidationRuleBuilder:
    """验证规则构建器"""
    
    def __init__(self):
        self.rules = {}
    
    def regex(self, pattern: str):
        """添加正则表达式验证"""
        self.rules['regex'] = pattern
        return self
    
    def range(self, min_val: Optional[float] = None, max_val: Optional[float] = None):
        """添加数值范围验证"""
        self.rules['range'] = {}
        if min_val is not None:
            self.rules['range']['min'] = min_val
        if max_val is not None:
            self.rules['range']['max'] = max_val
        return self
    
    def length(self, min_len: Optional[int] = None, max_len: Optional[int] = None):
        """添加长度验证"""
        self.rules['length'] = {}
        if min_len is not None:
            self.rules['length']['min'] = min_len
        if max_len is not None:
            self.rules['length']['max'] = max_len
        return self
    
    def enum(self, values: List[Any]):
        """添加枚举值验证"""
        self.rules['enum'] = values
        return self
    
    def required_if(self, dep_config: str, condition: Dict[str, Any]):
        """添加条件必填验证"""
        if 'dependencies' not in self.rules:
            self.rules['dependencies'] = []
        self.rules['dependencies'].append({
            'type': 'required_if',
            'config_key': dep_config,
            'condition': condition
        })
        return self
    
    def exclusive_with(self, dep_config: str):
        """添加互斥验证"""
        if 'dependencies' not in self.rules:
            self.rules['dependencies'] = []
        self.rules['dependencies'].append({
            'type': 'exclusive_with',
            'config_key': dep_config
        })
        return self
    
    def database_connection_test(self, timeout: int = 5):
        """添加数据库连接测试"""
        if 'business_rules' not in self.rules:
            self.rules['business_rules'] = []
        self.rules['business_rules'].append({
            'type': 'database_connection',
            'timeout': timeout
        })
        return self
    
    def url_accessibility_test(self, timeout: int = 5):
        """添加URL可访问性测试"""
        if 'business_rules' not in self.rules:
            self.rules['business_rules'] = []
        self.rules['business_rules'].append({
            'type': 'url_accessibility',
            'timeout': timeout
        })
        return self
    
    def build(self) -> Dict[str, Any]:
        """构建验证规则"""
        return self.rules


# 常用验证规则预设
class CommonValidationRules:
    """常用验证规则预设"""
    
    @staticmethod
    def database_host():
        """数据库主机验证规则"""
        return ValidationRuleBuilder().regex(r'^[a-zA-Z0-9.-]+$').build()
    
    @staticmethod
    def database_port():
        """数据库端口验证规则"""
        return ValidationRuleBuilder().range(1, 65535).build()
    
    @staticmethod
    def api_key():
        """API密钥验证规则"""
        return ValidationRuleBuilder().length(16, 64).regex(r'^[a-zA-Z0-9]+$').build()
    
    @staticmethod
    def email_settings():
        """邮箱设置验证规则"""
        return ValidationRuleBuilder().regex(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$').build()
    
    @staticmethod
    def url_endpoint():
        """URL端点验证规则"""
        return ValidationRuleBuilder().regex(r'^https?://[^\s/$.?#].[^\s]*$').url_accessibility_test(10).build()


print("✅ 高级配置验证器已创建完成")