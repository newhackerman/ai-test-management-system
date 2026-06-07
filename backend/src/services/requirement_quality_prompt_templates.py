"""
需求质量分析提示词模板

提供专业的需求质量分析提示词模板，包括：
1. 需求完整性检查模板
2. 需求一致性分析模板
3. 需求复杂度评估模板
4. 需求工作量估算模板
5. 需求质量综合评估模板

所有模板都基于软件工程最佳实践和需求工程标准。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PromptTemplate(Enum):
    """提示词模板类型"""
    QUALITY_ANALYSIS = "quality_analysis"
    COMPLETENESS_CHECK = "completeness_check"
    CONSISTENCY_ANALYSIS = "consistency_analysis"
    COMPLEXITY_ASSESSMENT = "complexity_assessment"
    EFFORT_ESTIMATION = "effort_estimation"
    TESTABILITY_ANALYSIS = "testability_analysis"


@dataclass
class PromptContext:
    """提示词上下文"""
    requirement_title: str
    requirement_description: str
    acceptance_criteria: Optional[str] = None
    requirement_type: Optional[str] = None
    project_context: Optional[Dict[str, Any]] = None
    existing_requirements: Optional[List[Dict[str, Any]]] = None


class RequirementQualityPromptTemplates:
    """需求质量分析提示词模板类"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return """你是一位资深的需求分析专家和软件工程师，拥有15年以上的需求工程经验。你的专长包括：

1. 需求质量评估 - 基于IEEE 830标准和BABOK指南
2. 需求完整性分析 - 识别缺失的关键信息
3. 需求一致性检查 - 发现内部矛盾和外部冲突
4. 需求可测试性评估 - 确保需求可验证和可测试
5. 技术可行性分析 - 评估实现复杂度和技术风险
6. 工作量估算 - 基于历史数据和复杂度分析

你的分析标准：
- 遵循SMART原则（具体、可测量、可实现、相关、有时限）
- 应用需求工程最佳实践
- 考虑业务价值和技术约束
- 提供具体可行的改进建议
- 保持客观和专业的评估态度

请始终以JSON格式返回结构化的分析结果，确保数据的准确性和一致性。"""
    
    @staticmethod
    def get_quality_analysis_prompt(context: PromptContext) -> str:
        """获取需求质量综合分析提示词"""
        prompt = f"""请对以下需求进行全面的质量分析：

## 需求信息
**标题**: {context.requirement_title}

