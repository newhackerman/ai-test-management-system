"""
Playwright集成模块
实现Web UI自动化测试执行，支持多浏览器和并发执行
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # 创建模拟类型以避免导入错误
    class Browser: pass
    class BrowserContext: pass
    class Page: pass
    class Playwright: pass

# 模拟依赖模块
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

def get_logger(name):
    return MockLogger()

class TestExecutionError(Exception):
    pass

class ConfigurationError(Exception):
    pass

logger = get_logger(__name__)


class BrowserType(Enum):
    """支持的浏览器类型"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class PlaywrightConfig:
    """Playwright配置"""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout: int = 30000  # 30秒
    screenshot_on_failure: bool = True
    video_recording: bool = False
    trace_recording: bool = False
    parallel_workers: int = 1
    retry_count: int = 0
    base_url: Optional[str] = None
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None


@dataclass
class TestStep:
    """测试步骤"""
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    expected: Optional[str] = None
    timeout: Optional[int] = None
    description: Optional[str] = None


@dataclass
class TestCase:
    """测试用例"""
    id: str
    title: str
    description: str
    steps: List[TestStep]
    preconditions: Optional[List[str]] = None
    test_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    test_case_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: datetime
    duration_ms: int
    error_message: Optional[str] = None
    screenshots: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    traces: Optional[List[str]] = None
    logs: Optional[List[str]] = None
    step_results: Optional[List[Dict[str, Any]]] = None


