"""
Allure报告集成模块
实现测试结果的Allure格式转换，支持丰富的测试报告生成
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, is_dataclass
from enum import Enum
import shutil

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


def _to_json_safe(value: Any) -> Any:
    """Convert dataclasses, enums, and containers to JSON-safe values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _to_json_safe(asdict(value))
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    return value


class AllureStatus(Enum):
    """Allure测试状态"""
    PASSED = "passed"
    FAILED = "failed"
    BROKEN = "broken"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class AllureSeverity(Enum):
    """Allure严重程度"""
    BLOCKER = "blocker"
    CRITICAL = "critical"
    NORMAL = "normal"
    MINOR = "minor"
    TRIVIAL = "trivial"


class AttachmentType(Enum):
    """附件类型"""
    TEXT = "text/plain"
    HTML = "text/html"
    JSON = "application/json"
    XML = "application/xml"
    PNG = "image/png"
    JPEG = "image/jpeg"
    PDF = "application/pdf"
    VIDEO = "video/mp4"
    LOG = "text/plain"


@dataclass
class AllureLabel:
    """Allure标签"""
    name: str
    value: str


@dataclass
class AllureLink:
    """Allure链接"""
    name: str
    url: str
    type: str = "link"  # link, issue, tms


@dataclass
class AllureParameter:
    """Allure参数"""
    name: str
    value: str


@dataclass
class AllureStep:
    """Allure测试步骤"""
    name: str
    status: AllureStatus
    start: int
    stop: int
    uuid: str
    parameters: Optional[List[AllureParameter]] = None
    attachments: Optional[List[str]] = None
    steps: Optional[List['AllureStep']] = None


@dataclass
class AllureAttachment:
    """Allure附件"""
    name: str
    source: str
    type: AttachmentType
    uuid: str


@dataclass
class AllureTestResult:
    """Allure测试结果"""
    uuid: str
    name: str
    full_name: str
    description: Optional[str]
    description_html: Optional[str]
    status: AllureStatus
    status_details: Optional[Dict[str, Any]]
    stage: str
    start: int
    stop: int
    labels: List[AllureLabel]
    parameters: Optional[List[AllureParameter]]
    links: Optional[List[AllureLink]]
    attachments: Optional[List[AllureAttachment]]
    steps: Optional[List[AllureStep]]


@dataclass
class AllureContainer:
    """Allure容器（测试套件）"""
    uuid: str
    name: str
    children: List[str]
    description: Optional[str]
    description_html: Optional[str]
    befores: Optional[List[Dict[str, Any]]]
    afters: Optional[List[Dict[str, Any]]]
    start: int
    stop: int


@dataclass
class AllureConfig:
    """Allure配置"""
    results_directory: str = "allure-results"
    report_directory: str = "allure-report"
    allure_command: str = "allure"
    clean_results: bool = True
    generate_report: bool = True
    open_report: bool = False
    history_trend: bool = True
    categories_file: Optional[str] = None
    environment_file: Optional[str] = None


