"""
测试质量监控服务

提供实时的测试质量监控、告警和持续改进建议
"""
import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class MetricType(Enum):
    """指标类型"""
    SUCCESS_RATE = "success_rate"
    COVERAGE_RATE = "coverage_rate"
    EXECUTION_TIME = "execution_time"
    FAILURE_COUNT = "failure_count"
    QUALITY_SCORE = "quality_score"

@dataclass
class QualityMetric:
    """质量指标"""
    metric_type: MetricType
    current_value: float
    previous_value: float
    threshold: float
    trend: str  # 'improving', 'stable', 'declining'
    timestamp: datetime
    
    @property
    def change_percent(self) -> float:
        if self.previous_value == 0:
            return 0.0
        return ((self.current_value - self.previous_value) / self.previous_value) * 100
    
    @property
    def is_above_threshold(self) -> bool:
        return self.current_value >= self.threshold

@dataclass
class QualityAlert:
    """质量告警"""
    alert_id: str
    level: AlertLevel
    metric_type: MetricType
    title: str
    description: str
    current_value: float
    threshold: float
    timestamp: datetime
    is_resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class QualityDashboard:
    """质量仪表板数据"""
    timestamp: datetime
    overall_health: str  # 'healthy', 'warning', 'critical'
    metrics: List[QualityMetric]
    active_alerts: List[QualityAlert]
    trends: Dict[str, List[float]]
    recommendations: List[str]
    sla_status: Dict[str, bool]

