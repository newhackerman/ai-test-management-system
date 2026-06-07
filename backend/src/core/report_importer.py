"""
报告导入解析器

支持导入PDF、HTML、Word、Excel等格式的外部测试报告
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

import pandas as pd
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document
import openpyxl
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


class ImportFormat(Enum):
    """导入格式枚举"""
    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"


class ReportSourceType(Enum):
    """报告来源类型"""
    ALLURE = "allure"
    JUNIT = "junit"
    TESTNG = "testng"
    PYTEST = "pytest"
    SELENIUM = "selenium"
    POSTMAN = "postman"
    JMETER = "jmeter"
    CUSTOM = "custom"


@dataclass
class ImportedTestResult:
    """导入的测试结果"""
    test_name: str
    status: str  # PASSED, FAILED, SKIPPED
    duration: Optional[float] = None
    error_message: Optional[str] = None
    test_suite: Optional[str] = None
    test_class: Optional[str] = None
    timestamp: Optional[datetime] = None
    attachments: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ImportedReport:
    """导入的报告"""
    import_id: str
    file_name: str
    file_type: ImportFormat
    source_type: ReportSourceType
    report_title: Optional[str] = None
    test_results: Optional[List[ImportedTestResult]] = None
    summary_stats: Optional[Dict[str, Any]] = None
    raw_content: Optional[str] = None
    tables_data: Optional[List[List[List[str]]]] = None
    excel_data: Optional[Dict[str, pd.DataFrame]] = None
    metadata: Optional[Dict[str, Any]] = None
    import_time: datetime = None
    
    def __post_init__(self):
        if self.import_time is None:
            self.import_time = datetime.now()


class BaseReportParser(ABC):
    """报告解析器基类"""
    
    @abstractmethod
    async def parse_report(self, file_path: str, source_type: ReportSourceType) -> ImportedReport:
        """解析报告文件"""
        pass
    
    def _extract_test_results_from_text(self, text: str, source_type: ReportSourceType) -> List[ImportedTestResult]:
        """从文本中提取测试结果"""
        results = []
        
        if source_type == ReportSourceType.JUNIT:
            results.extend(self._parse_junit_text(text))
        elif source_type == ReportSourceType.TESTNG:
            results.extend(self._parse_testng_text(text))
        elif source_type == ReportSourceType.PYTEST:
            results.extend(self._parse_pytest_text(text))
        elif source_type == ReportSourceType.ALLURE:
            results.extend(self._parse_allure_text(text))
        else:
            results.extend(self._parse_generic_text(text))
        
        return results
    
    def _parse_junit_text(self, text: str) -> List[ImportedTestResult]:
        """解析JUnit格式文本"""
        results = []
        
        # JUnit测试结果模式
        patterns = [
            r'Test\s+(\w+)\s*:\s*(PASSED|FAILED|SKIPPED)',
            r'(\w+)\s*\.\.\.\s*(PASSED|FAILED|SKIPPED)',
            r'✓\s*(\w+)',  # 通过
            r'✗\s*(\w+)',  # 失败
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    test_name = match.group(1)
                    status = match.group(2).upper()
                else:
                    test_name = match.group(1)
                    status = "PASSED" if "✓" in match.group(0) else "FAILED"
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status
                ))
        
        return results
    
    def _parse_testng_text(self, text: str) -> List[ImportedTestResult]:
        """解析TestNG格式文本"""
        results = []
        
        # TestNG测试结果模式
        patterns = [
            r'PASSED:\s*(\w+)',
            r'FAILED:\s*(\w+)',
            r'SKIPPED:\s*(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                status = match.group(0).split(':')[0].upper()
                test_name = match.group(1)
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status
                ))
        
        return results
    
    def _parse_pytest_text(self, text: str) -> List[ImportedTestResult]:
        """解析Pytest格式文本"""
        results = []
        
        # Pytest测试结果模式
        patterns = [
            r'(\w+\.py)::\w+\s*PASSED',
            r'(\w+\.py)::\w+\s*FAILED',
            r'(\w+\.py)::\w+\s*SKIPPED',
            r'test_(\w+)\s*\.\.\.\s*(PASSED|FAILED|SKIPPED)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if '::' in match.group(0):
                    test_name = match.group(1)
                    status = match.group(0).split()[-1].upper()
                else:
                    test_name = f"test_{match.group(1)}"
                    status = match.group(2).upper()
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status
                ))
        
        return results
    
    def _parse_allure_text(self, text: str) -> List[ImportedTestResult]:
        """解析Allure格式文本"""
        results = []
        
        # Allure测试结果模式
        patterns = [
            r'Test\s+(\w+)\s+(\w+)\s+in\s+([\d.]+)s',
            r'(\w+)\s*\|\s*(passed|failed|broken|skipped)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 3:
                    test_name = match.group(1)
                    status = match.group(2).upper()
                    duration = float(match.group(3)) if match.group(3) else None
                else:
                    test_name = match.group(1)
                    status = match.group(2).upper()
                    duration = None
                
                # 状态映射
                if status in ['BROKEN']:
                    status = 'FAILED'
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status,
                    duration=duration
                ))
        
        return results
    
    def _parse_generic_text(self, text: str) -> List[ImportedTestResult]:
        """解析通用格式文本"""
        results = []
        
        # 通用测试结果模式
        patterns = [
            r'(\w+)\s*:\s*(pass|fail|skip|success|error)',
            r'Test\s+(\w+)\s*:\s*(pass|fail|skip|success|error)',
            r'(\w+)\s+(通过|失败|跳过|成功|错误)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                test_name = match.group(1)
                status_text = match.group(2).lower()
                
                # 状态映射
                if status_text in ['pass', 'success', '通过', '成功']:
                    status = 'PASSED'
                elif status_text in ['fail', 'error', '失败', '错误']:
                    status = 'FAILED'
                else:
                    status = 'SKIPPED'
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status
                ))
        
        return results
    
    def _calculate_summary_stats(self, test_results: List[ImportedTestResult]) -> Dict[str, Any]:
        """计算摘要统计"""
        if not test_results:
            return {}
        
        total = len(test_results)
        passed = sum(1 for r in test_results if r.status == 'PASSED')
        failed = sum(1 for r in test_results if r.status == 'FAILED')
        skipped = sum(1 for r in test_results if r.status == 'SKIPPED')
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # 计算总执行时间
        total_duration = sum(r.duration for r in test_results if r.duration)
        
        return {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': failed,
            'skipped_tests': skipped,
            'pass_rate': round(pass_rate, 2),
            'total_duration': total_duration
        }


class PDFReportParser(BaseReportParser):
    """PDF报告解析器"""
    
    async def parse_report(self, file_path: str, source_type: ReportSourceType) -> ImportedReport:
        """解析PDF测试报告"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = ""
                
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            
            # 提取测试结果
            test_results = self._extract_test_results_from_text(text_content, source_type)
            
            # 计算摘要统计
            summary_stats = self._calculate_summary_stats(test_results)
            
            # 提取报告标题
            title_match = re.search(r'^(.+?)(?:\n|$)', text_content.strip())
            report_title = title_match.group(1) if title_match else "PDF测试报告"
            
            return ImportedReport(
                import_id=str(uuid.uuid4()),
                file_name=os.path.basename(file_path),
                file_type=ImportFormat.PDF,
                source_type=source_type,
                report_title=report_title,
                test_results=test_results,
                summary_stats=summary_stats,
                raw_content=text_content
            )
            
        except Exception as e:
            logger.error(f"解析PDF报告失败: {e}")
            raise


