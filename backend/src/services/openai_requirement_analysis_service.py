"""
OpenAI需求分析服务

基于OpenAI GPT模型提供智能需求分析功能，包括：
1. 需求质量分析 - 分析需求的完整性、一致性、可测试性等
2. 需求复杂度评估 - 评估需求的技术复杂度和实现难度
3. 需求优化建议 - 提供需求改进建议和最佳实践
4. 需求冲突检测 - 检测需求间的冲突和依赖关系
5. 工作量估算 - 基于需求内容估算开发工作量

技术特性：
- 异步编程模式，支持高并发
- 完善的错误处理和降级方案
- 智能提示词模板管理
- 结果缓存和性能优化
- 详细的操作日志记录
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..adapters.openai_adapter import OpenAIAdapter
from ..adapters.base import (
    AIRequest, ChatMessage, MessageRole, ResponseFormat, 
    AdapterConfig, AIProvider
)
from ..services.ai_operation_log_service import get_ai_operation_log_service
from ..models.ai_operation_log import AIOperationType, AIOperationResult
from ..services.requirement_quality_prompt_templates import (
    RequirementQualityPromptTemplates, PromptTemplate, PromptContext, get_prompt_template, get_system_prompt
)

logger = logging.getLogger(__name__)
settings = get_settings()


class RequirementQualityDimension(Enum):
    """需求质量维度"""
    COMPLETENESS = "completeness"  # 完整性
    CONSISTENCY = "consistency"    # 一致性
    CLARITY = "clarity"           # 清晰性
    TESTABILITY = "testability"   # 可测试性
    FEASIBILITY = "feasibility"   # 可行性
    TRACEABILITY = "traceability" # 可追溯性


class RequirementComplexity(Enum):
    """需求复杂度等级"""
    SIMPLE = "simple"           # 简单 (1-3人天)
    MEDIUM = "medium"           # 中等 (3-8人天)
    COMPLEX = "complex"         # 复杂 (8-20人天)
    VERY_COMPLEX = "very_complex"  # 极复杂 (20+人天)


class RequirementType(Enum):
    """需求类型"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    INTERFACE = "interface"


@dataclass
class QualityScore:
    """质量评分"""
    dimension: RequirementQualityDimension
    score: float  # 0-10分
    description: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class RequirementQualityAnalysis:
    """需求质量分析结果"""
    requirement_id: Optional[int] = None
    overall_score: float = 0.0  # 总体质量评分 (0-10)
    quality_scores: List[QualityScore] = field(default_factory=list)
    
    # 详细分析
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    clarity_score: float = 0.0
    testability_score: float = 0.0
    feasibility_score: float = 0.0
    traceability_score: float = 0.0
    
    # 复杂度评估
    complexity_estimate: RequirementComplexity = RequirementComplexity.MEDIUM
    effort_estimate: float = 0.0  # 预估工作量(人天)
    
    # 改进建议
    improvement_suggestions: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # 元数据
    analysis_time: float = 0.0
    model_used: str = ""
    confidence_level: float = 0.0
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RequirementConflictAnalysis:
    """需求冲突分析结果"""
    has_conflicts: bool = False
    conflict_types: List[str] = field(default_factory=list)
    conflicting_requirements: List[Dict[str, Any]] = field(default_factory=list)
    resolution_suggestions: List[str] = field(default_factory=list)
    severity_level: str = "low"  # low, medium, high, critical


@dataclass
class RequirementOptimizationSuggestion:
    """需求优化建议"""
    category: str  # structure, content, clarity, testability
    priority: str  # high, medium, low
    title: str
    description: str
    example: Optional[str] = None
    expected_benefit: str = ""


