"""
Allure报告管理器

本模块实现Allure测试报告的生成、管理和服务功能，包括：
- 测试结果转换为Allure格式
- HTML报告生成和服务
- 报告文件管理和存储
- 与现有测试执行系统的集成
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from ..integrations.allure_integration import (
    AllureIntegration, 
    AllureConfig, 
    AllureTestResult, 
    AllureStatus,
    AttachmentType
)
from ..core.config import get_settings
from ..core.exceptions import TestExecutionError, ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class AllureReportConfig:
    """Allure报告配置"""
    results_directory: str = "allure-results"
    report_directory: str = "allure-report"
    allure_command: str = "allure"
    clean_results: bool = True
    generate_report: bool = True
    open_report: bool = False
    history_trend: bool = True
    categories_file: Optional[str] = None
    environment_file: Optional[str] = None
    serve_port: int = 0
    auto_cleanup: bool = True
    max_report_age_days: int = 30


@dataclass
class TestExecutionData:
    """测试执行数据"""
    test_case_id: str
    test_name: str
    status: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    error_message: Optional[str] = None
    error_trace: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    labels: Optional[Dict[str, str]] = None
    links: Optional[List[Dict[str, str]]] = None
    project_id: Optional[int] = None
    test_plan_id: Optional[int] = None
    environment: Optional[str] = None


@dataclass
class AllureReportResult:
    """Allure报告生成结果"""
    report_id: str
    report_path: str
    report_url: Optional[str]
    status: str
    generation_time: float
    file_size: int
    test_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_message: Optional[str] = None


class AllureManager:
    """Allure报告管理器"""
    
    def __init__(self, config: Optional[AllureReportConfig] = None):
        """初始化Allure管理器"""
        self.config = config or AllureReportConfig()
        self.settings = get_settings()
        
        # 设置基础路径
        self.base_path = Path(self.settings.ALLURE_BASE_PATH or "reports/allure")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化Allure集成
        allure_config = AllureConfig(
            results_directory=str(self.base_path / self.config.results_directory),
            report_directory=str(self.base_path / self.config.report_directory),
            allure_command=self.config.allure_command,
            clean_results=self.config.clean_results,
            generate_report=self.config.generate_report,
            open_report=self.config.open_report,
            history_trend=self.config.history_trend
        )
        
        self.allure_integration = AllureIntegration(allure_config)
        
        # 报告存储
        self.active_reports: Dict[str, AllureReportResult] = {}
        
        logger.info(f"Allure管理器初始化完成，基础路径: {self.base_path}")
    
    async def create_report_from_test_executions(
        self,
        test_executions: List[TestExecutionData],
        report_name: str,
        project_id: Optional[int] = None,
        suite_name: Optional[str] = None
    ) -> AllureReportResult:
        """从测试执行数据创建Allure报告"""
        try:
            report_id = str(uuid.uuid4())
            start_time = datetime.now()
            
            logger.info(f"开始生成Allure报告: {report_name} (ID: {report_id})")
            
            # 创建报告专用目录
            report_base_path = self.base_path / report_id
            report_base_path.mkdir(parents=True, exist_ok=True)
            
            # 更新配置路径
            results_dir = report_base_path / "results"
            report_dir = report_base_path / "report"
            
            # 创建临时Allure配置
            temp_config = AllureConfig(
                results_directory=str(results_dir),
                report_directory=str(report_dir),
                allure_command=self.config.allure_command,
                clean_results=True,
                generate_report=True
            )
            
            temp_integration = AllureIntegration(temp_config)
            
            # 转换测试执行数据为Allure格式
            allure_results = []
            test_stats = {"passed": 0, "failed": 0, "skipped": 0, "broken": 0}
            
            for execution in test_executions:
                # 转换测试结果
                allure_result = temp_integration.convert_test_execution_to_allure(
                    test_case_id=execution.test_case_id,
                    test_name=execution.test_name,
                    status=execution.status,
                    start_time=execution.start_time,
                    end_time=execution.end_time,
                    description=execution.description,
                    error_message=execution.error_message,
                    error_trace=execution.error_trace,
                    attachments=execution.attachments,
                    steps=execution.steps,
                    labels=execution.labels,
                    links=execution.links
                )
                
                # 添加项目和环境标签
                if project_id:
                    temp_integration.results_generator.add_label(
                        allure_result, "project", str(project_id)
                    )
                
                if execution.environment:
                    temp_integration.results_generator.add_label(
                        allure_result, "environment", execution.environment
                    )
                
                allure_results.append(allure_result)
                
                # 统计测试结果
                status_key = allure_result.status.value
                if status_key in test_stats:
                    test_stats[status_key] += 1
            
            # 保存测试结果
            temp_integration.save_test_results(allure_results)
            
            # 创建测试套件容器
            if suite_name and allure_results:
                suite_start = min(r.start for r in allure_results)
                suite_end = max(r.stop for r in allure_results)
                
                temp_integration.create_test_suite_container(
                    suite_name=suite_name or report_name,
                    test_results=allure_results,
                    start_time=datetime.fromtimestamp(suite_start / 1000),
                    end_time=datetime.fromtimestamp(suite_end / 1000),
                    description=f"测试套件: {suite_name}"
                )
            
            # 设置环境信息
            environment_data = self._create_environment_data(project_id)
            temp_integration.setup_environment(environment_data)
            
            # 设置分类
            temp_integration.setup_categories()
            
            # 生成HTML报告
            report_path = await temp_integration.generate_static_report()
            
            # 计算报告大小
            report_size = self._calculate_directory_size(report_dir)
            
            # 生成时间
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # 创建报告结果
            report_result = AllureReportResult(
                report_id=report_id,
                report_path=str(report_dir),
                report_url=None,  # 将在服务启动时设置
                status="completed",
                generation_time=generation_time,
                file_size=report_size,
                test_count=len(test_executions),
                passed_count=test_stats["passed"],
                failed_count=test_stats["failed"],
                skipped_count=test_stats["skipped"]
            )
            
            # 存储报告信息
            self.active_reports[report_id] = report_result
            
            logger.info(f"Allure报告生成完成: {report_name}, 耗时: {generation_time:.2f}秒")
            
            return report_result
            
        except Exception as e:
            logger.error(f"生成Allure报告失败: {str(e)}")
            raise TestExecutionError(f"生成Allure报告失败: {str(e)}")
    
    async def serve_report(self, report_id: str, port: Optional[int] = None) -> str:
        """启动报告服务"""
        try:
            if report_id not in self.active_reports:
                raise ValueError(f"报告不存在: {report_id}")
            
            report = self.active_reports[report_id]
            serve_port = port or self.config.serve_port or 0
            
            # 使用Allure命令启动服务
            cmd = [
                self.config.allure_command,
                "serve",
                str(Path(report.report_path).parent / "results")
            ]
            
            if serve_port > 0:
                cmd.extend(["-p", str(serve_port)])
            
            logger.info(f"启动Allure报告服务: {' '.join(cmd)}")
            
            # 启动服务进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待服务启动
            await asyncio.sleep(3)
            
            if process.returncode is None:  # 进程仍在运行
                service_url = f"http://localhost:{serve_port if serve_port > 0 else 'auto'}"
                
                # 更新报告URL
                report.report_url = service_url
                
                logger.info(f"Allure报告服务启动成功: {service_url}")
                return service_url
            else:
                stdout, stderr = await process.communicate()
                error_msg = stderr.decode() if stderr else "未知错误"
                raise TestExecutionError(f"Allure报告服务启动失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"启动Allure报告服务失败: {str(e)}")
            raise TestExecutionError(f"启动Allure报告服务失败: {str(e)}")
    
    def get_report_info(self, report_id: str) -> Optional[AllureReportResult]:
        """获取报告信息"""
        return self.active_reports.get(report_id)
    
    def list_reports(self) -> List[AllureReportResult]:
        """列出所有报告"""
        return list(self.active_reports.values())
    
    async def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        try:
            if report_id not in self.active_reports:
                return False
            
            report = self.active_reports[report_id]
            
            # 删除报告文件
            report_base_path = Path(report.report_path).parent
            if report_base_path.exists():
                shutil.rmtree(report_base_path)
            
            # 从内存中移除
            del self.active_reports[report_id]
            
            logger.info(f"删除Allure报告: {report_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除Allure报告失败: {str(e)}")
            return False
    
    async def cleanup_old_reports(self) -> int:
        """清理过期报告"""
        if not self.config.auto_cleanup:
            return 0
        
        try:
            cleaned_count = 0
            cutoff_time = datetime.now().timestamp() - (self.config.max_report_age_days * 24 * 3600)
            
            # 检查文件系统中的报告目录
            for report_dir in self.base_path.iterdir():
                if report_dir.is_dir() and report_dir.name != self.config.results_directory:
                    try:
                        # 检查目录创建时间
                        dir_stat = report_dir.stat()
                        if dir_stat.st_ctime < cutoff_time:
                            # 删除过期报告
                            shutil.rmtree(report_dir)
                            
                            # 从内存中移除
                            if report_dir.name in self.active_reports:
                                del self.active_reports[report_dir.name]
                            
                            cleaned_count += 1
                            logger.info(f"清理过期报告: {report_dir.name}")
                    
                    except Exception as e:
                        logger.warning(f"清理报告失败 {report_dir.name}: {str(e)}")
            
            logger.info(f"清理完成，删除了 {cleaned_count} 个过期报告")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期报告失败: {str(e)}")
            return 0
    
    def _create_environment_data(self, project_id: Optional[int] = None) -> Dict[str, str]:
        """创建环境信息"""
        environment_data = {
            "Test.Framework": "TestManager",
            "Python.Version": "3.9+",
            "Report.Generator": "Allure",
            "Generation.Time": datetime.now().isoformat(),
            "System.OS": os.name,
            "System.Platform": os.uname().sysname if hasattr(os, 'uname') else 'Unknown'
        }
        
        if project_id:
            environment_data["Project.ID"] = str(project_id)
        
        # 添加配置中的环境信息
        if hasattr(self.settings, 'TEST_ENVIRONMENT'):
            environment_data["Test.Environment"] = self.settings.TEST_ENVIRONMENT
        
        return environment_data
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0
    
    async def add_test_execution_annotation(
        self,
        test_case_id: str,
        annotations: Dict[str, Any]
    ) -> bool:
        """为测试执行添加Allure注解"""
        try:
            # 这个方法用于在测试执行过程中添加Allure注解
            # 实际实现需要与测试执行引擎集成
            
            logger.debug(f"为测试用例 {test_case_id} 添加Allure注解: {annotations}")
            
            # 存储注解信息，供后续报告生成使用
            # 这里可以存储到数据库或缓存中
            
            return True
            
        except Exception as e:
            logger.error(f"添加Allure注解失败: {str(e)}")
            return False
    
    def create_sample_test_data(self) -> List[TestExecutionData]:
        """创建示例测试数据"""
        now = datetime.now()
        
        sample_data = [
            TestExecutionData(
                test_case_id="TC001",
                test_name="用户登录功能测试",
                status="PASSED",
                start_time=now,
                end_time=now,
                description="验证用户能够正常登录系统",
                labels={
                    "severity": "critical",
                    "feature": "登录功能",
                    "story": "用户认证",
                    "owner": "测试团队"
                },
                links=[
                    {
                        "name": "需求文档",
                        "url": "https://example.com/requirement/login",
                        "type": "tms"
                    }
                ]
            ),
            TestExecutionData(
                test_case_id="TC002",
                test_name="密码错误登录测试",
                status="FAILED",
                start_time=now,
                end_time=now,
                description="验证密码错误时的处理",
                error_message="登录失败：密码错误",
                error_trace="AssertionError: Expected login to fail but succeeded",
                labels={
                    "severity": "normal",
                    "feature": "登录功能",
                    "story": "错误处理"
                }
            ),
            TestExecutionData(
                test_case_id="TC003",
                test_name="用户注销功能测试",
                status="SKIPPED",
                start_time=now,
                end_time=now,
                description="验证用户注销功能",
                labels={
                    "severity": "minor",
                    "feature": "注销功能"
                }
            )
        ]
        
        return sample_data


# 全局Allure管理器实例
_allure_manager: Optional[AllureManager] = None


def get_allure_manager() -> AllureManager:
    """获取Allure管理器实例"""
    global _allure_manager
    if _allure_manager is None:
        _allure_manager = AllureManager()
    return _allure_manager


async def initialize_allure_manager(config: Optional[AllureReportConfig] = None) -> AllureManager:
    """初始化Allure管理器"""
    global _allure_manager
    _allure_manager = AllureManager(config)
    
    # 执行初始化清理
    await _allure_manager.cleanup_old_reports()
    
    return _allure_manager


# 导出主要类和函数
__all__ = [
    "AllureManager",
    "AllureReportConfig", 
    "TestExecutionData",
    "AllureReportResult",
    "get_allure_manager",
    "initialize_allure_manager"
]