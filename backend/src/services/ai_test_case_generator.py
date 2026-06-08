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
import asyncio
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
        self.generation_timeout_seconds = 170
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
        self.templates.setdefault(GenerationTemplate.INTEGRATION_TESTING, self.templates[GenerationTemplate.API_TESTING])
        self.templates.setdefault(GenerationTemplate.FUNCTIONAL_ADVANCED, self.templates[GenerationTemplate.FUNCTIONAL_BASIC])
    
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
                logger.warning("Invalid generation template %s, falling back to functional basic", config.template)
                config.template = GenerationTemplate.FUNCTIONAL_BASIC
                template_info = self.templates[GenerationTemplate.FUNCTIONAL_BASIC]
            
            # 3. 构建AI提示
            prompt = self._build_generation_prompt(requirement, config, template_info)
            
            # 4. 调用AI生成服务
            ai_response = await self._generate_ai_content(
                prompt=prompt,
                max_tokens=self._max_tokens_for_config(config),
                temperature=0.7
            )
            
            # 5. 解析生成结果
            generated_cases = self._parse_ai_response(ai_response, config)
            
            # 6. 质量检查和优化
            validated_cases = await self._validate_and_optimize_cases(generated_cases, requirement, config)
            
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
                logger.warning("Invalid generation template %s, falling back to functional basic", config.template)
                config.template = GenerationTemplate.FUNCTIONAL_BASIC
                template_info = self.templates[GenerationTemplate.FUNCTIONAL_BASIC]
            
            # 3. 构建AI提示
            prompt = self._build_generation_prompt(temp_requirement, config, template_info)
            
            # 4. 调用AI生成服务
            ai_response = await self._generate_ai_content(
                prompt=prompt,
                max_tokens=self._max_tokens_for_config(config),
                temperature=0.7
            )
            
            # 5. 解析生成结果
            generated_cases = self._parse_ai_response(ai_response, config)
            
            # 6. 质量检查和优化
            validated_cases = await self._validate_and_optimize_cases(generated_cases, temp_requirement, config)
            
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
    async def _generate_ai_content(self, prompt: str, max_tokens: int, temperature: float) -> str:
        try:
            return await asyncio.wait_for(
                self.ai_service.generate_content(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                timeout=self.generation_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise BusinessLogicError("AI生成测试用例超时，请稍后重试或选择内容更少的需求") from exc

    def _max_tokens_for_config(self, config: GenerationConfig) -> int:
        return max(1800, min(5000, 700 + config.max_cases * 650))

    def _limit_prompt_text(self, value: Any, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip()

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
            requirement_description=self._limit_prompt_text(getattr(requirement, 'description', ''), 1800),
            acceptance_criteria=self._limit_prompt_text(getattr(requirement, 'acceptance_criteria', ''), 1200),
            max_cases=config.max_cases,
            priority=config.priority.value,
            language=config.language,
            detail_level=config.detail_level
        )
    
    def _parse_ai_response(self, ai_response: str, config: GenerationConfig) -> List[Dict[str, Any]]:
        """解析AI响应"""
        try:
            response_text = str(ai_response or "").strip()
            for value in self._iter_json_values(response_text):
                cases = self._normalize_cases_payload(value, config)
                if cases:
                    return cases[:config.max_cases]

            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\s*", "", response_text, flags=re.IGNORECASE)
                response_text = re.sub(r"\s*```$", "", response_text).strip()

            json_start = response_text.find("{")
            json_end = response_text.rfind("}")
            if json_start >= 0 and json_end > json_start:
                response_data = json.loads(response_text[json_start:json_end + 1])
                cases = self._normalize_cases_payload(response_data, config)
                if cases:
                    return cases[:config.max_cases]

            array_start = response_text.find("[")
            array_end = response_text.rfind("]")
            if array_start >= 0 and array_end > array_start:
                response_data = json.loads(response_text[array_start:array_end + 1])
                cases = self._normalize_cases_payload(response_data, config)
                if cases:
                    return cases[:config.max_cases]
            
            # 如果不是JSON格式，尝试提取结构化信息
            return self._extract_cases_from_text(response_text, config)
            
        except json.JSONDecodeError:
            logger.warning("AI响应不是有效的JSON格式，尝试文本解析")
            return self._extract_cases_from_text(ai_response, config)

    def _iter_json_values(self, text: str) -> List[Any]:
        decoder = json.JSONDecoder()
        fragments = [
            match.group(1).strip()
            for match in re.finditer(r"```(?:json)?\s*(.*?)```", str(text or ""), flags=re.IGNORECASE | re.DOTALL)
        ]
        fragments.append(str(text or ""))

        values = []
        seen = set()
        for fragment in fragments:
            for match in re.finditer(r"[\[{]", fragment):
                candidate = fragment[match.start():].lstrip()
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                try:
                    value, _ = decoder.raw_decode(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, (dict, list)):
                    values.append(value)
        return values

    def _normalize_cases_payload(self, payload: Any, config: GenerationConfig) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            raw_cases = payload
        elif isinstance(payload, dict):
            raw_cases = (
                payload.get("test_cases")
                or payload.get("testCases")
                or payload.get("cases")
                or payload.get("data")
                or payload.get("items")
            )
            if raw_cases is None and self._looks_like_case(payload):
                raw_cases = [payload]
            elif isinstance(raw_cases, dict):
                raw_cases = raw_cases.get("test_cases") or raw_cases.get("cases") or raw_cases.get("items") or [raw_cases]
        else:
            raw_cases = []

        normalized_cases = []
        for raw_case in raw_cases or []:
            if not isinstance(raw_case, dict):
                continue
            case = self._normalize_generated_case(raw_case, config)
            if case:
                normalized_cases.append(case)
        return normalized_cases

    def _looks_like_case(self, value: Dict[str, Any]) -> bool:
        keys = {
            "case_title", "title", "name", "case_description", "description",
            "test_steps", "steps", "expected_result", "expected"
        }
        return any(key in value for key in keys)

    def _normalize_generated_case(self, raw_case: Dict[str, Any], config: GenerationConfig) -> Optional[Dict[str, Any]]:
        title = self._first_text(
            raw_case,
            "case_title", "title", "name", "test_case_title", "用例标题", "测试用例标题"
        )
        if not self._is_usable_title(title):
            return None

        test_steps = self._normalize_test_steps(
            raw_case.get("test_steps")
            or raw_case.get("steps")
            or raw_case.get("actions")
            or raw_case.get("测试步骤")
        )
        if not test_steps:
            api_method = self._first_text(raw_case, "api_method", "method", "request_method")
            api_url = self._first_text(raw_case, "api_url", "url", "endpoint", "request_url")
            if api_method or api_url:
                test_steps = [
                    {
                        "step": 1,
                        "action": "准备测试数据、请求头和鉴权信息",
                        "expected": "测试数据满足当前用例场景，必要的请求头和鉴权信息已准备完成",
                    },
                    {
                        "step": 2,
                        "action": f"发送 {api_method or 'HTTP'} 请求到 {api_url or '目标接口'}",
                        "expected": "接口请求成功发出并收到响应",
                    },
                    {
                        "step": 3,
                        "action": "校验响应状态、响应内容和相关业务数据",
                        "expected": self._format_expected_response(raw_case),
                    },
                ]

        return {
            "case_title": title[:200],
            "case_description": self._first_text(raw_case, "case_description", "description", "summary", "用例描述") or title,
            "case_type": raw_case.get("case_type") or config.case_type.value,
            "priority": raw_case.get("priority") or config.priority.value,
            "complexity": raw_case.get("complexity") or "MEDIUM",
            "automation_level": raw_case.get("automation_level") or "MANUAL",
            "preconditions": self._first_text(raw_case, "preconditions", "precondition", "前置条件") or "系统正常运行",
            "test_steps": test_steps,
            "expected_result": self._first_text(raw_case, "expected_result", "expected", "expected_response", "预期结果") or self._steps_expected_summary(test_steps),
            "test_data": raw_case.get("test_data") or raw_case.get("data") or raw_case.get("request_body") or {},
            "test_type": raw_case.get("test_type") or raw_case.get("scenario_type") or "positive",
            "tags": raw_case.get("tags") or [],
            "module": raw_case.get("module"),
        }

    def _first_text(self, data: Dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            text = str(value).strip()
            if text:
                return text
        return ""

    def _is_usable_title(self, title: str) -> bool:
        title = str(title or "").strip()
        if len(title) < 2:
            return False
        if title.lower() in {"{", "}", "[", "]", "```", "```json", "json", "test_cases"}:
            return False
        return bool(re.search(r"[\w\u4e00-\u9fff]", title))

    def _normalize_test_steps(self, steps: Any) -> List[Dict[str, Any]]:
        if isinstance(steps, str):
            parts = [part.strip(" -\t") for part in re.split(r"\n+|\d+[\.、)]", steps) if part.strip(" -\t")]
            return [
                {"step": index + 1, "action": part, "expected": "完成该步骤并符合预期"}
                for index, part in enumerate(parts)
            ]
        if not isinstance(steps, list):
            return []

        normalized = []
        for index, step in enumerate(steps, start=1):
            if isinstance(step, str):
                action = step.strip()
                expected = "完成该步骤并符合预期"
            elif isinstance(step, dict):
                action = self._first_text(step, "action", "operation", "description", "step_description", "步骤", "操作")
                expected = self._first_text(step, "expected", "expected_result", "assertion", "预期", "预期结果")
                if not action and step.get("step") and not isinstance(step.get("step"), int):
                    action = str(step.get("step")).strip()
            else:
                continue

            if not action:
                continue
            normalized.append({
                "step": index,
                "action": action,
                "expected": expected or "完成该步骤并符合预期",
            })
        return normalized

    def _format_expected_response(self, raw_case: Dict[str, Any]) -> str:
        status = raw_case.get("expected_status")
        response = raw_case.get("expected_response")
        if status is not None and response is not None:
            return f"响应状态为 {status}，响应内容符合预期：{json.dumps(response, ensure_ascii=False)}"
        if status is not None:
            return f"响应状态为 {status}"
        if response is not None:
            return f"响应内容符合预期：{json.dumps(response, ensure_ascii=False)}"
        return "接口响应符合预期"

    def _steps_expected_summary(self, steps: List[Dict[str, Any]]) -> str:
        expected_values = [str(step.get("expected", "")).strip() for step in steps if step.get("expected")]
        return expected_values[-1] if expected_values else "测试通过"
    
    def _extract_cases_from_text(self, text: str, config: GenerationConfig) -> List[Dict[str, Any]]:
        """从文本中提取测试用例"""
        cases = []
        
        title_patterns = [
            r'(?:用例标题|测试用例标题|Case Title|Title)[：:]\s*(.+?)(?:\n|$)',
            r'(?:测试用例|用例|Test Case)\s*\d*\s*[：:]\s*(.+?)(?:\n|$)',
            r'^\s*#{1,6}\s*(?:测试用例|用例|Test Case)\s*\d*[\s：:.-]+(.+?)\s*$',
            r'^\s*\d+[\.、]\s*(.+?)\s*$',
        ]
        titles = []
        for pattern in title_patterns:
            for match in re.findall(pattern, text, re.MULTILINE | re.IGNORECASE):
                title = str(match).strip().strip('"').strip("'")
                if self._is_usable_title(title) and title not in titles and len(title) <= 120:
                    titles.append(title)

        if not titles and text.strip():
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
            if self._is_usable_title(first_line):
                titles.append(first_line[:120])
        
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
        requirement: Any,
        config: GenerationConfig
    ) -> List[Dict[str, Any]]:
        """验证和优化用例"""
        validated_cases = []
        
        for case in cases:
            try:
                # 基本验证
                if not self._is_usable_title(case.get('case_title', '')):
                    case['case_title'] = f"基于{getattr(requirement, 'title', '需求')}的测试用例"
                
                if not case.get('test_steps'):
                    case['test_steps'] = [
                        {'step': 1, 'action': '执行测试', 'expected': '测试通过'}
                    ]
                
                if not case.get('expected_result'):
                    case['expected_result'] = '功能正常工作'
                
                # 设置默认值
                case.setdefault('case_type', config.case_type.value)
                case.setdefault('priority', config.priority.value)
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
