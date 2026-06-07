"""
中文提示词优化API端点

提供中文提示词优化的REST API接口，包括：
1. 提示词优化
2. 中文模板创建
3. 优化配置管理
4. 质量评估

API端点：
- POST /api/v1/chinese-prompt/optimize - 优化提示词
- POST /api/v1/chinese-prompt/create-templates - 创建中文优化模板
- GET /api/v1/chinese-prompt/optimization-config - 获取优化配置
- PUT /api/v1/chinese-prompt/optimization-config - 更新优化配置
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

from ...core.database import get_db
from ...core.auth import get_current_user
from ...services.chinese_prompt_optimizer import (
    get_chinese_prompt_optimizer,
    ChinesePromptOptimizer,
    ChineseOptimizationConfig,
    ChineseFormalityLevel,
    ChineseContextType
)
from ...services.prompt_service import PromptService
from ...services.multilingual_response_service import get_multilingual_response_service
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


# Pydantic模型定义
class PromptOptimizationRequest(BaseModel):
    """提示词优化请求"""
    original_prompt: str = Field(..., description="原始提示词", min_length=1, max_length=10000)
    formality_level: ChineseFormalityLevel = Field(
        ChineseFormalityLevel.SEMI_FORMAL, 
        description="正式程度"
    )
    context_type: ChineseContextType = Field(
        ChineseContextType.TECHNICAL, 
        description="上下文类型"
    )
    use_honorifics: bool = Field(True, description="使用敬语")
    prefer_classical_expressions: bool = Field(False, description="偏好古典表达")
    include_cultural_context: bool = Field(True, description="包含文化背景")
    optimize_for_ai_understanding: bool = Field(True, description="针对AI理解优化")
    target_audience: str = Field("专业用户", description="目标受众")
    domain_specific: Optional[str] = Field(None, description="专业领域")


class PromptOptimizationResponse(BaseModel):
    """提示词优化响应"""
    original_prompt: str = Field(..., description="原始提示词")
    optimized_prompt: str = Field(..., description="优化后的提示词")
    optimization_applied: List[str] = Field(..., description="应用的优化策略")
    quality_improvement: Dict[str, Any] = Field(..., description="质量改进指标")
    suggestions: List[str] = Field(..., description="进一步优化建议")


class CreateTemplatesRequest(BaseModel):
    """创建模板请求"""
    template_types: Optional[List[str]] = Field(
        None, 
        description="要创建的模板类型，为空则创建所有类型"
    )
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置")


class CreateTemplatesResponse(BaseModel):
    """创建模板响应"""
    created_templates: List[Dict[str, Any]] = Field(..., description="创建的模板列表")
    total_count: int = Field(..., description="创建的模板总数")
    success_count: int = Field(..., description="成功创建的模板数")
    failed_templates: List[Dict[str, str]] = Field(..., description="创建失败的模板")


class OptimizationConfigResponse(BaseModel):
    """优化配置响应"""
    formality_level: ChineseFormalityLevel = Field(..., description="正式程度")
    context_type: ChineseContextType = Field(..., description="上下文类型")
    use_honorifics: bool = Field(..., description="使用敬语")
    prefer_classical_expressions: bool = Field(..., description="偏好古典表达")
    include_cultural_context: bool = Field(..., description="包含文化背景")
    optimize_for_ai_understanding: bool = Field(..., description="针对AI理解优化")
    target_audience: str = Field(..., description="目标受众")
    domain_specific: Optional[str] = Field(None, description="专业领域")


@router.post("/optimize",
            response_model=PromptOptimizationResponse,
            summary="优化中文提示词",
            description="根据指定配置优化中文提示词，提升AI理解效果和文化适配性")
async def optimize_chinese_prompt(
    request: PromptOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """优化中文提示词"""
    try:
        logger.info(f"Chinese prompt optimization request from user {current_user.id}")
        
        # 获取服务实例
        prompt_service = PromptService()
        multilingual_service = await get_multilingual_response_service(db)
        optimizer = await get_chinese_prompt_optimizer(prompt_service, multilingual_service)
        
        # 创建优化配置
        config = ChineseOptimizationConfig(
            formality_level=request.formality_level,
            context_type=request.context_type,
            use_honorifics=request.use_honorifics,
            prefer_classical_expressions=request.prefer_classical_expressions,
            include_cultural_context=request.include_cultural_context,
            optimize_for_ai_understanding=request.optimize_for_ai_understanding,
            target_audience=request.target_audience,
            domain_specific=request.domain_specific
        )
        
        # 执行优化
        optimized_prompt = await optimizer.optimize_chinese_prompt(
            request.original_prompt, config
        )
        
        # 分析优化效果
        optimization_applied = []
        if request.formality_level != ChineseFormalityLevel.CASUAL:
            optimization_applied.append("正式程度调整")
        if request.include_cultural_context:
            optimization_applied.append("文化背景适配")
        if request.optimize_for_ai_understanding:
            optimization_applied.append("AI理解优化")
        if request.domain_specific:
            optimization_applied.append("专业术语优化")
        
        # 质量改进指标
        quality_improvement = {
            "length_change": len(optimized_prompt) - len(request.original_prompt),
            "formality_enhanced": request.formality_level != ChineseFormalityLevel.CASUAL,
            "cultural_adapted": request.include_cultural_context,
            "ai_optimized": request.optimize_for_ai_understanding
        }
        
        # 进一步优化建议
        suggestions = []
        if len(optimized_prompt) > 1000:
            suggestions.append("考虑简化提示词长度以提高处理效率")
        if request.context_type == ChineseContextType.TECHNICAL and not request.domain_specific:
            suggestions.append("建议指定具体的技术领域以获得更精准的优化")
        if not request.use_honorifics and request.formality_level in [ChineseFormalityLevel.FORMAL, ChineseFormalityLevel.VERY_FORMAL]:
            suggestions.append("在正式场合建议使用敬语以提升礼貌程度")
        
        return PromptOptimizationResponse(
            original_prompt=request.original_prompt,
            optimized_prompt=optimized_prompt,
            optimization_applied=optimization_applied,
            quality_improvement=quality_improvement,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Error optimizing Chinese prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"中文提示词优化失败: {str(e)}"
        )


@router.post("/create-templates",
            response_model=CreateTemplatesResponse,
            summary="创建中文优化模板",
            description="批量创建针对中文优化的提示词模板")
async def create_chinese_templates(
    request: CreateTemplatesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建中文优化模板"""
    try:
        logger.info(f"Create Chinese templates request from user {current_user.id}")
        
        # 获取服务实例
        prompt_service = PromptService()
        multilingual_service = await get_multilingual_response_service(db)
        optimizer = await get_chinese_prompt_optimizer(prompt_service, multilingual_service)
        
        # 创建模板
        created_templates = await optimizer.create_optimized_chinese_templates(db, current_user.id)
        
        # 统计结果
        success_count = len([t for t in created_templates if "template" in t])
        failed_templates = [
            {"type": t.get("type", "unknown"), "error": t.get("error", "未知错误")}
            for t in created_templates if "error" in t
        ]
        
        return CreateTemplatesResponse(
            created_templates=created_templates,
            total_count=len(created_templates),
            success_count=success_count,
            failed_templates=failed_templates
        )
        
    except Exception as e:
        logger.error(f"Error creating Chinese templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建中文模板失败: {str(e)}"
        )