class OpenAIRequirementAnalysisService:
    """
    OpenAI需求分析服务
    
    提供基于OpenAI GPT模型的智能需求分析功能，包括质量评估、
    复杂度分析、优化建议等。
    """
    
    def __init__(self, db: AsyncSession = None):
        """
        初始化OpenAI需求分析服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 操作日志服务
        self.log_service = None
        
        # OpenAI配置
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.api_endpoint = getattr(settings, 'OPENAI_API_ENDPOINT', 'https://api.openai.com/v1')
        self.default_model = getattr(settings, 'OPENAI_DEFAULT_MODEL', 'gpt-4')
        self.timeout = getattr(settings, 'OPENAI_TIMEOUT', 30.0)
        self.max_retries = getattr(settings, 'OPENAI_MAX_RETRIES', 3)
        
        # OpenAI适配器
        self.openai_adapter: Optional[OpenAIAdapter] = None
        
        # 服务状态
        self.is_initialized = False
        self.service_version = "1.0.0"
        
        # 性能指标
        self.metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "avg_analysis_time": 0.0,
            "total_tokens_used": 0
        }
    
    async def initialize(self):
        """初始化服务"""
        try:
            self.logger.info("Initializing OpenAI Requirement Analysis Service...")
            
            # 验证API密钥
            if not self.api_key:
                self.logger.warning("OpenAI API key not configured")
                return
            
            # 创建OpenAI适配器
            adapter_config = AdapterConfig(
                provider=AIProvider.OPENAI,
                api_key=self.api_key,
                api_endpoint=self.api_endpoint,
                default_model=self.default_model,
                timeout=self.timeout,
                max_retries=self.max_retries
            )
            
            self.openai_adapter = OpenAIAdapter(adapter_config)
            
            # 初始化操作日志服务
            if self.db:
                try:
                    self.log_service = await get_ai_operation_log_service(self.db)
                    self.logger.info("AI操作日志服务已初始化")
                except Exception as e:
                    self.logger.warning(f"AI操作日志服务初始化失败: {e}")
            
            # 健康检查
            is_healthy = await self.openai_adapter.health_check()
            if not is_healthy:
                self.logger.warning("OpenAI adapter health check failed")
                return
            
            self.is_initialized = True
            self.logger.info("OpenAI Requirement Analysis Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI Requirement Analysis Service: {str(e)}")
            raise
    
    async def analyze_requirement_quality(
        self, 
        title: str, 
        description: str, 
        acceptance_criteria: Optional[str] = None,
        requirement_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> RequirementQualityAnalysis:
        """
        分析需求质量
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            requirement_type: 需求类型
            user_id: 用户ID
            
        Returns:
            RequirementQualityAnalysis: 质量分析结果
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not self.openai_adapter:
                raise ValueError("OpenAI adapter not available")
            
            self.logger.info(f"Analyzing requirement quality for title: {title[:50]}...")
            
            # 构建分析提示词上下文
            context = PromptContext(
                requirement_title=title,
                requirement_description=description,
                acceptance_criteria=acceptance_criteria,
                requirement_type=requirement_type
            )
            
            # 获取提示词
            system_prompt = get_system_prompt()
            user_prompt = get_prompt_template(PromptTemplate.QUALITY_ANALYSIS, context)
            
            # 创建AI请求
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            
            request = AIRequest(
                messages=messages,
                model=self.default_model,
                temperature=0.3,  # 较低温度确保一致性
                max_tokens=2000,
                user_id=user_id
            )
            
            # 调用OpenAI API
            response = await self.openai_adapter.chat_completion(request)
            
            analysis_time = time.time() - start_time
            
            if response.error_code:
                self.logger.error(f"OpenAI API error: {response.error_message}")
                return self._create_fallback_analysis(analysis_time)
            
            # 解析分析结果
            analysis_result = self._parse_quality_analysis_response(
                response.content, analysis_time, response.model
            )
            
            # 更新指标
            self.metrics["total_analyses"] += 1
            self.metrics["successful_analyses"] += 1
            self.metrics["total_tokens_used"] += response.usage.total_tokens if response.usage else 0
            self._update_avg_analysis_time(analysis_time)
            
            # 记录操作日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=response.model,
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                    processing_time=analysis_time,
                    result=AIOperationResult.SUCCESS,
                    business_context={
                        "operation_type": "requirement_quality_analysis",
                        "requirement_title": title[:100],
                        "overall_score": analysis_result.overall_score
                    }
                )
            
            self.logger.info(f"Quality analysis completed in {analysis_time:.2f}s, "
                           f"overall score: {analysis_result.overall_score:.1f}")
            
            return analysis_result
            
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error analyzing requirement quality: {str(e)}")
            
            # 更新失败指标
            self.metrics["total_analyses"] += 1
            self.metrics["failed_analyses"] += 1
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=self.default_model,
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "requirement_quality_analysis",
                        "requirement_title": title[:100] if title else "unknown"
                    }
                )
            
            return self._create_fallback_analysis(analysis_time)
    
    async def detect_requirement_conflicts(
        self,
        current_requirement: Dict[str, Any],
        existing_requirements: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> RequirementConflictAnalysis:
        """
        检测需求冲突
        
        Args:
            current_requirement: 当前需求
            existing_requirements: 已存在的需求列表
            user_id: 用户ID
            
        Returns:
            RequirementConflictAnalysis: 冲突分析结果
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not self.openai_adapter:
                raise ValueError("OpenAI adapter not available")
            
            self.logger.info("Detecting requirement conflicts...")
            
            # 构建冲突检测提示词上下文
            context = PromptContext(
                requirement_title=current_requirement.get('title', ''),
                requirement_description=current_requirement.get('description', ''),
                requirement_type=current_requirement.get('type', ''),
                existing_requirements=existing_requirements
            )
            
            # 获取提示词
            system_prompt = self._get_conflict_detection_system_prompt()
            user_prompt = self._build_conflict_detection_prompt(current_requirement, existing_requirements)
            
            # 创建AI请求
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            
            request = AIRequest(
                messages=messages,
                model=self.default_model,
                temperature=0.2,  # 更低温度确保准确性
                max_tokens=1500,
                user_id=user_id
            )
            
            # 调用OpenAI API
            response = await self.openai_adapter.chat_completion(request)
            
            analysis_time = time.time() - start_time
            
            if response.error_code:
                self.logger.error(f"OpenAI API error: {response.error_message}")
                return RequirementConflictAnalysis()
            
            # 解析冲突分析结果
            conflict_analysis = self._parse_conflict_analysis_response(response.content)
            
            # 记录操作日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=response.model,
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                    processing_time=analysis_time,
                    result=AIOperationResult.SUCCESS,
                    business_context={
                        "operation_type": "requirement_conflict_detection",
                        "has_conflicts": conflict_analysis.has_conflicts,
                        "conflict_count": len(conflict_analysis.conflicting_requirements)
                    }
                )
            
            self.logger.info(f"Conflict detection completed in {analysis_time:.2f}s, "
                           f"conflicts found: {conflict_analysis.has_conflicts}")
            
            return conflict_analysis
            
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error detecting requirement conflicts: {str(e)}")
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=self.default_model,
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "requirement_conflict_detection"
                    }
                )
            
            return RequirementConflictAnalysis()
    
    async def generate_optimization_suggestions(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str] = None,
        quality_analysis: Optional[RequirementQualityAnalysis] = None,
        user_id: Optional[int] = None
    ) -> List[RequirementOptimizationSuggestion]:
        """
        生成需求优化建议
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            quality_analysis: 质量分析结果
            user_id: 用户ID
            
        Returns:
            List[RequirementOptimizationSuggestion]: 优化建议列表
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not self.openai_adapter:
                raise ValueError("OpenAI adapter not available")
            
            self.logger.info("Generating requirement optimization suggestions...")
            
            # 构建优化建议提示词
            prompt = self._build_optimization_prompt(
                title, description, acceptance_criteria, quality_analysis
            )
            
            # 创建AI请求
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=self._get_optimization_system_prompt()),
                ChatMessage(role=MessageRole.USER, content=prompt)
            ]
            
            request = AIRequest(
                messages=messages,
                model=self.default_model,
                temperature=0.4,  # 适中温度平衡创造性和准确性
                max_tokens=2000,
                user_id=user_id
            )
            
            # 调用OpenAI API
            response = await self.openai_adapter.chat_completion(request)
            
            analysis_time = time.time() - start_time
            
            if response.error_code:
                self.logger.error(f"OpenAI API error: {response.error_message}")
                return []
            
            # 解析优化建议
            suggestions = self._parse_optimization_suggestions(response.content)
            
            # 记录操作日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=response.model,
                    tokens_used=response.usage.total_tokens if response.usage else 0,
                    processing_time=analysis_time,
                    result=AIOperationResult.SUCCESS,
                    business_context={
                        "operation_type": "requirement_optimization_suggestions",
                        "suggestions_count": len(suggestions)
                    }
                )
            
            self.logger.info(f"Generated {len(suggestions)} optimization suggestions in {analysis_time:.2f}s")
            
            return suggestions
            
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error generating optimization suggestions: {str(e)}")
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=self.default_model,
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "requirement_optimization_suggestions"
                    }
                )
            
            return []
    
    async def analyze_requirement_completeness(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str] = None,
        requirement_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析需求完整性
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            requirement_type: 需求类型
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 完整性分析结果
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not self.openai_adapter:
                raise ValueError("OpenAI adapter not available")
            
            self.logger.info("Analyzing requirement completeness...")
            
            # 构建完整性分析提示词上下文
            context = PromptContext(
                requirement_title=title,
                requirement_description=description,
                acceptance_criteria=acceptance_criteria,
                requirement_type=requirement_type
            )
            
            # 获取提示词
            system_prompt = get_system_prompt()
            user_prompt = get_prompt_template(PromptTemplate.COMPLETENESS_CHECK, context)
            
            # 创建AI请求
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            
            request = AIRequest(
                messages=messages,
                model=self.default_model,
                temperature=0.2,
                max_tokens=1500,
                user_id=user_id
            )
            
            # 调用OpenAI API
            response = await self.openai_adapter.chat_completion(request)
            
            analysis_time = time.time() - start_time
            
            if response.error_code:
                self.logger.error(f"OpenAI API error: {response.error_message}")
                return {"error": response.error_message}
            
            # 解析完整性分析结果
            try:
                if response.content.strip().startswith('{'):
                    result = json.loads(response.content)
                else:
                    import re
                    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise ValueError("No JSON found in response")
                
                # 记录操作日志
                if self.log_service:
                    await self.log_service.log_ai_model_call(
                        user_id=user_id,
                        ai_provider="openai",
                        ai_model=response.model,
                        tokens_used=response.usage.total_tokens if response.usage else 0,
                        processing_time=analysis_time,
                        result=AIOperationResult.SUCCESS,
                        business_context={
                            "operation_type": "requirement_completeness_analysis",
                            "completeness_score": result.get("completeness_score", 0)
                        }
                    )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error parsing completeness analysis response: {str(e)}")
                return {"error": "Failed to parse analysis result"}
                
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error analyzing requirement completeness: {str(e)}")
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=self.default_model,
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "requirement_completeness_analysis"
                    }
                )
            
            return {"error": str(e)}
    
    async def analyze_requirement_consistency(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str] = None,
        existing_requirements: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析需求一致性
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            existing_requirements: 已存在的需求列表
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 一致性分析结果
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            if not self.openai_adapter:
                raise ValueError("OpenAI adapter not available")
            
            self.logger.info("Analyzing requirement consistency...")
            
            # 构建一致性分析提示词上下文
            context = PromptContext(
                requirement_title=title,
                requirement_description=description,
                acceptance_criteria=acceptance_criteria,
                existing_requirements=existing_requirements or []
            )
            
            # 获取提示词
            system_prompt = get_system_prompt()
            user_prompt = get_prompt_template(PromptTemplate.CONSISTENCY_ANALYSIS, context)
            
            # 创建AI请求
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt)
            ]
            
            request = AIRequest(
                messages=messages,
                model=self.default_model,
                temperature=0.2,
                max_tokens=1500,
                user_id=user_id
            )
            
            # 调用OpenAI API
            response = await self.openai_adapter.chat_completion(request)
            
            analysis_time = time.time() - start_time
            
            if response.error_code:
                self.logger.error(f"OpenAI API error: {response.error_message}")
                return {"error": response.error_message}
            
            # 解析一致性分析结果
            try:
                if response.content.strip().startswith('{'):
                    result = json.loads(response.content)
                else:
                    import re
                    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        raise ValueError("No JSON found in response")
                
                # 记录操作日志
                if self.log_service:
                    await self.log_service.log_ai_model_call(
                        user_id=user_id,
                        ai_provider="openai",
                        ai_model=response.model,
                        tokens_used=response.usage.total_tokens if response.usage else 0,
                        processing_time=analysis_time,
                        result=AIOperationResult.SUCCESS,
                        business_context={
                            "operation_type": "requirement_consistency_analysis",
                            "consistency_score": result.get("consistency_score", 0)
                        }
                    )
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error parsing consistency analysis response: {str(e)}")
                return {"error": "Failed to parse analysis result"}
                
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error analyzing requirement consistency: {str(e)}")
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model=self.default_model,
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "requirement_consistency_analysis"
                    }
                )
            
            return {"error": str(e)}
    
    def _get_quality_analysis_system_prompt(self) -> str:
        """获取质量分析系统提示词"""
        return """你是一个专业的需求分析专家，负责评估软件需求的质量。请从以下维度分析需求质量：

1. 完整性 (Completeness): 需求是否包含所有必要信息
2. 一致性 (Consistency): 需求内部是否一致，与其他需求是否冲突
3. 清晰性 (Clarity): 需求表述是否清晰明确，无歧义
4. 可测试性 (Testability): 需求是否可以被验证和测试
5. 可行性 (Feasibility): 需求在技术和资源约束下是否可实现
6. 可追溯性 (Traceability): 需求是否可以追溯到业务目标

请以JSON格式返回分析结果，包含：
- overall_score: 总体评分 (0-10)
- quality_scores: 各维度评分和建议
- complexity_estimate: 复杂度评估 (simple/medium/complex/very_complex)
- effort_estimate: 工作量估算 (人天)
- improvement_suggestions: 改进建议列表
- risk_factors: 风险因素列表
- confidence_level: 分析置信度 (0-1)

请确保分析客观、准确，并提供具体可行的改进建议。"""
    
    def _get_conflict_detection_system_prompt(self) -> str:
        """获取冲突检测系统提示词"""
        return """你是一个需求冲突检测专家，负责识别需求间的潜在冲突。请分析以下类型的冲突：

1. 功能冲突: 需求要求相互矛盾的功能
2. 数据冲突: 对同一数据有不同的定义或约束
3. 接口冲突: 接口定义不一致或不兼容
4. 性能冲突: 性能要求相互矛盾
5. 安全冲突: 安全要求与功能要求冲突
6. 用户体验冲突: 用户体验设计相互矛盾

请以JSON格式返回分析结果，包含：
- has_conflicts: 是否存在冲突
- conflict_types: 冲突类型列表
- conflicting_requirements: 冲突的需求详情
- resolution_suggestions: 解决建议
- severity_level: 严重程度 (low/medium/high/critical)

请仔细分析需求间的关系，识别显性和隐性冲突。"""
    
    def _get_optimization_system_prompt(self) -> str:
        """获取优化建议系统提示词"""
        return """你是一个需求优化专家，负责提供需求改进建议。请从以下方面提供优化建议：

1. 结构优化: 改进需求的组织结构和层次
2. 内容优化: 完善需求内容，补充缺失信息
3. 表达优化: 改进需求的表述方式，提高清晰度
4. 测试优化: 改进验收标准，提高可测试性
5. 实现优化: 提供实现方案建议，降低复杂度

请以JSON格式返回优化建议列表，每个建议包含：
- category: 建议类别 (structure/content/clarity/testability/implementation)
- priority: 优先级 (high/medium/low)
- title: 建议标题
- description: 详细描述
- example: 示例 (可选)
- expected_benefit: 预期收益

请确保建议具体可行，有助于提高需求质量。"""
    
    def _build_quality_analysis_prompt(
        self, 
        title: str, 
        description: str, 
        acceptance_criteria: Optional[str] = None,
        requirement_type: Optional[str] = None
    ) -> str:
        """构建质量分析提示词"""
        prompt = f"""请分析以下需求的质量：

需求标题: {title}

需求描述:
{description}
"""
        
        if acceptance_criteria:
            prompt += f"""
验收标准:
{acceptance_criteria}
"""
        
        if requirement_type:
            prompt += f"""
需求类型: {requirement_type}
"""
        
        prompt += """
请从完整性、一致性、清晰性、可测试性、可行性、可追溯性六个维度进行详细分析，并提供改进建议。"""
        
        return prompt
    
    def _build_conflict_detection_prompt(
        self,
        current_requirement: Dict[str, Any],
        existing_requirements: List[Dict[str, Any]]
    ) -> str:
        """构建冲突检测提示词"""
        prompt = f"""请检测以下新需求与已有需求是否存在冲突：

新需求:
标题: {current_requirement.get('title', '')}
描述: {current_requirement.get('description', '')}
类型: {current_requirement.get('type', '')}

已有需求:
"""
        
        for i, req in enumerate(existing_requirements[:10]):  # 限制数量避免token过多
            prompt += f"""
{i+1}. 标题: {req.get('title', '')}
   描述: {req.get('description', '')[:200]}...
   类型: {req.get('type', '')}
"""
        
        prompt += """
请分析是否存在功能冲突、数据冲突、接口冲突、性能冲突、安全冲突或用户体验冲突。"""
        
        return prompt
    
    def _build_optimization_prompt(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str] = None,
        quality_analysis: Optional[RequirementQualityAnalysis] = None
    ) -> str:
        """构建优化建议提示词"""
        prompt = f"""请为以下需求提供优化建议：

需求标题: {title}

需求描述:
{description}
"""
        
        if acceptance_criteria:
            prompt += f"""
验收标准:
{acceptance_criteria}
"""
        
        if quality_analysis:
            prompt += f"""
当前质量评分: {quality_analysis.overall_score:.1f}/10
主要问题:
"""
            for suggestion in quality_analysis.improvement_suggestions[:5]:
                prompt += f"- {suggestion}\n"
        
        prompt += """
请提供具体的优化建议，帮助提高需求质量和可实现性。"""
        
        return prompt
    
    def _parse_quality_analysis_response(
        self, 
        response_content: str, 
        analysis_time: float, 
        model_used: str
    ) -> RequirementQualityAnalysis:
        """解析质量分析响应"""
        try:
            # 尝试解析JSON响应
            if response_content.strip().startswith('{'):
                data = json.loads(response_content)
            else:
                # 如果不是JSON格式，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            
            # 构建质量评分列表
            quality_scores = []
            if 'quality_scores' in data:
                for score_data in data['quality_scores']:
                    quality_scores.append(QualityScore(
                        dimension=RequirementQualityDimension(score_data['dimension']),
                        score=float(score_data['score']),
                        description=score_data.get('description', ''),
                        suggestions=score_data.get('suggestions', [])
                    ))
            
            # 解析复杂度
            complexity_str = data.get('complexity_estimate', 'medium')
            try:
                complexity = RequirementComplexity(complexity_str)
            except ValueError:
                complexity = RequirementComplexity.MEDIUM
            
            return RequirementQualityAnalysis(
                overall_score=float(data.get('overall_score', 5.0)),
                quality_scores=quality_scores,
                completeness_score=float(data.get('completeness_score', 5.0)),
                consistency_score=float(data.get('consistency_score', 5.0)),
                clarity_score=float(data.get('clarity_score', 5.0)),
                testability_score=float(data.get('testability_score', 5.0)),
                feasibility_score=float(data.get('feasibility_score', 5.0)),
                traceability_score=float(data.get('traceability_score', 5.0)),
                complexity_estimate=complexity,
                effort_estimate=float(data.get('effort_estimate', 5.0)),
                improvement_suggestions=data.get('improvement_suggestions', []),
                risk_factors=data.get('risk_factors', []),
                analysis_time=analysis_time,
                model_used=model_used,
                confidence_level=float(data.get('confidence_level', 0.8))
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing quality analysis response: {str(e)}")
            return self._create_fallback_analysis(analysis_time, model_used)
    
    def _parse_conflict_analysis_response(self, response_content: str) -> RequirementConflictAnalysis:
        """解析冲突分析响应"""
        try:
            # 尝试解析JSON响应
            if response_content.strip().startswith('{'):
                data = json.loads(response_content)
            else:
                # 如果不是JSON格式，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            
            return RequirementConflictAnalysis(
                has_conflicts=bool(data.get('has_conflicts', False)),
                conflict_types=data.get('conflict_types', []),
                conflicting_requirements=data.get('conflicting_requirements', []),
                resolution_suggestions=data.get('resolution_suggestions', []),
                severity_level=data.get('severity_level', 'low')
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing conflict analysis response: {str(e)}")
            return RequirementConflictAnalysis()
    
    def _parse_optimization_suggestions(self, response_content: str) -> List[RequirementOptimizationSuggestion]:
        """解析优化建议响应"""
        try:
            # 尝试解析JSON响应
            if response_content.strip().startswith('['):
                data = json.loads(response_content)
            elif response_content.strip().startswith('{'):
                # 如果是对象格式，尝试提取suggestions字段
                obj_data = json.loads(response_content)
                data = obj_data.get('suggestions', [])
            else:
                # 如果不是JSON格式，尝试提取JSON部分
                import re
                json_match = re.search(r'\[.*\]', response_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON array found in response")
            
            suggestions = []
            for item in data:
                suggestions.append(RequirementOptimizationSuggestion(
                    category=item.get('category', 'general'),
                    priority=item.get('priority', 'medium'),
                    title=item.get('title', ''),
                    description=item.get('description', ''),
                    example=item.get('example'),
                    expected_benefit=item.get('expected_benefit', '')
                ))
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error parsing optimization suggestions response: {str(e)}")
            return []
    
    def _create_fallback_analysis(self, analysis_time: float, model_used: str = "") -> RequirementQualityAnalysis:
        """创建降级分析结果"""
        return RequirementQualityAnalysis(
            overall_score=5.0,
            completeness_score=5.0,
            consistency_score=5.0,
            clarity_score=5.0,
            testability_score=5.0,
            feasibility_score=5.0,
            traceability_score=5.0,
            complexity_estimate=RequirementComplexity.MEDIUM,
            effort_estimate=5.0,
            improvement_suggestions=["AI分析服务暂时不可用，请手动评估需求质量"],
            risk_factors=["无法进行AI分析"],
            analysis_time=analysis_time,
            model_used=model_used,
            confidence_level=0.0
        )
    
    def _update_avg_analysis_time(self, analysis_time: float):
        """更新平均分析时间"""
        if self.metrics["successful_analyses"] == 1:
            self.metrics["avg_analysis_time"] = analysis_time
        else:
            # 计算移动平均
            total_time = self.metrics["avg_analysis_time"] * (self.metrics["successful_analyses"] - 1)
            self.metrics["avg_analysis_time"] = (total_time + analysis_time) / self.metrics["successful_analyses"]
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return {
            **self.metrics,
            "is_initialized": self.is_initialized,
            "service_version": self.service_version,
            "openai_available": self.openai_adapter is not None and self.openai_adapter.is_healthy
        }
    
    async def shutdown(self):
        """关闭服务"""
        if self.openai_adapter:
            await self.openai_adapter.shutdown()
        self.logger.info("OpenAI Requirement Analysis Service shutdown completed")


# 全局服务实例
_openai_requirement_analysis_service: Optional[OpenAIRequirementAnalysisService] = None


async def get_openai_requirement_analysis_service(db: AsyncSession = None) -> OpenAIRequirementAnalysisService:
    """
    获取OpenAI需求分析服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        OpenAIRequirementAnalysisService: 服务实例
    """
    global _openai_requirement_analysis_service
    
    if _openai_requirement_analysis_service is None:
        _openai_requirement_analysis_service = OpenAIRequirementAnalysisService(db)
        await _openai_requirement_analysis_service.initialize()
    
    return _openai_requirement_analysis_service