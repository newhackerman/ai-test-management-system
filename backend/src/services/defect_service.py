"""
缺陷管理服务

本模块实现了缺陷管理的核心业务逻辑，包括：
- 缺陷的完整生命周期管理
- 智能缺陷分析和分配
- 缺陷趋势分析和预测
- 缺陷与测试活动的关联管理
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError

from ..models.test_case import Defect, DefectStatus, DefectSeverity, DefectType, DefectResolution, TestCasePriority
from ..models.user import User
from ..models.project import Project
from ..schemas.defect import (
    CreateDefectRequest, UpdateDefectRequest, DefectStatusUpdateRequest,
    DefectResponse, DefectListResponse, DefectQueryParams, DefectStatistics,
    DefectTrendAnalysis, DefectTrendData, DefectAssignmentSuggestion,
    DefectAnalysisResult, DefectSimilarityResult, DefectMetrics
)
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..utils.redis_client import RedisClient
from .ai_assistant_service import AIAssistantService
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class DefectService:
    """缺陷管理服务"""
    
    def __init__(self, db: Session, redis_client: Optional[RedisClient] = None,
                 ai_service: Optional[AIAssistantService] = None,
                 notification_service: Optional[NotificationService] = None):
        self.db = db
        self.redis = redis_client
        self.ai_service = ai_service
        self.notification_service = notification_service
    
    async def create_defect(self, defect_data: CreateDefectRequest, reporter_id: int) -> DefectResponse:
        """创建缺陷"""
        try:
            # 1. 验证缺陷数据
            await self._validate_defect_data(defect_data)
            
            # 2. 生成缺陷编码
            defect_code = await self._generate_defect_code()
            
            # 3. AI辅助分析缺陷
            ai_analysis = await self._analyze_defect_with_ai(defect_data)
            
            # 4. 智能分配建议
            assignment_suggestion = await self._suggest_defect_assignment(defect_data, ai_analysis)
            
            # 5. 创建缺陷实体
            defect = Defect(
                defect_code=defect_code,
                test_execution_id=defect_data.test_execution_id,
                test_case_id=defect_data.test_case_id,
                requirement_id=defect_data.requirement_id,
                title=defect_data.title,
                description=defect_data.description,
                steps_to_reproduce=defect_data.steps_to_reproduce,
                defect_type=ai_analysis.suggested_type or defect_data.defect_type,
                severity=ai_analysis.suggested_severity or defect_data.severity,
                priority=ai_analysis.suggested_priority or defect_data.priority,
                found_in_version=defect_data.found_in_version,
                test_environment=defect_data.test_environment,
                reporter_id=reporter_id,
                assignee_id=defect_data.assignee_id or assignment_suggestion.assignee_id,
                attachments=defect_data.attachments,
                status=DefectStatus.NEW
            )
            
            # 6. 保存缺陷
            self.db.add(defect)
            self.db.commit()
            self.db.refresh(defect)
            
            # 7. 建立关联关系
            await self._create_defect_associations(defect)
            
            # 8. 更新缓存
            await self._update_defect_cache(defect)
            
            # 9. 发送通知
            await self._send_defect_created_notifications(defect)
            
            # 10. 记录操作日志
            await self._log_defect_operation(defect.id, "CREATE", reporter_id, "创建缺陷")
            
            logger.info(f"缺陷创建成功: {defect.defect_code}")
            return DefectResponse.from_orm(defect)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建缺陷失败: {str(e)}")
            raise ValidationError(f"创建缺陷失败: {str(e)}")
    
    async def update_defect(self, defect_id: int, update_data: UpdateDefectRequest, 
                           user_id: int) -> DefectResponse:
        """更新缺陷"""
        try:
            # 1. 获取缺陷
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise NotFoundError("缺陷不存在")
            
            # 2. 验证更新权限
            if not await self._has_update_permission(user_id, defect):
                raise PermissionError("没有更新权限")
            
            # 3. 更新字段
            update_fields = update_data.dict(exclude_unset=True)
            for field, value in update_fields.items():
                if hasattr(defect, field):
                    setattr(defect, field, value)
            
            defect.updated_at = datetime.utcnow()
            
            # 4. 保存更改
            self.db.commit()
            self.db.refresh(defect)
            
            # 5. 更新缓存
            await self._update_defect_cache(defect)
            
            # 6. 发送通知
            await self._send_defect_updated_notifications(defect, update_fields)
            
            # 7. 记录操作日志
            await self._log_defect_operation(defect.id, "UPDATE", user_id, f"更新缺陷: {list(update_fields.keys())}")
            
            logger.info(f"缺陷更新成功: {defect.defect_code}")
            return DefectResponse.from_orm(defect)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新缺陷失败: {str(e)}")
            raise
    
    async def update_defect_status(self, defect_id: int, status_update: DefectStatusUpdateRequest,
                                  user_id: int) -> DefectResponse:
        """更新缺陷状态"""
        try:
            # 1. 获取缺陷
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise NotFoundError("缺陷不存在")
            
            # 2. 验证状态流转
            if not self._is_valid_status_transition(defect.status, status_update.status):
                raise ValidationError(f"不能从{defect.status.value}状态转换到{status_update.status.value}状态")
            
            # 3. 验证操作权限
            if not await self._has_status_change_permission(user_id, defect, status_update.status):
                raise PermissionError("没有状态变更权限")
            
            # 4. 记录状态历史
            await self._record_defect_status_history(
                defect_id, defect.status, status_update.status, user_id, status_update.notes
            )
            
            # 5. 更新缺陷状态
            old_status = defect.status
            defect.status = status_update.status
            if status_update.resolution:
                defect.resolution = status_update.resolution
            
            # 6. 更新时间戳
            if status_update.status == DefectStatus.ASSIGNED:
                defect.assigned_at = datetime.utcnow()
            elif status_update.status == DefectStatus.RESOLVED:
                defect.resolved_at = datetime.utcnow()
                defect.resolver_id = user_id
            elif status_update.status == DefectStatus.CLOSED:
                defect.verified_at = datetime.utcnow()
            
            defect.updated_at = datetime.utcnow()
            
            # 7. 保存更改
            self.db.commit()
            self.db.refresh(defect)
            
            # 8. 执行状态变更后置动作
            await self._execute_status_change_actions(defect, old_status, status_update.status)
            
            # 9. 更新缓存
            await self._update_defect_cache(defect)
            
            # 10. 发送通知
            await self._send_status_change_notifications(defect, old_status, status_update.status)
            
            # 11. 记录操作日志
            await self._log_defect_operation(
                defect.id, "STATUS_CHANGE", user_id, 
                f"状态变更: {old_status.value} -> {status_update.status.value}"
            )
            
            logger.info(f"缺陷状态更新成功: {defect.defect_code} {old_status.value} -> {status_update.status.value}")
            return DefectResponse.from_orm(defect)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新缺陷状态失败: {str(e)}")
            raise
    
    async def get_defect_by_id(self, defect_id: int) -> DefectResponse:
        """根据ID获取缺陷"""
        # 1. 尝试从缓存获取
        cached_defect = await self._get_defect_from_cache(defect_id)
        if cached_defect:
            return cached_defect
        
        # 2. 从数据库获取
        defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise NotFoundError("缺陷不存在")
        
        # 3. 更新缓存
        defect_response = DefectResponse.from_orm(defect)
        await self._cache_defect(defect_response)
        
        return defect_response
    
    async def get_defects(self, query_params: DefectQueryParams) -> DefectListResponse:
        """获取缺陷列表"""
        try:
            # 1. 构建查询
            query = self.db.query(Defect)
            
            # 2. 应用筛选条件
            if query_params.status:
                query = query.filter(Defect.status == query_params.status)
            if query_params.severity:
                query = query.filter(Defect.severity == query_params.severity)
            if query_params.priority:
                query = query.filter(Defect.priority == query_params.priority)
            if query_params.defect_type:
                query = query.filter(Defect.defect_type == query_params.defect_type)
            if query_params.assignee_id:
                query = query.filter(Defect.assignee_id == query_params.assignee_id)
            if query_params.reporter_id:
                query = query.filter(Defect.reporter_id == query_params.reporter_id)
            if query_params.test_case_id:
                query = query.filter(Defect.test_case_id == query_params.test_case_id)
            if query_params.requirement_id:
                query = query.filter(Defect.requirement_id == query_params.requirement_id)
            
            # 3. 关键词搜索
            if query_params.keyword:
                keyword = f"%{query_params.keyword}%"
                query = query.filter(
                    or_(
                        Defect.title.like(keyword),
                        Defect.description.like(keyword),
                        Defect.defect_code.like(keyword)
                    )
                )
            
            # 4. 日期范围筛选
            if query_params.start_date:
                query = query.filter(Defect.reported_at >= query_params.start_date)
            if query_params.end_date:
                end_datetime = datetime.combine(query_params.end_date, datetime.max.time())
                query = query.filter(Defect.reported_at <= end_datetime)
            
            # 5. 获取总数
            total = query.count()
            
            # 6. 分页和排序
            offset = (query_params.page - 1) * query_params.page_size
            defects = query.order_by(desc(Defect.reported_at)).offset(offset).limit(query_params.page_size).all()
            
            # 7. 转换为响应格式
            defect_responses = [DefectResponse.from_orm(defect) for defect in defects]
            
            # 8. 计算分页信息
            total_pages = (total + query_params.page_size - 1) // query_params.page_size
            
            return DefectListResponse(
                defects=defect_responses,
                total=total,
                page=query_params.page,
                page_size=query_params.page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"获取缺陷列表失败: {str(e)}")
            raise ValidationError(f"获取缺陷列表失败: {str(e)}")
    
    async def delete_defect(self, defect_id: int, user_id: int) -> bool:
        """删除缺陷"""
        try:
            # 1. 获取缺陷
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise NotFoundError("缺陷不存在")
            
            # 2. 验证删除权限
            if not await self._has_delete_permission(user_id, defect):
                raise PermissionError("没有删除权限")
            
            # 3. 检查是否可以删除
            if defect.status not in [DefectStatus.NEW, DefectStatus.REJECTED]:
                raise ValidationError("只能删除新建或已拒绝状态的缺陷")
            
            # 4. 删除缺陷
            self.db.delete(defect)
            self.db.commit()
            
            # 5. 清除缓存
            await self._remove_defect_from_cache(defect_id)
            
            # 6. 记录操作日志
            await self._log_defect_operation(defect_id, "DELETE", user_id, "删除缺陷")
            
            logger.info(f"缺陷删除成功: {defect.defect_code}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除缺陷失败: {str(e)}")
            raise
    
    async def get_defect_statistics(self, project_id: Optional[int] = None, 
                                   time_range: Optional[str] = None) -> DefectStatistics:
        """获取缺陷统计"""
        try:
            # 1. 构建查询
            query = self.db.query(Defect)
            
            if project_id:
                # 通过关联的测试用例或需求获取项目缺陷
                query = query.join(Defect.test_case).filter(TestCase.project_id == project_id)
            
            # 2. 时间范围筛选
            if time_range:
                start_date = self._get_start_date_by_range(time_range)
                query = query.filter(Defect.reported_at >= start_date)
            
            # 3. 统计各种状态的缺陷数量
            defects = query.all()
            
            stats = DefectStatistics()
            stats.total_defects = len(defects)
            
            # 按状态统计
            for defect in defects:
                if defect.status == DefectStatus.NEW:
                    stats.new_defects += 1
                elif defect.status == DefectStatus.ASSIGNED:
                    stats.assigned_defects += 1
                elif defect.status == DefectStatus.IN_PROGRESS:
                    stats.in_progress_defects += 1
                elif defect.status == DefectStatus.RESOLVED:
                    stats.resolved_defects += 1
                elif defect.status == DefectStatus.CLOSED:
                    stats.closed_defects += 1
                elif defect.status == DefectStatus.REOPENED:
                    stats.reopened_defects += 1
                
                # 按严重程度统计
                if defect.severity == DefectSeverity.CRITICAL:
                    stats.critical_defects += 1
                elif defect.severity == DefectSeverity.HIGH:
                    stats.high_defects += 1
                elif defect.severity == DefectSeverity.MEDIUM:
                    stats.medium_defects += 1
                elif defect.severity == DefectSeverity.LOW:
                    stats.low_defects += 1
                
                # 按类型统计
                if defect.defect_type == DefectType.FUNCTIONAL:
                    stats.functional_defects += 1
                elif defect.defect_type == DefectType.PERFORMANCE:
                    stats.performance_defects += 1
                elif defect.defect_type == DefectType.SECURITY:
                    stats.security_defects += 1
                elif defect.defect_type == DefectType.USABILITY:
                    stats.usability_defects += 1
            
            # 4. 计算质量指标
            if stats.total_defects > 0:
                stats.resolution_rate = (stats.resolved_defects + stats.closed_defects) / stats.total_defects
                stats.reopen_rate = stats.reopened_defects / stats.total_defects
            
            # 5. 计算平均解决时间
            resolved_defects = [d for d in defects if d.resolved_at and d.reported_at]
            if resolved_defects:
                total_resolution_time = sum(
                    (d.resolved_at - d.reported_at).total_seconds() / 3600 
                    for d in resolved_defects
                )
                stats.avg_resolution_time = total_resolution_time / len(resolved_defects)
            
            # 6. 计算缺陷密度（需要项目代码行数等信息）
            if project_id:
                stats.defect_density = await self._calculate_defect_density(project_id, stats.total_defects)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缺陷统计失败: {str(e)}")
            raise ValidationError(f"获取缺陷统计失败: {str(e)}")
    
    # 私有方法实现
    async def _validate_defect_data(self, defect_data: CreateDefectRequest):
        """验证缺陷数据"""
        # 验证关联的测试执行是否存在
        if defect_data.test_execution_id:
            from ..models.test_case import TestExecution
            execution = self.db.query(TestExecution).filter(
                TestExecution.id == defect_data.test_execution_id
            ).first()
            if not execution:
                raise ValidationError("关联的测试执行不存在")
        
        # 验证关联的测试用例是否存在
        if defect_data.test_case_id:
            from ..models.test_case import TestCase
            test_case = self.db.query(TestCase).filter(
                TestCase.id == defect_data.test_case_id
            ).first()
            if not test_case:
                raise ValidationError("关联的测试用例不存在")
        
        # 验证关联的需求是否存在
        if defect_data.requirement_id:
            from ..models.requirement import Requirement
            requirement = self.db.query(Requirement).filter(
                Requirement.id == defect_data.requirement_id
            ).first()
            if not requirement:
                raise ValidationError("关联的需求不存在")
        
        # 验证分配人是否存在
        if defect_data.assignee_id:
            assignee = self.db.query(User).filter(User.id == defect_data.assignee_id).first()
            if not assignee:
                raise ValidationError("分配人不存在")
    
    async def _generate_defect_code(self) -> str:
        """生成缺陷编码"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 获取今天已创建的缺陷数量
        count = self.db.query(Defect).filter(
            func.date(Defect.created_at) == datetime.now().date()
        ).count()
        
        return f"BUG-{today}-{count + 1:04d}"
    
    async def _analyze_defect_with_ai(self, defect_data: CreateDefectRequest) -> DefectAnalysisResult:
        """使用AI分析缺陷"""
        try:
            # 构建AI分析提示
            analysis_prompt = f"""
            请分析以下缺陷信息，并提供分类建议：
            
            标题: {defect_data.title}
            描述: {defect_data.description}
            重现步骤: {defect_data.steps_to_reproduce or '无'}
            测试环境: {defect_data.test_environment or '无'}
            
            请提供：
            1. 建议的缺陷类型（FUNCTIONAL/PERFORMANCE/SECURITY/USABILITY/COMPATIBILITY/DATA/INTERFACE）
            2. 建议的严重程度（CRITICAL/HIGH/MEDIUM/LOW）
            3. 建议的优先级（CRITICAL/HIGH/MEDIUM/LOW）
            4. 根因分析
            5. 修复建议
            """
            
            # 调用AI服务
            ai_response = await self.ai_service.analyze_text(analysis_prompt)
            
            # 解析AI响应（这里需要根据实际AI服务的响应格式进行解析）
            return DefectAnalysisResult(
                suggested_type=self._parse_defect_type_from_ai(ai_response),
                suggested_severity=self._parse_severity_from_ai(ai_response),
                suggested_priority=self._parse_priority_from_ai(ai_response),
                root_cause_analysis=self._extract_root_cause_from_ai(ai_response),
                fix_suggestions=self._extract_fix_suggestions_from_ai(ai_response),
                confidence=0.8  # 默认置信度
            )
            
        except Exception as e:
            logger.warning(f"AI分析缺陷失败: {str(e)}")
            # 返回默认分析结果
            return DefectAnalysisResult(confidence=0.0)
    
    async def _suggest_defect_assignment(self, defect_data: CreateDefectRequest, 
                                        ai_analysis: DefectAnalysisResult) -> DefectAssignmentSuggestion:
        """智能分配建议"""
        try:
            # 如果已指定分配人，直接返回
            if defect_data.assignee_id:
                assignee = self.db.query(User).filter(User.id == defect_data.assignee_id).first()
                return DefectAssignmentSuggestion(
                    assignee_id=defect_data.assignee_id,
                    assignee_name=assignee.username if assignee else "未知用户",
                    confidence=1.0,
                    reason="手动指定",
                    workload=0,
                    expertise_match=1.0
                )
            
            # 获取可分配的用户列表（开发人员）
            developers = self.db.query(User).filter(
                User.is_active == True,
                User.roles.any(name="developer")  # 假设有角色关联
            ).all()
            
            if not developers:
                # 如果没有开发人员，返回默认建议
                return DefectAssignmentSuggestion(
                    assignee_id=1,  # 默认管理员
                    assignee_name="系统管理员",
                    confidence=0.1,
                    reason="无可用开发人员",
                    workload=0,
                    expertise_match=0.1
                )
            
            # 简单的负载均衡分配（实际应用中可以更复杂）
            # 统计每个开发人员当前的缺陷数量
            developer_workloads = {}
            for dev in developers:
                workload = self.db.query(Defect).filter(
                    Defect.assignee_id == dev.id,
                    Defect.status.in_([DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS])
                ).count()
                developer_workloads[dev.id] = workload
            
            # 选择工作负载最少的开发人员
            best_assignee_id = min(developer_workloads.keys(), key=lambda x: developer_workloads[x])
            best_assignee = next(dev for dev in developers if dev.id == best_assignee_id)
            
            return DefectAssignmentSuggestion(
                assignee_id=best_assignee_id,
                assignee_name=best_assignee.username,
                confidence=0.7,
                reason="基于工作负载均衡",
                workload=developer_workloads[best_assignee_id],
                expertise_match=0.5  # 默认匹配度
            )
            
        except Exception as e:
            logger.warning(f"智能分配建议失败: {str(e)}")
            # 返回默认建议
            return DefectAssignmentSuggestion(
                assignee_id=1,
                assignee_name="系统管理员",
                confidence=0.1,
                reason="分配算法失败",
                workload=0,
                expertise_match=0.1
            )
    
    def _is_valid_status_transition(self, current_status: DefectStatus, new_status: DefectStatus) -> bool:
        """验证状态流转是否合法"""
        valid_transitions = {
            DefectStatus.NEW: [DefectStatus.ASSIGNED, DefectStatus.REJECTED],
            DefectStatus.ASSIGNED: [DefectStatus.IN_PROGRESS, DefectStatus.REJECTED],
            DefectStatus.IN_PROGRESS: [DefectStatus.RESOLVED, DefectStatus.ASSIGNED],
            DefectStatus.RESOLVED: [DefectStatus.VERIFIED, DefectStatus.REOPENED],
            DefectStatus.VERIFIED: [DefectStatus.CLOSED, DefectStatus.REOPENED],
            DefectStatus.CLOSED: [DefectStatus.REOPENED],
            DefectStatus.REOPENED: [DefectStatus.ASSIGNED, DefectStatus.REJECTED],
            DefectStatus.REJECTED: [DefectStatus.REOPENED]
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    async def _has_update_permission(self, user_id: int, defect: Defect) -> bool:
        """检查是否有更新权限"""
        # 报告人、分配人、管理员可以更新
        if user_id in [defect.reporter_id, defect.assignee_id]:
            return True
        
        # 检查是否是管理员（简化实现）
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.is_superuser:
            return True
        
        return False
    
    async def _has_status_change_permission(self, user_id: int, defect: Defect, new_status: DefectStatus) -> bool:
        """检查是否有状态变更权限"""
        # 不同状态变更需要不同权限
        if new_status == DefectStatus.ASSIGNED:
            # 项目经理或管理员可以分配
            return await self._is_project_manager_or_admin(user_id)
        elif new_status in [DefectStatus.IN_PROGRESS, DefectStatus.RESOLVED]:
            # 分配人可以处理
            return user_id == defect.assignee_id
        elif new_status in [DefectStatus.VERIFIED, DefectStatus.CLOSED]:
            # 报告人或测试人员可以验证
            return user_id == defect.reporter_id or await self._is_tester(user_id)
        elif new_status == DefectStatus.REJECTED:
            # 分配人或管理员可以拒绝
            return user_id == defect.assignee_id or await self._is_project_manager_or_admin(user_id)
        
        return False
    
    async def _has_delete_permission(self, user_id: int, defect: Defect) -> bool:
        """检查是否有删除权限"""
        # 只有报告人或管理员可以删除
        if user_id == defect.reporter_id:
            return True
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.is_superuser:
            return True
        
        return False
    
    # 辅助方法
    def _parse_defect_type_from_ai(self, ai_response: str) -> Optional[DefectType]:
        """从AI响应中解析缺陷类型"""
        # 简化实现，实际应用中需要更复杂的解析逻辑
        response_upper = ai_response.upper()
        for defect_type in DefectType:
            if defect_type.value in response_upper:
                return defect_type
        return None
    
    def _parse_severity_from_ai(self, ai_response: str) -> Optional[DefectSeverity]:
        """从AI响应中解析严重程度"""
        response_upper = ai_response.upper()
        for severity in DefectSeverity:
            if severity.value in response_upper:
                return severity
        return None
    
    def _parse_priority_from_ai(self, ai_response: str) -> Optional[TestCasePriority]:
        """从AI响应中解析优先级"""
        response_upper = ai_response.upper()
        for priority in TestCasePriority:
            if priority.value in response_upper:
                return priority
        return None
    
    def _extract_root_cause_from_ai(self, ai_response: str) -> Optional[str]:
        """从AI响应中提取根因分析"""
        # 简化实现
        lines = ai_response.split('\n')
        for line in lines:
            if '根因' in line or 'root cause' in line.lower():
                return line.strip()
        return None
    
    def _extract_fix_suggestions_from_ai(self, ai_response: str) -> Optional[List[str]]:
        """从AI响应中提取修复建议"""
        # 简化实现
        suggestions = []
        lines = ai_response.split('\n')
        in_suggestions = False
        for line in lines:
            if '修复建议' in line or 'fix suggestion' in line.lower():
                in_suggestions = True
                continue
            if in_suggestions and line.strip():
                suggestions.append(line.strip())
        return suggestions if suggestions else None
    
    async def _is_project_manager_or_admin(self, user_id: int) -> bool:
        """检查是否是项目经理或管理员"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # 简化实现
        return user.is_superuser or 'manager' in user.username.lower()
    
    async def _is_tester(self, user_id: int) -> bool:
        """检查是否是测试人员"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # 简化实现
        return 'test' in user.username.lower() or 'qa' in user.username.lower()
    
    def _get_start_date_by_range(self, time_range: str) -> datetime:
        """根据时间范围获取开始日期"""
        now = datetime.now()
        if time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        elif time_range == "90d":
            return now - timedelta(days=90)
        else:
            return now - timedelta(days=30)  # 默认30天
    
    async def _calculate_defect_density(self, project_id: int, total_defects: int) -> float:
        """计算缺陷密度"""
        # 简化实现，实际应用中需要获取项目的代码行数
        # 这里假设每个项目有10000行代码
        lines_of_code = 10000
        return (total_defects / lines_of_code) * 1000  # 每千行代码的缺陷数
    
    # 缓存相关方法
    async def _get_defect_from_cache(self, defect_id: int) -> Optional[DefectResponse]:
        """从缓存获取缺陷"""
        try:
            cache_key = f"defect:info:{defect_id}"
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return DefectResponse.parse_raw(cached_data)
        except Exception as e:
            logger.warning(f"从缓存获取缺陷失败: {str(e)}")
        return None
    
    async def _cache_defect(self, defect: DefectResponse):
        """缓存缺陷信息"""
        try:
            cache_key = f"defect:info:{defect.id}"
            await self.redis.setex(cache_key, 3600, defect.json())  # 缓存1小时
        except Exception as e:
            logger.warning(f"缓存缺陷信息失败: {str(e)}")
    
    async def _update_defect_cache(self, defect: Defect):
        """更新缺陷缓存"""
        try:
            defect_response = DefectResponse.from_orm(defect)
            await self._cache_defect(defect_response)
        except Exception as e:
            logger.warning(f"更新缺陷缓存失败: {str(e)}")
    
    async def _remove_defect_from_cache(self, defect_id: int):
        """从缓存中移除缺陷"""
        try:
            cache_key = f"defect:info:{defect_id}"
            await self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"从缓存移除缺陷失败: {str(e)}")
    
    # 通知相关方法
    async def _send_defect_created_notifications(self, defect: Defect):
        """发送缺陷创建通知"""
        try:
            # 通知分配人
            if defect.assignee_id:
                await self.notification_service.send_notification(
                    user_id=defect.assignee_id,
                    title="新缺陷分配",
                    content=f"您被分配了新的缺陷: {defect.title}",
                    notification_type="defect_assigned"
                )
            
            # 通知项目相关人员（简化实现）
            logger.info(f"发送缺陷创建通知: {defect.defect_code}")
        except Exception as e:
            logger.warning(f"发送缺陷创建通知失败: {str(e)}")
    
    async def _send_defect_updated_notifications(self, defect: Defect, updated_fields: Dict[str, Any]):
        """发送缺陷更新通知"""
        try:
            # 通知相关人员
            notification_users = [defect.reporter_id]
            if defect.assignee_id:
                notification_users.append(defect.assignee_id)
            
            for user_id in set(notification_users):
                await self.notification_service.send_notification(
                    user_id=user_id,
                    title="缺陷更新",
                    content=f"缺陷 {defect.title} 已更新: {list(updated_fields.keys())}",
                    notification_type="defect_updated"
                )
            
            logger.info(f"发送缺陷更新通知: {defect.defect_code}")
        except Exception as e:
            logger.warning(f"发送缺陷更新通知失败: {str(e)}")
    
    async def _send_status_change_notifications(self, defect: Defect, old_status: DefectStatus, new_status: DefectStatus):
        """发送状态变更通知"""
        try:
            # 通知相关人员
            notification_users = [defect.reporter_id]
            if defect.assignee_id:
                notification_users.append(defect.assignee_id)
            
            for user_id in set(notification_users):
                await self.notification_service.send_notification(
                    user_id=user_id,
                    title="缺陷状态变更",
                    content=f"缺陷 {defect.title} 状态从 {old_status.value} 变更为 {new_status.value}",
                    notification_type="defect_status_changed"
                )
            
            logger.info(f"发送状态变更通知: {defect.defect_code} {old_status.value} -> {new_status.value}")
        except Exception as e:
            logger.warning(f"发送状态变更通知失败: {str(e)}")
    
    # 其他辅助方法
    async def _create_defect_associations(self, defect: Defect):
        """创建缺陷关联关系"""
        # 这里可以实现与其他实体的关联逻辑
        pass
    
    async def _record_defect_status_history(self, defect_id: int, old_status: DefectStatus, 
                                          new_status: DefectStatus, user_id: int, notes: Optional[str]):
        """记录缺陷状态历史"""
        # 这里可以实现状态历史记录逻辑
        logger.info(f"记录状态历史: 缺陷{defect_id} {old_status.value} -> {new_status.value} by {user_id}")
    
    async def _execute_status_change_actions(self, defect: Defect, old_status: DefectStatus, new_status: DefectStatus):
        """执行状态变更后置动作"""
        # 这里可以实现状态变更后的自动化动作
        pass
    
    async def _log_defect_operation(self, defect_id: int, operation: str, user_id: int, description: str):
        """记录缺陷操作日志"""
        logger.info(f"缺陷操作日志: {operation} - 缺陷{defect_id} - 用户{user_id} - {description}")
