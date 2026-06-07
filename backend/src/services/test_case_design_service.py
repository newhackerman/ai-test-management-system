"""
测试用例设计方法和模板服务

本模块实现测试用例设计的各种方法和模板，包括：
- 等价类划分法
- 边界值分析法
- 场景法
- 决策表法
- 正交试验法
- 用例设计指导和最佳实践建议
- 用例模板的创建和复用
- 用例质量检查和评估
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from enum import Enum
import logging
import json

from ..models.test_case import TestCase, TestCaseType, TestCasePriority
from ..core.exceptions import ValidationError, NotFoundError
from ..services.ai_assistant_service import AIAssistantService

logger = logging.getLogger(__name__)


class TestDesignMethod(Enum):
    """测试设计方法枚举"""
    EQUIVALENCE_PARTITIONING = "EQUIVALENCE_PARTITIONING"  # 等价类划分
    BOUNDARY_VALUE_ANALYSIS = "BOUNDARY_VALUE_ANALYSIS"    # 边界值分析
    SCENARIO_TESTING = "SCENARIO_TESTING"                  # 场景法
    DECISION_TABLE = "DECISION_TABLE"                      # 决策表法
    ORTHOGONAL_ARRAY = "ORTHOGONAL_ARRAY"                 # 正交试验法
    STATE_TRANSITION = "STATE_TRANSITION"                 # 状态转换法
    USE_CASE_TESTING = "USE_CASE_TESTING"                 # 用例测试法


class TestCaseTemplate:
    """测试用例模板类"""
    
    def __init__(self, template_id: str, name: str, description: str, 
                 case_type: TestCaseType, design_method: TestDesignMethod):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.case_type = case_type
        self.design_method = design_method
        self.template_structure = {}
        self.quality_criteria = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'case_type': self.case_type.value,
            'design_method': self.design_method.value,
            'template_structure': self.template_structure,
            'quality_criteria': self.quality_criteria
        }


class TestCaseDesignService:
    """测试用例设计服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self._init_templates()
    
    def _init_templates(self):
        """初始化测试用例模板"""
        self.templates = {
            'functional_basic': TestCaseTemplate(
                'functional_basic',
                '基础功能测试模板',
                '适用于基本功能验证的测试用例模板',
                TestCaseType.FUNCTIONAL,
                TestDesignMethod.SCENARIO_TESTING
            ),
            'api_testing': TestCaseTemplate(
                'api_testing',
                'API接口测试模板',
                '适用于API接口测试的用例模板',
                TestCaseType.FUNCTIONAL,
                TestDesignMethod.BOUNDARY_VALUE_ANALYSIS
            ),
            'ui_testing': TestCaseTemplate(
                'ui_testing',
                'UI界面测试模板',
                '适用于用户界面测试的用例模板',
                TestCaseType.FUNCTIONAL,
                TestDesignMethod.SCENARIO_TESTING
            ),
            'performance_testing': TestCaseTemplate(
                'performance_testing',
                '性能测试模板',
                '适用于性能测试的用例模板',
                TestCaseType.PERFORMANCE,
                TestDesignMethod.BOUNDARY_VALUE_ANALYSIS
            )
        }
        
        # 设置模板结构
        self._setup_template_structures()
    
    def _setup_template_structures(self):
        """设置模板结构"""
        # 基础功能测试模板
        self.templates['functional_basic'].template_structure = {
            'preconditions': {
                'required': True,
                'description': '执行测试前需要满足的条件',
                'example': '用户已登录系统，具有相应权限'
            },
            'test_steps': {
                'required': True,
                'description': '详细的测试执行步骤',
                'format': 'list',
                'example': [
                    {'step': 1, 'action': '打开功能页面', 'expected': '页面正常加载'},
                    {'step': 2, 'action': '输入测试数据', 'expected': '数据输入成功'},
                    {'step': 3, 'action': '点击提交按钮', 'expected': '操作执行成功'}
                ]
            },
            'test_data': {
                'required': False,
                'description': '测试所需的数据',
                'example': {'username': 'test_user', 'password': 'test_pass'}
            },
            'expected_result': {
                'required': True,
                'description': '预期的测试结果',
                'example': '功能正常执行，返回预期结果'
            }
        }

        # API interface testing template
        self.templates['api_testing'].template_structure = {
            'api_endpoint': {
                'required': True,
                'description': 'API接口地址',
                'example': 'POST /api/v1/users'
            },
            'request_headers': {
                'required': False,
                'description': '请求头信息',
                'example': {'Content-Type': 'application/json', 'Authorization': 'Bearer token'}
            },
            'request_body': {
                'required': False,
                'description': '请求体数据',
                'example': {'name': 'test', 'email': 'test@example.com'}
            },
            'test_scenarios': {
                'required': True,
                'description': '测试场景列表',
                'format': 'list',
                'example': [
                    {'scenario': '正常请求', 'expected_status': 200, 'expected_response': '成功响应'},
                    {'scenario': '参数缺失', 'expected_status': 400, 'expected_response': '参数错误'},
                    {'scenario': '权限不足', 'expected_status': 403, 'expected_response': '权限拒绝'}
                ]
            }
        }
        
        # UI界面测试模板
        self.templates['ui_testing'].template_structure = {
            'page_url': {
                'required': True,
                'description': '测试页面URL',
                'example': 'https://example.com/login'
            },
            'ui_elements': {
                'required': True,
                'description': '涉及的UI元素',
                'format': 'list',
                'example': [
                    {'element': '用户名输入框', 'locator': '#username'},
                    {'element': '密码输入框', 'locator': '#password'},
                    {'element': '登录按钮', 'locator': '#login-btn'}
                ]
            },
            'user_actions': {
                'required': True,
                'description': '用户操作序列',
                'format': 'list',
                'example': [
                    {'action': '输入用户名', 'data': 'testuser'},
                    {'action': '输入密码', 'data': 'password123'},
                    {'action': '点击登录按钮', 'data': None}
                ]
            },
            'validation_points': {
                'required': True,
                'description': '验证点',
                'format': 'list',
                'example': [
                    {'point': '页面跳转', 'expected': '跳转到首页'},
                    {'point': '用户状态', 'expected': '显示已登录状态'}
                ]
            }
        }
        
        # 性能测试模板
        self.templates['performance_testing'].template_structure = {
            'test_scenario': {
                'required': True,
                'description': '性能测试场景',
                'example': '用户登录并发测试'
            },
            'load_parameters': {
                'required': True,
                'description': '负载参数',
                'example': {
                    'concurrent_users': 100,
                    'ramp_up_time': 60,
                    'test_duration': 300
                }
            },
            'performance_metrics': {
                'required': True,
                'description': '性能指标',
                'format': 'list',
                'example': [
                    {'metric': '响应时间', 'threshold': '< 2秒'},
                    {'metric': '吞吐量', 'threshold': '> 50 TPS'},
                    {'metric': 'CPU使用率', 'threshold': '< 80%'}
                ]
            },
            'test_data': {
                'required': True,
                'description': '测试数据配置',
                'example': {'data_file': 'users.csv', 'data_size': 1000}
            }
        }
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        获取可用的测试用例模板
        
        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        return [template.to_dict() for template in self.templates.values()]
    
    async def get_template_by_id(self, template_id: str) -> Optional[TestCaseTemplate]:
        """
        根据ID获取模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            Optional[TestCaseTemplate]: 模板对象或None
        """
        return self.templates.get(template_id)
    
    async def create_case_from_template(
        self, 
        template_id: str, 
        case_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        基于模板创建测试用例
        
        Args:
            template_id: 模板ID
            case_data: 用例数据
            
        Returns:
            Dict[str, Any]: 生成的用例数据
        """
        template = await self.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"模板 {template_id} 不存在")
        
        # 基于模板结构生成用例
        generated_case = {
            'case_title': case_data.get('case_title', f'基于{template.name}的测试用例'),
            'case_description': case_data.get('case_description', template.description),
            'case_type': template.case_type.value,
            'priority': case_data.get('priority', 'MEDIUM'),
            'complexity': case_data.get('complexity', 'MEDIUM'),
            'design_method': template.design_method.value
        }
        
        # 根据模板结构填充字段
        for field, config in template.template_structure.items():
            if field in case_data:
                generated_case[field] = case_data[field]
            elif config.get('required', False):
                generated_case[field] = config.get('example', '')
        
        return generated_case

    async def apply_equivalence_partitioning(
        self, 
        input_specification: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        应用等价类划分法生成测试用例
        
        Args:
            input_specification: 输入规格说明
            
        Returns:
            List[Dict[str, Any]]: 生成的测试用例列表
        """
        test_cases = []
        
        for field, spec in input_specification.items():
            field_type = spec.get('type', 'string')
            constraints = spec.get('constraints', {})
            
            # 有效等价类
            valid_cases = self._generate_valid_equivalence_cases(field, field_type, constraints)
            test_cases.extend(valid_cases)
            
            # 无效等价类
            invalid_cases = self._generate_invalid_equivalence_cases(field, field_type, constraints)
            test_cases.extend(invalid_cases)
        
        return test_cases
    
    async def apply_boundary_value_analysis(
        self, 
        input_specification: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        应用边界值分析法生成测试用例
        
        Args:
            input_specification: 输入规格说明
            
        Returns:
            List[Dict[str, Any]]: 生成的测试用例列表
        """
        test_cases = []
        
        for field, spec in input_specification.items():
            field_type = spec.get('type', 'string')
            constraints = spec.get('constraints', {})
            
            if field_type in ['integer', 'float', 'number']:
                # 数值边界值测试
                boundary_cases = self._generate_numeric_boundary_cases(field, constraints)
                test_cases.extend(boundary_cases)
            elif field_type == 'string':
                # 字符串长度边界值测试
                length_cases = self._generate_string_boundary_cases(field, constraints)
                test_cases.extend(length_cases)
            elif field_type == 'array':
                # 数组大小边界值测试
                array_cases = self._generate_array_boundary_cases(field, constraints)
                test_cases.extend(array_cases)
        
        return test_cases
    
    async def apply_scenario_testing(
        self, 
        business_scenarios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        应用场景法生成测试用例
        
        Args:
            business_scenarios: 业务场景列表
            
        Returns:
            List[Dict[str, Any]]: 生成的测试用例列表
        """
        test_cases = []
        
        for scenario in business_scenarios:
            scenario_name = scenario.get('name', '未命名场景')
            scenario_steps = scenario.get('steps', [])
            scenario_data = scenario.get('data', {})
            
            # 正常场景测试用例
            normal_case = {
                'case_title': f'{scenario_name} - 正常流程',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_steps': self._format_scenario_steps(scenario_steps),
                'test_data': scenario_data,
                'expected_result': scenario.get('expected_result', '场景执行成功')
            }
            test_cases.append(normal_case)
            
            # 异常场景测试用例
            if scenario.get('exceptions'):
                for exception in scenario['exceptions']:
                    exception_case = {
                        'case_title': f'{scenario_name} - {exception.get("name", "异常情况")}',
                        'case_type': 'FUNCTIONAL',
                        'priority': 'MEDIUM',
                        'test_steps': self._format_exception_steps(scenario_steps, exception),
                        'test_data': exception.get('data', scenario_data),
                        'expected_result': exception.get('expected_result', '异常处理正确')
                    }
                    test_cases.append(exception_case)
        
        return test_cases
    
    async def generate_decision_table_cases(
        self, 
        conditions: List[Dict[str, Any]], 
        actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        基于决策表生成测试用例
        
        Args:
            conditions: 条件列表
            actions: 动作列表
            
        Returns:
            List[Dict[str, Any]]: 生成的测试用例列表
        """
        test_cases = []
        
        # 生成所有可能的条件组合
        condition_combinations = self._generate_condition_combinations(conditions)
        
        for i, combination in enumerate(condition_combinations):
            # 确定对应的动作
            expected_actions = self._determine_actions(combination, conditions, actions)
            
            test_case = {
                'case_title': f'决策表测试用例 {i+1}',
                'case_type': 'FUNCTIONAL',
                'priority': 'MEDIUM',
                'preconditions': self._format_conditions(combination),
                'test_steps': self._format_decision_steps(combination, expected_actions),
                'expected_result': self._format_expected_actions(expected_actions)
            }
            test_cases.append(test_case)
        
        return test_cases

    async def evaluate_case_quality(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估测试用例质量
        
        Args:
            case_data: 用例数据
            
        Returns:
            Dict[str, Any]: 质量评估结果
        """
        quality_score = 0
        quality_issues = []
        suggestions = []
        
        # 1. 完整性检查
        completeness_score, completeness_issues = self._check_completeness(case_data)
        quality_score += completeness_score * 0.3
        quality_issues.extend(completeness_issues)
        
        # 2. 清晰性检查
        clarity_score, clarity_issues = self._check_clarity(case_data)
        quality_score += clarity_score * 0.25
        quality_issues.extend(clarity_issues)
        
        # 3. 可执行性检查
        executability_score, executability_issues = self._check_executability(case_data)
        quality_score += executability_score * 0.25
        quality_issues.extend(executability_issues)
        
        # 4. 可维护性检查
        maintainability_score, maintainability_issues = self._check_maintainability(case_data)
        quality_score += maintainability_score * 0.2
        quality_issues.extend(maintainability_issues)
        
        # 生成改进建议
        suggestions = self._generate_improvement_suggestions(quality_issues)
        
        return {
            'overall_score': round(quality_score, 2),
            'completeness_score': completeness_score,
            'clarity_score': clarity_score,
            'executability_score': executability_score,
            'maintainability_score': maintainability_score,
            'quality_issues': quality_issues,
            'suggestions': suggestions,
            'quality_level': self._determine_quality_level(quality_score)
        }
    
    async def get_design_best_practices(self, case_type: str) -> List[Dict[str, Any]]:
        """
        获取测试用例设计最佳实践
        
        Args:
            case_type: 用例类型
            
        Returns:
            List[Dict[str, Any]]: 最佳实践列表
        """
        best_practices = {
            'FUNCTIONAL': [
                {
                    'category': '用例设计',
                    'practice': '每个测试用例只验证一个功能点',
                    'description': '保持用例的单一职责，便于问题定位和维护'
                },
                {
                    'category': '步骤描述',
                    'practice': '使用清晰、具体的动作描述',
                    'description': '避免模糊的描述，确保任何人都能理解和执行'
                },
                {
                    'category': '数据准备',
                    'practice': '明确指定测试数据',
                    'description': '提供具体的测试数据，避免执行时的歧义'
                }
            ],
            'PERFORMANCE': [
                {
                    'category': '性能指标',
                    'practice': '明确定义性能基准',
                    'description': '设定具体的响应时间、吞吐量等指标阈值'
                },
                {
                    'category': '负载设计',
                    'practice': '模拟真实的用户负载',
                    'description': '基于实际业务场景设计负载模型'
                }
            ],
            'SECURITY': [
                {
                    'category': '威胁建模',
                    'practice': '基于威胁模型设计测试',
                    'description': '识别潜在的安全威胁，针对性设计测试用例'
                },
                {
                    'category': '边界测试',
                    'practice': '重点测试输入验证',
                    'description': '测试各种恶意输入和边界条件'
                }
            ]
        }
        
        return best_practices.get(case_type, [])
    
    # 私有辅助方法
    def _generate_valid_equivalence_cases(
        self, 
        field: str, 
        field_type: str, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成有效等价类测试用例"""
        cases = []
        
        if field_type == 'integer':
            min_val = constraints.get('min', 1)
            max_val = constraints.get('max', 100)
            valid_value = (min_val + max_val) // 2
            
            cases.append({
                'case_title': f'{field} - 有效等价类测试',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_data': {field: valid_value},
                'expected_result': '输入有效，处理成功'
            })
        
        elif field_type == 'string':
            min_len = constraints.get('min_length', 1)
            max_len = constraints.get('max_length', 50)
            valid_length = (min_len + max_len) // 2
            valid_value = 'a' * valid_length
            
            cases.append({
                'case_title': f'{field} - 有效等价类测试',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_data': {field: valid_value},
                'expected_result': '输入有效，处理成功'
            })
        
        return cases
    
    def _generate_invalid_equivalence_cases(
        self, 
        field: str, 
        field_type: str, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成无效等价类测试用例"""
        cases = []
        
        if field_type == 'integer':
            min_val = constraints.get('min', 1)
            max_val = constraints.get('max', 100)
            
            # 小于最小值
            cases.append({
                'case_title': f'{field} - 无效等价类测试（小于最小值）',
                'case_type': 'FUNCTIONAL',
                'priority': 'MEDIUM',
                'test_data': {field: min_val - 1},
                'expected_result': '输入无效，返回错误信息'
            })
            
            # 大于最大值
            cases.append({
                'case_title': f'{field} - 无效等价类测试（大于最大值）',
                'case_type': 'FUNCTIONAL',
                'priority': 'MEDIUM',
                'test_data': {field: max_val + 1},
                'expected_result': '输入无效，返回错误信息'
            })
        
        return cases

    def _generate_numeric_boundary_cases(
        self, 
        field: str, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成数值边界值测试用例"""
        cases = []
        min_val = constraints.get('min', 0)
        max_val = constraints.get('max', 100)
        
        boundary_values = [
            (min_val - 1, '最小值-1', '无效'),
            (min_val, '最小值', '有效'),
            (min_val + 1, '最小值+1', '有效'),
            (max_val - 1, '最大值-1', '有效'),
            (max_val, '最大值', '有效'),
            (max_val + 1, '最大值+1', '无效')
        ]
        
        for value, desc, validity in boundary_values:
            expected = '处理成功' if validity == '有效' else '返回错误信息'
            cases.append({
                'case_title': f'{field} - 边界值测试（{desc}）',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_data': {field: value},
                'expected_result': expected
            })
        
        return cases
    
    def _generate_string_boundary_cases(
        self, 
        field: str, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成字符串长度边界值测试用例"""
        cases = []
        min_len = constraints.get('min_length', 0)
        max_len = constraints.get('max_length', 50)
        
        boundary_lengths = [
            (min_len - 1, '最小长度-1', '无效'),
            (min_len, '最小长度', '有效'),
            (min_len + 1, '最小长度+1', '有效'),
            (max_len - 1, '最大长度-1', '有效'),
            (max_len, '最大长度', '有效'),
            (max_len + 1, '最大长度+1', '无效')
        ]
        
        for length, desc, validity in boundary_lengths:
            if length < 0:
                continue
            value = 'a' * length
            expected = '处理成功' if validity == '有效' else '返回错误信息'
            cases.append({
                'case_title': f'{field} - 字符串长度边界值测试（{desc}）',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_data': {field: value},
                'expected_result': expected
            })
        
        return cases
    
    def _generate_array_boundary_cases(
        self, 
        field: str, 
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成数组大小边界值测试用例"""
        cases = []
        min_size = constraints.get('min_size', 0)
        max_size = constraints.get('max_size', 10)
        
        boundary_sizes = [
            (min_size - 1, '最小大小-1', '无效'),
            (min_size, '最小大小', '有效'),
            (min_size + 1, '最小大小+1', '有效'),
            (max_size - 1, '最大大小-1', '有效'),
            (max_size, '最大大小', '有效'),
            (max_size + 1, '最大大小+1', '无效')
        ]
        
        for size, desc, validity in boundary_sizes:
            if size < 0:
                continue
            value = list(range(size))
            expected = '处理成功' if validity == '有效' else '返回错误信息'
            cases.append({
                'case_title': f'{field} - 数组大小边界值测试（{desc}）',
                'case_type': 'FUNCTIONAL',
                'priority': 'HIGH',
                'test_data': {field: value},
                'expected_result': expected
            })
        
        return cases
    
    def _format_scenario_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化场景步骤"""
        formatted_steps = []
        for i, step in enumerate(steps, 1):
            formatted_steps.append({
                'step': i,
                'action': step.get('action', ''),
                'expected': step.get('expected', '')
            })
        return formatted_steps
    
    def _format_exception_steps(
        self, 
        normal_steps: List[Dict[str, Any]], 
        exception: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """格式化异常场景步骤"""
        steps = self._format_scenario_steps(normal_steps)
        exception_step = exception.get('step', len(steps))
        
        # 在指定步骤插入异常操作
        if exception_step <= len(steps):
            steps[exception_step - 1]['action'] = exception.get('action', steps[exception_step - 1]['action'])
            steps[exception_step - 1]['expected'] = exception.get('expected', '异常处理')
        
        return steps

    def _generate_condition_combinations(self, conditions: List[Dict[str, Any]]) -> List[List[bool]]:
        """生成条件组合"""
        if not conditions:
            return []
        
        num_conditions = len(conditions)
        combinations = []
        
        # 生成所有可能的真假组合
        for i in range(2 ** num_conditions):
            combination = []
            for j in range(num_conditions):
                combination.append(bool(i & (1 << j)))
            combinations.append(combination)
        
        return combinations
    
    def _determine_actions(
        self, 
        combination: List[bool], 
        conditions: List[Dict[str, Any]], 
        actions: List[Dict[str, Any]]
    ) -> List[str]:
        """根据条件组合确定动作"""
        # 这里应该根据业务逻辑确定动作
        # 简化实现，返回默认动作
        return [action.get('name', '默认动作') for action in actions]
    
    def _format_conditions(self, combination: List[bool]) -> str:
        """格式化条件"""
        return f"条件组合: {combination}"
    
    def _format_decision_steps(
        self, 
        combination: List[bool], 
        actions: List[str]
    ) -> List[Dict[str, Any]]:
        """格式化决策步骤"""
        return [
            {'step': 1, 'action': f'设置条件: {combination}', 'expected': '条件设置成功'},
            {'step': 2, 'action': '执行业务逻辑', 'expected': f'执行动作: {", ".join(actions)}'}
        ]
    
    def _format_expected_actions(self, actions: List[str]) -> str:
        """格式化预期动作"""
        return f"系统执行以下动作: {', '.join(actions)}"
    
    def _check_completeness(self, case_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """检查完整性"""
        score = 100.0
        issues = []
        
        required_fields = ['case_title', 'test_steps', 'expected_result']
        for field in required_fields:
            if not case_data.get(field):
                score -= 20
                issues.append(f"缺少必填字段: {field}")
        
        # 检查测试步骤的完整性
        test_steps = case_data.get('test_steps', [])
        if isinstance(test_steps, list):
            for i, step in enumerate(test_steps):
                if not step.get('action'):
                    score -= 5
                    issues.append(f"第{i+1}步缺少操作描述")
                if not step.get('expected'):
                    score -= 5
                    issues.append(f"第{i+1}步缺少预期结果")
        
        return max(0, score), issues
    
    def _check_clarity(self, case_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """检查清晰性"""
        score = 100.0
        issues = []
        
        # 检查标题清晰性
        title = case_data.get('case_title', '')
        if len(title) < 10:
            score -= 15
            issues.append("用例标题过于简短，不够清晰")
        
        # 检查描述清晰性
        description = case_data.get('case_description', '')
        if not description:
            score -= 10
            issues.append("缺少用例描述")
        
        # 检查步骤描述的清晰性
        test_steps = case_data.get('test_steps', [])
        if isinstance(test_steps, list):
            for i, step in enumerate(test_steps):
                action = step.get('action', '')
                if len(action) < 5:
                    score -= 5
                    issues.append(f"第{i+1}步操作描述过于简短")
        
        return max(0, score), issues
    
    def _check_executability(self, case_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """检查可执行性"""
        score = 100.0
        issues = []
        
        # 检查前置条件
        preconditions = case_data.get('preconditions', '')
        if not preconditions:
            score -= 15
            issues.append("缺少前置条件说明")
        
        # 检查测试数据
        test_data = case_data.get('test_data')
        if not test_data:
            score -= 10
            issues.append("缺少测试数据")
        
        # 检查步骤的可执行性
        test_steps = case_data.get('test_steps', [])
        if isinstance(test_steps, list):
            for i, step in enumerate(test_steps):
                action = step.get('action', '')
                if '点击' in action or '输入' in action:
                    # 检查是否有具体的元素定位信息
                    if not any(keyword in action for keyword in ['按钮', '输入框', '链接', '菜单']):
                        score -= 5
                        issues.append(f"第{i+1}步缺少具体的操作对象")
        
        return max(0, score), issues
    
    def _check_maintainability(self, case_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """检查可维护性"""
        score = 100.0
        issues = []
        
        # 检查标签使用
        tags = case_data.get('tags', [])
        if not tags:
            score -= 10
            issues.append("建议添加标签以便分类管理")
        
        # 检查模块分类
        module = case_data.get('module', '')
        if not module:
            score -= 10
            issues.append("建议指定功能模块")
        
        # 检查优先级设置
        priority = case_data.get('priority', '')
        if not priority:
            score -= 5
            issues.append("建议设置用例优先级")
        
        return max(0, score), issues
    
    def _generate_improvement_suggestions(self, issues: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        for issue in issues:
            if "缺少必填字段" in issue:
                suggestions.append("请补充所有必填字段的内容")
            elif "缺少操作描述" in issue:
                suggestions.append("请为每个测试步骤添加详细的操作描述")
            elif "缺少预期结果" in issue:
                suggestions.append("请为每个测试步骤添加明确的预期结果")
            elif "标题过于简短" in issue:
                suggestions.append("建议用例标题更加详细，能够清楚表达测试目的")
            elif "缺少用例描述" in issue:
                suggestions.append("建议添加用例描述，说明测试的背景和目的")
            elif "缺少前置条件" in issue:
                suggestions.append("请添加前置条件，说明执行测试前需要满足的条件")
            elif "缺少测试数据" in issue:
                suggestions.append("请提供具体的测试数据，确保测试的可重复性")
        
        # 去重
        return list(set(suggestions))
    
    def _determine_quality_level(self, score: float) -> str:
        """确定质量等级"""
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
