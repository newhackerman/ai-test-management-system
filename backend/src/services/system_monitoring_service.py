"""
系统监控和健康检查增强服务
负责系统指标收集、健康检查、告警管理等
"""
import asyncio
import logging
import time
import json
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..core.redis import redis_service
from ..core.config import settings
from ..models.infrastructure import SystemMetrics, SystemAlerts
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SystemMonitoringService:
    """系统监控服务"""
    
    def __init__(self):
        self.monitoring_interval = 30  # 30秒监控间隔
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "response_time": 2000.0,  # 毫秒
            "error_rate": 5.0  # 百分比
        }
        self.notification_service = NotificationService()
        self.is_monitoring = False
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """启动系统监控"""
        try:
            if self.is_monitoring:
                return {"status": "already_running", "message": "监控已在运行中"}
            
            self.is_monitoring = True
            
            # 启动监控任务
            asyncio.create_task(self._monitoring_loop())
            
            logger.info("系统监控已启动")
            return {"status": "success", "message": "系统监控已启动"}
            
        except Exception as e:
            logger.error(f"启动系统监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """停止系统监控"""
        try:
            self.is_monitoring = False
            logger.info("系统监控已停止")
            return {"status": "success", "message": "系统监控已停止"}
            
        except Exception as e:
            logger.error(f"停止系统监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集系统指标
                metrics = await self.collect_system_metrics()
                
                # 存储指标到数据库
                await self._store_metrics(metrics)
                
                # 检查告警规则
                alerts = await self._check_alert_rules(metrics)
                
                # 处理告警
                if alerts:
                    await self._handle_alerts(alerts)
                
                # 等待下一次监控
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            timestamp = datetime.now()
            
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存指标
            memory = psutil.virtual_memory()
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            
            # 网络指标
            network = psutil.net_io_counters()
            
            # 进程指标
            process = psutil.Process()
            
            # 数据库指标
            db_metrics = await self._collect_database_metrics()
            
            # Redis指标
            redis_metrics = await self._collect_redis_metrics()
            
            # 应用指标
            app_metrics = await self._collect_application_metrics()
            
            metrics = {
                "timestamp": timestamp.isoformat(),
                "system": {
                    "cpu_usage_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "memory_total_bytes": memory.total,
                    "memory_used_bytes": memory.used,
                    "memory_usage_percent": memory.percent,
                    "memory_available_bytes": memory.available,
                    "disk_total_bytes": disk.total,
                    "disk_used_bytes": disk.used,
                    "disk_usage_percent": (disk.used / disk.total) * 100,
                    "disk_free_bytes": disk.free,
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv,
                    "network_packets_sent": network.packets_sent,
                    "network_packets_recv": network.packets_recv
                },
                "process": {
                    "cpu_percent": process.cpu_percent(),
                    "memory_bytes": process.memory_info().rss,
                    "memory_percent": process.memory_percent(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0
                },
                "database": db_metrics,
                "redis": redis_metrics,
                "application": app_metrics
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def _collect_database_metrics(self) -> Dict[str, Any]:
        """收集数据库指标"""
        try:
            async with AsyncSessionLocal() as session:
                # 连接数统计
                result = await session.execute(text("""
                    SELECT 
                        COUNT(*) as total_connections,
                        SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections,
                        SUM(CASE WHEN COMMAND = 'Sleep' THEN 1 ELSE 0 END) as idle_connections
                    FROM information_schema.PROCESSLIST 
                    WHERE DB = DATABASE()
                """))
                
                conn_stats = result.fetchone()
                
                # 查询性能统计
                result = await session.execute(text("""
                    SELECT 
                        COUNT(*) as total_queries,
                        AVG(avg_latency/1000000) as avg_query_time_ms,
                        MAX(max_latency/1000000) as max_query_time_ms
                    FROM performance_schema.events_statements_summary_by_digest 
                    WHERE last_seen > DATE_SUB(NOW(), INTERVAL 1 MINUTE)
                """))
                
                query_stats = result.fetchone()
                
                return {
                    "total_connections": conn_stats.total_connections if conn_stats else 0,
                    "active_connections": conn_stats.active_connections if conn_stats else 0,
                    "idle_connections": conn_stats.idle_connections if conn_stats else 0,
                    "total_queries": query_stats.total_queries if query_stats else 0,
                    "avg_query_time_ms": float(query_stats.avg_query_time_ms) if query_stats and query_stats.avg_query_time_ms else 0,
                    "max_query_time_ms": float(query_stats.max_query_time_ms) if query_stats and query_stats.max_query_time_ms else 0
                }
                
        except Exception as e:
            logger.error(f"收集数据库指标失败: {e}")
            return {"error": str(e)}
    
    async def _collect_redis_metrics(self) -> Dict[str, Any]:
        """收集Redis指标"""
        try:
            if not redis_service.is_connected():
                return {"error": "Redis连接不可用"}
            
            # 获取Redis信息
            info_data = redis_service.redis_client.info()
            stats_data = redis_service.redis_client.info('stats')
            
            # 计算命中率
            hits = int(stats_data.get('keyspace_hits', 0))
            misses = int(stats_data.get('keyspace_misses', 0))
            total_requests = hits + misses
            hit_rate = hits / total_requests if total_requests > 0 else 0
            
            return {
                "connected_clients": info_data.get('connected_clients', 0),
                "used_memory_bytes": info_data.get('used_memory', 0),
                "used_memory_peak_bytes": info_data.get('used_memory_peak', 0),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate": round(hit_rate, 4),
                "total_commands_processed": info_data.get('total_commands_processed', 0),
                "instantaneous_ops_per_sec": info_data.get('instantaneous_ops_per_sec', 0),
                "expired_keys": stats_data.get('expired_keys', 0),
                "evicted_keys": stats_data.get('evicted_keys', 0)
            }
            
        except Exception as e:
            logger.error(f"收集Redis指标失败: {e}")
            return {"error": str(e)}
    
    async def _collect_application_metrics(self) -> Dict[str, Any]:
        """收集应用指标"""
        try:
            # 这里可以收集应用特定的指标
            # 例如：API响应时间、错误率、活跃用户数等
            
            # 模拟应用指标
            return {
                "active_sessions": 0,  # 可以从Redis或数据库获取
                "api_requests_per_minute": 0,  # 可以从日志或监控系统获取
                "error_rate_percent": 0,  # 可以从错误日志计算
                "avg_response_time_ms": 0,  # 可以从性能监控获取
                "queue_size": 0,  # 可以从消息队列获取
                "cache_hit_rate": 0  # 可以从缓存系统获取
            }
            
        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")
            return {"error": str(e)}
    
    async def _store_metrics(self, metrics: Dict[str, Any]):
        """存储指标到数据库"""
        try:
            if "error" in metrics:
                return
            
            async with AsyncSessionLocal() as session:
                timestamp = datetime.fromisoformat(metrics["timestamp"])
                
                # 存储系统指标
                system_metrics = metrics.get("system", {})
                for metric_name, metric_value in system_metrics.items():
                    if isinstance(metric_value, (int, float)):
                        metric = SystemMetrics(
                            metric_name=metric_name,
                            metric_type="GAUGE",
                            metric_category="SYSTEM",
                            metric_value=float(metric_value),
                            metric_unit=self._get_metric_unit(metric_name),
                            source_host="localhost",
                            source_service="system_monitor",
                            timestamp=timestamp,
                            collection_time=datetime.now()
                        )
                        session.add(metric)
                
                # 存储进程指标
                process_metrics = metrics.get("process", {})
                for metric_name, metric_value in process_metrics.items():
                    if isinstance(metric_value, (int, float)):
                        metric = SystemMetrics(
                            metric_name=f"process_{metric_name}",
                            metric_type="GAUGE",
                            metric_category="APPLICATION",
                            metric_value=float(metric_value),
                            metric_unit=self._get_metric_unit(metric_name),
                            source_host="localhost",
                            source_service="application",
                            timestamp=timestamp,
                            collection_time=datetime.now()
                        )
                        session.add(metric)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"存储指标失败: {e}")
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """获取指标单位"""
        if "percent" in metric_name:
            return "%"
        elif "bytes" in metric_name:
            return "bytes"
        elif "ms" in metric_name:
            return "ms"
        elif "count" in metric_name:
            return "count"
        else:
            return ""
    
    async def _check_alert_rules(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查告警规则"""
        alerts = []
        
        try:
            if "error" in metrics:
                return alerts
            
            system_metrics = metrics.get("system", {})
            
            # 检查CPU使用率
            cpu_usage = system_metrics.get("cpu_usage_percent", 0)
            if cpu_usage > self.alert_thresholds["cpu_usage"]:
                alerts.append({
                    "alert_code": "HIGH_CPU_USAGE",
                    "alert_name": "CPU使用率过高",
                    "alert_level": "WARNING" if cpu_usage < 90 else "CRITICAL",
                    "alert_type": "THRESHOLD",
                    "alert_message": f"CPU使用率达到 {cpu_usage:.1f}%，超过阈值 {self.alert_thresholds['cpu_usage']}%",
                    "current_value": cpu_usage,
                    "threshold_value": self.alert_thresholds["cpu_usage"],
                    "metric_name": "cpu_usage_percent"
                })
            
            # 检查内存使用率
            memory_usage = system_metrics.get("memory_usage_percent", 0)
            if memory_usage > self.alert_thresholds["memory_usage"]:
                alerts.append({
                    "alert_code": "HIGH_MEMORY_USAGE",
                    "alert_name": "内存使用率过高",
                    "alert_level": "WARNING" if memory_usage < 95 else "CRITICAL",
                    "alert_type": "THRESHOLD",
                    "alert_message": f"内存使用率达到 {memory_usage:.1f}%，超过阈值 {self.alert_thresholds['memory_usage']}%",
                    "current_value": memory_usage,
                    "threshold_value": self.alert_thresholds["memory_usage"],
                    "metric_name": "memory_usage_percent"
                })
            
            # 检查磁盘使用率
            disk_usage = system_metrics.get("disk_usage_percent", 0)
            if disk_usage > self.alert_thresholds["disk_usage"]:
                alerts.append({
                    "alert_code": "HIGH_DISK_USAGE",
                    "alert_name": "磁盘使用率过高",
                    "alert_level": "WARNING" if disk_usage < 95 else "CRITICAL",
                    "alert_type": "THRESHOLD",
                    "alert_message": f"磁盘使用率达到 {disk_usage:.1f}%，超过阈值 {self.alert_thresholds['disk_usage']}%",
                    "current_value": disk_usage,
                    "threshold_value": self.alert_thresholds["disk_usage"],
                    "metric_name": "disk_usage_percent"
                })
            
            # 检查数据库指标
            db_metrics = metrics.get("database", {})
            if not db_metrics.get("error"):
                avg_query_time = db_metrics.get("avg_query_time_ms", 0)
                if avg_query_time > self.alert_thresholds["response_time"]:
                    alerts.append({
                        "alert_code": "SLOW_DATABASE_QUERIES",
                        "alert_name": "数据库查询响应慢",
                        "alert_level": "WARNING",
                        "alert_type": "THRESHOLD",
                        "alert_message": f"数据库平均查询时间 {avg_query_time:.1f}ms，超过阈值 {self.alert_thresholds['response_time']}ms",
                        "current_value": avg_query_time,
                        "threshold_value": self.alert_thresholds["response_time"],
                        "metric_name": "avg_query_time_ms"
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查告警规则失败: {e}")
            return []
    
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """处理告警"""
        try:
            async with AsyncSessionLocal() as session:
                for alert_data in alerts:
                    # 检查是否已存在相同的活跃告警
                    existing_alert = await session.execute(
                        text("SELECT id FROM system_alerts WHERE alert_code = :code AND status = 'ACTIVE'"),
                        {"code": alert_data["alert_code"]}
                    )
                    
                    if existing_alert.fetchone():
                        # 更新现有告警的发生次数和最后发生时间
                        await session.execute(
                            text("""
                                UPDATE system_alerts 
                                SET occurrence_count = occurrence_count + 1,
                                    last_occurred_at = NOW(),
                                    current_value = :current_value,
                                    updated_at = NOW()
                                WHERE alert_code = :code AND status = 'ACTIVE'
                            """),
                            {
                                "code": alert_data["alert_code"],
                                "current_value": alert_data["current_value"]
                            }
                        )
                    else:
                        # 创建新告警
                        alert = SystemAlerts(
                            alert_code=alert_data["alert_code"],
                            alert_name=alert_data["alert_name"],
                            alert_level=alert_data["alert_level"],
                            alert_type=alert_data["alert_type"],
                            alert_message=alert_data["alert_message"],
                            alert_source="system_monitor",
                            threshold_value=alert_data["threshold_value"],
                            current_value=alert_data["current_value"],
                            status="ACTIVE",
                            severity_score=self._calculate_severity_score(alert_data["alert_level"]),
                            first_occurred_at=datetime.now(),
                            last_occurred_at=datetime.now(),
                            occurrence_count=1
                        )
                        session.add(alert)
                        
                        # 发送告警通知
                        await self._send_alert_notification(alert_data)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"处理告警失败: {e}")
    
    def _calculate_severity_score(self, alert_level: str) -> int:
        """计算严重程度评分"""
        severity_map = {
            "INFO": 10,
            "WARNING": 50,
            "ERROR": 75,
            "CRITICAL": 90,
            "FATAL": 100
        }
        return severity_map.get(alert_level, 0)
    
    async def _send_alert_notification(self, alert_data: Dict[str, Any]):
        """发送告警通知"""
        try:
            # 构建通知消息
            message = f"""
            🚨 系统告警通知
            
            告警名称: {alert_data['alert_name']}
            告警级别: {alert_data['alert_level']}
            告警消息: {alert_data['alert_message']}
            当前值: {alert_data['current_value']}
            阈值: {alert_data['threshold_value']}
            时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # 发送通知（这里可以集成邮件、短信、钉钉等通知方式）
            await self.notification_service.send_notification(
                title=f"系统告警: {alert_data['alert_name']}",
                message=message,
                level=alert_data['alert_level'],
                channels=["email", "webhook"]  # 可配置通知渠道
            )
            
        except Exception as e:
            logger.error(f"发送告警通知失败: {e}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 收集当前指标
            metrics = await self.collect_system_metrics()
            
            if "error" in metrics:
                return {
                    "status": "unhealthy",
                    "message": "无法收集系统指标",
                    "error": metrics["error"]
                }
            
            # 评估系统健康状态
            health_status = self._evaluate_system_health(metrics)
            
            return {
                "status": health_status["overall_status"],
                "score": health_status["health_score"],
                "components": health_status["components"],
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _evaluate_system_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """评估系统健康状态"""
        components = {}
        total_score = 0
        component_count = 0
        
        # 评估系统组件
        system_metrics = metrics.get("system", {})
        
        # CPU健康状态
        cpu_usage = system_metrics.get("cpu_usage_percent", 0)
        cpu_score = max(0, 100 - cpu_usage)
        components["cpu"] = {
            "status": "healthy" if cpu_usage < 70 else "warning" if cpu_usage < 90 else "critical",
            "score": cpu_score,
            "usage": cpu_usage
        }
        total_score += cpu_score
        component_count += 1
        
        # 内存健康状态
        memory_usage = system_metrics.get("memory_usage_percent", 0)
        memory_score = max(0, 100 - memory_usage)
        components["memory"] = {
            "status": "healthy" if memory_usage < 75 else "warning" if memory_usage < 90 else "critical",
            "score": memory_score,
            "usage": memory_usage
        }
        total_score += memory_score
        component_count += 1
        
        # 磁盘健康状态
        disk_usage = system_metrics.get("disk_usage_percent", 0)
        disk_score = max(0, 100 - disk_usage)
        components["disk"] = {
            "status": "healthy" if disk_usage < 80 else "warning" if disk_usage < 95 else "critical",
            "score": disk_score,
            "usage": disk_usage
        }
        total_score += disk_score
        component_count += 1
        
        # 数据库健康状态
        db_metrics = metrics.get("database", {})
        if not db_metrics.get("error"):
            db_score = 100  # 基础分数
            
            # 根据连接数调整分数
            active_connections = db_metrics.get("active_connections", 0)
            if active_connections > 50:
                db_score -= min(30, (active_connections - 50) * 2)
            
            # 根据查询时间调整分数
            avg_query_time = db_metrics.get("avg_query_time_ms", 0)
            if avg_query_time > 100:
                db_score -= min(40, (avg_query_time - 100) / 10)
            
            db_score = max(0, db_score)
            components["database"] = {
                "status": "healthy" if db_score > 70 else "warning" if db_score > 40 else "critical",
                "score": db_score,
                "active_connections": active_connections,
                "avg_query_time_ms": avg_query_time
            }
            total_score += db_score
            component_count += 1
        else:
            components["database"] = {
                "status": "critical",
                "score": 0,
                "error": db_metrics["error"]
            }
            component_count += 1
        
        # Redis健康状态
        redis_metrics = metrics.get("redis", {})
        if not redis_metrics.get("error"):
            redis_score = 100
            
            # 根据内存使用调整分数
            used_memory = redis_metrics.get("used_memory_bytes", 0)
            if used_memory > 1024 * 1024 * 1024:  # 1GB
                redis_score -= min(30, (used_memory - 1024 * 1024 * 1024) / (1024 * 1024 * 100))
            
            # 根据命中率调整分数
            hit_rate = redis_metrics.get("hit_rate", 1.0)
            if hit_rate < 0.8:
                redis_score -= (0.8 - hit_rate) * 100
            
            redis_score = max(0, redis_score)
            components["redis"] = {
                "status": "healthy" if redis_score > 70 else "warning" if redis_score > 40 else "critical",
                "score": redis_score,
                "hit_rate": hit_rate,
                "used_memory_mb": used_memory / (1024 * 1024)
            }
            total_score += redis_score
            component_count += 1
        else:
            components["redis"] = {
                "status": "critical",
                "score": 0,
                "error": redis_metrics["error"]
            }
            component_count += 1
        
        # 计算总体健康分数
        health_score = total_score / component_count if component_count > 0 else 0
        
        # 确定总体状态
        if health_score >= 80:
            overall_status = "healthy"
        elif health_score >= 60:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "health_score": round(health_score, 2),
            "components": components
        }
    
    async def get_metrics_history(self, metric_name: str, time_range: str = "1h") -> List[Dict[str, Any]]:
        """获取指标历史数据"""
        try:
            # 解析时间范围
            end_time = datetime.now()
            if time_range.endswith('h'):
                hours = int(time_range[:-1])
                start_time = end_time - timedelta(hours=hours)
            elif time_range.endswith('d'):
                days = int(time_range[:-1])
                start_time = end_time - timedelta(days=days)
            else:
                start_time = end_time - timedelta(hours=1)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT timestamp, metric_value, metric_unit
                        FROM system_metrics 
                        WHERE metric_name = :metric_name 
                        AND timestamp BETWEEN :start_time AND :end_time
                        ORDER BY timestamp ASC
                    """),
                    {
                        "metric_name": metric_name,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                )
                
                history = []
                for row in result:
                    history.append({
                        "timestamp": row.timestamp.isoformat(),
                        "value": float(row.metric_value),
                        "unit": row.metric_unit
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"获取指标历史数据失败: {e}")
            return []


# 创建服务实例
system_monitoring_service = SystemMonitoringService()