class AllureResultsGenerator:
    """Allure结果生成器"""
    
    def __init__(self, config: AllureConfig):
        self.config = config
        self.results_dir = Path(config.results_directory)
        self.attachments_dir = self.results_dir / "attachments"
        
        # 确保目录存在
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # 清理旧结果
        if config.clean_results:
            self._clean_results_directory()
    
    def _clean_results_directory(self):
        """清理结果目录"""
        if self.results_dir.exists():
            for file in self.results_dir.glob("*.json"):
                file.unlink()
            for file in self.attachments_dir.glob("*"):
                file.unlink()
        logger.info(f"清理Allure结果目录: {self.results_dir}")
    
    def create_test_result(
        self,
        test_case_id: str,
        test_name: str,
        status: AllureStatus,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        error_message: Optional[str] = None,
        error_trace: Optional[str] = None
    ) -> AllureTestResult:
        """创建测试结果"""
        test_uuid = str(uuid.uuid4())
        
        # 状态详情
        status_details = None
        if status in [AllureStatus.FAILED, AllureStatus.BROKEN]:
            status_details = {
                "known": False,
                "muted": False,
                "flaky": False
            }
            if error_message:
                status_details["message"] = error_message
            if error_trace:
                status_details["trace"] = error_trace
        
        # 基本标签
        labels = [
            AllureLabel("testId", test_case_id),
            AllureLabel("testClass", "TestManager"),
            AllureLabel("testMethod", test_name),
            AllureLabel("package", "testmanager"),
            AllureLabel("framework", "custom"),
            AllureLabel("language", "python")
        ]
        
        result = AllureTestResult(
            uuid=test_uuid,
            name=test_name,
            full_name=f"testmanager.{test_case_id}.{test_name}",
            description=description,
            description_html=f"<p>{description}</p>" if description else None,
            status=status,
            status_details=status_details,
            stage="finished",
            start=int(start_time.timestamp() * 1000),
            stop=int(end_time.timestamp() * 1000),
            labels=labels,
            parameters=None,
            links=None,
            attachments=None,
            steps=None
        )
        
        return result
    
    def add_label(self, result: AllureTestResult, name: str, value: str):
        """添加标签"""
        result.labels.append(AllureLabel(name, value))
    
    def add_link(self, result: AllureTestResult, name: str, url: str, link_type: str = "link"):
        """添加链接"""
        if result.links is None:
            result.links = []
        result.links.append(AllureLink(name, url, link_type))
    
    def add_parameter(self, result: AllureTestResult, name: str, value: str):
        """添加参数"""
        if result.parameters is None:
            result.parameters = []
        result.parameters.append(AllureParameter(name, value))
    
    def add_attachment(
        self,
        result: AllureTestResult,
        name: str,
        content: Union[str, bytes],
        attachment_type: AttachmentType
    ) -> str:
        """添加附件"""
        attachment_uuid = str(uuid.uuid4())
        
        # 确定文件扩展名
        extension_map = {
            AttachmentType.TEXT: ".txt",
            AttachmentType.HTML: ".html",
            AttachmentType.JSON: ".json",
            AttachmentType.XML: ".xml",
            AttachmentType.PNG: ".png",
            AttachmentType.JPEG: ".jpg",
            AttachmentType.PDF: ".pdf",
            AttachmentType.VIDEO: ".mp4",
            AttachmentType.LOG: ".log"
        }
        
        extension = extension_map.get(attachment_type, ".txt")
        filename = f"{attachment_uuid}-attachment{extension}"
        file_path = self.attachments_dir / filename
        
        # 保存附件文件
        if isinstance(content, str):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        # 创建附件对象
        attachment = AllureAttachment(
            name=name,
            source=filename,
            type=attachment_type,
            uuid=attachment_uuid
        )
        
        if result.attachments is None:
            result.attachments = []
        result.attachments.append(attachment)
        
        logger.debug(f"添加附件: {name} -> {filename}")
        return attachment_uuid
    
    def add_step(
        self,
        result: AllureTestResult,
        step_name: str,
        status: AllureStatus,
        start_time: datetime,
        end_time: datetime,
        parameters: Optional[List[AllureParameter]] = None
    ) -> AllureStep:
        """添加测试步骤"""
        step_uuid = str(uuid.uuid4())
        
        step = AllureStep(
            name=step_name,
            status=status,
            start=int(start_time.timestamp() * 1000),
            stop=int(end_time.timestamp() * 1000),
            uuid=step_uuid,
            parameters=parameters,
            attachments=None,
            steps=None
        )
        
        if result.steps is None:
            result.steps = []
        result.steps.append(step)
        
        return step
    
    def save_test_result(self, result: AllureTestResult):
        """保存测试结果"""
        result_file = self.results_dir / f"{result.uuid}-result.json"
        
        # 转换为字典并处理特殊字段
        result_dict = _to_json_safe(result)
        
        # 处理嵌套对象
        if result_dict.get("attachments"):
            result_dict["attachments"] = [
                {
                    "name": att.name,
                    "source": att.source,
                    "type": att.type.value,
                    "uuid": att.uuid
                } for att in result.attachments
            ]
        
        if result_dict.get("steps"):
            result_dict["steps"] = self._serialize_steps(result.steps)
        
        # 保存JSON文件
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"保存测试结果: {result_file}")
    
    def _serialize_steps(self, steps: List[AllureStep]) -> List[Dict[str, Any]]:
        """序列化测试步骤"""
        serialized_steps = []
        
        for step in steps:
            step_dict = {
                "name": step.name,
                "status": step.status.value,
                "start": step.start,
                "stop": step.stop,
                "uuid": step.uuid
            }
            
            if step.parameters:
                step_dict["parameters"] = [
                    {"name": p.name, "value": p.value} for p in step.parameters
                ]
            
            if step.attachments:
                step_dict["attachments"] = step.attachments
            
            if step.steps:
                step_dict["steps"] = self._serialize_steps(step.steps)
            
            serialized_steps.append(step_dict)
        
        return serialized_steps
    
    def create_container(
        self,
        container_name: str,
        children_uuids: List[str],
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None
    ) -> AllureContainer:
        """创建容器（测试套件）"""
        container_uuid = str(uuid.uuid4())
        
        container = AllureContainer(
            uuid=container_uuid,
            name=container_name,
            children=children_uuids,
            description=description,
            description_html=f"<p>{description}</p>" if description else None,
            befores=None,
            afters=None,
            start=int(start_time.timestamp() * 1000),
            stop=int(end_time.timestamp() * 1000)
        )
        
        return container
    
    def save_container(self, container: AllureContainer):
        """保存容器"""
        container_file = self.results_dir / f"{container.uuid}-container.json"
        
        container_dict = _to_json_safe(container)
        
        with open(container_file, 'w', encoding='utf-8') as f:
            json.dump(container_dict, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"保存容器: {container_file}")
    
    def create_environment_file(self, environment_data: Dict[str, str]):
        """创建环境信息文件"""
        env_file = self.results_dir / "environment.properties"
        
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in environment_data.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"创建环境文件: {env_file}")
    
    def create_categories_file(self, categories: List[Dict[str, Any]]):
        """创建分类文件"""
        categories_file = self.results_dir / "categories.json"
        
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        logger.info(f"创建分类文件: {categories_file}")


