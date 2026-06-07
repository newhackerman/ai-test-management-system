"""
配置验证器
"""
import re
import json
import ipaddress
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """配置类型枚举"""
    STRING = "STRING"       # 字符串
    TEXT = "TEXT"           # 长文本
    INTEGER = "INTEGER"     # 整数
    FLOAT = "FLOAT"         # 浮点数
    BOOLEAN = "BOOLEAN"     # 布尔值
    JSON = "JSON"          # JSON对象
    ARRAY = "ARRAY"         # 数组
    EMAIL = "EMAIL"         # 邮箱地址
    URL = "URL"            # 网址
    ENUM = "ENUM"           # 枚举值
    PASSWORD = "PASSWORD"   # 密码
    FILE = "FILE"           # 文件路径
    COLOR = "COLOR"         # 颜色值
    DATE = "DATE"           # 日期
    TIME = "TIME"           # 时间


class ValidationRule:
    """验证规则类"""
    
    def __init__(self, rule_dict: Dict[str, Any]):
        """
        初始化验证规则
        
        Args:
            rule_dict: 规则字典
        """
        self.rules = rule_dict or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取规则值"""
        return self.rules.get(key, default)
    
    def has(self, key: str) -> bool:
        """检查是否有指定规则"""
        return key in self.rules


class ConfigValidator:
    """配置验证器"""
    
    # 预定义的验证规则
    DEFAULT_RULES = {
        ConfigType.STRING: {
            'min_length': 0,
            'max_length': 65535,
            'pattern': None,
            'allowed_chars': None,
            'forbidden_chars': None
        },
        ConfigType.TEXT: {
            'min_length': 0,
            'max_length': 1048576,  # 1MB
            'pattern': None,
            'allowed_chars': None,
            'forbidden_chars': None
        },
        ConfigType.INTEGER: {
            'min_value': -(2**63),
            'max_value': 2**63 - 1
        },
        ConfigType.FLOAT: {
            'min_value': float('-inf'),
            'max_value': float('inf'),
            'precision': None  # 小数点精度
        },
        ConfigType.BOOLEAN: {
            'true_values': ['true', '1', 'yes', 'on', 'enable', 'enabled'],
            'false_values': ['false', '0', 'no', 'off', 'disable', 'disabled']
        },
        ConfigType.JSON: {
            'max_depth': 10,
            'max_length': 1048576,  # 1MB
            'required_keys': [],
            'forbidden_keys': []
        },
        ConfigType.ARRAY: {
            'min_items': 0,
            'max_items': 1000,
            'item_type': None,  # 数组元素类型
            'unique_items': False
        },
        ConfigType.EMAIL: {
            'allow_multiple': False,  # 是否允许多个邮箱（逗号分隔）
            'require_mx': False,  # 是否验证MX记录
            'allowed_domains': [],  # 允许的域名列表
            'forbidden_domains': []  # 禁止的域名列表
        },
        ConfigType.URL: {
            'allowed_schemes': ['http', 'https', 'ftp', 'ftps'],
            'allow_localhost': True,
            'allow_private_ip': True,
            'require_tld': False
        },
        ConfigType.ENUM: {
            'allowed_values': [],  # 允许的枚举值列表
            'case_sensitive': True
        },
        ConfigType.PASSWORD: {
            'min_length': 8,
            'max_length': 128,
            'require_uppercase': False,
            'require_lowercase': False,
            'require_digits': False,
            'require_special_chars': False,
            'forbidden_patterns': []
        },
        ConfigType.FILE: {
            'allowed_extensions': [],  # 允许的文件扩展名
            'max_size': 104857600,  # 100MB
            'check_existence': False,  # 是否检查文件是否存在
            'absolute_path_only': False
        },
        ConfigType.COLOR: {
            'formats': ['hex', 'rgb', 'rgba', 'hsl', 'hsla'],  # 支持的颜色格式
            'allow_named_colors': True  # 是否允许命名颜色（如red、blue）
        },
        ConfigType.DATE: {
            'formats': ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y'],  # 支持的日期格式
            'min_date': None,  # 最小日期
            'max_date': None   # 最大日期
        },
        ConfigType.TIME: {
            'formats': ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'],  # 支持的时间格式
            'min_time': None,  # 最小时间
            'max_time': None   # 最大时间
        }
    }
    
    @classmethod
    def validate_config_value(cls, value: Any, config_type: ConfigType, 
                            validation_rule: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        验证配置值
        
        Args:
            value: 配置值
            config_type: 配置类型
            validation_rule: 自定义验证规则
            
        Returns:
            (是否有效, 错误消息)
        """
        try:
            validator = cls()
            return validator.validate(value, config_type, validation_rule)
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False, f"验证过程出错: {str(e)}"
    
    def validate(self, value: Any, config_type: ConfigType, 
                validation_rule: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        验证配置值
        
        Args:
            value: 配置值
            config_type: 配置类型
            validation_rule: 自定义验证规则
            
        Returns:
            (是否有效, 错误消息)
        """
        # 如果值为None或空字符串，检查是否必填
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return True, None  # 空值验证由is_required字段在上层处理
        
        # 合并默认规则和自定义规则
        rules = ValidationRule(self._merge_rules(config_type, validation_rule))
        
        # 根据类型调用相应的验证方法
        validation_methods = {
            ConfigType.STRING: self._validate_string,
            ConfigType.TEXT: self._validate_text,
            ConfigType.INTEGER: self._validate_integer,
            ConfigType.FLOAT: self._validate_float,
            ConfigType.BOOLEAN: self._validate_boolean,
            ConfigType.JSON: self._validate_json,
            ConfigType.ARRAY: self._validate_array,
            ConfigType.EMAIL: self._validate_email,
            ConfigType.URL: self._validate_url,
            ConfigType.ENUM: self._validate_enum,
            ConfigType.PASSWORD: self._validate_password,
            ConfigType.FILE: self._validate_file,
            ConfigType.COLOR: self._validate_color,
            ConfigType.DATE: self._validate_date,
            ConfigType.TIME: self._validate_time
        }
        
        method = validation_methods.get(config_type)
        if not method:
            return False, f"不支持的配置类型: {config_type}"
        
        return method(value, rules)
    
    def _merge_rules(self, config_type: ConfigType, custom_rules: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并默认规则和自定义规则"""
        default_rules = self.DEFAULT_RULES.get(config_type, {}).copy()
        if custom_rules:
            default_rules.update(custom_rules)
        return default_rules
    
    def _validate_string(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证字符串类型"""
        # 转换为字符串
        if not isinstance(value, str):
            value = str(value)
        
        # 长度验证
        min_length = rules.get('min_length', 0)
        max_length = rules.get('max_length', 65535)
        
        if len(value) < min_length:
            return False, f"字符串长度不能少于{min_length}个字符"
        
        if len(value) > max_length:
            return False, f"字符串长度不能超过{max_length}个字符"
        
        # 正则表达式验证
        pattern = rules.get('pattern')
        if pattern:
            try:
                if not re.match(pattern, value):
                    return False, f"字符串格式不符合要求: {pattern}"
            except re.error as e:
                return False, f"正则表达式错误: {e}"
        
        # 允许的字符验证
        allowed_chars = rules.get('allowed_chars')
        if allowed_chars and not all(c in allowed_chars for c in value):
            return False, f"包含不允许的字符，只允许: {allowed_chars}"
        
        # 禁止的字符验证
        forbidden_chars = rules.get('forbidden_chars')
        if forbidden_chars and any(c in forbidden_chars for c in value):
            return False, f"包含禁止的字符: {forbidden_chars}"
        
        return True, None
    
    def _validate_integer(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证整数类型"""
        # 类型转换
        try:
            if isinstance(value, str):
                int_value = int(value)
            elif isinstance(value, (int, float)):
                int_value = int(value)
            else:
                return False, "值不能转换为整数"
        except (ValueError, TypeError):
            return False, "值不是有效的整数"
        
        # 范围验证
        min_value = rules.get('min_value', -(2**63))
        max_value = rules.get('max_value', 2**63 - 1)
        
        if int_value < min_value:
            return False, f"整数值不能小于{min_value}"
        
        if int_value > max_value:
            return False, f"整数值不能大于{max_value}"
        
        return True, None
    
    def _validate_boolean(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证布尔类型"""
        if isinstance(value, bool):
            return True, None
        
        # 字符串转布尔
        if isinstance(value, str):
            value_lower = value.lower().strip()
            true_values = rules.get('true_values', ['true', '1', 'yes', 'on'])
            false_values = rules.get('false_values', ['false', '0', 'no', 'off'])
            
            if value_lower in true_values or value_lower in false_values:
                return True, None
        
        # 数字转布尔
        if isinstance(value, (int, float)):
            return True, None
        
        return False, "值不是有效的布尔值"
    
    def _validate_json(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证JSON类型"""
        # 如果已经是dict或list，转换为JSON字符串再解析
        if isinstance(value, (dict, list)):
            try:
                json_str = json.dumps(value, ensure_ascii=False)
                json_obj = value
            except (TypeError, ValueError) as e:
                return False, f"JSON对象序列化失败: {e}"
        else:
            # 字符串解析
            if not isinstance(value, str):
                value = str(value)
            
            try:
                json_obj = json.loads(value)
                json_str = value
            except json.JSONDecodeError as e:
                return False, f"JSON格式错误: {e}"
        
        # 长度验证
        max_length = rules.get('max_length', 1048576)
        if len(json_str.encode('utf-8')) > max_length:
            return False, f"JSON长度超过限制: {max_length}字节"
        
        # 深度验证
        max_depth = rules.get('max_depth', 10)
        if self._get_json_depth(json_obj) > max_depth:
            return False, f"JSON嵌套深度超过限制: {max_depth}"
        
        # 必需键验证
        required_keys = rules.get('required_keys', [])
        if required_keys and isinstance(json_obj, dict):
            missing_keys = [key for key in required_keys if key not in json_obj]
            if missing_keys:
                return False, f"缺少必需的键: {missing_keys}"
        
        # 禁止键验证
        forbidden_keys = rules.get('forbidden_keys', [])
        if forbidden_keys and isinstance(json_obj, dict):
            found_forbidden = [key for key in forbidden_keys if key in json_obj]
            if found_forbidden:
                return False, f"包含禁止的键: {found_forbidden}"
        
        return True, None
    
    def _validate_password(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证密码类型"""
        if not isinstance(value, str):
            return False, "密码必须是字符串"
        
        # 长度验证
        min_length = rules.get('min_length', 8)
        max_length = rules.get('max_length', 128)
        
        if len(value) < min_length:
            return False, f"密码长度不能少于{min_length}个字符"
        
        if len(value) > max_length:
            return False, f"密码长度不能超过{max_length}个字符"
        
        # 复杂度验证
        if rules.get('require_uppercase', False) and not re.search(r'[A-Z]', value):
            return False, "密码必须包含大写字母"
        
        if rules.get('require_lowercase', False) and not re.search(r'[a-z]', value):
            return False, "密码必须包含小写字母"
        
        if rules.get('require_digits', False) and not re.search(r'\d', value):
            return False, "密码必须包含数字"
        
        if rules.get('require_special_chars', False) and not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            return False, "密码必须包含特殊字符"
        
        # 禁止模式验证
        forbidden_patterns = rules.get('forbidden_patterns', [])
        for pattern in forbidden_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False, f"密码包含禁止的模式"
        
        return True, None
    
    def _validate_url(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
        """验证URL类型"""
        if not isinstance(value, str):
            return False, "URL必须是字符串"
        
        try:
            parsed = urlparse(value)
        except Exception as e:
            return False, f"URL格式错误: {e}"
        
        # 协议验证
        allowed_schemes = rules.get('allowed_schemes', ['http', 'https'])
        if parsed.scheme.lower() not in allowed_schemes:
            return False, f"不支持的协议，允许的协议: {allowed_schemes}"
        
        # 主机名验证
        if not parsed.netloc:
            return False, "URL必须包含主机名"
        
        # localhost验证
        if not rules.get('allow_localhost', True):
            if parsed.hostname in ['localhost', '127.0.0.1', '::1']:
                return False, "不允许使用localhost"
        
        # 私有IP验证
        if not rules.get('allow_private_ip', True):
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private:
                    return False, "不允许使用私有IP地址"
            except ValueError:
                pass  # 不是IP地址，跳过检查
        
        # TLD验证
        if rules.get('require_tld', False):
            hostname = parsed.hostname or parsed.netloc.split(':')[0]
            if '.' not in hostname or hostname.split('.')[-1].isdigit():
                return False, "URL必须包含有效的顶级域名"
        
        return True, None
    
    def _get_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """获取JSON对象的嵌套深度"""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_json_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_json_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    @classmethod
    def get_validation_schema(cls, config_type: ConfigType) -> Dict[str, Any]:
        """获取配置类型的验证规则模式"""
        return cls.DEFAULT_RULES.get(config_type, {}).copy()
    
    @classmethod
    def convert_value(cls, value: str, config_type: ConfigType) -> Any:
        """
        将字符串值转换为对应的类型
        
        Args:
            value: 字符串值
            config_type: 目标类型
            
        Returns:
            转换后的值
        """
        if not value:
            return value
        
        try:
            if config_type == ConfigType.STRING:
                return str(value)
            elif config_type == ConfigType.INTEGER:
                return int(value)
            elif config_type == ConfigType.BOOLEAN:
                value_lower = value.lower().strip()
                true_values = ['true', '1', 'yes', 'on', 'enable', 'enabled']
                return value_lower in true_values
            elif config_type == ConfigType.JSON:
                return json.loads(value)
            elif config_type in [ConfigType.PASSWORD, ConfigType.URL]:
                return str(value)
            else:
                return value
        except Exception:
            # 转换失败，返回原值
            return value


# 便捷函数
def validate_config(value: Any, config_type: str, validation_rule: Optional[Dict] = None) -> Tuple[bool, Optional[str]]:
    """验证配置值的便捷函数"""
    try:
        config_type_enum = ConfigType(config_type.upper())
        return ConfigValidator.validate_config_value(value, config_type_enum, validation_rule)
    except ValueError:
        return False, f"不支持的配置类型: {config_type}"


def convert_config_value(value: str, config_type: str) -> Any:
    """转换配置值的便捷函数"""
    try:
        config_type_enum = ConfigType(config_type.upper())
        return ConfigValidator.convert_value(value, config_type_enum)
    except ValueError:
        return value


# 为ConfigValidator类添加新的验证方法
def _validate_text(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证长文本类型（基本与字符串相同，但支持更大长度）"""
    return self._validate_string(value, rules)


def _validate_float(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证浮点数类型"""
    # 类型转换
    try:
        if isinstance(value, str):
            float_value = float(value)
        elif isinstance(value, (int, float)):
            float_value = float(value)
        else:
            return False, "值不能转换为浮点数"
    except (ValueError, TypeError):
        return False, "值不是有效的浮点数"
    
    # 范围验证
    min_value = rules.get('min_value', float('-inf'))
    max_value = rules.get('max_value', float('inf'))
    
    if float_value < min_value:
        return False, f"浮点数值不能小于{min_value}"
    
    if float_value > max_value:
        return False, f"浮点数值不能大于{max_value}"
    
    # 精度验证
    precision = rules.get('precision')
    if precision is not None:
        decimal_places = len(str(float_value).split('.')[-1]) if '.' in str(float_value) else 0
        if decimal_places > precision:
            return False, f"浮点数精度不能超过{precision}位小数"
    
    return True, None


# 为ConfigValidator类添加新的验证方法
ConfigValidator._validate_text = _validate_text
ConfigValidator._validate_float = _validate_float

# 导入并加载其他验证方法扩展
try:
    from .config_validator_ext import *
except ImportError:
    pass  # 扩展模块不存在时忽略