"""
报告导出API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import io

from ....core.security import get_current_user
from ....services.report_service import ReportService, get_report_service

router = APIRouter()

class ExportRequest(BaseModel):
    """导出请求模型"""
    report_type: str
    format: str  # pdf, excel, csv, json
    data_range: Optional[str] = "current"
    project_ids: Optional[List[int]] = None
    filters: Optional[Dict[str, Any]] = None

@router.post("/export")
async def export_report(
    request: ExportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
):
    """导出报告"""
    try:
        # 支持的报告类型
        supported_types = [
            "dashboard_summary", "project_overview", "requirement_analysis",
            "test_report", "quality_metrics", "performance_report"
        ]
        
        if request.report_type not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的报告类型。支持的类型: {', '.join(supported_types)}"
            )
        
        # 支持的格式
        supported_formats = ["pdf", "excel", "csv", "json"]
        if request.format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式。支持的格式: {', '.join(supported_formats)}"
            )
        
        # 生成报告
        report_data = await report_service.generate_report(
            report_type=request.report_type,
            user_id=current_user["id"],
            project_ids=request.project_ids,
            data_range=request.data_range,
            filters=request.filters
        )
        
        # 导出报告
        file_content, filename, media_type = await report_service.export_report(
            report_data=report_data,
            format=request.format,
            report_type=request.report_type
        )
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出报告失败: {str(e)}")

@router.get("/templates")
async def get_report_templates(
    current_user: Dict[str, Any] = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service)
):
    """获取报告模板列表"""
    try:
        templates = await report_service.get_report_templates(current_user["id"])
        return {"templates": templates}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告模板失败: {str(e)}")