**描述**:
{context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"""
**验收标准**:
{context.acceptance_criteria}
"""
        
        if context.requirement_type:
            prompt += f"""
**需求类型**: {context.requirement_type}
"""
        
        if context.project_context:
            prompt += f"""
**项目背景**: {context.project_context.get('description', '未提供')}
**技术栈**: {context.project_context.get('tech_stack', '未指定')}
**团队规模**: {context.project_context.get('team_size', '未知')}
"""
        
        prompt += """
## 分析要求

请从以下6个维度进行详细分析，每个维度评分0-10分：

### 1. 完整性 (Completeness)
- 是否包含所有必要的功能描述？
- 是否明确了输入、输出和处理逻辑？
- 是否定义了边界条件和异常情况？
- 是否包含了用户角色和权限要求？
- 是否考虑了数据完整性和安全性？

### 2. 一致性 (Consistency)
- 需求内部是否存在矛盾？
- 术语使用是否一致？
- 与业务目标是否一致？
- 与技术架构是否兼容？
- 与现有系统是否协调？

### 3. 清晰性 (Clarity)
- 表述是否清晰明确？
- 是否存在歧义或模糊表达？
- 技术术语使用是否准确？
- 是否易于理解和实现？
- 是否有具体的示例说明？

### 4. 可测试性 (Testability)
- 验收标准是否明确可测？
- 是否可以设计有效的测试用例？
- 成功标准是否可量化？
- 是否考虑了正常和异常场景？
- 是否便于自动化测试？

### 5. 可行性 (Feasibility)
- 技术实现是否可行？
- 时间和资源约束是否合理？
- 是否存在技术风险？
- 依赖关系是否明确？
- 是否符合性能要求？

### 6. 可追溯性 (Traceability)
- 是否可以追溯到业务需求？
- 与其他需求的关系是否清晰？
- 是否便于变更影响分析？
- 是否支持需求覆盖率分析？
- 是否有明确的验证标准？

## 复杂度评估

请评估需求的技术复杂度：
- **简单** (1-3人天): 标准CRUD操作，无复杂业务逻辑
- **中等** (3-8人天): 涉及业务规则，需要一定的设计和集成
- **复杂** (8-20人天): 复杂业务逻辑，多系统集成，性能要求高
- **极复杂** (20+人天): 创新性功能，高技术难度，重大架构变更

## 工作量估算

基于以下因素估算开发工作量（人天）：
- 功能复杂度和业务逻辑
- 技术实现难度
- 集成和依赖复杂度
- 测试和质量保证工作
- 文档和部署工作

## 返回格式

请严格按照以下JSON格式返回分析结果：

```json
{
  "overall_score": 7.5,
  "quality_scores": [
    {
      "dimension": "completeness",
      "score": 8.0,
      "description": "需求基本完整，但缺少异常处理说明",
      "suggestions": ["补充错误处理场景", "明确边界条件"]
    },
    {
      "dimension": "consistency",
      "score": 7.5,
      "description": "需求内部一致，术语使用规范",
      "suggestions": ["统一数据格式定义"]
    }
  ],
  "completeness_score": 8.0,
  "consistency_score": 7.5,
  "clarity_score": 7.0,
  "testability_score": 6.5,
  "feasibility_score": 8.5,
  "traceability_score": 7.0,
  "complexity_estimate": "medium",
  "effort_estimate": 5.5,
  "improvement_suggestions": [
    "补充异常处理场景描述",
    "明确性能和安全要求",
    "添加具体的用户交互流程",
    "完善验收标准的可测试性"
  ],
  "risk_factors": [
    "第三方API依赖可能影响稳定性",
    "数据一致性要求较高",
    "用户权限控制复杂度中等"
  ],
  "confidence_level": 0.85
}
```

请确保分析客观准确，建议具体可行。"""
        
        return prompt
    
    @staticmethod
    def get_completeness_check_prompt(context: PromptContext) -> str:
        """获取需求完整性检查提示词"""
        prompt = f"""请专门检查以下需求的完整性：

## 需求信息
**标题**: {context.requirement_title}
**描述**: {context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"**验收标准**: {context.acceptance_criteria}\n"
        
        prompt += """
## 完整性检查清单

请检查需求是否包含以下关键要素：

### 功能性要素
- [ ] 明确的功能描述和目标
- [ ] 输入数据的格式和来源
- [ ] 输出结果的格式和去向
- [ ] 处理逻辑和业务规则
- [ ] 用户角色和权限定义
- [ ] 用户界面和交互要求

### 非功能性要素
- [ ] 性能要求（响应时间、吞吐量）
- [ ] 安全性要求（认证、授权、加密）
- [ ] 可用性要求（正常运行时间）
- [ ] 兼容性要求（浏览器、设备）
- [ ] 可维护性要求
- [ ] 可扩展性要求

### 约束条件
- [ ] 技术约束和限制
- [ ] 业务规则和政策
- [ ] 法规和合规要求
- [ ] 时间和资源约束
- [ ] 集成和依赖关系

### 验证标准
- [ ] 明确的验收标准
- [ ] 可测试的成功标准
- [ ] 错误和异常处理
- [ ] 边界条件定义
- [ ] 测试数据要求

请以JSON格式返回检查结果：

```json
{
  "completeness_score": 7.5,
  "missing_elements": [
    "性能要求未明确",
    "错误处理场景缺失",
    "用户权限定义不完整"
  ],
  "present_elements": [
    "基本功能描述清晰",
    "输入输出格式明确",
    "主要业务规则已定义"
  ],
  "improvement_suggestions": [
    "补充响应时间要求（建议<2秒）",
    "添加异常情况处理说明",
    "明确不同用户角色的操作权限",
    "定义数据验证规则"
  ],
  "priority_gaps": [
    {
      "element": "性能要求",
      "priority": "high",
      "reason": "影响用户体验和系统设计"
    },
    {
      "element": "错误处理",
      "priority": "medium", 
      "reason": "影响系统稳定性"
    }
  ]
}
```"""
        
        return prompt
    
    @staticmethod
    def get_consistency_analysis_prompt(context: PromptContext) -> str:
        """获取需求一致性分析提示词"""
        prompt = f"""请分析以下需求的一致性：

## 需求信息
**标题**: {context.requirement_title}
**描述**: {context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"**验收标准**: {context.acceptance_criteria}\n"
        
        if context.existing_requirements:
            prompt += "\n## 相关需求\n"
            for i, req in enumerate(context.existing_requirements[:5]):
                prompt += f"{i+1}. {req.get('title', '')}: {req.get('description', '')[:100]}...\n"
        
        prompt += """
## 一致性分析维度

### 1. 内部一致性
- 需求描述与验收标准是否一致？
- 功能要求与非功能要求是否冲突？
- 术语和概念使用是否统一？
- 数据定义是否前后一致？

### 2. 外部一致性
- 与业务目标是否一致？
- 与技术架构是否兼容？
- 与现有需求是否冲突？
- 与用户期望是否匹配？

### 3. 语义一致性
- 术语定义是否明确统一？
- 概念使用是否准确？
- 表达方式是否规范？
- 逻辑关系是否清晰？

请以JSON格式返回分析结果：

```json
{
  "consistency_score": 8.0,
  "internal_consistency": {
    "score": 8.5,
    "issues": [],
    "strengths": ["描述与验收标准一致", "术语使用规范"]
  },
  "external_consistency": {
    "score": 7.5,
    "issues": ["与需求REQ-001存在轻微冲突"],
    "strengths": ["符合业务目标", "技术架构兼容"]
  },
  "semantic_consistency": {
    "score": 8.0,
    "issues": [],
    "strengths": ["术语定义清晰", "逻辑关系明确"]
  },
  "identified_conflicts": [
    {
      "type": "data_definition",
      "description": "用户ID格式定义与REQ-001不一致",
      "severity": "medium",
      "resolution": "统一使用UUID格式"
    }
  ],
  "improvement_suggestions": [
    "统一用户标识符格式定义",
    "建立术语词汇表",
    "与相关需求进行一致性检查"
  ]
}
```"""
        
        return prompt
    
    @staticmethod
    def get_complexity_assessment_prompt(context: PromptContext) -> str:
        """获取需求复杂度评估提示词"""
        prompt = f"""请评估以下需求的技术复杂度：

## 需求信息
**标题**: {context.requirement_title}
**描述**: {context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"**验收标准**: {context.acceptance_criteria}\n"
        
        if context.project_context:
            prompt += f"""
## 项目背景
**技术栈**: {context.project_context.get('tech_stack', '未指定')}
**团队经验**: {context.project_context.get('team_experience', '中等')}
**时间约束**: {context.project_context.get('timeline', '正常')}
"""
        
        prompt += """
## 复杂度评估维度

### 1. 功能复杂度 (30%)
- 业务逻辑复杂程度
- 数据处理复杂度
- 用户交互复杂度
- 集成接口数量

### 2. 技术复杂度 (25%)
- 技术实现难度
- 新技术使用程度
- 性能优化要求
- 安全性要求

### 3. 集成复杂度 (20%)
- 外部系统依赖
- 数据同步要求
- API集成数量
- 第三方服务依赖

### 4. 数据复杂度 (15%)
- 数据模型复杂度
- 数据迁移需求
- 数据一致性要求
- 数据量级大小

### 5. 测试复杂度 (10%)
- 测试场景数量
- 自动化测试难度
- 性能测试要求
- 集成测试复杂度

## 复杂度等级定义

- **简单** (1-3人天): 标准功能，成熟技术，少量集成
- **中等** (3-8人天): 一般业务逻辑，常用技术，适度集成
- **复杂** (8-20人天): 复杂业务逻辑，新技术应用，多系统集成
- **极复杂** (20+人天): 创新功能，高难度技术，重大架构变更

请以JSON格式返回评估结果：

```json
{
  "overall_complexity": "medium",
  "complexity_score": 6.5,
  "dimension_scores": {
    "functional_complexity": 7.0,
    "technical_complexity": 6.0,
    "integration_complexity": 5.5,
    "data_complexity": 7.5,
    "testing_complexity": 6.0
  },
  "complexity_factors": [
    {
      "factor": "多表关联查询",
      "impact": "medium",
      "description": "需要优化查询性能"
    },
    {
      "factor": "实时数据同步",
      "impact": "high",
      "description": "增加技术实现难度"
    }
  ],
  "risk_factors": [
    "第三方API稳定性风险",
    "数据一致性保证难度",
    "性能优化挑战"
  ],
  "mitigation_strategies": [
    "设计API重试机制",
    "实现数据校验和回滚",
    "进行性能测试和优化"
  ],
  "estimated_effort": 6.5,
  "confidence_level": 0.8
}
```"""
        
        return prompt
    
    @staticmethod
    def get_effort_estimation_prompt(context: PromptContext) -> str:
        """获取工作量估算提示词"""
        prompt = f"""请估算以下需求的开发工作量：

## 需求信息
**标题**: {context.requirement_title}
**描述**: {context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"**验收标准**: {context.acceptance_criteria}\n"
        
        if context.project_context:
            prompt += f"""
## 项目背景
**团队规模**: {context.project_context.get('team_size', '5人')}
**团队经验**: {context.project_context.get('team_experience', '中等')}
**开发模式**: {context.project_context.get('dev_methodology', 'Scrum')}
**技术栈**: {context.project_context.get('tech_stack', '未指定')}
"""
        
        prompt += """
## 工作量估算维度

### 1. 分析设计 (15-20%)
- 需求分析和澄清
- 技术方案设计
- 数据库设计
- 接口设计
- 架构设计

### 2. 开发实现 (50-60%)
- 前端开发
- 后端开发
- 数据库开发
- 接口开发
- 集成开发

### 3. 测试验证 (20-25%)
- 单元测试
- 集成测试
- 系统测试
- 用户验收测试
- 性能测试

### 4. 部署运维 (5-10%)
- 环境配置
- 部署脚本
- 监控配置
- 文档编写
- 培训支持

## 影响因素

### 正面因素（减少工作量）
- 团队经验丰富
- 技术栈熟悉
- 需求清晰明确
- 有现成组件可复用
- 开发工具完善

### 负面因素（增加工作量）
- 新技术学习成本
- 需求变更频繁
- 集成复杂度高
- 性能要求严格
- 安全要求复杂

请以JSON格式返回估算结果：

```json
{
  "total_effort": 8.5,
  "effort_breakdown": {
    "analysis_design": 1.5,
    "development": 5.0,
    "testing": 1.5,
    "deployment": 0.5
  },
  "effort_by_role": {
    "business_analyst": 0.5,
    "architect": 0.5,
    "frontend_developer": 2.0,
    "backend_developer": 3.0,
    "tester": 1.5,
    "devops": 0.5,
    "project_manager": 0.5
  },
  "estimation_factors": {
    "positive_factors": [
      "团队对技术栈熟悉",
      "有类似功能可参考",
      "需求相对清晰"
    ],
    "negative_factors": [
      "需要新的第三方集成",
      "性能要求较高",
      "数据迁移复杂"
    ]
  },
  "risk_buffer": 1.5,
  "confidence_range": {
    "min_effort": 7.0,
    "max_effort": 12.0,
    "confidence_level": 0.75
  },
  "assumptions": [
    "团队成员经验水平中等",
    "需求变更控制在10%以内",
    "第三方API稳定可用",
    "测试环境及时就绪"
  ],
  "recommendations": [
    "预留20%的风险缓冲时间",
    "尽早进行技术验证",
    "制定详细的集成测试计划",
    "建立需求变更控制流程"
  ]
}
```"""
        
        return prompt
    
    @staticmethod
    def get_testability_analysis_prompt(context: PromptContext) -> str:
        """获取可测试性分析提示词"""
        prompt = f"""请分析以下需求的可测试性：

## 需求信息
**标题**: {context.requirement_title}
**描述**: {context.requirement_description}
"""
        
        if context.acceptance_criteria:
            prompt += f"**验收标准**: {context.acceptance_criteria}\n"
        
        prompt += """
## 可测试性分析维度

### 1. 验收标准质量
- 是否具体明确？
- 是否可量化验证？
- 是否覆盖主要场景？
- 是否包含异常情况？

### 2. 测试场景覆盖
- 正常流程测试
- 异常流程测试
- 边界条件测试
- 性能测试场景
- 安全测试场景

### 3. 测试数据要求
- 测试数据是否易于准备？
- 是否需要特殊环境？
- 数据依赖是否复杂？
- 是否支持自动化？

### 4. 验证方法
- 结果是否可观察？
- 是否有明确的成功标准？
- 是否支持自动化验证？
- 是否便于回归测试？

请以JSON格式返回分析结果：

```json
{
  "testability_score": 7.5,
  "acceptance_criteria_quality": {
    "score": 8.0,
    "strengths": ["标准明确具体", "覆盖主要场景"],
    "weaknesses": ["缺少性能标准", "异常场景不完整"]
  },
  "test_scenario_coverage": {
    "score": 7.0,
    "normal_scenarios": 8,
    "exception_scenarios": 5,
    "boundary_scenarios": 6,
    "performance_scenarios": 4,
    "security_scenarios": 6
  },
  "test_data_requirements": {
    "complexity": "medium",
    "preparation_effort": "moderate",
    "automation_friendly": true,
    "special_requirements": ["需要模拟第三方API响应"]
  },
  "verification_methods": [
    {
      "aspect": "功能正确性",
      "method": "UI自动化测试",
      "feasibility": "high"
    },
    {
      "aspect": "性能表现",
      "method": "性能测试工具",
      "feasibility": "medium"
    }
  ],
  "improvement_suggestions": [
    "补充具体的性能验收标准",
    "添加异常情况的处理验证",
    "定义边界值测试用例",
    "设计自动化测试友好的接口"
  ],
  "testing_challenges": [
    "第三方服务依赖难以模拟",
    "复杂业务规则验证困难",
    "大数据量场景测试成本高"
  ],
  "automation_potential": {
    "unit_testing": "high",
    "integration_testing": "medium", 
    "ui_testing": "medium",
    "performance_testing": "high"
  }
}
```"""
        
        return prompt


def get_prompt_template(template_type: PromptTemplate, context: PromptContext) -> str:
    """
    获取指定类型的提示词模板
    
    Args:
        template_type: 模板类型
        context: 提示词上下文
        
    Returns:
        str: 格式化的提示词
    """
    templates = RequirementQualityPromptTemplates()
    
    if template_type == PromptTemplate.QUALITY_ANALYSIS:
        return templates.get_quality_analysis_prompt(context)
    elif template_type == PromptTemplate.COMPLETENESS_CHECK:
        return templates.get_completeness_check_prompt(context)
    elif template_type == PromptTemplate.CONSISTENCY_ANALYSIS:
        return templates.get_consistency_analysis_prompt(context)
    elif template_type == PromptTemplate.COMPLEXITY_ASSESSMENT:
        return templates.get_complexity_assessment_prompt(context)
    elif template_type == PromptTemplate.EFFORT_ESTIMATION:
        return templates.get_effort_estimation_prompt(context)
    elif template_type == PromptTemplate.TESTABILITY_ANALYSIS:
        return templates.get_testability_analysis_prompt(context)
    else:
        raise ValueError(f"Unknown template type: {template_type}")


def get_system_prompt() -> str:
    """获取系统提示词"""
    return RequirementQualityPromptTemplates.get_system_prompt()