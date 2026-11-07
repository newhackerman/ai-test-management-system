"""
会议录制服务

本模块实现会议录制的核心业务逻辑，包括：
- 录制启动功能
- 录制进程管理
- 录制停止功能
- 录制文件后处理
- 音频转录功能
- 录制文件存储管理
- 录制回放服务
- 录制权限管理
"""
import asyncio
import logging
import os
import json
import uuid
import signal
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, update, delete
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from ..core.database import AsyncSessionLocal, get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.meeting import (
    Meeting, MeetingRecording, RecordingType, RecordingStatus, FileFormat,
    MeetingParticipant, ParticipantRole, MeetingStatus
)
from ..models.user import User
from ..services.permission_service import PermissionService
from ..services.user import UserService
from ..services.meeting_notification_service import MeetingNotificationService
from ..utils.file_storage_utils import FileStorageUtils
from ..utils.redis_client import RedisClient
from ..utils.recording_utils import media_processor, recording_validator, storage_manager
from ..config.recording_config import recording_config

logger = logging.getLogger(__name__)


class RecordingProcess:
    """录制进程管理类"""
    
    def __init__(self, recording_id: int, meeting_id: int, config: Dict[str, Any]):
        self.recording_id = recording_id
        self.meeting_id = meeting_id
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.status = "INITIALIZING"
        self.start_time = datetime.utcnow()
        self.output_file = None
        
    async def start(self) -> bool:
        """启动录制进程"""
        try:
            # 创建输出文件路径
            output_dir = Path(f"recordings/{self.meeting_id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.output_file = output_dir / f"recording_{self.recording_id}_{int(self.start_time.timestamp())}.mp4"
            
            # 构建FFmpeg命令
            cmd = self._build_ffmpeg_command()
            
            # 启动录制进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.status = "RECORDING"
            logger.info(f"Recording process started for recording {self.recording_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording process: {e}")
            self.status = "FAILED"
            return False
    
    async def stop(self) -> bool:
        """停止录制进程"""
        try:
            if self.process and self.process.poll() is None:
                # 发送SIGTERM信号优雅停止
                self.process.terminate()
                
                # 等待进程结束，最多等待10秒
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.process.kill()
                    self.process.wait()
                
                self.status = "STOPPED"
                logger.info(f"Recording process stopped for recording {self.recording_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to stop recording process: {e}")
            self.status = "FAILED"
            return False

    async def pause(self) -> bool:
        """暂停采集进程：SIGSTOP 冻结 ffmpeg，输出文件保持打开，恢复时继续写入同一文件。"""
        try:
            if self.process and self.process.poll() is None:
                self.process.send_signal(signal.SIGSTOP)
                self.status = "PAUSED"
                logger.info(f"Recording process paused for recording {self.recording_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause recording process: {e}")
            return False

    async def resume(self) -> bool:
        """恢复采集进程：SIGCONT 解冻 ffmpeg。"""
        try:
            if self.process and self.process.poll() is None:
                self.process.send_signal(signal.SIGCONT)
                self.status = "RECORDING"
                logger.info(f"Recording process resumed for recording {self.recording_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume recording process: {e}")
            return False
    
    def _build_ffmpeg_command(self) -> List[str]:
        """构建FFmpeg录制命令"""
        recording_type = self.config.get('recording_type', 'FULL_MEETING')
        quality = self.config.get('quality', 'standard')
        
        # 基础命令
        cmd = ['ffmpeg', '-y']  # -y 覆盖输出文件
        
        if recording_type == 'FULL_MEETING':
            # 录制完整会议（音频+视频）
            cmd.extend([
                '-f', 'pulse',  # 音频输入
                '-i', 'default',
                '-f', 'x11grab',  # 视频输入（屏幕录制）
                '-s', '1920x1080',
                '-r', '30',
                '-i', ':0.0'
            ])
        elif recording_type == 'SCREEN_SHARE':
            # 仅录制屏幕共享
            cmd.extend([
                '-f', 'x11grab',
                '-s', '1920x1080',
                '-r', '30',
                '-i', ':0.0'
            ])
        elif recording_type == 'AUDIO_ONLY':
            # 仅录制音频
            cmd.extend([
                '-f', 'pulse',
                '-i', 'default'
            ])
        
        # 编码设置
        if quality == 'high':
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '18'])
        elif quality == 'low':
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '28'])
        else:  # standard
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'])
        
        # 音频编码
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        
        # 输出文件
        cmd.append(str(self.output_file))
        
        return cmd
    
    def get_status(self) -> Dict[str, Any]:
        """获取录制状态"""
        return {
            'recording_id': self.recording_id,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'output_file': str(self.output_file) if self.output_file else None,
            'process_id': self.process.pid if self.process else None
        }


