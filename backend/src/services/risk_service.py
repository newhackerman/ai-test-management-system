"""
项目风险管理服务

本模块提供项目风险管理的核心功能，包括：
- 智能风险识别和评估
- 风险监控和预警
- 风险分析和报告
- 风险应对策略管理
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from ..models.project import ProjectRisk, Project, Task, Milestone, WorkLog
from ..models.system_notification import SystemNotification
from ..models.user import User
from ..schemas.risk import (
    CreateRiskRequest, UpdateRiskRequest, RiskResponse, RiskListQuery,
    RiskAnalysisResponse, RiskMetrics, RiskCategoryAnalysis, RiskAlert,
    AutoRiskDetectionResult, RiskTrendData, RiskTrendResponse,
    RiskCategory, RiskLevel, RiskStatus, MitigationStrategy
)
from ..core.database import get_db
from ..utils.error_responses import validation_error, not_found_error

logger = logging.getLogger(__name__)


class RiskService:
    """风险管理服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 风险检测规则配置
        self.risk_detection_rules = {
            'schedule_risk': {
                'delay_threshold': 0.15,  # 延期超过15%触发风险
                'critical_path_delay': 0.10,  # 关键路径延期10%
                'milestone_overdue': 1  # 里程碑逾期1天
            },
            'quality_risk': {
                'defect_density_threshold': 2.0,  # 缺陷密度>2个/KLOC
                'test_coverage_threshold': 0.80,  # 测试覆盖率<80%
                'critical_defects_threshold': 5  # 严重缺陷>5个
            },
            'resource_risk': {
                'key_person_absence': 3,  # 关键人员缺席>3天
                'workload_threshold': 1.5,  # 工作负载>150%
                'skill_gap_threshold': 0.3  # 技能缺口>30%
            },
            'technical_risk': {
                'complexity_threshold': 0.8,  # 技术复杂度>80%
                'dependency_risk': 5,  # 外部依赖>5个
                'integration_failure_rate': 0.2  # 集成失败率>20%
            }
        }
    
    async def create_risk(self, risk_data: CreateRiskRequest, creator_id: int) -> RiskResponse:
        """创建项目风险"""
        try:
            # 验证项目存在
            project = self.db.query(Project).filter(Project.id == risk_data.project_id).first()
            self._validate_owner(risk_data.owner_id)
            if not project:
                raise not_found_error("项目不存在")
            
            # 计算风险评分
            risk_score = self._calculate_risk_score(risk_data.probability, risk_data.impact_score)
            
            # 创建风险记录
            risk = ProjectRisk(
                project_id=risk_data.project_id,
                risk_name=risk_data.risk_name,
                description=risk_data.description,
                risk_category=risk_data.risk_category,
                risk_level=risk_data.risk_level,
                probability=risk_data.probability,
                impact_score=risk_data.impact_score,
                risk_score=risk_score,
                mitigation_strategy=risk_data.mitigation_strategy,
                mitigation_plan=risk_data.mitigation_plan,
                contingency_plan=risk_data.contingency_plan,
                owner_id=risk_data.owner_id,
                identified_date=date.today(),
                target_resolution_date=risk_data.target_resolution_date,
                created_by=creator_id
            )
            
            self.db.add(risk)
            self.db.commit()
            self.db.refresh(risk)
            
            # 更新项目风险等级
            await self._update_project_risk_level(risk_data.project_id)
            self._send_owner_notification(
                risk=risk,
                sender_id=creator_id,
                project_name=project.project_name or f"项目#{project.id}",
                changed=True,
            )
            
            logger.info(f"创建风险成功: {risk.id} - {risk.risk_name}")
            return RiskResponse.from_orm(risk)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建风险失败: {str(e)}")
            raise
    
    async def update_risk(self, risk_id: int, risk_data: UpdateRiskRequest, updater_id: int) -> RiskResponse:
        """更新项目风险"""
        try:
            risk = self.db.query(ProjectRisk).filter(ProjectRisk.id == risk_id).first()
            old_owner_id = risk.owner_id if risk else None
            if not risk:
                raise not_found_error("风险不存在")
            
            # 更新字段
            update_fields = risk_data.dict(exclude_unset=True)
            if "owner_id" in update_fields and update_fields["owner_id"]:
                self._validate_owner(update_fields["owner_id"])
            for field, value in update_fields.items():
                setattr(risk, field, value)
            
            # 重新计算风险评分
            if 'probability' in update_fields or 'impact_score' in update_fields:
                risk.risk_score = self._calculate_risk_score(risk.probability, risk.impact_score)
            
            # 设置实际解决日期
            if risk_data.status == RiskStatus.CLOSED and not risk.actual_resolution_date:
                risk.actual_resolution_date = date.today()
            
            risk.updated_by = updater_id
            
            self.db.commit()
            self.db.refresh(risk)
            
            # 更新项目风险等级
            await self._update_project_risk_level(risk.project_id)
            if risk.owner_id and int(risk.owner_id) != int(old_owner_id or 0):
                project = self.db.query(Project).filter(Project.id == risk.project_id).first()
                self._send_owner_notification(
                    risk=risk,
                    sender_id=updater_id,
                    project_name=(project.project_name if project else None) or f"项目#{risk.project_id}",
                    changed=True,
                )
            
            logger.info(f"更新风险成功: {risk.id}")
            return RiskResponse.from_orm(risk)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新风险失败: {str(e)}")
            raise
    
    async def get_risk(self, risk_id: int) -> RiskResponse:
        """获取风险详情"""
        risk = self.db.query(ProjectRisk).filter(ProjectRisk.id == risk_id).first()
        if not risk:
            raise not_found_error("风险不存在")
        
        return RiskResponse.from_orm(risk)
    
    async def list_risks(self, query: RiskListQuery) -> Dict[str, Any]:
        """获取风险列表"""
        # 构建查询条件
        filters = []
        if query.project_id:
            filters.append(ProjectRisk.project_id == query.project_id)
        if getattr(query, "search", None):
            keyword = f"%{query.search.strip()}%"
            filters.append(
                or_(
                    ProjectRisk.risk_name.ilike(keyword),
                    ProjectRisk.description.ilike(keyword),
                    ProjectRisk.mitigation_plan.ilike(keyword),
                    ProjectRisk.contingency_plan.ilike(keyword),
                )
            )
        if query.risk_category:
            filters.append(ProjectRisk.risk_category == query.risk_category)
        if query.risk_level:
            filters.append(ProjectRisk.risk_level == query.risk_level)
        if query.status:
            filters.append(ProjectRisk.status == query.status)
        if query.owner_id:
            filters.append(ProjectRisk.owner_id == query.owner_id)
        
        # 构建基础查询
        base_query = self.db.query(ProjectRisk)
        if filters:
            base_query = base_query.filter(and_(*filters))
        
        # 获取总数
        total = base_query.count()
        
        # 排序
        if query.sort_by:
            sort_column = getattr(ProjectRisk, query.sort_by, None)
            if sort_column:
                if query.sort_order == "desc":
                    base_query = base_query.order_by(desc(sort_column))
                else:
                    base_query = base_query.order_by(asc(sort_column))
        
        # 分页
        offset = (query.page - 1) * query.page_size
        risks = base_query.offset(offset).limit(query.page_size).all()
        
        # 计算总页数
        total_pages = (total + query.page_size - 1) // query.page_size
        
        return {
            "risks": [RiskResponse.from_orm(risk) for risk in risks],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "total_pages": total_pages
        }
    
    async def delete_risk(self, risk_id: int) -> bool:
        """删除风险"""
        try:
            risk = self.db.query(ProjectRisk).filter(ProjectRisk.id == risk_id).first()
            if not risk:
                raise not_found_error("风险不存在")
            
            project_id = risk.project_id
            self.db.delete(risk)
            self.db.commit()
            
            # 更新项目风险等级
            await self._update_project_risk_level(project_id)
            
            logger.info(f"删除风险成功: {risk_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除风险失败: {str(e)}")
            raise
    
    async def auto_detect_risks(self, project_id: int) -> AutoRiskDetectionResult:
        """自动检测项目风险"""
        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise not_found_error("项目不存在")
            
            detected_risks = []
            risk_indicators = {}
            recommendations = []
            
            # 1. 检测进度风险
            schedule_risks = await self._detect_schedule_risks(project_id)
            detected_risks.extend(schedule_risks['risks'])
            risk_indicators.update(schedule_risks['indicators'])
            recommendations.extend(schedule_risks['recommendations'])
            
            # 2. 检测质量风险
            quality_risks = await self._detect_quality_risks(project_id)
            detected_risks.extend(quality_risks['risks'])
            risk_indicators.update(quality_risks['indicators'])
            recommendations.extend(quality_risks['recommendations'])
            
            # 3. 检测资源风险
            resource_risks = await self._detect_resource_risks(project_id)
            detected_risks.extend(resource_risks['risks'])
            risk_indicators.update(resource_risks['indicators'])
            recommendations.extend(resource_risks['recommendations'])
            
            # 4. 检测技术风险
            technical_risks = await self._detect_technical_risks(project_id)
            detected_risks.extend(technical_risks['risks'])
            risk_indicators.update(technical_risks['indicators'])
            recommendations.extend(technical_risks['recommendations'])
            
            # 5. 自动创建高风险项
            for risk_data in detected_risks:
                if risk_data.get('auto_create', False) and risk_data.get('risk_level') in ['HIGH', 'CRITICAL']:
                    await self._auto_create_risk(project_id, risk_data)
            
            result = AutoRiskDetectionResult(
                project_id=project_id,
                detection_time=datetime.utcnow(),
                detected_risks=detected_risks,
                risk_indicators=risk_indicators,
                recommendations=list(set(recommendations))  # 去重
            )
            
            logger.info(f"自动风险检测完成: 项目{project_id}, 检测到{len(detected_risks)}个风险")
            return result
            
        except Exception as e:
            logger.error(f"自动风险检测失败: {str(e)}")
            raise
    
    async def _detect_schedule_risks(self, project_id: int) -> Dict[str, Any]:
        """检测进度风险"""
        risks = []
        indicators = {}
        recommendations = []
        
        try:
            # 获取项目信息
            project = self.db.query(Project).filter(Project.id == project_id).first()
            
            # 1. 检查项目整体进度偏差
            if project.planned_end_date and project.progress_percentage:
                days_passed = (date.today() - project.planned_start_date).days if project.planned_start_date else 0
                total_days = (project.planned_end_date - project.planned_start_date).days if project.planned_start_date else 1
                expected_progress = (days_passed / total_days) * 100 if total_days > 0 else 0
                progress_deviation = expected_progress - float(project.progress_percentage)
                
                indicators['progress_deviation'] = progress_deviation
                
                if progress_deviation > self.risk_detection_rules['schedule_risk']['delay_threshold'] * 100:
                    risks.append({
                        'risk_name': '项目进度延期风险',
                        'description': f'项目进度落后预期{progress_deviation:.1f}%',
                        'risk_category': 'SCHEDULE',
                        'risk_level': 'HIGH' if progress_deviation > 25 else 'MEDIUM',
                        'probability': min(0.8, progress_deviation / 100),
                        'impact_score': 8 if progress_deviation > 25 else 6,
                        'auto_create': True
                    })
                    recommendations.append('调整资源分配，优化任务安排')
                    recommendations.append('重新评估项目计划和里程碑')
            
            # 2. 检查里程碑逾期
            overdue_milestones = self.db.query(Milestone).filter(
                and_(
                    Milestone.project_id == project_id,
                    Milestone.planned_date < date.today(),
                    Milestone.status.in_(['PENDING', 'IN_PROGRESS'])
                )
            ).count()
            
            indicators['overdue_milestones'] = overdue_milestones
            
            if overdue_milestones > 0:
                risks.append({
                    'risk_name': '里程碑逾期风险',
                    'description': f'有{overdue_milestones}个里程碑已逾期',
                    'risk_category': 'SCHEDULE',
                    'risk_level': 'CRITICAL' if overdue_milestones > 2 else 'HIGH',
                    'probability': 0.9,
                    'impact_score': min(10, 6 + overdue_milestones),
                    'auto_create': True
                })
                recommendations.append('立即评估逾期里程碑的影响')
                recommendations.append('制定里程碑恢复计划')
            
            # 3. 检查任务延期情况
            overdue_tasks = self.db.query(Task).filter(
                and_(
                    Task.project_id == project_id,
                    Task.planned_end_date < date.today(),
                    Task.status.in_(['TODO', 'ASSIGNED', 'IN_PROGRESS'])
                )
            ).count()
            
            indicators['overdue_tasks'] = overdue_tasks
            
            if overdue_tasks > 5:
                risks.append({
                    'risk_name': '任务延期风险',
                    'description': f'有{overdue_tasks}个任务已延期',
                    'risk_category': 'SCHEDULE',
                    'risk_level': 'MEDIUM',
                    'probability': 0.7,
                    'impact_score': min(8, 4 + overdue_tasks // 5),
                    'auto_create': False
                })
                recommendations.append('分析任务延期原因')
                recommendations.append('调整任务优先级和资源分配')
            
        except Exception as e:
            logger.error(f"检测进度风险失败: {str(e)}")
        
        return {
            'risks': risks,
            'indicators': indicators,
            'recommendations': recommendations
        }
    
    async def _detect_quality_risks(self, project_id: int) -> Dict[str, Any]:
        """检测质量风险"""
        risks = []
        indicators = {}
        recommendations = []
        
        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            
            # 1. 检查缺陷密度
            if project.defect_count and project.test_case_count:
                defect_density = project.defect_count / max(project.test_case_count, 1) * 1000
                indicators['defect_density'] = defect_density
                
                if defect_density > self.risk_detection_rules['quality_risk']['defect_density_threshold']:
                    risks.append({
                        'risk_name': '缺陷密度过高风险',
                        'description': f'缺陷密度为{defect_density:.2f}/千行代码，超过阈值',
                        'risk_category': 'QUALITY',
                        'risk_level': 'HIGH' if defect_density > 5 else 'MEDIUM',
                        'probability': 0.8,
                        'impact_score': min(9, int(defect_density) + 3),
                        'auto_create': True
                    })
                    recommendations.append('增加代码审查频率')
                    recommendations.append('加强单元测试覆盖')
            
            # 2. 检查测试覆盖率
            if project.test_case_count and project.passed_test_count:
                test_coverage = project.passed_test_count / project.test_case_count
                indicators['test_coverage'] = test_coverage
                
                if test_coverage < self.risk_detection_rules['quality_risk']['test_coverage_threshold']:
                    risks.append({
                        'risk_name': '测试覆盖率不足风险',
                        'description': f'测试覆盖率仅为{test_coverage:.1%}，低于80%标准',
                        'risk_category': 'QUALITY',
                        'risk_level': 'MEDIUM',
                        'probability': 0.7,
                        'impact_score': 6,
                        'auto_create': False
                    })
                    recommendations.append('增加测试用例设计')
                    recommendations.append('提高测试执行率')
            
            # 3. 检查严重缺陷数量
            # 这里假设有缺陷严重程度的统计，实际需要根据具体的缺陷模型调整
            critical_defects = project.defect_count // 4  # 假设25%为严重缺陷
            indicators['critical_defects'] = critical_defects
            
            if critical_defects > self.risk_detection_rules['quality_risk']['critical_defects_threshold']:
                risks.append({
                    'risk_name': '严重缺陷过多风险',
                    'description': f'严重缺陷数量为{critical_defects}个，超过阈值',
                    'risk_category': 'QUALITY',
                    'risk_level': 'CRITICAL',
                    'probability': 0.9,
                    'impact_score': 9,
                    'auto_create': True
                })
                recommendations.append('立即修复所有严重缺陷')
                recommendations.append('加强质量控制流程')
        
        except Exception as e:
            logger.error(f"检测质量风险失败: {str(e)}")
        
        return {
            'risks': risks,
            'indicators': indicators,
            'recommendations': recommendations
        }
    
    async def _detect_resource_risks(self, project_id: int) -> Dict[str, Any]:
        """检测资源风险"""
        risks = []
        indicators = {}
        recommendations = []
        
        try:
            # 1. 检查关键人员工作负载
            # 这里需要根据实际的工时记录和团队成员模型来实现
            # 暂时使用模拟数据
            
            # 2. 检查技能缺口
            # 需要根据项目需求和团队技能匹配度来分析
            
            # 3. 检查人员流失风险
            # 可以基于历史数据和当前项目参与度来评估
            
            # 示例风险检测
            indicators['resource_utilization'] = 0.85  # 资源利用率
            indicators['skill_match_rate'] = 0.75      # 技能匹配率
            
            if indicators['skill_match_rate'] < 0.8:
                risks.append({
                    'risk_name': '技能匹配度不足风险',
                    'description': f'团队技能匹配度仅为{indicators["skill_match_rate"]:.1%}',
                    'risk_category': 'RESOURCE',
                    'risk_level': 'MEDIUM',
                    'probability': 0.6,
                    'impact_score': 5,
                    'auto_create': False
                })
                recommendations.append('安排技能培训')
                recommendations.append('考虑引入外部专家')
        
        except Exception as e:
            logger.error(f"检测资源风险失败: {str(e)}")
        
        return {
            'risks': risks,
            'indicators': indicators,
            'recommendations': recommendations
        }
    
    async def _detect_technical_risks(self, project_id: int) -> Dict[str, Any]:
        """检测技术风险"""
        risks = []
        indicators = {}
        recommendations = []
        
        try:
            # 1. 检查技术复杂度
            # 2. 检查外部依赖风险
            # 3. 检查集成风险
            
            # 示例技术风险检测
            indicators['technical_complexity'] = 0.7
            indicators['external_dependencies'] = 3
            
            if indicators['technical_complexity'] > 0.8:
                risks.append({
                    'risk_name': '技术复杂度过高风险',
                    'description': '项目技术复杂度较高，可能影响开发进度',
                    'risk_category': 'TECHNICAL',
                    'risk_level': 'MEDIUM',
                    'probability': 0.5,
                    'impact_score': 6,
                    'auto_create': False
                })
                recommendations.append('制定技术攻关计划')
                recommendations.append('增加技术评审频率')
        
        except Exception as e:
            logger.error(f"检测技术风险失败: {str(e)}")
        
        return {
            'risks': risks,
            'indicators': indicators,
            'recommendations': recommendations
        }
    
    async def _auto_create_risk(self, project_id: int, risk_data: Dict[str, Any]) -> None:
        """自动创建风险记录"""
        try:
            # 检查是否已存在相同风险
            existing_risk = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.risk_name == risk_data['risk_name'],
                    ProjectRisk.status != RiskStatus.CLOSED
                )
            ).first()
            
            if existing_risk:
                # 更新现有风险的评分和描述
                existing_risk.description = risk_data['description']
                existing_risk.probability = Decimal(str(risk_data['probability']))
                existing_risk.impact_score = risk_data['impact_score']
                existing_risk.risk_score = self._calculate_risk_score(
                    existing_risk.probability, existing_risk.impact_score
                )
                self.db.commit()
                return
            
            # 创建新风险
            risk = ProjectRisk(
                project_id=project_id,
                risk_name=risk_data['risk_name'],
                description=risk_data['description'],
                risk_category=risk_data['risk_category'],
                risk_level=risk_data['risk_level'],
                probability=Decimal(str(risk_data['probability'])),
                impact_score=risk_data['impact_score'],
                risk_score=self._calculate_risk_score(
                    Decimal(str(risk_data['probability'])), risk_data['impact_score']
                ),
                mitigation_strategy=MitigationStrategy.MITIGATE,
                owner_id=1,  # 默认分配给系统管理员，实际应该分配给项目经理
                identified_date=date.today(),
                created_by=1  # 系统自动创建
            )
            
            self.db.add(risk)
            self.db.commit()
            
            logger.info(f"自动创建风险: {risk.risk_name}")
            
        except Exception as e:
            logger.error(f"自动创建风险失败: {str(e)}")
            self.db.rollback()
    
    def _calculate_risk_score(self, probability: Decimal, impact_score: int) -> Decimal:
        """计算风险评分"""
        return probability * Decimal(str(impact_score))

    def _validate_owner(self, owner_id: int) -> None:
        """Validate that the selected risk owner exists and is active."""
        user = self.db.query(User).filter(User.id == owner_id).first()
        if not user:
            raise validation_error(f"风险负责人不存在: {owner_id}")
        if getattr(user, "is_active", True) is False:
            raise validation_error(f"风险负责人已停用: {owner_id}")

    def _send_owner_notification(self, *, risk: ProjectRisk, sender_id: int, project_name: str, changed: bool) -> None:
        """Create an unread in-app notification for the risk owner."""
        if not risk.owner_id:
            return

        try:
            notification = SystemNotification(
                user_id=int(risk.owner_id),
                sender_id=sender_id,
                category="risk_assignment",
                title="你有新的风险负责人安排",
                content=f"风险“{risk.risk_name}”已由你负责，所属项目：{project_name}。",
                related_type="risk",
                related_id=risk.id,
                payload={
                    "risk_id": risk.id,
                    "risk_name": risk.risk_name,
                    "project_id": risk.project_id,
                    "project_name": project_name,
                    "changed": changed,
                },
            )
            self.db.add(notification)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning(f"创建风险负责人通知失败: {exc}")
    
    async def _update_project_risk_level(self, project_id: int) -> None:
        """更新项目风险等级"""
        try:
            # 获取项目所有未关闭的风险
            risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.status != RiskStatus.CLOSED
                )
            ).all()
            
            if not risks:
                risk_level = 'LOW'
            else:
                # 根据最高风险等级确定项目风险等级
                risk_levels = [risk.risk_level for risk in risks]
                if 'CRITICAL' in risk_levels:
                    risk_level = 'CRITICAL'
                elif 'HIGH' in risk_levels:
                    risk_level = 'HIGH'
                elif 'MEDIUM' in risk_levels:
                    risk_level = 'MEDIUM'
                else:
                    risk_level = 'LOW'
            
            # 更新项目风险等级
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.risk_level = risk_level
                self.db.commit()
                
        except Exception as e:
            logger.error(f"更新项目风险等级失败: {str(e)}")
            self.db.rollback()
    
    async def get_risk_analysis(self, project_id: int) -> RiskAnalysisResponse:
        """获取风险分析报告"""
        try:
            # 获取项目所有风险
            risks = self.db.query(ProjectRisk).filter(ProjectRisk.project_id == project_id).all()
            
            # 计算风险指标
            total_risks = len(risks)
            open_risks = len([r for r in risks if r.status != RiskStatus.CLOSED])
            critical_risks = len([r for r in risks if r.risk_level == RiskLevel.CRITICAL])
            high_risks = len([r for r in risks if r.risk_level == RiskLevel.HIGH])
            medium_risks = len([r for r in risks if r.risk_level == RiskLevel.MEDIUM])
            low_risks = len([r for r in risks if r.risk_level == RiskLevel.LOW])
            
            avg_score = sum(float(r.risk_score) for r in risks) / len(risks) if risks else 0
            
            # 风险趋势分析（简化版）
            recent_risks = len([r for r in risks if r.identified_date >= date.today() - timedelta(days=7)])
            if recent_risks > total_risks * 0.3:
                risk_trend = "上升"
            elif recent_risks < total_risks * 0.1:
                risk_trend = "下降"
            else:
                risk_trend = "稳定"
            
            metrics = RiskMetrics(
                total_risks=total_risks,
                open_risks=open_risks,
                critical_risks=critical_risks,
                high_risks=high_risks,
                medium_risks=medium_risks,
                low_risks=low_risks,
                average_risk_score=Decimal(str(avg_score)),
                risk_trend=risk_trend
            )
            
            # 类别分析
            category_stats = {}
            for risk in risks:
                category = risk.risk_category
                if category not in category_stats:
                    category_stats[category] = {'count': 0, 'total_score': 0}
                category_stats[category]['count'] += 1
                category_stats[category]['total_score'] += float(risk.risk_score)
            
            category_analysis = []
            for category, stats in category_stats.items():
                percentage = (stats['count'] / total_risks * 100) if total_risks > 0 else 0
                avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
                
                category_analysis.append(RiskCategoryAnalysis(
                    category=category,
                    count=stats['count'],
                    percentage=Decimal(str(percentage)),
                    average_score=Decimal(str(avg_score))
                ))
            
            # 获取高风险列表
            top_risks = sorted(risks, key=lambda x: float(x.risk_score), reverse=True)[:5]
            
            # 生成建议
            recommendations = []
            if critical_risks > 0:
                recommendations.append("立即处理所有严重风险")
            if open_risks > total_risks * 0.7:
                recommendations.append("加强风险管控，提高风险解决效率")
            if risk_trend == "上升":
                recommendations.append("分析风险增长原因，制定预防措施")
            
            return RiskAnalysisResponse(
                project_id=project_id,
                analysis_date=datetime.utcnow(),
                metrics=metrics,
                category_analysis=category_analysis,
                top_risks=[RiskResponse.from_orm(risk) for risk in top_risks],
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"获取风险分析失败: {str(e)}")
            raise
    
    async def get_risk_trend(self, project_id: int, days: int = 30) -> RiskTrendResponse:
        """获取风险趋势数据"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 获取时间范围内的风险数据
            risks = self.db.query(ProjectRisk).filter(
                and_(
                    ProjectRisk.project_id == project_id,
                    ProjectRisk.identified_date >= start_date
                )
            ).all()
            
            # 按日期统计风险数据
            trend_data = []
            current_date = start_date
            
            while current_date <= end_date:
                day_risks = [r for r in risks if r.identified_date <= current_date]
                new_risks = [r for r in risks if r.identified_date == current_date]
                closed_risks = [r for r in day_risks if r.actual_resolution_date == current_date]
                critical_risks = [r for r in day_risks if r.risk_level == RiskLevel.CRITICAL and r.status != RiskStatus.CLOSED]
                
                avg_score = sum(float(r.risk_score) for r in day_risks) / len(day_risks) if day_risks else 0
                
                trend_data.append(RiskTrendData(
                    trend_date=current_date,
                    total_risks=len(day_risks),
                    new_risks=len(new_risks),
                    closed_risks=len(closed_risks),
                    average_score=Decimal(str(avg_score)),
                    critical_count=len(critical_risks)
                ))
                
                current_date += timedelta(days=1)
            
            # 生成趋势总结
            summary = {
                'total_new_risks': len(risks),
                'total_closed_risks': len([r for r in risks if r.status == RiskStatus.CLOSED]),
                'trend_direction': '上升' if len(risks) > 0 else '稳定',
                'peak_risk_date': max(trend_data, key=lambda x: x.total_risks).trend_date if trend_data else None
            }
            
            return RiskTrendResponse(
                project_id=project_id,
                start_date=start_date,
                end_date=end_date,
                trend_data=trend_data,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"获取风险趋势失败: {str(e)}")
            raise