class HTMLReportParser(BaseReportParser):
    """HTML报告解析器"""
    
    async def parse_report(self, file_path: str, source_type: ReportSourceType) -> ImportedReport:
        """解析HTML测试报告"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 根据不同报告类型解析
            if source_type == ReportSourceType.ALLURE:
                test_results = self._parse_allure_html(soup)
            elif source_type == ReportSourceType.JUNIT:
                test_results = self._parse_junit_html(soup)
            else:
                test_results = self._parse_generic_html(soup)
            
            # 计算摘要统计
            summary_stats = self._calculate_summary_stats(test_results)
            
            # 提取报告标题
            title_element = soup.find('title') or soup.find('h1') or soup.find('h2')
            report_title = title_element.get_text().strip() if title_element else "HTML测试报告"
            
            return ImportedReport(
                import_id=str(uuid.uuid4()),
                file_name=os.path.basename(file_path),
                file_type=ImportFormat.HTML,
                source_type=source_type,
                report_title=report_title,
                test_results=test_results,
                summary_stats=summary_stats,
                raw_content=html_content
            )
            
        except Exception as e:
            logger.error(f"解析HTML报告失败: {e}")
            raise
    
    def _parse_allure_html(self, soup: BeautifulSoup) -> List[ImportedTestResult]:
        """解析Allure HTML报告"""
        results = []
        
        # 查找测试结果表格或列表
        test_elements = soup.find_all(['tr', 'div'], class_=re.compile(r'test|result'))
        
        for element in test_elements:
            try:
                # 提取测试名称
                name_element = element.find(['td', 'span', 'div'], class_=re.compile(r'name|title'))
                if not name_element:
                    continue
                
                test_name = name_element.get_text().strip()
                
                # 提取状态
                status_element = element.find(['td', 'span', 'div'], class_=re.compile(r'status|result'))
                if status_element:
                    status_text = status_element.get_text().strip().upper()
                    if 'PASS' in status_text:
                        status = 'PASSED'
                    elif 'FAIL' in status_text or 'BROKEN' in status_text:
                        status = 'FAILED'
                    else:
                        status = 'SKIPPED'
                else:
                    status = 'UNKNOWN'
                
                # 提取执行时间
                duration_element = element.find(['td', 'span'], class_=re.compile(r'duration|time'))
                duration = None
                if duration_element:
                    duration_text = duration_element.get_text().strip()
                    duration_match = re.search(r'([\d.]+)', duration_text)
                    if duration_match:
                        duration = float(duration_match.group(1))
                
                results.append(ImportedTestResult(
                    test_name=test_name,
                    status=status,
                    duration=duration
                ))
                
            except Exception as e:
                logger.warning(f"解析测试元素失败: {e}")
                continue
        
        return results
    
    def _parse_junit_html(self, soup: BeautifulSoup) -> List[ImportedTestResult]:
        """解析JUnit HTML报告"""
        results = []
        
        # 查找测试结果表格
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    test_name = cells[0].get_text().strip()
                    status_text = cells[1].get_text().strip().upper()
                    
                    if 'PASS' in status_text or 'SUCCESS' in status_text:
                        status = 'PASSED'
                    elif 'FAIL' in status_text or 'ERROR' in status_text:
                        status = 'FAILED'
                    else:
                        status = 'SKIPPED'
                    
                    results.append(ImportedTestResult(
                        test_name=test_name,
                        status=status
                    ))
        
        return results
    
    def _parse_generic_html(self, soup: BeautifulSoup) -> List[ImportedTestResult]:
        """解析通用HTML报告"""
        results = []
        
        # 提取所有文本并使用通用解析
        text_content = soup.get_text()
        return self._extract_test_results_from_text(text_content, ReportSourceType.CUSTOM)


class WordReportParser(BaseReportParser):
    """Word报告解析器"""
    
    async def parse_report(self, file_path: str, source_type: ReportSourceType) -> ImportedReport:
        """解析Word测试报告"""
        try:
            doc = Document(file_path)
            text_content = ""
            tables_data = []
            
            # 提取文本内容
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            # 提取表格数据
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                tables_data.append(table_data)
            
            # 从表格中提取测试结果
            test_results = self._extract_test_results_from_tables(tables_data)
            
            # 如果表格中没有找到结果，从文本中提取
            if not test_results:
                test_results = self._extract_test_results_from_text(text_content, source_type)
            
            # 计算摘要统计
            summary_stats = self._calculate_summary_stats(test_results)
            
            # 提取报告标题（通常是第一个段落）
            report_title = doc.paragraphs[0].text.strip() if doc.paragraphs else "Word测试报告"
            
            return ImportedReport(
                import_id=str(uuid.uuid4()),
                file_name=os.path.basename(file_path),
                file_type=ImportFormat.DOCX,
                source_type=source_type,
                report_title=report_title,
                test_results=test_results,
                summary_stats=summary_stats,
                raw_content=text_content,
                tables_data=tables_data
            )
            
        except Exception as e:
            logger.error(f"解析Word报告失败: {e}")
            raise
    
    def _extract_test_results_from_tables(self, tables_data: List[List[List[str]]]) -> List[ImportedTestResult]:
        """从表格数据中提取测试结果"""
        results = []
        
        for table_data in tables_data:
            if len(table_data) < 2:  # 至少需要表头和一行数据
                continue
            
            headers = [h.lower() for h in table_data[0]]
            
            # 查找相关列
            name_col = None
            status_col = None
            duration_col = None
            
            for i, header in enumerate(headers):
                if any(keyword in header for keyword in ['name', 'test', '测试', '用例']):
                    name_col = i
                elif any(keyword in header for keyword in ['status', 'result', '状态', '结果']):
                    status_col = i
                elif any(keyword in header for keyword in ['time', 'duration', '时间', '耗时']):
                    duration_col = i
            
            if name_col is not None and status_col is not None:
                for row in table_data[1:]:
                    if len(row) > max(name_col, status_col):
                        test_name = row[name_col].strip()
                        status_text = row[status_col].strip().lower()
                        
                        # 状态映射
                        if any(keyword in status_text for keyword in ['pass', 'success', '通过', '成功']):
                            status = 'PASSED'
                        elif any(keyword in status_text for keyword in ['fail', 'error', '失败', '错误']):
                            status = 'FAILED'
                        else:
                            status = 'SKIPPED'
                        
                        # 提取执行时间
                        duration = None
                        if duration_col is not None and len(row) > duration_col:
                            duration_text = row[duration_col].strip()
                            duration_match = re.search(r'([\d.]+)', duration_text)
                            if duration_match:
                                duration = float(duration_match.group(1))
                        
                        results.append(ImportedTestResult(
                            test_name=test_name,
                            status=status,
                            duration=duration
                        ))
        
        return results


class ExcelReportParser(BaseReportParser):
    """Excel报告解析器"""
    
    async def parse_report(self, file_path: str, source_type: ReportSourceType) -> ImportedReport:
        """解析Excel测试报告"""
        try:
            # 读取所有工作表
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            test_results = []
            
            # 从每个工作表中提取测试结果
            for sheet_name, df in excel_data.items():
                sheet_results = self._parse_excel_sheet(df, sheet_name)
                test_results.extend(sheet_results)
            
            # 计算摘要统计
            summary_stats = self._calculate_summary_stats(test_results)
            
            # 提取报告标题
            first_sheet = list(excel_data.values())[0] if excel_data else pd.DataFrame()
            report_title = f"Excel测试报告 - {list(excel_data.keys())[0]}" if excel_data else "Excel测试报告"
            
            return ImportedReport(
                import_id=str(uuid.uuid4()),
                file_name=os.path.basename(file_path),
                file_type=ImportFormat.XLSX,
                source_type=source_type,
                report_title=report_title,
                test_results=test_results,
                summary_stats=summary_stats,
                excel_data=excel_data
            )
            
        except Exception as e:
            logger.error(f"解析Excel报告失败: {e}")
            raise
    
    def _parse_excel_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[ImportedTestResult]:
        """解析Excel工作表"""
        results = []
        
        if df.empty:
            return results
        
        # 查找相关列
        columns = [col.lower() for col in df.columns]
        name_col = None
        status_col = None
        duration_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['name', 'test', '测试', '用例']):
                name_col = col
            elif any(keyword in col_lower for keyword in ['status', 'result', '状态', '结果']):
                status_col = col
            elif any(keyword in col_lower for keyword in ['time', 'duration', '时间', '耗时']):
                duration_col = col
        
        if name_col and status_col:
            for _, row in df.iterrows():
                try:
                    test_name = str(row[name_col]).strip()
                    status_text = str(row[status_col]).strip().lower()
                    
                    # 跳过空行或标题行
                    if not test_name or test_name.lower() in ['nan', 'name', 'test']:
                        continue
                    
                    # 状态映射
                    if any(keyword in status_text for keyword in ['pass', 'success', '通过', '成功']):
                        status = 'PASSED'
                    elif any(keyword in status_text for keyword in ['fail', 'error', '失败', '错误']):
                        status = 'FAILED'
                    else:
                        status = 'SKIPPED'
                    
                    # 提取执行时间
                    duration = None
                    if duration_col and duration_col in row:
                        try:
                            duration = float(row[duration_col])
                        except:
                            pass
                    
                    results.append(ImportedTestResult(
                        test_name=test_name,
                        status=status,
                        duration=duration,
                        test_suite=sheet_name
                    ))
                    
                except Exception as e:
                    logger.warning(f"解析Excel行失败: {e}")
                    continue
        
        return results


class ReportImporter:
    """报告导入管理器"""
    
    def __init__(self, import_dir: str = "imported_reports"):
        self.import_dir = Path(import_dir)
        self.import_dir.mkdir(exist_ok=True)
        
        # 初始化解析器
        self.parsers = {
            ImportFormat.PDF: PDFReportParser(),
            ImportFormat.HTML: HTMLReportParser(),
            ImportFormat.DOCX: WordReportParser(),
            ImportFormat.XLSX: ExcelReportParser()
        }
    
    async def import_report(
        self,
        file_path: str,
        source_type: ReportSourceType = ReportSourceType.CUSTOM
    ) -> ImportedReport:
        """
        导入外部测试报告
        
        Args:
            file_path: 报告文件路径
            source_type: 报告来源类型
            
        Returns:
            ImportedReport: 导入的报告对象
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"报告文件不存在: {file_path}")
            
            # 确定文件格式
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            
            try:
                format_type = ImportFormat(file_ext)
            except ValueError:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 获取对应的解析器
            parser = self.parsers.get(format_type)
            if not parser:
                raise ValueError(f"没有找到 {format_type.value} 格式的解析器")
            
            # 解析报告
            imported_report = await parser.parse_report(file_path, source_type)
            
            # 保存导入记录
            await self._save_import_record(imported_report, file_path)
            
            logger.info(f"成功导入报告: {file_path}")
            return imported_report
            
        except Exception as e:
            logger.error(f"导入报告失败: {e}")
            raise
    
    async def _save_import_record(self, imported_report: ImportedReport, original_path: str):
        """保存导入记录"""
        try:
            # 创建导入记录目录
            import_record_dir = self.import_dir / imported_report.import_id
            import_record_dir.mkdir(exist_ok=True)
            
            # 保存元数据
            metadata = {
                'import_id': imported_report.import_id,
                'original_file_path': original_path,
                'file_name': imported_report.file_name,
                'file_type': imported_report.file_type.value,
                'source_type': imported_report.source_type.value,
                'report_title': imported_report.report_title,
                'import_time': imported_report.import_time.isoformat(),
                'summary_stats': imported_report.summary_stats,
                'test_results_count': len(imported_report.test_results) if imported_report.test_results else 0
            }
            
            metadata_path = import_record_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 保存测试结果
            if imported_report.test_results:
                results_data = []
                for result in imported_report.test_results:
                    results_data.append({
                        'test_name': result.test_name,
                        'status': result.status,
                        'duration': result.duration,
                        'error_message': result.error_message,
                        'test_suite': result.test_suite,
                        'test_class': result.test_class,
                        'timestamp': result.timestamp.isoformat() if result.timestamp else None,
                        'attachments': result.attachments,
                        'metadata': result.metadata
                    })
                
                results_path = import_record_dir / "test_results.json"
                with open(results_path, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            # 保存原始内容（如果有）
            if imported_report.raw_content:
                content_path = import_record_dir / "raw_content.txt"
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(imported_report.raw_content)
            
        except Exception as e:
            logger.error(f"保存导入记录失败: {e}")
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return [format_type.value for format_type in ImportFormat]
    
    def get_supported_source_types(self) -> List[str]:
        """获取支持的报告来源类型"""
        return [source_type.value for source_type in ReportSourceType]
    
    async def list_imported_reports(self) -> List[Dict[str, Any]]:
        """列出所有导入的报告"""
        reports = []
        
        try:
            for import_dir in self.import_dir.iterdir():
                if import_dir.is_dir():
                    metadata_path = import_dir / "metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            reports.append(metadata)
        except Exception as e:
            logger.error(f"列出导入报告失败: {e}")
        
        return reports
    
    async def get_imported_report(self, import_id: str) -> Optional[ImportedReport]:
        """获取导入的报告详情"""
        try:
            import_record_dir = self.import_dir / import_id
            if not import_record_dir.exists():
                return None
            
            # 读取元数据
            metadata_path = import_record_dir / "metadata.json"
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 读取测试结果
            test_results = []
            results_path = import_record_dir / "test_results.json"
            if results_path.exists():
                with open(results_path, 'r', encoding='utf-8') as f:
                    results_data = json.load(f)
                    
                for result_data in results_data:
                    test_results.append(ImportedTestResult(
                        test_name=result_data['test_name'],
                        status=result_data['status'],
                        duration=result_data.get('duration'),
                        error_message=result_data.get('error_message'),
                        test_suite=result_data.get('test_suite'),
                        test_class=result_data.get('test_class'),
                        timestamp=datetime.fromisoformat(result_data['timestamp']) if result_data.get('timestamp') else None,
                        attachments=result_data.get('attachments'),
                        metadata=result_data.get('metadata')
                    ))
            
            # 读取原始内容
            raw_content = None
            content_path = import_record_dir / "raw_content.txt"
            if content_path.exists():
                with open(content_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
            
            return ImportedReport(
                import_id=metadata['import_id'],
                file_name=metadata['file_name'],
                file_type=ImportFormat(metadata['file_type']),
                source_type=ReportSourceType(metadata['source_type']),
                report_title=metadata.get('report_title'),
                test_results=test_results,
                summary_stats=metadata.get('summary_stats'),
                raw_content=raw_content,
                import_time=datetime.fromisoformat(metadata['import_time'])
            )
            
        except Exception as e:
            logger.error(f"获取导入报告失败: {e}")
            return None


def get_report_importer() -> ReportImporter:
    """获取报告导入器实例"""
    return ReportImporter()