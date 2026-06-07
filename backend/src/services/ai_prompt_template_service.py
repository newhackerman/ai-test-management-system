"""
AI提示词模板管理服务

本模块实现AI提示词模板的管理和优化功能，包括：
- 创建可配置的AI提示词模板系统
- 支持不同测试类型的模板定制
- 实现模板效果评估和持续优化
- 提供模板使用统计和分析
- 模板版本管理和A/B测试
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from enum import Enum
import logging
import json
import hashlib
import statistics

from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..utils.test_cache import TestCacheManager

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """模板类型枚举"""
    TEST_CASE_GENERATION = "TEST_CASE_GENERATION"
    AUTOMATION_SCRIPT = "AUTOMATION_SCRIPT"
    TEST_STRATEGY = "TEST_STRATEGY"
    DEFECT_ANALYSIS = "DEFECT_ANALYSIS"
    REQUIREMENT_ANALYSIS = "REQUIREMENT_ANALYSIS"
    QUALITY_ASSESSMENT = "QUALITY_ASSESSMENT"


class TemplateCategory(Enum):
    """模板分类枚举"""
    FUNCTIONAL_TESTING = "FUNCTIONAL_TESTING"
    PERFORMANCE_TESTING = "PERFORMANCE_TESTING"
    SECURITY_TESTING = "SECURITY_TESTING"
    API_TESTING = "API_TESTING"
    UI_TESTING = "UI_TESTING"
    INTEGRATION_TESTING = "INTEGRATION_TESTING"
    GENERAL = "GENERAL"


class TemplateStatus(Enum):
    """模板状态枚举"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    TESTING = "TESTING"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class AIPromptTemplate:
    """AI提示词模板类"""
    
    def __init__(self, template_id: str, name: str, template_type: TemplateType, 
                 category: TemplateCategory, prompt_content: str):
        self.template_id = template_id
        self.name = name
        self.template_type = template_type
        self.category = category
        self.prompt_content = prompt_content
        self.description = ""
        self.parameters = []
        self.status = TemplateStatus.DRAFT
        self.version = 1
        self.created_by = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # 使用统计
        self.usage_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.average_rating = 0.0
        self.effectiveness_score = 0.0
        
        # 性能指标
        self.average_response_time = 0.0
        self.average_token_usage = 0
        self.cost_per_use = 0.0
        
        # 质量指标
        self.output_quality_score = 0.0
        self.user_satisfaction_score = 0.0
        
        # 元数据
        self.tags = []
        self.examples = []
        self.best_practices = []
        
        # 计算内容哈希
        self.content_hash = self._calculate_content_hash()
    
    def _calculate_content_hash(self) -> str:
        """计算内容哈希"""
        content = f"{self.prompt_content}{json.dumps(self.parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'name': self.name,
            'template_type': self.template_type.value,
            'category': self.category.value,
            'prompt_content': self.prompt_content,
            'description': self.description,
            'parameters': self.parameters,
            'status': self.status.value,
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'usage_statistics': {
                'usage_count': self.usage_count,
                'success_count': self.success_count,
                'failure_count': self.failure_count,
                'success_rate': self.get_success_rate(),
                'average_rating': self.average_rating,
                'effectiveness_score': self.effectiveness_score
            },
            'performance_metrics': {
                'average_response_time': self.average_response_time,
                'average_token_usage': self.average_token_usage,
                'cost_per_use': self.cost_per_use
            },
            'quality_metrics': {
                'output_quality_score': self.output_quality_score,
                'user_satisfaction_score': self.user_satisfaction_score
            },
            'tags': self.tags,
            'examples': self.examples,
            'best_practices': self.best_practices,
            'content_hash': self.content_hash
        }
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100


class TemplateUsageRecord:
    """模板使用记录类"""
    
    def __init__(self, template_id: str, user_id: int, parameters: Dict[str, Any]):
        self.record_id = f"{template_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
        self.template_id = template_id
        self.user_id = user_id
        self.parameters = parameters
        self.used_at = datetime.utcnow()
        
        # 执行结果
        self.success = False
        self.response_time = 0.0
        self.token_usage = 0
        self.cost = 0.0
        self.output_quality = 0.0
        self.user_rating = 0
        self.feedback = ""
        self.error_message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'template_id': self.template_id,
            'user_id': self.user_id,
            'parameters': self.parameters,
            'used_at': self.used_at.isoformat(),
            'success': self.success,
            'response_time': self.response_time,
            'token_usage': self.token_usage,
            'cost': self.cost,
            'output_quality': self.output_quality,
            'user_rating': self.user_rating,
            'feedback': self.feedback,
            'error_message': self.error_message
        }


