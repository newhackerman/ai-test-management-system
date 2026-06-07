"""
健康监控工具

提供健康检查的监控、告警和报告功能。
"""

import asyncio
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
import json

from ..services.health_check_service import HealthCheckService, HealthStatus, HealthCheckResult

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """告警配置"""
    # 邮件配置
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    
    # 收件人配置
    alert_recipients: List[str] = None
    
    # Webhook配置
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = None
    
    # 告警级别
    alert_on_warning: bool = True
    alert_on_critical: bool = True
    
    def __post_init__(self):
        if self.alert_recipients is None:
            self.alert_recipients = []
        if self.webhook_headers is None:
            self.webhook_headers = {}


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self, health_service: HealthCheckService, alert_config: Optional[AlertConfig] = None):
        """
        初始化健康监控器
        
        Args:
            health_service: 健康检查服务
            alert_config: 告警配置
        """
        self.health_service = health_service
        self.alert_config = alert_config or AlertConfig()
        self.logger = logging.getLogger(__name__)
        
        # 注册回调
        self.health_service.add_status_change_callback(self._on_status_change)
        self.health_service.add_alert_callback(self._on_alert)
        
        # 告警历史
        self.alert_history: List[Dict[str, Any]] = []
        
        # 监控统计
        self.monitor_stats = {
            "alerts_sent": 0,
            "emails_sent": 0,
            "webhooks_sent": 0,
            "last_alert_time": None
        }
    
    def _on_status_change(self, adapter_name: str, old_status: HealthStatus, new_status: HealthStatus):
        """状态变化回调"""
        self.logger.info(f"Health status changed for {adapter_name}: {old_status.value} -> {new_status.value}")
        
        # 记录状态变化
        change_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "adapter_name": adapter_name,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "type": "status_change"
        }
        
        self.alert_history.append(change_record)
        
        # 限制历史记录数量
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
    
    def _on_alert(self, adapter_name: str, result: HealthCheckResult):
        """告警回调"""
        self.logger.warning(f"Health alert for {adapter_name}: {result.status.value}")
        
        # 检查是否需要发送告警
        should_alert = (
            (result.status == HealthStatus.WARNING and self.alert_config.alert_on_warning) or
            (result.status == HealthStatus.CRITICAL and self.alert_config.alert_on_critical)
        )
        
        if not should_alert:
            return
        
        # 创建告警记录
        alert_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "adapter_name": adapter_name,
            "status": result.status.value,
            "check_type": result.check_type.value,
            "error_message": result.error_message,
            "response_time": result.response_time,
            "type": "alert"
        }
        
        self.alert_history.append(alert_record)
        self.monitor_stats["alerts_sent"] += 1
        self.monitor_stats["last_alert_time"] = alert_record["timestamp"]
        
        # 发送告警
        asyncio.create_task(self._send_alert(adapter_name, result))
    
    async def _send_alert(self, adapter_name: str, result: HealthCheckResult):
        """发送告警"""
        try:
            # 发送邮件告警
            if self.alert_config.smtp_server and self.alert_config.alert_recipients:
                await self._send_email_alert(adapter_name, result)
            
            # 发送Webhook告警
            if self.alert_config.webhook_url:
                await self._send_webhook_alert(adapter_name, result)
                
        except Exception as e:
            self.logger.error(f"Failed to send alert for {adapter_name}: {str(e)}")
    
    async def _send_email_alert(self, adapter_name: str, result: HealthCheckResult):
        """发送邮件告警"""
        try:
            # 创建邮件内容
            subject = f"AI Adapter Health Alert: {adapter_name} - {result.status.value.upper()}"
            
            body = self._generate_email_body(adapter_name, result)
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.alert_config.smtp_username
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            # 发送给所有收件人
            for recipient in self.alert_config.alert_recipients:
                msg['To'] = recipient
                
                # 连接SMTP服务器并发送
                with smtplib.SMTP(self.alert_config.smtp_server, self.alert_config.smtp_port) as server:
                    if self.alert_config.smtp_use_tls:
                        server.starttls()
                    
                    if self.alert_config.smtp_username and self.alert_config.smtp_password:
                        server.login(self.alert_config.smtp_username, self.alert_config.smtp_password)
                    
                    server.send_message(msg)
                
                self.logger.info(f"Email alert sent to {recipient} for {adapter_name}")
            
            self.monitor_stats["emails_sent"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")
    
    async def _send_webhook_alert(self, adapter_name: str, result: HealthCheckResult):
        """发送Webhook告警"""
        try:
            import aiohttp
            
            # 创建Webhook负载
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "adapter_name": adapter_name,
                "status": result.status.value,
                "check_type": result.check_type.value,
                "success": result.success,
                "error_message": result.error_message,
                "error_code": result.error_code,
                "response_time": result.response_time,
                "latency_ms": result.latency_ms,
                "availability": result.availability,
                "metadata": result.metadata
            }
            
            # 发送Webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.alert_config.webhook_url,
                    json=payload,
                    headers=self.alert_config.webhook_headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook alert sent for {adapter_name}")
                        self.monitor_stats["webhooks_sent"] += 1
                    else:
                        self.logger.error(f"Webhook alert failed with status {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {str(e)}")
    
    def _generate_email_body(self, adapter_name: str, result: HealthCheckResult) -> str:
        """生成邮件正文"""
        status_color = {
            HealthStatus.HEALTHY: "#28a745",
            HealthStatus.WARNING: "#ffc107", 
            HealthStatus.CRITICAL: "#dc3545",
            HealthStatus.UNKNOWN: "#6c757d"
        }
        
        color = status_color.get(result.status, "#6c757d")
        
        # 获取适配器历史状态
        history = self.health_service.get_adapter_history(adapter_name, limit=5)
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .history {{ margin: 20px 0; }}
                .history table {{ width: 100%; border-collapse: collapse; }}
                .history th, .history td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .history th {{ background-color: #f2f2f2; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>AI Adapter Health Alert</h2>
                <p>Adapter: <strong>{adapter_name}</strong></p>
                <p>Status: <strong>{result.status.value.upper()}</strong></p>
                <p>Time: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="content">
                <div class="details">
                    <h3>Alert Details</h3>
                    <p><strong>Check Type:</strong> {result.check_type.value}</p>
                    <p><strong>Success:</strong> {'Yes' if result.success else 'No'}</p>
                    <p><strong>Response Time:</strong> {result.response_time:.2f}s</p>
                    {f'<p><strong>Error:</strong> {result.error_message}</p>' if result.error_message else ''}
                    {f'<p><strong>Error Code:</strong> {result.error_code}</p>' if result.error_code else ''}
                    {f'<p><strong>Latency:</strong> {result.latency_ms:.1f}ms</p>' if result.latency_ms else ''}
                    {f'<p><strong>Availability:</strong> {result.availability:.1%}</p>' if result.availability else ''}
                </div>
                
                <div class="history">
                    <h3>Recent Health Check History</h3>
                    <table>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Response Time</th>
                            <th>Success</th>
                        </tr>
        """
        
        for h in reversed(history[-5:]):  # 最近5条记录
            html_body += f"""
                        <tr>
                            <td>{h.timestamp.strftime('%H:%M:%S')}</td>
                            <td>{h.check_type.value}</td>
                            <td style="color: {status_color.get(h.status, '#000')}">{h.status.value}</td>
                            <td>{h.response_time:.2f}s</td>
                            <td>{'✓' if h.success else '✗'}</td>
                        </tr>
            """
        
        html_body += """
                    </table>
                </div>
            </div>
            
            <div class="footer">
                <p>This is an automated alert from the AI Adapter Health Monitoring System.</p>
                <p>Please check the system dashboard for more details.</p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取告警历史"""
        history = self.alert_history.copy()
        if limit:
            history = history[-limit:]
        return history
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """获取监控统计"""
        return self.monitor_stats.copy()
    
    def generate_health_dashboard_data(self) -> Dict[str, Any]:
        """生成健康仪表板数据"""
        summary = self.health_service.get_health_summary()
        
        # 添加告警信息
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.get("type") == "alert" and
            datetime.fromisoformat(alert["timestamp"]) > datetime.now(timezone.utc) - timedelta(hours=24)
        ]
        
        dashboard_data = {
            "summary": summary,
            "recent_alerts": recent_alerts,
            "monitor_stats": self.monitor_stats,
            "alert_trends": self._calculate_alert_trends(),
            "adapter_performance": self._calculate_adapter_performance()
        }
        
        return dashboard_data
    
    def _calculate_alert_trends(self) -> Dict[str, Any]:
        """计算告警趋势"""
        now = datetime.now(timezone.utc)
        
        # 按小时统计最近24小时的告警
        hourly_alerts = {}
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_key = hour_start.strftime('%H:00')
            hourly_alerts[hour_key] = 0
            
            for alert in self.alert_history:
                if alert.get("type") == "alert":
                    alert_time = datetime.fromisoformat(alert["timestamp"])
                    if hour_start <= alert_time < hour_end:
                        hourly_alerts[hour_key] += 1
        
        # 按适配器统计告警数量
        adapter_alerts = {}
        for alert in self.alert_history:
            if alert.get("type") == "alert":
                adapter_name = alert.get("adapter_name")
                if adapter_name:
                    adapter_alerts[adapter_name] = adapter_alerts.get(adapter_name, 0) + 1
        
        return {
            "hourly_alerts": hourly_alerts,
            "adapter_alerts": adapter_alerts,
            "total_alerts_24h": len([
                a for a in self.alert_history
                if a.get("type") == "alert" and
                datetime.fromisoformat(a["timestamp"]) > now - timedelta(hours=24)
            ])
        }
    
    def _calculate_adapter_performance(self) -> Dict[str, Any]:
        """计算适配器性能指标"""
        performance = {}
        
        for adapter_name in self.health_service.adapter_manager.adapters.keys():
            history = self.health_service.get_adapter_history(adapter_name, limit=100)
            
            if not history:
                continue
            
            # 计算性能指标
            recent_history = [
                h for h in history
                if h.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
            ]
            
            if recent_history:
                avg_response_time = sum(h.response_time for h in recent_history) / len(recent_history)
                success_rate = sum(1 for h in recent_history if h.success) / len(recent_history)
                
                performance[adapter_name] = {
                    "avg_response_time": avg_response_time,
                    "success_rate": success_rate,
                    "total_checks": len(recent_history),
                    "last_check": recent_history[-1].timestamp.isoformat() if recent_history else None
                }
        
        return performance


class HealthReporter:
    """健康报告生成器"""
    
    def __init__(self, health_service: HealthCheckService):
        """
        初始化健康报告生成器
        
        Args:
            health_service: 健康检查服务
        """
        self.health_service = health_service
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """生成日报"""
        if not date:
            date = datetime.now(timezone.utc).date()
        
        start_time = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        return self.health_service.export_health_report(
            start_time=start_time,
            end_time=end_time
        )
    
    def generate_weekly_report(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """生成周报"""
        if not week_start:
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
        
        start_time = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)
        
        return self.health_service.export_health_report(
            start_time=start_time,
            end_time=end_time
        )
    
    def generate_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """生成月报"""
        now = datetime.now(timezone.utc)
        if not year:
            year = now.year
        if not month:
            month = now.month
        
        start_time = datetime(year, month, 1, tzinfo=timezone.utc)
        
        # 计算下个月的第一天
        if month == 12:
            end_time = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_time = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        return self.health_service.export_health_report(
            start_time=start_time,
            end_time=end_time
        )
    
    def export_report_to_file(self, report: Dict[str, Any], filename: str):
        """导出报告到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Health report exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to export report to {filename}: {str(e)}")
            raise
    
    def generate_html_report(self, report: Dict[str, Any]) -> str:
        """生成HTML格式的报告"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Adapter Health Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .summary { display: flex; justify-content: space-around; margin: 20px 0; }
                .metric { text-align: center; padding: 15px; background-color: #e9ecef; border-radius: 5px; }
                .adapter-section { margin: 20px 0; }
                .adapter-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0; }
                .status-healthy { color: #28a745; }
                .status-warning { color: #ffc107; }
                .status-critical { color: #dc3545; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
        """
        
        # 报告头部
        html += f"""
            <div class="header">
                <h1>AI Adapter Health Report</h1>
                <p><strong>Report Time:</strong> {report['report_time']}</p>
                <p><strong>Period:</strong> {report['period']['start']} to {report['period']['end']}</p>
            </div>
        """
        
        # 适配器详情
        html += '<div class="adapter-section">'
        for adapter_name, adapter_data in report['adapters'].items():
            status_class = f"status-{adapter_data['current_status']}"
            
            html += f"""
                <div class="adapter-card">
                    <h3>{adapter_name}</h3>
                    <p><strong>Current Status:</strong> <span class="{status_class}">{adapter_data['current_status'].upper()}</span></p>
                    <p><strong>Total Checks:</strong> {adapter_data['total_checks']}</p>
                    <p><strong>Success Rate:</strong> {adapter_data['success_rate']:.1%}</p>
                    <p><strong>Average Response Time:</strong> {adapter_data['avg_response_time']:.2f}s</p>
                </div>
            """
        
        html += '</div>'
        html += '</body></html>'
        
        return html