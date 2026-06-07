"""
中文提示词优化服务

本模块专门针对中文AI交互场景，提供提示词模板的优化功能，包括：
1. 中文语言特性优化
2. 文化背景适配
3. 专业术语处理
4. 语言风格调整
5. 上下文理解增强

主要功能：
- 中文提示词模板生成和优化
- 语言风格和正式程度调整
- 文化背景和礼貌用语适配
- 专业领域术语优化
- 中文语法和表达习惯优化
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .prompt_service import PromptService, TemplateRenderer
from .multilingual_response_service import MultilingualResponseService, SupportedLanguage
from ..schemas.prompt_template import (
    PromptTemplateCreate, TemplateVariable, TemplateCategory, TemplateVisibility
)

logger = logging.getLogger(__name__)


class ChineseFormalityLevel(str, Enum):
    """中文正式程度枚举"""
    VERY_FORMAL = "very_formal"      # 非常正式（书面语、官方文档）
    FORMAL = "formal"                # 正式（商务交流、学术讨论）
    SEMI_FORMAL = "semi_formal"      # 半正式（工作沟通、技术交流）
    CASUAL = "casual"                # 随意（日常对话、朋友交流）
    VERY_CASUAL = "very_casual"      # 非常随意（网络用语、口语化）


class ChineseContextType(str, Enum):
    """中文上下文类型枚举"""
    TECHNICAL = "technical"          # 技术类
    BUSINESS = "business"            # 商务类
    ACADEMIC = "academic"            # 学术类
    EDUCATIONAL = "educational"      # 教育类
    CREATIVE = "creative"            # 创意类
    DAILY = "daily"                  # 日常类


@dataclass
class ChineseOptimizationConfig:
    """中文优化配置"""
    formality_level: ChineseFormalityLevel = ChineseFormalityLevel.SEMI_FORMAL
    context_type: ChineseContextType = ChineseContextType.TECHNICAL
    use_honorifics: bool = True
    prefer_classical_expressions: bool = False
    include_cultural_context: bool = True
    optimize_for_ai_understanding: bool = True
    target_audience: str = "专业用户"
    domain_specific: Optional[str] = None


class ChinesePromptOptimizer:
    """中文提示词优化器"""
    
    def __init__(self, prompt_service: PromptService, 
                 multilingual_service: MultilingualResponseService):
        self.prompt_service = prompt_service
        self.multilingual_service = multilingual_service
        self.logger = logging.getLogger(__name__)
        
        # 中文优化规则
        self._load_optimization_rules()
    
    def _load_optimization_rules(self):
        """加载中文优化规则"""
        # 正式程度词汇映射
        self.formality_mappings = {
            ChineseFormalityLevel.VERY_FORMAL: {
                "你": "您",
                "怎么": "如何",
                "什么": "何种",
                "好的": "好的，明白了",
                "可以": "能够",
                "帮助": "协助"
            },
            ChineseFormalityLevel.FORMAL: {
                "你": "您",
                "怎么": "如何",
                "好的": "好的",
                "可以": "能够"
            },
            ChineseFormalityLevel.SEMI_FORMAL: {
                "你": "你",
                "怎么": "怎么",
                "好的": "好的"
            }
        }      
  
        # 专业术语词典
        self.technical_terms = {
            "测试": ["测试", "检测", "验证", "校验"],
            "需求": ["需求", "要求", "规格", "规范"],
            "分析": ["分析", "解析", "剖析", "研究"],
            "优化": ["优化", "改进", "完善", "提升"],
            "实现": ["实现", "完成", "达成", "执行"]
        }
        
        # 文化背景表达
        self.cultural_expressions = {
            "greeting": ["您好", "你好", "欢迎", "很高兴为您服务"],
            "politeness": ["请", "麻烦", "劳烦", "不好意思"],
            "gratitude": ["谢谢", "感谢", "多谢", "非常感谢"],
            "apology": ["抱歉", "对不起", "不好意思", "很遗憾"]
        }
        
        # AI理解优化关键词
        self.ai_optimization_keywords = [
            "请详细说明", "具体来说", "举例说明", "步骤如下",
            "需要注意的是", "重点是", "关键在于", "总结一下"
        ]
    
    async def optimize_chinese_prompt(self, 
                                    original_prompt: str,
                                    config: ChineseOptimizationConfig) -> str:
        """优化中文提示词"""
        try:
            self.logger.info("开始优化中文提示词")
            
            optimized_prompt = original_prompt
            
            # 1. 正式程度调整
            optimized_prompt = self._adjust_formality_level(optimized_prompt, config)
            
            # 2. 文化背景适配
            if config.include_cultural_context:
                optimized_prompt = self._add_cultural_context(optimized_prompt, config)
            
            # 3. 专业术语优化
            if config.domain_specific:
                optimized_prompt = self._optimize_domain_terms(optimized_prompt, config)
            
            # 4. AI理解优化
            if config.optimize_for_ai_understanding:
                optimized_prompt = self._optimize_for_ai(optimized_prompt, config)
            
            # 5. 语法和表达优化
            optimized_prompt = self._optimize_grammar_and_expression(optimized_prompt, config)
            
            self.logger.info("中文提示词优化完成")
            return optimized_prompt
            
        except Exception as e:
            self.logger.error(f"中文提示词优化失败: {e}")
            return original_prompt
    
    def _adjust_formality_level(self, prompt: str, config: ChineseOptimizationConfig) -> str:
        """调整正式程度"""
        if config.formality_level not in self.formality_mappings:
            return prompt
        
        mappings = self.formality_mappings[config.formality_level]
        optimized = prompt
        
        for informal, formal in mappings.items():
            optimized = optimized.replace(informal, formal)
        
        return optimized
    
    def _add_cultural_context(self, prompt: str, config: ChineseOptimizationConfig) -> str:
        """添加文化背景适配"""
        optimized = prompt
        
        # 添加礼貌用语
        if config.use_honorifics and not any(greeting in prompt for greeting in self.cultural_expressions["greeting"]):
            optimized = f"您好！{optimized}"
        
        # 添加礼貌结尾
        if config.formality_level in [ChineseFormalityLevel.FORMAL, ChineseFormalityLevel.VERY_FORMAL]:
            if not optimized.endswith(("。", "！", "？")):
                optimized += "。"
            optimized += "谢谢！"
        
        return optimized
    
    def _optimize_domain_terms(self, prompt: str, config: ChineseOptimizationConfig) -> str:
        """优化专业术语"""
        optimized = prompt
        
        # 根据领域调整术语
        if config.domain_specific == "testing":
            # 测试领域术语优化
            replacements = {
                "bug": "缺陷",
                "test case": "测试用例",
                "coverage": "覆盖率",
                "automation": "自动化"
            }
            for en_term, zh_term in replacements.items():
                optimized = optimized.replace(en_term, zh_term)
        
        return optimized
    
    def _optimize_for_ai(self, prompt: str, config: ChineseOptimizationConfig) -> str:
        """针对AI理解进行优化"""
        optimized = prompt
        
        # 添加结构化指示词
        if "请" not in optimized and "帮我" not in optimized:
            optimized = f"请{optimized}"
        
        # 添加明确的输出要求
        if not any(keyword in optimized for keyword in ["输出", "返回", "生成", "提供"]):
            optimized += "，请提供详细的回答。"
        
        # 添加格式要求
        if config.context_type == ChineseContextType.TECHNICAL:
            if "步骤" not in optimized and "方法" not in optimized:
                optimized += "请按步骤说明。"
        
        return optimized
    
    def _optimize_grammar_and_expression(self, prompt: str, config: ChineseOptimizationConfig) -> str:
        """优化语法和表达"""
        optimized = prompt
        
        # 修正常见语法问题
        grammar_fixes = {
            "的的": "的",
            "了了": "了",
            "。。": "。",
            "？？": "？",
            "！！": "！"
        }
        
        for wrong, correct in grammar_fixes.items():
            optimized = optimized.replace(wrong, correct)
        
        # 优化表达习惯
        expression_improvements = {
            "能不能": "是否能够",
            "可不可以": "是否可以",
            "行不行": "是否可行"
        }
        
        for casual, formal in expression_improvements.items():
            if config.formality_level in [ChineseFormalityLevel.FORMAL, ChineseFormalityLevel.VERY_FORMAL]:
                optimized = optimized.replace(casual, formal)
        
        return optimized
    
    async def create_optimized_chinese_templates(self, db, user_id: int) -> List[Dict[str, Any]]:
        """创建优化的中文提示词模板"""
        try:
            self.logger.info("开始创建优化的中文提示词模板")
            
            templates = []
            
            # 1. 测试用例生成模板
            test_case_template = await self._create_test_case_template(db, user_id)
            templates.append(test_case_template)
            
            # 2. 需求分析模板
            requirement_analysis_template = await self._create_requirement_analysis_template(db, user_id)
            templates.append(requirement_analysis_template)
            
            # 3. 代码审查模板
            code_review_template = await self._create_code_review_template(db, user_id)
            templates.append(code_review_template)
            
            # 4. 文档生成模板
            document_generation_template = await self._create_document_generation_template(db, user_id)
            templates.append(document_generation_template)
            
            # 5. 问题分析模板
            problem_analysis_template = await self._create_problem_analysis_template(db, user_id)
            templates.append(problem_analysis_template)
            
            self.logger.info(f"成功创建 {len(templates)} 个中文优化模板")
            return templates
            
        except Exception as e:
            self.logger.error(f"创建中文优化模板失败: {e}")
            return []
    
    async def _create_test_case_template(self, db, user_id: int) -> Dict[str, Any]:
        """创建测试用例生成模板"""
        template_data = PromptTemplateCreate(
            name="chinese_test_case_generation",
            title="中文测试用例生成模板",
            description="专门针对中文环境优化的测试用例生成提示词模板，包含完整的测试场景描述和验证步骤。",
            category=TemplateCategory.TEST_CASE,
            subcategory="功能测试",
            content="""您好！我需要为以下功能生成详细的测试用例：