class PlaywrightTestExecutor:
    """Playwright测试执行器"""
    
    def __init__(self, config: PlaywrightConfig):
        if not PLAYWRIGHT_AVAILABLE:
            raise ConfigurationError("Playwright未安装，请运行: pip install playwright")
        
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self.results: List[ExecutionResult] = []
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
        
    async def initialize(self):
        """初始化Playwright"""
        try:
            self.playwright = await async_playwright().start()
            
            # 启动浏览器
            browser_options = {
                "headless": self.config.headless,
                "args": []
            }
            
            if self.config.user_agent:
                browser_options["args"].append(f"--user-agent={self.config.user_agent}")
                
            if self.config.browser_type == BrowserType.CHROMIUM:
                self.browser = await self.playwright.chromium.launch(**browser_options)
            elif self.config.browser_type == BrowserType.FIREFOX:
                self.browser = await self.playwright.firefox.launch(**browser_options)
            elif self.config.browser_type == BrowserType.WEBKIT:
                self.browser = await self.playwright.webkit.launch(**browser_options)
            else:
                raise ConfigurationError(f"不支持的浏览器类型: {self.config.browser_type}")
                
            logger.info(f"Playwright初始化完成，浏览器: {self.config.browser_type.value}")
            
        except Exception as e:
            logger.error(f"Playwright初始化失败: {str(e)}")
            raise TestExecutionError(f"Playwright初始化失败: {str(e)}")
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 关闭所有上下文
            for context in self.contexts:
                await context.close()
            self.contexts.clear()
            
            # 关闭浏览器
            if self.browser:
                await self.browser.close()
                
            # 停止Playwright
            if self.playwright:
                await self.playwright.stop()
                
            logger.info("Playwright资源清理完成")
            
        except Exception as e:
            logger.error(f"Playwright资源清理失败: {str(e)}")
    
    async def create_context(self, test_case: TestCase) -> BrowserContext:
        """创建浏览器上下文"""
        context_options = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            },
            "ignore_https_errors": True,
            "record_video_dir": None,
            "record_video_size": None
        }
        
        # 配置基础URL
        if self.config.base_url:
            context_options["base_url"] = self.config.base_url
            
        # 配置额外HTTP头
        if self.config.extra_http_headers:
            context_options["extra_http_headers"] = self.config.extra_http_headers
            
        # 配置视频录制
        if self.config.video_recording:
            video_dir = tempfile.mkdtemp(prefix="playwright_videos_")
            context_options["record_video_dir"] = video_dir
            context_options["record_video_size"] = {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            }
        
        context = await self.browser.new_context(**context_options)
        
        # 配置追踪
        if self.config.trace_recording:
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            
        self.contexts.append(context)
        return context
    
    async def execute_test_case(self, test_case: TestCase) -> ExecutionResult:
        """执行单个测试用例"""
        start_time = datetime.now()
        result = ExecutionResult(
            test_case_id=test_case.id,
            status=ExecutionStatus.PENDING,
            start_time=start_time,
            end_time=start_time,
            duration_ms=0
        )
        
        try:
            logger.info(f"开始执行测试用例: {test_case.title}")
            result.status = ExecutionStatus.RUNNING
            
            # 创建浏览器上下文
            context = await self.create_context(test_case)
            page = await context.new_page()
            
            # 设置默认超时
            page.set_default_timeout(self.config.timeout)
            
            # 执行前置条件
            if test_case.preconditions:
                await self._execute_preconditions(page, test_case.preconditions)
            
            # 执行测试步骤
            step_results = []
            for i, step in enumerate(test_case.steps):
                try:
                    step_result = await self._execute_step(page, step, i + 1)
                    step_results.append(step_result)
                    
                    if not step_result.get("success", False):
                        result.status = ExecutionStatus.FAILED
                        result.error_message = step_result.get("error", "步骤执行失败")
                        break
                        
                except Exception as e:
                    step_result = {
                        "step_number": i + 1,
                        "action": step.action,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    step_results.append(step_result)
                    result.status = ExecutionStatus.FAILED
                    result.error_message = str(e)
                    break
            
            result.step_results = step_results
            
            # 如果所有步骤都成功，标记为通过
            if result.status == ExecutionStatus.RUNNING:
                result.status = ExecutionStatus.PASSED
            
            # 截图（失败时或配置要求时）
            if (result.status == ExecutionStatus.FAILED and self.config.screenshot_on_failure) or \
               (result.status == ExecutionStatus.PASSED):
                screenshot_path = await self._take_screenshot(page, test_case.id, result.status)
                if screenshot_path:
                    result.screenshots = [screenshot_path]
            
            # 保存追踪
            if self.config.trace_recording:
                trace_path = await self._save_trace(context, test_case.id)
                if trace_path:
                    result.traces = [trace_path]
            
            # 保存视频
            if self.config.video_recording:
                await page.close()
                video_path = await page.video.path() if page.video else None
                if video_path:
                    result.videos = [str(video_path)]
            
            await context.close()
            
        except Exception as e:
            logger.error(f"测试用例执行异常: {test_case.id}, 错误: {str(e)}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.now()
            result.duration_ms = int((result.end_time - result.start_time).total_seconds() * 1000)
            
        logger.info(f"测试用例执行完成: {test_case.id}, 状态: {result.status.value}, 耗时: {result.duration_ms}ms")
        return result
    
    async def _execute_preconditions(self, page: Page, preconditions: List[str]):
        """执行前置条件"""
        for condition in preconditions:
            logger.debug(f"执行前置条件: {condition}")
            # 这里可以根据具体需求实现前置条件的执行逻辑
            # 例如：登录、设置数据等
    
    async def _execute_step(self, page: Page, step: TestStep, step_number: int) -> Dict[str, Any]:
        """执行测试步骤"""
        step_result = {
            "step_number": step_number,
            "action": step.action,
            "selector": step.selector,
            "value": step.value,
            "expected": step.expected,
            "success": False,
            "actual": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            logger.debug(f"执行步骤 {step_number}: {step.action}")
            
            # 设置步骤超时
            timeout = step.timeout or self.config.timeout
            
            if step.action == "navigate":
                await page.goto(step.value, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "click":
                await page.click(step.selector, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "fill":
                await page.fill(step.selector, step.value, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "type":
                await page.type(step.selector, step.value, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "select":
                await page.select_option(step.selector, step.value, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "wait_for_selector":
                await page.wait_for_selector(step.selector, timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "wait_for_text":
                await page.wait_for_selector(f"text={step.value}", timeout=timeout)
                step_result["success"] = True
                
            elif step.action == "assert_text":
                element = await page.wait_for_selector(step.selector, timeout=timeout)
                actual_text = await element.text_content()
                step_result["actual"] = actual_text
                if actual_text == step.expected:
                    step_result["success"] = True
                else:
                    step_result["error"] = f"期望文本: {step.expected}, 实际文本: {actual_text}"
                    
            elif step.action == "assert_visible":
                element = await page.wait_for_selector(step.selector, timeout=timeout)
                is_visible = await element.is_visible()
                step_result["actual"] = is_visible
                if is_visible:
                    step_result["success"] = True
                else:
                    step_result["error"] = f"元素不可见: {step.selector}"
                    
            elif step.action == "assert_url":
                current_url = page.url
                step_result["actual"] = current_url
                if step.expected in current_url:
                    step_result["success"] = True
                else:
                    step_result["error"] = f"期望URL包含: {step.expected}, 实际URL: {current_url}"
                    
            elif step.action == "wait":
                await page.wait_for_timeout(int(step.value))
                step_result["success"] = True
                
            elif step.action == "scroll":
                await page.evaluate(f"window.scrollTo(0, {step.value})")
                step_result["success"] = True
                
            elif step.action == "screenshot":
                screenshot_path = await self._take_screenshot(page, f"step_{step_number}", ExecutionStatus.RUNNING)
                step_result["screenshot"] = screenshot_path
                step_result["success"] = True
                
            else:
                step_result["error"] = f"不支持的操作: {step.action}"
                
        except Exception as e:
            step_result["error"] = str(e)
            logger.error(f"步骤执行失败: {step_number}, 错误: {str(e)}")
        
        return step_result
    
    async def _take_screenshot(self, page: Page, test_id: str, status: ExecutionStatus) -> Optional[str]:
        """截图"""
        try:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{test_id}_{status.value}_{timestamp}.png"
            screenshot_path = screenshots_dir / filename
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.debug(f"截图保存: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None
    
    async def _save_trace(self, context: BrowserContext, test_id: str) -> Optional[str]:
        """保存追踪"""
        try:
            traces_dir = Path("traces")
            traces_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{test_id}_{timestamp}.zip"
            trace_path = traces_dir / filename
            
            await context.tracing.stop(path=str(trace_path))
            logger.debug(f"追踪保存: {trace_path}")
            return str(trace_path)
            
        except Exception as e:
            logger.error(f"追踪保存失败: {str(e)}")
            return None
    
    async def execute_test_suite(self, test_cases: List[TestCase]) -> List[ExecutionResult]:
        """执行测试套件"""
        logger.info(f"开始执行测试套件，共 {len(test_cases)} 个用例")
        
        if self.config.parallel_workers > 1:
            # 并发执行
            semaphore = asyncio.Semaphore(self.config.parallel_workers)
            tasks = []
            
            async def execute_with_semaphore(test_case: TestCase):
                async with semaphore:
                    return await self._execute_with_retry(test_case)
            
            for test_case in test_cases:
                task = asyncio.create_task(execute_with_semaphore(test_case))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = ExecutionResult(
                        test_case_id=test_cases[i].id,
                        status=ExecutionStatus.ERROR,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        duration_ms=0,
                        error_message=str(result)
                    )
                    final_results.append(error_result)
                else:
                    final_results.append(result)
            
            self.results = final_results
        else:
            # 串行执行
            results = []
            for test_case in test_cases:
                result = await self._execute_with_retry(test_case)
                results.append(result)
            
            self.results = results
        
        # 统计结果
        passed = len([r for r in self.results if r.status == ExecutionStatus.PASSED])
        failed = len([r for r in self.results if r.status == ExecutionStatus.FAILED])
        error = len([r for r in self.results if r.status == ExecutionStatus.ERROR])
        
        logger.info(f"测试套件执行完成: 总计 {len(self.results)}, 通过 {passed}, 失败 {failed}, 错误 {error}")
        
        return self.results
    
    async def _execute_with_retry(self, test_case: TestCase) -> ExecutionResult:
        """带重试的执行"""
        last_result = None
        
        for attempt in range(self.config.retry_count + 1):
            if attempt > 0:
                logger.info(f"重试执行测试用例: {test_case.id}, 第 {attempt} 次重试")
                await asyncio.sleep(1)  # 重试间隔
            
            result = await self.execute_test_case(test_case)
            last_result = result
            
            if result.status == ExecutionStatus.PASSED:
                break
        
        return last_result
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        if not self.results:
            return {"total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0}
        
        summary = {
            "total": len(self.results),
            "passed": len([r for r in self.results if r.status == ExecutionStatus.PASSED]),
            "failed": len([r for r in self.results if r.status == ExecutionStatus.FAILED]),
            "error": len([r for r in self.results if r.status == ExecutionStatus.ERROR]),
            "skipped": len([r for r in self.results if r.status == ExecutionStatus.SKIPPED]),
            "total_duration_ms": sum(r.duration_ms for r in self.results),
            "average_duration_ms": sum(r.duration_ms for r in self.results) // len(self.results) if self.results else 0
        }
        
        summary["pass_rate"] = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
        
        return summary


class PlaywrightIntegration:
    """Playwright集成主类"""
    
    def __init__(self):
        self.default_config = PlaywrightConfig()
    
    async def execute_tests(
        self, 
        test_cases: List[TestCase], 
        config: Optional[PlaywrightConfig] = None
    ) -> Dict[str, Any]:
        """执行测试"""
        execution_config = config or self.default_config
        
        async with PlaywrightTestExecutor(execution_config) as executor:
            results = await executor.execute_test_suite(test_cases)
            summary = executor.get_execution_summary()
            
            return {
                "summary": summary,
                "results": [asdict(result) for result in results],
                "config": asdict(execution_config)
            }
    
    def parse_test_case_from_json(self, test_case_data: Dict[str, Any]) -> TestCase:
        """从JSON数据解析测试用例"""
        steps = []
        for step_data in test_case_data.get("steps", []):
            step = TestStep(
                action=step_data["action"],
                selector=step_data.get("selector"),
                value=step_data.get("value"),
                expected=step_data.get("expected"),
                timeout=step_data.get("timeout"),
                description=step_data.get("description")
            )
            steps.append(step)
        
        return TestCase(
            id=test_case_data["id"],
            title=test_case_data["title"],
            description=test_case_data.get("description", ""),
            steps=steps,
            preconditions=test_case_data.get("preconditions"),
            test_data=test_case_data.get("test_data"),
            tags=test_case_data.get("tags")
        )
    
    def create_sample_test_case(self) -> TestCase:
        """创建示例测试用例"""
        steps = [
            TestStep(
                action="navigate",
                value="https://example.com",
                description="打开示例网站"
            ),
            TestStep(
                action="wait_for_selector",
                selector="h1",
                description="等待页面标题加载"
            ),
            TestStep(
                action="assert_text",
                selector="h1",
                expected="Example Domain",
                description="验证页面标题"
            ),
            TestStep(
                action="screenshot",
                description="截图记录"
            )
        ]
        
        return TestCase(
            id="sample_test_001",
            title="示例网站访问测试",
            description="验证示例网站的基本功能",
            steps=steps,
            tags=["smoke", "basic"]
        )


# 导出主要类和函数
__all__ = [
    "PlaywrightIntegration",
    "PlaywrightConfig",
    "TestCase",
    "TestStep",
    "ExecutionResult",
    "BrowserType",
    "ExecutionStatus"
]