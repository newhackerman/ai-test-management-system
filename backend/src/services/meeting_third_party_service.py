"""
会议第三方服务集成配置

本模块实现会议相关第三方服务的集成配置，包括：
- Jitsi Meet或Agora.io集成参数
- TURN/STUN服务器连接
- 对象存储服务（MinIO/S3）
- AI服务API密钥和限制
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict

from ..core.config import get_settings
from ..core.exceptions import ValidationError, ConfigurationError

logger = logging.getLogger(__name__)
settings = get_settings()


class ThirdPartyServiceType(Enum):
    """第三方服务类型"""
    JITSI_MEET = "jitsi_meet"
    AGORA = "agora"
    MINIO = "minio"
    AWS_S3 = "aws_s3"
    BAIDU_ASR = "baidu_asr"
    XFYUN_ASR = "xfyun_asr"
    ALIYUN_ASR = "aliyun_asr"


@dataclass
class JitsiMeetConfig:
    """Jitsi Meet配置"""
    url: str
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    domain: Optional[str] = None
    room_prefix: str = "meeting_"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.url)


@dataclass
class AgoraConfig:
    """Agora.io配置"""
    app_id: str
    app_certificate: Optional[str] = None
    channel_prefix: str = "meeting_"
    token_expire_seconds: int = 3600
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.app_id)


@dataclass
class MinIOConfig:
    """MinIO配置"""
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str
    secure: bool = False
    region: str = "us-east-1"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key)


@dataclass
class AWSS3Config:
    """AWS S3配置"""
    access_key_id: str
    secret_access_key: str
    region: str
    bucket_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.access_key_id and self.secret_access_key and self.bucket_name)


@dataclass
class BaiduASRConfig:
    """百度ASR配置"""
    app_id: str
    api_key: str
    secret_key: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.app_id and self.api_key and self.secret_key)


@dataclass
class XFYunASRConfig:
    """科大讯飞ASR配置"""
    app_id: str
    api_key: str
    api_secret: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.app_id and self.api_key and self.api_secret)


@dataclass
class AliyunASRConfig:
    """阿里云ASR配置"""
    access_key_id: str
    access_key_secret: str
    region: str = "cn-shanghai"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_configured(self) -> bool:
        return bool(self.access_key_id and self.access_key_secret)


class MeetingThirdPartyService:
    """会议第三方服务集成配置"""
    
    def __init__(self):
        self._configs_cache: Dict[str, Any] = {}
    
    def get_jitsi_meet_config(self) -> JitsiMeetConfig:
        """获取Jitsi Meet配置"""
        return JitsiMeetConfig(
            url=os.getenv('JITSI_MEET_URL', 'https://meet.jit.si'),
            app_id=os.getenv('JITSI_APP_ID'),
            app_secret=os.getenv('JITSI_APP_SECRET'),
            domain=os.getenv('JITSI_DOMAIN'),
            room_prefix=os.getenv('JITSI_ROOM_PREFIX', 'meeting_')
        )
    
    def get_agora_config(self) -> AgoraConfig:
        """获取Agora.io配置"""
        app_id = os.getenv('AGORA_APP_ID', '')
        if not app_id:
            raise ConfigurationError("Agora App ID未配置")
        
        return AgoraConfig(
            app_id=app_id,
            app_certificate=os.getenv('AGORA_APP_CERTIFICATE'),
            channel_prefix=os.getenv('AGORA_CHANNEL_PREFIX', 'meeting_'),
            token_expire_seconds=int(os.getenv('AGORA_TOKEN_EXPIRE_SECONDS', '3600'))
        )
    
    def get_minio_config(self) -> MinIOConfig:
        """获取MinIO配置"""
        endpoint = os.getenv('MINIO_ENDPOINT', '')
        if not endpoint:
            raise ConfigurationError("MinIO endpoint未配置")
        
        return MinIOConfig(
            endpoint=endpoint,
            access_key=os.getenv('MINIO_ACCESS_KEY', ''),
            secret_key=os.getenv('MINIO_SECRET_KEY', ''),
            bucket_name=os.getenv('MINIO_BUCKET_NAME', 'meeting-recordings'),
            secure=os.getenv('MINIO_SECURE', 'false').lower() == 'true',
            region=os.getenv('MINIO_REGION', 'us-east-1')
        )
    
    def get_aws_s3_config(self) -> AWSS3Config:
        """获取AWS S3配置"""
        access_key_id = os.getenv('AWS_ACCESS_KEY_ID', '')
        if not access_key_id:
            raise ConfigurationError("AWS Access Key ID未配置")
        
        return AWSS3Config(
            access_key_id=access_key_id,
            secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            region=os.getenv('AWS_REGION', 'us-east-1'),
            bucket_name=os.getenv('AWS_S3_BUCKET', 'meeting-recordings')
        )
    
    def get_baidu_asr_config(self) -> BaiduASRConfig:
        """获取百度ASR配置"""
        app_id = os.getenv('BAIDU_ASR_APP_ID', '')
        if not app_id:
            raise ConfigurationError("百度ASR App ID未配置")
        
        return BaiduASRConfig(
            app_id=app_id,
            api_key=os.getenv('BAIDU_ASR_API_KEY', ''),
            secret_key=os.getenv('BAIDU_ASR_SECRET_KEY', '')
        )
    
    def get_xfyun_asr_config(self) -> XFYunASRConfig:
        """获取科大讯飞ASR配置"""
        app_id = os.getenv('XFYUN_ASR_APP_ID', '')
        if not app_id:
            raise ConfigurationError("科大讯飞ASR App ID未配置")
        
        return XFYunASRConfig(
            app_id=app_id,
            api_key=os.getenv('XFYUN_ASR_API_KEY', ''),
            api_secret=os.getenv('XFYUN_ASR_API_SECRET', '')
        )
    
    def get_aliyun_asr_config(self) -> AliyunASRConfig:
        """获取阿里云ASR配置"""
        access_key_id = os.getenv('ALIYUN_ASR_ACCESS_KEY_ID', '')
        if not access_key_id:
            raise ConfigurationError("阿里云ASR Access Key ID未配置")
        
        return AliyunASRConfig(
            access_key_id=access_key_id,
            access_key_secret=os.getenv('ALIYUN_ASR_ACCESS_KEY_SECRET', ''),
            region=os.getenv('ALIYUN_ASR_REGION', 'cn-shanghai')
        )
    
    def get_webrtc_servers_config(self) -> Dict[str, Any]:
        """获取WebRTC服务器配置"""
        stun_servers = self._parse_server_list(
            os.getenv('WEBRTC_STUN_SERVERS', 'stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302')
        )
        
        turn_servers = self._parse_turn_servers(
            os.getenv('WEBRTC_TURN_SERVERS', '')
        )
        
        return {
            'ice_servers': [
                {'urls': stun_servers},
                *turn_servers
            ]
        }
    
    def get_active_media_server_config(self) -> Dict[str, Any]:
        """获取当前激活的媒体服务器配置"""
        media_server_type = os.getenv('MEDIA_SERVER_TYPE', 'jitsi').lower()
        
        if media_server_type == 'jitsi':
            jitsi_config = self.get_jitsi_meet_config()
            if jitsi_config.is_configured():
                return {
                    'type': 'jitsi',
                    'config': jitsi_config.to_dict()
                }
        elif media_server_type == 'agora':
            try:
                agora_config = self.get_agora_config()
                if agora_config.is_configured():
                    return {
                        'type': 'agora',
                        'config': agora_config.to_dict()
                    }
            except ConfigurationError:
                pass
        
        # 默认返回Jitsi配置
        return {
            'type': 'jitsi',
            'config': self.get_jitsi_meet_config().to_dict()
        }
    
    def get_active_storage_config(self) -> Dict[str, Any]:
        """获取当前激活的存储配置"""
        storage_type = os.getenv('RECORDING_STORAGE_TYPE', 'local').lower()
        
        if storage_type == 'minio':
            try:
                minio_config = self.get_minio_config()
                if minio_config.is_configured():
                    return {
                        'type': 'minio',
                        'config': minio_config.to_dict()
                    }
            except ConfigurationError:
                pass
        elif storage_type == 's3':
            try:
                s3_config = self.get_aws_s3_config()
                if s3_config.is_configured():
                    return {
                        'type': 's3',
                        'config': s3_config.to_dict()
                    }
            except ConfigurationError:
                pass
        
        # 默认返回本地存储
        return {
            'type': 'local',
            'config': {
                'storage_path': os.getenv('RECORDING_STORAGE_PATH', 'recordings')
            }
        }
    
    def get_active_asr_config(self) -> Dict[str, Any]:
        """获取当前激活的ASR配置"""
        asr_service_type = os.getenv('ASR_SERVICE_TYPE', 'baidu').lower()
        
        if asr_service_type == 'baidu':
            try:
                baidu_config = self.get_baidu_asr_config()
                if baidu_config.is_configured():
                    return {
                        'type': 'baidu',
                        'config': baidu_config.to_dict()
                    }
            except ConfigurationError:
                pass
        elif asr_service_type == 'xfyun':
            try:
                xfyun_config = self.get_xfyun_asr_config()
                if xfyun_config.is_configured():
                    return {
                        'type': 'xfyun',
                        'config': xfyun_config.to_dict()
                    }
            except ConfigurationError:
                pass
        elif asr_service_type == 'aliyun':
            try:
                aliyun_config = self.get_aliyun_asr_config()
                if aliyun_config.is_configured():
                    return {
                        'type': 'aliyun',
                        'config': aliyun_config.to_dict()
                    }
            except ConfigurationError:
                pass
        
        # 如果没有配置ASR服务，返回空配置
        return {
            'type': 'none',
            'config': {},
            'message': '未配置ASR服务'
        }
    
    def validate_all_configurations(self) -> Dict[str, Any]:
        """验证所有第三方服务配置"""
        validation_result = {
            'valid': True,
            'services': {},
            'errors': [],
            'warnings': []
        }
        
        # 验证媒体服务器配置
        try:
            media_config = self.get_active_media_server_config()
            validation_result['services']['media_server'] = {
                'status': 'configured',
                'type': media_config['type'],
                'details': media_config['config']
            }
        except Exception as e:
            validation_result['services']['media_server'] = {
                'status': 'error',
                'error': str(e)
            }
            validation_result['errors'].append(f"媒体服务器配置错误: {str(e)}")
            validation_result['valid'] = False
        
        # 验证存储配置
        try:
            storage_config = self.get_active_storage_config()
            validation_result['services']['storage'] = {
                'status': 'configured',
                'type': storage_config['type'],
                'details': storage_config['config']
            }
        except Exception as e:
            validation_result['services']['storage'] = {
                'status': 'error',
                'error': str(e)
            }
            validation_result['errors'].append(f"存储配置错误: {str(e)}")
            validation_result['valid'] = False
        
        # 验证ASR配置
        try:
            asr_config = self.get_active_asr_config()
            if asr_config['type'] == 'none':
                validation_result['services']['asr'] = {
                    'status': 'not_configured',
                    'message': asr_config['message']
                }
                validation_result['warnings'].append("未配置ASR服务，语音转录功能不可用")
            else:
                validation_result['services']['asr'] = {
                    'status': 'configured',
                    'type': asr_config['type'],
                    'details': asr_config['config']
                }
        except Exception as e:
            validation_result['services']['asr'] = {
                'status': 'error',
                'error': str(e)
            }
            validation_result['warnings'].append(f"ASR配置警告: {str(e)}")
        
        # 验证WebRTC服务器配置
        try:
            webrtc_config = self.get_webrtc_servers_config()
            validation_result['services']['webrtc'] = {
                'status': 'configured',
                'details': webrtc_config
            }
        except Exception as e:
            validation_result['services']['webrtc'] = {
                'status': 'error',
                'error': str(e)
            }
            validation_result['errors'].append(f"WebRTC配置错误: {str(e)}")
            validation_result['valid'] = False
        
        return validation_result
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """获取服务健康状态"""
        health_status = {
            'overall_status': 'healthy',
            'services': {},
            'timestamp': str(datetime.utcnow())
        }
        
        # 检查各个服务的配置状态
        validation_result = self.validate_all_configurations()
        
        for service_name, service_info in validation_result['services'].items():
            if service_info['status'] == 'error':
                health_status['services'][service_name] = 'unhealthy'
                health_status['overall_status'] = 'degraded'
            elif service_info['status'] == 'not_configured':
                health_status['services'][service_name] = 'not_available'
            else:
                health_status['services'][service_name] = 'healthy'
        
        if validation_result['errors']:
            health_status['overall_status'] = 'unhealthy'
        
        return health_status
    
    # 私有辅助方法
    
    def _parse_server_list(self, servers_str: str) -> List[str]:
        """解析服务器列表"""
        if not servers_str:
            return []
        return [server.strip() for server in servers_str.split(',') if server.strip()]
    
    def _parse_turn_servers(self, turn_str: str) -> List[Dict[str, str]]:
        """解析TURN服务器配置"""
        if not turn_str:
            return []
        
        turn_servers = []
        for server_config in turn_str.split(';'):
            if not server_config.strip():
                continue
            
            parts = server_config.strip().split(',')
            if len(parts) >= 3:
                turn_servers.append({
                    'urls': parts[0].strip(),
                    'username': parts[1].strip(),
                    'credential': parts[2].strip()
                })
        
        return turn_servers