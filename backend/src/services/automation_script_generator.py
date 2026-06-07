"""
自动化脚本生成服务

本模块实现基于手动测试用例生成自动化测试脚本的功能，包括：
- 基于手动用例生成自动化测试脚本
- 支持多种自动化框架（Playwright、Selenium等）
- 脚本预览、编辑和语法验证
- 脚本的保存和版本管理
- 脚本质量检查和优化建议
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from enum import Enum
import logging
import json
import re

from ..models.test_case import TestCase, AutomationScript
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..services.test_case_service import TestCaseService

logger = logging.getLogger(__name__)


class AutomationFramework(Enum):
    """自动化框架枚举"""
    PLAYWRIGHT = "PLAYWRIGHT"
    SELENIUM = "SELENIUM"
    CYPRESS = "CYPRESS"
    PYTEST = "PYTEST"
    JEST = "JEST"
    WEBDRIVER_IO = "WEBDRIVER_IO"


class ProgrammingLanguage(Enum):
    """编程语言枚举"""
    PYTHON = "PYTHON"
    JAVASCRIPT = "JAVASCRIPT"
    TYPESCRIPT = "TYPESCRIPT"
    JAVA = "JAVA"
    CSHARP = "CSHARP"


class BrowserType(Enum):
    """浏览器类型枚举"""
    CHROME = "CHROME"
    FIREFOX = "FIREFOX"
    SAFARI = "SAFARI"
    EDGE = "EDGE"


class AutomationConfig:
    """自动化配置类"""
    
    def __init__(self):
        self.framework = AutomationFramework.PLAYWRIGHT
        self.language = ProgrammingLanguage.PYTHON
        self.browser = BrowserType.CHROME
        self.use_page_object_model = True
        self.include_error_handling = True
        self.include_screenshots = True
        self.include_logging = True
        self.wait_strategy = "explicit"  # explicit, implicit, fixed
        self.assertion_style = "expect"  # expect, assert
        self.test_data_source = "inline"  # inline, file, database
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'framework': self.framework.value,
            'language': self.language.value,
            'browser': self.browser.value,
            'use_page_object_model': self.use_page_object_model,
            'include_error_handling': self.include_error_handling,
            'include_screenshots': self.include_screenshots,
            'include_logging': self.include_logging,
            'wait_strategy': self.wait_strategy,
            'assertion_style': self.assertion_style,
            'test_data_source': self.test_data_source
        }


class AutomationScriptGenerator:
    """自动化脚本生成器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.test_case_service = TestCaseService(db)
        self._init_templates()
    
    def _init_templates(self):
        """初始化脚本模板"""
        self.templates = {
            (AutomationFramework.PLAYWRIGHT, ProgrammingLanguage.PYTHON): {
                'name': 'Playwright Python 模板',
                'template': '''
import pytest
from playwright.sync_api import Page, expect
import logging

logger = logging.getLogger(__name__)

class {class_name}:
    """
    {test_description}
    """
    
    def __init__(self, page: Page):
        self.page = page
        {page_elements}
    
    def test_{test_method_name}(self):
        """
        测试用例: {case_title}
        描述: {case_description}
        """
        try:
            logger.info("开始执行测试: {case_title}")
            
            # 前置条件
            {preconditions}
            
            # 测试步骤
            {test_steps}
            
            # 验证结果
            {assertions}
            
            logger.info("测试执行成功: {case_title}")
            
        except Exception as e:
            logger.error(f"测试执行失败: {case_title}, 错误: {{str(e)}}")
            {error_handling}
            raise

{helper_methods}
                ''',
                'imports': [
                    'import pytest',
                    'from playwright.sync_api import Page, expect',
                    'import logging'
                ]
            },
            (AutomationFramework.SELENIUM, ProgrammingLanguage.PYTHON): {
                'name': 'Selenium Python 模板',
                'template': '''
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

logger = logging.getLogger(__name__)

class {class_name}(unittest.TestCase):
    """
    {test_description}
    """
    
    def setUp(self):
        self.driver = webdriver.{browser}()
        self.wait = WebDriverWait(self.driver, 10)
        {page_elements}
    
    def tearDown(self):
        if self.driver:
            self.driver.quit()
    
    def test_{test_method_name}(self):
        """
        测试用例: {case_title}
        描述: {case_description}
        """
        try:
            logger.info("开始执行测试: {case_title}")
            
            # 前置条件
            {preconditions}
            
            # 测试步骤
            {test_steps}
            
            # 验证结果
            {assertions}
            
            logger.info("测试执行成功: {case_title}")
            
        except Exception as e:
            logger.error(f"测试执行失败: {case_title}, 错误: {{str(e)}}")
            {error_handling}
            raise

{helper_methods}

if __name__ == '__main__':
    unittest.main()
                ''',
                'imports': [
                    'import unittest',
                    'from selenium import webdriver',
                    'from selenium.webdriver.common.by import By',
                    'from selenium.webdriver.support.ui import WebDriverWait',
                    'from selenium.webdriver.support import expected_conditions as EC',
                    'import logging'
                ]
            }
        }
    
    async def generate_automation_script(
        self, 
        test_case_id: int, 
        config: AutomationConfig,
        user_id: int
    ) -> Dict[str, Any]:
        """
        基于测试用例生成自动化脚本
        
        Args:
            test_case_id: 测试用例ID
            config: 自动化配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 1. 获取测试用例
            test_case = await self.test_case_service.get_test_case_by_id(test_case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")
            
            # 2. 验证用例是否适合自动化
            self._validate_automation_suitability(test_case)
            
            # 3. 构建AI生成提示
            prompt = self._build_script_generation_prompt(test_case, config)
            
            # 4. 调用AI生成服务
            ai_response = await self.ai_service.generate_content(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.3
            )
            
            # 5. 解析生成结果
            script_data = self._parse_script_response(ai_response, test_case, config)
            
            # 6. 应用模板和格式化
            formatted_script = self._apply_template_formatting(script_data, config)
            
            # 7. 语法验证
            validation_result = await self._validate_script_syntax(formatted_script, config)
            
            # 8. 构建返回结果
            result = {
                'test_case_id': test_case_id,
                'test_case_title': test_case.case_title,
                'automation_config': config.to_dict(),
                'generated_script': formatted_script,
                'script_metadata': {
                    'framework': config.framework.value,
                    'language': config.language.value,
                    'browser': config.browser.value,
                    'estimated_execution_time': self._estimate_execution_time(test_case),
                    'complexity_score': self._calculate_complexity_score(test_case)
                },
                'validation_result': validation_result,
                'generation_time': datetime.utcnow().isoformat(),
                'dependencies': self._get_required_dependencies(config)
            }
            
            logger.info(f"自动化脚本生成成功: 用例{test_case_id}, 框架{config.framework.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"生成自动化脚本失败: {str(e)}")
            raise
    
    async def batch_generate_scripts(
        self, 
        test_case_ids: List[int], 
        config: AutomationConfig,
        user_id: int
    ) -> Dict[str, Any]:
        """
        批量生成自动化脚本
        
        Args:
            test_case_ids: 测试用例ID列表
            config: 自动化配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 批量生成结果
        """
        try:
            results = {
                'successful': [],
                'failed': [],
                'total_cases': len(test_case_ids),
                'generation_time': datetime.utcnow().isoformat()
            }
            
            for case_id in test_case_ids:
                try:
                    script_result = await self.generate_automation_script(case_id, config, user_id)
                    results['successful'].append(script_result)
                except Exception as e:
                    results['failed'].append({
                        'test_case_id': case_id,
                        'error': str(e)
                    })
                    logger.warning(f"批量生成脚本失败: 用例{case_id}, 错误: {str(e)}")
            
            logger.info(f"批量生成脚本完成: {len(results['successful'])}/{len(test_case_ids)} 成功")
            
            return results
            
        except Exception as e:
            logger.error(f"批量生成脚本失败: {str(e)}")
            raise
    
    async def save_automation_script(
        self, 
        test_case_id: int, 
        script_data: Dict[str, Any],
        user_id: int
    ) -> AutomationScript:
        """
        保存自动化脚本
        
        Args:
            test_case_id: 测试用例ID
            script_data: 脚本数据
            user_id: 用户ID
            
        Returns:
            AutomationScript: 保存的脚本对象
        """
        try:
            # 1. 验证脚本数据
            self._validate_script_data(script_data)
            
            # 2. 检查是否已存在脚本
            existing_script = self.db.query(AutomationScript)\
                .filter(AutomationScript.test_case_id == test_case_id)\
                .filter(AutomationScript.framework == script_data['framework'])\
                .first()
            
            if existing_script:
                # 更新现有脚本
                existing_script.script_content = script_data['script_content']
                existing_script.script_path = script_data.get('script_path')
                existing_script.dependencies = script_data.get('dependencies', [])
                existing_script.environment_config = script_data.get('environment_config', {})
                existing_script.updated_by = user_id
                existing_script.updated_at = datetime.utcnow()
                
                self.db.commit()
                return existing_script
            else:
                # 创建新脚本
                automation_script = AutomationScript(
                    test_case_id=test_case_id,
                    script_name=script_data.get('script_name', f'自动化脚本_{test_case_id}'),
                    framework=script_data['framework'],
                    language=script_data['language'],
                    script_content=script_data['script_content'],
                    script_path=script_data.get('script_path'),
                    browser=script_data.get('browser'),
                    environment_config=script_data.get('environment_config', {}),
                    dependencies=script_data.get('dependencies', []),
                    created_by=user_id
                )
                
                self.db.add(automation_script)
                self.db.commit()
                
                logger.info(f"自动化脚本保存成功: 用例{test_case_id}")
                
                return automation_script
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存自动化脚本失败: {str(e)}")
            raise
    
    async def preview_script(
        self, 
        script_content: str, 
        config: AutomationConfig
    ) -> Dict[str, Any]:
        """
        预览脚本内容
        
        Args:
            script_content: 脚本内容
            config: 自动化配置
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        try:
            # 1. 语法验证
            validation_result = await self._validate_script_syntax(script_content, config)
            
            # 2. 复杂度分析
            complexity_analysis = self._analyze_script_complexity(script_content)
            
            # 3. 依赖分析
            dependencies = self._analyze_script_dependencies(script_content, config)
            
            # 4. 代码质量检查
            quality_check = self._check_code_quality(script_content, config)
            
            return {
                'script_content': script_content,
                'validation_result': validation_result,
                'complexity_analysis': complexity_analysis,
                'dependencies': dependencies,
                'quality_check': quality_check,
                'estimated_execution_time': complexity_analysis.get('estimated_time', 0),
                'maintainability_score': quality_check.get('maintainability_score', 0)
            }
            
        except Exception as e:
            logger.error(f"脚本预览失败: {str(e)}")
            raise
    
    async def optimize_script(
        self, 
        script_content: str, 
        config: AutomationConfig,
        optimization_goals: List[str] = None
    ) -> Dict[str, Any]:
        """
        优化脚本
        
        Args:
            script_content: 脚本内容
            config: 自动化配置
            optimization_goals: 优化目标 (performance, maintainability, reliability)
            
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            if not optimization_goals:
                optimization_goals = ['performance', 'maintainability']
            
            # 构建优化提示
            optimization_prompt = self._build_optimization_prompt(
                script_content, config, optimization_goals
            )
            
            # 调用AI优化服务
            ai_response = await self.ai_service.generate_content(
                prompt=optimization_prompt,
                max_tokens=3000,
                temperature=0.2
            )
            
            # 解析优化结果
            optimized_script = self._parse_optimization_response(ai_response, script_content)
            
            # 对比分析
            comparison = self._compare_scripts(script_content, optimized_script, config)
            
            return {
                'original_script': script_content,
                'optimized_script': optimized_script,
                'optimization_goals': optimization_goals,
                'improvements': comparison['improvements'],
                'performance_gain': comparison.get('performance_gain', 0),
                'maintainability_improvement': comparison.get('maintainability_improvement', 0)
            }
            
        except Exception as e:
            logger.error(f"脚本优化失败: {str(e)}")
            return {
                'original_script': script_content,
                'optimized_script': script_content,
                'optimization_goals': optimization_goals,
                'improvements': [],
                'error': str(e)
            }
    
    async def get_script_templates(self, framework: AutomationFramework, language: ProgrammingLanguage) -> Dict[str, Any]:
        """
        获取脚本模板
        
        Args:
            framework: 自动化框架
            language: 编程语言
            
        Returns:
            Dict[str, Any]: 模板信息
        """
        template_key = (framework, language)
        template = self.templates.get(template_key)
        
        if not template:
            return {
                'available': False,
                'message': f'暂不支持 {framework.value} + {language.value} 组合'
            }
        
        return {
            'available': True,
            'template_name': template['name'],
            'template_content': template['template'],
            'required_imports': template['imports'],
            'supported_features': self._get_supported_features(framework, language)
        }
    
    # 私有方法
    def _validate_automation_suitability(self, test_case: TestCase) -> None:
        """验证用例是否适合自动化"""
        if not test_case.test_steps:
            raise ValidationError("测试用例缺少测试步骤，无法生成自动化脚本")
        
        # 检查是否包含UI操作
        has_ui_operations = False
        for step in test_case.test_steps:
            action = step.get('action', '').lower()
            if any(keyword in action for keyword in ['点击', '输入', '选择', '滚动', 'click', 'input', 'select']):
                has_ui_operations = True
                break
        
        if not has_ui_operations:
            logger.warning(f"测试用例 {test_case.case_code} 可能不适合UI自动化")
    
    def _build_script_generation_prompt(self, test_case: TestCase, config: AutomationConfig) -> str:
        """构建脚本生成提示"""
        prompt = f"""
