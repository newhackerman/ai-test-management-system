"""
测试执行监控和日志管理服务
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, AsyncGenerator
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..models.test_case import TestExecution, TestCase, ExecutionStatus
from ..models.test_plan import TestPlan
from ..models.user import User
from ..utils.redis_client import RedisClient
from ..utils.file_storage_utils import FileStorageUtils
from .notification_service import NotificationService
from ..core.exceptions import ValidationError, NotFoundError, PermissionError


class ExecutionLogLevel:
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExecutionMonitoringService:
    """测试执行监控和日志管理服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: RedisClient,
        file_storage: FileStorageUtils,
        notification_service: NotificationService
    ):
        self.db = db
        self.redis = redis_client
        self.file_storage = file_storage
        self.notification_service = notification_service
        self.log_retention_days = 30  # 日志保留天数
        self.monitoring_interval = 5  # 监控间隔（秒）
    
    # 实时监控
    async def start_execution_monitoring(self, execution_id: int) -> str:
        """开始执行监控"""
        # 1. 验证执行记录存在
        execution = await self._get_execution_by_id(execution_id)
        
        # 2. 生成监控会话ID
        monitor_session_id = str(uuid.uuid4())
        
        # 3. 初始化监控数据
        monitor_data = {
            "execution_id": execution_id,
            "session_id": monitor_session_id,
            "status": "ACTIVE",
            "started_at": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "metrics": {
                "cpu_usage": 0,
                "memory_usage": 0,
                "network_io": 0,
                "disk_io": 0
            },
            "alerts": []
        }
        
        # 4. 保存监控会话
        await self.redis.hset(f"execution_monitor:{execution_id}", mapping={
            "session_id": monitor_session_id,
            "data": json.dumps(monitor_data)
        })
        
        # 5. 启动监控任务
        asyncio.create_task(self._monitor_execution_task(execution_id, monitor_session_id))
        
        return monitor_session_id
    
    async def stop_execution_monitoring(self, execution_id: int, session_id: str) -> bool:
        """停止执行监控"""
        # 1. 获取监控会话
        monitor_key = f"execution_monitor:{execution_id}"
        session_data = await self.redis.hget(monitor_key, "session_id")
        
        if not session_data or session_data.decode() != session_id:
            raise ValidationError("监控会话不存在或已过期")
        
        # 2. 更新监控状态
        monitor_data_str = await self.redis.hget(monitor_key, "data")
        if monitor_data_str:
            monitor_data = json.loads(monitor_data_str)
            monitor_data["status"] = "STOPPED"
            monitor_data["stopped_at"] = datetime.utcnow().isoformat()
            
            await self.redis.hset(monitor_key, "data", json.dumps(monitor_data))
        
        # 3. 设置过期时间
        await self.redis.expire(monitor_key, 3600)  # 1小时后清理
        
        return True
    
    async def get_execution_monitoring_data(self, execution_id: int) -> Dict[str, Any]:
        """获取执行监控数据"""
        # 1. 获取监控数据
        monitor_key = f"execution_monitor:{execution_id}"
        monitor_data_str = await self.redis.hget(monitor_key, "data")
        
        if not monitor_data_str:
            raise NotFoundError("监控数据不存在")
        
        monitor_data = json.loads(monitor_data_str)
        
        # 2. 获取实时指标
        metrics = await self._get_real_time_metrics(execution_id)
        monitor_data["metrics"].update(metrics)
        
        # 3. 获取最近的日志
        recent_logs = await self.get_execution_logs(
            execution_id, 
            limit=50, 
            level=ExecutionLogLevel.INFO
        )
        monitor_data["recent_logs"] = recent_logs
        
        # 4. 获取告警信息
        alerts = await self._get_execution_alerts(execution_id)
        monitor_data["alerts"] = alerts
        
        return monitor_data
    
    async def get_execution_progress_stream(self, execution_id: int) -> AsyncGenerator[Dict[str, Any], None]:
        """获取执行进度流"""
        monitor_key = f"execution_monitor:{execution_id}"
        
        while True:
            try:
                # 获取监控数据
                monitor_data_str = await self.redis.hget(monitor_key, "data")
                if not monitor_data_str:
                    break
                
                monitor_data = json.loads(monitor_data_str)
                
                # 如果监控已停止，退出
                if monitor_data.get("status") == "STOPPED":
                    yield monitor_data
                    break
                
                # 获取执行进度
                execution = await self._get_execution_by_id(execution_id)
                progress_data = {
                    "execution_id": execution_id,
                    "status": execution.execution_status.value,
                    "progress": await self._calculate_execution_progress(execution),
                    "metrics": monitor_data.get("metrics", {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                yield progress_data
                
                # 等待下次更新
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                yield {
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                break
    
    # 日志管理
    async def log_execution_event(
        self,
        execution_id: int,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> str:
        """记录执行事件日志"""
        # 1. 生成日志ID
        log_id = str(uuid.uuid4())
        
        # 2. 构建日志记录
        log_entry = {
            "log_id": log_id,
            "execution_id": execution_id,
            "level": level,
            "message": message,
            "details": details or {},
            "source": source or "system",
            "timestamp": datetime.utcnow().isoformat(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else None
        }
        
        # 3. 保存到Redis（实时日志）
        log_key = f"execution_logs:{execution_id}"
        await self.redis.lpush(log_key, json.dumps(log_entry))
        
        # 4. 设置日志过期时间
        await self.redis.expire(log_key, 86400 * self.log_retention_days)
        
        # 5. 如果是错误或关键日志，触发告警
        if level in [ExecutionLogLevel.ERROR, ExecutionLogLevel.CRITICAL]:
            await self._trigger_execution_alert(execution_id, level, message, details)
        
        # 6. 异步保存到文件（持久化）
        asyncio.create_task(self._save_log_to_file(execution_id, log_entry))
        
        return log_id
    
    async def get_execution_logs(
        self,
        execution_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取执行日志"""
        # 1. 从Redis获取实时日志
        log_key = f"execution_logs:{execution_id}"
        log_entries = await self.redis.lrange(log_key, offset, offset + limit - 1)
        
        logs = []
        for entry in log_entries:
            try:
                log_data = json.loads(entry)
                
                # 应用过滤条件
                if level and log_data.get("level") != level:
                    continue
                
                if source and log_data.get("source") != source:
                    continue
                
                if start_time:
                    log_time = datetime.fromisoformat(log_data.get("timestamp"))
                    if log_time < start_time:
                        continue
                
                if end_time:
                    log_time = datetime.fromisoformat(log_data.get("timestamp"))
                    if log_time > end_time:
                        continue
                
                logs.append(log_data)
                
            except (json.JSONDecodeError, ValueError):
                continue
        
        # 2. 如果Redis中的日志不够，从文件中补充
        if len(logs) < limit:
            file_logs = await self._get_logs_from_file(
                execution_id, start_time, end_time, level, source, 
                limit - len(logs), offset
            )
            logs.extend(file_logs)
        
        return logs
    
    async def search_execution_logs(
        self,
        execution_id: int,
        search_query: str,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """搜索执行日志"""
        # 1. 获取所有日志
        all_logs = await self.get_execution_logs(execution_id, level=level, limit=1000)
        
        # 2. 执行搜索
        search_results = []
        search_query_lower = search_query.lower()
        
        for log in all_logs:
            # 在消息中搜索
            if search_query_lower in log.get("message", "").lower():
                search_results.append(log)
                continue
            
            # 在详细信息中搜索
            details = log.get("details", {})
            if isinstance(details, dict):
                details_str = json.dumps(details).lower()
                if search_query_lower in details_str:
                    search_results.append(log)
                    continue
            
            # 达到限制数量
            if len(search_results) >= limit:
                break
        
        return search_results[:limit]
    
    async def export_execution_logs(
        self,
        execution_id: int,
        format_type: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """导出执行日志"""
        # 1. 获取所有日志
        logs = await self.get_execution_logs(
            execution_id, start_time, end_time, limit=10000
        )
        
        # 2. 根据格式导出
        if format_type.lower() == "json":
            export_data = {
                "execution_id": execution_id,
                "export_time": datetime.utcnow().isoformat(),
                "total_logs": len(logs),
                "logs": logs
            }
            content = json.dumps(export_data, indent=2, ensure_ascii=False)
            file_extension = "json"
            
        elif format_type.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入标题行
            writer.writerow(["Timestamp", "Level", "Source", "Message", "Details"])
            
            # 写入日志数据
            for log in logs:
                writer.writerow([
                    log.get("timestamp", ""),
                    log.get("level", ""),
                    log.get("source", ""),
                    log.get("message", ""),
                    json.dumps(log.get("details", {}))
                ])
            
            content = output.getvalue()
            file_extension = "csv"
            
        else:
            # 纯文本格式
            lines = []
            for log in logs:
                line = f"[{log.get('timestamp')}] {log.get('level')} - {log.get('message')}"
                if log.get("details"):
                    line += f" | Details: {json.dumps(log.get('details'))}"
                lines.append(line)
            
            content = "\n".join(lines)
            file_extension = "txt"
        
        # 3. 保存文件
        filename = f"execution_logs_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        file_path = await self.file_storage.save_file(
            content.encode("utf-8"),
            "execution_logs",
            filename
        )
        
        return file_path
    
    # 附件管理
    async def upload_execution_attachment(
        self,
        execution_id: int,
        attachment_type: str,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传执行附件"""
        # 1. 验证执行记录
        execution = await self._get_execution_by_id(execution_id)
        
        # 2. 生成附件ID
        attachment_id = str(uuid.uuid4())
        
        # 3. 保存文件
        file_path = await self.file_storage.save_file(
            file_data,
            f"test_executions/{execution_id}/{attachment_type}",
            f"{attachment_id}_{filename}"
        )
        
        # 4. 构建附件信息
        attachment_info = {
            "attachment_id": attachment_id,
            "execution_id": execution_id,
            "attachment_type": attachment_type,
            "filename": filename,
            "file_path": file_path,
            "file_size": len(file_data),
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        # 5. 更新执行记录的附件信息
        await self._update_execution_attachments(execution, attachment_type, attachment_info)
        
        # 6. 记录日志
        await self.log_execution_event(
            execution_id,
            ExecutionLogLevel.INFO,
            f"上传{attachment_type}附件: {filename}",
            {"attachment_id": attachment_id, "file_size": len(file_data)}
        )
        
        return attachment_info
    
    async def get_execution_attachments(
        self,
        execution_id: int,
        attachment_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取执行附件列表"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(execution_id)
        
        # 2. 收集附件信息
        attachments = []
        
        if not attachment_type or attachment_type == "screenshots":
            screenshots = execution.screenshots or []
            for screenshot in screenshots:
                if isinstance(screenshot, dict):
                    screenshot["attachment_type"] = "screenshots"
                    attachments.append(screenshot)
        
        if not attachment_type or attachment_type == "logs":
            logs = execution.logs or []
            for log in logs:
                if isinstance(log, dict):
                    log["attachment_type"] = "logs"
                    attachments.append(log)
        
        if not attachment_type or attachment_type == "videos":
            videos = execution.videos or []
            for video in videos:
                if isinstance(video, dict):
                    video["attachment_type"] = "videos"
                    attachments.append(video)
        
        return attachments
    
    async def delete_execution_attachment(
        self,
        execution_id: int,
        attachment_id: str
    ) -> bool:
        """删除执行附件"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(execution_id)
        
        # 2. 查找并删除附件
        attachment_found = False
        
        # 检查截图
        if execution.screenshots:
            execution.screenshots = [
                s for s in execution.screenshots 
                if s.get("attachment_id") != attachment_id
            ]
            if len(execution.screenshots) != len(execution.screenshots or []):
                attachment_found = True
        
        # 检查日志文件
        if execution.logs:
            execution.logs = [
                l for l in execution.logs 
                if l.get("attachment_id") != attachment_id
            ]
            if len(execution.logs) != len(execution.logs or []):
                attachment_found = True
        
        # 检查视频
        if execution.videos:
            execution.videos = [
                v for v in execution.videos 
                if v.get("attachment_id") != attachment_id
            ]
            if len(execution.videos) != len(execution.videos or []):
                attachment_found = True
        
        if not attachment_found:
            raise NotFoundError("附件不存在")
        
        # 3. 保存更改
        await self.db.commit()
        
        # 4. 记录日志
        await self.log_execution_event(
            execution_id,
            ExecutionLogLevel.INFO,
            f"删除附件: {attachment_id}"
        )
        
        return True
    
    # 异常检测
    async def detect_execution_anomalies(self, execution_id: int) -> List[Dict[str, Any]]:
        """检测执行异常"""
        anomalies = []
        
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(execution_id)
        
        # 2. 检查执行时间异常
        if execution.duration and execution.duration > 3600:  # 超过1小时
            anomalies.append({
                "type": "LONG_EXECUTION",
                "severity": "WARNING",
                "message": f"执行时间过长: {execution.duration}秒",
                "details": {"duration": execution.duration}
            })
        
        # 3. 检查内存使用异常
        metrics = await self._get_real_time_metrics(execution_id)
        if metrics.get("memory_usage", 0) > 80:  # 内存使用超过80%
            anomalies.append({
                "type": "HIGH_MEMORY_USAGE",
                "severity": "WARNING",
                "message": f"内存使用率过高: {metrics['memory_usage']}%",
                "details": {"memory_usage": metrics["memory_usage"]}
            })
        
        # 4. 检查错误日志频率
        error_logs = await self.get_execution_logs(
            execution_id, 
            level=ExecutionLogLevel.ERROR,
            start_time=datetime.utcnow() - timedelta(minutes=10),
            limit=50
        )
        
        if len(error_logs) > 10:  # 10分钟内超过10个错误
            anomalies.append({
                "type": "HIGH_ERROR_RATE",
                "severity": "ERROR",
                "message": f"错误日志频率过高: {len(error_logs)}个错误/10分钟",
                "details": {"error_count": len(error_logs)}
            })
        
        # 5. 检查执行状态异常
        if execution.execution_status == ExecutionStatus.IN_PROGRESS:
            # 检查是否长时间无更新
            last_log = await self.get_execution_logs(execution_id, limit=1)
            if last_log:
                last_update = datetime.fromisoformat(last_log[0]["timestamp"])
                if datetime.utcnow() - last_update > timedelta(minutes=30):
                    anomalies.append({
                        "type": "EXECUTION_STALLED",
                        "severity": "ERROR",
                        "message": "执行可能已停滞，长时间无更新",
                        "details": {"last_update": last_update.isoformat()}
                    })
        
        return anomalies
    
    # 私有方法
    async def _monitor_execution_task(self, execution_id: int, session_id: str):
        """监控执行任务"""
        monitor_key = f"execution_monitor:{execution_id}"
        
        while True:
            try:
                # 检查监控会话是否还活跃
                session_data = await self.redis.hget(monitor_key, "session_id")
                if not session_data or session_data.decode() != session_id:
                    break
                
                # 获取监控数据
                monitor_data_str = await self.redis.hget(monitor_key, "data")
                if not monitor_data_str:
                    break
                
                monitor_data = json.loads(monitor_data_str)
                if monitor_data.get("status") == "STOPPED":
                    break
                
                # 更新监控指标
                metrics = await self._get_real_time_metrics(execution_id)
                monitor_data["metrics"].update(metrics)
                monitor_data["last_update"] = datetime.utcnow().isoformat()
                
                # 检测异常
                anomalies = await self.detect_execution_anomalies(execution_id)
                if anomalies:
                    monitor_data["alerts"].extend(anomalies)
                
                # 保存更新的监控数据
                await self.redis.hset(monitor_key, "data", json.dumps(monitor_data))
                
                # 等待下次监控
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                # 记录监控错误
                await self.log_execution_event(
                    execution_id,
                    ExecutionLogLevel.ERROR,
                    f"监控任务异常: {str(e)}"
                )
                break
    
    async def _get_execution_by_id(self, execution_id: int) -> TestExecution:
        """根据ID获取执行记录"""
        execution = await self.db.get(TestExecution, execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        return execution
    
    async def _get_real_time_metrics(self, execution_id: int) -> Dict[str, Any]:
        """获取实时指标"""
        # TODO: 实现真实的系统指标收集
        # 这里返回模拟数据
        import random
        
        return {
            "cpu_usage": random.uniform(10, 80),
            "memory_usage": random.uniform(20, 70),
            "network_io": random.uniform(0, 100),
            "disk_io": random.uniform(0, 50),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _calculate_execution_progress(self, execution: TestExecution) -> Dict[str, Any]:
        """计算执行进度"""
        # 获取测试用例步骤信息
        test_case = await self.db.get(TestCase, execution.test_case_id)
        if not test_case or not test_case.test_steps:
            return {"percentage": 0, "current_step": 0, "total_steps": 0}
        
        total_steps = len(test_case.test_steps)
        
        # 从Redis获取步骤执行情况
        completed_steps = 0
        for i in range(total_steps):
            step_key = f"execution_step:{execution.id}:{i}"
            step_data = await self.redis.hgetall(step_key)
            if step_data:
                completed_steps += 1
        
        percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            "percentage": percentage,
            "current_step": completed_steps,
            "total_steps": total_steps,
            "status": execution.execution_status.value
        }
    
    async def _get_execution_alerts(self, execution_id: int) -> List[Dict[str, Any]]:
        """获取执行告警"""
        alert_key = f"execution_alerts:{execution_id}"
        alerts = await self.redis.lrange(alert_key, 0, -1)
        
        alert_list = []
        for alert in alerts:
            try:
                alert_data = json.loads(alert)
                alert_list.append(alert_data)
            except json.JSONDecodeError:
                continue
        
        return alert_list
    
    async def _trigger_execution_alert(
        self,
        execution_id: int,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """触发执行告警"""
        alert = {
            "alert_id": str(uuid.uuid4()),
            "execution_id": execution_id,
            "level": level,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 保存告警
        alert_key = f"execution_alerts:{execution_id}"
        await self.redis.lpush(alert_key, json.dumps(alert))
        await self.redis.expire(alert_key, 86400)  # 24小时过期
        
        # 发送通知
        await self.notification_service.send_execution_alert(alert)
    
    async def _save_log_to_file(self, execution_id: int, log_entry: Dict[str, Any]):
        """保存日志到文件"""
        try:
            # 按日期组织日志文件
            log_date = datetime.fromisoformat(log_entry["timestamp"]).strftime("%Y%m%d")
            log_filename = f"execution_{execution_id}_{log_date}.log"
            
            # 构建日志行
            log_line = f"[{log_entry['timestamp']}] {log_entry['level']} - {log_entry['message']}"
            if log_entry.get("details"):
                log_line += f" | {json.dumps(log_entry['details'])}"
            log_line += "\n"
            
            # 保存到文件
            await self.file_storage.append_to_file(
                log_line.encode("utf-8"),
                "execution_logs",
                log_filename
            )
            
        except Exception as e:
            # 记录保存失败，但不影响主流程
            print(f"保存日志到文件失败: {e}")
    
    async def _get_logs_from_file(
        self,
        execution_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """从文件获取日志"""
        # TODO: 实现从文件读取日志的逻辑
        # 这里返回空列表，实际实现需要解析日志文件
        return []
    
    async def _update_execution_attachments(
        self,
        execution: TestExecution,
        attachment_type: str,
        attachment_info: Dict[str, Any]
    ):
        """更新执行记录的附件信息"""
        if attachment_type == "screenshots":
            if not execution.screenshots:
                execution.screenshots = []
            execution.screenshots.append(attachment_info)
        
        elif attachment_type == "logs":
            if not execution.logs:
                execution.logs = []
            execution.logs.append(attachment_info)
        
        elif attachment_type == "videos":
            if not execution.videos:
                execution.videos = []
            execution.videos.append(attachment_info)
        
        await self.db.commit()
    
    # 清理方法
    async def cleanup_old_logs(self, days: int = None) -> int:
        """清理旧日志"""
        if days is None:
            days = self.log_retention_days
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleanup_count = 0
        
        # 清理Redis中的旧日志
        pattern = "execution_logs:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            # 获取日志条目
            logs = await self.redis.lrange(key, 0, -1)
            new_logs = []
            
            for log in logs:
                try:
                    log_data = json.loads(log)
                    log_time = datetime.fromisoformat(log_data["timestamp"])
                    
                    if log_time >= cutoff_date:
                        new_logs.append(log)
                    else:
                        cleanup_count += 1
                        
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
            
            # 更新日志列表
            if len(new_logs) != len(logs):
                await self.redis.delete(key)
                if new_logs:
                    await self.redis.lpush(key, *new_logs)
        
        return cleanup_count
    
    async def cleanup_old_monitoring_data(self, hours: int = 24) -> int:
        """清理旧监控数据"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cleanup_count = 0
        
        # 清理监控会话
        pattern = "execution_monitor:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            monitor_data_str = await self.redis.hget(key, "data")
            if monitor_data_str:
                try:
                    monitor_data = json.loads(monitor_data_str)
                    started_at = datetime.fromisoformat(monitor_data["started_at"])
                    
                    if started_at < cutoff_time:
                        await self.redis.delete(key)
                        cleanup_count += 1
                        
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        return cleanup_count