**功能描述：** {feature_description}
**需求来源：** {requirement_source}
**测试类型：** {test_type}

请按照以下格式生成测试用例：

## 测试用例设计

### 1. 功能测试用例
- **测试目标：** 验证功能的基本实现
- **前置条件：** {preconditions}
- **测试步骤：**
  1. 详细的操作步骤
  2. 输入数据和参数
  3. 预期的系统响应
- **预期结果：** 明确的验证标准
- **优先级：** {priority}

### 2. 边界值测试用例
- **测试目标：** 验证边界条件处理
- **测试数据：** 最小值、最大值、临界值
- **验证要点：** 系统在边界条件下的表现

### 3. 异常场景测试用例
- **测试目标：** 验证异常处理机制
- **异常情况：** 错误输入、网络异常、系统故障
- **预期处理：** 错误提示、容错机制、恢复方案

请确保测试用例覆盖全面，描述清晰，便于执行和验证。谢谢！""",
            variables=[
                TemplateVariable(
                    name="feature_description",
                    type="string",
                    description="功能描述",
                    required=True,
                    example="用户登录功能"
                ),
                TemplateVariable(
                    name="requirement_source",
                    type="string",
                    description="需求来源",
                    required=False,
                    default_value="产品需求文档"
                ),
                TemplateVariable(
                    name="test_type",
                    type="string",
                    description="测试类型",
                    required=False,
                    default_value="功能测试"
                ),
                TemplateVariable(
                    name="preconditions",
                    type="string",
                    description="前置条件",
                    required=False,
                    default_value="系统正常运行，用户数据准备完毕"
                ),
                TemplateVariable(
                    name="priority",
                    type="string",
                    description="优先级",
                    required=False,
                    default_value="高"
                )
            ],
            supported_providers=["文心一言", "通义千问", "ChatGLM", "OpenAI", "Claude"],
            supported_models=["文心一言4.0", "通义千问-max", "ChatGLM-4", "GPT-4", "Claude-3"],
            use_cases=["功能测试", "回归测试", "验收测试", "系统测试"],
            tags=["中文优化", "测试用例", "功能测试", "质量保证"],
            visibility=TemplateVisibility.PUBLIC
        )
        
        template = await self.prompt_service.create_template(db, template_data, user_id)
        return {"template": template, "type": "test_case"}
    
    async def _create_requirement_analysis_template(self, db, user_id: int) -> Dict[str, Any]:
        """创建需求分析模板"""
        template_data = PromptTemplateCreate(
            name="chinese_requirement_analysis",
            title="中文需求分析模板",
            description="专门针对中文需求文档的分析模板，提供全面的需求质量评估和改进建议。",
            category=TemplateCategory.DATA_ANALYSIS,
            subcategory="需求分析",
            content="""您好！请帮我分析以下需求文档的质量：

