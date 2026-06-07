"""
AI服务健康检查服务

提供全面的AI服务健康检查机制，包括：
1. 定期健康检查
2. 健康状态监控和报告
3. 异常检测和告警
4. 健康指标统计和分析
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import json

# from ..adapters.base import BaseAIAdapter, AIRequest, AIResponse, MessageRole, ChatMessage
# from ..adapters.adapter_manager import AIAdapterManager, AdapterStatus

logger = logging.getLogger(__name__)


class HealthCheckType(Enum):
    """健康检查类型"""
    BASIC = "basic"  # 基础连通性检查
    FUNCTIONAL = "functional"  # 功能性检查
    PERFORMANCE = "performance"  # 性能检查
    COMPREHENSIVE = "comprehensive"  # 综合检查


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    adapter_name: str
    check_type: HealthCheckType
    status: HealthStatus
    response_time: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # 详细信息
    success: bool = True
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # 性能指标
    latency_ms: Optional[float] = None
    throughput: Optional[float] = None
    availability: Optional[float] = None
    
    # 功能检查结果
    api_accessible: bool = True
    model_available: bool = True
    response_quality: Optional[float] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "adapter_name": self.adapter_name,
            "check_type": self.check_type.value,
            "status": self.status.value,
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "latency_ms": self.latency_ms,
            "throughput": self.throughput,
            "availability": self.availability,
            "api_accessible": self.api_accessible,
            "model_available": self.model_available,
            "response_quality": self.response_quality,
            "metadata": self.metadata
        }


@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    # 检查间隔（秒）
    basic_interval: int = 60
    functional_interval: int = 300  # 5分钟
    performance_interval: int = 600  # 10分钟
    comprehensive_interval: int = 1800  # 30分钟
    
    # 超时设置（秒）
    basic_timeout: float = 10.0
    functional_timeout: float = 30.0
    performance_timeout: float = 60.0
    
    # 重试设置
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 阈值设置
    warning_response_time: float = 5.0  # 响应时间警告阈值（秒）
    critical_response_time: float = 10.0  # 响应时间严重阈值（秒）
    warning_error_rate: float = 0.1  # 错误率警告阈值（10%）
    critical_error_rate: float = 0.3  # 错误率严重阈值（30%）
    
    # 历史数据保留
    history_retention_days: int = 7
    
    # 告警设置
    enable_alerts: bool = True
    alert_cooldown: int = 300  # 告警冷却时间（秒）


class HealthCheckService:
    """健康检查服务"""
    
    def __init__(self, adapter_manager=None, config: Optional[HealthCheckConfig] = None):
        """
        初始化健康检查服务
        
        Args:
            adapter_manager: AI适配器管理器
            config: 健康检查配置
        """
        self.adapter_manager = adapter_manager
        self.config = config or HealthCheckConfig()
        self.logger = logging.getLogger(__name__)
        
        # 健康检查历史
        self.check_history: Dict[str, List[HealthCheckResult]] = {}
        
        # 当前健康状态
        self.current_status: Dict[str, HealthStatus] = {}
        
        # 告警状态
        self.alert_history: Dict[str, datetime] = {}
        
        # 任务管理
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 回调函数
        self.status_change_callbacks: List[Callable[[str, HealthStatus, HealthStatus], None]] = []
        self.alert_callbacks: List[Callable[[str, HealthCheckResult], None]] = []
        
        # 统计信息
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "avg_response_time": 0.0,
            "last_check_time": None
        }
    
    async def start(self):
        """启动健康检查服务"""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting Health Check Service")
        
        # 启动各种类型的健康检查任务
        self._tasks = [
            asyncio.create_task(self._basic_health_check_loop()),
            asyncio.create_task(self._functional_health_check_loop()),
            asyncio.create_task(self._performance_health_check_loop()),
            asyncio.create_task(self._comprehensive_health_check_loop()),
            asyncio.create_task(self._cleanup_history_loop())
        ]
        
        self.logger.info("Health Check Service started")
    
    async def stop(self):
        """停止健康检查服务"""
        if not self._running:
            return
        
        self._running = False
        self.logger.info("Stopping Health Check Service")
        
        # 取消所有任务
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._tasks.clear()
        self.logger.info("Health Check Service stopped")
    
    async def check_adapter_health(self, adapter_name: str, 
                                 check_type: HealthCheckType = HealthCheckType.BASIC) -> HealthCheckResult:
        """
        检查单个适配器的健康状态
        
        Args:
            adapter_name: 适配器名称
            check_type: 检查类型
            
        Returns:
            HealthCheckResult: 健康检查结果
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # 获取适配器
            if adapter_name not in self.adapter_manager.adapters:
                return HealthCheckResult(
                    adapter_name=adapter_name,
                    check_type=check_type,
                    status=HealthStatus.CRITICAL,
                    response_time=0.0,
                    success=False,
                    error_message="Adapter not found",
                    error_code="ADAPTER_NOT_FOUND"
                )
            
            adapter = self.adapter_manager.adapters[adapter_name]
            
            # 根据检查类型执行不同的检查
            if check_type == HealthCheckType.BASIC:
                result = await self._basic_health_check(adapter_name, adapter)
            elif check_type == HealthCheckType.FUNCTIONAL:
                result = await self._functional_health_check(adapter_name, adapter)
            elif check_type == HealthCheckType.PERFORMANCE:
                result = await self._performance_health_check(adapter_name, adapter)
            elif check_type == HealthCheckType.COMPREHENSIVE:
                result = await self._comprehensive_health_check(adapter_name, adapter)
            else:
                result = await self._basic_health_check(adapter_name, adapter)
            
            # 计算响应时间
            end_time = datetime.now(timezone.utc)
            result.response_time = (end_time - start_time).total_seconds()
            
            # 更新统计信息
            self._update_stats(result)
            
            # 记录历史
            self._record_check_result(result)
            
            # 检查状态变化
            await self._check_status_change(adapter_name, result.status)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Health check failed for {adapter_name}: {str(e)}")
            
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds()
            
            result = HealthCheckResult(
                adapter_name=adapter_name,
                check_type=check_type,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                success=False,
                error_message=str(e),
                error_code="HEALTH_CHECK_ERROR"
            )
            
            self._update_stats(result)
            self._record_check_result(result)
            
            return result
    
    async def _basic_health_check(self, adapter_name: str, adapter: BaseAIAdapter) -> HealthCheckResult:
        """基础健康检查"""
        try:
            # 调用适配器的健康检查方法
            is_healthy = await asyncio.wait_for(
                adapter.health_check(),
                timeout=self.config.basic_timeout
            )
            
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.CRITICAL
            
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.BASIC,
                status=status,
                response_time=0.0,  # 将在外层计算
                success=is_healthy,
                api_accessible=is_healthy,
                metadata={"check_method": "adapter.health_check()"}
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.BASIC,
                status=HealthStatus.CRITICAL,
                response_time=0.0,
                success=False,
                error_message="Health check timeout",
                error_code="TIMEOUT",
                api_accessible=False
            )
    
    async def _functional_health_check(self, adapter_name: str, adapter: BaseAIAdapter) -> HealthCheckResult:
        """功能性健康检查"""
        try:
            # 创建测试请求
            test_request = AIRequest(
                messages=[
                    ChatMessage(role=MessageRole.USER, content="Hello, this is a health check test.")
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            # 发送测试请求
            response = await asyncio.wait_for(
                adapter.chat_completion(test_request),
                timeout=self.config.functional_timeout
            )
            
            # 分析响应质量
            response_quality = self._analyze_response_quality(response)
            
            # 确定健康状态
            if response.success and response_quality > 0.8:
                status = HealthStatus.HEALTHY
            elif response.success and response_quality > 0.5:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.FUNCTIONAL,
                status=status,
                response_time=0.0,
                success=response.success,
                error_message=response.error_message if not response.success else None,
                error_code=response.error_code if not response.success else None,
                api_accessible=True,
                model_available=response.success,
                response_quality=response_quality,
                latency_ms=response.response_time * 1000 if response.response_time else None,
                metadata={
                    "test_request": "functional_test",
                    "response_length": len(response.content) if response.content else 0,
                    "model": response.model if hasattr(response, 'model') else None
                }
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.FUNCTIONAL,
                status=HealthStatus.CRITICAL,
                response_time=0.0,
                success=False,
                error_message="Functional test timeout",
                error_code="TIMEOUT",
                api_accessible=False,
                model_available=False
            )
        except Exception as e:
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.FUNCTIONAL,
                status=HealthStatus.CRITICAL,
                response_time=0.0,
                success=False,
                error_message=str(e),
                error_code="FUNCTIONAL_TEST_ERROR",
                api_accessible=False,
                model_available=False
            )
    
    async def _performance_health_check(self, adapter_name: str, adapter: BaseAIAdapter) -> HealthCheckResult:
        """性能健康检查"""
        try:
            # 执行多个并发请求来测试性能
            test_requests = [
                AIRequest(
                    messages=[
                        ChatMessage(role=MessageRole.USER, content=f"Performance test {i}")
                    ],
                    max_tokens=5,
                    temperature=0.1
                )
                for i in range(3)
            ]
            
            start_time = datetime.now(timezone.utc)
            
            # 并发执行请求
            tasks = [
                asyncio.wait_for(
                    adapter.chat_completion(request),
                    timeout=self.config.performance_timeout / 3
                )
                for request in test_requests
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = datetime.now(timezone.utc)
            total_time = (end_time - start_time).total_seconds()
            
            # 分析性能指标
            successful_responses = [r for r in responses if isinstance(r, AIResponse) and r.success]
            failed_responses = [r for r in responses if not isinstance(r, AIResponse) or not r.success]
            
            success_rate = len(successful_responses) / len(responses)
            avg_latency = sum(r.response_time for r in successful_responses) / len(successful_responses) if successful_responses else 0
            throughput = len(successful_responses) / total_time if total_time > 0 else 0
            
            # 确定健康状态
            if success_rate >= 0.9 and avg_latency < self.config.warning_response_time:
                status = HealthStatus.HEALTHY
            elif success_rate >= 0.7 and avg_latency < self.config.critical_response_time:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.PERFORMANCE,
                status=status,
                response_time=total_time,
                success=success_rate > 0.5,
                api_accessible=len(responses) > 0,
                model_available=len(successful_responses) > 0,
                latency_ms=avg_latency * 1000,
                throughput=throughput,
                availability=success_rate,
                metadata={
                    "concurrent_requests": len(test_requests),
                    "successful_requests": len(successful_responses),
                    "failed_requests": len(failed_responses),
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency * 1000
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.PERFORMANCE,
                status=HealthStatus.CRITICAL,
                response_time=0.0,
                success=False,
                error_message=str(e),
                error_code="PERFORMANCE_TEST_ERROR",
                api_accessible=False,
                model_available=False
            )
    
    async def _comprehensive_health_check(self, adapter_name: str, adapter: BaseAIAdapter) -> HealthCheckResult:
        """综合健康检查"""
        try:
            # 执行所有类型的检查
            basic_result = await self._basic_health_check(adapter_name, adapter)
            functional_result = await self._functional_health_check(adapter_name, adapter)
            performance_result = await self._performance_health_check(adapter_name, adapter)
            
            # 综合评估健康状态
            status_scores = {
                HealthStatus.HEALTHY: 3,
                HealthStatus.WARNING: 2,
                HealthStatus.CRITICAL: 1,
                HealthStatus.UNKNOWN: 0
            }
            
            total_score = (
                status_scores[basic_result.status] * 0.4 +
                status_scores[functional_result.status] * 0.4 +
                status_scores[performance_result.status] * 0.2
            )
            
            if total_score >= 2.5:
                overall_status = HealthStatus.HEALTHY
            elif total_score >= 1.5:
                overall_status = HealthStatus.WARNING
            else:
                overall_status = HealthStatus.CRITICAL
            
            # 合并结果
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.COMPREHENSIVE,
                status=overall_status,
                response_time=basic_result.response_time + functional_result.response_time + performance_result.response_time,
                success=basic_result.success and functional_result.success and performance_result.success,
                api_accessible=basic_result.api_accessible,
                model_available=functional_result.model_available,
                response_quality=functional_result.response_quality,
                latency_ms=performance_result.latency_ms,
                throughput=performance_result.throughput,
                availability=performance_result.availability,
                metadata={
                    "basic_status": basic_result.status.value,
                    "functional_status": functional_result.status.value,
                    "performance_status": performance_result.status.value,
                    "overall_score": total_score
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                adapter_name=adapter_name,
                check_type=HealthCheckType.COMPREHENSIVE,
                status=HealthStatus.CRITICAL,
                response_time=0.0,
                success=False,
                error_message=str(e),
                error_code="COMPREHENSIVE_CHECK_ERROR"
            )
    
    def _analyze_response_quality(self, response: AIResponse) -> float:
        """分析响应质量"""
        if not response.success:
            return 0.0
        
        quality_score = 1.0
        
        # 检查响应内容
        if not response.content or len(response.content.strip()) == 0:
            quality_score -= 0.5
        
        # 检查响应时间
        if response.response_time > 10.0:
            quality_score -= 0.3
        elif response.response_time > 5.0:
            quality_score -= 0.1
        
        # 检查错误信息
        if response.error_message:
            quality_score -= 0.2
        
        return max(0.0, quality_score)
    
    def _update_stats(self, result: HealthCheckResult):
        """更新统计信息"""
        self.stats["total_checks"] += 1
        self.stats["last_check_time"] = result.timestamp
        
        if result.success:
            self.stats["successful_checks"] += 1
        else:
            self.stats["failed_checks"] += 1
        
        # 更新平均响应时间
        total_checks = self.stats["total_checks"]
        current_avg = self.stats["avg_response_time"]
        self.stats["avg_response_time"] = (
            (current_avg * (total_checks - 1) + result.response_time) / total_checks
        )
    
    def _record_check_result(self, result: HealthCheckResult):
        """记录检查结果"""
        adapter_name = result.adapter_name
        
        if adapter_name not in self.check_history:
            self.check_history[adapter_name] = []
        
        self.check_history[adapter_name].append(result)
        
        # 限制历史记录数量
        max_history = 1000  # 每个适配器最多保留1000条记录
        if len(self.check_history[adapter_name]) > max_history:
            self.check_history[adapter_name] = self.check_history[adapter_name][-max_history:]
    
    async def _check_status_change(self, adapter_name: str, new_status: HealthStatus):
        """检查状态变化并触发回调"""
        old_status = self.current_status.get(adapter_name, HealthStatus.UNKNOWN)
        self.current_status[adapter_name] = new_status
        
        if old_status != new_status:
            self.logger.info(f"Health status changed for {adapter_name}: {old_status.value} -> {new_status.value}")
            
            # 触发状态变化回调
            for callback in self.status_change_callbacks:
                try:
                    callback(adapter_name, old_status, new_status)
                except Exception as e:
                    self.logger.error(f"Error in status change callback: {str(e)}")
            
            # 检查是否需要发送告警
            if new_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                await self._check_alert(adapter_name, new_status)
    
    async def _check_alert(self, adapter_name: str, status: HealthStatus):
        """检查是否需要发送告警"""
        if not self.config.enable_alerts:
            return
        
        # 检查告警冷却时间
        last_alert = self.alert_history.get(adapter_name)
        if last_alert:
            time_since_last = (datetime.now(timezone.utc) - last_alert).total_seconds()
            if time_since_last < self.config.alert_cooldown:
                return
        
        # 发送告警
        self.alert_history[adapter_name] = datetime.now(timezone.utc)
        
        # 获取最新的检查结果
        if adapter_name in self.check_history and self.check_history[adapter_name]:
            latest_result = self.check_history[adapter_name][-1]
            
            # 触发告警回调
            for callback in self.alert_callbacks:
                try:
                    callback(adapter_name, latest_result)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {str(e)}")
    
    async def _basic_health_check_loop(self):
        """基础健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.basic_interval)
                
                # 检查所有适配器
                for adapter_name in self.adapter_manager.adapters.keys():
                    try:
                        await self.check_adapter_health(adapter_name, HealthCheckType.BASIC)
                    except Exception as e:
                        self.logger.error(f"Basic health check failed for {adapter_name}: {str(e)}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in basic health check loop: {str(e)}")
    
    async def _functional_health_check_loop(self):
        """功能性健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.functional_interval)
                
                # 检查所有适配器
                for adapter_name in self.adapter_manager.adapters.keys():
                    try:
                        await self.check_adapter_health(adapter_name, HealthCheckType.FUNCTIONAL)
                    except Exception as e:
                        self.logger.error(f"Functional health check failed for {adapter_name}: {str(e)}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in functional health check loop: {str(e)}")
    
    async def _performance_health_check_loop(self):
        """性能健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.performance_interval)
                
                # 检查所有适配器
                for adapter_name in self.adapter_manager.adapters.keys():
                    try:
                        await self.check_adapter_health(adapter_name, HealthCheckType.PERFORMANCE)
                    except Exception as e:
                        self.logger.error(f"Performance health check failed for {adapter_name}: {str(e)}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance health check loop: {str(e)}")
    
    async def _comprehensive_health_check_loop(self):
        """综合健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.comprehensive_interval)
                
                # 检查所有适配器
                for adapter_name in self.adapter_manager.adapters.keys():
                    try:
                        await self.check_adapter_health(adapter_name, HealthCheckType.COMPREHENSIVE)
                    except Exception as e:
                        self.logger.error(f"Comprehensive health check failed for {adapter_name}: {str(e)}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in comprehensive health check loop: {str(e)}")
    
    async def _cleanup_history_loop(self):
        """清理历史数据循环"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.history_retention_days)
                
                for adapter_name in list(self.check_history.keys()):
                    # 清理过期的历史记录
                    self.check_history[adapter_name] = [
                        result for result in self.check_history[adapter_name]
                        if result.timestamp > cutoff_time
                    ]
                    
                    # 如果没有历史记录，删除该适配器的条目
                    if not self.check_history[adapter_name]:
                        del self.check_history[adapter_name]
                
                self.logger.debug("Cleaned up health check history")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup history loop: {str(e)}")
    
    def add_status_change_callback(self, callback: Callable[[str, HealthStatus, HealthStatus], None]):
        """添加状态变化回调"""
        self.status_change_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[str, HealthCheckResult], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def get_adapter_status(self, adapter_name: str) -> Optional[HealthStatus]:
        """获取适配器当前状态"""
        return self.current_status.get(adapter_name)
    
    def get_adapter_history(self, adapter_name: str, 
                          check_type: Optional[HealthCheckType] = None,
                          limit: Optional[int] = None) -> List[HealthCheckResult]:
        """获取适配器历史记录"""
        if adapter_name not in self.check_history:
            return []
        
        history = self.check_history[adapter_name]
        
        # 按检查类型过滤
        if check_type:
            history = [result for result in history if result.check_type == check_type]
        
        # 限制数量
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        summary = {
            "total_adapters": len(self.adapter_manager.adapters),
            "healthy_adapters": 0,
            "warning_adapters": 0,
            "critical_adapters": 0,
            "unknown_adapters": 0,
            "adapters": {},
            "stats": self.stats.copy()
        }
        
        for adapter_name in self.adapter_manager.adapters.keys():
            status = self.current_status.get(adapter_name, HealthStatus.UNKNOWN)
            
            if status == HealthStatus.HEALTHY:
                summary["healthy_adapters"] += 1
            elif status == HealthStatus.WARNING:
                summary["warning_adapters"] += 1
            elif status == HealthStatus.CRITICAL:
                summary["critical_adapters"] += 1
            else:
                summary["unknown_adapters"] += 1
            
            # 获取最新的检查结果
            latest_result = None
            if adapter_name in self.check_history and self.check_history[adapter_name]:
                latest_result = self.check_history[adapter_name][-1]
            
            summary["adapters"][adapter_name] = {
                "status": status.value,
                "last_check": latest_result.timestamp.isoformat() if latest_result else None,
                "last_response_time": latest_result.response_time if latest_result else None,
                "last_error": latest_result.error_message if latest_result else None
            }
        
        return summary
    
    async def check_ai_model_health(self, model_config) -> 'AIModelHealthCheck':
        """检查AI模型健康状态"""
        from ..schemas.ai_model_config import AIModelHealthCheck, HealthStatusEnum
        
        try:
            # 模拟健康检查 - 在实际实现中应该调用真实的AI服务
            import time
            start_time = time.time()
            
            # 模拟网络延迟
            await asyncio.sleep(0.1)
            
            response_time = time.time() - start_time
            
            # 基于配置判断健康状态
            if model_config.is_enabled:
                status = HealthStatusEnum.HEALTHY
                error = None
            else:
                status = HealthStatusEnum.UNHEALTHY
                error = "Model is disabled"
            
            return AIModelHealthCheck(
                status=status,
                response_time=response_time,
                error=error
            )
            
        except Exception as e:
            return AIModelHealthCheck(
                status=HealthStatusEnum.ERROR,
                response_time=None,
                error=str(e)
            )
        
        return summary
    
    def export_health_report(self, adapter_name: Optional[str] = None, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """导出健康报告"""
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)  # 默认24小时
        
        report = {
            "report_time": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "adapters": {}
        }
        
        adapters_to_report = [adapter_name] if adapter_name else list(self.check_history.keys())
        
        for name in adapters_to_report:
            if name not in self.check_history:
                continue
            
            # 过滤时间范围内的记录
            filtered_history = [
                result for result in self.check_history[name]
                if start_time <= result.timestamp <= end_time
            ]
            
            if not filtered_history:
                continue
            
            # 计算统计信息
            total_checks = len(filtered_history)
            successful_checks = sum(1 for r in filtered_history if r.success)
            failed_checks = total_checks - successful_checks
            
            avg_response_time = sum(r.response_time for r in filtered_history) / total_checks
            
            status_counts = {}
            for status in HealthStatus:
                status_counts[status.value] = sum(1 for r in filtered_history if r.status == status)
            
            report["adapters"][name] = {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "success_rate": successful_checks / total_checks if total_checks > 0 else 0,
                "avg_response_time": avg_response_time,
                "status_distribution": status_counts,
                "current_status": self.current_status.get(name, HealthStatus.UNKNOWN).value,
                "check_history": [result.to_dict() for result in filtered_history]
            }
        
        return report