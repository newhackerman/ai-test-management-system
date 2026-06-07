"""
报告生成管理器

提供多格式报告生成功能，支持HTML、PDF、Excel、JSON等格式
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from jinja2 import Environment, FileSystemLoader, Template
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot

# PDF生成相关导入
WEASYPRINT_AVAILABLE = False  # 在Windows环境下禁用WeasyPrint
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """报告格式枚举"""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"
    CSV = "csv"


class ReportType(Enum):
    """报告类型枚举"""
    TEST_EXECUTION = "test_execution"
    TEST_COVERAGE = "test_coverage"
    PERFORMANCE = "performance"
    SECURITY = "security"
    QUALITY_METRICS = "quality_metrics"
    PROJECT_SUMMARY = "project_summary"
    CUSTOM = "custom"


@dataclass
class ReportConfig:
    """报告配置"""
    report_id: str
    report_name: str
    report_type: ReportType
    template_name: Optional[str] = None
    include_charts: bool = True
    include_details: bool = True
    include_attachments: bool = False
    custom_fields: Optional[Dict[str, Any]] = None
    branding: Optional[Dict[str, str]] = None


@dataclass
class ReportData:
    """报告数据"""
    title: str
    summary: Dict[str, Any]
    sections: List[Dict[str, Any]]
    charts: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class GeneratedReport:
    """生成的报告"""
    report_id: str
    format: ReportFormat
    file_path: str
    file_size: int
    generation_time: float
    status: str = "completed"
    error_message: Optional[str] = None


class ReportGenerator:
    """报告生成管理器"""
    
    def __init__(self, output_dir: str = "reports", templates_dir: str = "templates"):
        self.output_dir = Path(output_dir)
        self.templates_dir = Path(templates_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        
        # 注册自定义过滤器
        self._register_filters()
    
    def _register_filters(self):
        """注册Jinja2自定义过滤器"""
        
        def percentage_filter(value, decimals=1):
            """百分比格式化"""
            if value is None:
                return "N/A"
            return f"{float(value):.{decimals}f}%"
        
        def datetime_format_filter(value, format='%Y-%m-%d %H:%M:%S'):
            """日期时间格式化"""
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    return value
            return value.strftime(format) if value else "N/A"
        
        def file_size_filter(value):
            """文件大小格式化"""
            if not value:
                return "0 B"
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if value < 1024.0:
                    return f"{value:.1f} {unit}"
                value /= 1024.0
            return f"{value:.1f} TB"
        
        # 注册过滤器
        self.jinja_env.filters['percentage'] = percentage_filter
        self.jinja_env.filters['datetime_format'] = datetime_format_filter
        self.jinja_env.filters['file_size'] = file_size_filter
    
    async def generate_report(
        self,
        config: ReportConfig,
        data: ReportData,
        formats: List[ReportFormat]
    ) -> List[GeneratedReport]:
        """
        生成多格式报告
        
        Args:
            config: 报告配置
            data: 报告数据
            formats: 输出格式列表
            
        Returns:
            List[GeneratedReport]: 生成的报告列表
        """
        start_time = datetime.now()
        generated_reports = []
        
        try:
            # 预处理数据
            processed_data = await self._preprocess_data(data, config)
            
            # 生成图表
            if config.include_charts and data.charts:
                chart_paths = await self._generate_charts(data.charts, config.report_id)
                processed_data['chart_paths'] = chart_paths
            
            # 为每种格式生成报告
            for format_type in formats:
                try:
                    report = await self._generate_single_format(
                        config, processed_data, format_type
                    )
                    generated_reports.append(report)
                    logger.info(f"成功生成 {format_type.value} 格式报告: {report.file_path}")
                    
                except Exception as e:
                    error_report = GeneratedReport(
                        report_id=config.report_id,
                        format=format_type,
                        file_path="",
                        file_size=0,
                        generation_time=(datetime.now() - start_time).total_seconds(),
                        status="failed",
                        error_message=str(e)
                    )
                    generated_reports.append(error_report)
                    logger.error(f"生成 {format_type.value} 格式报告失败: {e}")
            
            return generated_reports
            
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            raise
    
    async def _preprocess_data(self, data: ReportData, config: ReportConfig) -> Dict[str, Any]:
        """预处理报告数据"""
        processed = {
            'config': config,
            'title': data.title,
            'summary': data.summary,
            'sections': data.sections,
            'metadata': data.metadata or {},
            'generation_time': datetime.now(),
            'report_id': config.report_id
        }
        
        # 添加自定义字段
        if config.custom_fields:
            processed.update(config.custom_fields)
        
        # 添加品牌信息
        if config.branding:
            processed['branding'] = config.branding
        else:
            processed['branding'] = {
                'company_name': 'AI测试管理系统',
                'logo_url': '/static/logo.png'
            }
        
        return processed
    
    async def _generate_charts(self, charts_config: List[Dict[str, Any]], report_id: str) -> Dict[str, str]:
        """生成图表文件"""
        chart_paths = {}
        charts_dir = self.output_dir / "charts" / report_id
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        for i, chart_config in enumerate(charts_config):
            try:
                chart_type = chart_config.get('type', 'bar')
                chart_data = chart_config.get('data', {})
                chart_title = chart_config.get('title', f'Chart {i+1}')
                
                # 创建图表
                if chart_type == 'bar':
                    fig = px.bar(
                        x=chart_data.get('labels', []),
                        y=chart_data.get('values', []),
                        title=chart_title
                    )
                elif chart_type == 'pie':
                    fig = px.pie(
                        values=chart_data.get('values', []),
                        names=chart_data.get('labels', []),
                        title=chart_title
                    )
                elif chart_type == 'line':
                    fig = px.line(
                        x=chart_data.get('x', []),
                        y=chart_data.get('y', []),
                        title=chart_title
                    )
                else:
                    # 默认柱状图
                    fig = px.bar(
                        x=chart_data.get('labels', []),
                        y=chart_data.get('values', []),
                        title=chart_title
                    )
                
                # 保存图表
                chart_filename = f"chart_{i+1}.png"
                chart_path = charts_dir / chart_filename
                fig.write_image(str(chart_path), width=800, height=600)
                
                chart_paths[f'chart_{i+1}'] = str(chart_path)
                
            except Exception as e:
                logger.warning(f"生成图表 {i+1} 失败: {e}")
                continue
        
        return chart_paths
    
    async def _generate_single_format(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        format_type: ReportFormat
    ) -> GeneratedReport:
        """生成单一格式报告"""
        start_time = datetime.now()
        
        if format_type == ReportFormat.HTML:
            return await self._generate_html_report(config, data, start_time)
        elif format_type == ReportFormat.PDF:
            return await self._generate_pdf_report(config, data, start_time)
        elif format_type == ReportFormat.EXCEL:
            return await self._generate_excel_report(config, data, start_time)
        elif format_type == ReportFormat.JSON:
            return await self._generate_json_report(config, data, start_time)
        elif format_type == ReportFormat.CSV:
            return await self._generate_csv_report(config, data, start_time)
        else:
            raise ValueError(f"不支持的报告格式: {format_type}")
    
    async def _generate_html_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime
    ) -> GeneratedReport:
        """生成HTML报告"""
        try:
            # 选择模板
            template_name = config.template_name or f"{config.report_type.value}_report.html"
            
            try:
                template = self.jinja_env.get_template(template_name)
            except:
                # 使用默认模板
                template = self.jinja_env.get_template("default_report.html")
            
            # 渲染HTML
            html_content = template.render(**data)
            
            # 保存文件
            filename = f"{config.report_id}_{config.report_name}.html"
            file_path = self.output_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_size = file_path.stat().st_size
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return GeneratedReport(
                report_id=config.report_id,
                format=ReportFormat.HTML,
                file_path=str(file_path),
                file_size=file_size,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {e}")
            raise
    
    async def _generate_pdf_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime
    ) -> GeneratedReport:
        """生成PDF报告"""
        try:
            filename = f"{config.report_id}_{config.report_name}.pdf"
            pdf_path = self.output_dir / filename
            
            if WEASYPRINT_AVAILABLE:
                # 使用WeasyPrint生成PDF
                return await self._generate_pdf_with_weasyprint(config, data, start_time, pdf_path)
            elif REPORTLAB_AVAILABLE:
                # 使用ReportLab生成PDF
                return await self._generate_pdf_with_reportlab(config, data, start_time, pdf_path)
            else:
                # 如果都不可用，生成HTML作为替代
                logger.warning("PDF生成库不可用，将生成HTML格式作为替代")
                html_report = await self._generate_html_report(config, data, start_time)
                
                # 复制HTML文件并重命名为PDF扩展名（实际还是HTML）
                import shutil
                shutil.copy2(html_report.file_path, str(pdf_path.with_suffix('.html')))
                
                return GeneratedReport(
                    report_id=config.report_id,
                    format=ReportFormat.HTML,  # 实际格式
                    file_path=str(pdf_path.with_suffix('.html')),
                    file_size=Path(pdf_path.with_suffix('.html')).stat().st_size,
                    generation_time=(datetime.now() - start_time).total_seconds()
                )
            
        except Exception as e:
            logger.error(f"生成PDF报告失败: {e}")
            raise
    
    async def _generate_pdf_with_weasyprint(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime,
        pdf_path: Path
    ) -> GeneratedReport:
        """使用WeasyPrint生成PDF"""
        # 首先生成HTML
        html_report = await self._generate_html_report(config, data, start_time)
        
        # 使用weasyprint转换
        html_doc = HTML(filename=html_report.file_path)
        
        # 添加CSS样式
        css_content = """
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'Arial', sans-serif;
            font-size: 12px;
            line-height: 1.4;
        }
        .page-break {
            page-break-before: always;
        }
        """
        
        html_doc.write_pdf(
            str(pdf_path),
            stylesheets=[CSS(string=css_content)]
        )
        
        file_size = pdf_path.stat().st_size
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return GeneratedReport(
            report_id=config.report_id,
            format=ReportFormat.PDF,
            file_path=str(pdf_path),
            file_size=file_size,
            generation_time=generation_time
        )
    
    async def _generate_pdf_with_reportlab(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime,
        pdf_path: Path
    ) -> GeneratedReport:
        """使用ReportLab生成PDF"""
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # 标题
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph(data.get('title', '测试报告'), title_style))
        story.append(Spacer(1, 20))
        
        # 报告信息
        info_data = [
            ['报告ID', config.report_id],
            ['报告名称', config.report_name],
            ['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['报告类型', config.report_type.value]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # 摘要数据
        summary = data.get('summary', {})
        if summary:
            story.append(Paragraph('摘要信息', styles['Heading2']))
            story.append(Spacer(1, 10))
            
            summary_data = [['指标', '数值']]
            for key, value in summary.items():
                summary_data.append([str(key), str(value)])
            
            summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
        
        # 详细章节
        sections = data.get('sections', [])
        for section in sections:
            story.append(Paragraph(section.get('title', '详细信息'), styles['Heading2']))
            story.append(Spacer(1, 10))
            
            section_data = section.get('data', [])
            if section_data and isinstance(section_data, list) and len(section_data) > 0:
                if isinstance(section_data[0], dict):
                    # 表格数据
                    headers = list(section_data[0].keys())
                    table_data = [headers]
                    
                    for item in section_data:
                        row = [str(item.get(header, '')) for header in headers]
                        table_data.append(row)
                    
                    section_table = Table(table_data)
                    section_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(section_table)
                else:
                    # 文本数据
                    for item in section_data:
                        story.append(Paragraph(str(item), styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        # 生成PDF
        doc.build(story)
        
        file_size = pdf_path.stat().st_size
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return GeneratedReport(
            report_id=config.report_id,
            format=ReportFormat.PDF,
            file_path=str(pdf_path),
            file_size=file_size,
            generation_time=generation_time
        )
    
    async def _generate_excel_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime
    ) -> GeneratedReport:
        """生成Excel报告"""
        try:
            filename = f"{config.report_id}_{config.report_name}.xlsx"
            file_path = self.output_dir / filename
            
            wb = Workbook()
            
            # 删除默认工作表
            wb.remove(wb.active)
            
            # 创建摘要工作表
            summary_ws = wb.create_sheet("报告摘要")
            self._create_summary_sheet(summary_ws, data)
            
            # 创建详细数据工作表
            if config.include_details and data.get('sections'):
                for i, section in enumerate(data['sections']):
                    sheet_name = section.get('title', f'Section_{i+1}')[:31]  # Excel工作表名称限制
                    detail_ws = wb.create_sheet(sheet_name)
                    self._create_detail_sheet(detail_ws, section)
            
            # 保存文件
            wb.save(str(file_path))
            
            file_size = file_path.stat().st_size
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return GeneratedReport(
                report_id=config.report_id,
                format=ReportFormat.EXCEL,
                file_path=str(file_path),
                file_size=file_size,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"生成Excel报告失败: {e}")
            raise
    
    def _create_summary_sheet(self, ws, data: Dict[str, Any]):
        """创建Excel摘要工作表"""
        # 设置标题
        ws['A1'] = data.get('title', '测试报告')
        ws['A1'].font = Font(size=16, bold=True)
        
        # 基本信息
        row = 3
        ws[f'A{row}'] = '报告ID:'
        ws[f'B{row}'] = data.get('report_id', '')
        row += 1
        
        ws[f'A{row}'] = '生成时间:'
        ws[f'B{row}'] = data.get('generation_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        row += 2
        
        # 摘要数据
        summary = data.get('summary', {})
        if summary:
            ws[f'A{row}'] = '摘要信息'
            ws[f'A{row}'].font = Font(size=14, bold=True)
            row += 1
            
            for key, value in summary.items():
                ws[f'A{row}'] = str(key)
                ws[f'B{row}'] = str(value)
                row += 1
    
    def _create_detail_sheet(self, ws, section: Dict[str, Any]):
        """创建Excel详细数据工作表"""
        # 设置标题
        ws['A1'] = section.get('title', '详细数据')
        ws['A1'].font = Font(size=14, bold=True)
        
        # 添加数据
        data = section.get('data', [])
        if isinstance(data, list) and data:
            # 如果是字典列表，创建表格
            if isinstance(data[0], dict):
                headers = list(data[0].keys())
                
                # 写入表头
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=3, column=col, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                
                # 写入数据
                for row, item in enumerate(data, 4):
                    for col, header in enumerate(headers, 1):
                        ws.cell(row=row, column=col, value=str(item.get(header, '')))
        
        # 自动调整列宽
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    async def _generate_json_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime
    ) -> GeneratedReport:
        """生成JSON报告"""
        try:
            filename = f"{config.report_id}_{config.report_name}.json"
            file_path = self.output_dir / filename
            
            # 准备JSON数据
            json_data = {
                'report_info': {
                    'id': config.report_id,
                    'name': config.report_name,
                    'type': config.report_type.value,
                    'generated_at': datetime.now().isoformat(),
                    'generator': 'AI测试管理系统'
                },
                'summary': data.get('summary', {}),
                'sections': data.get('sections', []),
                'metadata': data.get('metadata', {})
            }
            
            # 保存JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
            
            file_size = file_path.stat().st_size
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return GeneratedReport(
                report_id=config.report_id,
                format=ReportFormat.JSON,
                file_path=str(file_path),
                file_size=file_size,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"生成JSON报告失败: {e}")
            raise
    
    async def _generate_csv_report(
        self,
        config: ReportConfig,
        data: Dict[str, Any],
        start_time: datetime
    ) -> GeneratedReport:
        """生成CSV报告"""
        try:
            filename = f"{config.report_id}_{config.report_name}.csv"
            file_path = self.output_dir / filename
            
            # 收集所有表格数据
            all_data = []
            
            # 添加摘要数据
            summary = data.get('summary', {})
            for key, value in summary.items():
                all_data.append({
                    'Section': 'Summary',
                    'Key': key,
                    'Value': str(value)
                })
            
            # 添加各部分数据
            sections = data.get('sections', [])
            for section in sections:
                section_title = section.get('title', 'Unknown')
                section_data = section.get('data', [])
                
                if isinstance(section_data, list):
                    for item in section_data:
                        if isinstance(item, dict):
                            for key, value in item.items():
                                all_data.append({
                                    'Section': section_title,
                                    'Key': key,
                                    'Value': str(value)
                                })
                        else:
                            all_data.append({
                                'Section': section_title,
                                'Key': 'Data',
                                'Value': str(item)
                            })
            
            # 创建DataFrame并保存
            if all_data:
                df = pd.DataFrame(all_data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                # 创建空CSV文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('Section,Key,Value\n')
            
            file_size = file_path.stat().st_size
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return GeneratedReport(
                report_id=config.report_id,
                format=ReportFormat.CSV,
                file_path=str(file_path),
                file_size=file_size,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"生成CSV报告失败: {e}")
            raise
    
    def create_sample_data(self) -> ReportData:
        """创建示例报告数据"""
        return ReportData(
            title="测试执行报告",
            summary={
                "总测试用例": 150,
                "通过用例": 142,
                "失败用例": 6,
                "跳过用例": 2,
                "通过率": 94.67,
                "执行时间": "2小时15分钟"
            },
            sections=[
                {
                    "title": "测试结果详情",
                    "data": [
                        {"模块": "用户管理", "总数": 45, "通过": 43, "失败": 2, "通过率": 95.56},
                        {"模块": "项目管理", "总数": 38, "通过": 36, "失败": 1, "通过率": 94.74},
                        {"模块": "测试管理", "总数": 42, "通过": 40, "失败": 2, "通过率": 95.24},
                        {"模块": "报告管理", "总数": 25, "通过": 23, "失败": 1, "通过率": 92.00}
                    ]
                }
            ],
            charts=[
                {
                    "type": "pie",
                    "title": "测试结果分布",
                    "data": {
                        "labels": ["通过", "失败", "跳过"],
                        "values": [142, 6, 2]
                    }
                },
                {
                    "type": "bar",
                    "title": "各模块通过率",
                    "data": {
                        "labels": ["用户管理", "项目管理", "测试管理", "报告管理"],
                        "values": [95.56, 94.74, 95.24, 92.00]
                    }
                }
            ],
            metadata={
                "project": "AI测试管理系统",
                "version": "1.0.0",
                "environment": "测试环境",
                "executor": "自动化测试"
            }
        )


def get_report_generator() -> ReportGenerator:
    """获取报告生成器实例"""
    return ReportGenerator()