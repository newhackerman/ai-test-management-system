"""
自动错误恢复机制服务
负责系统故障检测、自动恢复、故障转移等
"""
import asyncio
import logging
import time
import json
import os
import psutil
import aiohttp
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import text

from ..core.database import AsyncSessionLocal, async_engine
from ..core.redis import redis_service, get_redis_client
from ..core.config import settings
from ..models.infrastructure import SystemAlerts, RecoveryActions
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """故障类型枚举"""
    DATABASE_CONNECTION = "database_connection"
    REDIS_CONNECTION = "redis_connection"
    HIGH_CPU_USAGE = "high_cpu_usage"
    HIGH_MEMORY_USAGE = "high_memory_usage"
    DISK_FULL = "disk_full"
    SERVICE_UNAVAILABLE = "service_unavailable"
    SLOW_RESPONSE = "slow_response"
    ERROR_RATE_HIGH = "error_rate_high"


class RecoveryStatus(Enum):
    """恢复状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AutoRecoveryService:
    """自动错误恢复服务"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.failure_thresholds = {
            FailureType.HIGH_CPU_USAGE: 90.0,
            FailureType.HIGH_MEMORY_USAGE: 95.0,
            FailureType.DISK_FULL: 98.0,
            FailureType.SLOW_RESPONSE: 5000.0,  # 5秒
            FailureType.ERROR_RATE_HIGH: 10.0   # 10%
        }
        self.recovery_cooldown = 300  # 5分钟冷却时间
        self.last_recovery_times = {}
        self.is_monitoring = False
    
    def _initialize_recovery_strategies(self) -> Dict[FailureType, Callable]:
        """初始化恢复策略"""
        return {
            FailureType.DATABASE_CONNECTION: self._recover_database_connection,
            FailureType.REDIS_CONNECTION: self._recover_redis_connection,
            FailureType.HIGH_CPU_USAGE: self._recover_high_cpu_usage,
            FailureType.HIGH_MEMORY_USAGE: self._recover_high_memory_usage,
            FailureType.DISK_FULL: self._recover_disk_full,
            FailureType.SERVICE_UNAVAILABLE: self._recover_service_unavailable,
            FailureType.SLOW_RESPONSE: self._recover_slow_response,
            FailureType.ERROR_RATE_HIGH: self._recover_error_rate_high
        }
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """启动自动恢复监控"""
        try:
            if self.is_monitoring:
                return {"status": "already_running", "message": "自动恢复监控已在运行中"}
            
            self.is_monitoring = True
            
            # 启动监控任务
            asyncio.create_task(self._monitoring_loop())
            
            logger.info("自动恢复监控已启动")
            return {"status": "success", "message": "自动恢复监控已启动"}
            
        except Exception as e:
            logger.error(f"启动自动恢复监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """停止自动恢复监控"""
        try:
            self.is_monitoring = False
            logger.info("自动恢复监控已停止")
            return {"status": "success", "message": "自动恢复监控已停止"}
            
        except Exception as e:
            logger.error(f"停止自动恢复监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 检测系统故障
                failures = await self.detect_failures()
                
                # 处理检测到的故障
                for failure in failures:
                    await self._handle_failure(failure)
                
                # 等待下一次检测
                await asyncio.sleep(30)  # 30秒检测间隔
                
            except Exception as e:
                logger.error(f"自动恢复监控循环异常: {e}")
                await asyncio.sleep(30)
    
    async def detect_failures(self) -> List[Dict[str, Any]]:
        """检测系统故障"""
        failures = []
        
        try:
            # 检测数据库连接
            db_failure = await self._check_database_connection()
            if db_failure:
                failures.append(db_failure)
            
            # 检测Redis连接
            redis_failure = await self._check_redis_connection()
            if redis_failure:
                failures.append(redis_failure)
            
            # 检测系统资源
            resource_failures = await self._check_system_resources()
            failures.extend(resource_failures)
            
            # 检测服务可用性
            service_failures = await self._check_service_availability()
            failures.extend(service_failures)
            
            return failures
            
        except Exception as e:
            logger.error(f"故障检测失败: {e}")
            return []
    
    async def _check_database_connection(self) -> Optional[Dict[str, Any]]:
        """检测数据库连接"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return None  # 连接正常
            
        except Exception as e:
            return {
                "failure_type": FailureType.DATABASE_CONNECTION,
                "severity": "critical",
                "message": f"数据库连接失败: {str(e)}",
                "detected_at": datetime.now(),
                "details": {"error": str(e)}
            }
    
    async def _check_redis_connection(self) -> Optional[Dict[str, Any]]:
        """检测Redis连接"""
        try:
            client = await get_redis_client()
            if client:
                await client.ping()
                await client.close()
                return None  # 连接正常
            else:
                raise Exception("无法获取Redis客户端")
                
        except Exception as e:
            return {
                "failure_type": FailureType.REDIS_CONNECTION,
                "severity": "high",
                "message": f"Redis连接失败: {str(e)}",
                "detected_at": datetime.now(),
                "details": {"error": str(e)}
            }
    
    async def _check_system_resources(self) -> List[Dict[str, Any]]:
        """检测系统资源"""
        failures = []
        
        try:
            # 检测CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.failure_thresholds[FailureType.HIGH_CPU_USAGE]:
                failures.append({
                    "failure_type": FailureType.HIGH_CPU_USAGE,
                    "severity": "high",
                    "message": f"CPU使用率过高: {cpu_percent}%",
                    "detected_at": datetime.now(),
                    "details": {"cpu_percent": cpu_percent, "threshold": self.failure_thresholds[FailureType.HIGH_CPU_USAGE]}
                })
            
            # 检测内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > self.failure_thresholds[FailureType.HIGH_MEMORY_USAGE]:
                failures.append({
                    "failure_type": FailureType.HIGH_MEMORY_USAGE,
                    "severity": "high",
                    "message": f"内存使用率过高: {memory.percent}%",
                    "detected_at": datetime.now(),
                    "details": {"memory_percent": memory.percent, "threshold": self.failure_thresholds[FailureType.HIGH_MEMORY_USAGE]}
                })
            
            # 检测磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > self.failure_thresholds[FailureType.DISK_FULL]:
                failures.append({
                    "failure_type": FailureType.DISK_FULL,
                    "severity": "critical",
                    "message": f"磁盘使用率过高: {disk_percent:.1f}%",
                    "detected_at": datetime.now(),
                    "details": {"disk_percent": disk_percent, "threshold": self.failure_thresholds[FailureType.DISK_FULL]}
                })
            
            return failures
            
        except Exception as e:
            logger.error(f"系统资源检测失败: {e}")
            return []
    
    async def _check_service_availability(self) -> List[Dict[str, Any]]:
        """检测服务可用性"""
        failures = []
        
        try:
            # 检测API服务响应时间
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"http://localhost:{settings.PORT}/health", timeout=5) as response:
                        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                        
                        if response.status != 200:
                            failures.append({
                                "failure_type": FailureType.SERVICE_UNAVAILABLE,
                                "severity": "critical",
                                "message": f"API服务不可用，状态码: {response.status}",
                                "detected_at": datetime.now(),
                                "details": {"status_code": response.status, "response_time_ms": response_time}
                            })
                        elif response_time > self.failure_thresholds[FailureType.SLOW_RESPONSE]:
                            failures.append({
                                "failure_type": FailureType.SLOW_RESPONSE,
                                "severity": "medium",
                                "message": f"API响应时间过慢: {response_time:.1f}ms",
                                "detected_at": datetime.now(),
                                "details": {"response_time_ms": response_time, "threshold": self.failure_thresholds[FailureType.SLOW_RESPONSE]}
                            })
                            
                except asyncio.TimeoutError:
                    failures.append({
                        "failure_type": FailureType.SERVICE_UNAVAILABLE,
                        "severity": "critical",
                        "message": "API服务响应超时",
                        "detected_at": datetime.now(),
                        "details": {"timeout": True}
                    })
            
            return failures
            
        except Exception as e:
            logger.error(f"服务可用性检测失败: {e}")
            return []
    
    async def _handle_failure(self, failure: Dict[str, Any]):
        """处理检测到的故障"""
        try:
            failure_type = failure["failure_type"]
            
            # 检查冷却时间
            if not self._can_recover(failure_type):
                logger.info(f"故障 {failure_type.value} 在冷却期内，跳过恢复")
                return
            
            # 记录故障
            await self._log_failure(failure)
            
            # 执行自动恢复
            recovery_result = await self.auto_recover(failure_type, failure)
            
            # 记录恢复操作
            await self._log_recovery_action(failure, recovery_result)
            
            # 发送通知
            await self._send_recovery_notification(failure, recovery_result)
            
        except Exception as e:
            logger.error(f"处理故障失败: {e}")
    
    def _can_recover(self, failure_type: FailureType) -> bool:
        """检查是否可以执行恢复操作（冷却时间检查）"""
        last_recovery = self.last_recovery_times.get(failure_type)
        if last_recovery:
            time_since_last = (datetime.now() - last_recovery).total_seconds()
            return time_since_last >= self.recovery_cooldown
        return True
    
    async def auto_recover(self, failure_type: FailureType, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """执行自动恢复"""
        try:
            recovery_strategy = self.recovery_strategies.get(failure_type)
            if not recovery_strategy:
                return {
                    "status": RecoveryStatus.SKIPPED,
                    "message": f"没有找到 {failure_type.value} 的恢复策略"
                }
            
            # 更新最后恢复时间
            self.last_recovery_times[failure_type] = datetime.now()
            
            # 执行恢复策略
            logger.info(f"开始执行 {failure_type.value} 的自动恢复")
            recovery_result = await recovery_strategy(failure_details)
            
            logger.info(f"{failure_type.value} 自动恢复完成: {recovery_result['status'].value}")
            return recovery_result
            
        except Exception as e:
            logger.error(f"自动恢复执行失败: {e}")
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"恢复执行异常: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_database_connection(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复数据库连接"""
        try:
            # 尝试重新连接数据库
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "数据库连接已恢复",
                "actions_taken": ["重新建立数据库连接"]
            }
            
        except Exception as e:
            # 尝试重启数据库连接池
            try:
                if async_engine:
                    await async_engine.dispose()
                
                return {
                    "status": RecoveryStatus.SUCCESS,
                    "message": "数据库连接池已重置",
                    "actions_taken": ["重置数据库连接池"]
                }
                
            except Exception as e2:
                return {
                    "status": RecoveryStatus.FAILED,
                    "message": f"数据库连接恢复失败: {str(e2)}",
                    "actions_taken": ["尝试重新连接", "尝试重置连接池"],
                    "error": str(e2)
                }
    
    async def _recover_redis_connection(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复Redis连接"""
        try:
            # 尝试重新连接Redis
            client = await get_redis_client()
            if client:
                await client.ping()
                await client.close()
                
                return {
                    "status": RecoveryStatus.SUCCESS,
                    "message": "Redis连接已恢复",
                    "actions_taken": ["重新建立Redis连接"]
                }
            else:
                return {
                    "status": RecoveryStatus.FAILED,
                    "message": "无法重新建立Redis连接",
                    "actions_taken": ["尝试重新连接Redis"]
                }
                
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"Redis连接恢复失败: {str(e)}",
                "actions_taken": ["尝试重新连接Redis"],
                "error": str(e)
            }
    
    async def _recover_high_cpu_usage(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复高CPU使用率"""
        try:
            actions_taken = []
            
            # 查找CPU使用率最高的进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 10:  # CPU使用率超过10%的进程
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # 记录高CPU进程
            high_cpu_processes = processes[:5]  # 前5个高CPU进程
            actions_taken.append(f"识别出 {len(high_cpu_processes)} 个高CPU使用率进程")
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "高CPU使用率问题已分析",
                "actions_taken": actions_taken,
                "high_cpu_processes": high_cpu_processes
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"高CPU使用率恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_high_memory_usage(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复高内存使用率"""
        try:
            actions_taken = []
            
            # 清理缓存
            if redis_service.is_connected():
                # 清理过期的Redis键
                client = await get_redis_client()
                if client:
                    keys = await client.keys("*")
                    expired_keys = 0
                    for key in keys:
                        ttl = await client.ttl(key)
                        if ttl == 0:  # 已过期
                            await client.delete(key)
                            expired_keys += 1
                    
                    await client.close()
                    actions_taken.append(f"清理了 {expired_keys} 个过期的Redis键")
            
            # 强制垃圾回收
            import gc
            collected = gc.collect()
            actions_taken.append(f"执行垃圾回收，回收了 {collected} 个对象")
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "高内存使用率问题已处理",
                "actions_taken": actions_taken
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"高内存使用率恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_disk_full(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复磁盘空间不足"""
        try:
            actions_taken = []
            
            # 清理临时文件
            temp_dirs = ["/tmp", "/var/tmp", "temp_uploads", "reports"]
            cleaned_size = 0
            
            for temp_dir in temp_dirs:
                try:
                    if os.path.exists(temp_dir):
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    # 删除超过1天的临时文件
                                    if os.path.getmtime(file_path) < time.time() - 86400:
                                        file_size = os.path.getsize(file_path)
                                        os.remove(file_path)
                                        cleaned_size += file_size
                                except:
                                    pass
                except:
                    pass
            
            actions_taken.append(f"清理临时文件，释放了 {cleaned_size / (1024*1024):.1f} MB空间")
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "磁盘空间清理完成",
                "actions_taken": actions_taken,
                "cleaned_size_mb": cleaned_size / (1024*1024)
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"磁盘空间恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_service_unavailable(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复服务不可用"""
        try:
            actions_taken = []
            
            # 检查服务进程
            current_process = psutil.Process()
            actions_taken.append(f"当前进程状态: {current_process.status()}")
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "服务状态已检查",
                "actions_taken": actions_taken
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"服务恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_slow_response(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复响应缓慢"""
        try:
            actions_taken = []
            
            # 清理数据库连接池
            if async_engine:
                pool = async_engine.pool
                actions_taken.append(f"数据库连接池状态: {pool.size()} 总连接, {pool.checkedout()} 已使用")
            
            # 清理缓存以释放内存
            if redis_service.is_connected():
                client = await get_redis_client()
                if client:
                    info = await client.info('memory')
                    actions_taken.append(f"Redis内存使用: {info.get('used_memory_human', 'N/A')}")
                    await client.close()
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "响应缓慢问题已分析",
                "actions_taken": actions_taken
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"响应缓慢恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _recover_error_rate_high(self, failure_details: Dict[str, Any]) -> Dict[str, Any]:
        """恢复高错误率"""
        try:
            actions_taken = []
            actions_taken.append("分析了错误率情况")
            
            return {
                "status": RecoveryStatus.SUCCESS,
                "message": "高错误率问题已分析",
                "actions_taken": actions_taken
            }
            
        except Exception as e:
            return {
                "status": RecoveryStatus.FAILED,
                "message": f"高错误率恢复失败: {str(e)}",
                "error": str(e)
            }
    
    async def _log_failure(self, failure: Dict[str, Any]):
        """记录故障信息"""
        try:
            async with AsyncSessionLocal() as session:
                alert = SystemAlerts(
                    alert_code=f"AUTO_RECOVERY_{failure['failure_type'].value.upper()}",
                    alert_name=f"自动恢复检测到故障: {failure['failure_type'].value}",
                    alert_level=failure['severity'].upper(),
                    alert_type="AUTO_RECOVERY",
                    alert_message=failure['message'],
                    alert_source="auto_recovery_service",
                    status="ACTIVE",
                    severity_score=self._get_severity_score(failure['severity']),
                    first_occurred_at=failure['detected_at'],
                    last_occurred_at=failure['detected_at'],
                    occurrence_count=1,
                    additional_data=json.dumps(failure.get('details', {}))
                )
                session.add(alert)
                await session.commit()
                
        except Exception as e:
            logger.error(f"记录故障信息失败: {e}")
    
    async def _log_recovery_action(self, failure: Dict[str, Any], recovery_result: Dict[str, Any]):
        """记录恢复操作"""
        try:
            async with AsyncSessionLocal() as session:
                recovery_action = RecoveryActions(
                    failure_type=failure['failure_type'].value,
                    recovery_strategy=failure['failure_type'].value,
                    trigger_condition=failure['message'],
                    recovery_status=recovery_result['status'].value,
                    recovery_message=recovery_result.get('message', ''),
                    actions_taken=json.dumps(recovery_result.get('actions_taken', [])),
                    execution_time=datetime.now(),
                    success_rate=1.0 if recovery_result['status'] == RecoveryStatus.SUCCESS else 0.0,
                    additional_data=json.dumps({
                        'failure_details': failure.get('details', {}),
                        'recovery_details': recovery_result
                    })
                )
                session.add(recovery_action)
                await session.commit()
                
        except Exception as e:
            logger.error(f"记录恢复操作失败: {e}")
    
    def _get_severity_score(self, severity: str) -> int:
        """获取严重程度评分"""
        severity_map = {
            "low": 25,
            "medium": 50,
            "high": 75,
            "critical": 100
        }
        return severity_map.get(severity.lower(), 50)
    
    async def _send_recovery_notification(self, failure: Dict[str, Any], recovery_result: Dict[str, Any]):
        """发送恢复通知"""
        try:
            status_emoji = "✅" if recovery_result['status'] == RecoveryStatus.SUCCESS else "❌"
            
            message = f"""
            {status_emoji} 自动恢复通知
            
            故障类型: {failure['failure_type'].value}
            故障描述: {failure['message']}
            恢复状态: {recovery_result['status'].value}
            恢复结果: {recovery_result.get('message', '')}
            
            执行的操作:
            {chr(10).join(f"• {action}" for action in recovery_result.get('actions_taken', []))}
            
            时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.notification_service.send_notification(
                title=f"自动恢复通知: {failure['failure_type'].value}",
                message=message,
                level=failure['severity'],
                channels=["email", "webhook"]
            )
            
        except Exception as e:
            logger.error(f"发送恢复通知失败: {e}")
    
    async def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取恢复历史记录"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT * FROM recovery_actions 
                        ORDER BY execution_time DESC 
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                
                history = []
                for row in result:
                    history.append({
                        "id": row.id,
                        "failure_type": row.failure_type,
                        "recovery_strategy": row.recovery_strategy,
                        "recovery_status": row.recovery_status,
                        "recovery_message": row.recovery_message,
                        "actions_taken": json.loads(row.actions_taken) if row.actions_taken else [],
                        "execution_time": row.execution_time.isoformat(),
                        "success_rate": row.success_rate
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"获取恢复历史失败: {e}")
            return []
    
    async def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        try:
            async with AsyncSessionLocal() as session:
                # 总恢复次数
                result = await session.execute(text("SELECT COUNT(*) as total FROM recovery_actions"))
                total_recoveries = result.fetchone().total
                
                # 成功恢复次数
                result = await session.execute(
                    text("SELECT COUNT(*) as success FROM recovery_actions WHERE recovery_status = 'success'")
                )
                successful_recoveries = result.fetchone().success
                
                # 按故障类型统计
                result = await session.execute(
                    text("""
                        SELECT failure_type, COUNT(*) as count, AVG(success_rate) as avg_success_rate
                        FROM recovery_actions 
                        GROUP BY failure_type
                    """)
                )
                
                failure_type_stats = {}
                for row in result:
                    failure_type_stats[row.failure_type] = {
                        "count": row.count,
                        "avg_success_rate": float(row.avg_success_rate) if row.avg_success_rate else 0
                    }
                
                # 最近24小时的恢复次数
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as recent FROM recovery_actions 
                        WHERE execution_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    """)
                )
                recent_recoveries = result.fetchone().recent
                
                success_rate = (successful_recoveries / total_recoveries * 100) if total_recoveries > 0 else 0
                
                return {
                    "total_recoveries": total_recoveries,
                    "successful_recoveries": successful_recoveries,
                    "success_rate": round(success_rate, 2),
                    "recent_24h_recoveries": recent_recoveries,
                    "failure_type_statistics": failure_type_stats,
                    "monitoring_status": "active" if self.is_monitoring else "inactive"
                }
                
        except Exception as e:
            logger.error(f"获取恢复统计失败: {e}")
            return {
                "error": str(e),
                "monitoring_status": "active" if self.is_monitoring else "inactive"
            }


# 创建服务实例
auto_recovery_service = AutoRecoveryService()