**需求标题：** {requirement_title}
**需求描述：** {requirement_description}
**验收标准：** {acceptance_criteria}
**业务价值：** {business_value}

请从以下维度进行详细分析：

## 需求质量分析

### 1. 完整性分析（0-10分）
- **描述完整度：** 需求描述是否包含所有必要信息
- **验收标准：** 是否定义了明确的验收条件
- **业务价值：** 是否说明了需求的商业意义
- **依赖关系：** 是否识别了相关依赖

### 2. 清晰度分析（0-10分）
- **表述明确性：** 是否避免了模糊和歧义表达
- **术语一致性：** 专业术语使用是否规范统一
- **逻辑结构：** 需求组织是否条理清晰
- **理解难度：** 相关人员是否容易理解

### 3. 可测试性分析（0-10分）
- **验证标准：** 是否可以设计具体的测试用例
- **量化指标：** 是否包含可测量的性能指标
- **边界条件：** 是否明确了边界和异常情况
- **测试数据：** 是否便于准备测试数据

### 4. 可行性分析（0-10分）
- **技术可行性：** 当前技术条件下是否可以实现
- **资源需求：** 所需人力和时间是否合理
- **风险评估：** 是否识别了潜在风险
- **优先级合理性：** 优先级设置是否恰当

## 改进建议

