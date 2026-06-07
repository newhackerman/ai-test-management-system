"""
录制服务配置

本模块定义录制服务的配置参数和默认值。
"""
import os
from typing import Dict, Any, List
from pathlib import Path


class RecordingConfig:
    """录制配置类"""
    
    # 存储配置
    STORAGE_BASE_PATH = os.getenv('RECORDING_STORAGE_PATH', './recordings')
    MAX_FILE_SIZE = int(os.getenv('MAX_RECORDING_SIZE', '5368709120'))  # 5GB
    USER_QUOTA = int(os.getenv('USER_RECORDING_QUOTA', '10737418240'))  # 10GB
    RETENTION_DAYS = int(os.getenv('RECORDING_RETENTION_DAYS', '90'))
    
    # 支持的格式
    SUPPORTED_FORMATS = ['MP4', 'WEBM', 'MP3', 'M4A']
    SUPPORTED_TYPES = ['FULL_MEETING', 'SCREEN_SHARE', 'AUDIO_ONLY', 'HIGHLIGHTS']
    QUALITY_LEVELS = ['low', 'medium', 'high']
    
    # FFmpeg配置
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
    FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')
    
    # 录制质量设置
    QUALITY_SETTINGS = {
        'low': {
            'video_crf': '28',
            'video_preset': 'fast',
            'audio_bitrate': '64k',
            'resolution': '720x480',
            'framerate': 15
        },
        'medium': {
            'video_crf': '23',
            'video_preset': 'medium',
            'audio_bitrate': '128k',
            'resolution': '1280x720',
            'framerate': 30
        },
        'high': {
            'video_crf': '18',
            'video_preset': 'slow',
            'audio_bitrate': '256k',
            'resolution': '1920x1080',
            'framerate': 30
        }
    }
    
    # 处理配置
    MAX_CONCURRENT_PROCESSING = int(os.getenv('MAX_CONCURRENT_RECORDING_PROCESSING', '3'))
    PROCESSING_TIMEOUT = int(os.getenv('RECORDING_PROCESSING_TIMEOUT', '3600'))  # 1小时
    
    # 转录配置
    TRANSCRIPTION_ENABLED = os.getenv('TRANSCRIPTION_ENABLED', 'true').lower() == 'true'
    TRANSCRIPTION_LANGUAGE = os.getenv('TRANSCRIPTION_LANGUAGE', 'zh-CN')
    
    # 缓存配置
    CACHE_EXPIRY = {
        'recording_status': 3600,      # 1小时
        'playback_token': 86400,       # 24小时
        'transcript': 2592000,         # 30天
        'statistics': 3600             # 1小时
    }
    
    # 通知配置
    NOTIFY_ON_COMPLETION = os.getenv('NOTIFY_RECORDING_COMPLETION', 'true').lower() == 'true'
    NOTIFY_ON_FAILURE = os.getenv('NOTIFY_RECORDING_FAILURE', 'true').lower() == 'true'
    
    # 安全配置
    PLAYBACK_TOKEN_EXPIRY = int(os.getenv('PLAYBACK_TOKEN_EXPIRY_HOURS', '24'))
    MAX_DOWNLOAD_ATTEMPTS = int(os.getenv('MAX_RECORDING_DOWNLOAD_ATTEMPTS', '5'))
    
    @classmethod
    def get_storage_path(cls, meeting_id: int, recording_id: int = None) -> Path:
        """获取存储路径"""
        base_path = Path(cls.STORAGE_BASE_PATH)
        meeting_path = base_path / str(meeting_id)
        
        if recording_id:
            return meeting_path / str(recording_id)
        return meeting_path
    
    @classmethod
    def get_quality_settings(cls, quality: str) -> Dict[str, Any]:
        """获取质量设置"""
        return cls.QUALITY_SETTINGS.get(quality, cls.QUALITY_SETTINGS['medium'])
    
    @classmethod
    def validate_format(cls, file_format: str) -> bool:
        """验证文件格式"""
        return file_format.upper() in cls.SUPPORTED_FORMATS
    
    @classmethod
    def validate_type(cls, recording_type: str) -> bool:
        """验证录制类型"""
        return recording_type.upper() in cls.SUPPORTED_TYPES
    
    @classmethod
    def validate_quality(cls, quality: str) -> bool:
        """验证质量级别"""
        return quality.lower() in cls.QUALITY_LEVELS
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'type': 'FULL_MEETING',
            'format': 'MP4',
            'quality': 'medium',
            'resolution': '1280x720',
            'framerate': 30,
            'audio_bitrate': '128k',
            'enable_transcription': cls.TRANSCRIPTION_ENABLED
        }


# 创建全局配置实例
recording_config = RecordingConfig()


# 导出配置类和实例
__all__ = ['RecordingConfig', 'recording_config']