class TestQualityMonitor:
    """测试质量监控器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # 监控数据库
        self.db_path = self.reports_dir / "quality_monitoring.db"
        self._init_monitoring_db()
        
        # 质量阈值配置
        self.thresholds = {
            MetricType.SUCCESS_RATE: 90.0,
            MetricType.COVERAGE_RATE: 80.0,
            MetricType.EXECUTION_TIME: 300.0,  # 5分钟
            MetricType.FAILURE_COUNT: 5,
            MetricType.QUALITY_SCORE: 75.0
        }
        
        # SLA配置
        self.sla_targets = {
            'daily_success_rate': 95.0,
            'weekly_coverage_rate': 85.0,
            'monthly_quality_score': 80.0,
            'max_critical_alerts': 0,
            'max_resolution_time_hours': 24
        }
        
        # 通知配置
        self.notification_config = {
            'email_enabled': False,
            'slack_enabled': False,
            'webhook_enabled': False
        }
    
    def _init_monitoring_db(self):
        """初始化监控数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 质量指标表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT
                )
            """)
            
            # 质量告警表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_alerts (
                    id TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_resolved BOOLEAN DEFAULT FALSE,
                    resolution_time DATETIME,
                    metadata TEXT
                )
            """)
            
            # SLA跟踪表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sla_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sla_name TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    actual_value REAL NOT NULL,
                    is_met BOOLEAN NOT NULL,
                    period_start DATETIME NOT NULL,
                    period_end DATETIME NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            # 监控配置表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)
    
    async def collect_metrics(self) -> List[QualityMetric]:
        """收集质量指标"""
        logger.info("收集测试质量指标...")
        
        metrics = []
        
        try:
            # 从测试报告数据库获取最新数据
            test_reports_db = self.reports_dir / "test_reports.db"
            
            if test_reports_db.exists():
                with sqlite3.connect(test_reports_db) as conn:
                    # 获取最近两次的报告数据
                    cursor = conn.execute("""
                        SELECT overall_success_rate, overall_coverage_rate, 
                               execution_time, quality_score, timestamp
                        FROM test_reports 
                        ORDER BY timestamp DESC 
                        LIMIT 2
                    """)
                    
                    reports = cursor.fetchall()
                    
                    if reports:
                        current_report = reports[0]
                        previous_report = reports[1] if len(reports) > 1 else current_report
                        
                        # 成功率指标
                        metrics.append(QualityMetric(
                            metric_type=MetricType.SUCCESS_RATE,
                            current_value=current_report[0],
                            previous_value=previous_report[0],
                            threshold=self.thresholds[MetricType.SUCCESS_RATE],
                            trend=self._calculate_trend(current_report[0], previous_report[0]),
                            timestamp=datetime.fromisoformat(current_report[4])
                        ))
                        
                        # 覆盖率指标
                        metrics.append(QualityMetric(
                            metric_type=MetricType.COVERAGE_RATE,
                            current_value=current_report[1],
                            previous_value=previous_report[1],
                            threshold=self.thresholds[MetricType.COVERAGE_RATE],
                            trend=self._calculate_trend(current_report[1], previous_report[1]),
                            timestamp=datetime.fromisoformat(current_report[4])
                        ))
                        
                        # 执行时间指标
                        metrics.append(QualityMetric(
                            metric_type=MetricType.EXECUTION_TIME,
                            current_value=current_report[2],
                            previous_value=previous_report[2],
                            threshold=self.thresholds[MetricType.EXECUTION_TIME],
                            trend=self._calculate_trend(previous_report[2], current_report[2]),  # 时间越短越好
                            timestamp=datetime.fromisoformat(current_report[4])
                        ))
                        
                        # 质量评分指标
                        metrics.append(QualityMetric(
                            metric_type=MetricType.QUALITY_SCORE,
                            current_value=current_report[3],
                            previous_value=previous_report[3],
                            threshold=self.thresholds[MetricType.QUALITY_SCORE],
                            trend=self._calculate_trend(current_report[3], previous_report[3]),
                            timestamp=datetime.fromisoformat(current_report[4])
                        ))
            
            # 保存指标到监控数据库
            await self._save_metrics(metrics)
            
            logger.info(f"收集了{len(metrics)}个质量指标")
            return metrics
            
        except Exception as e:
            logger.error(f"收集质量指标失败: {e}")
            return []
    
    def _calculate_trend(self, current: float, previous: float) -> str:
        """计算趋势"""
        if previous == 0:
            return 'stable'
        
        change_percent = ((current - previous) / previous) * 100
        
        if change_percent > 5:
            return 'improving'
        elif change_percent < -5:
            return 'declining'
        else:
            return 'stable'
    
    async def _save_metrics(self, metrics: List[QualityMetric]):
        """保存指标到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for metric in metrics:
                    conn.execute("""
                        INSERT INTO quality_metrics 
                        (metric_type, value, threshold, timestamp, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        metric.metric_type.value,
                        metric.current_value,
                        metric.threshold,
                        metric.timestamp.isoformat(),
                        json.dumps({
                            'previous_value': metric.previous_value,
                            'trend': metric.trend,
                            'change_percent': metric.change_percent
                        })
                    ))
        except Exception as e:
            logger.error(f"保存指标失败: {e}")
    
    async def check_alerts(self, metrics: List[QualityMetric]) -> List[QualityAlert]:
        """检查告警"""
        logger.info("检查质量告警...")
        
        alerts = []
        
        for metric in metrics:
            # 检查阈值告警
            if not metric.is_above_threshold:
                alert_level = self._determine_alert_level(metric)
                
                alert = QualityAlert(
                    alert_id=f"{metric.metric_type.value}_{int(metric.timestamp.timestamp())}",
                    level=alert_level,
                    metric_type=metric.metric_type,
                    title=f"{metric.metric_type.value.replace('_', ' ').title()} 低于阈值",
                    description=f"当前值 {metric.current_value:.1f} 低于阈值 {metric.threshold:.1f}",
                    current_value=metric.current_value,
                    threshold=metric.threshold,
                    timestamp=metric.timestamp
                )
                
                alerts.append(alert)
            
            # 检查趋势告警
            if metric.trend == 'declining' and metric.change_percent < -10:
                alert = QualityAlert(
                    alert_id=f"{metric.metric_type.value}_trend_{int(metric.timestamp.timestamp())}",
                    level=AlertLevel.WARNING,
                    metric_type=metric.metric_type,
                    title=f"{metric.metric_type.value.replace('_', ' ').title()} 呈下降趋势",
                    description=f"指标下降了 {abs(metric.change_percent):.1f}%",
                    current_value=metric.current_value,
                    threshold=metric.threshold,
                    timestamp=metric.timestamp
                )
                
                alerts.append(alert)
        
        # 保存告警
        await self._save_alerts(alerts)
        
        # 发送通知
        await self._send_alert_notifications(alerts)
        
        logger.info(f"检查到{len(alerts)}个告警")
        return alerts
    
    def _determine_alert_level(self, metric: QualityMetric) -> AlertLevel:
        """确定告警级别"""
        deviation_percent = ((metric.threshold - metric.current_value) / metric.threshold) * 100
        
        if deviation_percent > 20:
            return AlertLevel.CRITICAL
        elif deviation_percent > 10:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    async def _save_alerts(self, alerts: List[QualityAlert]):
        """保存告警到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for alert in alerts:
                    # 检查是否已存在相同告警
                    cursor = conn.execute("""
                        SELECT id FROM quality_alerts 
                        WHERE metric_type = ? AND is_resolved = FALSE
                        AND timestamp > datetime('now', '-1 hour')
                    """, (alert.metric_type.value,))
                    
                    if not cursor.fetchone():
                        conn.execute("""
                            INSERT INTO quality_alerts 
                            (id, level, metric_type, title, description, 
                             current_value, threshold, timestamp, is_resolved)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            alert.alert_id,
                            alert.level.value,
                            alert.metric_type.value,
                            alert.title,
                            alert.description,
                            alert.current_value,
                            alert.threshold,
                            alert.timestamp.isoformat(),
                            alert.is_resolved
                        ))
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    async def _send_alert_notifications(self, alerts: List[QualityAlert]):
        """发送告警通知"""
        if not alerts:
            return
        
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]
        
        # 发送邮件通知
        if self.notification_config.get('email_enabled'):
            await self._send_email_notification(critical_alerts, warning_alerts)
        
        # 发送Slack通知
        if self.notification_config.get('slack_enabled'):
            await self._send_slack_notification(critical_alerts, warning_alerts)
        
        # 发送Webhook通知
        if self.notification_config.get('webhook_enabled'):
            await self._send_webhook_notification(critical_alerts, warning_alerts)
    
    async def _send_email_notification(self, critical_alerts: List[QualityAlert], 
                                     warning_alerts: List[QualityAlert]):
        """发送邮件通知"""
        try:
            # 这里需要配置SMTP设置
            # 示例实现
            pass
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
    
    async def _send_slack_notification(self, critical_alerts: List[QualityAlert], 
                                     warning_alerts: List[QualityAlert]):
        """发送Slack通知"""
        try:
            # 这里需要配置Slack Webhook
            # 示例实现
            pass
        except Exception as e:
            logger.error(f"发送Slack通知失败: {e}")
    
    async def _send_webhook_notification(self, critical_alerts: List[QualityAlert], 
                                       warning_alerts: List[QualityAlert]):
        """发送Webhook通知"""
        try:
            # 这里需要配置Webhook URL
            # 示例实现
            pass
        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
    
    async def track_sla(self) -> Dict[str, bool]:
        """跟踪SLA"""
        logger.info("跟踪SLA指标...")
        
        sla_status = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查日成功率SLA
                cursor = conn.execute("""
                    SELECT AVG(value) FROM quality_metrics 
                    WHERE metric_type = 'success_rate' 
                    AND timestamp > datetime('now', '-1 day')
                """)
                
                daily_success_rate = cursor.fetchone()[0] or 0
                sla_status['daily_success_rate'] = daily_success_rate >= self.sla_targets['daily_success_rate']
                
                # 检查周覆盖率SLA
                cursor = conn.execute("""
                    SELECT AVG(value) FROM quality_metrics 
                    WHERE metric_type = 'coverage_rate' 
                    AND timestamp > datetime('now', '-7 days')
                """)
                
                weekly_coverage_rate = cursor.fetchone()[0] or 0
                sla_status['weekly_coverage_rate'] = weekly_coverage_rate >= self.sla_targets['weekly_coverage_rate']
                
                # 检查月质量评分SLA
                cursor = conn.execute("""
                    SELECT AVG(value) FROM quality_metrics 
                    WHERE metric_type = 'quality_score' 
                    AND timestamp > datetime('now', '-30 days')
                """)
                
                monthly_quality_score = cursor.fetchone()[0] or 0
                sla_status['monthly_quality_score'] = monthly_quality_score >= self.sla_targets['monthly_quality_score']
                
                # 检查关键告警SLA
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM quality_alerts 
                    WHERE level = 'critical' 
                    AND is_resolved = FALSE
                """)
                
                critical_alerts_count = cursor.fetchone()[0] or 0
                sla_status['max_critical_alerts'] = critical_alerts_count <= self.sla_targets['max_critical_alerts']
                
                # 保存SLA跟踪记录
                await self._save_sla_tracking(sla_status, {
                    'daily_success_rate': daily_success_rate,
                    'weekly_coverage_rate': weekly_coverage_rate,
                    'monthly_quality_score': monthly_quality_score,
                    'critical_alerts_count': critical_alerts_count
                })
            
            logger.info(f"SLA跟踪完成: {sum(sla_status.values())}/{len(sla_status)} 达标")
            return sla_status
            
        except Exception as e:
            logger.error(f"SLA跟踪失败: {e}")
            return {}
    
    async def _save_sla_tracking(self, sla_status: Dict[str, bool], actual_values: Dict[str, float]):
        """保存SLA跟踪记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for sla_name, is_met in sla_status.items():
                    target_value = self.sla_targets.get(sla_name, 0)
                    actual_value = actual_values.get(sla_name, 0)
                    
                    conn.execute("""
                        INSERT INTO sla_tracking 
                        (sla_name, target_value, actual_value, is_met, 
                         period_start, period_end, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sla_name,
                        target_value,
                        actual_value,
                        is_met,
                        (datetime.now() - timedelta(days=1)).isoformat(),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
        except Exception as e:
            logger.error(f"保存SLA跟踪记录失败: {e}")
    
    async def generate_dashboard(self) -> QualityDashboard:
        """生成质量仪表板"""
        logger.info("生成质量仪表板...")
        
        try:
            # 收集指标
            metrics = await self.collect_metrics()
            
            # 检查告警
            alerts = await self.check_alerts(metrics)
            
            # 跟踪SLA
            sla_status = await self.track_sla()
            
            # 获取趋势数据
            trends = await self._get_trends_data()
            
            # 生成建议
            recommendations = self._generate_recommendations(metrics, alerts, sla_status)
            
            # 确定整体健康状态
            overall_health = self._determine_overall_health(metrics, alerts, sla_status)
            
            dashboard = QualityDashboard(
                timestamp=datetime.now(),
                overall_health=overall_health,
                metrics=metrics,
                active_alerts=[a for a in alerts if not a.is_resolved],
                trends=trends,
                recommendations=recommendations,
                sla_status=sla_status
            )
            
            # 保存仪表板数据
            await self._save_dashboard(dashboard)
            
            logger.info(f"质量仪表板生成完成，整体健康状态: {overall_health}")
            return dashboard
            
        except Exception as e:
            logger.error(f"生成质量仪表板失败: {e}")
            raise
    
    async def _get_trends_data(self) -> Dict[str, List[float]]:
        """获取趋势数据"""
        trends = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for metric_type in MetricType:
                    cursor = conn.execute("""
                        SELECT value FROM quality_metrics 
                        WHERE metric_type = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 30
                    """, (metric_type.value,))
                    
                    values = [row[0] for row in cursor.fetchall()]
                    trends[metric_type.value] = list(reversed(values))
        
        except Exception as e:
            logger.error(f"获取趋势数据失败: {e}")
        
        return trends
    
    def _generate_recommendations(self, metrics: List[QualityMetric], 
                                alerts: List[QualityAlert], 
                                sla_status: Dict[str, bool]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于指标的建议
        for metric in metrics:
            if not metric.is_above_threshold:
                if metric.metric_type == MetricType.SUCCESS_RATE:
                    recommendations.append("🔧 测试成功率低，建议检查失败的测试用例并修复")
                elif metric.metric_type == MetricType.COVERAGE_RATE:
                    recommendations.append("📊 代码覆盖率不足，建议增加测试用例")
                elif metric.metric_type == MetricType.EXECUTION_TIME:
                    recommendations.append("⏱️ 测试执行时间过长，建议优化测试性能")
                elif metric.metric_type == MetricType.QUALITY_SCORE:
                    recommendations.append("📈 质量评分偏低，建议全面提升测试质量")
            
            if metric.trend == 'declining':
                recommendations.append(f"📉 {metric.metric_type.value.replace('_', ' ').title()} 呈下降趋势，需要关注")
        
        # 基于告警的建议
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            recommendations.append(f"🚨 有{len(critical_alerts)}个关键告警需要立即处理")
        
        # 基于SLA的建议
        failed_slas = [name for name, status in sla_status.items() if not status]
        if failed_slas:
            recommendations.append(f"📋 {len(failed_slas)}个SLA未达标，需要制定改进计划")
        
        # 积极建议
        if not recommendations:
            recommendations.append("✅ 测试质量良好，继续保持！")
            recommendations.append("🚀 可以考虑提升测试自动化程度")
        
        return recommendations
    
    def _determine_overall_health(self, metrics: List[QualityMetric], 
                                alerts: List[QualityAlert], 
                                sla_status: Dict[str, bool]) -> str:
        """确定整体健康状态"""
        # 检查关键告警
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        if critical_alerts:
            return 'critical'
        
        # 检查SLA
        failed_slas = [name for name, status in sla_status.items() if not status]
        if len(failed_slas) > len(sla_status) / 2:
            return 'critical'
        elif failed_slas:
            return 'warning'
        
        # 检查指标
        failed_metrics = [m for m in metrics if not m.is_above_threshold]
        if len(failed_metrics) > len(metrics) / 2:
            return 'critical'
        elif failed_metrics:
            return 'warning'
        
        return 'healthy'
    
    async def _save_dashboard(self, dashboard: QualityDashboard):
        """保存仪表板数据"""
        try:
            dashboard_file = self.reports_dir / f"quality_dashboard_{dashboard.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            dashboard_dict = asdict(dashboard)
            dashboard_dict['timestamp'] = dashboard.timestamp.isoformat()
            
            # 转换枚举类型
            for metric in dashboard_dict['metrics']:
                metric['metric_type'] = metric['metric_type'].value
                metric['timestamp'] = datetime.fromisoformat(metric['timestamp']).isoformat()
            
            for alert in dashboard_dict['active_alerts']:
                alert['level'] = alert['level'].value
                alert['metric_type'] = alert['metric_type'].value
                alert['timestamp'] = datetime.fromisoformat(alert['timestamp']).isoformat()
            
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"质量仪表板已保存: {dashboard_file}")
            
        except Exception as e:
            logger.error(f"保存质量仪表板失败: {e}")
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE quality_alerts 
                    SET is_resolved = TRUE, resolution_time = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), alert_id))
                
                if cursor.rowcount > 0:
                    logger.info(f"告警已解决: {alert_id}")
                    return True
                else:
                    logger.warning(f"未找到告警: {alert_id}")
                    return False
        
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False
    
    async def get_quality_report(self, days: int = 7) -> Dict[str, Any]:
        """获取质量报告"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取指标统计
                cursor = conn.execute("""
                    SELECT metric_type, AVG(value), MIN(value), MAX(value), COUNT(*)
                    FROM quality_metrics 
                    WHERE timestamp > datetime('now', '-{} days')
                    GROUP BY metric_type
                """.format(days))
                
                metrics_stats = {}
                for row in cursor.fetchall():
                    metrics_stats[row[0]] = {
                        'average': row[1],
                        'minimum': row[2],
                        'maximum': row[3],
                        'count': row[4]
                    }
                
                # 获取告警统计
                cursor = conn.execute("""
                    SELECT level, COUNT(*) 
                    FROM quality_alerts 
                    WHERE timestamp > datetime('now', '-{} days')
                    GROUP BY level
                """.format(days))
                
                alerts_stats = {}
                for row in cursor.fetchall():
                    alerts_stats[row[0]] = row[1]
                
                # 获取SLA统计
                cursor = conn.execute("""
                    SELECT sla_name, AVG(CASE WHEN is_met THEN 1.0 ELSE 0.0 END) * 100
                    FROM sla_tracking 
                    WHERE timestamp > datetime('now', '-{} days')
                    GROUP BY sla_name
                """.format(days))
                
                sla_stats = {}
                for row in cursor.fetchall():
                    sla_stats[row[0]] = row[1]
                
                report = {
                    'period_days': days,
                    'generated_at': datetime.now().isoformat(),
                    'metrics_statistics': metrics_stats,
                    'alerts_statistics': alerts_stats,
                    'sla_statistics': sla_stats
                }
                
                return report
        
        except Exception as e:
            logger.error(f"获取质量报告失败: {e}")
            return {}
    
    async def start_monitoring(self, interval_minutes: int = 30):
        """启动持续监控"""
        logger.info(f"启动测试质量监控，间隔: {interval_minutes}分钟")
        
        while True:
            try:
                # 生成仪表板
                dashboard = await self.generate_dashboard()
                
                # 记录监控日志
                logger.info(f"监控完成 - 健康状态: {dashboard.overall_health}, "
                          f"活跃告警: {len(dashboard.active_alerts)}")
                
                # 等待下次监控
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试


# 全局监控器实例
test_quality_monitor = TestQualityMonitor()