@router.get("/optimization-config",
           response_model=OptimizationConfigResponse,
           summary="获取优化配置",
           description="获取当前用户的中文提示词优化配置")
async def get_optimization_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取优化配置"""
    try:
        logger.info(f"Get optimization config request from user {current_user.id}")
        
        # 从用户偏好或默认配置获取
        # 这里可以扩展为从数据库读取用户的个性化配置
        default_config = ChineseOptimizationConfig()
        
        return OptimizationConfigResponse(
            formality_level=default_config.formality_level,
            context_type=default_config.context_type,
            use_honorifics=default_config.use_honorifics,
            prefer_classical_expressions=default_config.prefer_classical_expressions,
            include_cultural_context=default_config.include_cultural_context,
            optimize_for_ai_understanding=default_config.optimize_for_ai_understanding,
            target_audience=default_config.target_audience,
            domain_specific=default_config.domain_specific
        )
        
    except Exception as e:
        logger.error(f"Error getting optimization config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取优化配置失败: {str(e)}"
        )


@router.put("/optimization-config",
           response_model=OptimizationConfigResponse,
           summary="更新优化配置",
           description="更新当前用户的中文提示词优化配置")
async def update_optimization_config(
    config_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新优化配置"""
    try:
        logger.info(f"Update optimization config request from user {current_user.id}")
        
        # 验证配置参数
        valid_keys = {
            "formality_level", "context_type", "use_honorifics", 
            "prefer_classical_expressions", "include_cultural_context",
            "optimize_for_ai_understanding", "target_audience", "domain_specific"
        }
        
        invalid_keys = set(config_update.keys()) - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的配置参数: {', '.join(invalid_keys)}"
            )
        
        # 这里可以扩展为保存到数据库
        # 目前返回更新后的配置
        updated_config = ChineseOptimizationConfig()
        
        # 应用更新
        for key, value in config_update.items():
            if hasattr(updated_config, key):
                if key == "formality_level":
                    updated_config.formality_level = ChineseFormalityLevel(value)
                elif key == "context_type":
                    updated_config.context_type = ChineseContextType(value)
                else:
                    setattr(updated_config, key, value)
        
        return OptimizationConfigResponse(
            formality_level=updated_config.formality_level,
            context_type=updated_config.context_type,
            use_honorifics=updated_config.use_honorifics,
            prefer_classical_expressions=updated_config.prefer_classical_expressions,
            include_cultural_context=updated_config.include_cultural_context,
            optimize_for_ai_understanding=updated_config.optimize_for_ai_understanding,
            target_audience=updated_config.target_audience,
            domain_specific=updated_config.domain_specific
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating optimization config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新优化配置失败: {str(e)}"
        )