基于以下手动测试用例，生成{config.framework.value}自动化测试脚本（{config.language.value}语言）：

测试用例信息：
- 用例标题：{test_case.case_title}
- 用例描述：{test_case.case_description or ''}
- 前置条件：{test_case.preconditions or ''}
- 测试步骤：{json.dumps(test_case.test_steps, ensure_ascii=False)}
- 预期结果：{test_case.expected_result or ''}
- 测试数据：{json.dumps(test_case.test_data, ensure_ascii=False) if test_case.test_data else '{}'}

技术要求：
- 框架：{config.framework.value}
- 语言：{config.language.value}
- 浏览器：{config.browser.value}
- 使用页面对象模式：{config.use_page_object_model}
- 包含错误处理：{config.include_error_handling}
- 包含截图：{config.include_screenshots}
- 等待策略：{config.wait_strategy}

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
        
        return prompt
    
    def _parse_script_response(self, ai_response: str, test_case: TestCase, config: AutomationConfig) -> Dict[str, Any]:
        """解析脚本响应"""
        try:
            if ai_response.strip().startswith('{'):
                return json.loads(ai_response)
            else:
                # 如果不是JSON格式，尝试提取代码
                return self._extract_script_from_text(ai_response, test_case, config)
        except json.JSONDecodeError:
            return self._extract_script_from_text(ai_response, test_case, config)
    
    def _extract_script_from_text(self, text: str, test_case: TestCase, config: AutomationConfig) -> Dict[str, Any]:
        """从文本中提取脚本"""
        # 使用正则表达式提取代码块
        code_pattern = r'```(?:python|javascript|java)?\n(.*?)\n```'
        code_matches = re.findall(code_pattern, text, re.DOTALL)
        
        script_content = code_matches[0] if code_matches else self._generate_basic_script(test_case, config)
        
        return {
            'script_content': script_content,
            'page_elements': {},
            'test_methods': [f'test_{test_case.case_code.lower().replace("-", "_")}'],
            'dependencies': self._get_required_dependencies(config),
            'setup_instructions': '请安装所需依赖包'
        }
    
    def _apply_template_formatting(self, script_data: Dict[str, Any], config: AutomationConfig) -> str:
        """应用模板格式化"""
        template_key = (config.framework, config.language)
        template = self.templates.get(template_key)
        
        if not template:
            return script_data.get('script_content', '')
        
        # 提取脚本组件
        script_content = script_data.get('script_content', '')
        page_elements = script_data.get('page_elements', {})
        
        # 格式化参数
        format_params = {
            'class_name': 'TestAutomation',
            'test_description': '自动化测试脚本',
            'test_method_name': 'automation_test',
            'case_title': '自动化测试',
            'case_description': '基于手动用例生成的自动化测试',
            'browser': config.browser.value.lower(),
            'page_elements': self._format_page_elements(page_elements, config),
            'preconditions': '# 前置条件设置',
            'test_steps': '# 测试步骤执行',
            'assertions': '# 结果验证',
            'error_handling': '# 错误处理',
            'helper_methods': '# 辅助方法'
        }
        
        try:
            return template['template'].format(**format_params)
        except KeyError as e:
            logger.warning(f"模板格式化失败: {str(e)}")
            return script_content
    
    def _format_page_elements(self, elements: Dict[str, str], config: AutomationConfig) -> str:
        """格式化页面元素"""
        if not elements:
            return '# 页面元素定位'
        
        if config.framework == AutomationFramework.PLAYWRIGHT:
            return '\n'.join([
                f'        self.{name} = "{locator}"'
                for name, locator in elements.items()
            ])
        elif config.framework == AutomationFramework.SELENIUM:
            return '\n'.join([
                f'        self.{name} = (By.CSS_SELECTOR, "{locator}")'
                for name, locator in elements.items()
            ])
        
        return '# 页面元素定位'
    
    async def _validate_script_syntax(self, script_content: str, config: AutomationConfig) -> Dict[str, Any]:
        """验证脚本语法"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        try:
            if config.language == ProgrammingLanguage.PYTHON:
                # Python语法检查
                import ast
                ast.parse(script_content)
                
                # 检查常见问题
                if 'import' not in script_content:
                    validation_result['warnings'].append('脚本缺少必要的导入语句')
                
                if 'def test_' not in script_content:
                    validation_result['warnings'].append('脚本缺少测试方法')
                
            elif config.language == ProgrammingLanguage.JAVASCRIPT:
                # JavaScript基本检查
                if 'function' not in script_content and 'const' not in script_content:
                    validation_result['warnings'].append('脚本可能缺少函数定义')
            
            # 框架特定检查
            if config.framework == AutomationFramework.PLAYWRIGHT:
                if 'playwright' not in script_content.lower():
                    validation_result['warnings'].append('脚本可能缺少Playwright相关导入')
            
            elif config.framework == AutomationFramework.SELENIUM:
                if 'selenium' not in script_content.lower():
                    validation_result['warnings'].append('脚本可能缺少Selenium相关导入')
            
        except SyntaxError as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'语法错误: {str(e)}')
        except Exception as e:
            validation_result['warnings'].append(f'验证警告: {str(e)}')
        
        return validation_result
    
    def _analyze_script_complexity(self, script_content: str) -> Dict[str, Any]:
        """分析脚本复杂度"""
        lines = script_content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # 基本指标
        total_lines = len(lines)
        code_lines = len(non_empty_lines)
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        
        # 复杂度指标
        function_count = len(re.findall(r'def\s+\w+', script_content))
        class_count = len(re.findall(r'class\s+\w+', script_content))
        loop_count = len(re.findall(r'\b(for|while)\b', script_content))
        condition_count = len(re.findall(r'\b(if|elif)\b', script_content))
        
        # 计算复杂度分数
        complexity_score = (
            function_count * 2 +
            class_count * 3 +
            loop_count * 2 +
            condition_count * 1.5
        )
        
        # 估算执行时间（秒）
        estimated_time = max(10, code_lines * 0.5 + loop_count * 2)
        
        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'function_count': function_count,
            'class_count': class_count,
            'loop_count': loop_count,
            'condition_count': condition_count,
            'complexity_score': complexity_score,
            'complexity_level': self._get_complexity_level(complexity_score),
            'estimated_time': estimated_time
        }
    
    def _get_complexity_level(self, score: float) -> str:
        """获取复杂度等级"""
        if score < 10:
            return '简单'
        elif score < 25:
            return '中等'
        elif score < 50:
            return '复杂'
        else:
            return '非常复杂'
    
    def _analyze_script_dependencies(self, script_content: str, config: AutomationConfig) -> List[str]:
        """分析脚本依赖"""
        dependencies = set()
        
        # 基础依赖
        base_deps = self._get_required_dependencies(config)
        dependencies.update(base_deps)
        
        # 从导入语句中提取依赖
        import_pattern = r'(?:from\s+(\w+)|import\s+(\w+))'
        imports = re.findall(import_pattern, script_content)
        
        for from_import, direct_import in imports:
            if from_import:
                dependencies.add(from_import)
            if direct_import:
                dependencies.add(direct_import)
        
        # 过滤标准库
        standard_libs = {'os', 'sys', 'json', 'time', 'datetime', 'logging', 're', 'unittest'}
        dependencies = dependencies - standard_libs
        
        return list(dependencies)
    
    def _check_code_quality(self, script_content: str, config: AutomationConfig) -> Dict[str, Any]:
        """检查代码质量"""
        quality_issues = []
        suggestions = []
        
        lines = script_content.split('\n')
        
        # 检查代码风格
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                quality_issues.append(f'第{i}行过长（超过120字符）')
            
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                if 'def ' in line or 'class ' in line:
                    continue
                if i > 1 and lines[i-2].strip().endswith(':'):
                    quality_issues.append(f'第{i}行缩进不正确')
        
        # 检查最佳实践
        if 'sleep(' in script_content:
            suggestions.append('建议使用显式等待替代固定等待（sleep）')
        
        if 'find_element(' in script_content and 'WebDriverWait' not in script_content:
            suggestions.append('建议使用WebDriverWait进行元素等待')
        
        if 'assert' in script_content and config.framework == AutomationFramework.PLAYWRIGHT:
            suggestions.append('建议使用expect()替代assert进行断言')
        
        # 计算可维护性分数
        comment_ratio = len([l for l in lines if l.strip().startswith('#')]) / max(1, len(lines))
        function_ratio = script_content.count('def ') / max(1, len(lines)) * 100
        
        maintainability_score = min(100, (comment_ratio * 30 + function_ratio * 20 + 50))
        
        return {
            'quality_issues': quality_issues,
            'suggestions': suggestions,
            'maintainability_score': round(maintainability_score, 2),
            'comment_ratio': round(comment_ratio * 100, 2),
            'function_density': round(function_ratio, 2)
        }
    
    def _get_required_dependencies(self, config: AutomationConfig) -> List[str]:
        """获取必需依赖"""
        dependencies = []
        
        if config.framework == AutomationFramework.PLAYWRIGHT:
            if config.language == ProgrammingLanguage.PYTHON:
                dependencies.extend(['playwright', 'pytest'])
            elif config.language == ProgrammingLanguage.JAVASCRIPT:
                dependencies.extend(['@playwright/test'])
        
        elif config.framework == AutomationFramework.SELENIUM:
            if config.language == ProgrammingLanguage.PYTHON:
                dependencies.extend(['selenium', 'pytest'])
            elif config.language == ProgrammingLanguage.JAVA:
                dependencies.extend(['selenium-java', 'junit'])
        
        elif config.framework == AutomationFramework.CYPRESS:
            dependencies.extend(['cypress'])
        
        # 通用依赖
        if config.include_logging:
            if config.language == ProgrammingLanguage.PYTHON:
                dependencies.append('logging')
        
        return dependencies
    
    def _get_supported_features(self, framework: AutomationFramework, language: ProgrammingLanguage) -> List[str]:
        """获取支持的特性"""
        features = ['基础UI操作', '元素定位', '断言验证']
        
        if framework == AutomationFramework.PLAYWRIGHT:
            features.extend([
                '多浏览器支持',
                '移动端测试',
                '网络拦截',
                '截图和录屏',
                '自动等待'
            ])
        
        elif framework == AutomationFramework.SELENIUM:
            features.extend([
                '跨浏览器测试',
                '远程执行',
                '并行测试',
                '页面对象模式'
            ])
        
        return features
    
    def _estimate_execution_time(self, test_case: TestCase) -> int:
        """估算执行时间（秒）"""
        base_time = 10  # 基础时间
        
        if test_case.test_steps:
            step_time = len(test_case.test_steps) * 3  # 每步3秒
            base_time += step_time
        
        # 根据复杂度调整
        if test_case.complexity == 'COMPLEX':
            base_time *= 1.5
        elif test_case.complexity == 'SIMPLE':
            base_time *= 0.8
        
        return int(base_time)
    
    def _calculate_complexity_score(self, test_case: TestCase) -> float:
        """计算复杂度分数"""
        score = 1.0
        
        if test_case.test_steps:
            score += len(test_case.test_steps) * 0.2
        
        if test_case.test_data:
            score += len(test_case.test_data) * 0.1
        
        complexity_multiplier = {
            'SIMPLE': 0.8,
            'MEDIUM': 1.0,
            'COMPLEX': 1.5
        }
        
        score *= complexity_multiplier.get(test_case.complexity, 1.0)
        
        return round(score, 2)
    
    def _generate_basic_script(self, test_case: TestCase, config: AutomationConfig) -> str:
        """生成基础脚本"""
        if config.framework == AutomationFramework.PLAYWRIGHT and config.language == ProgrammingLanguage.PYTHON:
            return f'''
import pytest
from playwright.sync_api import Page, expect

def test_{test_case.case_code.lower().replace("-", "_")}(page: Page):
    """
    测试用例: {test_case.case_title}
    """
    # 前置条件
    # TODO: 添加前置条件设置
    
    # 测试步骤
    # TODO: 实现测试步骤
    
    # 验证结果
    # TODO: 添加断言验证
    
    pass
            '''
        
        return f'# 自动化测试脚本 - {test_case.case_title}\n# TODO: 实现测试逻辑'
    
    def _validate_script_data(self, script_data: Dict[str, Any]) -> None:
        """验证脚本数据"""
        required_fields = ['framework', 'language', 'script_content']
        for field in required_fields:
            if not script_data.get(field):
                raise ValidationError(f"脚本数据缺少必填字段: {field}")
    
    def _build_optimization_prompt(
        self, 
        script_content: str, 
        config: AutomationConfig, 
        goals: List[str]
    ) -> str:
        """构建优化提示"""
        return f"""
