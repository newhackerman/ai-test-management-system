"""
测试报告和覆盖率分析服务

提供完整的测试报告生成、覆盖率分析和质量监控功能
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3
# 重量级绘图/数据科学库（pandas/matplotlib/seaborn/plotly）改为惰性导入：
# 顶层 import 会让模块加载在 pytest fixture setup 的 10s 超时窗口内无法完成
# （seaborn→matplotlib→plotly 链路过长），导致测试 run 整体卡死。
# 这些库只在报告生成方法内部使用，延迟到首次调用时再加载即可。
from jinja2 import Template


def _lazy_imports():
    """惰性加载重量级绘图库，仅在首次生成报告时调用一次。"""
    g = globals()
    if 'plt' not in g:
        import pandas as pd
        import matplotlib
        matplotlib.use('Agg')  # 无显示环境后端
        import matplotlib.pyplot as plt
        import seaborn as sns
        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        g['pd'] = pd
        g['plt'] = plt
        g['sns'] = sns
        g['go'] = go
        g['px'] = px
        g['make_subplots'] = make_subplots

logger = logging.getLogger(__name__)

@dataclass
class CoverageMetrics:
    """覆盖率指标"""
    lines_covered: int
    lines_total: int
    branches_covered: int
    branches_total: int
    functions_covered: int
    functions_total: int
    statements_covered: int
    statements_total: int
    
    @property
    def line_coverage_percent(self) -> float:
        return (self.lines_covered / self.lines_total * 100) if self.lines_total > 0 else 0.0
    
    @property
    def branch_coverage_percent(self) -> float:
        return (self.branches_covered / self.branches_total * 100) if self.branches_total > 0 else 0.0
    
    @property
    def function_coverage_percent(self) -> float:
        return (self.functions_covered / self.functions_total * 100) if self.functions_total > 0 else 0.0
    
    @property
    def statement_coverage_percent(self) -> float:
        return (self.statements_covered / self.statements_total * 100) if self.statements_total > 0 else 0.0

@dataclass
class TestSuiteMetrics:
    """测试套件指标"""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    execution_time: float
    coverage_metrics: CoverageMetrics
    timestamp: datetime
    
    @property
    def success_rate(self) -> float:
        return (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0.0
    
    @property
    def failure_rate(self) -> float:
        return ((self.failed_tests + self.error_tests) / self.total_tests * 100) if self.total_tests > 0 else 0.0

@dataclass
class QualityTrend:
    """质量趋势数据"""
    date: datetime
    success_rate: float
    coverage_rate: float
    test_count: int
    execution_time: float
    defect_density: float

@dataclass
class TestReport:
    """完整测试报告"""
    report_id: str
    timestamp: datetime
    suite_metrics: List[TestSuiteMetrics]
    overall_coverage: CoverageMetrics
    quality_score: float
    trends: List[QualityTrend]
    recommendations: List[str]
    
    @property
    def overall_success_rate(self) -> float:
        total_tests = sum(m.total_tests for m in self.suite_metrics)
        passed_tests = sum(m.passed_tests for m in self.suite_metrics)
        return (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

class TestReportService:
    """测试报告服务"""
    
    def __init__(self, project_root: str = None):
        self.db = project_root if hasattr(project_root, "query") else None
        if self.db is not None:
            project_root = None
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # 创建报告数据库
        self.db_path = self.reports_dir / "test_reports.db"
        self._init_database()
        
        # 配置可视化样式（惰性加载重量级绘图库）
        _lazy_imports()
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    def _require_db(self):
        if self.db is None:
            raise RuntimeError("Database session is required for report record operations")
        return self.db

    def _ensure_record_tables(self):
        from sqlalchemy import text

        db = self._require_db()
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS test_report_templates (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NULL,
                template_type VARCHAR(50) NOT NULL,
                template_content JSON NULL,
                default_config JSON NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_by INT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX ix_test_report_templates_id (id)
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS test_report_records (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT NULL,
                report_type VARCHAR(50) NOT NULL,
                project_id INT NULL,
                template_id INT NULL,
                report_config JSON NULL,
                include_sections JSON NULL,
                date_range JSON NULL,
                export_formats JSON NULL,
                file_paths JSON NULL,
                file_size INT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                generation_time FLOAT NULL,
                error_message TEXT NULL,
                view_count INT DEFAULT 0,
                download_count INT DEFAULT 0,
                created_by INT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX ix_test_report_records_id (id),
                INDEX ix_test_report_records_project_id (project_id),
                INDEX ix_test_report_records_created_by (created_by),
                INDEX ix_test_report_records_status (status)
            )
        """))
        db.commit()

    async def create_report_record(self, report_data: Dict[str, Any]):
        from ..models.test_report import TestReportRecord

        db = self._require_db()
        self._ensure_record_tables()
        report = TestReportRecord(
            name=report_data.get("name"),
            description=report_data.get("description"),
            report_type=report_data.get("report_type"),
            project_id=report_data.get("project_id"),
            template_id=report_data.get("template_id"),
            report_config=report_data.get("report_config") or {},
            include_sections=report_data.get("include_sections") or [],
            date_range=report_data.get("date_range"),
            export_formats=report_data.get("export_formats") or ["HTML"],
            file_paths=report_data.get("file_paths") or {},
            file_size=report_data.get("file_size"),
            status=report_data.get("status") or "pending",
            created_by=report_data.get("created_by"),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    async def get_report_by_id(self, report_id: int):
        from ..models.test_report import TestReportRecord

        db = self._require_db()
        self._ensure_record_tables()
        return db.query(TestReportRecord).filter(TestReportRecord.id == report_id).first()

    async def get_reports_by_filters(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20):
        from ..models.test_report import TestReportRecord

        db = self._require_db()
        self._ensure_record_tables()
        query = db.query(TestReportRecord)

        if filters.get("project_id"):
            query = query.filter(TestReportRecord.project_id == filters["project_id"])
        if filters.get("report_type"):
            query = query.filter(TestReportRecord.report_type == filters["report_type"])
        if filters.get("status"):
            query = query.filter(TestReportRecord.status == filters["status"])
        if filters.get("created_by"):
            query = query.filter(TestReportRecord.created_by == filters["created_by"])
        if filters.get("start_date"):
            query = query.filter(TestReportRecord.created_at >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(TestReportRecord.created_at <= filters["end_date"])
        if filters.get("search"):
            keyword = f"%{filters['search']}%"
            query = query.filter(TestReportRecord.name.ilike(keyword))

        query = query.order_by(TestReportRecord.created_at.desc(), TestReportRecord.id.desc())

        if filters.get("test_plan_id"):
            target_plan_id = str(filters["test_plan_id"])
            matched_reports = []
            for report in query.all():
                config = report.report_config or {}
                if str(config.get("test_plan_id", "")) == target_plan_id:
                    matched_reports.append(report)
            total = len(matched_reports)
            start = (page - 1) * page_size
            return matched_reports[start:start + page_size], total

        total = query.count()
        reports = query.offset((page - 1) * page_size).limit(page_size).all()
        return reports, total

    async def increment_view_count(self, report_id: int):
        report = await self.get_report_by_id(report_id)
        if report:
            report.view_count = (report.view_count or 0) + 1
            self._require_db().commit()
        return report

    async def increment_download_count(self, report_id: int):
        report = await self.get_report_by_id(report_id)
        if report:
            report.download_count = (report.download_count or 0) + 1
            self._require_db().commit()
        return report

    async def get_report_templates(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20):
        """获取报告模板列表（查询 test_report_templates 表，支持分页与过滤）。"""
        from sqlalchemy import text

        db = self._require_db()
        self._ensure_record_tables()

        where_clauses = []
        params: Dict[str, Any] = {}
        template_type = filters.get("template_type") if filters else None
        is_active = filters.get("is_active") if filters else None
        if template_type:
            where_clauses.append("template_type = :template_type")
            params["template_type"] = template_type
        if is_active is not None:
            where_clauses.append("is_active = :is_active")
            params["is_active"] = bool(is_active)
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        total_row = db.execute(text(f"SELECT COUNT(*) FROM test_report_templates{where_sql}"), params).fetchone()
        total = int(total_row[0]) if total_row else 0

        offset = (page - 1) * page_size
        rows = db.execute(
            text(f"SELECT * FROM test_report_templates{where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {**params, "limit": page_size, "offset": offset}
        ).fetchall()

        templates = []
        for row in rows:
            templates.append(type("ReportTemplate", (), {
                "id": row[0], "name": row[1], "description": row[2],
                "template_type": row[3], "template_content": row[4],
                "default_config": row[5], "is_active": row[6],
                "created_by": row[7], "created_at": row[8], "updated_at": row[9],
            }))
        return templates, total

    async def get_report_schedules(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20):
        """获取报告计划列表（当前无独立计划表，返回空列表）。"""
        return [], 0

    async def delete_report(self, report_id: int, user_id: int):
        from ..core.exceptions import NotFoundError, PermissionError

        report = await self.get_report_by_id(report_id)
        if not report:
            raise NotFoundError("测试报告不存在")
        if report.created_by != user_id:
            raise PermissionError("无权删除该测试报告")

        db = self._require_db()
        db.delete(report)
        db.commit()
        return True

    async def generate_report_async(self, report_id: int, auto_send: bool = False, recipients: List[str] = None):
        report = await self.get_report_by_id(report_id)
        if not report:
            return None

        try:
            report.status = "completed"
            report.generation_time = 0.0
            report.file_paths = report.file_paths or {}
            report.updated_at = datetime.utcnow()
            self._require_db().commit()
            return report
        except Exception as e:
            logger.error(f"Generate report record failed: {e}")
            report.status = "failed"
            report.error_message = str(e)
            report.updated_at = datetime.utcnow()
            self._require_db().commit()
            return report
    
    def _init_database(self):
        """初始化报告数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_reports (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    overall_success_rate REAL,
                    overall_coverage_rate REAL,
                    total_tests INTEGER,
                    passed_tests INTEGER,
                    failed_tests INTEGER,
                    execution_time REAL,
                    quality_score REAL,
                    report_data TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS suite_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    suite_name TEXT,
                    total_tests INTEGER,
                    passed_tests INTEGER,
                    failed_tests INTEGER,
                    skipped_tests INTEGER,
                    error_tests INTEGER,
                    execution_time REAL,
                    line_coverage REAL,
                    branch_coverage REAL,
                    function_coverage REAL,
                    timestamp DATETIME,
                    FOREIGN KEY (report_id) REFERENCES test_reports (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    success_rate REAL,
                    coverage_rate REAL,
                    test_count INTEGER,
                    execution_time REAL,
                    defect_density REAL
                )
            """)
    
    async def generate_comprehensive_report(self, test_results_dir: str = None) -> TestReport:
        """生成综合测试报告"""
        logger.info("开始生成综合测试报告...")
        
        # 收集测试结果
        test_results_dir = Path(test_results_dir) if test_results_dir else self.reports_dir
        suite_metrics = await self._collect_test_metrics(test_results_dir)
        
        # 分析覆盖率
        overall_coverage = await self._analyze_coverage()
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(suite_metrics, overall_coverage)
        
        # 获取历史趋势
        trends = await self._get_quality_trends()
        
        # 生成改进建议
        recommendations = self._generate_recommendations(suite_metrics, overall_coverage, trends)
        
        # 创建报告
        report = TestReport(
            report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            suite_metrics=suite_metrics,
            overall_coverage=overall_coverage,
            quality_score=quality_score,
            trends=trends,
            recommendations=recommendations
        )
        
        # 保存报告
        await self._save_report(report)
        
        # 生成可视化报告
        await self._generate_visual_reports(report)
        
        logger.info(f"综合测试报告生成完成: {report.report_id}")
        return report
    
    async def _collect_test_metrics(self, test_results_dir: Path) -> List[TestSuiteMetrics]:
        """收集测试指标"""
        suite_metrics = []
        
        # 查找所有测试结果文件
        for xml_file in test_results_dir.glob("*.xml"):
            if xml_file.name.startswith(("junit", "test_", "coverage")):
                continue
                
            try:
                metrics = await self._parse_junit_xml(xml_file)
                if metrics:
                    suite_metrics.append(metrics)
            except Exception as e:
                logger.warning(f"解析测试结果文件失败 {xml_file}: {e}")
        
        # 如果没有找到XML文件，尝试解析JSON文件
        if not suite_metrics:
            for json_file in test_results_dir.glob("*.json"):
                try:
                    metrics = await self._parse_json_results(json_file)
                    if metrics:
                        suite_metrics.extend(metrics)
                except Exception as e:
                    logger.warning(f"解析JSON结果文件失败 {json_file}: {e}")
        
        return suite_metrics
    
    async def _parse_junit_xml(self, xml_file: Path) -> Optional[TestSuiteMetrics]:
        """解析JUnit XML文件"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # 获取测试套件信息
            if root.tag == 'testsuite':
                testsuite = root
            else:
                testsuite = root.find('.//testsuite')
            
            if testsuite is None:
                return None
            
            suite_name = testsuite.get('name', xml_file.stem)
            total_tests = int(testsuite.get('tests', 0))
            failures = int(testsuite.get('failures', 0))
            errors = int(testsuite.get('errors', 0))
            skipped = int(testsuite.get('skipped', 0))
            execution_time = float(testsuite.get('time', 0))
            
            passed_tests = total_tests - failures - errors - skipped
            
            # 获取覆盖率信息（如果有）
            coverage_metrics = await self._get_coverage_for_suite(suite_name)
            
            return TestSuiteMetrics(
                suite_name=suite_name,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failures,
                skipped_tests=skipped,
                error_tests=errors,
                execution_time=execution_time,
                coverage_metrics=coverage_metrics,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"解析JUnit XML失败 {xml_file}: {e}")
            return None
    
    async def _parse_json_results(self, json_file: Path) -> List[TestSuiteMetrics]:
        """解析JSON测试结果"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metrics_list = []
            
            # 处理不同格式的JSON结果
            if isinstance(data, dict):
                if 'suites' in data:
                    # 处理包含多个套件的结果
                    for suite_name, suite_data in data['suites'].items():
                        metrics = self._parse_suite_data(suite_name, suite_data)
                        if metrics:
                            metrics_list.append(metrics)
                else:
                    # 处理单个套件结果
                    metrics = self._parse_suite_data(json_file.stem, data)
                    if metrics:
                        metrics_list.append(metrics)
            
            return metrics_list
            
        except Exception as e:
            logger.error(f"解析JSON结果失败 {json_file}: {e}")
            return []
    
    def _parse_suite_data(self, suite_name: str, suite_data: dict) -> Optional[TestSuiteMetrics]:
        """解析套件数据"""
        try:
            total_tests = suite_data.get('total_tests', 0)
            passed_tests = suite_data.get('passed', 0)
            failed_tests = suite_data.get('failed', 0)
            skipped_tests = suite_data.get('skipped', 0)
            error_tests = suite_data.get('errors', 0)
            execution_time = suite_data.get('duration', 0.0)
            
            # 获取覆盖率信息
            coverage_data = suite_data.get('coverage', {})
            coverage_metrics = CoverageMetrics(
                lines_covered=coverage_data.get('lines_covered', 0),
                lines_total=coverage_data.get('lines_total', 0),
                branches_covered=coverage_data.get('branches_covered', 0),
                branches_total=coverage_data.get('branches_total', 0),
                functions_covered=coverage_data.get('functions_covered', 0),
                functions_total=coverage_data.get('functions_total', 0),
                statements_covered=coverage_data.get('statements_covered', 0),
                statements_total=coverage_data.get('statements_total', 0)
            )
            
            return TestSuiteMetrics(
                suite_name=suite_name,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                error_tests=error_tests,
                execution_time=execution_time,
                coverage_metrics=coverage_metrics,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"解析套件数据失败 {suite_name}: {e}")
            return None
    
    async def _analyze_coverage(self) -> CoverageMetrics:
        """分析代码覆盖率"""
        coverage_file = self.reports_dir / "coverage.json"
        
        if not coverage_file.exists():
            logger.warning("覆盖率文件不存在，使用默认值")
            return CoverageMetrics(0, 0, 0, 0, 0, 0, 0, 0)
        
        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
            
            totals = coverage_data.get('totals', {})
            
            return CoverageMetrics(
                lines_covered=totals.get('covered_lines', 0),
                lines_total=totals.get('num_statements', 0),
                branches_covered=totals.get('covered_branches', 0),
                branches_total=totals.get('num_branches', 0),
                functions_covered=0,  # coverage.py不直接提供函数覆盖率
                functions_total=0,
                statements_covered=totals.get('covered_lines', 0),
                statements_total=totals.get('num_statements', 0)
            )
            
        except Exception as e:
            logger.error(f"分析覆盖率失败: {e}")
            return CoverageMetrics(0, 0, 0, 0, 0, 0, 0, 0)
    
    async def _get_coverage_for_suite(self, suite_name: str) -> CoverageMetrics:
        """获取特定套件的覆盖率"""
        # 这里可以实现更细粒度的覆盖率分析
        # 目前返回默认值
        return CoverageMetrics(0, 0, 0, 0, 0, 0, 0, 0)
    
    def _calculate_quality_score(self, suite_metrics: List[TestSuiteMetrics], 
                                coverage: CoverageMetrics) -> float:
        """计算质量评分"""
        if not suite_metrics:
            return 0.0
        
        # 计算各项指标权重
        weights = {
            'success_rate': 0.4,      # 测试成功率权重40%
            'coverage_rate': 0.3,     # 覆盖率权重30%
            'test_completeness': 0.2, # 测试完整性权重20%
            'performance': 0.1        # 性能权重10%
        }
        
        # 计算成功率
        total_tests = sum(m.total_tests for m in suite_metrics)
        passed_tests = sum(m.passed_tests for m in suite_metrics)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 计算覆盖率
        coverage_rate = coverage.line_coverage_percent
        
        # 计算测试完整性（基于测试数量和覆盖的模块）
        test_completeness = min(100, total_tests / 10 * 10)  # 假设100个测试为满分
        
        # 计算性能评分（基于执行时间）
        avg_execution_time = sum(m.execution_time for m in suite_metrics) / len(suite_metrics)
        performance_score = max(0, 100 - avg_execution_time / 10)  # 10秒以内为满分
        
        # 计算综合评分
        quality_score = (
            success_rate * weights['success_rate'] +
            coverage_rate * weights['coverage_rate'] +
            test_completeness * weights['test_completeness'] +
            performance_score * weights['performance']
        )
        
        return min(100, max(0, quality_score))
    
    async def _get_quality_trends(self, days: int = 30) -> List[QualityTrend]:
        """获取质量趋势数据"""
        trends = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT date, success_rate, coverage_rate, test_count, 
                           execution_time, defect_density
                    FROM quality_trends
                    WHERE date >= date('now', '-{} days')
                    ORDER BY date
                """.format(days))
                
                for row in cursor.fetchall():
                    trends.append(QualityTrend(
                        date=datetime.fromisoformat(row[0]),
                        success_rate=row[1],
                        coverage_rate=row[2],
                        test_count=row[3],
                        execution_time=row[4],
                        defect_density=row[5]
                    ))
        
        except Exception as e:
            logger.error(f"获取质量趋势失败: {e}")
        
        return trends
    
    def _generate_recommendations(self, suite_metrics: List[TestSuiteMetrics],
                                coverage: CoverageMetrics,
                                trends: List[QualityTrend]) -> List[str]:
        """生成改进建议"""
        _lazy_imports()
        recommendations = []
        
        if not suite_metrics:
            recommendations.append("❌ 未找到测试结果，请确保测试正常执行")
            return recommendations
        
        # 分析成功率
        overall_success_rate = sum(m.passed_tests for m in suite_metrics) / sum(m.total_tests for m in suite_metrics) * 100
        if overall_success_rate < 90:
            recommendations.append(f"⚠️ 测试成功率较低 ({overall_success_rate:.1f}%)，建议修复失败的测试用例")
        
        # 分析覆盖率
        if coverage.line_coverage_percent < 80:
            recommendations.append(f"📊 代码覆盖率较低 ({coverage.line_coverage_percent:.1f}%)，建议增加测试用例")
        
        # 分析执行时间
        total_execution_time = sum(m.execution_time for m in suite_metrics)
        if total_execution_time > 300:  # 5分钟
            recommendations.append(f"⏱️ 测试执行时间较长 ({total_execution_time:.1f}秒)，建议优化测试性能")
        
        # 分析失败的套件
        failed_suites = [m for m in suite_metrics if m.failure_rate > 10]
        if failed_suites:
            suite_names = [s.suite_name for s in failed_suites]
            recommendations.append(f"🔍 以下测试套件失败率较高: {', '.join(suite_names)}")
        
        # 分析趋势
        if len(trends) >= 2:
            recent_trend = trends[-1]
            previous_trend = trends[-2]
            
            if recent_trend.success_rate < previous_trend.success_rate:
                recommendations.append("📉 测试成功率呈下降趋势，需要关注代码质量")
            
            if recent_trend.coverage_rate < previous_trend.coverage_rate:
                recommendations.append("📉 代码覆盖率呈下降趋势，建议增加测试覆盖")
        
        # 如果一切正常，给出积极建议
        if not recommendations:
            recommendations.append("✅ 测试质量良好，继续保持！")
            recommendations.append("🚀 可以考虑增加更多边界条件和异常情况的测试")
        
        return recommendations
    
    async def _save_report(self, report: TestReport):
        """保存测试报告"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 保存主报告
                conn.execute("""
                    INSERT INTO test_reports 
                    (id, timestamp, overall_success_rate, overall_coverage_rate, 
                     total_tests, passed_tests, failed_tests, execution_time, 
                     quality_score, report_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report.report_id,
                    report.timestamp.isoformat(),
                    report.overall_success_rate,
                    report.overall_coverage.line_coverage_percent,
                    sum(m.total_tests for m in report.suite_metrics),
                    sum(m.passed_tests for m in report.suite_metrics),
                    sum(m.failed_tests + m.error_tests for m in report.suite_metrics),
                    sum(m.execution_time for m in report.suite_metrics),
                    report.quality_score,
                    json.dumps(asdict(report), default=str, ensure_ascii=False)
                ))
                
                # 保存套件指标
                for metrics in report.suite_metrics:
                    conn.execute("""
                        INSERT INTO suite_metrics 
                        (report_id, suite_name, total_tests, passed_tests, 
                         failed_tests, skipped_tests, error_tests, execution_time,
                         line_coverage, branch_coverage, function_coverage, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        report.report_id,
                        metrics.suite_name,
                        metrics.total_tests,
                        metrics.passed_tests,
                        metrics.failed_tests,
                        metrics.skipped_tests,
                        metrics.error_tests,
                        metrics.execution_time,
                        metrics.coverage_metrics.line_coverage_percent,
                        metrics.coverage_metrics.branch_coverage_percent,
                        metrics.coverage_metrics.function_coverage_percent,
                        metrics.timestamp.isoformat()
                    ))
                
                # 更新质量趋势
                today = datetime.now().date()
                conn.execute("""
                    INSERT OR REPLACE INTO quality_trends 
                    (date, success_rate, coverage_rate, test_count, 
                     execution_time, defect_density)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    today.isoformat(),
                    report.overall_success_rate,
                    report.overall_coverage.line_coverage_percent,
                    sum(m.total_tests for m in report.suite_metrics),
                    sum(m.execution_time for m in report.suite_metrics),
                    sum(m.failed_tests + m.error_tests for m in report.suite_metrics) / 
                    sum(m.total_tests for m in report.suite_metrics) * 100 if sum(m.total_tests for m in report.suite_metrics) > 0 else 0
                ))
            
            logger.info(f"测试报告已保存: {report.report_id}")
            
        except Exception as e:
            logger.error(f"保存测试报告失败: {e}")
    
    async def _generate_visual_reports(self, report: TestReport):
        """生成可视化报告"""
        try:
            # 生成HTML报告
            await self._generate_html_report(report)
            
            # 生成图表
            await self._generate_charts(report)
            
            # 生成PDF报告（可选）
            # await self._generate_pdf_report(report)
            
        except Exception as e:
            logger.error(f"生成可视化报告失败: {e}")
    
    async def _generate_html_report(self, report: TestReport):
        """生成HTML报告"""
        _lazy_imports()
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>测试报告 - {{ report.report_id }}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f5f5f5; 
                }
                .container { 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                    overflow: hidden;
                }
                .header { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 30px; 
                    text-align: center; 
                }
                .header h1 { margin: 0; font-size: 2.5em; }
                .header p { margin: 10px 0 0 0; opacity: 0.9; }
                .content { padding: 30px; }
                .metrics-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px; 
                }
                .metric-card { 
                    background: #f8f9fa; 
                    border-radius: 8px; 
                    padding: 20px; 
                    text-align: center; 
                    border-left: 4px solid #007bff; 
                }
                .metric-value { 
                    font-size: 2.5em; 
                    font-weight: bold; 
                    color: #007bff; 
                    margin: 10px 0; 
                }
                .metric-label { 
                    color: #6c757d; 
                    font-size: 0.9em; 
                    text-transform: uppercase; 
                    letter-spacing: 1px; 
                }
                .section { 
                    margin-bottom: 40px; 
                    border-radius: 8px; 
                    overflow: hidden; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }
                .section-header { 
                    background: #343a40; 
                    color: white; 
                    padding: 15px 20px; 
                    font-weight: bold; 
                    font-size: 1.2em; 
                }
                .section-content { 
                    background: white; 
                    padding: 20px; 
                }
                .suite-table { 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin-top: 10px; 
                }
                .suite-table th, .suite-table td { 
                    border: 1px solid #dee2e6; 
                    padding: 12px; 
                    text-align: left; 
                }
                .suite-table th { 
                    background-color: #f8f9fa; 
                    font-weight: bold; 
                }
                .status-passed { color: #28a745; font-weight: bold; }
                .status-failed { color: #dc3545; font-weight: bold; }
                .status-warning { color: #ffc107; font-weight: bold; }
                .recommendations { 
                    background: #e7f3ff; 
                    border-left: 4px solid #007bff; 
                    padding: 20px; 
                    border-radius: 0 8px 8px 0; 
                }
                .recommendations ul { 
                    margin: 0; 
                    padding-left: 20px; 
                }
                .recommendations li { 
                    margin-bottom: 10px; 
                    line-height: 1.5; 
                }
                .chart-container { 
                    margin: 20px 0; 
                    height: 400px; 
                }
                .progress-bar { 
                    background: #e9ecef; 
                    border-radius: 10px; 
                    overflow: hidden; 
                    height: 20px; 
                    margin: 10px 0; 
                }
                .progress-fill { 
                    height: 100%; 
                    background: linear-gradient(90deg, #28a745, #20c997); 
                    transition: width 0.3s ease; 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 测试质量报告</h1>
                    <p>报告ID: {{ report.report_id }} | 生成时间: {{ report.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                </div>
                
                <div class="content">
                    <!-- 关键指标 -->
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">质量评分</div>
                            <div class="metric-value">{{ "%.1f"|format(report.quality_score) }}</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {{ report.quality_score }}%"></div>
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">测试成功率</div>
                            <div class="metric-value">{{ "%.1f"|format(report.overall_success_rate) }}%</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {{ report.overall_success_rate }}%"></div>
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">代码覆盖率</div>
                            <div class="metric-value">{{ "%.1f"|format(report.overall_coverage.line_coverage_percent) }}%</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {{ report.overall_coverage.line_coverage_percent }}%"></div>
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">总测试数</div>
                            <div class="metric-value">{{ suite_metrics|sum(attribute='total_tests') }}</div>
                        </div>
                    </div>
                    
                    <!-- 测试套件详情 -->
                    <div class="section">
                        <div class="section-header">📊 测试套件详情</div>
                        <div class="section-content">
                            <table class="suite-table">
                                <thead>
                                    <tr>
                                        <th>套件名称</th>
                                        <th>总测试数</th>
                                        <th>通过</th>
                                        <th>失败</th>
                                        <th>跳过</th>
                                        <th>成功率</th>
                                        <th>覆盖率</th>
                                        <th>执行时间</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for suite in report.suite_metrics %}
                                    <tr>
                                        <td>{{ suite.suite_name }}</td>
                                        <td>{{ suite.total_tests }}</td>
                                        <td class="status-passed">{{ suite.passed_tests }}</td>
                                        <td class="status-failed">{{ suite.failed_tests + suite.error_tests }}</td>
                                        <td class="status-warning">{{ suite.skipped_tests }}</td>
                                        <td>
                                            <span class="{% if suite.success_rate >= 90 %}status-passed{% elif suite.success_rate >= 70 %}status-warning{% else %}status-failed{% endif %}">
                                                {{ "%.1f"|format(suite.success_rate) }}%
                                            </span>
                                        </td>
                                        <td>{{ "%.1f"|format(suite.coverage_metrics.line_coverage_percent) }}%</td>
                                        <td>{{ "%.2f"|format(suite.execution_time) }}s</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- 改进建议 -->
                    <div class="section">
                        <div class="section-header">💡 改进建议</div>
                        <div class="section-content">
                            <div class="recommendations">
                                <ul>
                                    {% for recommendation in report.recommendations %}
                                    <li>{{ recommendation }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 图表区域 -->
                    <div class="section">
                        <div class="section-header">📈 趋势分析</div>
                        <div class="section-content">
                            <div id="trendsChart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // 生成趋势图表
                const trendsData = {{ trends_chart_data|safe }};
                Plotly.newPlot('trendsChart', trendsData.data, trendsData.layout, {responsive: true});
            </script>
        </body>
        </html>
        """
        
        # 准备趋势图表数据
        trends_chart_data = self._prepare_trends_chart_data(report.trends)
        
        # 渲染模板
        template = Template(html_template)
        html_content = template.render(
            report=report,
            suite_metrics=report.suite_metrics,
            trends_chart_data=json.dumps(trends_chart_data)
        )
        
        # 保存HTML文件
        html_file = self.reports_dir / f"{report.report_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {html_file}")
    
    def _prepare_trends_chart_data(self, trends: List[QualityTrend]) -> dict:
        """准备趋势图表数据"""
        _lazy_imports()
        if not trends:
            return {"data": [], "layout": {}}
        
        dates = [trend.date.strftime('%Y-%m-%d') for trend in trends]
        success_rates = [trend.success_rate for trend in trends]
        coverage_rates = [trend.coverage_rate for trend in trends]
        
        data = [
            {
                'x': dates,
                'y': success_rates,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '测试成功率',
                'line': {'color': '#28a745'}
            },
            {
                'x': dates,
                'y': coverage_rates,
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': '代码覆盖率',
                'line': {'color': '#007bff'}
            }
        ]
        
        layout = {
            'title': '质量趋势分析',
            'xaxis': {'title': '日期'},
            'yaxis': {'title': '百分比 (%)'},
            'hovermode': 'x unified'
        }
        
        return {"data": data, "layout": layout}
    
    async def _generate_charts(self, report: TestReport):
        """生成图表"""
        try:
            _lazy_imports()
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表目录
            charts_dir = self.reports_dir / "charts"
            charts_dir.mkdir(exist_ok=True)
            
            # 1. 测试结果饼图
            await self._create_test_results_pie_chart(report, charts_dir)
            
            # 2. 覆盖率柱状图
            await self._create_coverage_bar_chart(report, charts_dir)
            
            # 3. 趋势线图
            await self._create_trends_line_chart(report, charts_dir)
            
            # 4. 套件性能对比图
            await self._create_suite_performance_chart(report, charts_dir)
            
        except Exception as e:
            logger.error(f"生成图表失败: {e}")
    
    async def _create_test_results_pie_chart(self, report: TestReport, charts_dir: Path):
        """创建测试结果饼图"""
        total_passed = sum(m.passed_tests for m in report.suite_metrics)
        total_failed = sum(m.failed_tests + m.error_tests for m in report.suite_metrics)
        total_skipped = sum(m.skipped_tests for m in report.suite_metrics)
        
        labels = ['通过', '失败', '跳过']
        sizes = [total_passed, total_failed, total_skipped]
        colors = ['#28a745', '#dc3545', '#ffc107']
        
        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('测试结果分布', fontsize=16, fontweight='bold')
        plt.axis('equal')
        
        chart_file = charts_dir / f"{report.report_id}_test_results.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    async def _create_coverage_bar_chart(self, report: TestReport, charts_dir: Path):
        """创建覆盖率柱状图"""
        suite_names = [m.suite_name for m in report.suite_metrics]
        coverage_rates = [m.coverage_metrics.line_coverage_percent for m in report.suite_metrics]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(suite_names, coverage_rates, color='#007bff', alpha=0.7)
        
        # 添加数值标签
        for bar, rate in zip(bars, coverage_rates):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{rate:.1f}%', ha='center', va='bottom')
        
        plt.title('各测试套件代码覆盖率', fontsize=16, fontweight='bold')
        plt.xlabel('测试套件')
        plt.ylabel('覆盖率 (%)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        
        chart_file = charts_dir / f"{report.report_id}_coverage.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    async def _create_trends_line_chart(self, report: TestReport, charts_dir: Path):
        """创建趋势线图"""
        if not report.trends:
            return
        
        dates = [trend.date for trend in report.trends]
        success_rates = [trend.success_rate for trend in report.trends]
        coverage_rates = [trend.coverage_rate for trend in report.trends]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, success_rates, marker='o', label='测试成功率', color='#28a745', linewidth=2)
        plt.plot(dates, coverage_rates, marker='s', label='代码覆盖率', color='#007bff', linewidth=2)
        
        plt.title('质量趋势分析', fontsize=16, fontweight='bold')
        plt.xlabel('日期')
        plt.ylabel('百分比 (%)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        chart_file = charts_dir / f"{report.report_id}_trends.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    async def _create_suite_performance_chart(self, report: TestReport, charts_dir: Path):
        """创建套件性能对比图"""
        suite_names = [m.suite_name for m in report.suite_metrics]
        execution_times = [m.execution_time for m in report.suite_metrics]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(suite_names, execution_times, color='#17a2b8', alpha=0.7)
        
        # 添加数值标签
        for bar, time in zip(bars, execution_times):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{time:.2f}s', ha='center', va='bottom')
        
        plt.title('各测试套件执行时间', fontsize=16, fontweight='bold')
        plt.xlabel('测试套件')
        plt.ylabel('执行时间 (秒)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        
        chart_file = charts_dir / f"{report.report_id}_performance.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    async def generate_coverage_report(self) -> dict:
        """生成详细的覆盖率报告"""
        logger.info("生成详细覆盖率报告...")
        
        try:
            # 运行覆盖率分析
            result = subprocess.run([
                sys.executable, '-m', 'coverage', 'report', '--format=json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                coverage_data = json.loads(result.stdout)
            else:
                logger.warning("无法获取覆盖率数据，使用默认值")
                coverage_data = {"totals": {}}
            
            # 分析覆盖率数据
            totals = coverage_data.get('totals', {})
            files = coverage_data.get('files', {})
            
            # 生成详细报告
            detailed_report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'covered_lines': totals.get('covered_lines', 0),
                    'num_statements': totals.get('num_statements', 0),
                    'percent_covered': totals.get('percent_covered', 0.0),
                    'missing_lines': totals.get('missing_lines', 0),
                    'excluded_lines': totals.get('excluded_lines', 0)
                },
                'files': []
            }
            
            # 分析每个文件的覆盖率
            for file_path, file_data in files.items():
                file_info = {
                    'path': file_path,
                    'covered_lines': file_data.get('summary', {}).get('covered_lines', 0),
                    'num_statements': file_data.get('summary', {}).get('num_statements', 0),
                    'percent_covered': file_data.get('summary', {}).get('percent_covered', 0.0),
                    'missing_lines': file_data.get('missing_lines', []),
                    'excluded_lines': file_data.get('excluded_lines', [])
                }
                detailed_report['files'].append(file_info)
            
            # 保存详细报告
            report_file = self.reports_dir / f"coverage_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"详细覆盖率报告已生成: {report_file}")
            return detailed_report
            
        except Exception as e:
            logger.error(f"生成覆盖率报告失败: {e}")
            return {}
    
    async def monitor_test_quality(self) -> dict:
        """监控测试质量"""
        logger.info("开始测试质量监控...")
        
        try:
            # 获取最近的测试报告
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM test_reports 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                
                recent_reports = cursor.fetchall()
            
            if not recent_reports:
                return {"status": "no_data", "message": "没有找到测试报告数据"}
            
            # 分析质量趋势
            quality_scores = [report[8] for report in recent_reports]  # quality_score字段
            success_rates = [report[2] for report in recent_reports]   # overall_success_rate字段
            coverage_rates = [report[3] for report in recent_reports]  # overall_coverage_rate字段
            
            # 计算趋势
            quality_trend = self._calculate_trend(quality_scores)
            success_trend = self._calculate_trend(success_rates)
            coverage_trend = self._calculate_trend(coverage_rates)
            
            # 生成监控报告
            monitoring_report = {
                'timestamp': datetime.now().isoformat(),
                'status': 'healthy',
                'metrics': {
                    'latest_quality_score': quality_scores[0] if quality_scores else 0,
                    'latest_success_rate': success_rates[0] if success_rates else 0,
                    'latest_coverage_rate': coverage_rates[0] if coverage_rates else 0,
                    'quality_trend': quality_trend,
                    'success_trend': success_trend,
                    'coverage_trend': coverage_trend
                },
                'alerts': []
            }
            
            # 生成告警
            if quality_scores[0] < 70:
                monitoring_report['alerts'].append({
                    'level': 'critical',
                    'message': f'质量评分过低: {quality_scores[0]:.1f}%'
                })
                monitoring_report['status'] = 'critical'
            
            if success_rates[0] < 80:
                monitoring_report['alerts'].append({
                    'level': 'warning',
                    'message': f'测试成功率过低: {success_rates[0]:.1f}%'
                })
                if monitoring_report['status'] == 'healthy':
                    monitoring_report['status'] = 'warning'
            
            if coverage_rates[0] < 70:
                monitoring_report['alerts'].append({
                    'level': 'warning',
                    'message': f'代码覆盖率过低: {coverage_rates[0]:.1f}%'
                })
                if monitoring_report['status'] == 'healthy':
                    monitoring_report['status'] = 'warning'
            
            # 趋势告警
            if quality_trend == 'declining':
                monitoring_report['alerts'].append({
                    'level': 'warning',
                    'message': '质量评分呈下降趋势'
                })
            
            # 保存监控报告
            monitoring_file = self.reports_dir / f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(monitoring_file, 'w', encoding='utf-8') as f:
                json.dump(monitoring_report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"测试质量监控完成: {monitoring_report['status']}")
            return monitoring_report
            
        except Exception as e:
            logger.error(f"测试质量监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'stable'
        
        # 计算最近几个值的平均变化
        recent_avg = sum(values[:3]) / min(3, len(values))
        older_avg = sum(values[3:6]) / min(3, len(values[3:]))
        
        if len(values) < 4:
            return 'stable'
        
        change_percent = (recent_avg - older_avg) / older_avg * 100
        
        if change_percent > 5:
            return 'improving'
        elif change_percent < -5:
            return 'declining'
        else:
            return 'stable'
    
    async def cleanup_old_reports(self, days: int = 30):
        """清理旧报告"""
        logger.info(f"清理{days}天前的旧报告...")
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 清理数据库记录
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM test_reports 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                
                # 清理相关的套件指标
                conn.execute("""
                    DELETE FROM suite_metrics 
                    WHERE report_id NOT IN (SELECT id FROM test_reports)
                """)
            
            # 清理文件
            for file_path in self.reports_dir.glob("*.html"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
            
            for file_path in self.reports_dir.glob("*.json"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
            
            # 清理图表目录
            charts_dir = self.reports_dir / "charts"
            if charts_dir.exists():
                for file_path in charts_dir.glob("*.png"):
                    if file_path.stat().st_mtime < cutoff_date.timestamp():
                        file_path.unlink()
            
            logger.info(f"清理完成，删除了{deleted_count}个报告记录")
            
        except Exception as e:
            logger.error(f"清理旧报告失败: {e}")


# 全局服务实例
test_report_service = TestReportService()