class AIPromptTemplateService:
    """AI提示词模板管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.cache_manager = TestCacheManager()
        
        # 内存存储（实际应用中应该使用数据库）
        self.templates = {}
        self.usage_records = {}
        self.ab_tests = {}
        
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认模板"""
        # 功能测试用例生成模板
        functional_template = AIPromptTemplate(
            'functional_test_generation',
            '功能测试用例生成模板',
            TemplateType.TEST_CASE_GENERATION,
            TemplateCategory.FUNCTIONAL_TESTING,
            """
基于以下需求描述，生成详细的功能测试用例：

需求信息：
- 需求标题：{requirement_title}
- 需求描述：{requirement_description}
- 验收标准：{acceptance_criteria}

生成要求：
1. 生成{max_cases}个测试用例
2. 包含正向测试用例和负向测试用例
3. 每个用例包含：用例标题、前置条件、测试步骤、预期结果、测试数据
4. 测试步骤要详细、可执行
5. 优先级设置为{priority}

请按照以下JSON格式返回：
{{
    "test_cases": [
        {{
            "case_title": "用例标题",
            "case_description": "用例描述",
            "priority": "{priority}",
            "preconditions": "前置条件",
            "test_steps": [
                {{"step": 1, "action": "操作描述", "expected": "预期结果"}}
            ],
            "expected_result": "整体预期结果",
            "test_data": {{"key": "value"}},
            "test_type": "positive/negative"
        }}
    ]
}}
            """
        )
        
        functional_template.description = "用于生成功能测试用例的标准模板"
        functional_template.parameters = [
            {'name': 'requirement_title', 'type': 'string', 'required': True, 'description': '需求标题'},
            {'name': 'requirement_description', 'type': 'string', 'required': True, 'description': '需求描述'},
            {'name': 'acceptance_criteria', 'type': 'string', 'required': False, 'description': '验收标准'},
            {'name': 'max_cases', 'type': 'integer', 'required': False, 'default': 5, 'description': '最大用例数'},
            {'name': 'priority', 'type': 'string', 'required': False, 'default': 'MEDIUM', 'description': '优先级'}
        ]
        functional_template.status = TemplateStatus.ACTIVE
        functional_template.tags = ['功能测试', '用例生成', '标准模板']
        
        self.templates['functional_test_generation'] = functional_template 
       # API测试用例生成模板
        api_template = AIPromptTemplate(
            'api_test_generation',
            'API测试用例生成模板',
            TemplateType.TEST_CASE_GENERATION,
            TemplateCategory.API_TESTING,
            """
基于以下API接口需求，生成详细的接口测试用例：

接口信息：
- 接口名称：{api_name}
- 接口路径：{api_path}
- 请求方法：{http_method}
- 接口描述：{api_description}
- 请求参数：{request_parameters}
- 响应格式：{response_format}

生成要求：
1. 生成{max_cases}个API测试用例
2. 包含正常请求、异常请求、边界值测试
3. 每个用例包含：请求方法、请求URL、请求头、请求体、预期响应
4. 考虑各种HTTP状态码场景
5. 包含参数验证测试

请按照以下JSON格式返回：
{{
    "test_cases": [
        {{
            "case_title": "API用例标题",
            "case_description": "用例描述",
            "priority": "{priority}",
            "api_method": "{http_method}",
            "api_url": "{api_path}",
            "request_headers": {{"Content-Type": "application/json"}},
            "request_body": {{"param": "value"}},
            "expected_status": 200,
            "expected_response": {{"result": "success"}},
            "test_type": "positive/negative/boundary"
        }}
    ]
}}
            """
        )
        
        api_template.description = "用于生成API接口测试用例的专用模板"
        api_template.parameters = [
            {'name': 'api_name', 'type': 'string', 'required': True, 'description': 'API接口名称'},
            {'name': 'api_path', 'type': 'string', 'required': True, 'description': 'API路径'},
            {'name': 'http_method', 'type': 'string', 'required': True, 'description': 'HTTP方法'},
            {'name': 'api_description', 'type': 'string', 'required': True, 'description': 'API描述'},
            {'name': 'request_parameters', 'type': 'string', 'required': False, 'description': '请求参数'},
            {'name': 'response_format', 'type': 'string', 'required': False, 'description': '响应格式'},
            {'name': 'max_cases', 'type': 'integer', 'required': False, 'default': 8, 'description': '最大用例数'},
            {'name': 'priority', 'type': 'string', 'required': False, 'default': 'HIGH', 'description': '优先级'}
        ]
        api_template.status = TemplateStatus.ACTIVE
        api_template.tags = ['API测试', '接口测试', '自动化']
        
        self.templates['api_test_generation'] = api_template
        
        # 自动化脚本生成模板
        automation_template = AIPromptTemplate(
            'automation_script_generation',
            '自动化脚本生成模板',
            TemplateType.AUTOMATION_SCRIPT,
            TemplateCategory.UI_TESTING,
            """
基于以下手动测试用例，生成{framework}自动化测试脚本（{language}语言）：

测试用例信息：
- 用例标题：{case_title}
- 用例描述：{case_description}
- 前置条件：{preconditions}
- 测试步骤：{test_steps}
- 预期结果：{expected_results}
- 测试数据：{test_data}

技术要求：
- 框架：{framework}
- 语言：{language}
- 浏览器：{browser}
- 使用页面对象模式：{use_pom}
- 包含错误处理：{include_error_handling}

请生成完整的自动化测试脚本，包含：
1. 必要的导入语句
2. 页面元素定位
3. 测试方法实现
4. 断言验证
5. 错误处理
6. 清理操作

返回JSON格式：
{{
    "script_content": "完整的脚本代码",
    "page_elements": {{"element_name": "locator"}},
    "test_methods": ["method1", "method2"],
    "dependencies": ["package1", "package2"],
    "setup_instructions": "环境设置说明"
}}
            """
        )
        
        automation_template.description = "用于生成自动化测试脚本的模板"
        automation_template.parameters = [
            {'name': 'case_title', 'type': 'string', 'required': True, 'description': '用例标题'},
            {'name': 'case_description', 'type': 'string', 'required': False, 'description': '用例描述'},
            {'name': 'preconditions', 'type': 'string', 'required': False, 'description': '前置条件'},
            {'name': 'test_steps', 'type': 'array', 'required': True, 'description': '测试步骤'},
            {'name': 'expected_results', 'type': 'string', 'required': True, 'description': '预期结果'},
            {'name': 'test_data', 'type': 'object', 'required': False, 'description': '测试数据'},
            {'name': 'framework', 'type': 'string', 'required': True, 'description': '自动化框架'},
            {'name': 'language', 'type': 'string', 'required': True, 'description': '编程语言'},
            {'name': 'browser', 'type': 'string', 'required': False, 'default': 'Chrome', 'description': '目标浏览器'},
            {'name': 'use_pom', 'type': 'boolean', 'required': False, 'default': True, 'description': '使用页面对象模式'},
            {'name': 'include_error_handling', 'type': 'boolean', 'required': False, 'default': True, 'description': '包含错误处理'}
        ]
        automation_template.status = TemplateStatus.ACTIVE
        automation_template.tags = ['自动化', '脚本生成', 'UI测试']
        
        self.templates['automation_script_generation'] = automation_template
    
    async def create_template(
        self, 
        template_data: Dict[str, Any], 
        user_id: int
    ) -> AIPromptTemplate:
        """
        创建AI提示词模板
        
        Args:
            template_data: 模板数据
            user_id: 创建用户ID
            
        Returns:
            AIPromptTemplate: 创建的模板对象
        """
        try:
            # 1. 验证模板数据
            await self._validate_template_data(template_data)
            
            # 2. 生成模板ID
            template_id = self._generate_template_id(template_data)
            
            # 3. 创建模板对象
            template = AIPromptTemplate(
                template_id=template_id,
                name=template_data['name'],
                template_type=TemplateType(template_data['template_type']),
                category=TemplateCategory(template_data['category']),
                prompt_content=template_data['prompt_content']
            )
            
            template.description = template_data.get('description', '')
            template.parameters = template_data.get('parameters', [])
            template.tags = template_data.get('tags', [])
            template.examples = template_data.get('examples', [])
            template.best_practices = template_data.get('best_practices', [])
            template.created_by = user_id
            
            # 4. 验证模板语法
            validation_result = await self._validate_template_syntax(template)
            if not validation_result['is_valid']:
                raise ValidationError(f"模板语法错误: {', '.join(validation_result['errors'])}")
            
            # 5. 保存模板
            self.templates[template_id] = template
            
            # 6. 清除缓存
            await self._clear_template_cache()
            
            logger.info(f"AI提示词模板创建成功: {template_id}, 创建人: {user_id}")
            
            return template
            
        except Exception as e:
            logger.error(f"创建AI提示词模板失败: {str(e)}")
            raise 

    async def update_template(
        self, 
        template_id: str, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> AIPromptTemplate:
        """
        更新AI提示词模板
        
        Args:
            template_id: 模板ID
            update_data: 更新数据
            user_id: 更新用户ID
            
        Returns:
            AIPromptTemplate: 更新后的模板对象
        """
        try:
            # 1. 获取模板
            template = await self.get_template_by_id(template_id)
            if not template:
                raise NotFoundError("模板不存在")
            
            # 2. 创建新版本
            old_version = template.version
            template.version += 1
            
            # 3. 更新字段
            for field, value in update_data.items():
                if hasattr(template, field) and field not in ['template_id', 'created_by', 'created_at']:
                    if field == 'template_type':
                        setattr(template, field, TemplateType(value))
                    elif field == 'category':
                        setattr(template, field, TemplateCategory(value))
                    elif field == 'status':
                        setattr(template, field, TemplateStatus(value))
                    else:
                        setattr(template, field, value)
            
            # 4. 更新时间戳和哈希
            template.updated_at = datetime.utcnow()
            template.content_hash = template._calculate_content_hash()
            
            # 5. 验证更新后的模板
            validation_result = await self._validate_template_syntax(template)
            if not validation_result['is_valid']:
                raise ValidationError(f"模板语法错误: {', '.join(validation_result['errors'])}")
            
            # 6. 记录版本变更
            await self._record_template_version_change(template_id, old_version, template.version, user_id)
            
            # 7. 清除缓存
            await self._clear_template_cache(template_id)
            
            logger.info(f"AI提示词模板更新成功: {template_id}, 版本: {old_version} -> {template.version}")
            
            return template
            
        except Exception as e:
            logger.error(f"更新AI提示词模板失败: {str(e)}")
            raise
    
    async def get_template_by_id(self, template_id: str) -> Optional[AIPromptTemplate]:
        """
        根据ID获取模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            Optional[AIPromptTemplate]: 模板对象或None
        """
        # 先尝试从缓存获取
        cached_template = await self.cache_manager.get_ai_template(template_id)
        if cached_template:
            return cached_template
        
        # 从内存获取
        template = self.templates.get(template_id)
        
        # 缓存结果
        if template:
            await self.cache_manager.set_ai_template(template_id, template)
        
        return template
    
    async def get_templates_by_type(
        self, 
        template_type: TemplateType,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None
    ) -> List[AIPromptTemplate]:
        """
        根据类型获取模板列表
        
        Args:
            template_type: 模板类型
            category: 模板分类（可选）
            status: 模板状态（可选）
            
        Returns:
            List[AIPromptTemplate]: 模板列表
        """
        templates = []
        
        for template in self.templates.values():
            if template.template_type == template_type:
                if category is None or template.category == category:
                    if status is None or template.status == status:
                        templates.append(template)
        
        # 按效果分数排序
        templates.sort(key=lambda x: x.effectiveness_score, reverse=True)
        
        return templates
    
    async def search_templates(
        self, 
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[AIPromptTemplate]:
        """
        搜索模板
        
        Args:
            query: 搜索关键词
            filters: 过滤条件
            
        Returns:
            List[AIPromptTemplate]: 搜索结果
        """
        results = []
        query_lower = query.lower()
        
        for template in self.templates.values():
            # 搜索匹配
            if (query_lower in template.name.lower() or 
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                
                # 应用过滤条件
                if self._match_filters(template, filters):
                    results.append(template)
        
        # 按相关性排序
        results.sort(key=lambda x: self._calculate_relevance_score(x, query), reverse=True)
        
        return results
    
    async def use_template(
        self, 
        template_id: str, 
        parameters: Dict[str, Any], 
        user_id: int
    ) -> Dict[str, Any]:
        """
        使用模板生成内容
        
        Args:
            template_id: 模板ID
            parameters: 模板参数
            user_id: 使用用户ID
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 1. 获取模板
            template = await self.get_template_by_id(template_id)
            if not template:
                raise NotFoundError("模板不存在")
            
            if template.status not in [TemplateStatus.ACTIVE, TemplateStatus.TESTING]:
                raise BusinessLogicError("模板状态不允许使用")
            
            # 2. 验证参数
            await self._validate_template_parameters(template, parameters)
            
            # 3. 创建使用记录
            usage_record = TemplateUsageRecord(template_id, user_id, parameters)
            
            # 4. 构建提示词
            prompt = await self._build_prompt_from_template(template, parameters)
            
            # 5. 调用AI服务
            start_time = datetime.utcnow()
            try:
                ai_response = await self.ai_service.generate_content(
                    prompt=prompt,
                    max_tokens=3000,
                    temperature=0.7
                )
                
                # 记录成功
                usage_record.success = True
                usage_record.response_time = (datetime.utcnow() - start_time).total_seconds()
                
            except Exception as e:
                # 记录失败
                usage_record.success = False
                usage_record.error_message = str(e)
                raise
            
            finally:
                # 保存使用记录
                self.usage_records[usage_record.record_id] = usage_record
                
                # 更新模板统计
                await self._update_template_statistics(template_id, usage_record)
            
            # 6. 构建返回结果
            result = {
                'template_id': template_id,
                'template_name': template.name,
                'generated_content': ai_response,
                'parameters_used': parameters,
                'usage_record_id': usage_record.record_id,
                'response_time': usage_record.response_time,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"模板使用成功: {template_id}, 用户: {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"使用模板失败: {str(e)}")
            raise

    async def evaluate_template_effectiveness(
        self, 
        template_id: str, 
        evaluation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估模板效果
        
        Args:
            template_id: 模板ID
            evaluation_data: 评估数据
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                raise NotFoundError("模板不存在")
            
            # 获取使用记录
            usage_records = await self._get_template_usage_records(template_id)
            
            if not usage_records:
                return {
                    'template_id': template_id,
                    'evaluation_status': 'insufficient_data',
                    'message': '使用数据不足，无法进行评估'
                }
            
            # 计算各项指标
            effectiveness_metrics = {
                'success_rate': self._calculate_success_rate(usage_records),
                'average_response_time': self._calculate_average_response_time(usage_records),
                'user_satisfaction': self._calculate_user_satisfaction(usage_records),
                'output_quality': self._calculate_output_quality(usage_records),
                'cost_efficiency': self._calculate_cost_efficiency(usage_records),
                'consistency': self._calculate_output_consistency(usage_records)
            }
            
            # 计算综合效果分数
            overall_score = self._calculate_overall_effectiveness_score(effectiveness_metrics)
            
            # 更新模板效果分数
            template.effectiveness_score = overall_score
            
            # 生成改进建议
            improvement_suggestions = await self._generate_improvement_suggestions(
                template, effectiveness_metrics, evaluation_data
            )
            
            evaluation_result = {
                'template_id': template_id,
                'template_name': template.name,
                'evaluation_date': datetime.utcnow().isoformat(),
                'usage_count': len(usage_records),
                'effectiveness_metrics': effectiveness_metrics,
                'overall_effectiveness_score': overall_score,
                'effectiveness_level': self._get_effectiveness_level(overall_score),
                'improvement_suggestions': improvement_suggestions,
                'evaluation_status': 'completed'
            }
            
            logger.info(f"模板效果评估完成: {template_id}, 分数: {overall_score}")
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"评估模板效果失败: {str(e)}")
            raise
    
    async def optimize_template(
        self, 
        template_id: str, 
        optimization_goals: List[str],
        user_id: int
    ) -> Dict[str, Any]:
        """
        优化模板
        
        Args:
            template_id: 模板ID
            optimization_goals: 优化目标
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                raise NotFoundError("模板不存在")
            
            # 获取使用数据和反馈
            usage_records = await self._get_template_usage_records(template_id)
            feedback_data = await self._get_template_feedback(template_id)
            
            # 构建优化提示
            optimization_prompt = await self._build_optimization_prompt(
                template, usage_records, feedback_data, optimization_goals
            )
            
            # 调用AI优化服务
            ai_response = await self.ai_service.generate_content(
                prompt=optimization_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # 解析优化建议
            optimization_suggestions = self._parse_optimization_response(ai_response)
            
            # 生成优化版本
            optimized_template_data = await self._apply_optimization_suggestions(
                template, optimization_suggestions
            )
            
            # 创建优化版本
            optimized_template_id = f"{template_id}_optimized_{int(datetime.utcnow().timestamp())}"
            optimized_template = await self.create_template(optimized_template_data, user_id)
            optimized_template.template_id = optimized_template_id
            optimized_template.status = TemplateStatus.TESTING
            
            self.templates[optimized_template_id] = optimized_template
            
            optimization_result = {
                'original_template_id': template_id,
                'optimized_template_id': optimized_template_id,
                'optimization_goals': optimization_goals,
                'optimization_suggestions': optimization_suggestions,
                'changes_made': self._compare_templates(template, optimized_template),
                'optimization_date': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            logger.info(f"模板优化完成: {template_id} -> {optimized_template_id}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"优化模板失败: {str(e)}")
            raise
    
    async def start_ab_test(
        self, 
        template_a_id: str, 
        template_b_id: str, 
        test_config: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        启动A/B测试
        
        Args:
            template_a_id: 模板A的ID
            template_b_id: 模板B的ID
            test_config: 测试配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: A/B测试信息
        """
        try:
            # 验证模板存在
            template_a = await self.get_template_by_id(template_a_id)
            template_b = await self.get_template_by_id(template_b_id)
            
            if not template_a or not template_b:
                raise NotFoundError("模板不存在")
            
            # 创建A/B测试
            test_id = f"ab_test_{int(datetime.utcnow().timestamp())}"
            ab_test = {
                'test_id': test_id,
                'template_a_id': template_a_id,
                'template_b_id': template_b_id,
                'test_config': test_config,
                'created_by': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active',
                'traffic_split': test_config.get('traffic_split', 50),  # A/B流量分配百分比
                'duration_days': test_config.get('duration_days', 7),
                'min_samples': test_config.get('min_samples', 100),
                'results': {
                    'template_a': {'usage_count': 0, 'success_count': 0, 'ratings': []},
                    'template_b': {'usage_count': 0, 'success_count': 0, 'ratings': []}
                }
            }
            
            self.ab_tests[test_id] = ab_test
            
            logger.info(f"A/B测试启动: {test_id}, 模板: {template_a_id} vs {template_b_id}")
            
            return ab_test
            
        except Exception as e:
            logger.error(f"启动A/B测试失败: {str(e)}")
            raise
    
    async def get_template_statistics(self, template_id: str) -> Dict[str, Any]:
        """
        获取模板统计信息
        
        Args:
            template_id: 模板ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        template = await self.get_template_by_id(template_id)
        if not template:
            raise NotFoundError("模板不存在")
        
        # 获取使用记录
        usage_records = await self._get_template_usage_records(template_id)
        
        # 计算统计信息
        statistics = {
            'template_id': template_id,
            'template_name': template.name,
            'basic_stats': {
                'total_usage': template.usage_count,
                'success_count': template.success_count,
                'failure_count': template.failure_count,
                'success_rate': template.get_success_rate()
            },
            'performance_stats': {
                'average_response_time': template.average_response_time,
                'average_token_usage': template.average_token_usage,
                'cost_per_use': template.cost_per_use
            },
            'quality_stats': {
                'output_quality_score': template.output_quality_score,
                'user_satisfaction_score': template.user_satisfaction_score,
                'effectiveness_score': template.effectiveness_score
            },
            'usage_trend': await self._get_usage_trend(template_id),
            'user_feedback': await self._get_recent_feedback(template_id),
            'last_updated': template.updated_at.isoformat()
        }
        
        return statistics    
# 私有方法
    def _generate_template_id(self, template_data: Dict[str, Any]) -> str:
        """生成模板ID"""
        name = template_data['name'].lower().replace(' ', '_').replace('-', '_')
        timestamp = int(datetime.utcnow().timestamp())
        return f"template_{name}_{timestamp}"
    
    async def _validate_template_data(self, template_data: Dict[str, Any]) -> None:
        """验证模板数据"""
        required_fields = ['name', 'template_type', 'category', 'prompt_content']
        for field in required_fields:
            if not template_data.get(field):
                raise ValidationError(f"字段 {field} 不能为空")
        
        # 验证枚举值
        try:
            TemplateType(template_data['template_type'])
            TemplateCategory(template_data['category'])
        except ValueError as e:
            raise ValidationError(f"无效的枚举值: {str(e)}")
        
        # 验证参数格式
        parameters = template_data.get('parameters', [])
        for param in parameters:
            if not isinstance(param, dict) or 'name' not in param or 'type' not in param:
                raise ValidationError("参数格式错误")
    
    async def _validate_template_syntax(self, template: AIPromptTemplate) -> Dict[str, Any]:
        """验证模板语法"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 检查参数占位符
            import re
            placeholders = re.findall(r'\{(\w+)\}', template.prompt_content)
            
            # 检查是否所有占位符都有对应参数
            param_names = [p['name'] for p in template.parameters]
            
            for placeholder in placeholders:
                if placeholder not in param_names:
                    validation_result['warnings'].append(f"占位符 {{{placeholder}}} 没有对应的参数定义")
            
            # 检查是否有未使用的参数
            for param_name in param_names:
                if f"{{{param_name}}}" not in template.prompt_content:
                    validation_result['warnings'].append(f"参数 {param_name} 在模板中未使用")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"语法验证错误: {str(e)}")
        
        return validation_result
    
    async def _validate_template_parameters(self, template: AIPromptTemplate, parameters: Dict[str, Any]) -> None:
        """验证模板参数"""
        # 检查必需参数
        for param in template.parameters:
            if param.get('required', False) and param['name'] not in parameters:
                raise ValidationError(f"缺少必需参数: {param['name']}")
        
        # 检查参数类型
        for param_name, param_value in parameters.items():
            param_def = next((p for p in template.parameters if p['name'] == param_name), None)
            if param_def:
                expected_type = param_def['type']
                if not self._validate_parameter_type(param_value, expected_type):
                    raise ValidationError(f"参数 {param_name} 类型错误，期望: {expected_type}")
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """验证参数类型"""
        type_mapping = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True
    
    async def _build_prompt_from_template(self, template: AIPromptTemplate, parameters: Dict[str, Any]) -> str:
        """从模板构建提示词"""
        prompt = template.prompt_content
        
        # 填充参数
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            if isinstance(param_value, (dict, list)):
                param_value = json.dumps(param_value, ensure_ascii=False)
            prompt = prompt.replace(placeholder, str(param_value))
        
        # 填充默认值
        for param in template.parameters:
            if param['name'] not in parameters and 'default' in param:
                placeholder = f"{{{param['name']}}}"
                default_value = param['default']
                if isinstance(default_value, (dict, list)):
                    default_value = json.dumps(default_value, ensure_ascii=False)
                prompt = prompt.replace(placeholder, str(default_value))
        
        return prompt
    
    async def _update_template_statistics(self, template_id: str, usage_record: TemplateUsageRecord) -> None:
        """更新模板统计信息"""
        template = self.templates.get(template_id)
        if not template:
            return
        
        # 更新使用统计
        template.usage_count += 1
        if usage_record.success:
            template.success_count += 1
        else:
            template.failure_count += 1
        
        # 更新性能指标
        if usage_record.response_time > 0:
            template.average_response_time = (
                (template.average_response_time * (template.usage_count - 1) + usage_record.response_time) 
                / template.usage_count
            )
        
        if usage_record.token_usage > 0:
            template.average_token_usage = int(
                (template.average_token_usage * (template.usage_count - 1) + usage_record.token_usage) 
                / template.usage_count
            )
        
        if usage_record.cost > 0:
            template.cost_per_use = (
                (template.cost_per_use * (template.usage_count - 1) + usage_record.cost) 
                / template.usage_count
            )
    
    async def _get_template_usage_records(self, template_id: str) -> List[TemplateUsageRecord]:
        """获取模板使用记录"""
        return [record for record in self.usage_records.values() if record.template_id == template_id]
    
    def _calculate_success_rate(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算成功率"""
        if not usage_records:
            return 0.0
        
        success_count = len([r for r in usage_records if r.success])
        return (success_count / len(usage_records)) * 100
    
    def _calculate_average_response_time(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算平均响应时间"""
        response_times = [r.response_time for r in usage_records if r.response_time > 0]
        return statistics.mean(response_times) if response_times else 0.0
    
    def _calculate_user_satisfaction(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算用户满意度"""
        ratings = [r.user_rating for r in usage_records if r.user_rating > 0]
        return statistics.mean(ratings) if ratings else 0.0
    
    def _calculate_output_quality(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算输出质量"""
        quality_scores = [r.output_quality for r in usage_records if r.output_quality > 0]
        return statistics.mean(quality_scores) if quality_scores else 0.0
    
    def _calculate_cost_efficiency(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算成本效率"""
        costs = [r.cost for r in usage_records if r.cost > 0]
        if not costs:
            return 0.0
        
        avg_cost = statistics.mean(costs)
        success_rate = self._calculate_success_rate(usage_records) / 100
        
        # 成本效率 = 成功率 / 平均成本
        return success_rate / avg_cost if avg_cost > 0 else 0.0
    
    def _calculate_output_consistency(self, usage_records: List[TemplateUsageRecord]) -> float:
        """计算输出一致性"""
        # 简化实现，基于成功率计算
        success_rate = self._calculate_success_rate(usage_records)
        return min(success_rate, 95.0)  # 最高95%
    
    def _calculate_overall_effectiveness_score(self, metrics: Dict[str, float]) -> float:
        """计算综合效果分数"""
        weights = {
            'success_rate': 0.3,
            'user_satisfaction': 0.25,
            'output_quality': 0.25,
            'cost_efficiency': 0.1,
            'consistency': 0.1
        }
        
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                score += metrics[metric] * weight
        
        return round(score, 2)
    
    def _get_effectiveness_level(self, score: float) -> str:
        """获取效果等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 60:
            return "较差"
        else:
            return "很差"
    
    def _match_filters(self, template: AIPromptTemplate, filters: Optional[Dict[str, Any]]) -> bool:
        """匹配过滤条件"""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key == 'template_type' and template.template_type.value != value:
                return False
            elif key == 'category' and template.category.value != value:
                return False
            elif key == 'status' and template.status.value != value:
                return False
            elif key == 'tags' and not any(tag in template.tags for tag in value):
                return False
        
        return True
    
    def _calculate_relevance_score(self, template: AIPromptTemplate, query: str) -> float:
        """计算相关性分数"""
        score = 0.0
        query_lower = query.lower()
        
        # 名称匹配
        if query_lower in template.name.lower():
            score += 10
        
        # 描述匹配
        if query_lower in template.description.lower():
            score += 5
        
        # 标签匹配
        for tag in template.tags:
            if query_lower in tag.lower():
                score += 3
        
        # 效果分数加权
        score += template.effectiveness_score * 0.1
        
        return score
    
    async def _record_template_version_change(self, template_id: str, old_version: int, new_version: int, user_id: int) -> None:
        """记录模板版本变更"""
        # 这里可以记录到数据库或日志
        logger.info(f"模板版本变更: {template_id}, {old_version} -> {new_version}, 用户: {user_id}")
    
    async def _clear_template_cache(self, template_id: Optional[str] = None) -> None:
        """清除模板缓存"""
        try:
            if template_id:
                await self.cache_manager.delete_ai_template(template_id)
            else:
                await self.cache_manager.clear_ai_templates()
        except Exception as e:
            logger.warning(f"清除模板缓存失败: {str(e)}")
    
    async def _generate_improvement_suggestions(
        self, 
        template: AIPromptTemplate, 
        metrics: Dict[str, float], 
        evaluation_data: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if metrics.get('success_rate', 0) < 80:
            suggestions.append("建议优化提示词结构，提高成功率")
        
        if metrics.get('user_satisfaction', 0) < 4.0:
            suggestions.append("建议收集用户反馈，改进输出质量")
        
        if metrics.get('average_response_time', 0) > 10:
            suggestions.append("建议简化提示词，减少响应时间")
        
        if template.usage_count < 10:
            suggestions.append("建议增加模板使用量，获得更多数据")
        
        return suggestions
    
    async def _build_optimization_prompt(
        self, 
        template: AIPromptTemplate, 
        usage_records: List[TemplateUsageRecord], 
        feedback_data: List[Dict[str, Any]], 
        goals: List[str]
    ) -> str:
        """构建优化提示"""
        return f"""
请优化以下AI提示词模板，优化目标：{', '.join(goals)}

当前模板：
名称：{template.name}
类型：{template.template_type.value}
内容：
{template.prompt_content}

使用统计：
- 总使用次数：{len(usage_records)}
- 成功率：{self._calculate_success_rate(usage_records):.1f}%
- 平均响应时间：{self._calculate_average_response_time(usage_records):.2f}秒

用户反馈：
{json.dumps(feedback_data, ensure_ascii=False)}

请提供优化建议和改进后的模板内容。
        """
    
    def _parse_optimization_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """解析优化响应"""
        # 简化实现，返回基本建议
        return [
            {'type': 'structure', 'suggestion': '优化提示词结构'},
            {'type': 'clarity', 'suggestion': '提高表达清晰度'},
            {'type': 'parameters', 'suggestion': '优化参数设置'}
        ]
    
    async def _apply_optimization_suggestions(
        self, 
        template: AIPromptTemplate, 
        suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """应用优化建议"""
        # 创建优化版本的数据
        optimized_data = {
            'name': f"{template.name} (优化版)",
            'template_type': template.template_type.value,
            'category': template.category.value,
            'prompt_content': template.prompt_content,  # 这里应该应用具体的优化
            'description': f"{template.description} - 基于使用数据优化",
            'parameters': template.parameters.copy(),
            'tags': template.tags + ['优化版']
        }
        
        return optimized_data
    
    def _compare_templates(self, template_a: AIPromptTemplate, template_b: AIPromptTemplate) -> List[str]:
        """比较模板差异"""
        changes = []
        
        if template_a.prompt_content != template_b.prompt_content:
            changes.append("提示词内容已修改")
        
        if template_a.parameters != template_b.parameters:
            changes.append("参数配置已修改")
        
        if template_a.description != template_b.description:
            changes.append("描述已修改")
        
        return changes
    
    async def _get_template_feedback(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板反馈"""
        usage_records = await self._get_template_usage_records(template_id)
        feedback = []
        
        for record in usage_records:
            if record.feedback:
                feedback.append({
                    'user_id': record.user_id,
                    'rating': record.user_rating,
                    'feedback': record.feedback,
                    'date': record.used_at.isoformat()
                })
        
        return feedback
    
    async def _get_usage_trend(self, template_id: str) -> List[Dict[str, Any]]:
        """获取使用趋势"""
        usage_records = await self._get_template_usage_records(template_id)
        
        # 按日期统计使用量
        daily_usage = {}
        for record in usage_records:
            date_key = record.used_at.date().isoformat()
            daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
        
        # 转换为趋势数据
        trend_data = []
        for date, count in sorted(daily_usage.items()):
            trend_data.append({'date': date, 'usage_count': count})
        
        return trend_data
    
    async def _get_recent_feedback(self, template_id: str) -> List[Dict[str, Any]]:
        """获取最近反馈"""
        feedback = await self._get_template_feedback(template_id)
        
        # 返回最近10条反馈
        return sorted(feedback, key=lambda x: x['date'], reverse=True)[:10]
