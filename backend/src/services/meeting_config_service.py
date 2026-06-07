"""
会议配置管理服务

提供会议系统的配置管理功能，包括：
- 系统配置管理
- 环境变量配置
- WebRTC配置
- 第三方服务配置
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.config import Config
from ..core.exceptions import ConfigurationError, ValidationError


class MeetingConfigService:
    """会议配置服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._config_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5分钟缓存
    
    async def update_meeting_config(self, config_data: Dict[str, Any]) -> None:
        """更新会议配置"""
        try:
            for key, value in config_data.items():
                # 检查配置是否存在
                config_query = select(Config).where(
                    and_(
                        Config.category == 'meeting',
                        Config.key == key
                    )
                )
                config_result = await self.db_session.execute(config_query)
                config = config_result.scalar_one_or_none()
                
                if config:
                    # 更新现有配置
                    config.value = value
                    config.updated_at = datetime.now()
                else:
                    # 创建新配置
                    new_config = Config(
                        category='meeting',
                        key=key,
                        value=value,
                        description=self._get_config_description(key),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    self.db_session.add(new_config)
            
            await self.db_session.flush()
            
            # 清除缓存
            self._clear_cache()
            
        except Exception as e:
            raise ConfigurationError(f"配置更新失败: {str(e)}")
    
    async def get_meeting_config(self, key: str) -> Any:
        """获取会议配置"""
        try:
            # 检查缓存
            if self._is_cache_valid():
                if key in self._config_cache:
                    return self._config_cache[key]
            
            # 从数据库获取
            config_query = select(Config).where(
                and_(
                    Config.category == 'meeting',
                    Config.key == key
                )
            )
            config_result = await self.db_session.execute(config_query)
            config = config_result.scalar_one_or_none()
            
            if config:
                value = config.value
                self._config_cache[key] = value
                return value
            
            # 返回默认值
            return self._get_default_config_value(key)
            
        except Exception as e:
            raise ConfigurationError(f"配置获取失败: {str(e)}")
    
    async def get_all_meeting_configs(self) -> Dict[str, Any]:
        """获取所有会议配置"""
        try:
            # 检查缓存
            if self._is_cache_valid() and self._config_cache:
                return self._config_cache.copy()
            
            # 从数据库获取所有配置
            config_query = select(Config).where(Config.category == 'meeting')
            config_result = await self.db_session.execute(config_query)
            configs = config_result.scalars().all()
            
            config_dict = {}
            for config in configs:
                config_dict[config.key] = config.value
            
            # 添加默认配置
            default_configs = self._get_default_configs()
            for key, value in default_configs.items():
                if key not in config_dict:
                    config_dict[key] = value
            
            # 更新缓存
            self._config_cache = config_dict
            self._cache_timestamp = datetime.now()
            
            return config_dict.copy()
            
        except Exception as e:
            raise ConfigurationError(f"配置获取失败: {str(e)}")
    
    async def get_webrtc_config(self, meeting_id: int) -> Dict[str, Any]:
        """获取WebRTC配置"""
        try:
            # 获取基础WebRTC配置
            webrtc_config = await self.get_meeting_config('webrtc_servers')
            
            if not webrtc_config:
                # 使用默认WebRTC配置
                webrtc_config = {
                    'stun_servers': [
                        'stun:stun.l.google.com:19302',
                        'stun:stun1.l.google.com:19302'
                    ],
                    'turn_servers': []
                }
            
            # 添加会议特定配置
            webrtc_config['meeting_id'] = meeting_id
            webrtc_config['ice_transport_policy'] = 'all'
            webrtc_config['bundle_policy'] = 'balanced'
            webrtc_config['rtcp_mux_policy'] = 'require'
            
            # 从环境变量获取TURN服务器配置
            turn_server = os.getenv('WEBRTC_TURN_SERVER')
            turn_username = os.getenv('WEBRTC_TURN_USERNAME')
            turn_credential = os.getenv('WEBRTC_TURN_CREDENTIAL')
            
            if turn_server and turn_username and turn_credential:
                webrtc_config['turn_servers'].append({
                    'urls': turn_server,
                    'username': turn_username,
                    'credential': turn_credential
                })
            
            return webrtc_config
            
        except Exception as e:
            raise ConfigurationError(f"WebRTC配置获取失败: {str(e)}")
    
    async def load_environment_config(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}
        
        # 会议基础配置
        if os.getenv('MEETING_MAX_DURATION'):
            env_config['max_duration'] = int(os.getenv('MEETING_MAX_DURATION'))
        
        if os.getenv('MEETING_MAX_PARTICIPANTS'):
            env_config['max_participants'] = int(os.getenv('MEETING_MAX_PARTICIPANTS'))
        
        # WebRTC配置
        if os.getenv('WEBRTC_STUN_SERVER'):
            env_config['stun_server'] = os.getenv('WEBRTC_STUN_SERVER')
        
        # 录制配置
        if os.getenv('RECORDING_STORAGE_PATH'):
            env_config['recording_path'] = os.getenv('RECORDING_STORAGE_PATH')
        
        if os.getenv('RECORDING_MAX_DURATION'):
            env_config['recording_max_duration'] = int(os.getenv('RECORDING_MAX_DURATION'))
        
        # AI服务配置
        if os.getenv('AI_SERVICE_ENDPOINT'):
            env_config['ai_endpoint'] = os.getenv('AI_SERVICE_ENDPOINT')
        
        if os.getenv('AI_SERVICE_API_KEY'):
            env_config['ai_api_key'] = os.getenv('AI_SERVICE_API_KEY')
        
        # 安全配置
        if os.getenv('MEETING_ENCRYPTION_KEY'):
            env_config['encryption_key'] = os.getenv('MEETING_ENCRYPTION_KEY')
        
        if os.getenv('MEETING_SESSION_TIMEOUT'):
            env_config['session_timeout'] = int(os.getenv('MEETING_SESSION_TIMEOUT'))
        
        # 第三方服务配置
        if os.getenv('JITSI_MEET_DOMAIN'):
            env_config['jitsi_domain'] = os.getenv('JITSI_MEET_DOMAIN')
        
        if os.getenv('AGORA_APP_ID'):
            env_config['agora_app_id'] = os.getenv('AGORA_APP_ID')
        
        return env_config
    
    async def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置数据"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 验证数值范围
            if 'max_meeting_duration' in config_data:
                duration = config_data['max_meeting_duration']
                if not isinstance(duration, int) or duration < 15 or duration > 480:
                    validation_result['errors'].append(
                        'max_meeting_duration必须是15-480之间的整数（分钟）'
                    )
            
            if 'max_participants_per_meeting' in config_data:
                participants = config_data['max_participants_per_meeting']
                if not isinstance(participants, int) or participants < 2 or participants > 1000:
                    validation_result['errors'].append(
                        'max_participants_per_meeting必须是2-1000之间的整数'
                    )
            
            # 验证WebRTC配置
            if 'webrtc_servers' in config_data:
                webrtc_config = config_data['webrtc_servers']
                if not isinstance(webrtc_config, dict):
                    validation_result['errors'].append('webrtc_servers必须是字典类型')
                else:
                    if 'stun_servers' not in webrtc_config:
                        validation_result['warnings'].append('建议配置STUN服务器')
                    
                    if 'turn_servers' not in webrtc_config:
                        validation_result['warnings'].append('建议配置TURN服务器以支持NAT穿透')
            
            # 验证布尔值配置
            boolean_configs = ['recording_enabled', 'auto_transcription', 'ai_analysis_enabled']
            for key in boolean_configs:
                if key in config_data and not isinstance(config_data[key], bool):
                    validation_result['errors'].append(f'{key}必须是布尔值')
            
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f'配置验证失败: {str(e)}')
        
        return validation_result
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_timestamp:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl
    
    def _clear_cache(self) -> None:
        """清除配置缓存"""
        self._config_cache = {}
        self._cache_timestamp = None
    
    def _get_config_description(self, key: str) -> str:
        """获取配置项描述"""
        descriptions = {
            'max_meeting_duration': '会议最大时长（分钟）',
            'max_participants_per_meeting': '单个会议最大参与者数量',
            'recording_enabled': '是否启用录制功能',
            'auto_transcription': '是否启用自动转录',
            'ai_analysis_enabled': '是否启用AI分析',
            'webrtc_servers': 'WebRTC服务器配置',
            'waiting_room_enabled': '是否默认启用等候室',
            'meeting_password_required': '是否要求设置会议密码',
            'data_retention_days': '数据保留天数',
            'max_recording_size': '录制文件最大大小（MB）'
        }
        
        return descriptions.get(key, f'会议配置项: {key}')
    
    def _get_default_config_value(self, key: str) -> Any:
        """获取默认配置值"""
        defaults = self._get_default_configs()
        return defaults.get(key)
    
    def _get_default_configs(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'max_meeting_duration': 120,  # 2小时
            'max_participants_per_meeting': 50,
            'recording_enabled': True,
            'auto_transcription': False,
            'ai_analysis_enabled': True,
            'waiting_room_enabled': False,
            'meeting_password_required': False,
            'data_retention_days': 90,
            'max_recording_size': 1024,  # 1GB
            'webrtc_servers': {
                'stun_servers': [
                    'stun:stun.l.google.com:19302',
                    'stun:stun1.l.google.com:19302'
                ],
                'turn_servers': []
            },
            'recording_formats': ['mp4', 'webm'],
            'supported_languages': ['zh-CN', 'en-US'],
            'ai_service_timeout': 30,  # 秒
            'session_timeout': 3600,  # 1小时
            'max_file_upload_size': 100,  # MB
            'allowed_file_types': ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'jpg', 'png']
        }
    
    async def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        try:
            # 删除所有会议配置
            from sqlalchemy import delete
            
            delete_query = delete(Config).where(Config.category == 'meeting')
            await self.db_session.execute(delete_query)
            
            # 添加默认配置
            default_configs = self._get_default_configs()
            for key, value in default_configs.items():
                config = Config(
                    category='meeting',
                    key=key,
                    value=value,
                    description=self._get_config_description(key),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db_session.add(config)
            
            await self.db_session.flush()
            
            # 清除缓存
            self._clear_cache()
            
        except Exception as e:
            raise ConfigurationError(f"重置配置失败: {str(e)}")
    
    async def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        try:
            all_configs = await self.get_all_meeting_configs()
            
            export_data = {
                'export_time': datetime.now().isoformat(),
                'version': '1.0',
                'configs': all_configs
            }
            
            return export_data
            
        except Exception as e:
            raise ConfigurationError(f"配置导出失败: {str(e)}")
    
    async def import_config(self, import_data: Dict[str, Any]) -> None:
        """导入配置"""
        try:
            if 'configs' not in import_data:
                raise ValidationError('导入数据格式错误：缺少configs字段')
            
            configs = import_data['configs']
            
            # 验证配置
            validation_result = await self.validate_config(configs)
            if not validation_result['valid']:
                raise ValidationError(f"配置验证失败: {validation_result['errors']}")
            
            # 更新配置
            await self.update_meeting_config(configs)
            
        except Exception as e:
            raise ConfigurationError(f"配置导入失败: {str(e)}")