请针对发现的问题提供具体的改进建议：
1. **高优先级问题：** 需要立即解决的关键问题
2. **中优先级问题：** 建议改进的一般问题  
3. **低优先级问题：** 可以优化的细节问题

## 总体评分和建议

请给出总体质量评分（0-10分）和核心改进建议。

谢谢您的详细分析！""",
            variables=[
                TemplateVariable(
                    name="requirement_title",
                    type="string",
                    description="需求标题",
                    required=True,
                    example="用户注册功能需求"
                ),
                TemplateVariable(
                    name="requirement_description",
                    type="string",
                    description="需求描述",
                    required=True,
                    example="系统应支持用户通过邮箱和手机号进行注册"
                ),
                TemplateVariable(
                    name="acceptance_criteria",
                    type="string",
                    description="验收标准",
                    required=False,
                    default_value="待补充"
                ),
                TemplateVariable(
                    name="business_value",
                    type="string",
                    description="业务价值",
                    required=False,
                    default_value="待补充"
                )
            ],
            supported_providers=["文心一言", "通义千问", "ChatGLM", "OpenAI", "Claude"],
            use_cases=["需求评审", "质量分析", "项目管理", "产品设计"],
            tags=["中文优化", "需求分析", "质量评估", "项目管理"],
            visibility=TemplateVisibility.PUBLIC
        )
        
        template = await self.prompt_service.create_template(db, template_data, user_id)
        return {"template": template, "type": "requirement_analysis"} 
   
    async def _create_code_review_template(self, db, user_id: int) -> Dict[str, Any]:
        """创建代码审查模板"""
        template_data = PromptTemplateCreate(
            name="chinese_code_review",
            title="中文代码审查模板",
            description="专门针对中文开发团队的代码审查模板，提供全面的代码质量分析和改进建议。",
            category=TemplateCategory.CODE_GENERATION,
            subcategory="代码审查",
            content="""您好！请帮我审查以下代码：

**代码语言：** {programming_language}
**代码模块：** {module_name}
**审查重点：** {review_focus}

```{programming_language}
{code_content}
```

请从以下方面进行详细的代码审查：

## 代码质量分析

### 1. 代码规范性（0-10分）
- **命名规范：** 变量、函数、类的命名是否符合规范
- **代码格式：** 缩进、空格、换行是否统一规范
- **注释质量：** 注释是否清晰、完整、有意义
- **代码结构：** 代码组织是否清晰合理

### 2. 功能正确性（0-10分）
- **逻辑正确性：** 代码逻辑是否正确实现预期功能
- **边界处理：** 是否正确处理边界条件和异常情况
- **数据验证：** 输入数据验证是否充分
- **错误处理：** 异常处理机制是否完善

### 3. 性能优化（0-10分）
- **算法效率：** 算法选择是否合理高效
- **资源使用：** 内存和CPU使用是否优化
- **数据库操作：** 查询是否高效，是否存在N+1问题
- **缓存策略：** 是否合理使用缓存机制

### 4. 安全性分析（0-10分）
- **输入安全：** 是否防范SQL注入、XSS等攻击
- **权限控制：** 访问权限验证是否充分
- **数据保护：** 敏感数据是否得到保护
- **安全配置：** 安全相关配置是否正确

### 5. 可维护性（0-10分）
- **代码复杂度：** 函数和类的复杂度是否合理
- **模块耦合：** 模块间耦合度是否适当
- **代码重用：** 是否避免了重复代码
- **扩展性：** 代码是否便于后续扩展

## 具体问题和建议

### 🔴 严重问题（必须修复）
- 列出影响功能或安全的严重问题
- 提供具体的修复建议和代码示例

### 🟡 一般问题（建议修复）
- 列出影响代码质量的一般问题
- 提供改进建议和最佳实践