请优化以下{config.framework.value}自动化测试脚本，优化目标：{', '.join(goals)}

当前脚本：
```{config.language.value.lower()}
{script_content}
```

优化要求：
1. 提高脚本性能和执行效率
2. 增强代码可维护性和可读性
3. 添加适当的错误处理和日志
4. 优化元素定位策略
5. 改进等待策略

请返回优化后的完整脚本代码。
        """
    
    def _parse_optimization_response(self, ai_response: str, original_script: str) -> str:
        """解析优化响应"""
        # 提取代码块
        code_pattern = r'```(?:python|javascript|java)?\n(.*?)\n```'
        code_matches = re.findall(code_pattern, ai_response, re.DOTALL)
        
        if code_matches:
            return code_matches[0].strip()
        
        # 如果没有代码块，返回原始脚本
        return original_script
    
    def _compare_scripts(
        self, 
        original: str, 
        optimized: str, 
        config: AutomationConfig
    ) -> Dict[str, Any]:
        """对比脚本"""
        original_analysis = self._analyze_script_complexity(original)
        optimized_analysis = self._analyze_script_complexity(optimized)
        
        improvements = []
        
        # 性能改进
        time_diff = original_analysis['estimated_time'] - optimized_analysis['estimated_time']
        if time_diff > 0:
            improvements.append(f'预计执行时间减少 {time_diff} 秒')
        
        # 复杂度改进
        complexity_diff = original_analysis['complexity_score'] - optimized_analysis['complexity_score']
        if complexity_diff > 0:
            improvements.append(f'复杂度降低 {complexity_diff:.1f} 分')
        
        # 代码质量改进
        original_quality = self._check_code_quality(original, config)
        optimized_quality = self._check_code_quality(optimized, config)
        
        quality_diff = optimized_quality['maintainability_score'] - original_quality['maintainability_score']
        if quality_diff > 0:
            improvements.append(f'可维护性提升 {quality_diff:.1f} 分')
        
        return {
            'improvements': improvements,
            'performance_gain': max(0, time_diff),
            'maintainability_improvement': max(0, quality_diff)
        }