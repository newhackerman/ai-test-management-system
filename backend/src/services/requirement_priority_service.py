"""
需求优先级管理服务

提供需求优先级相关的业务逻辑，包括：
- 优先级评估算法
- 动态优先级调整
- 优先级冲突检测和解决
- 优先级历史管理
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.requirement_priority_repository import (
    RequirementPriorityConfigRepository,
    RequirementPriorityEvaluationRepository,
    RequirementPriorityConflictRepository,
    RequirementPriorityHistoryRepository
)
from ..models.requirement_priority import (
    RequirementPriorityConfig, RequirementPriorityEvaluation,
    RequirementPriorityConflict, RequirementPriorityHistory,
    PriorityCalculationMethod, PriorityFactorType, ConflictResolutionStrategy,
    PriorityConflictStatus
)
from ..models.requirement import Requirement, Priority
from ..schemas.requirement_priority import (
    CreatePriorityConfigRequest, UpdatePriorityConfigRequest,
    EvaluatePriorityRequest, PriorityEvaluationResponse,
    ConflictResolutionRequest
)
from .ai_assistant_service import AIAssistantService


class RequirementPriorityService:
    """需求优先级管理服务"""
    
    def __init__(
        self,
        session: AsyncSession,
        ai_service: Optional[AIAssistantService] = None
    ):
        self.session = session
        self.ai_service = ai_service
        
        # 初始化仓储
        self.config_repo = RequirementPriorityConfigRepository(session)
        self.evaluation_repo = RequirementPriorityEvaluationRepository(session)
        self.conflict_repo = RequirementPriorityConflictRepository(session)
        self.history_repo = RequirementPriorityHistoryRepository(session)
    
    # 优先级配置管理
    async def create_priority_config(
        self,
        config_data: CreatePriorityConfigRequest,
        creator_id: int
    ) -> RequirementPriorityConfig:
        """创建优先级配置"""
        # 验证权重总和为1
        total_weight = (
            config_data.business_value_weight +
            config_data.user_impact_weight +
            config_data.technical_risk_weight +
            config_data.implementation_cost_weight +
            config_data.time_urgency_weight
        )
        
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("权重总和必须等于1.0")
        
        # 如果设置为默认配置，需要取消其他默认配置
        if config_data.is_default:
            await self._clear_default_configs(config_data.project_id)
        
        config = RequirementPriorityConfig(
            project_id=config_data.project_id,
            config_name=config_data.config_name,
            description=config_data.description,
            calculation_method=config_data.calculation_method,
            business_value_weight=config_data.business_value_weight,
            user_impact_weight=config_data.user_impact_weight,
            technical_risk_weight=config_data.technical_risk_weight,
            implementation_cost_weight=config_data.implementation_cost_weight,
            time_urgency_weight=config_data.time_urgency_weight,
            critical_threshold=config_data.critical_threshold,
            high_threshold=config_data.high_threshold,
            medium_threshold=config_data.medium_threshold,
            low_threshold=config_data.low_threshold,
            conflict_resolution_strategy=config_data.conflict_resolution_strategy,
            is_default=config_data.is_default,
            additional_config=config_data.additional_config,
            created_by=creator_id
        )
        
        return await self.config_repo.create(config)
    
    async def get_project_priority_configs(self, project_id: int) -> List[RequirementPriorityConfig]:
        """获取项目的优先级配置"""
        return await self.config_repo.get_by_project_id(project_id)
    
    async def get_default_priority_config(self, project_id: int) -> Optional[RequirementPriorityConfig]:
        """获取项目的默认优先级配置"""
        return await self.config_repo.get_default_config(project_id)

    # Priority evaluation
    async def evaluate_requirement_priority(
        self,
        requirement_id: int,
        evaluation_data: EvaluatePriorityRequest,
        evaluator_id: int
    ) -> RequirementPriorityEvaluation:
        """评估需求优先级"""
        # 验证需求存在
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        requirement = await req_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError("需求不存在")
        
        # 获取配置
        config = await self.config_repo.get_by_id(evaluation_data.config_id)
        if not config:
            raise ValueError("优先级配置不存在")
        
        # 计算加权得分
        weighted_score = self._calculate_weighted_score(evaluation_data, config)
        
        # 根据得分确定优先级
        calculated_priority = self._determine_priority_by_score(weighted_score, config)
        
        # 最终优先级（可能经过手动调整）
        final_priority = evaluation_data.manual_priority or calculated_priority
        
        # 创建评估记录
        evaluation = RequirementPriorityEvaluation(
            requirement_id=requirement_id,
            config_id=evaluation_data.config_id,
            business_value_score=evaluation_data.business_value_score,
            user_impact_score=evaluation_data.user_impact_score,
            technical_risk_score=evaluation_data.technical_risk_score,
            implementation_cost_score=evaluation_data.implementation_cost_score,
            time_urgency_score=evaluation_data.time_urgency_score,
            weighted_score=weighted_score,
            calculated_priority=calculated_priority,
            final_priority=final_priority,
            evaluation_method=config.calculation_method,
            evaluation_reason=evaluation_data.evaluation_reason,
            manual_adjustment_reason=evaluation_data.manual_adjustment_reason,
            evaluator_id=evaluator_id,
            evaluated_at=datetime.utcnow(),
            evaluation_data=evaluation_data.additional_data,
            created_by=evaluator_id
        )
        
        saved_evaluation = await self.evaluation_repo.create(evaluation)
        
        # 设置为当前有效评估
        await self.evaluation_repo.set_current_evaluation(requirement_id, saved_evaluation.id)
        
        # 更新需求的优先级
        old_priority = requirement.priority
        requirement.priority = final_priority
        await req_repo.update(requirement)
        
        # 记录优先级变更历史
        if old_priority != final_priority:
            await self._record_priority_change(
                requirement_id, old_priority, final_priority,
                config.calculation_method, "优先级评估", evaluator_id, weighted_score
            )
        
        # 检测优先级冲突
        await self._detect_priority_conflicts(requirement_id, final_priority)
        
        return saved_evaluation
    
    async def get_requirement_priority_evaluation(self, requirement_id: int) -> Optional[RequirementPriorityEvaluation]:
        """获取需求的当前优先级评估"""
        return await self.evaluation_repo.get_current_evaluation(requirement_id)
    
    async def get_priority_evaluation_history(self, requirement_id: int) -> List[RequirementPriorityEvaluation]:
        """获取需求的优先级评估历史"""
        return await self.evaluation_repo.get_evaluations_by_requirement(requirement_id)    

    # 智能优先级分析
    async def analyze_priority_with_ai(
        self,
        requirement_id: int,
        project_id: int
    ) -> Dict[str, Any]:
        """使用AI分析需求优先级"""
        if not self.ai_service:
            raise ValueError("AI服务不可用")
        
        # 获取需求信息
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        requirement = await req_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError("需求不存在")
        
        # 获取项目的默认优先级配置
        config = await self.get_default_priority_config(project_id)
        if not config:
            raise ValueError("项目没有配置优先级评估规则")
        
        # 构建AI分析提示词
        prompt = f"""
        请分析以下需求的优先级，并为各个评估因子打分(0-10分)：
        
        需求信息：
        标题：{requirement.title}
        描述：{requirement.description or '无描述'}
        需求类型：{requirement.requirement_type.value if requirement.requirement_type else '未指定'}
        当前优先级：{requirement.priority.value if requirement.priority else '未设置'}
        
        评估因子权重：
        - 商业价值权重：{float(config.business_value_weight)}
        - 用户影响权重：{float(config.user_impact_weight)}
        - 技术风险权重：{float(config.technical_risk_weight)}
        - 实现成本权重：{float(config.implementation_cost_weight)}
        - 时间紧迫性权重：{float(config.time_urgency_weight)}
        
        请返回JSON格式的分析结果，包含：
        - business_value_score: 商业价值得分(0-10)
        - user_impact_score: 用户影响得分(0-10)
        - technical_risk_score: 技术风险得分(0-10)
        - implementation_cost_score: 实现成本得分(0-10)
        - time_urgency_score: 时间紧迫性得分(0-10)
        - reasoning: 分析理由
        - recommended_priority: 推荐优先级(CRITICAL/HIGH/MEDIUM/LOW/OPTIONAL)
        """
        
        try:
            # 调用AI服务
            ai_response = await self.ai_service.generate_response(
                prompt=prompt,
                context_data={
                    'requirement_id': requirement_id,
                    'project_id': project_id
                }
            )
            
            # 解析AI响应
            import json
            analysis_data = json.loads(ai_response.get('content', '{}'))
            
            # 计算加权得分
            weighted_score = (
                analysis_data.get('business_value_score', 5) * float(config.business_value_weight) +
                analysis_data.get('user_impact_score', 5) * float(config.user_impact_weight) +
                analysis_data.get('technical_risk_score', 5) * float(config.technical_risk_weight) +
                analysis_data.get('implementation_cost_score', 5) * float(config.implementation_cost_weight) +
                analysis_data.get('time_urgency_score', 5) * float(config.time_urgency_weight)
            )
            
            # 根据得分确定优先级
            calculated_priority = self._determine_priority_by_score(weighted_score, config)
            
            return {
                'business_value_score': analysis_data.get('business_value_score', 5),
                'user_impact_score': analysis_data.get('user_impact_score', 5),
                'technical_risk_score': analysis_data.get('technical_risk_score', 5),
                'implementation_cost_score': analysis_data.get('implementation_cost_score', 5),
                'time_urgency_score': analysis_data.get('time_urgency_score', 5),
                'weighted_score': weighted_score,
                'calculated_priority': calculated_priority.value,
                'recommended_priority': analysis_data.get('recommended_priority', calculated_priority.value),
                'reasoning': analysis_data.get('reasoning', '基于AI分析的优先级建议'),
                'config_id': config.id
            }
            
        except Exception as e:
            raise ValueError(f"AI优先级分析失败: {e}")
    
    # 优先级冲突管理
    async def detect_priority_conflicts(self, project_id: int) -> List[RequirementPriorityConflict]:
        """检测项目中的优先级冲突"""
        # 获取项目的所有需求及其优先级评估
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        requirements = await req_repo.get_by_project_id(project_id)
        
        conflicts = []
        
        # 检测高优先级需求过多的冲突
        high_priority_reqs = [
            req for req in requirements 
            if req.priority in [Priority.CRITICAL, Priority.HIGH]
        ]
        
        if len(high_priority_reqs) > len(requirements) * 0.3:  # 超过30%为高优先级
            conflict = await self._create_priority_conflict(
                requirement_ids=[req.id for req in high_priority_reqs],
                conflict_type="HIGH_PRIORITY_OVERLOAD",
                description=f"项目中有{len(high_priority_reqs)}个高优先级需求，占比{len(high_priority_reqs)/len(requirements)*100:.1f}%，可能存在优先级通胀问题",
                severity_level=3
            )
            conflicts.append(conflict)
        
        # 检测相似需求优先级不一致的冲突
        # 这里可以添加更复杂的冲突检测逻辑
        
        return conflicts

    async def get_active_conflicts(self) -> List[RequirementPriorityConflict]:
        """获取活跃的优先级冲突"""
        return await self.conflict_repo.get_active_conflicts()
    
    async def resolve_priority_conflict(
        self,
        conflict_id: int,
        resolution_data: ConflictResolutionRequest,
        resolver_id: int
    ) -> bool:
        """解决优先级冲突"""
        conflict = await self.conflict_repo.get_by_id(conflict_id)
        if not conflict:
            raise ValueError("优先级冲突不存在")
        
        # 根据解决策略执行相应操作
        if resolution_data.resolution_strategy == ConflictResolutionStrategy.MANUAL_REVIEW:
            # 手动解决，只更新冲突状态
            await self.conflict_repo.resolve_conflict(
                conflict_id, resolver_id, resolution_data.resolution_notes
            )
        
        elif resolution_data.resolution_strategy == ConflictResolutionStrategy.HIGHEST_PRIORITY:
            # 将所有冲突需求设为最高优先级
            await self._apply_priority_resolution(
                conflict.requirement_ids, Priority.CRITICAL, resolver_id
            )
            await self.conflict_repo.resolve_conflict(
                conflict_id, resolver_id, "应用最高优先级策略"
            )
        
        elif resolution_data.resolution_strategy == ConflictResolutionStrategy.WEIGHTED_AVERAGE:
            # 根据加权平均重新计算优先级
            await self._apply_weighted_average_resolution(
                conflict.requirement_ids, resolver_id
            )
            await self.conflict_repo.resolve_conflict(
                conflict_id, resolver_id, "应用加权平均策略"
            )
        
        return True
    
    # 优先级历史管理
    async def get_priority_change_history(self, requirement_id: int) -> List[RequirementPriorityHistory]:
        """获取需求的优先级变更历史"""
        return await self.history_repo.get_priority_history(requirement_id)
    
    async def get_recent_priority_changes(self, days: int = 7) -> List[RequirementPriorityHistory]:
        """获取最近的优先级变更"""
        return await self.history_repo.get_recent_changes(days)
    
    # 统计分析
    async def get_priority_distribution(self, project_id: int) -> Dict[str, int]:
        """获取项目的优先级分布"""
        return await self.evaluation_repo.get_priority_distribution(project_id)
    
    # 私有方法
    def _calculate_weighted_score(
        self,
        evaluation_data: EvaluatePriorityRequest,
        config: RequirementPriorityConfig
    ) -> Decimal:
        """计算加权得分"""
        score = (
            evaluation_data.business_value_score * config.business_value_weight +
            evaluation_data.user_impact_score * config.user_impact_weight +
            evaluation_data.technical_risk_score * config.technical_risk_weight +
            evaluation_data.implementation_cost_score * config.implementation_cost_weight +
            evaluation_data.time_urgency_score * config.time_urgency_weight
        )
        return Decimal(str(round(score, 2)))
    
    def _determine_priority_by_score(
        self,
        weighted_score: Decimal,
        config: RequirementPriorityConfig
    ) -> Priority:
        """根据得分确定优先级"""
        score_float = float(weighted_score)
        
        if score_float >= float(config.critical_threshold):
            return Priority.CRITICAL
        elif score_float >= float(config.high_threshold):
            return Priority.HIGH
        elif score_float >= float(config.medium_threshold):
            return Priority.MEDIUM
        elif score_float >= float(config.low_threshold):
            return Priority.LOW
        else:
            return Priority.OPTIONAL

    async def _record_priority_change(
        self,
        requirement_id: int,
        old_priority: Optional[Priority],
        new_priority: Priority,
        change_method: PriorityCalculationMethod,
        change_trigger: str,
        changed_by: int,
        new_weighted_score: Optional[Decimal] = None,
        old_weighted_score: Optional[Decimal] = None
    ) -> RequirementPriorityHistory:
        """记录优先级变更历史"""
        history = RequirementPriorityHistory(
            requirement_id=requirement_id,
            old_priority=old_priority,
            new_priority=new_priority,
            change_method=change_method,
            change_trigger=change_trigger,
            old_weighted_score=old_weighted_score,
            new_weighted_score=new_weighted_score,
            changed_by=changed_by
        )
        
        return await self.history_repo.create(history)
    
    async def _detect_priority_conflicts(
        self,
        requirement_id: int,
        priority: Priority
    ) -> None:
        """检测单个需求的优先级冲突"""
        # 这里可以实现更复杂的冲突检测逻辑
        # 例如检测依赖需求的优先级是否合理等
        pass
    
    async def _create_priority_conflict(
        self,
        requirement_ids: List[int],
        conflict_type: str,
        description: str,
        severity_level: int
    ) -> RequirementPriorityConflict:
        """创建优先级冲突记录"""
        conflict = RequirementPriorityConflict(
            requirement_ids=requirement_ids,
            conflict_type=conflict_type,
            conflict_description=description,
            severity_level=severity_level,
            detected_by_system=True,
            detection_algorithm="SYSTEM_RULE_BASED",
            detection_confidence=Decimal("0.85")
        )
        
        return await self.conflict_repo.create(conflict)
    
    async def _clear_default_configs(self, project_id: int) -> None:
        """清除项目的其他默认配置"""
        configs = await self.config_repo.get_by_project_id(project_id)
        for config in configs:
            if config.is_default:
                config.is_default = False
                await self.config_repo.update(config)
    
    async def _apply_priority_resolution(
        self,
        requirement_ids: List[int],
        new_priority: Priority,
        resolver_id: int
    ) -> None:
        """应用优先级解决方案"""
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        
        for req_id in requirement_ids:
            requirement = await req_repo.get_by_id(req_id)
            if requirement:
                old_priority = requirement.priority
                requirement.priority = new_priority
                await req_repo.update(requirement)
                
                # 记录变更历史
                await self._record_priority_change(
                    req_id, old_priority, new_priority,
                    PriorityCalculationMethod.MANUAL, "冲突解决", resolver_id
                )
    
    async def _apply_weighted_average_resolution(
        self,
        requirement_ids: List[int],
        resolver_id: int
    ) -> None:
        """应用加权平均解决方案"""
        # 获取所有需求的当前评估
        evaluations = []
        for req_id in requirement_ids:
            evaluation = await self.evaluation_repo.get_current_evaluation(req_id)
            if evaluation:
                evaluations.append(evaluation)
        
        if not evaluations:
            return
        
        # 计算平均加权得分
        total_score = sum(float(eval.weighted_score) for eval in evaluations)
        avg_score = total_score / len(evaluations)
        
        # 根据平均得分重新确定优先级
        config = evaluations[0].config  # 假设使用相同配置
        new_priority = self._determine_priority_by_score(Decimal(str(avg_score)), config)
        
        # 应用新优先级
        await self._apply_priority_resolution(requirement_ids, new_priority, resolver_id)