class RecordingService:
    """会议录制核心服务"""
    
    def __init__(self, db: AsyncSession, redis_client: Optional[RedisClient] = None):
        self.db = db
        self.redis_client = redis_client or RedisClient()
        self.permission_service = PermissionService(db)
        self.user_service = UserService(db)
        self.notification_service = MeetingNotificationService(db)
        self.file_storage = FileStorageUtils()
        
        # 活跃录制进程管理
        self.active_recordings: Dict[int, RecordingProcess] = {}

    async def _notify_best_effort(self, method_name: str, *args) -> None:
        """录制通知是尽力而为的：MeetingNotificationService 目前没有
        notify_recording_* 系列方法，缺失时只记日志，不让通知失败
        拖垮录制的状态流转。"""
        method = getattr(self.notification_service, method_name, None)
        if method is None:
            logger.warning(f"跳过录制通知：{method_name} 未实现")
            return
        try:
            await method(*args)
        except Exception as e:
            logger.warning(f"录制通知 {method_name} 失败（已忽略）: {e}")
        
        # 存储配置
        self.storage_config = {
            'base_path': recording_config.STORAGE_BASE_PATH,
            'max_file_size': recording_config.MAX_FILE_SIZE,
            'allowed_formats': recording_config.SUPPORTED_FORMATS,
            'retention_days': recording_config.RETENTION_DAYS
        }
    
    async def start_recording(
        self, 
        meeting_id: int, 
        recording_config: Dict[str, Any], 
        user_id: int
    ) -> MeetingRecording:
        """
        启动录制功能
        
        Args:
            meeting_id: 会议ID
            recording_config: 录制配置
            user_id: 用户ID
            
        Returns:
            MeetingRecording: 录制记录
            
        Raises:
            PermissionError: 权限不足
            ValidationError: 配置无效
            RuntimeError: 录制启动失败
        """
        try:
            # 1. 验证权限
            await self._check_recording_permission(meeting_id, user_id)
            
            # 2. 验证会议状态
            meeting = await self._get_meeting(meeting_id)
            # 注意：MeetingStatus 是普通 PyEnum（非 str 枚举），成员与
            # 字符串永远不相等；此前这里写 'IN_PROGRESS' 导致任何会议
            # 都无法开始录制（第 14 项补用例时发现的真缺陷）。
            if meeting.status != MeetingStatus.IN_PROGRESS:
                raise ValidationError("只能在进行中的会议中开始录制")
            
            # 3. 检查是否已有录制
            existing_recording = await self._get_active_recording(meeting_id)
            if existing_recording:
                raise ValidationError("会议已在录制中")
            
            # 4. 验证录制配置
            validated_config = await self._validate_recording_config(recording_config)
            
            # 5. 检查存储空间配额
            await self._check_storage_quota(user_id)
            
            # 6. 生成录制名称
            recording_name = validated_config.get('name') or f"Meeting_{meeting_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 7. 创建录制记录
            recording = MeetingRecording(
                meeting_id=meeting_id,
                recording_name=recording_name,
                recording_type=RecordingType(validated_config.get('type', 'FULL_MEETING')),
                file_format=FileFormat(validated_config.get('format', 'MP4')),
                file_path='',  # 进程启动成功后回填 output_file（见下）
                recording_status=RecordingStatus.RECORDING,
                start_time=datetime.utcnow(),
                created_by=user_id,
                updated_by=user_id
            )
            
            # 8. 保存录制记录
            self.db.add(recording)
            await self.db.commit()
            await self.db.refresh(recording)
            
            # 9. 启动录制进程
            recording_process = RecordingProcess(recording.id, meeting_id, validated_config)
            success = await recording_process.start()
            
            if not success:
                # 录制启动失败，更新状态
                recording.recording_status = RecordingStatus.FAILED
                await self.db.commit()
                raise RuntimeError("录制进程启动失败")
            
            # 10. 存储活跃录制信息
            self.active_recordings[recording.id] = recording_process

            # 10b. 持久化输出文件路径：此前 file_path 恒为 ''，停止后的后处理
            # 永远报 "Recording file not found: "；回填后库里指向预期的输出路径
            #（无头环境下 ffmpeg 因无 X11/PulseAudio 仍建不出文件，后处理仍会
            # 失败，但报错会带出真实路径而非空串）。
            if recording_process.output_file is not None:
                recording.file_path = str(recording_process.output_file)
                await self.db.commit()
                # commit 后属性过期，需 refresh，否则路由层 from_orm 取值会
                # 抛 MissingGreenlet（与 pause/resume 的同类修复一致）。
                await self.db.refresh(recording)
            
            # 11. 缓存录制状态
            await self._cache_recording_status(recording.id, recording_process.get_status())
            
            # 12. 通知参与者录制开始
            await self._notify_best_effort("notify_recording_started", meeting_id, recording)
            
            logger.info(f"Recording started successfully: {recording.id}")
            return recording
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            await self.db.rollback()
            raise
    
    async def stop_recording(self, recording_id: int, user_id: int) -> MeetingRecording:
        """
        停止录制功能
        
        Args:
            recording_id: 录制ID
            user_id: 用户ID
            
        Returns:
            MeetingRecording: 更新后的录制记录
            
        Raises:
            NotFoundError: 录制不存在
            PermissionError: 权限不足
        """
        try:
            # 1. 获取录制记录
            recording = await self._get_recording(recording_id)
            
            # 2. 验证权限
            await self._check_stop_permission(recording, user_id)
            
            # 3. 检查录制状态
            if recording.recording_status != RecordingStatus.RECORDING:
                raise ValidationError("录制未在进行中")
            
            # 4. 停止录制进程
            if recording_id in self.active_recordings:
                recording_process = self.active_recordings[recording_id]
                success = await recording_process.stop()
                
                if success:
                    # 更新文件路径
                    recording.file_path = str(recording_process.output_file)
                
                # 移除活跃录制
                del self.active_recordings[recording_id]
            
            # 5. 更新录制状态
            recording.recording_status = RecordingStatus.PROCESSING
            recording.end_time = datetime.utcnow()
            recording.duration_seconds = int((recording.end_time - recording.start_time).total_seconds())
            recording.updated_by = user_id
            
            # 6. 保存录制记录
            await self.db.commit()
            
            # 7. 启动后处理任务
            await self._start_post_processing(recording)
            
            # 8. 通知参与者录制结束
            await self._notify_best_effort("notify_recording_stopped", recording.meeting_id, recording)
            
            logger.info(f"Recording stopped successfully: {recording_id}")
            return recording
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            await self.db.rollback()
            raise
    
    async def pause_recording(self, recording_id: int, user_id: int) -> MeetingRecording:
        """暂停录制：仅 RECORDING -> PAUSED；与停止用同一权限（创建者/组织者/主持人）。

        若采集进程在本后端进程内存中（active_recordings），SIGSTOP 冻结 ffmpeg；
        若进程不在内存中（如后端重启后），仅翻转数据库状态并记日志——此时
        底层采集实际仍在跑，调用方应以返回的状态为准，不保证已冻结。
        """
        try:
            recording = await self._get_recording(recording_id)
            await self._check_stop_permission(recording, user_id)
            if recording.recording_status != RecordingStatus.RECORDING:
                raise ValidationError("只有进行中的录制可以暂停")
            if recording_id in self.active_recordings:
                await self.active_recordings[recording_id].pause()
            else:
                logger.warning(f"暂停录制 {recording_id}：采集进程不在本进程内存中，仅更新状态")
            recording.recording_status = RecordingStatus.PAUSED
            recording.updated_by = user_id
            await self.db.commit()
            # commit 后属性过期：立即 refresh，否则路由层 from_orm 同步读属性会报 MissingGreenlet
            await self.db.refresh(recording)
            logger.info(f"Recording paused successfully: {recording_id}")
            return recording
        except Exception as e:
            logger.error(f"Failed to pause recording: {e}")
            await self.db.rollback()
            raise

    async def resume_recording(self, recording_id: int, user_id: int) -> MeetingRecording:
        """恢复录制：仅 PAUSED -> RECORDING；权限与暂停相同。"""
        try:
            recording = await self._get_recording(recording_id)
            await self._check_stop_permission(recording, user_id)
            if recording.recording_status != RecordingStatus.PAUSED:
                raise ValidationError("只有已暂停的录制可以恢复")
            if recording_id in self.active_recordings:
                await self.active_recordings[recording_id].resume()
            else:
                logger.warning(f"恢复录制 {recording_id}：采集进程不在本进程内存中，仅更新状态")
            recording.recording_status = RecordingStatus.RECORDING
            recording.updated_by = user_id
            await self.db.commit()
            # 同上：commit 后 refresh，避免 from_orm 触发过期属性懒加载
            await self.db.refresh(recording)
            logger.info(f"Recording resumed successfully: {recording_id}")
            return recording
        except Exception as e:
            logger.error(f"Failed to resume recording: {e}")
            await self.db.rollback()
            raise

    async def process_recording(self, recording_id: int):
        """
        处理录制文件
        
        Args:
            recording_id: 录制ID
        """
        try:
            # 1. 获取录制记录
            recording = await self._get_recording(recording_id)
            
            if recording.recording_status != RecordingStatus.PROCESSING:
                logger.warning(f"Recording {recording_id} is not in processing status")
                return
            
            # 2. 更新处理进度
            await self._update_processing_progress(recording_id, 10)
            
            # 3. 验证录制文件
            if not os.path.exists(recording.file_path):
                raise FileNotFoundError(f"Recording file not found: {recording.file_path}")
            
            # 4. 视频转码和压缩
            processed_file = await self._process_video_file(recording)
            await self._update_processing_progress(recording_id, 40)
            
            # 5. 生成缩略图
            thumbnail_path = await self._generate_thumbnail(processed_file)
            await self._update_processing_progress(recording_id, 60)
            
            # 6. 提取音频进行转录
            transcript_data = None
            if recording.recording_type in [RecordingType.FULL_MEETING, RecordingType.AUDIO_ONLY]:
                transcript_data = await self._transcribe_audio(processed_file)
                await self._save_transcript(recording_id, transcript_data)
            await self._update_processing_progress(recording_id, 80)
            
            # 7. 上传到存储服务
            final_file_path = await self._upload_to_storage(processed_file, recording)
            await self._update_processing_progress(recording_id, 90)
            
            # 8. 更新录制信息
            recording.file_path = final_file_path
            recording.file_size = os.path.getsize(processed_file)
            recording.recording_status = RecordingStatus.COMPLETED
            recording.processing_progress = 100
            
            # 9. 生成分辨率信息
            if recording.recording_type in [RecordingType.FULL_MEETING, RecordingType.SCREEN_SHARE]:
                recording.resolution = await self._get_video_resolution(processed_file)
            
            await self.db.commit()
            await self._update_processing_progress(recording_id, 100)
            
            # 10. 清理临时文件
            await self._cleanup_temp_files(recording_id)
            
            # 11. 发送完成通知
            await self._notify_best_effort("notify_recording_completed", recording.meeting_id, recording)
            
            logger.info(f"Recording processing completed: {recording_id}")
            
        except Exception as e:
            logger.error(f"Failed to process recording {recording_id}: {e}")
            
            # 更新为失败状态
            try:
                recording = await self._get_recording(recording_id)
                recording.recording_status = RecordingStatus.FAILED
                await self.db.commit()
                
                await self._notify_best_effort("notify_recording_failed", recording.meeting_id, recording, str(e))
            except Exception as update_error:
                logger.error(f"Failed to update recording status: {update_error}")   
 
    async def get_recording_playback_info(
        self, 
        recording_id: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        获取录制回放信息
        
        Args:
            recording_id: 录制ID
            user_id: 用户ID
            
        Returns:
            Dict: 回放信息
            
        Raises:
            NotFoundError: 录制不存在
            PermissionError: 权限不足
        """
        try:
            # 1. 获取录制记录
            recording = await self._get_recording(recording_id)
            
            # 2. 检查访问权限
            await self._check_playback_permission(recording, user_id)
            
            # 3. 检查录制状态
            if recording.recording_status != RecordingStatus.COMPLETED:
                raise ValidationError("录制尚未完成处理")
            
            # 4. 生成播放令牌
            playback_token = await self._generate_playback_token(recording_id, user_id)
            
            # 5. 获取字幕信息
            subtitles = await self._get_subtitles(recording_id)
            
            # 6. 获取章节信息
            chapters = await self._get_chapters(recording_id)
            
            # 7. 构建播放配置
            playback_config = {
                'video_url': recording.file_path,
                'duration': recording.duration_seconds,
                'resolution': recording.resolution,
                'format': recording.file_format.value,
                'subtitles': subtitles,
                'chapters': chapters,
                'thumbnail': await self._get_thumbnail_url(recording_id)
            }
            
            # 8. 更新观看统计
            recording.view_count += 1
            await self.db.commit()
            
            # 9. 记录观看日志
            await self._log_playback_access(recording_id, user_id)
            
            return {
                'recording_id': recording_id,
                'playback_token': playback_token,
                'playback_config': playback_config,
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get playback info: {e}")
            raise
    
    async def delete_recording(self, recording_id: int, user_id: int) -> bool:
        """
        删除录制
        
        Args:
            recording_id: 录制ID
            user_id: 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 1. 获取录制记录
            recording = await self._get_recording(recording_id)
            
            # 2. 验证删除权限
            await self._check_delete_permission(recording, user_id)
            
            # 3. 停止正在进行的录制
            if recording.recording_status == RecordingStatus.RECORDING:
                await self.stop_recording(recording_id, user_id)
            
            # 4. 删除存储文件
            await self._delete_storage_files(recording)
            
            # 5. 更新数据库状态
            recording.recording_status = RecordingStatus.DELETED
            recording.updated_by = user_id
            await self.db.commit()
            
            # 6. 清理缓存
            await self._clear_recording_cache(recording_id)
            
            logger.info(f"Recording deleted successfully: {recording_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete recording: {e}")
            return False
    
    async def get_recording_list(
        self, 
        meeting_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[RecordingStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[MeetingRecording], int]:
        """
        获取录制列表
        
        Args:
            meeting_id: 会议ID（可选）
            user_id: 用户ID（可选）
            status: 录制状态（可选）
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            Tuple[List[MeetingRecording], int]: 录制列表和总数
        """
        try:
            # 构建查询条件
            conditions = []
            
            if meeting_id:
                conditions.append(MeetingRecording.meeting_id == meeting_id)
            
            if user_id:
                conditions.append(MeetingRecording.created_by == user_id)
            
            if status:
                conditions.append(MeetingRecording.recording_status == status)
            
            # 排除已删除的录制
            conditions.append(MeetingRecording.recording_status != RecordingStatus.DELETED)
            
            # 查询总数
            count_query = select(func.count(MeetingRecording.id)).where(and_(*conditions))
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # 查询列表
            query = (
                select(MeetingRecording)
                .where(and_(*conditions))
                .order_by(desc(MeetingRecording.created_at))
                .limit(limit)
                .offset(offset)
            )
            
            result = await self.db.execute(query)
            recordings = result.scalars().all()
            
            return recordings, total
            
        except Exception as e:
            logger.error(f"Failed to get recording list: {e}")
            raise

    async def get_recordings(
        self,
        meeting_id: int,
        query_params: Any,
        user_id: int
    ) -> Tuple[List[MeetingRecording], int, Dict[str, Any]]:
        """
        获取会议的录制列表（带分页、过滤和统计）。

        Args:
            meeting_id: 会议ID
            query_params: 录制查询参数（RecordingQueryParams）
            user_id: 当前用户ID

        Returns:
            Tuple[List[MeetingRecording], int, Dict]: 录制列表、总数、统计信息

        Raises:
            NotFoundError: 会议不存在
        """
        # 验证会议存在（不存在时抛出 NotFoundError，由路由层转为 404）
        await self._get_meeting(meeting_id)

        conditions = [MeetingRecording.meeting_id == meeting_id]

        if not getattr(query_params, 'include_deleted', False):
            conditions.append(MeetingRecording.recording_status != RecordingStatus.DELETED)

        recording_type = getattr(query_params, 'recording_type', None)
        if recording_type is not None:
            conditions.append(MeetingRecording.recording_type == recording_type)

        status_filter = getattr(query_params, 'status', None)
        if status_filter is not None:
            conditions.append(MeetingRecording.recording_status == status_filter)

        file_format = getattr(query_params, 'file_format', None)
        if file_format is not None:
            conditions.append(MeetingRecording.file_format == file_format)

        start_date = getattr(query_params, 'start_date', None)
        if start_date:
            conditions.append(MeetingRecording.start_time >= start_date)

        end_date = getattr(query_params, 'end_date', None)
        if end_date:
            conditions.append(MeetingRecording.start_time <= end_date)

        keyword = getattr(query_params, 'keyword', None)
        if keyword:
            conditions.append(MeetingRecording.recording_name.ilike(f"%{keyword}%"))

        # 查询总数
        count_query = select(func.count(MeetingRecording.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序
        sort_by = getattr(query_params, 'sort_by', 'start_time') or 'start_time'
        sort_order = getattr(query_params, 'sort_order', 'desc') or 'desc'
        sort_column = getattr(MeetingRecording, sort_by, MeetingRecording.start_time)
        order_clause = asc(sort_column) if sort_order == 'asc' else desc(sort_column)

        page = getattr(query_params, 'page', 1) or 1
        page_size = getattr(query_params, 'page_size', 20) or 20
        offset = (page - 1) * page_size

        query = (
            select(MeetingRecording)
            .where(and_(*conditions))
            .order_by(order_clause)
            .limit(page_size)
            .offset(offset)
        )
        result = await self.db.execute(query)
        recordings = result.scalars().all()

        # 统计信息
        total_size = sum((r.file_size or 0) for r in recordings)
        total_duration = sum((r.duration_seconds or 0) for r in recordings)
        statistics = {
            'total_size_mb': total_size / (1024 * 1024) if total_size else 0,
            'total_duration_minutes': total_duration / 60 if total_duration else 0,
        }

        return recordings, total, statistics

    async def get_recording_by_id(
        self,
        recording_id: int,
        user_id: int
    ) -> Optional[MeetingRecording]:
        """
        根据ID获取录制详情（不存在时返回 None，由路由层转为 404）。

        Args:
            recording_id: 录制ID
            user_id: 当前用户ID

        Returns:
            Optional[MeetingRecording]: 录制记录，不存在时返回 None
        """
        try:
            query = select(MeetingRecording).where(MeetingRecording.id == recording_id)
            result = await self.db.execute(query)
            recording = result.scalar_one_or_none()
        except Exception as e:
            # 录制表未创建或数据库不可用时，视为录制不存在，由路由层转为 404，
            # 避免将底层异常透出为 500。
            logger.warning(f"查询录制 {recording_id} 失败，视为不存在: {e}")
            return None

        if not recording:
            return None

        # 已删除的录制视为不存在
        if recording.recording_status == RecordingStatus.DELETED:
            return None

        return recording

    async def get_recording_statistics(
        self,
        meeting_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取录制统计信息。

        返回与 RecordingStatistics 模型匹配的统计字典。
        """
        conditions = [MeetingRecording.recording_status != RecordingStatus.DELETED]

        if meeting_id:
            conditions.append(MeetingRecording.meeting_id == meeting_id)
        if user_id:
            conditions.append(MeetingRecording.created_by == user_id)
        if start_date:
            conditions.append(MeetingRecording.start_time >= start_date)
        if end_date:
            conditions.append(MeetingRecording.start_time <= end_date)

        filter_clause = and_(*conditions)

        # 总数
        total_result = await self.db.execute(
            select(func.count(MeetingRecording.id)).where(filter_clause)
        )
        total_recordings = total_result.scalar() or 0

        # 按状态统计
        async def _count_for_status(status: RecordingStatus) -> int:
            res = await self.db.execute(
                select(func.count(MeetingRecording.id)).where(
                    and_(filter_clause, MeetingRecording.recording_status == status)
                )
            )
            return res.scalar() or 0

        active_recordings = await _count_for_status(RecordingStatus.RECORDING)
        completed_recordings = await _count_for_status(RecordingStatus.COMPLETED)
        failed_recordings = await _count_for_status(RecordingStatus.FAILED)

        # 总时长与总大小
        agg_result = await self.db.execute(
            select(
                func.coalesce(func.sum(MeetingRecording.duration_seconds), 0),
                func.coalesce(func.sum(MeetingRecording.file_size), 0),
            ).where(filter_clause)
        )
        total_duration_seconds, total_file_size = agg_result.one()

        # 按类型统计
        by_type_result = await self.db.execute(
            select(
                MeetingRecording.recording_type,
                func.count(MeetingRecording.id),
            )
            .where(filter_clause)
            .group_by(MeetingRecording.recording_type)
        )
        by_type = {
            (rt.value if rt else 'UNKNOWN'): cnt
            for rt, cnt in by_type_result.all()
        }

        # 按格式统计
        by_format_result = await self.db.execute(
            select(
                MeetingRecording.file_format,
                func.count(MeetingRecording.id),
            )
            .where(filter_clause)
            .group_by(MeetingRecording.file_format)
        )
        by_format = {
            (ff.value if ff else 'UNKNOWN'): cnt
            for ff, cnt in by_format_result.all()
        }

        return {
            'total_recordings': total_recordings,
            'active_recordings': active_recordings,
            'completed_recordings': completed_recordings,
            'failed_recordings': failed_recordings,
            'total_duration_minutes': int(total_duration_seconds / 60) if total_duration_seconds else 0,
            'total_file_size_mb': (total_file_size / (1024 * 1024)) if total_file_size else 0.0,
            'by_type': by_type,
            'by_format': by_format,
        }

    # 私有方法实现
    
    async def _check_recording_permission(self, meeting_id: int, user_id: int) -> bool:
        """检查录制权限"""
        # 1. 检查用户是否是会议参与者
        participant_query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(participant_query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise PermissionError("用户不是会议参与者")
        
        # 2. 检查录制权限
        if not participant.can_record and participant.participant_role not in [
            ParticipantRole.ORGANIZER, 
            ParticipantRole.MODERATOR
        ]:
            raise PermissionError("用户无录制权限")
        
        return True
    
    async def _get_meeting(self, meeting_id: int) -> Meeting:
        """获取会议信息"""
        query = select(Meeting).where(Meeting.id == meeting_id)
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")
        
        return meeting
    
    async def _get_recording(self, recording_id: int) -> MeetingRecording:
        """获取录制记录（录制表不存在或查询失败时抛出 NotFoundError，由路由层转为 404）。"""
        try:
            query = select(MeetingRecording).where(MeetingRecording.id == recording_id)
            result = await self.db.execute(query)
            recording = result.scalar_one_or_none()
        except Exception as e:
            # 录制表未创建或数据库不可用时，视为录制不存在，避免透出为 500。
            logger.warning(f"查询录制 {recording_id} 失败，视为不存在: {e}")
            raise NotFoundError(f"录制不存在: {recording_id}")

        if not recording:
            raise NotFoundError(f"录制不存在: {recording_id}")
        
        return recording
    
    async def _get_active_recording(self, meeting_id: int) -> Optional[MeetingRecording]:
        """获取活跃的录制"""
        query = select(MeetingRecording).where(
            and_(
                MeetingRecording.meeting_id == meeting_id,
                MeetingRecording.recording_status == RecordingStatus.RECORDING
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_recording_config(self, config) -> Dict[str, Any]:
        """验证录制配置

        归一化（第 14 项补用例时发现的真缺陷）：路由传进来的是
        StartRecordingRequest（Pydantic 模型），不是 dict——此前
        直接调 config.get() 导致开始录制恒 500。先转 dict，再把
        请求字段名映射为校验器要的键（recording_name→name、
        recording_type→type、file_format→format）；quality 的
        'standard'（请求模型的默认值）映射为校验器的 'medium'。
        """
        if hasattr(config, "model_dump"):
            config = config.model_dump(mode="json")
        if not isinstance(config, dict):
            config = dict(config)
        config = {
            "type": config.get("type", config.get("recording_type", "FULL_MEETING")),
            "format": config.get("format", config.get("file_format", "MP4")),
            "quality": {"standard": "medium"}.get(
                config.get("quality", "medium"), config.get("quality", "medium")
            ),
            "name": config.get("name", config.get("recording_name", "")),
            "resolution": config.get("resolution", "1280x720"),
            "framerate": config.get("framerate", 30),
        }
        # 使用录制验证器
        is_valid, errors = recording_validator.validate_recording_config(config)
        
        if not is_valid:
            raise ValidationError(f"录制配置无效: {', '.join(errors)}")
        
        # 返回验证后的配置
        validated_config = {
            'type': config.get('type', 'FULL_MEETING'),
            'format': config.get('format', 'MP4'),
            'quality': config.get('quality', 'medium'),
            'name': config.get('name', ''),
            'resolution': config.get('resolution', '1280x720'),
            'framerate': config.get('framerate', 30)
        }
        
        return validated_config
    
    async def _check_storage_quota(self, user_id: int) -> bool:
        """检查存储空间配额"""
        # 查询用户已使用的存储空间
        query = select(func.sum(MeetingRecording.file_size)).where(
            and_(
                MeetingRecording.created_by == user_id,
                MeetingRecording.recording_status != RecordingStatus.DELETED
            )
        )
        result = await self.db.execute(query)
        used_space = result.scalar() or 0
        
        # 检查是否超过配额
        max_quota = recording_config.USER_QUOTA
        
        if used_space >= max_quota:
            raise ValidationError("存储空间配额不足")
        
        return True
    
    async def _check_stop_permission(self, recording: MeetingRecording, user_id: int) -> bool:
        """检查停止录制权限"""
        # 录制创建者可以停止
        if recording.created_by == user_id:
            return True
        
        # 会议组织者和主持人可以停止
        participant_query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == recording.meeting_id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.participant_role.in_([
                    ParticipantRole.ORGANIZER,
                    ParticipantRole.MODERATOR
                ])
            )
        )
        result = await self.db.execute(participant_query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise PermissionError("无权限停止录制")
        
        return True
    
    async def _check_playback_permission(self, recording: MeetingRecording, user_id: int) -> bool:
        """检查回放权限"""
        # 公开录制任何人都可以观看
        if recording.is_public:
            return True
        
        # 检查用户是否是会议参与者
        participant_query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == recording.meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(participant_query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise PermissionError("无权限观看录制")
        
        return True
    
    async def _check_delete_permission(self, recording: MeetingRecording, user_id: int) -> bool:
        """检查删除权限"""
        # 录制创建者可以删除
        if recording.created_by == user_id:
            return True
        
        # 会议组织者可以删除
        meeting_query = select(Meeting).where(Meeting.id == recording.meeting_id)
        result = await self.db.execute(meeting_query)
        meeting = result.scalar_one_or_none()
        
        if meeting and meeting.organizer_id == user_id:
            return True
        
        raise PermissionError("无权限删除录制")
    
    async def _start_post_processing(self, recording: MeetingRecording):
        """启动后处理任务（独立会话）。

        后处理必须用自己的会话：此前直接 create_task(self.process_recording(...))
        与请求共享 self.db，会在请求结束时与 get_async_session 的 session.close()
        并发使用同一条 MySQL 连接，触发 asyncmy 2014 'Command Out of Sync'，
        close() 抛错 → "Exception in ASGI application" → uvicorn 关闭该 keep-alive
        连接，客户端下一次复用该连接的请求直接失败（RemoteProtocolError/ReadTimeout）。
        """
        asyncio.create_task(self._run_post_processing_in_new_session(recording.id))

    async def _run_post_processing_in_new_session(self, recording_id: int):
        """以后处理专用会话执行 process_recording，与请求会话完全隔离。"""
        if AsyncSessionLocal is None:
            logger.error("AsyncSessionLocal 未初始化，跳过录制后处理")
            return
        async with AsyncSessionLocal() as session:
            service = RecordingService(session)
            await service.process_recording(recording_id)
    
    async def _process_video_file(self, recording: MeetingRecording) -> str:
        """处理视频文件"""
        input_file = recording.file_path
        output_file = input_file.replace('.mp4', '_processed.mp4')
        
        # 使用FFmpeg进行视频处理
        cmd = [
            'ffmpeg', '-i', input_file,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-y', output_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg processing failed: {stderr.decode()}")
            raise RuntimeError("视频处理失败")
        
        return output_file
    
    async def _generate_thumbnail(self, video_file: str) -> str:
        """生成视频缩略图"""
        thumbnail_file = video_file.replace('.mp4', '_thumbnail.jpg')
        
        cmd = [
            'ffmpeg', '-i', video_file,
            '-ss', '00:00:10',  # 从第10秒截取
            '-vframes', '1',
            '-y', thumbnail_file
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(thumbnail_file):
            return thumbnail_file
        
        return ""
    
    async def _transcribe_audio(self, video_file: str) -> Optional[Dict[str, Any]]:
        """转录音频"""
        try:
            # 提取音频
            audio_file = video_file.replace('.mp4', '.wav')
            
            cmd = [
                'ffmpeg', '-i', video_file,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                '-y', audio_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode != 0 or not os.path.exists(audio_file):
                logger.error("Failed to extract audio for transcription")
                return None
            
            # 这里应该集成实际的语音识别服务
            # 暂时返回模拟数据
            transcript_data = {
                'text': '这是一个模拟的转录文本',
                'segments': [
                    {
                        'start': 0.0,
                        'end': 5.0,
                        'text': '这是一个模拟的转录文本',
                        'speaker': 'Speaker 1'
                    }
                ],
                'language': 'zh-CN',
                'confidence': 0.95
            }
            
            # 清理临时音频文件
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            return None
    
    async def _save_transcript(self, recording_id: int, transcript_data: Dict[str, Any]):
        """保存转录数据"""
        if not transcript_data:
            return
        
        # 将转录数据保存到Redis或数据库
        cache_key = f"recording_transcript:{recording_id}"
        await self.redis_client.set(cache_key, json.dumps(transcript_data), ex=86400 * 30)  # 30天过期
    
    async def _upload_to_storage(self, file_path: str, recording: MeetingRecording) -> str:
        """上传到存储服务"""
        # 这里应该集成实际的对象存储服务（如MinIO、S3等）
        # 暂时返回本地路径
        storage_path = f"recordings/{recording.meeting_id}/{recording.id}_{recording.recording_name}.{recording.file_format.value.lower()}"
        
        # 创建存储目录
        storage_dir = os.path.dirname(storage_path)
        os.makedirs(storage_dir, exist_ok=True)
        
        # 移动文件到最终位置
        final_path = os.path.join(self.storage_config['base_path'], storage_path)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        
        if os.path.exists(file_path):
            os.rename(file_path, final_path)
        
        return final_path
    
    async def _get_video_resolution(self, video_file: str) -> str:
        """获取视频分辨率"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                video_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        width = stream.get('width')
                        height = stream.get('height')
                        if width and height:
                            return f"{width}x{height}"
            
            return "1920x1080"  # 默认分辨率
            
        except Exception as e:
            logger.error(f"Failed to get video resolution: {e}")
            return "1920x1080"
    
    async def _generate_playback_token(self, recording_id: int, user_id: int) -> str:
        """生成播放令牌"""
        token_data = {
            'recording_id': recording_id,
            'user_id': user_id,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).timestamp()
        }
        
        token = str(uuid.uuid4())
        cache_key = f"playback_token:{token}"
        
        await self.redis_client.set(cache_key, json.dumps(token_data), ex=86400)  # 24小时过期
        
        return token
    
    async def _get_subtitles(self, recording_id: int) -> List[Dict[str, Any]]:
        """获取字幕信息"""
        cache_key = f"recording_transcript:{recording_id}"
        transcript_data = await self.redis_client.get(cache_key)
        
        if transcript_data:
            data = json.loads(transcript_data)
            return data.get('segments', [])
        
        return []
    
    async def _get_chapters(self, recording_id: int) -> List[Dict[str, Any]]:
        """获取章节信息"""
        # 这里可以基于会议议程或AI分析生成章节
        # 暂时返回空列表
        return []
    
    async def _get_thumbnail_url(self, recording_id: int) -> str:
        """获取缩略图URL"""
        # 返回缩略图的访问URL
        return f"/api/v1/recordings/{recording_id}/thumbnail"
    
    async def _update_processing_progress(self, recording_id: int, progress: int):
        """更新处理进度"""
        cache_key = f"recording_progress:{recording_id}"
        await self.redis_client.set(cache_key, str(progress), ex=3600)  # 1小时过期
        
        # 也可以更新数据库
        query = (
            update(MeetingRecording)
            .where(MeetingRecording.id == recording_id)
            .values(processing_progress=progress)
        )
        await self.db.execute(query)
        await self.db.commit()
    
    async def _cleanup_temp_files(self, recording_id: int):
        """清理临时文件"""
        # 清理处理过程中产生的临时文件
        temp_patterns = [
            f"*recording_{recording_id}_*",
            f"*{recording_id}_processed*",
            f"*{recording_id}_thumbnail*"
        ]
        
        temp_dir = tempfile.gettempdir()
        for pattern in temp_patterns:
            for file_path in Path(temp_dir).glob(pattern):
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    async def _delete_storage_files(self, recording: MeetingRecording):
        """删除存储文件"""
        try:
            if recording.file_path and os.path.exists(recording.file_path):
                os.remove(recording.file_path)
            
            # 删除相关的缩略图等文件
            base_path = recording.file_path.rsplit('.', 1)[0] if recording.file_path else ""
            related_files = [
                f"{base_path}_thumbnail.jpg",
                f"{base_path}_processed.mp4"
            ]
            
            for file_path in related_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            logger.error(f"Failed to delete storage files: {e}")
    
    async def _cache_recording_status(self, recording_id: int, status_data: Dict[str, Any]):
        """缓存录制状态"""
        cache_key = f"recording_status:{recording_id}"
        await self.redis_client.set(cache_key, json.dumps(status_data), ex=3600)
    
    async def _clear_recording_cache(self, recording_id: int):
        """清理录制缓存"""
        cache_keys = [
            f"recording_status:{recording_id}",
            f"recording_progress:{recording_id}",
            f"recording_transcript:{recording_id}"
        ]
        
        for key in cache_keys:
            await self.redis_client.delete(key)
    
    async def _log_playback_access(self, recording_id: int, user_id: int):
        """记录播放访问日志"""
        log_data = {
            'recording_id': recording_id,
            'user_id': user_id,
            'access_time': datetime.utcnow().isoformat(),
            'ip_address': '',  # 可以从请求中获取
            'user_agent': ''   # 可以从请求中获取
        }
        
        # 记录到日志系统或数据库
        logger.info(f"Recording playback access: {json.dumps(log_data)}")


# 导出服务类
__all__ = ['RecordingService', 'RecordingProcess']
def get_recording_service(db: AsyncSession = Depends(get_async_session)) -> RecordingService:
    """
    获取录制服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        RecordingService: 录制服务实例
    """
    return RecordingService(db)