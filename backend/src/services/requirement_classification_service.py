"""
需求分类管理服务

提供需求分类相关的业务逻辑，包括：
- 多维度分类管理
- 智能分类建议
- 分类标签系统
- 分类统计分析
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.requirement_classification_repository import (
    RequirementClassificationRepository,
    RequirementClassificationCategoryRepository,
    RequirementClassificationAssignmentRepository,
    RequirementClassificationSuggestionRepository,
    RequirementTagRepository
)
from ..models.requirement_classification import (
    RequirementClassificationDimension, RequirementClassificationCategory,
    RequirementClassification, RequirementClassificationSuggestion,
    RequirementTag, RequirementTagAssignment,
    ClassificationDimension, ClassificationStatus, ClassificationSuggestionStatus
)
from ..models.requirement import Requirement
from ..schemas.requirement_classification import (
    CreateClassificationDimensionRequest, UpdateClassificationDimensionRequest,
    CreateClassificationCategoryRequest, UpdateClassificationCategoryRequest,
    ClassifyRequirementRequest, ClassificationSuggestionResponse
)
from .ai_assistant_service import AIAssistantService


class RequirementClassificationService:
    """需求分类管理服务"""
    
    def __init__(
        self,
        session: AsyncSession,
        ai_service: Optional[AIAssistantService] = None
    ):
        self.session = session
        self.ai_service = ai_service
        
        # 初始化仓储
        self.dimension_repo = RequirementClassificationRepository(session)
        self.category_repo = RequirementClassificationCategoryRepository(session)
        self.assignment_repo = RequirementClassificationAssignmentRepository(session)
        self.suggestion_repo = RequirementClassificationSuggestionRepository(session)
        self.tag_repo = RequirementTagRepository(session)
    
    # 分类维度管理
    async def create_classification_dimension(
        self,
        dimension_data: CreateClassificationDimensionRequest,
        creator_id: int
    ) -> RequirementClassificationDimension:
        """创建分类维度"""
        # 检查维度编码是否已存在
        existing = await self.dimension_repo.get_dimension_by_code(dimension_data.dimension_code)
        if existing:
            raise ValueError(f"维度编码 {dimension_data.dimension_code} 已存在")
        
        dimension = RequirementClassificationDimension(
            dimension_code=dimension_data.dimension_code,
            dimension_name=dimension_data.dimension_name,
            dimension_type=dimension_data.dimension_type,
            description=dimension_data.description,
            is_hierarchical=dimension_data.is_hierarchical,
            is_multi_select=dimension_data.is_multi_select,
            is_required=dimension_data.is_required,
            sort_order=dimension_data.sort_order,
            config_data=dimension_data.config_data,
            created_by=creator_id
        )
        
        return await self.dimension_repo.create(dimension)
    
    async def get_active_dimensions(self) -> List[RequirementClassificationDimension]:
        """获取激活的分类维度"""
        return await self.dimension_repo.get_active_dimensions()
    
    async def update_classification_dimension(
        self,
        dimension_id: int,
        dimension_data: UpdateClassificationDimensionRequest,
        updater_id: int
    ) -> RequirementClassificationDimension:
        """更新分类维度"""
        dimension = await self.dimension_repo.get_by_id(dimension_id)
        if not dimension:
            raise ValueError("分类维度不存在")
        
        # 更新字段
        if dimension_data.dimension_name is not None:
            dimension.dimension_name = dimension_data.dimension_name
        if dimension_data.description is not None:
            dimension.description = dimension_data.description
        if dimension_data.is_hierarchical is not None:
            dimension.is_hierarchical = dimension_data.is_hierarchical
        if dimension_data.is_multi_select is not None:
            dimension.is_multi_select = dimension_data.is_multi_select
        if dimension_data.is_required is not None:
            dimension.is_required = dimension_data.is_required
        if dimension_data.sort_order is not None:
            dimension.sort_order = dimension_data.sort_order
        if dimension_data.status is not None:
            dimension.status = dimension_data.status
        if dimension_data.config_data is not None:
            dimension.config_data = dimension_data.config_data
        
        dimension.updated_by = updater_id
        
        return await self.dimension_repo.update(dimension)  
  
    # 分类类别管理
    async def create_classification_category(
        self,
        category_data: CreateClassificationCategoryRequest,
        creator_id: int
    ) -> RequirementClassificationCategory:
        """创建分类类别"""
        # 验证维度存在
        dimension = await self.dimension_repo.get_by_id(category_data.dimension_id)
        if not dimension:
            raise ValueError("分类维度不存在")
        
        # 检查类别编码在维度内是否唯一
        existing = await self.category_repo.get_by_code(
            category_data.category_code, 
            category_data.dimension_id
        )
        if existing:
            raise ValueError(f"类别编码 {category_data.category_code} 在该维度下已存在")
        
        # 处理层级信息
        level = 1
        path = category_data.category_code
        
        if category_data.parent_id:
            parent = await self.category_repo.get_by_id(category_data.parent_id)
            if not parent or parent.dimension_id != category_data.dimension_id:
                raise ValueError("父类别不存在或不属于同一维度")
            
            level = parent.level + 1
            path = f"{parent.path}/{category_data.category_code}"
        
        category = RequirementClassificationCategory(
            dimension_id=category_data.dimension_id,
            parent_id=category_data.parent_id,
            category_code=category_data.category_code,
            category_name=category_data.category_name,
            description=category_data.description,
            level=level,
            path=path,
            sort_order=category_data.sort_order,
            attributes=category_data.attributes,
            created_by=creator_id
        )
        
        return await self.category_repo.create(category)
    
    async def get_category_tree(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """获取分类类别树"""
        return await self.dimension_repo.get_category_tree(dimension_id)
    
    async def get_categories_by_dimension(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """根据维度获取类别列表"""
        return await self.dimension_repo.get_categories_by_dimension(dimension_id)    
    
# 需求分类管理
    async def classify_requirement(
        self,
        requirement_id: int,
        classification_data: ClassifyRequirementRequest,
        classifier_id: int
    ) -> List[RequirementClassification]:
        """为需求分配分类"""
        # 验证需求存在
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        requirement = await req_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError("需求不存在")
        
        # 移除现有分类（如果指定）
        if classification_data.replace_existing:
            existing_classifications = await self.assignment_repo.get_requirement_classifications(requirement_id)
            if existing_classifications:
                category_ids = [c.category_id for c in existing_classifications]
                await self.assignment_repo.remove_requirement_classifications(requirement_id, category_ids)
        
        # 添加新分类
        new_classifications = []
        for category_id in classification_data.category_ids:
            # 验证类别存在
            category = await self.category_repo.get_by_id(category_id)
            if not category:
                continue
            
            # 检查是否已存在
            existing = await self.assignment_repo.get_by_fields({
                'requirement_id': requirement_id,
                'category_id': category_id
            })
            if existing:
                continue
            
            classification = RequirementClassification(
                requirement_id=requirement_id,
                category_id=category_id,
                confidence_score=classification_data.confidence_score,
                is_auto_classified=classification_data.is_auto_classified,
                classification_reason=classification_data.classification_reason,
                created_by=classifier_id
            )
            
            saved_classification = await self.assignment_repo.create(classification)
            new_classifications.append(saved_classification)
            
            # 更新类别使用次数
            await self.category_repo.update_usage_count(category_id, 1)
        
        return new_classifications
    
    async def get_requirement_classifications(self, requirement_id: int) -> List[RequirementClassification]:
        """获取需求的分类"""
        return await self.assignment_repo.get_requirement_classifications(requirement_id)
    
    async def remove_requirement_classification(
        self,
        requirement_id: int,
        category_id: int,
        remover_id: int
    ) -> bool:
        """移除需求分类"""
        await self.assignment_repo.remove_requirement_classifications(requirement_id, [category_id])
        
        # 更新类别使用次数
        await self.category_repo.update_usage_count(category_id, -1)
        
        return True    
 
   # 智能分类建议
    async def generate_classification_suggestions(
        self,
        requirement_id: int,
        suggester_id: Optional[int] = None
    ) -> List[RequirementClassificationSuggestion]:
        """生成智能分类建议"""
        if not self.ai_service:
            return []
        
        # 获取需求信息
        from ..repositories.requirement_repository import RequirementRepository
        req_repo = RequirementRepository(self.session)
        requirement = await req_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError("需求不存在")
        
        # 获取所有激活的分类维度和类别
        dimensions = await self.get_active_dimensions()
        
        suggestions = []
        for dimension in dimensions:
            categories = await self.get_categories_by_dimension(dimension.id)
            if not categories:
                continue
            
            # 使用AI分析需求并生成分类建议
            try:
                ai_suggestions = await self._analyze_requirement_for_classification(
                    requirement, dimension, categories
                )
                
                for ai_suggestion in ai_suggestions:
                    # 检查建议是否已存在
                    existing = await self.suggestion_repo.get_by_fields({
                        'requirement_id': requirement_id,
                        'category_id': ai_suggestion['category_id'],
                        'status': ClassificationSuggestionStatus.PENDING
                    })
                    if existing:
                        continue
                    
                    suggestion = RequirementClassificationSuggestion(
                        requirement_id=requirement_id,
                        category_id=ai_suggestion['category_id'],
                        suggestion_type='AI_SUGGESTION',
                        confidence_score=ai_suggestion['confidence_score'],
                        reasoning=ai_suggestion['reasoning'],
                        expires_at=datetime.utcnow() + timedelta(days=30),
                        created_by=suggester_id
                    )
                    
                    saved_suggestion = await self.suggestion_repo.create(suggestion)
                    suggestions.append(saved_suggestion)
                    
            except Exception as e:
                # 记录错误但不中断流程
                print(f"AI分类建议生成失败: {e}")
                continue
        
        return suggestions
    
    async def get_pending_suggestions(self, requirement_id: int) -> List[RequirementClassificationSuggestion]:
        """获取待处理的分类建议"""
        return await self.suggestion_repo.get_pending_suggestions(requirement_id)
    
    async def accept_classification_suggestion(
        self,
        suggestion_id: int,
        accepter_id: int,
        feedback: Optional[str] = None
    ) -> RequirementClassification:
        """接受分类建议"""
        suggestion = await self.suggestion_repo.get_by_id(suggestion_id)
        if not suggestion:
            raise ValueError("分类建议不存在")
        
        if suggestion.status != ClassificationSuggestionStatus.PENDING:
            raise ValueError("建议已被处理")
        
        # 创建分类关联
        classification = RequirementClassification(
            requirement_id=suggestion.requirement_id,
            category_id=suggestion.category_id,
            confidence_score=suggestion.confidence_score,
            is_auto_classified=True,
            classification_reason=f"接受AI建议: {suggestion.reasoning}",
            created_by=accepter_id
        )
        
        saved_classification = await self.assignment_repo.create(classification)
        
        # 更新建议状态
        suggestion.status = ClassificationSuggestionStatus.ACCEPTED
        suggestion.processed_by = accepter_id
        suggestion.processed_at = datetime.utcnow()
        suggestion.feedback = feedback
        await self.suggestion_repo.update(suggestion)
        
        # 更新类别使用次数
        await self.category_repo.update_usage_count(suggestion.category_id, 1)
        
        return saved_classification    

    async def reject_classification_suggestion(
        self,
        suggestion_id: int,
        rejecter_id: int,
        feedback: Optional[str] = None
    ) -> bool:
        """拒绝分类建议"""
        suggestion = await self.suggestion_repo.get_by_id(suggestion_id)
        if not suggestion:
            raise ValueError("分类建议不存在")
        
        if suggestion.status != ClassificationSuggestionStatus.PENDING:
            raise ValueError("建议已被处理")
        
        # 更新建议状态
        suggestion.status = ClassificationSuggestionStatus.REJECTED
        suggestion.processed_by = rejecter_id
        suggestion.processed_at = datetime.utcnow()
        suggestion.feedback = feedback
        await self.suggestion_repo.update(suggestion)
        
        return True
    
    # 标签管理
    async def create_tag(
        self,
        tag_name: str,
        tag_color: Optional[str] = None,
        description: Optional[str] = None,
        creator_id: int = None
    ) -> RequirementTag:
        """创建标签"""
        # 检查标签是否已存在
        existing = await self.tag_repo.get_by_name(tag_name)
        if existing:
            raise ValueError(f"标签 {tag_name} 已存在")
        
        tag = RequirementTag(
            tag_name=tag_name,
            tag_color=tag_color,
            description=description,
            created_by=creator_id
        )
        
        return await self.tag_repo.create(tag)
    
    async def get_popular_tags(self, limit: int = 20) -> List[RequirementTag]:
        """获取热门标签"""
        return await self.tag_repo.get_popular_tags(limit)
    
    async def search_tags(self, keyword: str) -> List[RequirementTag]:
        """搜索标签"""
        return await self.tag_repo.search_tags(keyword)
    
    # 统计分析
    async def get_classification_statistics(self, dimension_id: int) -> Dict[str, Any]:
        """获取分类统计信息"""
        return await self.assignment_repo.get_classification_statistics(dimension_id)
    
    # 私有方法
    async def _analyze_requirement_for_classification(
        self,
        requirement: Requirement,
        dimension: RequirementClassificationDimension,
        categories: List[RequirementClassificationCategory]
    ) -> List[Dict[str, Any]]:
        """使用AI分析需求并生成分类建议"""
        if not self.ai_service:
            return []
        
        # 构建分析提示词
        category_info = "\n".join([
            f"- {cat.category_code}: {cat.category_name} - {cat.description or '无描述'}"
            for cat in categories
        ])
        
        prompt = f"""
        请分析以下需求，并为其在"{dimension.dimension_name}"维度下推荐合适的分类。
        
        需求信息：
        标题：{requirement.title}
        描述：{requirement.description or '无描述'}
        验收标准：{requirement.acceptance_criteria or '无验收标准'}
        需求类型：{requirement.requirement_type.value if requirement.requirement_type else '未指定'}
        
        可选分类：
        {category_info}
        
        请返回JSON格式的建议，包含以下字段：
        - category_code: 推荐的分类编码
        - confidence_score: 置信度(0-1)
        - reasoning: 推荐理由
        
        只返回置信度大于0.6的建议，最多返回3个建议。
        """
        
        try:
            # 调用AI服务
            ai_response = await self.ai_service.generate_response(
                prompt=prompt,
                context_data={
                    'requirement_id': requirement.id,
                    'dimension_id': dimension.id
                }
            )
            
            # 解析AI响应
            import json
            suggestions_data = json.loads(ai_response.get('content', '[]'))
            
            # 转换为标准格式
            suggestions = []
            for suggestion_data in suggestions_data:
                # 根据category_code找到对应的category_id
                category = next(
                    (cat for cat in categories if cat.category_code == suggestion_data.get('category_code')),
                    None
                )
                if category and suggestion_data.get('confidence_score', 0) > 0.6:
                    suggestions.append({
                        'category_id': category.id,
                        'confidence_score': suggestion_data.get('confidence_score', 0.7),
                        'reasoning': suggestion_data.get('reasoning', '基于AI分析的建议')
                    })
            
            return suggestions
            
        except Exception as e:
            print(f"AI分类分析失败: {e}")
            return []