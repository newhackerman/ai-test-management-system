"""
报告服务

提供通用的报告生成和导出功能
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import Depends

from .test_report_service import TestReportService
from .requirement_report_service import RequirementReportService
from ..core.database import get_db

logger = logging.getLogger(__name__)


class ReportService:
    """通用报告服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.test_report_service = TestReportService(db)
        self.requirement_report_service = RequirementReportService(db)
    
    async def generate_report(self, report_type: str, **kwargs) -> Dict[str, Any]:
        """
        生成报告
        
        Args:
            report_type: 报告类型
            **kwargs: 报告参数
            
        Returns:
            Dict[str, Any]: 报告数据
        """
        try:
            if report_type == "test":
                return await self.test_report_service.generate_comprehensive_report(**kwargs)
            elif report_type == "requirement":
                return await self.requirement_report_service.generate_report(**kwargs)
            else:
                raise ValueError(f"Unsupported report type: {report_type}")
                
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            raise
    
    async def export_report(self, report_data: Dict[str, Any], format: str, report_type: Optional[str] = None) -> tuple:
        """
        导出报告

        Args:
            report_data: 报告数据
            format: 导出格式 (pdf, excel, csv, json)
            report_type: 报告类型 (可选，用于生成文件名)

        Returns:
            tuple: (file_content: bytes, filename: str, media_type: str)
        """
        try:
            media_types = {
                "pdf": "application/pdf",
                "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "csv": "text/csv",
                "json": "application/json",
            }
            ext_map = {"pdf": "pdf", "excel": "xlsx", "csv": "csv", "json": "json"}
            ext = ext_map.get(format, format)
            type_prefix = report_type or "report"
            filename = f"{type_prefix}_export.{ext}"
            media_type = media_types.get(format, "application/octet-stream")

            if format == "json":
                import json
                content = json.dumps(report_data, ensure_ascii=False, indent=2, default=str).encode('utf-8')
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                if isinstance(report_data, dict) and 'data' in report_data:
                    data = report_data['data']
                    if isinstance(data, list) and data:
                        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
                        writer.writeheader()
                        writer.writerows(data)
                elif isinstance(report_data, list) and report_data:
                    writer = csv.DictWriter(output, fieldnames=list(report_data[0].keys()))
                    writer.writeheader()
                    writer.writerows(report_data)
                content = output.getvalue().encode('utf-8')
            else:
                raise ValueError(f"Unsupported export format: {format}")

            return content, filename, media_type

        except Exception as e:
            logger.error(f"导出报告失败: {str(e)}")
            raise

    async def get_report_templates(self, user_id: Optional[int] = None, *args, **kwargs) -> List[Dict[str, Any]]:
        """获取报告模板列表

        历史上调用方有两种签名：
          - dashboard route: get_report_templates(current_user["id"])  → 单参数 user_id
          - test_reports route: get_report_templates(filters, page, page_size)  → 三参数

        为兼容两者，本方法签名宽松：第一个位置参数若为 int 视为 user_id；
        否则忽略多余参数。返回内置静态模板清单，避免依赖未初始化的子服务。
        """
        # 兼容：若调用方传入的是 dict 形式 filters，则忽略其结构，仍走静态清单
        templates = [
            {
                "id": "dashboard_summary",
                "name": "仪表盘摘要",
                "description": "整体仪表盘关键指标摘要",
                "report_type": "dashboard_summary",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
            {
                "id": "project_overview",
                "name": "项目概览",
                "description": "项目级质量与进度概览",
                "report_type": "project_overview",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
            {
                "id": "requirement_analysis",
                "name": "需求分析",
                "description": "需求覆盖率与变更影响分析",
                "report_type": "requirement_analysis",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
            {
                "id": "test_report",
                "name": "测试报告",
                "description": "测试执行情况汇总",
                "report_type": "test_report",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
            {
                "id": "quality_metrics",
                "name": "质量指标",
                "description": "质量度量与趋势",
                "report_type": "quality_metrics",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
            {
                "id": "performance_report",
                "name": "性能报告",
                "description": "性能测试结果汇总",
                "report_type": "performance_report",
                "supported_formats": ["pdf", "excel", "csv", "json"],
            },
        ]
        # 若传了 filters/page/page_size 也做最简单的过滤，但不抛错
        filters = kwargs.get('filters')
        if isinstance(filters, dict):
            report_type = filters.get('template_type') or filters.get('report_type')
            if report_type:
                templates = [t for t in templates if t['report_type'] == report_type]
        page = kwargs.get('page', 1)
        page_size = kwargs.get('page_size', 50)
        if isinstance(page, int) and isinstance(page_size, int) and page_size > 0:
            start = (max(1, page) - 1) * page_size
            templates = templates[start:start + page_size]
        return templates


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """
    获取报告服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        ReportService: 报告服务实例
    """
    return ReportService(db)


