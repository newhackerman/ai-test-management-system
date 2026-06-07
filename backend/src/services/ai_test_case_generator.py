"""
AI智能测试用例生成服务

本模块实现基于AI的智能测试用例生成功能，包括：
- 基于需求描述生成测试用例
- AI提示词模板的管理和优化
- 生成用例的预览、编辑和批量保存
- 用例质量检查和完整性验证
- 多种测试类型的智能生成
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from enum import Enum
import logging
import json
import re

from ..models.test_case import TestCase, TestCaseType, TestCasePriority
from ..models.requirement import Requirement
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..services.test_case_service import TestCaseService

logger = logging.getLogger(__name__)


class GenerationTemplate(Enum):
    """生成模板类型枚举"""
    FUNCTIONAL_BASIC = "FUNCTIONAL_BASIC"
    FUNCTIONAL_ADVANCED = "FUNCTIONAL_ADVANCED"
    API_TESTING = "API_TESTING"
    UI_TESTING = "UI_TESTING"
    PERFORMANCE_TESTING = "PERFORMANCE_TESTING"
    SECURITY_TESTING = "SECURITY_TESTING"
    INTEGRATION_TESTING = "INTEGRATION_TESTING"


class GenerationConfig:
    """生成配置类"""
    
    def __init__(self):
        self.case_type = TestCaseType.FUNCTIONAL
        self.priority = TestCasePriority.MEDIUM
        self.template = GenerationTemplate.FUNCTIONAL_BASIC
        self.max_cases = 10
        self.include_negative_cases = True
        self.include_boundary_cases = True
        self.include_edge_cases = True
        self.language = "zh-CN"
        self.detail_level = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_type': self.case_type.value,
            'priority': self.priority.value,
            'template': self.template.value,
            'max_cases': self.max_cases,
            'include_negative_cases': self.include_negative_cases,
            'include_boundary_cases': self.include_boundary_cases,
            'include_edge_cases': self.include_edge_cases,
            'language': self.language,
            'detail_level': self.detail_level
        }


class AITestCaseGenerator:
    """AI测试用例生成器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.test_case_service = TestCaseService(db)
        self._init_templates()
    
    def _init_templates(self):
        """初始化AI提示词模板"""
        self.templates = {
            GenerationTemplate.FUNCTIONAL_BASIC: {
                'name': '基础功能测试用例生成',
                'description': '生成基本的功能测试用例',
                'prompt_template': """
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
                {{"step": 1, "action": "操作描述", "expected": "预期结果"}},
                {{"step": 2, "action": "操作描述", "expected": "预期结果"}}
            ],
            "expected_result": "整体预期结果",
            "test_data": {{"key": "value"}},
            "test_type": "positive/negative"
        }}
    ]
}}
                """
            },
            GenerationTemplate.API_TESTING: {
                'name': 'API接口测试用例生成',
                'description': '生成API接口测试用例',
                'prompt_template': """
基于以下API接口需求，生成详细的接口测试用例：

接口信息：
- 接口名称：{requirement_title}
- 接口描述：{requirement_description}
- 接口规范：{acceptance_criteria}

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
            "api_method": "GET/POST/PUT/DELETE",
            "api_url": "/api/endpoint",
            "request_headers": {{"Content-Type": "application/json"}},
            "request_body": {{"param": "value"}},
            "expected_status": 200,
            "expected_response": {{"result": "success"}},
            "test_type": "positive/negative/boundary"
        }}
    ]
}}
                """
            },
            GenerationTemplate.UI_TESTING: {
                'name': 'UI界面测试用例生成',
                'description': '生成UI界面测试用例',
                'prompt_template': """
基于以下UI功能需求，生成详细的界面测试用例：

UI功能信息：
- 功能名称：{requirement_title}
- 功能描述：{requirement_description}
- 界面要求：{acceptance_criteria}

生成要求：
1. 生成{max_cases}个UI测试用例
2. 包含正常操作流程和异常操作流程
3. 考虑不同浏览器和设备兼容性
4. 包含界面元素验证、交互验证、数据验证
5. 每个用例包含：页面URL、操作步骤、验证点

请按照以下JSON格式返回：
{{
    "test_cases": [
        {{
            "case_title": "UI用例标题",
            "case_description": "用例描述",
            "priority": "{priority}",
            "page_url": "页面URL",
            "preconditions": "前置条件",
            "test_steps": [
                {{"step": 1, "action": "操作描述", "element": "元素定位", "expected": "预期结果"}}
            ],
            "validation_points": ["验证点1", "验证点2"],
            "test_data": {{"input": "value"}},
            "browser_compatibility": ["Chrome", "Firefox", "Safari"]
        }}
    ]
}}
                """
            },
            GenerationTemplate.PERFORMANCE_TESTING: {
                'name': '性能测试用例生成',
                'description': '生成性能测试用例',
                'prompt_template': """
基于以下性能需求，生成详细的性能测试用例：

性能需求信息：
- 功能名称：{requirement_title}
- 性能要求：{requirement_description}
- 性能指标：{acceptance_criteria}

生成要求：
1. 生成{max_cases}个性能测试用例
2. 包含负载测试、压力测试、容量测试
3. 明确性能指标和阈值
4. 包含测试环境和数据准备要求

请按照以下JSON格式返回：
{{
    "test_cases": [
        {{
            "case_title": "性能用例标题",
            "case_description": "用例描述",
            "priority": "{priority}",
            "test_scenario": "测试场景",
            "load_parameters": {{
                "concurrent_users": 100,
                "ramp_up_time": 60,
                "test_duration": 300
            }},
            "performance_metrics": [
                {{"metric": "响应时间", "threshold": "< 2秒"}},
                {{"metric": "吞吐量", "threshold": "> 100 TPS"}}
            ],
            "test_environment": "环境要求",
            "test_data": "数据准备要求"
        }}
    ]
}}
                """
            },
            GenerationTemplate.SECURITY_TESTING: {
                'name': '安全测试用例生成',
                'description': '生成安全测试用例',
                'prompt_template': """
基于以下安全需求，生成详细的安全测试用例：

安全需求信息：
- 功能名称：{requirement_title}
- 安全要求：{requirement_description}
- 安全标准：{acceptance_criteria}

生成要求：
1. 生成{max_cases}个安全测试用例
2. 包含输入验证、权限控制、数据保护等测试
3. 考虑常见的安全漏洞（OWASP Top 10）
4. 包含恶意输入和攻击场景测试

请按照以下JSON格式返回：
{{
    "test_cases": [
        {{
            "case_title": "安全用例标题",
            "case_description": "用例描述",
            "priority": "{priority}",
            "security_category": "输入验证/权限控制/数据保护",
            "attack_vector": "攻击向量",
            "test_steps": [
                {{"step": 1, "action": "操作描述", "payload": "测试载荷", "expected": "预期结果"}}
            ],
            "risk_level": "高/中/低",
            "mitigation": "缓解措施验证"
        }}
    ]
}}
                """
            }
        }
    
    async def generate_test_cases_from_requirement(
        self, 
        requirement_id: int, 
        config: GenerationConfig,
        user_id: int
    ) -> Dict[str, Any]:
        """
        基于需求生成测试用例
        
        Args:
            requirement_id: 需求ID
            config: 生成配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 1. 获取需求信息
            requirement = self.db.query(Requirement).filter(Requirement.id == requirement_id).first()
            if not requirement:
                raise NotFoundError("需求不存在")
            
            # 2. 获取模板
            template_info = self.templates.get(config.template)
            if not template_info:
                raise ValidationError("无效的生成模板")
            
            # 3. 构建AI提示
            prompt = self._build_generation_prompt(requirement, config, template_info)
            
            # 4. 调用AI生成服务
            ai_response = await self.ai_service.generate_content(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.7
            )
            
            # 5. 解析生成结果
            generated_cases = self._parse_ai_response(ai_response, config)
            
            # 6. 质量检查和优化
            validated_cases = await self._validate_and_optimize_cases(generated_cases, requirement)
            
            # 7. 构建返回结果
            result = {
                'requirement_id': requirement_id,
                'requirement_title': requirement.title,
                'generation_config': config.to_dict(),
                'generated_cases': validated_cases,
                'generation_time': datetime.utcnow().isoformat(),
                'total_cases': len(validated_cases),
                'template_used': template_info['name']
            }
            
            logger.info(f"AI生成测试用例成功: 需求{requirement_id}, 生成{len(validated_cases)}个用例")
            
            return result
            
        except Exception as e:
            logger.error(f"AI生成测试用例失败: {str(e)}")
            raise
    
    async def generate_test_cases_from_text(
        self, 
        requirement_text: str, 
        config: GenerationConfig,
        user_id: int
    ) -> Dict[str, Any]:
        """
        基于文本描述生成测试用例
        
        Args:
            requirement_text: 需求文本描述
            config: 生成配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 1. 创建临时需求对象
            temp_requirement = type('Requirement', (), {
                'title': '临时需求',
                'description': requirement_text,
                'acceptance_criteria': ''
            })()
            
            # 2. 获取模板
            template_info = self.templates.get(config.template)
            if not template_info:
                raise ValidationError("无效的生成模板")
            
            # 3. 构建AI提示
            prompt = self._build_generation_prompt(temp_requirement, config, template_info)
            
            # 4. 调用AI生成服务
            ai_response = await self.ai_service.generate_content(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.7
            )
            
            # 5. 解析生成结果
            generated_cases = self._parse_ai_response(ai_response, config)
            
            # 6. 质量检查和优化
            validated_cases = await self._validate_and_optimize_cases(generated_cases, temp_requirement)
            
            # 7. 构建返回结果
            result = {
                'requirement_text': requirement_text,
                'generation_config': config.to_dict(),
                'generated_cases': validated_cases,
                'generation_time': datetime.utcnow().isoformat(),
                'total_cases': len(validated_cases),
                'template_used': template_info['name']
            }
            
            logger.info(f"基于文本生成测试用例成功: 生成{len(validated_cases)}个用例")
            
            return result
            
        except Exception as e:
            logger.error(f"基于文本生成测试用例失败: {str(e)}")
            raise
    
    async def batch_save_generated_cases(
        self, 
        generated_cases: List[Dict[str, Any]], 
        test_plan_id: Optional[int],
        requirement_id: Optional[int],
        user_id: int
    ) -> List[TestCase]:
        """
        批量保存生成的测试用例
        
        Args:
            generated_cases: 生成的用例列表
            test_plan_id: 测试计划ID
            requirement_id: 需求ID
            user_id: 用户ID
            
        Returns:
            List[TestCase]: 保存的用例列表
        """
        try:
            saved_cases = []
            
            for case_data in generated_cases:
                # 转换为标准格式
                standard_case_data = self._convert_to_standard_format(
                    case_data, test_plan_id, requirement_id
                )
                
                # 创建测试用例
                try:
                    saved_case = await self.test_case_service.create_test_case(
                        standard_case_data, user_id
                    )
                    saved_cases.append(saved_case)
                except Exception as e:
                    logger.warning(f"保存用例失败: {case_data.get('case_title', '未知')}, 错误: {str(e)}")
                    continue
            
            logger.info(f"批量保存测试用例完成: {len(saved_cases)}/{len(generated_cases)} 成功")
            
            return saved_cases
            
        except Exception as e:
            logger.error(f"批量保存测试用例失败: {str(e)}")
            raise
    
    async def preview_generated_cases(
        self, 
        generated_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        预览生成的测试用例
        
        Args:
            generated_cases: 生成的用例列表
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        preview_data = {
            'total_cases': len(generated_cases),
            'case_types': {},
            'priorities': {},
            'test_types': {},
            'cases_preview': []
        }
        
        for case in generated_cases:
            # 统计用例类型
            case_type = case.get('case_type', 'FUNCTIONAL')
            preview_data['case_types'][case_type] = preview_data['case_types'].get(case_type, 0) + 1
            
            # 统计优先级
            priority = case.get('priority', 'MEDIUM')
            preview_data['priorities'][priority] = preview_data['priorities'].get(priority, 0) + 1
            
            # 统计测试类型
            test_type = case.get('test_type', 'positive')
            preview_data['test_types'][test_type] = preview_data['test_types'].get(test_type, 0) + 1
            
            # 添加预览信息
            preview_data['cases_preview'].append({
                'case_title': case.get('case_title', ''),
                'case_description': case.get('case_description', ''),
                'priority': priority,
                'test_type': test_type,
                'steps_count': len(case.get('test_steps', [])),
                'has_test_data': bool(case.get('test_data'))
            })
        
        return preview_data
    
    async def optimize_generated_case(
        self, 
        case_data: Dict[str, Any], 
        optimization_type: str = "quality"
    ) -> Dict[str, Any]:
        """
        优化生成的测试用例
        
        Args:
            case_data: 用例数据
            optimization_type: 优化类型 (quality, completeness, clarity)
            
        Returns:
            Dict[str, Any]: 优化后的用例数据
        """
        try:
            optimization_prompt = self._build_optimization_prompt(case_data, optimization_type)
            
            # 调用AI优化服务
            ai_response = await self.ai_service.generate_content(
                prompt=optimization_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # 解析优化结果
            optimized_case = self._parse_optimization_response(ai_response, case_data)
            
            return optimized_case
            
        except Exception as e:
            logger.warning(f"用例优化失败: {str(e)}")
            return case_data
    
    # 私有方法
    def _build_generation_prompt(
        self, 
        requirement: Any, 
        config: GenerationConfig, 
        template_info: Dict[str, Any]
    ) -> str:
        """构建生成提示"""
        prompt_template = template_info['prompt_template']
        
        return prompt_template.format(
            requirement_title=getattr(requirement, 'title', ''),
            requirement_description=getattr(requirement, 'description', ''),
            acceptance_criteria=getattr(requirement, 'acceptance_criteria', ''),
            max_cases=config.max_cases,
            priority=config.priority.value,
            language=config.language,
            detail_level=config.detail_level
        )
    
    def _parse_ai_response(self, ai_response: str, config: GenerationConfig) -> List[Dict[str, Any]]:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if ai_response.strip().startswith('{'):
                response_data = json.loads(ai_response)
                return response_data.get('test_cases', [])
            
            # 如果不是JSON格式，尝试提取结构化信息
            return self._extract_cases_from_text(ai_response, config)
            
        except json.JSONDecodeError:
            logger.warning("AI响应不是有效的JSON格式，尝试文本解析")
            return self._extract_cases_from_text(ai_response, config)
    
    def _extract_cases_from_text(self, text: str, config: GenerationConfig) -> List[Dict[str, Any]]:
        """从文本中提取测试用例"""
        cases = []
        
        # 使用正则表达式提取用例信息
        case_pattern = r'用例标题[：:]\s*(.+?)(?:\n|$)'
        titles = re.findall(case_pattern, text, re.MULTILINE)
        
        for i, title in enumerate(titles):
            if i >= config.max_cases:
                break
            
            case = {
                'case_title': title.strip(),
                'case_description': f'基于需求生成的测试用例 {i+1}',
                'case_type': config.case_type.value,
                'priority': config.priority.value,
                'preconditions': '系统正常运行',
                'test_steps': [
                    {'step': 1, 'action': '执行测试操作', 'expected': '操作成功'}
                ],
                'expected_result': '测试通过',
                'test_data': {},
                'test_type': 'positive'
            }
            cases.append(case)
        
        return cases
    
    async def _validate_and_optimize_cases(
        self, 
        cases: List[Dict[str, Any]], 
        requirement: Any
    ) -> List[Dict[str, Any]]:
        """验证和优化用例"""
        validated_cases = []
        
        for case in cases:
            try:
                # 基本验证
                if not case.get('case_title'):
                    case['case_title'] = f"基于{getattr(requirement, 'title', '需求')}的测试用例"
                
                if not case.get('test_steps'):
                    case['test_steps'] = [
                        {'step': 1, 'action': '执行测试', 'expected': '测试通过'}
                    ]
                
                if not case.get('expected_result'):
                    case['expected_result'] = '功能正常工作'
                
                # 设置默认值
                case.setdefault('case_type', 'FUNCTIONAL')
                case.setdefault('priority', 'MEDIUM')
                case.setdefault('complexity', 'MEDIUM')
                case.setdefault('automation_level', 'MANUAL')
                
                validated_cases.append(case)
                
            except Exception as e:
                logger.warning(f"用例验证失败: {case.get('case_title', '未知')}, 错误: {str(e)}")
                continue
        
        return validated_cases
    
    def _convert_to_standard_format(
        self, 
        case_data: Dict[str, Any], 
        test_plan_id: Optional[int],
        requirement_id: Optional[int]
    ) -> Dict[str, Any]:
        """转换为标准格式"""
        standard_data = {
            'case_title': case_data.get('case_title', ''),
            'case_description': case_data.get('case_description', ''),
            'case_type': case_data.get('case_type', 'FUNCTIONAL'),
            'priority': case_data.get('priority', 'MEDIUM'),
            'complexity': case_data.get('complexity', 'MEDIUM'),
            'automation_level': case_data.get('automation_level', 'MANUAL'),
            'preconditions': case_data.get('preconditions', ''),
            'test_steps': case_data.get('test_steps', []),
            'expected_result': case_data.get('expected_result', ''),
            'test_data': case_data.get('test_data', {}),
            'test_plan_id': test_plan_id,
            'requirement_id': requirement_id
        }
        
        # 处理特殊字段
        if 'tags' in case_data:
            standard_data['tags'] = case_data['tags']
        
        if 'module' in case_data:
            standard_data['module'] = case_data['module']
        
        return standard_data
    
    def _build_optimization_prompt(self, case_data: Dict[str, Any], optimization_type: str) -> str:
        """构建优化提示"""
        base_prompt = f"""
请优化以下测试用例，重点关注{optimization_type}：

当前用例：
- 标题：{case_data.get('case_title', '')}
- 描述：{case_data.get('case_description', '')}
- 前置条件：{case_data.get('preconditions', '')}
- 测试步骤：{json.dumps(case_data.get('test_steps', []), ensure_ascii=False)}
- 预期结果：{case_data.get('expected_result', '')}
- 测试数据：{json.dumps(case_data.get('test_data', {}), ensure_ascii=False)}

优化要求：
        """
        
        if optimization_type == "quality":
            base_prompt += """
1. 提高用例的整体质量
2. 确保步骤清晰、可执行
3. 完善测试数据
4. 优化预期结果描述
            """
        elif optimization_type == "completeness":
            base_prompt += """
1. 补充缺失的信息
2. 完善测试步骤
3. 添加边界条件测试
4. 补充异常场景
            """
        elif optimization_type == "clarity":
            base_prompt += """
1. 提高描述的清晰度
2. 使用更准确的术语
3. 简化复杂的步骤
4. 改进可读性
            """
        
        base_prompt += """

请返回优化后的用例，保持JSON格式：
{
    "case_title": "优化后的标题",
    "case_description": "优化后的描述",
    "preconditions": "优化后的前置条件",
    "test_steps": [
        {"step": 1, "action": "优化后的操作", "expected": "优化后的预期"}
    ],
    "expected_result": "优化后的预期结果",
    "test_data": {"key": "优化后的数据"}
}
        """
        
        return base_prompt
    
    def _parse_optimization_response(self, ai_response: str, original_case: Dict[str, Any]) -> Dict[str, Any]:
        """解析优化响应"""
        try:
            optimized_data = json.loads(ai_response)
            
            # 合并原始数据和优化数据
            result = original_case.copy()
            result.update(optimized_data)
            
            return result
            
        except json.JSONDecodeError:
            logger.warning("优化响应解析失败，返回原始用例")
            return original_case


class AIPromptTemplateManager:
    """AI提示词模板管理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载模板"""
        # 这里可以从数据库或配置文件加载模板
        pass
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板"""
        return self.templates.get(template_id)
    
    async def create_template(
        self, 
        template_data: Dict[str, Any], 
        user_id: int
    ) -> Dict[str, Any]:
        """创建模板"""
        template = {
            'id': template_data['id'],
            'name': template_data['name'],
            'description': template_data['description'],
            'template_type': template_data['template_type'],
            'prompt_template': template_data['prompt_template'],
            'parameters': template_data.get('parameters', []),
            'created_by': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'usage_count': 0,
            'effectiveness_score': 0.0
        }
        
        self.templates[template['id']] = template
        return template
    
    async def update_template(
        self, 
        template_id: str, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> Dict[str, Any]:
        """更新模板"""
        if template_id not in self.templates:
            raise NotFoundError("模板不存在")
        
        template = self.templates[template_id]
        template.update(update_data)
        template['updated_by'] = user_id
        template['updated_at'] = datetime.utcnow().isoformat()
        
        return template
    
    async def evaluate_template_effectiveness(
        self, 
        template_id: str, 
        generated_cases: List[Dict[str, Any]],
        user_feedback: Dict[str, Any]
    ) -> float:
        """评估模板效果"""
        if template_id not in self.templates:
            return 0.0
        
        # 基于生成质量和用户反馈计算效果分数
        quality_score = self._calculate_quality_score(generated_cases)
        feedback_score = self._calculate_feedback_score(user_feedback)
        
        effectiveness_score = (quality_score * 0.6 + feedback_score * 0.4)
        
        # 更新模板效果分数
        template = self.templates[template_id]
        template['effectiveness_score'] = effectiveness_score
        template['usage_count'] += 1
        
        return effectiveness_score
    
    def _calculate_quality_score(self, generated_cases: List[Dict[str, Any]]) -> float:
        """计算质量分数"""
        if not generated_cases:
            return 0.0
        
        total_score = 0
        for case in generated_cases:
            score = 0
            
            # 检查必要字段
            if case.get('case_title'):
                score += 20
            if case.get('test_steps'):
                score += 30
            if case.get('expected_result'):
                score += 20
            if case.get('test_data'):
                score += 15
            if case.get('preconditions'):
                score += 15
            
            total_score += score
        
        return total_score / len(generated_cases)
    
    def _calculate_feedback_score(self, user_feedback: Dict[str, Any]) -> float:
        """计算用户反馈分数"""
        rating = user_feedback.get('rating', 3)  # 1-5分
        return (rating / 5) * 100
    
    async def get_template_statistics(self, template_id: str) -> Dict[str, Any]:
        """获取模板统计信息"""
        if template_id not in self.templates:
            raise NotFoundError("模板不存在")
        
        template = self.templates[template_id]
        
        return {
            'template_id': template_id,
            'usage_count': template['usage_count'],
            'effectiveness_score': template['effectiveness_score'],
            'created_at': template['created_at'],
            'last_used': template.get('last_used'),
            'average_cases_generated': template.get('average_cases_generated', 0),
            'user_satisfaction': template.get('user_satisfaction', 0.0)
        }