### 🟢 优化建议（可选改进）
- 列出可以进一步优化的地方
- 提供性能或可读性改进建议

## 总体评价

**总体评分：** _/10分
**主要优点：** 
**核心问题：** 
**改进重点：** 

谢谢您的详细审查！""",
            variables=[
                TemplateVariable(
                    name="programming_language",
                    type="string",
                    description="编程语言",
                    required=True,
                    example="Python"
                ),
                TemplateVariable(
                    name="module_name",
                    type="string",
                    description="代码模块名称",
                    required=False,
                    default_value="待审查模块"
                ),
                TemplateVariable(
                    name="review_focus",
                    type="string",
                    description="审查重点",
                    required=False,
                    default_value="全面审查"
                ),
                TemplateVariable(
                    name="code_content",
                    type="string",
                    description="代码内容",
                    required=True,
                    example="def example_function():\n    pass"
                )
            ],
            supported_providers=["文心一言", "通义千问", "ChatGLM", "OpenAI", "Claude"],
            use_cases=["代码审查", "质量控制", "团队协作", "技术指导"],
            tags=["中文优化", "代码审查", "质量控制", "开发规范"],
            visibility=TemplateVisibility.PUBLIC
        )
        
        template = await self.prompt_service.create_template(db, template_data, user_id)
        return {"template": template, "type": "code_review"}
    
    async def _create_document_generation_template(self, db, user_id: int) -> Dict[str, Any]:
        """创建文档生成模板"""
        template_data = PromptTemplateCreate(
            name="chinese_document_generation",
            title="中文技术文档生成模板",
            description="专门针对中文技术文档的生成模板，支持多种文档类型的标准化生成。",
            category=TemplateCategory.DOCUMENT_WRITING,
            subcategory="技术文档",
            content="""您好！请帮我生成以下技术文档：

**文档类型：** {document_type}
**项目名称：** {project_name}
**目标读者：** {target_audience}
**详细程度：** {detail_level}

## 文档生成要求

请按照以下结构生成专业的中文技术文档：

### 1. 文档概述
- **文档目的：** 说明文档的作用和价值
- **适用范围：** 明确文档的适用场景
- **读者对象：** 定义目标读者群体
- **文档版本：** 版本信息和更新记录

### 2. 主要内容
根据文档类型生成相应的核心内容：

**如果是API文档：**
- 接口概述和架构说明
- 详细的接口规范和参数说明
- 请求和响应示例
- 错误码和异常处理
- 使用指南和最佳实践

**如果是用户手册：**
- 功能概述和使用流程
- 详细的操作步骤和截图说明
- 常见问题和解决方案
- 注意事项和限制条件
- 联系方式和技术支持

**如果是设计文档：**
- 需求背景和目标
- 系统架构和技术选型
- 详细设计和实现方案
- 风险评估和应对策略
- 测试计划和验收标准

### 3. 附加信息
- **相关资源：** 参考文档和外部链接
- **更新历史：** 版本变更记录
- **联系信息：** 负责人和维护团队
- **反馈渠道：** 问题反馈和建议收集

## 文档要求

请确保生成的文档：
1. **结构清晰：** 层次分明，逻辑合理
2. **内容完整：** 信息全面，细节充分
3. **表达准确：** 术语规范，描述精确
4. **易于理解：** 语言简洁，便于阅读
5. **实用性强：** 贴近实际，便于操作

谢谢您的协助！""",
            variables=[
                TemplateVariable(
                    name="document_type",
                    type="string",
                    description="文档类型",
                    required=True,
                    example="API接口文档"
                ),
                TemplateVariable(
                    name="project_name",
                    type="string",
                    description="项目名称",
                    required=True,
                    example="AI测试管理系统"
                ),
                TemplateVariable(
                    name="target_audience",
                    type="string",
                    description="目标读者",
                    required=False,
                    default_value="开发人员和测试人员"
                ),
                TemplateVariable(
                    name="detail_level",
                    type="string",
                    description="详细程度",
                    required=False,
                    default_value="详细"
                )
            ],
            supported_providers=["文心一言", "通义千问", "ChatGLM", "OpenAI", "Claude"],
            use_cases=["技术文档", "用户手册", "API文档", "设计文档"],
            tags=["中文优化", "文档生成", "技术写作", "项目管理"],
            visibility=TemplateVisibility.PUBLIC
        )
        
        template = await self.prompt_service.create_template(db, template_data, user_id)
        return {"template": template, "type": "document_generation"}
    
    async def _create_problem_analysis_template(self, db, user_id: int) -> Dict[str, Any]:
        """创建问题分析模板"""
        template_data = PromptTemplateCreate(
            name="chinese_problem_analysis",
            title="中文问题分析模板",
            description="专门针对中文环境的问题分析模板，提供系统化的问题诊断和解决方案。",
            category=TemplateCategory.DATA_ANALYSIS,
            subcategory="问题分析",
            content="""您好！请帮我分析以下问题：