@router.get("/template-categories",
           summary="获取模板分类",
           description="获取中文优化模板的分类信息")
async def get_template_categories():
    """获取模板分类"""
    try:
        categories = {
            "test_case": {
                "name": "测试用例生成",
                "description": "生成详细的中文测试用例，包含完整的测试场景和验证步骤",
                "use_cases": ["功能测试", "回归测试", "验收测试"]
            },
            "requirement_analysis": {
                "name": "需求分析",
                "description": "分析需求文档质量，提供改进建议和质量评估",
                "use_cases": ["需求评审", "质量分析", "项目管理"]
            },
            "code_review": {
                "name": "代码审查",
                "description": "全面的代码质量分析和改进建议",
                "use_cases": ["代码审查", "质量控制", "团队协作"]
            },
            "document_generation": {
                "name": "文档生成",
                "description": "生成标准化的中文技术文档",
                "use_cases": ["技术文档", "用户手册", "API文档"]
            },
            "problem_analysis": {
                "name": "问题分析",
                "description": "系统化的问题诊断和解决方案",
                "use_cases": ["问题诊断", "根因分析", "解决方案"]
            }
        }
        
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Error getting template categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模板分类失败: {str(e)}"
        )


@router.get("/optimization-rules",
           summary="获取优化规则",
           description="获取中文提示词优化规则和最佳实践")
async def get_optimization_rules():
    """获取优化规则"""
    try:
        rules = {
            "formality_rules": {
                "very_formal": {
                    "description": "非常正式，适用于官方文档和正式场合",
                    "characteristics": ["使用敬语", "书面语表达", "完整句式", "规范术语"],
                    "examples": ["您好，请问您需要什么帮助？", "根据您的需求，我建议采用以下方案"]
                },
                "formal": {
                    "description": "正式，适用于商务交流和学术讨论",
                    "characteristics": ["礼貌用语", "标准表达", "逻辑清晰", "专业术语"],
                    "examples": ["您好，关于这个问题", "建议您考虑以下几个方面"]
                },
                "semi_formal": {
                    "description": "半正式，适用于工作沟通和技术交流",
                    "characteristics": ["友好语调", "简洁明了", "实用导向", "适度礼貌"],
                    "examples": ["你好，这个问题可以这样解决", "我们来看看具体的实现方法"]
                }
            },
            "cultural_adaptations": {
                "greeting": ["您好", "你好", "欢迎使用"],
                "politeness": ["请", "麻烦", "不好意思"],
                "gratitude": ["谢谢", "感谢", "多谢"],
                "conclusion": ["希望对您有帮助", "如有疑问请随时联系", "祝您工作顺利"]
            },
            "ai_optimization_tips": [
                "使用明确的指令词，如'请'、'帮我'、'生成'",
                "提供具体的输出要求和格式说明",
                "包含示例和参考标准",
                "使用结构化的提示词格式",
                "避免模糊和歧义的表达"
            ],
            "best_practices": [
                "根据目标受众调整语言风格",
                "在技术内容中保持术语的一致性",
                "适当使用礼貌用语增强用户体验",
                "提供清晰的上下文和背景信息",
                "使用分步骤的说明提高可操作性"
            ]
        }
        
        return {"rules": rules}
        
    except Exception as e:
        logger.error(f"Error getting optimization rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取优化规则失败: {str(e)}"
        )