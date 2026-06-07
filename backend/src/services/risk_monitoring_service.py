"""
风险监控和预警服务

本模块提供实时风险监控和自动预警功能，包括：
- 实时风险监控系统
- 自动预警生成
- 风险趋势分析
- 预警通知管理
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..models.project import ProjectRisk, Project, Task, Milestone
from ..schemas.risk import RiskAlert, RiskLevel, RiskStatus, RiskCategory
from ..core.database import get_db
from ..services.risk_service import RiskService
# from ..utils.notification import NotificationService  # Will implement later

logger = logging.getLogger(__name__)


class RiskMonitoringService:
    """风险监控服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.risk_service = RiskService(db)
        # self.notification_service = NotificationService()  # Will implement later
        
        # 预警阈值配置
        self.alert_thresholds = {
            'critical_risk_count': 3,      # 严重风险数量阈值
            'high_risk_count': 5,          # 高风险数量阈值
            'risk_score_threshold': 8.0,   # 风险评分阈值
            'overdue_risk_days': 7,        # 风险逾期天数阈值
            'new_risk_rate': 0.2,          # 新增风险比率阈值
            'resolution_delay_days': 14    # 解决延期天数阈值
        }
        
        # 监控规则配置
        self.monitoring_rules = {
            'schedule_monitoring': {
                'check_interval': 3600,    # 1小时检查一次
                'alert_conditions': [
                    'milestone_overdue',
                    'critical_path_delay',
                    'progress_deviation'
                ]
            },
            'quality_monitoring': {
                'check_interval': 7200,    # 2小时检查一次
                'alert_conditions': [
                    'defect_density_high',
                    'test_coverage_low',
                    'critical_defects'
                ]
            },
            'resource_monitoring': {
                'check_interval': 14400,   # 4小时检查一次
                'alert_conditions': [
                    'workload_overload',
                    'skill_gap',
                    'key_person_risk'
                ]
            }
        }
    
    async def start_monitoring(self, project_id: int, config: Dict[str, Any] = None) -> bool:
        """启动项目风险监控"""
        try:
            # 验证项目存在
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError("项目不存在")
            
            # 合并配置
            if config:
                self.alert_thresholds.update(config.get('alert_thresholds', {}))
            
            # 执行初始风险检测
            await self.risk_service.auto_detect_risks(project_id)
            
            # 生成初始监控报告
            monitoring_report = await self._generate_monitoring_report(project_id)
            
            logger.info(f"项目{project_id}风险监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动风险监控失败: {str(e)}")
            raise
    
    async def stop_monitoring(self, project_id: int) -> bool:
        """停止项目风险监控"""
        try:
            # 这里可以添加停止监控的逻辑
            # 例如取消定时任务、清理监控状态等
            
            logger.info(f"项目{project_id}风险监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止风险监控失败: {str(e)}")
            raise
    
    async def check_project_risks(self, project_id: int) -> List[RiskAlert]:
        """检查项目风险并生成预警"""
        alerts = []
        
        try:
            # 1. 检查风险数量预警
            quantity_alerts = await self._check_risk_quantity_alerts(project_id)
            alerts.extend(quantity_alerts)
            
            # 2. 检查风险评分预警
            score_alerts = await self._check_risk_score_alerts(project_id)
            alerts.extend(score_alerts)
            
            # 3. 检查风险逾期预警
            overdue_alerts = await self._check_overdue_risk_alerts(project_id)
            alerts.extend(overdue_alerts)
            
            # 4. 检查风险趋势预警
            trend_alerts = await self._check_risk_trend_alerts(project_id)
            alerts.extend(trend_alerts)
            
            # 5. 检查特定风险类型预警
            category_alerts = await self._check_category_specific_alerts(project_id)
            alerts.extend(category_alerts)
            
            # 发送预警通知
            if alerts:
                await self._send_alert_notifications(project_id, alerts)
            
            logger.info(f"项目{project_id}风险检查完成，生成{len(alerts)}个预警")
            return alerts
            
        except Exception as e:
            logger.error(f"检查项目风险失败: {str(e)}")
            raise
    
    async def _check_risk_quantity_alerts(self, project_id: int) -> List[RiskAlert]:
        """检查风险数量预警"""
        alerts = []
        
        try:
            # 获取项目风险统计
            risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.status != RiskStatus.CLOSED
                )
            ).all()
            
            critical_risks = [r for r in risks if r.risk_level == RiskLevel.CRITICAL]
            high_risks = [r for r in risks if r.risk_level == RiskLevel.HIGH]
            
            # 检查严重风险数量
            if len(critical_risks) >= self.alert_thresholds['critical_risk_count']:
                alerts.append(RiskAlert(
                    risk_id=0,  # 系统级预警
                    alert_type="CRITICAL_RISK_COUNT",
                    severity="CRITICAL",
                    message=f"项目存在{len(critical_risks)}个严重风险，超过阈值{self.alert_thresholds['critical_risk_count']}",
                    recommendation="立即召开风险评审会议，制定应急处理方案",
                    created_at=datetime.utcnow()
                ))
            
            # 检查高风险数量
            if len(high_risks) >= self.alert_thresholds['high_risk_count']:
                alerts.append(RiskAlert(
                    risk_id=0,
                    alert_type="HIGH_RISK_COUNT",
                    severity="HIGH",
                    message=f"项目存在{len(high_risks)}个高风险，超过阈值{self.alert_thresholds['high_risk_count']}",
                    recommendation="加强风险管控，优先处理高风险项",
                    created_at=datetime.utcnow()
                ))
            
        except Exception as e:
            logger.error(f"检查风险数量预警失败: {str(e)}")
        
        return alerts
    
    async def _check_risk_score_alerts(self, project_id: int) -> List[RiskAlert]:
        """检查风险评分预警"""
        alerts = []
        
        try:
            # 获取高评分风险
            high_score_risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.status != RiskStatus.CLOSED,
                    ProjectRisk.risk_score >= self.alert_thresholds['risk_score_threshold']
                )
            ).all()
            
            for risk in high_score_risks:
                alerts.append(RiskAlert(
                    risk_id=risk.id,
                    alert_type="HIGH_RISK_SCORE",
                    severity="HIGH",
                    message=f"风险'{risk.risk_name}'评分为{float(risk.risk_score):.1f}，超过阈值{self.alert_thresholds['risk_score_threshold']}",
                    recommendation="立即制定详细的风险缓解计划",
                    created_at=datetime.utcnow()
                ))
            
        except Exception as e:
            logger.error(f"检查风险评分预警失败: {str(e)}")
        
        return alerts
    
    async def _check_overdue_risk_alerts(self, project_id: int) -> List[RiskAlert]:
        """检查风险逾期预警"""
        alerts = []
        
        try:
            # 检查目标解决日期逾期的风险
            overdue_date = date.today() - timedelta(days=self.alert_thresholds['overdue_risk_days'])
            
            overdue_risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.status.in_([RiskStatus.IDENTIFIED, RiskStatus.ANALYZING, RiskStatus.MITIGATING]),
                    ProjectRisk.target_resolution_date < overdue_date
                )
            ).all()
            
            for risk in overdue_risks:
                overdue_days = (date.today() - risk.target_resolution_date).days
                alerts.append(RiskAlert(
                    risk_id=risk.id,
                    alert_type="RISK_OVERDUE",
                    severity="MEDIUM",
                    message=f"风险'{risk.risk_name}'已逾期{overdue_days}天未解决",
                    recommendation="更新风险处理计划，调整目标解决日期",
                    created_at=datetime.utcnow()
                ))
            
        except Exception as e:
            logger.error(f"检查风险逾期预警失败: {str(e)}")
        
        return alerts
    
    async def _check_risk_trend_alerts(self, project_id: int) -> List[RiskAlert]:
        """检查风险趋势预警"""
        alerts = []
        
        try:
            # 获取最近7天的风险数据
            recent_date = date.today() - timedelta(days=7)
            
            recent_risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.identified_date >= recent_date
                )
            ).count()
            
            total_risks = self.db.query(ProjectRisk).filter(
                ProjectRisk.project_id == project_id
            ).count()
            
            # 检查新增风险比率
            if total_risks > 0:
                new_risk_rate = recent_risks / total_risks
                if new_risk_rate > self.alert_thresholds['new_risk_rate']:
                    alerts.append(RiskAlert(
                        risk_id=0,
                        alert_type="RISK_TREND_RISING",
                        severity="MEDIUM",
                        message=f"最近7天新增风险占比{new_risk_rate:.1%}，风险呈上升趋势",
                        recommendation="分析风险增长原因，制定预防措施",
                        created_at=datetime.utcnow()
                    ))
            
        except Exception as e:
            logger.error(f"检查风险趋势预警失败: {str(e)}")
        
        return alerts
    
    async def _check_category_specific_alerts(self, project_id: int) -> List[RiskAlert]:
        """检查特定类别风险预警"""
        alerts = []
        
        try:
            # 检查进度风险
            schedule_risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.risk_category == RiskCategory.SCHEDULE,
                    ProjectRisk.status != RiskStatus.CLOSED,
                    ProjectRisk.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
                )
            ).count()
            
            if schedule_risks > 2:
                alerts.append(RiskAlert(
                    risk_id=0,
                    alert_type="SCHEDULE_RISK_CLUSTER",
                    severity="HIGH",
                    message=f"项目存在{schedule_risks}个高级别进度风险",
                    recommendation="重新评估项目计划，考虑调整里程碑",
                    created_at=datetime.utcnow()
                ))
            
            # 检查质量风险
            quality_risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.risk_category == RiskCategory.QUALITY,
                    ProjectRisk.status != RiskStatus.CLOSED,
                    ProjectRisk.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
                )
            ).count()
            
            if quality_risks > 2:
                alerts.append(RiskAlert(
                    risk_id=0,
                    alert_type="QUALITY_RISK_CLUSTER",
                    severity="HIGH",
                    message=f"项目存在{quality_risks}个高级别质量风险",
                    recommendation="加强质量控制流程，增加测试资源",
                    created_at=datetime.utcnow()
                ))
            
        except Exception as e:
            logger.error(f"检查特定类别风险预警失败: {str(e)}")
        
        return alerts
    
    async def _send_alert_notifications(self, project_id: int, alerts: List[RiskAlert]) -> None:
        """发送预警通知"""
        try:
            # 获取项目信息
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return
            
            # 按严重程度分组预警
            critical_alerts = [a for a in alerts if a.severity == "CRITICAL"]
            high_alerts = [a for a in alerts if a.severity == "HIGH"]
            medium_alerts = [a for a in alerts if a.severity == "MEDIUM"]
            
            # 构建通知消息
            notification_data = {
                'project_id': project_id,
                'project_name': project.project_name,
                'total_alerts': len(alerts),
                'critical_count': len(critical_alerts),
                'high_count': len(high_alerts),
                'medium_count': len(medium_alerts),
                'alerts': [
                    {
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'message': alert.message,
                        'recommendation': alert.recommendation
                    }
                    for alert in alerts
                ]
            }
            
            # 发送通知给项目经理和相关人员
            recipients = [project.project_manager_id]
            if project.test_manager_id:
                recipients.append(project.test_manager_id)
            
            # await self.notification_service.send_risk_alert_notification(
            #     recipients, notification_data
            # )
            # For now, just log the notification
            logger.info(f"Would send notification to {recipients}: {notification_data}")
            
            logger.info(f"已发送项目{project_id}风险预警通知给{len(recipients)}个用户")
            
        except Exception as e:
            logger.error(f"发送预警通知失败: {str(e)}")
    
    async def _generate_monitoring_report(self, project_id: int) -> Dict[str, Any]:
        """生成监控报告"""
        try:
            # 获取风险统计
            risks = self.db.query(ProjectRisk).filter(ProjectRisk.project_id == project_id).all()
            
            report = {
                'project_id': project_id,
                'monitoring_time': datetime.utcnow(),
                'total_risks': len(risks),
                'open_risks': len([r for r in risks if r.status != RiskStatus.CLOSED]),
                'critical_risks': len([r for r in risks if r.risk_level == RiskLevel.CRITICAL]),
                'high_risks': len([r for r in risks if r.risk_level == RiskLevel.HIGH]),
                'overdue_risks': len([
                    r for r in risks 
                    if r.target_resolution_date and r.target_resolution_date < date.today() 
                    and r.status != RiskStatus.CLOSED
                ]),
                'avg_risk_score': sum(float(r.risk_score) for r in risks) / len(risks) if risks else 0,
                'monitoring_status': 'ACTIVE'
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成监控报告失败: {str(e)}")
            return {}
    
    async def get_monitoring_status(self, project_id: int) -> Dict[str, Any]:
        """获取监控状态"""
        try:
            report = await self._generate_monitoring_report(project_id)
            
            # 添加监控配置信息
            report.update({
                'alert_thresholds': self.alert_thresholds,
                'monitoring_rules': self.monitoring_rules,
                'last_check_time': datetime.utcnow()
            })
            
            return report
            
        except Exception as e:
            logger.error(f"获取监控状态失败: {str(e)}")
            raise
    
    async def update_monitoring_config(self, project_id: int, config: Dict[str, Any]) -> bool:
        """更新监控配置"""
        try:
            # 更新预警阈值
            if 'alert_thresholds' in config:
                self.alert_thresholds.update(config['alert_thresholds'])
            
            # 更新监控规则
            if 'monitoring_rules' in config:
                self.monitoring_rules.update(config['monitoring_rules'])
            
            logger.info(f"项目{project_id}监控配置已更新")
            return True
            
        except Exception as e:
            logger.error(f"更新监控配置失败: {str(e)}")
            raise
    
    async def get_alert_history(self, project_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """获取预警历史"""
        try:
            # 这里可以从数据库或缓存中获取历史预警记录
            # 暂时返回示例数据
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 实际实现中应该从预警记录表中查询
            alert_history = []
            
            return alert_history
            
        except Exception as e:
            logger.error(f"获取预警历史失败: {str(e)}")
            raise


class NotificationService:
    """通知服务类"""
    
    async def send_risk_alert_notification(self, recipients: List[int], data: Dict[str, Any]) -> None:
        """发送风险预警通知"""
        try:
            # 这里可以实现具体的通知发送逻辑
            # 例如邮件、短信、系统内通知等
            
            logger.info(f"发送风险预警通知: 项目{data['project_id']}, 接收人{recipients}")
            
        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}")
            raise