**问题描述：** {problem_description}
**发生环境：** {environment}
**影响范围：** {impact_scope}
**紧急程度：** {urgency_level}

请按照以下框架进行系统性的问题分析：

## 问题分析框架

### 1. 问题理解和定义
- **问题本质：** 准确识别问题的核心所在
- **现象描述：** 详细记录问题的具体表现
- **影响评估：** 分析问题对系统和用户的影响
- **时间线分析：** 梳理问题发生的时间脉络

### 2. 根因分析（5Why分析法）
请运用5Why方法深入挖掘问题根因：

**第1个Why：** 为什么会出现这个问题？
- 直接原因分析
- 相关因素识别

**第2个Why：** 为什么会有这个直接原因？
- 深层原因探索
- 系统性因素分析

**第3个Why：** 为什么会存在这些深层原因？
- 流程和机制分析
- 管理和控制问题

**第4个Why：** 为什么流程和机制存在缺陷？
- 设计和规划问题
- 资源和能力分析

**第5个Why：** 为什么在设计和规划阶段没有考虑到？
- 根本原因识别
- 系统性改进方向

### 3. 解决方案设计

#### 3.1 临时解决方案（应急措施）
- **目标：** 快速缓解问题影响
- **措施：** 具体的临时处理步骤
- **时间：** 预计实施时间和效果
- **风险：** 临时方案的潜在风险

#### 3.2 根本解决方案（长期措施）
- **目标：** 彻底解决问题根因
- **方案：** 详细的改进计划和步骤
- **资源：** 所需的人力、时间、成本
- **效果：** 预期的改进效果和验证方法

### 4. 预防措施
- **监控机制：** 建立问题预警和监控体系
- **流程改进：** 优化相关工作流程和标准
- **能力建设：** 提升团队技能和知识水平
- **制度完善：** 建立和完善相关管理制度

### 5. 实施计划
- **优先级排序：** 按重要性和紧急性排序
- **时间安排：** 详细的实施时间表
- **责任分工：** 明确各项任务的负责人
- **里程碑设置：** 关键节点和验收标准

## 总结和建议

**核心问题：** 
**关键根因：** 
**推荐方案：** 
**实施重点：** 

谢谢您的详细分析！""",
            variables=[
                TemplateVariable(
                    name="problem_description",
                    type="string",
                    description="问题描述",
                    required=True,
                    example="系统响应缓慢，用户体验不佳"
                ),
                TemplateVariable(
                    name="environment",
                    type="string",
                    description="发生环境",
                    required=False,
                    default_value="生产环境"
                ),
                TemplateVariable(
                    name="impact_scope",
                    type="string",
                    description="影响范围",
                    required=False,
                    default_value="部分用户"
                ),
                TemplateVariable(
                    name="urgency_level",
                    type="string",
                    description="紧急程度",
                    required=False,
                    default_value="中等"
                )
            ],
            supported_providers=["文心一言", "通义千问", "ChatGLM", "OpenAI", "Claude"],
            use_cases=["问题诊断", "根因分析", "解决方案", "流程改进"],
            tags=["中文优化", "问题分析", "根因分析", "解决方案"],
            visibility=TemplateVisibility.PUBLIC
        )
        
        template = await self.prompt_service.create_template(db, template_data, user_id)
        return {"template": template, "type": "problem_analysis"}


# 全局优化器实例
_chinese_optimizer_instance: Optional[ChinesePromptOptimizer] = None


async def get_chinese_prompt_optimizer(prompt_service: PromptService = None,
                                     multilingual_service: MultilingualResponseService = None) -> ChinesePromptOptimizer:
    """获取中文提示词优化器实例"""
    global _chinese_optimizer_instance
    
    if _chinese_optimizer_instance is None:
        if not prompt_service or not multilingual_service:
            raise ValueError("需要提供 prompt_service 和 multilingual_service 实例")
        _chinese_optimizer_instance = ChinesePromptOptimizer(prompt_service, multilingual_service)
    
    return _chinese_optimizer_instance