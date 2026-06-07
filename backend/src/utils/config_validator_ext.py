"""
配置验证器扩展 - 为新配置类型添加验证方法
"""
import re
import json
import os
from typing import Any, Tuple, Optional
from datetime import datetime
from .config_validator import ConfigValidator, ValidationRule


def _validate_array(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证数组类型"""
    # 类型转换
    if isinstance(value, str):
        try:
            array_value = json.loads(value)
            if not isinstance(array_value, list):
                return False, "数组值必须是JSON数组格式"
        except json.JSONDecodeError:
            return False, "数组值不是有效的JSON格式"
    elif isinstance(value, list):
        array_value = value
    else:
        return False, "数组值必须是数组或JSON数组字符串"
    
    # 数组长度验证
    min_items = rules.get('min_items', 0)
    max_items = rules.get('max_items', 1000)
    
    if len(array_value) < min_items:
        return False, f"数组元素数量不能少于{min_items}个"
    
    if len(array_value) > max_items:
        return False, f"数组元素数量不能超过{max_items}个"
    
    # 唯一性验证
    if rules.get('unique_items', False):
        if len(array_value) != len(set(json.dumps(item, sort_keys=True) for item in array_value)):
            return False, "数组元素必须唯一"
    
    return True, None


def _validate_email(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证邮箱类型"""
    if not isinstance(value, str):
        return False, "邮箱必须是字符串"
    
    # 多邮箱支持
    if rules.get('allow_multiple', False):
        emails = [email.strip() for email in value.split(',')]
    else:
        emails = [value.strip()]
    
    for email in emails:
        # 基本邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, f"邮箱格式不正确: {email}"
        
        # 域名限制
        domain = email.split('@')[1]
        
        allowed_domains = rules.get('allowed_domains', [])
        if allowed_domains and domain not in allowed_domains:
            return False, f"不允许的邮箱域名: {domain}"
        
        forbidden_domains = rules.get('forbidden_domains', [])
        if domain in forbidden_domains:
            return False, f"禁止的邮箱域名: {domain}"
    
    return True, None


def _validate_enum(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证枚举类型"""
    allowed_values = rules.get('allowed_values', [])
    if not allowed_values:
        return False, "枚举类型必须定义允许的值列表"
    
    case_sensitive = rules.get('case_sensitive', True)
    
    if case_sensitive:
        if value not in allowed_values:
            return False, f"枚举值不在允许列表中: {allowed_values}"
    else:
        if str(value).lower() not in [str(v).lower() for v in allowed_values]:
            return False, f"枚举值不在允许列表中: {allowed_values}"
    
    return True, None


def _validate_file(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证文件路径类型"""
    if not isinstance(value, str):
        return False, "文件路径必须是字符串"
    
    # 绝对路径验证
    if rules.get('absolute_path_only', False) and not os.path.isabs(value):
        return False, "必须使用绝对路径"
    
    # 文件扩展名验证
    allowed_extensions = rules.get('allowed_extensions', [])
    if allowed_extensions:
        file_ext = os.path.splitext(value)[1].lower()
        if file_ext not in [ext.lower() for ext in allowed_extensions]:
            return False, f"不允许的文件扩展名，允许: {allowed_extensions}"
    
    # 文件存在性验证
    if rules.get('check_existence', False) and not os.path.exists(value):
        return False, f"文件不存在: {value}"
    
    return True, None


def _validate_color(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证颜色值类型"""
    if not isinstance(value, str):
        return False, "颜色值必须是字符串"
    
    value = value.strip()
    formats = rules.get('formats', ['hex', 'rgb', 'rgba', 'hsl', 'hsla'])
    allow_named_colors = rules.get('allow_named_colors', True)
    
    # 命名颜色验证
    if allow_named_colors:
        named_colors = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'brown', 'black', 'white', 'gray', 'grey']
        if value.lower() in named_colors:
            return True, None
    
    # HEX颜色验证
    if 'hex' in formats and re.match(r'^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^#[0-9a-fA-F]{8}$', value):
        return True, None
    
    # RGB颜色验证
    if 'rgb' in formats and re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', value):
        return True, None
    
    # RGBA颜色验证
    if 'rgba' in formats and re.match(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[0-1]?(\.[0-9]+)?\s*\)$', value):
        return True, None
    
    # HSL颜色验证
    if 'hsl' in formats and re.match(r'^hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)$', value):
        return True, None
    
    # HSLA颜色验证
    if 'hsla' in formats and re.match(r'^hsla\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*,\s*[0-1]?(\.[0-9]+)?\s*\)$', value):
        return True, None
    
    return False, f"颜色值格式不正确，支持的格式: {formats}"


def _validate_date(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证日期类型"""
    if not isinstance(value, str):
        return False, "日期必须是字符串"
    
    formats = rules.get('formats', ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y'])
    
    parsed_date = None
    for date_format in formats:
        try:
            parsed_date = datetime.strptime(value, date_format)
            break
        except ValueError:
            continue
    
    if parsed_date is None:
        return False, f"日期格式不正确，支持的格式: {formats}"
    
    # 日期范围验证
    min_date = rules.get('min_date')
    if min_date and parsed_date < min_date:
        return False, f"日期不能早于{min_date}"
    
    max_date = rules.get('max_date')
    if max_date and parsed_date > max_date:
        return False, f"日期不能晚于{max_date}"
    
    return True, None


def _validate_time(self, value: Any, rules: ValidationRule) -> Tuple[bool, Optional[str]]:
    """验证时间类型"""
    if not isinstance(value, str):
        return False, "时间必须是字符串"
    
    formats = rules.get('formats', ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'])
    
    parsed_time = None
    for time_format in formats:
        try:
            parsed_time = datetime.strptime(value, time_format).time()
            break
        except ValueError:
            continue
    
    if parsed_time is None:
        return False, f"时间格式不正确，支持的格式: {formats}"
    
    # 时间范围验证
    min_time = rules.get('min_time')
    if min_time and parsed_time < min_time:
        return False, f"时间不能早于{min_time}"
    
    max_time = rules.get('max_time')
    if max_time and parsed_time > max_time:
        return False, f"时间不能晚于{max_time}"
    
    return True, None


# 将新的验证方法添加到ConfigValidator类
ConfigValidator._validate_array = _validate_array
ConfigValidator._validate_email = _validate_email
ConfigValidator._validate_enum = _validate_enum
ConfigValidator._validate_file = _validate_file
ConfigValidator._validate_color = _validate_color
ConfigValidator._validate_date = _validate_date
ConfigValidator._validate_time = _validate_time

print("✅ ConfigValidator已扩展支持15种配置类型的验证")