class AllureReportGenerator:
    """Allure报告生成器"""
    
    def __init__(self, config: AllureConfig):
        self.config = config
        self.allure_command = self._find_allure_command()
    
    def _find_allure_command(self) -> str:
        """查找Allure命令"""
        # 尝试配置中的命令
        if self.config.allure_command:
            try:
                result = subprocess.run([self.config.allure_command, "--version"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return self.config.allure_command
            except:
                pass
        
        # 尝试从PATH中查找
        try:
            result = subprocess.run(["which", "allure"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # 尝试常见路径
        common_paths = [
            "/usr/local/bin/allure",
            "/opt/allure/bin/allure",
            "C:\\allure\\bin\\allure.bat"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        logger.warning("未找到Allure命令，报告生成功能将不可用")
        return "allure"
    
    async def generate_report(self, results_dir: Optional[str] = None, report_dir: Optional[str] = None) -> str:
        """生成Allure报告"""
        results_path = results_dir or self.config.results_directory
        report_path = report_dir or self.config.report_directory
        
        # 确保报告目录存在
        Path(report_path).mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.allure_command,
            "generate",
            results_path,
            "-o", report_path,
            "--clean"
        ]

        if not shutil.which(self.allure_command):
            logger.warning(f"Allure CLI not found, using built-in HTML report renderer: {self.allure_command}")
            return self._generate_fallback_report(results_path, report_path, self.allure_command)
        
        try:
            logger.info(f"生成Allure报告: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Allure报告生成成功: {report_path}")
                
                # 如果配置了打开报告
                if self.config.open_report:
                    await self.open_report(report_path)
                
                return report_path
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"Allure报告生成失败: {error_msg}")
                raise TestExecutionError(f"Allure报告生成失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"Allure报告生成异常: {str(e)}")
            raise TestExecutionError(f"Allure报告生成异常: {str(e)}")
    
    def _generate_fallback_report(self, results_dir: str, report_dir: str, reason: str = "") -> str:
        """Render a minimal static HTML report when the Allure CLI is unavailable."""
        results_path = Path(results_dir)
        report_path = Path(report_dir)
        report_path.mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, Any]] = []
        for result_file in results_path.glob("*-result.json"):
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to read Allure result file {result_file}: {e}")

        status_counts: Dict[str, int] = {}
        for result in results:
            status = str(result.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        summary_items = "\n".join(
            f"<div class='metric'><strong>{count}</strong><span>{escape(status)}</span></div>"
            for status, count in sorted(status_counts.items())
        )
        rows = "\n".join(
            f"<tr><td>{escape(str(item.get('name', '-')))}</td>"
            f"<td><span class='status {escape(str(item.get('status', 'unknown')))}'>"
            f"{escape(str(item.get('status', 'unknown')))}</span></td>"
            f"<td>{escape(str(item.get('description') or ''))}</td></tr>"
            for item in results
        )

        fallback_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Allure Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f6f8fa; color: #1f2937; }}
    header {{ background: #111827; color: white; padding: 24px 32px; }}
    main {{ padding: 24px 32px; }}
    .metrics {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }}
    .metric {{ background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 14px 18px; min-width: 110px; }}
    .metric strong {{ display: block; font-size: 24px; }}
    .notice {{ background: #fff7ed; border: 1px solid #fed7aa; border-radius: 6px; padding: 12px; margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; }}
    th, td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
    th {{ background: #f9fafb; }}
    .status {{ padding: 3px 8px; border-radius: 999px; background: #e5e7eb; }}
    .passed {{ background: #dcfce7; color: #166534; }}
    .failed, .broken {{ background: #fee2e2; color: #991b1b; }}
    .skipped {{ background: #fef3c7; color: #92400e; }}
  </style>
</head>
<body>
  <header>
    <h1>Allure Report</h1>
    <p>Generated by built-in fallback renderer</p>
  </header>
  <main>
    <div class="notice">Allure CLI is unavailable or failed, so a built-in HTML report was generated. Reason: {escape(reason)}</div>
    <div class="metrics">
      <div class="metric"><strong>{len(results)}</strong><span>Total</span></div>
      {summary_items}
    </div>
    <table>
      <thead><tr><th>Test</th><th>Status</th><th>Description</th></tr></thead>
      <tbody>{rows or "<tr><td colspan='3'>No results</td></tr>"}</tbody>
    </table>
  </main>
</body>
</html>"""

        (report_path / "index.html").write_text(fallback_html, encoding="utf-8")
        return str(report_path)

    async def serve_report(self, results_dir: Optional[str] = None, port: int = 0) -> str:
        """启动Allure报告服务"""
        results_path = results_dir or self.config.results_directory
        
        cmd = [self.allure_command, "serve", results_path]
        if port > 0:
            cmd.extend(["-p", str(port)])
        
        try:
            logger.info(f"启动Allure报告服务: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待服务启动
            await asyncio.sleep(3)
            
            if process.returncode is None:  # 进程仍在运行
                logger.info("Allure报告服务启动成功")
                return f"http://localhost:{port if port > 0 else 'auto'}"
            else:
                stdout, stderr = await process.communicate()
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"Allure报告服务启动失败: {error_msg}")
                raise TestExecutionError(f"Allure报告服务启动失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"Allure报告服务异常: {str(e)}")
            raise TestExecutionError(f"Allure报告服务异常: {str(e)}")
    
    async def open_report(self, report_dir: str):
        """打开报告"""
        index_file = Path(report_dir) / "index.html"
        
        if index_file.exists():
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(index_file))
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(["open" if os.uname().sysname == "Darwin" else "xdg-open", str(index_file)])
                
                logger.info(f"打开Allure报告: {index_file}")
            except Exception as e:
                logger.warning(f"无法自动打开报告: {str(e)}")
        else:
            logger.warning(f"报告文件不存在: {index_file}")


class AllureIntegration:
    """Allure集成主类"""
    
    def __init__(self, config: Optional[AllureConfig] = None):
        self.config = config or AllureConfig()
        self.results_generator = AllureResultsGenerator(self.config)
        self.report_generator = AllureReportGenerator(self.config)
    
    def convert_test_execution_to_allure(
        self,
        test_case_id: str,
        test_name: str,
        status: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        error_message: Optional[str] = None,
        error_trace: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        labels: Optional[Dict[str, str]] = None,
        links: Optional[List[Dict[str, str]]] = None
    ) -> AllureTestResult:
        """将测试执行结果转换为Allure格式"""
        
        # 状态映射
        status_mapping = {
            "PASSED": AllureStatus.PASSED,
            "FAILED": AllureStatus.FAILED,
            "ERROR": AllureStatus.BROKEN,
            "SKIPPED": AllureStatus.SKIPPED,
            "BLOCKED": AllureStatus.BROKEN
        }
        
        allure_status = status_mapping.get(status.upper(), AllureStatus.UNKNOWN)
        
        # 创建测试结果
        result = self.results_generator.create_test_result(
            test_case_id=test_case_id,
            test_name=test_name,
            status=allure_status,
            start_time=start_time,
            end_time=end_time,
            description=description,
            error_message=error_message,
            error_trace=error_trace
        )
        
        # 添加标签
        if labels:
            for name, value in labels.items():
                self.results_generator.add_label(result, name, value)
        
        # 添加链接
        if links:
            for link in links:
                self.results_generator.add_link(
                    result,
                    link.get("name", ""),
                    link.get("url", ""),
                    link.get("type", "link")
                )
        
        # 添加附件
        if attachments:
            for attachment in attachments:
                attachment_type = AttachmentType.TEXT
                if attachment.get("type"):
                    try:
                        attachment_type = AttachmentType(attachment["type"])
                    except ValueError:
                        attachment_type = AttachmentType.TEXT
                
                self.results_generator.add_attachment(
                    result,
                    attachment.get("name", "attachment"),
                    attachment.get("content", ""),
                    attachment_type
                )
        
        # 添加步骤
        if steps:
            for step_data in steps:
                step_status = status_mapping.get(step_data.get("status", "PASSED").upper(), AllureStatus.PASSED)
                
                step_start = datetime.fromisoformat(step_data.get("start_time", start_time.isoformat()))
                step_end = datetime.fromisoformat(step_data.get("end_time", end_time.isoformat()))
                
                self.results_generator.add_step(
                    result,
                    step_data.get("name", "Step"),
                    step_status,
                    step_start,
                    step_end
                )
        
        return result
    
    def save_test_results(self, results: List[AllureTestResult]):
        """保存测试结果"""
        for result in results:
            self.results_generator.save_test_result(result)
        
        logger.info(f"保存了 {len(results)} 个测试结果")
    
    def create_test_suite_container(
        self,
        suite_name: str,
        test_results: List[AllureTestResult],
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None
    ) -> AllureContainer:
        """创建测试套件容器"""
        children_uuids = [result.uuid for result in test_results]
        
        container = self.results_generator.create_container(
            container_name=suite_name,
            children_uuids=children_uuids,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        
        self.results_generator.save_container(container)
        return container
    
    def setup_environment(self, environment_data: Dict[str, str]):
        """设置环境信息"""
        self.results_generator.create_environment_file(environment_data)
    
    def setup_categories(self):
        """设置默认分类"""
        default_categories = [
            {
                "name": "产品缺陷",
                "matchedStatuses": ["failed"],
                "messageRegex": ".*AssertionError.*"
            },
            {
                "name": "测试缺陷",
                "matchedStatuses": ["broken"],
                "messageRegex": ".*"
            },
            {
                "name": "已知问题",
                "matchedStatuses": ["failed", "broken"],
                "messageRegex": ".*known issue.*"
            }
        ]
        
        self.results_generator.create_categories_file(default_categories)
    
    async def generate_and_serve_report(self, port: int = 0) -> str:
        """生成并启动报告服务"""
        # 生成报告
        report_path = await self.report_generator.generate_report()
        
        # 启动服务
        service_url = await self.report_generator.serve_report(port=port)
        
        return service_url
    
    async def generate_static_report(self) -> str:
        """生成静态报告"""
        return await self.report_generator.generate_report()
    
    def create_sample_environment(self) -> Dict[str, str]:
        """创建示例环境信息"""
        return {
            "Browser": "Chrome",
            "Browser.Version": "91.0.4472.124",
            "OS": "Linux",
            "Python.Version": "3.9.0",
            "Test.Environment": "QA",
            "Application.Version": "1.0.0",
            "Database": "MySQL 8.0",
            "Test.Framework": "TestManager"
        }
    
    def create_sample_test_result(self) -> AllureTestResult:
        """创建示例测试结果"""
        start_time = datetime.now()
        end_time = datetime.now()
        
        result = self.convert_test_execution_to_allure(
            test_case_id="TC001",
            test_name="示例测试用例",
            status="PASSED",
            start_time=start_time,
            end_time=end_time,
            description="这是一个示例测试用例，用于演示Allure报告功能",
            labels={
                "severity": "normal",
                "feature": "登录功能",
                "story": "用户登录",
                "owner": "测试团队"
            },
            links=[
                {
                    "name": "需求链接",
                    "url": "https://example.com/requirement/123",
                    "type": "tms"
                }
            ]
        )
        
        return result


# 导出主要类和函数
__all__ = [
    "AllureIntegration",
    "AllureConfig",
    "AllureTestResult",
    "AllureStatus",
    "AllureSeverity",
    "AttachmentType"
]
