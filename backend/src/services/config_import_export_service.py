"""
配置文件导入导出服务
支持 .env、JSON、YAML、XML、Properties 格式
"""
import json
import yaml
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import Dict, List, Any, Tuple, Optional, Union
from enum import Enum
import logging
import configparser
from io import StringIO
import re

from ..models.config import SystemConfig, ConfigType, Environment
from ..services.config import config_service
from ..core.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FileFormat(str, Enum):
    """文件格式枚举"""
    ENV = "env"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    PROPERTIES = "properties"


class ConfigImportExportService:
    """配置导入导出服务"""
    
    def __init__(self):
        self.supported_formats = {
            FileFormat.ENV: {
                'extensions': ['.env'],
                'mime_types': ['text/plain'],
                'description': '环境变量文件'
            },
            FileFormat.JSON: {
                'extensions': ['.json'],
                'mime_types': ['application/json'],
                'description': 'JSON配置文件'
            },
            FileFormat.YAML: {
                'extensions': ['.yml', '.yaml'],
                'mime_types': ['application/x-yaml', 'text/yaml'],
                'description': 'YAML配置文件'
            },
            FileFormat.XML: {
                'extensions': ['.xml'],
                'mime_types': ['application/xml', 'text/xml'],
                'description': 'XML配置文件'
            },
            FileFormat.PROPERTIES: {
                'extensions': ['.properties'],
                'mime_types': ['text/plain'],
                'description': 'Properties配置文件'
            }
        }

    async def export_configs(
        self,
        format_type: FileFormat,
        environment: str,
        group_id: Optional[int] = None,
        config_keys: Optional[List[str]] = None,
        include_sensitive: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        导出配置文件
        
        Args:
            format_type: 导出格式
            environment: 环境名
            group_id: 分组ID（可选）
            config_keys: 指定配置键列表（可选）
            include_sensitive: 是否包含敏感配置
            
        Returns:
            (成功状态, 错误信息, 文件内容)
        """
        try:
            # 获取配置数据
            db = next(get_db())
            query = db.query(SystemConfig).filter(
                SystemConfig.environment == environment,
                SystemConfig.is_enabled.is_(True)
            )
            
            if group_id:
                query = query.filter(SystemConfig.group_id == group_id)
            
            if config_keys:
                query = query.filter(SystemConfig.config_key.in_(config_keys))
            
            if not include_sensitive:
                query = query.filter(SystemConfig.is_encrypted.is_(False))
            
            configs = query.all()
            
            if not configs:
                return False, "没有找到要导出的配置", None
            
            # 转换为字典格式
            config_dict = {}
            for config in configs:
                # 敏感配置脱敏处理
                value = config.config_value
                if not include_sensitive and config.is_encrypted:
                    value = "****"  # 脱敏显示
                
                config_dict[config.config_key] = {
                    'value': value,
                    'type': config.config_type.value,
                    'description': config.description,
                    'group_id': config.group_id,
                    'is_sensitive': config.is_encrypted
                }
            
            # 根据格式生成文件内容
            if format_type == FileFormat.ENV:
                content = self._export_to_env(config_dict)
            elif format_type == FileFormat.JSON:
                content = self._export_to_json(config_dict)
            elif format_type == FileFormat.YAML:
                content = self._export_to_yaml(config_dict)
            elif format_type == FileFormat.XML:
                content = self._export_to_xml(config_dict)
            elif format_type == FileFormat.PROPERTIES:
                content = self._export_to_properties(config_dict)
            else:
                return False, f"不支持的导出格式: {format_type}", None
            
            return True, None, content
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False, f"导出配置失败: {str(e)}", None

    async def import_configs(
        self,
        file_content: str,
        format_type: FileFormat,
        environment: str,
        user_id: int,
        group_id: Optional[int] = None,
        overwrite_existing: bool = False,
        dry_run: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        导入配置文件
        
        Args:
            file_content: 文件内容
            format_type: 文件格式
            environment: 目标环境
            user_id: 操作用户ID
            group_id: 目标分组ID（可选）
            overwrite_existing: 是否覆盖已存在的配置
            dry_run: 是否为试运行（不实际导入）
            
        Returns:
            (成功状态, 错误信息, 导入结果)
        """
        try:
            # 解析文件内容
            if format_type == FileFormat.ENV:
                parsed_configs = self._parse_env_file(file_content)
            elif format_type == FileFormat.JSON:
                parsed_configs = self._parse_json_file(file_content)
            elif format_type == FileFormat.YAML:
                parsed_configs = self._parse_yaml_file(file_content)
            elif format_type == FileFormat.XML:
                parsed_configs = self._parse_xml_file(file_content)
            elif format_type == FileFormat.PROPERTIES:
                parsed_configs = self._parse_properties_file(file_content)
            else:
                return False, f"不支持的导入格式: {format_type}", None
            
            if not parsed_configs:
                return False, "文件中没有找到有效的配置项", None
            
            # 验证配置格式
            validation_result = await self._validate_import_configs(parsed_configs)
            if not validation_result['valid']:
                return False, f"配置验证失败: {validation_result['errors']}", None
            
            # 检查冲突
            db = next(get_db())
            existing_configs = db.query(SystemConfig).filter(
                SystemConfig.environment == environment,
                SystemConfig.config_key.in_(list(parsed_configs.keys()))
            ).all()
            
            conflicts = []
            for existing in existing_configs:
                if existing.config_key in parsed_configs:
                    conflicts.append({
                        'key': existing.config_key,
                        'existing_value': existing.config_value,
                        'new_value': parsed_configs[existing.config_key]['value']
                    })
            
            if conflicts and not overwrite_existing:
                return False, "存在配置冲突，请选择是否覆盖", {
                    'conflicts': conflicts,
                    'total_configs': len(parsed_configs)
                }
            
            # 如果是试运行，返回预览结果
            if dry_run:
                return True, None, {
                    'preview': True,
                    'total_configs': len(parsed_configs),
                    'conflicts': conflicts,
                    'new_configs': [key for key in parsed_configs.keys() 
                                  if key not in [c['key'] for c in conflicts]],
                    'configs': parsed_configs
                }
            
            # 执行导入
            import_result = await self._execute_import(
                parsed_configs, environment, user_id, group_id, overwrite_existing
            )
            
            return True, None, import_result
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False, f"导入配置失败: {str(e)}", None

    def _export_to_env(self, config_dict: Dict) -> str:
        """导出为 .env 格式"""
        lines = ["# 配置文件导出", f"# 导出时间: {self._get_current_time()}", ""]
        
        for key, config in config_dict.items():
            if config.get('description'):
                lines.append(f"# {config['description']}")
            
            value = config['value']
            # 如果值包含特殊字符，需要加引号
            if isinstance(value, str) and (' ' in value or '"' in value or "'" in value):
                value = f'"{value}"'
            
            lines.append(f"{key}={value}")
            lines.append("")
        
        return "\n".join(lines)

    def _export_to_json(self, config_dict: Dict) -> str:
        """导出为 JSON 格式"""
        export_data = {
            "metadata": {
                "export_time": self._get_current_time(),
                "format": "json",
                "total_configs": len(config_dict)
            },
            "configs": {}
        }
        
        for key, config in config_dict.items():
            export_data["configs"][key] = {
                "value": self._convert_config_value(config['value'], config['type']),
                "type": config['type'],
                "description": config.get('description', ''),
                "is_sensitive": config.get('is_sensitive', False)
            }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def _export_to_yaml(self, config_dict: Dict) -> str:
        """导出为 YAML 格式"""
        export_data = {
            "metadata": {
                "export_time": self._get_current_time(),
                "format": "yaml",
                "total_configs": len(config_dict)
            },
            "configs": {}
        }
        
        for key, config in config_dict.items():
            export_data["configs"][key] = {
                "value": self._convert_config_value(config['value'], config['type']),
                "type": config['type'],
                "description": config.get('description', ''),
                "is_sensitive": config.get('is_sensitive', False)
            }
        
        return yaml.dump(export_data, default_flow_style=False, allow_unicode=True)

    def _export_to_xml(self, config_dict: Dict) -> str:
        """导出为 XML 格式"""
        root = ET.Element("configuration")
        
        # 添加元数据
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "export_time").text = self._get_current_time()
        ET.SubElement(metadata, "format").text = "xml"
        ET.SubElement(metadata, "total_configs").text = str(len(config_dict))
        
        # 添加配置项
        configs = ET.SubElement(root, "configs")
        for key, config in config_dict.items():
            config_elem = ET.SubElement(configs, "config")
            config_elem.set("key", key)
            
            ET.SubElement(config_elem, "value").text = str(config['value'])
            ET.SubElement(config_elem, "type").text = config['type']
            ET.SubElement(config_elem, "description").text = config.get('description', '')
            ET.SubElement(config_elem, "is_sensitive").text = str(config.get('is_sensitive', False))
        
        # 格式化输出
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _export_to_properties(self, config_dict: Dict) -> str:
        """导出为 Properties 格式"""
        lines = [
            "# 配置文件导出",
            f"# 导出时间: {self._get_current_time()}",
            f"# 配置项数量: {len(config_dict)}",
            ""
        ]
        
        for key, config in config_dict.items():
            if config.get('description'):
                lines.append(f"# {config['description']}")
            
            # Properties 格式需要转义特殊字符
            value = str(config['value']).replace('\\', '\\\\').replace('=', '\\=').replace(':', '\\:')
            lines.append(f"{key}={value}")
            lines.append("")
        
        return "\n".join(lines)

    def _parse_env_file(self, content: str) -> Dict:
        """解析 .env 文件"""
        configs = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                configs[key] = {
                    'value': value,
                    'type': self._infer_config_type(value),
                    'description': '',
                    'is_sensitive': False
                }
        
        return configs

    def _parse_json_file(self, content: str) -> Dict:
        """解析 JSON 文件"""
        try:
            data = json.loads(content)
            
            # 如果是标准格式
            if 'configs' in data:
                return data['configs']
            
            # 如果是简单的键值对格式
            configs = {}
            for key, value in data.items():
                if isinstance(value, dict) and 'value' in value:
                    configs[key] = value
                else:
                    configs[key] = {
                        'value': value,
                        'type': self._infer_config_type(value),
                        'description': '',
                        'is_sensitive': False
                    }
            
            return configs
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {e}")

    def _parse_yaml_file(self, content: str) -> Dict:
        """解析 YAML 文件"""
        try:
            data = yaml.safe_load(content)
            
            # 如果是标准格式
            if isinstance(data, dict) and 'configs' in data:
                return data['configs']
            
            # 如果是简单的键值对格式
            configs = {}
            for key, value in data.items():
                if isinstance(value, dict) and 'value' in value:
                    configs[key] = value
                else:
                    configs[key] = {
                        'value': value,
                        'type': self._infer_config_type(value),
                        'description': '',
                        'is_sensitive': False
                    }
            
            return configs
            
        except yaml.YAMLError as e:
            raise ValueError(f"YAML格式错误: {e}")

    def _parse_xml_file(self, content: str) -> Dict:
        """解析 XML 文件"""
        try:
            root = ET.fromstring(content)
            configs = {}
            
            # 查找配置节点
            config_nodes = root.findall(".//config") or root.findall(".//configs/config")
            
            for config_node in config_nodes:
                key = config_node.get('key') or config_node.find('key')
                if key is None:
                    continue
                
                if isinstance(key, ET.Element):
                    key = key.text
                
                value_node = config_node.find('value')
                value = value_node.text if value_node is not None else ''
                
                type_node = config_node.find('type')
                config_type = type_node.text if type_node is not None else self._infer_config_type(value)
                
                desc_node = config_node.find('description')
                description = desc_node.text if desc_node is not None else ''
                
                sensitive_node = config_node.find('is_sensitive')
                is_sensitive = (sensitive_node is not None and 
                              sensitive_node.text and
                              sensitive_node.text.lower() == 'true')
                
                configs[key] = {
                    'value': value,
                    'type': config_type,
                    'description': description,
                    'is_sensitive': is_sensitive
                }
            
            return configs
            
        except ET.ParseError as e:
            raise ValueError(f"XML格式错误: {e}")

    def _parse_properties_file(self, content: str) -> Dict:
        """解析 Properties 文件"""
        configs = {}
        
        # 使用 configparser 解析
        config_parser = configparser.ConfigParser()
        config_parser.read_string(f"[DEFAULT]\n{content}")
        
        for key, value in config_parser['DEFAULT'].items():
            configs[key] = {
                'value': value,
                'type': self._infer_config_type(value),
                'description': '',
                'is_sensitive': False
            }
        
        return configs

    def _infer_config_type(self, value: Any) -> str:
        """推断配置类型"""
        if isinstance(value, bool):
            return ConfigType.BOOLEAN.value
        elif isinstance(value, int):
            return ConfigType.INTEGER.value
        elif isinstance(value, float):
            return ConfigType.STRING.value  # 暂时使用STRING代替FLOAT
        elif isinstance(value, (dict, list)):
            return ConfigType.JSON.value
        elif isinstance(value, str):
            # 尝试推断特殊类型
            if value.lower() in ['true', 'false']:
                return ConfigType.BOOLEAN.value
            elif value.isdigit():
                return ConfigType.INTEGER.value
            elif self._is_float(value):
                return ConfigType.STRING.value  # 暂时使用STRING代替FLOAT
            elif value.startswith('http://') or value.startswith('https://'):
                return ConfigType.URL.value
            elif '@' in value and '.' in value:
                return ConfigType.STRING.value  # 暂时使用STRING代替EMAIL
            else:
                return ConfigType.STRING.value
        else:
            return ConfigType.STRING.value

    def _is_float(self, value: str) -> bool:
        """检查字符串是否为浮点数"""
        try:
            float(value)
            return '.' in value
        except ValueError:
            return False

    def _convert_config_value(self, value: Any, config_type: str) -> Any:
        """根据配置类型转换值"""
        try:
            if config_type == ConfigType.BOOLEAN.value:
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes', 'on']
                return bool(value)
            elif config_type == ConfigType.INTEGER.value:
                return int(value)
            elif config_type == ConfigType.STRING.value:  # 暂时使用STRING代替FLOAT
                try:
                    return float(value)
                except ValueError:
                    return str(value)
            elif config_type == ConfigType.JSON.value:
                if isinstance(value, str):
                    return json.loads(value)
                return value
            else:
                return str(value)
        except (ValueError, json.JSONDecodeError):
            return value

    async def _validate_import_configs(self, configs: Dict) -> Dict:
        """验证导入的配置"""
        errors = []
        
        for key, config in configs.items():
            # 验证配置键名
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*$', key):
                errors.append(f"配置键 '{key}' 格式不正确")
            
            # 验证配置类型
            config_type = config.get('type', 'STRING')
            if config_type not in [t.value for t in ConfigType]:
                errors.append(f"配置 '{key}' 的类型 '{config_type}' 不支持")
            
            # 验证配置值
            try:
                self._convert_config_value(config['value'], config_type)
            except Exception as e:
                errors.append(f"配置 '{key}' 的值格式错误: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    async def _execute_import(
        self,
        configs: Dict,
        environment: str,
        user_id: int,
        group_id: Optional[int],
        overwrite_existing: bool
    ) -> Dict:
        """执行配置导入"""
        success_count = 0
        error_count = 0
        errors = []
        
        for key, config in configs.items():
            try:
                # 检查配置是否已存在
                existing = await config_service.get_config(key, environment)
                
                if existing and not overwrite_existing:
                    error_count += 1
                    errors.append(f"配置 '{key}' 已存在，跳过导入")
                    continue
                
                # 创建或更新配置
                config_data = {
                    'config_key': key,
                    'config_value': str(config['value']),
                    'config_type': ConfigType(config.get('type', 'STRING')),
                    'environment': Environment(environment),
                    'description': config.get('description', ''),
                    'group_id': group_id,
                    'is_encrypted': config.get('is_sensitive', False),
                    'created_by': user_id,
                    'updated_by': user_id
                }
                
                if existing:
                    await config_service.update_config(key, config_data)
                else:
                    await config_service.create_config(config_data)
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"导入配置 '{key}' 失败: {e}")
                logger.error(f"导入配置失败: {key} - {e}")
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'total_count': len(configs),
            'errors': errors
        }

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_supported_formats(self) -> Dict:
        """获取支持的文件格式"""
        return self.supported_formats


# 创建全局实例
config_import_export_service = ConfigImportExportService()