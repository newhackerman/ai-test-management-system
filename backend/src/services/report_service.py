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
    
    async def export_report(self, report_data: Dict[str, Any], format: str) -> bytes:
        """
        导出报告
        
        Args:
            report_data: 报告数据
            format: 导出格式 (pdf, excel, csv, json)
            
        Returns:
            bytes: 导出的报告数据
        """
        try:
            if format == "json":
                import json
                return json.dumps(report_data, ensure_ascii=False, indent=2).encode('utf-8')
            elif format == "csv":
                # 简化的CSV导出
                import csv
                import io
                output = io.StringIO()
                if isinstance(report_data, dict) and 'data' in report_data:
                    data = report_data['data']
                    if isinstance(data, list) and data:
                        writer = csv.DictWriter(output, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                return output.getvalue().encode('utf-8')
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"导出报告失败: {str(e)}")
            raise


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """
    获取报告服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        ReportService: 报告服务实例
    """
    return ReportService(db)


