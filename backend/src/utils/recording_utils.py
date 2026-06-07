"""
录制工具函数

本模块提供录制相关的工具函数，包括：
- 视频处理工具
- 音频处理工具
- 文件格式转换
- 媒体信息提取
- 录制配置验证
"""
import os
import json
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

import logging

logger = logging.getLogger(__name__)


class MediaProcessor:
    """媒体处理工具类"""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffmpeg(self) -> str:
        """查找FFmpeg可执行文件"""
        # 尝试常见的FFmpeg路径
        possible_paths = [
            'ffmpeg',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        logger.warning("FFmpeg not found, using default 'ffmpeg'")
        return 'ffmpeg'
    
    def _find_ffprobe(self) -> str:
        """查找FFprobe可执行文件"""
        # 尝试常见的FFprobe路径
        possible_paths = [
            'ffprobe',
            '/usr/bin/ffprobe',
            '/usr/local/bin/ffprobe',
            'C:\\ffmpeg\\bin\\ffprobe.exe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        logger.warning("FFprobe not found, using default 'ffprobe'")
        return 'ffprobe'
    
    async def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """获取媒体文件信息"""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return json.loads(stdout.decode())
            else:
                logger.error(f"FFprobe failed: {stderr.decode()}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get media info: {e}")
            return {}
    
    async def extract_audio(self, video_file: str, output_file: str, 
                          sample_rate: int = 16000, channels: int = 1) -> bool:
        """从视频中提取音频"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_file,
                '-vn',  # 不包含视频
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                '-y', output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                logger.error(f"Audio extraction failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            return False
    
    async def generate_thumbnail(self, video_file: str, output_file: str, 
                               timestamp: str = "00:00:10") -> bool:
        """生成视频缩略图"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_file,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',  # 高质量
                '-y', output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_file):
                return True
            else:
                logger.error(f"Thumbnail generation failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return False
    
    async def compress_video(self, input_file: str, output_file: str, 
                           quality: str = "medium") -> bool:
        """压缩视频文件"""
        try:
            # 根据质量设置参数
            quality_settings = {
                "low": {"crf": "28", "preset": "fast"},
                "medium": {"crf": "23", "preset": "medium"},
                "high": {"crf": "18", "preset": "slow"}
            }
            
            settings = quality_settings.get(quality, quality_settings["medium"])
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-c:v', 'libx264',
                '-preset', settings["preset"],
                '-crf', settings["crf"],
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',  # 优化网络播放
                '-y', output_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                logger.error(f"Video compression failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to compress video: {e}")
            return False
    
    async def convert_format(self, input_file: str, output_file: str, 
                           target_format: str) -> bool:
        """转换文件格式"""
        try:
            cmd = [self.ffmpeg_path, '-i', input_file]
            
            # 根据目标格式设置参数
            if target_format.upper() == 'MP4':
                cmd.extend(['-c:v', 'libx264', '-c:a', 'aac'])
            elif target_format.upper() == 'WEBM':
                cmd.extend(['-c:v', 'libvpx-vp9', '-c:a', 'libvorbis'])
            elif target_format.upper() == 'MP3':
                cmd.extend(['-vn', '-c:a', 'libmp3lame'])
            elif target_format.upper() == 'M4A':
                cmd.extend(['-vn', '-c:a', 'aac'])
            
            cmd.extend(['-y', output_file])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                logger.error(f"Format conversion failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to convert format: {e}")
            return False


class RecordingValidator:
    """录制配置验证器"""
    
    SUPPORTED_FORMATS = ['MP4', 'WEBM', 'MP3', 'M4A']
    SUPPORTED_TYPES = ['FULL_MEETING', 'SCREEN_SHARE', 'AUDIO_ONLY', 'HIGHLIGHTS']
    QUALITY_LEVELS = ['low', 'medium', 'high']
    
    @classmethod
    def validate_recording_config(cls, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证录制配置"""
        errors = []
        
        # 验证录制类型
        recording_type = config.get('type', 'FULL_MEETING')
        if recording_type not in cls.SUPPORTED_TYPES:
            errors.append(f"不支持的录制类型: {recording_type}")
        
        # 验证文件格式
        file_format = config.get('format', 'MP4')
        if file_format not in cls.SUPPORTED_FORMATS:
            errors.append(f"不支持的文件格式: {file_format}")
        
        # 验证质量设置
        quality = config.get('quality', 'medium')
        if quality not in cls.QUALITY_LEVELS:
            errors.append(f"无效的质量设置: {quality}")
        
        # 验证录制名称
        name = config.get('name', '')
        if name and len(name) > 200:
            errors.append("录制名称过长（最大200字符）")
        
        # 验证分辨率设置
        resolution = config.get('resolution')
        if resolution and not cls._validate_resolution(resolution):
            errors.append(f"无效的分辨率设置: {resolution}")
        
        # 验证帧率设置
        framerate = config.get('framerate')
        if framerate and not cls._validate_framerate(framerate):
            errors.append(f"无效的帧率设置: {framerate}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_resolution(cls, resolution: str) -> bool:
        """验证分辨率格式"""
        try:
            if 'x' not in resolution:
                return False
            
            width, height = resolution.split('x')
            width, height = int(width), int(height)
            
            # 检查分辨率范围
            if width < 320 or width > 3840 or height < 240 or height > 2160:
                return False
            
            return True
        except (ValueError, AttributeError):
            return False
    
    @classmethod
    def _validate_framerate(cls, framerate: int) -> bool:
        """验证帧率"""
        return isinstance(framerate, int) and 1 <= framerate <= 60


class StorageManager:
    """存储管理器"""
    
    def __init__(self, base_path: str = "./recordings"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_recording_path(self, meeting_id: int, recording_id: int, 
                          filename: str) -> Path:
        """获取录制文件路径"""
        meeting_dir = self.base_path / str(meeting_id)
        meeting_dir.mkdir(parents=True, exist_ok=True)
        return meeting_dir / f"{recording_id}_{filename}"
    
    def get_temp_path(self, recording_id: int, suffix: str = "") -> Path:
        """获取临时文件路径"""
        temp_dir = Path(tempfile.gettempdir()) / "recordings"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir / f"temp_{recording_id}_{suffix}"
    
    def calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to calculate directory size: {e}")
        
        return total_size
    
    def cleanup_old_files(self, days: int = 90) -> int:
        """清理旧文件"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        try:
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
        
        return cleaned_count


class RecordingMetrics:
    """录制指标收集器"""
    
    @staticmethod
    def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
        """计算压缩比"""
        if original_size == 0:
            return 0.0
        return (original_size - compressed_size) / original_size
    
    @staticmethod
    def estimate_processing_time(file_size: int, file_duration: int) -> int:
        """估算处理时间（秒）"""
        # 基于文件大小和时长的简单估算
        # 实际应该基于历史数据进行机器学习预测
        base_time = file_duration * 0.1  # 基础处理时间为视频时长的10%
        size_factor = file_size / (1024 * 1024 * 100)  # 每100MB增加额外时间
        return int(base_time + size_factor * 30)
    
    @staticmethod
    def calculate_quality_score(resolution: str, bitrate: int, framerate: int) -> float:
        """计算质量评分"""
        try:
            width, height = map(int, resolution.split('x'))
            pixel_count = width * height
            
            # 基于分辨率、码率和帧率的质量评分
            resolution_score = min(pixel_count / (1920 * 1080), 1.0)
            bitrate_score = min(bitrate / 5000, 1.0)  # 5Mbps为满分
            framerate_score = min(framerate / 30, 1.0)  # 30fps为满分
            
            return (resolution_score + bitrate_score + framerate_score) / 3
        except Exception:
            return 0.5  # 默认中等质量


# 创建全局实例
media_processor = MediaProcessor()
recording_validator = RecordingValidator()
storage_manager = StorageManager()
recording_metrics = RecordingMetrics()


# 导出工具类和实例
__all__ = [
    'MediaProcessor',
    'RecordingValidator', 
    'StorageManager',
    'RecordingMetrics',
    'media_processor',
    'recording_validator',
    'storage_manager',
    'recording_metrics'
]