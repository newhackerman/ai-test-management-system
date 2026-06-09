"""
澶氭牸寮忔姤鍛婄鐞咥PI

鎻愪緵鎶ュ憡鐢熸垚銆佸鍏ャ€佸鍑哄拰绠＄悊鐨勭粺涓€鎺ュ彛
"""

import os
import json
import logging
import html
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, Body, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError
from ...core.report_generator import (
    ReportGenerator, ReportConfig, ReportData, ReportFormat, ReportType, GeneratedReport
)
from ...core.report_importer import (
    ReportImporter, ReportSourceType, ImportedReport, ImportFormat
)
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])
security = HTTPBearer()


def _split_generated_report_file(file_path: Path) -> Dict[str, Any]:
    stem = file_path.stem
    parts = stem.split("_")

    if len(parts) >= 4 and parts[0] == "gen":
        report_id = "_".join(parts[:4])
        report_name = "_".join(parts[4:]) or stem
    elif len(parts) >= 3 and parts[0] == "demo":
        report_id = "_".join(parts[:3])
        report_name = "_".join(parts[3:]) or stem
    else:
        report_id = stem
        report_name = stem

    return {
        "id": report_id,
        "name": report_name,
        "format": file_path.suffix.lstrip(".").lower(),
        "size": file_path.stat().st_size,
        "created_at": datetime.fromtimestamp(file_path.stat().st_mtime),
    }


def _metadata_file(report_id: str) -> Path:
    return Path("reports") / f"{report_id}.metadata.json"


def _load_report_metadata(report_id: str) -> Dict[str, Any]:
    metadata_path = _metadata_file(report_id)
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"读取报告元数据失败 {metadata_path}: {exc}")
        return {}


def _save_report_metadata(report_id: str, metadata: Dict[str, Any]) -> None:
    metadata_path = _metadata_file(report_id)
    metadata_path.parent.mkdir(exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _list_generated_reports() -> List[Any]:
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return []

    supported_suffixes = {".html", ".pdf", ".xlsx", ".json", ".csv"}
    generated_reports: List[UnifiedReportResponse] = []

    for file_path in reports_dir.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in supported_suffixes:
            continue
        if file_path.name.endswith(".metadata.json"):
            continue

        info = _split_generated_report_file(file_path)
        metadata = _load_report_metadata(info["id"])
        generated_reports.append(UnifiedReportResponse(
            id=info["id"],
            name=metadata.get("report_name") or info["name"],
            type="generated",
            format=info["format"],
            size=info["size"],
            created_at=info["created_at"],
            status="completed",
            summary={
                "file_path": str(file_path),
                "report_type": metadata.get("report_type"),
                "business_report_type": metadata.get("business_report_type"),
                "test_plan_id": metadata.get("test_plan_id"),
                "source": metadata.get("source"),
                "formats": metadata.get("formats"),
            }
        ))

    return generated_reports


# 璇锋眰妯″紡
class GenerateReportRequest(BaseModel):
    """鐢熸垚鎶ュ憡璇锋眰"""
    report_name: str = Field(..., min_length=1, max_length=200, description="鎶ュ憡鍚嶇О")
    report_type: str = Field(..., description="鎶ュ憡绫诲瀷")
    formats: List[str] = Field(["html"], description="杈撳嚭鏍煎紡鍒楄〃")
    template_name: Optional[str] = Field(None, description="妯℃澘鍚嶇О")
    include_charts: bool = Field(True, description="鏄惁鍖呭惈鍥捐〃")
    include_details: bool = Field(True, description="鏄惁鍖呭惈璇︾粏淇℃伅")
    include_attachments: bool = Field(False, description="鏄惁鍖呭惈闄勪欢")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="custom fields")
    branding: Optional[Dict[str, str]] = Field(None, description="鍝佺墝淇℃伅")
    
    # 鎶ュ憡鏁版嵁
    title: str = Field(..., description="鎶ュ憡鏍囬")
    summary: Dict[str, Any] = Field(..., description="鎽樿鏁版嵁")
    sections: List[Dict[str, Any]] = Field(..., description="鎶ュ憡绔犺妭")
    charts: Optional[List[Dict[str, Any]]] = Field(None, description="鍥捐〃閰嶇疆")
    metadata: Optional[Dict[str, Any]] = Field(None, description="metadata")


class ImportReportRequest(BaseModel):
    """瀵煎叆鎶ュ憡璇锋眰"""
    source_type: str = Field("custom", description="鎶ュ憡鏉ユ簮绫诲瀷")
    project_id: Optional[int] = Field(None, description="鍏宠仈椤圭洰ID")
    description: Optional[str] = Field(None, description="瀵煎叆鎻忚堪")


class ReportTemplateRequest(BaseModel):
    """鎶ュ憡妯℃澘璇锋眰"""
    name: str = Field(..., min_length=1, max_length=100, description="妯℃澘鍚嶇О")
    description: Optional[str] = Field(None, description="妯℃澘鎻忚堪")
    template_type: str = Field(..., description="妯℃澘绫诲瀷")
    template_content: str = Field(..., description="妯℃澘鍐呭")
    is_active: bool = Field(True, description="active")


# 鍝嶅簲妯″紡
class GeneratedReportResponse(BaseModel):
    """鐢熸垚鎶ュ憡鍝嶅簲"""
    report_id: str = Field(..., description="鎶ュ憡ID")
    report_name: str = Field(..., description="鎶ュ憡鍚嶇О")
    formats: List[Dict[str, Any]] = Field(..., description="generated formats")
    generation_time: float = Field(..., description="鐢熸垚鑰楁椂(绉?")
    total_size: int = Field(..., description="鎬绘枃浠跺ぇ灏?瀛楄妭)")
    status: str = Field(..., description="status")
    created_at: datetime = Field(..., description="鍒涘缓鏃堕棿")


class ImportedReportResponse(BaseModel):
    """瀵煎叆鎶ュ憡鍝嶅簲"""
    import_id: str = Field(..., description="瀵煎叆ID")
    file_name: str = Field(..., description="file name")
    file_type: str = Field(..., description="鏂囦欢绫诲瀷")
    source_type: str = Field(..., description="鏉ユ簮绫诲瀷")
    report_title: Optional[str] = Field(None, description="鎶ュ憡鏍囬")
    summary_stats: Optional[Dict[str, Any]] = Field(None, description="鎽樿缁熻")
    test_results_count: int = Field(0, description="娴嬭瘯缁撴灉鏁伴噺")
    import_time: datetime = Field(..., description="瀵煎叆鏃堕棿")


class UnifiedReportResponse(BaseModel):
    """缁熶竴鎶ュ憡鍝嶅簲"""
    id: str = Field(..., description="鎶ュ憡ID")
    name: str = Field(..., description="鎶ュ憡鍚嶇О")
    type: str = Field(..., description="鎶ュ憡绫诲瀷")  # generated, imported
    format: str = Field(..., description="鏂囦欢鏍煎紡")
    size: int = Field(..., description="鏂囦欢澶у皬")
    created_at: datetime = Field(..., description="鍒涘缓鏃堕棿")
    status: str = Field(..., description="status")
    summary: Optional[Dict[str, Any]] = Field(None, description="鎽樿淇℃伅")


class AllureTestExecutionData(BaseModel):
    test_case_id: str = Field(..., description="测试用例ID")
    test_name: str = Field(..., description="测试名称")
    status: str = Field(..., description="执行状态")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    description: Optional[str] = Field(None, description="描述")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_trace: Optional[str] = Field(None, description="错误堆栈")
    steps: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="步骤")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="标签")
    links: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="链接")
    environment: Optional[str] = Field(None, description="执行环境")


class AllureReportFromDataRequest(BaseModel):
    report_name: str = Field(..., min_length=1, max_length=200, description="报告名称")
    test_executions: List[AllureTestExecutionData] = Field(..., min_items=1, description="测试执行数据")
    project_id: Optional[int] = Field(None, description="项目ID")
    suite_name: Optional[str] = Field(None, description="测试套件名称")
    auto_serve: bool = Field(False, description="是否自动生成访问地址")
    serve_port: Optional[int] = Field(None, description="服务端口")


class AllureReportResponse(BaseModel):
    report_id: str = Field(..., description="报告ID")
    report_name: str = Field(..., description="报告名称")
    report_path: str = Field(..., description="报告路径")
    report_url: Optional[str] = Field(None, description="报告访问地址")
    status: str = Field(..., description="状态")
    generation_time: float = Field(..., description="生成耗时")
    file_size: int = Field(..., description="文件大小")
    test_count: int = Field(..., description="测试数量")
    passed_count: int = Field(..., description="通过数量")
    failed_count: int = Field(..., description="失败数量")
    skipped_count: int = Field(..., description="跳过数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")


ALLURE_STORE_PATH = Path("data/allure_reports.json")
ALLURE_REPORT_DIR = Path("reports/allure")


def _load_allure_store() -> List[Dict[str, Any]]:
    if not ALLURE_STORE_PATH.exists():
        return []
    try:
        return json.loads(ALLURE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_allure_store(reports: List[Dict[str, Any]]) -> None:
    ALLURE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALLURE_STORE_PATH.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_allure_status(status: str) -> str:
    normalized = (status or "").upper()
    if normalized in {"PASSED", "PASS", "SUCCESS", "通过"}:
        return "PASSED"
    if normalized in {"FAILED", "FAIL", "ERROR", "BROKEN", "失败"}:
        return "FAILED"
    if normalized in {"SKIPPED", "SKIP", "跳过"}:
        return "SKIPPED"
    return "UNKNOWN"


def _render_allure_html(report_name: str, suite_name: Optional[str], executions: List[AllureTestExecutionData], created_at: datetime) -> str:
    rows = []
    passed = failed = skipped = 0
    for item in executions:
        status = _normalize_allure_status(item.status)
        passed += 1 if status == "PASSED" else 0
        failed += 1 if status == "FAILED" else 0
        skipped += 1 if status == "SKIPPED" else 0
        status_class = {"PASSED": "passed", "FAILED": "failed", "SKIPPED": "skipped"}.get(status, "unknown")
        labels = ", ".join(f"{key}: {value}" for key, value in (item.labels or {}).items())
        detail = item.error_message or item.description or ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.test_case_id)}</td>"
            f"<td>{html.escape(item.test_name)}</td>"
            f"<td><span class='status {status_class}'>{html.escape(status)}</span></td>"
            f"<td>{html.escape(item.environment or '-')}</td>"
            f"<td>{html.escape(labels or '-')}</td>"
            f"<td>{html.escape(detail or '-')}</td>"
            "</tr>"
        )

    total = len(executions)
    unknown = max(0, total - passed - failed - skipped)
    safe_title = html.escape(report_name)
    safe_suite = html.escape(suite_name or "未指定套件")
    generated = html.escape(created_at.strftime("%Y-%m-%d %H:%M:%S"))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; color: #172033; background: #f6f7fb; }}
    header {{ background: #111827; color: white; padding: 28px 40px; }}
    main {{ padding: 28px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .muted {{ color: #8ea0bc; }}
    .stats {{ display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 14px; margin: 24px 0; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, .04); }}
    .value {{ font-size: 26px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }}
    th, td {{ text-align: left; padding: 13px 14px; border-bottom: 1px solid #edf0f5; vertical-align: top; }}
    th {{ background: #f9fafb; color: #4b5563; font-size: 13px; }}
    .status {{ display: inline-block; min-width: 70px; border-radius: 999px; padding: 4px 9px; text-align: center; font-size: 12px; font-weight: 700; }}
    .passed {{ background: #dcfce7; color: #166534; }}
    .failed {{ background: #fee2e2; color: #991b1b; }}
    .skipped {{ background: #fef3c7; color: #92400e; }}
    .unknown {{ background: #e5e7eb; color: #374151; }}
  </style>
</head>
<body>
  <header>
    <h1>{safe_title}</h1>
    <div class="muted">套件：{safe_suite} · 生成时间：{generated}</div>
  </header>
  <main>
    <section class="stats">
      <div class="card"><div class="value">{total}</div><div class="muted">总用例</div></div>
      <div class="card"><div class="value">{passed}</div><div class="muted">通过</div></div>
      <div class="card"><div class="value">{failed}</div><div class="muted">失败</div></div>
      <div class="card"><div class="value">{skipped}</div><div class="muted">跳过</div></div>
      <div class="card"><div class="value">{unknown}</div><div class="muted">未知</div></div>
    </section>
    <table>
      <thead><tr><th>用例ID</th><th>测试名称</th><th>状态</th><th>环境</th><th>标签</th><th>说明</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>"""


# API鎺ュ彛瀹炵幇
@router.get("/allure", response_model=BaseResponse[List[AllureReportResponse]])
async def list_allure_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        reports = [AllureReportResponse(**item) for item in _load_allure_store()]
        reports.sort(key=lambda item: item.created_at, reverse=True)
        return BaseResponse(success=True, message="获取Allure报告列表成功", data=reports)
    except Exception as exc:
        logger.error(f"获取Allure报告列表失败: {exc}")
        raise HTTPException(status_code=500, detail="获取Allure报告列表失败")


@router.post("/allure/generate-from-data", response_model=BaseResponse[AllureReportResponse])
async def generate_allure_report_from_data(
    request: AllureReportFromDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    started_at = datetime.utcnow()
    try:
        report_id = f"allure_{started_at.strftime('%Y%m%d_%H%M%S')}_{current_user.id}_{uuid.uuid4().hex[:6]}"
        ALLURE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = ALLURE_REPORT_DIR / f"{report_id}.html"
        content = _render_allure_html(request.report_name, request.suite_name, request.test_executions, started_at)
        report_path.write_text(content, encoding="utf-8")

        statuses = [_normalize_allure_status(item.status) for item in request.test_executions]
        elapsed = round((datetime.utcnow() - started_at).total_seconds(), 3)
        report = {
            "report_id": report_id,
            "report_name": request.report_name,
            "report_path": str(report_path),
            "report_url": f"/api/v1/reports/allure/{report_id}/view",
            "status": "completed",
            "generation_time": elapsed,
            "file_size": report_path.stat().st_size,
            "test_count": len(request.test_executions),
            "passed_count": statuses.count("PASSED"),
            "failed_count": statuses.count("FAILED"),
            "skipped_count": statuses.count("SKIPPED"),
            "error_message": None,
            "created_at": started_at.isoformat(),
            "project_id": request.project_id,
            "suite_name": request.suite_name,
            "created_by": current_user.id,
        }
        reports = _load_allure_store()
        reports.append(report)
        _save_allure_store(reports)
        return BaseResponse(success=True, message="Allure报告生成成功", data=AllureReportResponse(**report))
    except Exception as exc:
        logger.error(f"生成Allure报告失败: {exc}")
        raise HTTPException(status_code=500, detail="生成Allure报告失败")


@router.get("/allure/{report_id}/view")
async def view_allure_report(
    report_id: str = PathParam(..., description="报告ID")
):
    reports = _load_allure_store()
    report = next((item for item in reports if item["report_id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Allure报告不存在")
    report_path = Path(report["report_path"])
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Allure报告文件不存在")
    return FileResponse(report_path, media_type="text/html; charset=utf-8")


@router.get("/allure/{report_id}", response_model=BaseResponse[AllureReportResponse])
async def get_allure_report(
    report_id: str = PathParam(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = next((item for item in _load_allure_store() if item["report_id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Allure报告不存在")
    return BaseResponse(success=True, message="获取Allure报告成功", data=AllureReportResponse(**report))


@router.post("/allure/{report_id}/serve", response_model=BaseResponse[Dict[str, str]])
async def serve_allure_report(
    report_id: str = PathParam(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = next((item for item in _load_allure_store() if item["report_id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Allure报告不存在")
    return BaseResponse(success=True, message="Allure报告访问地址已生成", data={"service_url": report["report_url"]})


@router.delete("/allure/{report_id}", response_model=BaseResponse[bool])
async def delete_allure_report(
    report_id: str = PathParam(..., description="报告ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reports = _load_allure_store()
    report = next((item for item in reports if item["report_id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Allure报告不存在")
    report_path = Path(report["report_path"])
    if report_path.exists():
        report_path.unlink()
    _save_allure_store([item for item in reports if item["report_id"] != report_id])
    return BaseResponse(success=True, message="Allure报告删除成功", data=True)


@router.post("/generate", response_model=BaseResponse[GeneratedReportResponse])
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鐢熸垚澶氭牸寮忔姤鍛?
    
    鏍规嵁鎻愪緵鐨勬暟鎹拰閰嶇疆鐢熸垚澶氱鏍煎紡鐨勬姤鍛?
    """
    try:
        generator = ReportGenerator()
        
        # 鍒涘缓鎶ュ憡閰嶇疆
        config = ReportConfig(
            report_id=f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_user.id}",
            report_name=request.report_name,
            report_type=ReportType(request.report_type),
            template_name=request.template_name,
            include_charts=request.include_charts,
            include_details=request.include_details,
            include_attachments=request.include_attachments,
            custom_fields=request.custom_fields,
            branding=request.branding
        )
        
        # 鍒涘缓鎶ュ憡鏁版嵁
        data = ReportData(
            title=request.title,
            summary=request.summary,
            sections=request.sections,
            charts=request.charts,
            metadata=request.metadata
        )
        
        # 杞崲鏍煎紡鍒楄〃
        formats = []
        for format_str in request.formats:
            try:
                formats.append(ReportFormat(format_str.lower()))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"涓嶆敮鎸佺殑鏍煎紡: {format_str}")
        
        # 鐢熸垚鎶ュ憡
        generated_reports = await generator.generate_report(config, data, formats)
        
        # 璁＄畻鎬诲ぇ灏忓拰鐘舵€?
        total_size = sum(r.file_size for r in generated_reports if r.status == "completed")
        total_time = max(r.generation_time for r in generated_reports)
        
        # 妫€鏌ユ槸鍚︽湁澶辫触鐨勬姤鍛?
        failed_reports = [r for r in generated_reports if r.status == "failed"]
        overall_status = "completed" if not failed_reports else "partial"
        
        # 鏋勫缓鏍煎紡鍒楄〃
        format_list = []
        for report in generated_reports:
            format_list.append({
                "format": report.format.value,
                "file_path": report.file_path,
                "file_size": report.file_size,
                "generation_time": report.generation_time,
                "status": report.status,
                "error_message": report.error_message
            })

        custom_fields = request.custom_fields or {}
        _save_report_metadata(config.report_id, {
            "report_id": config.report_id,
            "report_name": config.report_name,
            "report_type": request.report_type,
            "business_report_type": custom_fields.get("business_report_type") or request.report_type,
            "test_plan_id": custom_fields.get("test_plan_id"),
            "source": custom_fields.get("source") or request.summary.get("来源"),
            "formats": [item["format"] for item in format_list],
            "generated_by": current_user.id,
            "created_at": datetime.now().isoformat(),
        })
        
        response_data = GeneratedReportResponse(
            report_id=config.report_id,
            report_name=config.report_name,
            formats=format_list,
            generation_time=total_time,
            total_size=total_size,
            status=overall_status,
            created_at=datetime.now()
        )
        
        return BaseResponse(
            success=True,
            message="鎶ュ憡鐢熸垚瀹屾垚",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"鐢熸垚鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail=f"鐢熸垚鎶ュ憡澶辫触: {str(e)}")


@router.post("/import", response_model=BaseResponse[ImportedReportResponse])
async def import_report(
    file: UploadFile = File(..., description="鎶ュ憡鏂囦欢"),
    source_type: str = Form("custom", description="鎶ュ憡鏉ユ簮绫诲瀷"),
    project_id: Optional[int] = Form(None, description="鍏宠仈椤圭洰ID"),
    description: Optional[str] = Form(None, description="瀵煎叆鎻忚堪"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    瀵煎叆澶栭儴娴嬭瘯鎶ュ憡
    
    鏀寔瀵煎叆PDF銆丠TML銆乄ord銆丒xcel绛夋牸寮忕殑娴嬭瘯鎶ュ憡
    """
    try:
        importer = ReportImporter()
        
        # 楠岃瘉鏂囦欢鏍煎紡
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        if file_ext not in importer.get_supported_formats():
            raise HTTPException(
                status_code=400, 
                detail=f"涓嶆敮鎸佺殑鏂囦欢鏍煎紡: {file_ext}銆傛敮鎸佺殑鏍煎紡: {', '.join(importer.get_supported_formats())}"
            )
        
        # 楠岃瘉鏉ユ簮绫诲瀷
        if source_type not in importer.get_supported_source_types():
            raise HTTPException(
                status_code=400,
                detail=f"涓嶆敮鎸佺殑鏉ユ簮绫诲瀷: {source_type}銆傛敮鎸佺殑绫诲瀷: {', '.join(importer.get_supported_source_types())}"
            )
        
        # 淇濆瓨涓婁紶鐨勬枃浠?
        upload_dir = Path("temp_uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        try:
            # 瀵煎叆鎶ュ憡
            imported_report = await importer.import_report(
                str(file_path),
                ReportSourceType(source_type)
            )
            
            # 鏋勫缓鍝嶅簲
            response_data = ImportedReportResponse(
                import_id=imported_report.import_id,
                file_name=imported_report.file_name,
                file_type=imported_report.file_type.value,
                source_type=imported_report.source_type.value,
                report_title=imported_report.report_title,
                summary_stats=imported_report.summary_stats,
                test_results_count=len(imported_report.test_results) if imported_report.test_results else 0,
                import_time=imported_report.import_time
            )
            
            return BaseResponse(
                success=True,
                message="鎶ュ憡瀵煎叆鎴愬姛",
                data=response_data
            )
            
        finally:
            # 娓呯悊涓存椂鏂囦欢
            try:
                os.unlink(file_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"瀵煎叆鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail=f"瀵煎叆鎶ュ憡澶辫触: {str(e)}")


@router.get("/unified", response_model=PaginatedResponse[UnifiedReportResponse])
async def get_unified_reports(
    report_type: Optional[str] = Query(None, description="鎶ュ憡绫诲瀷杩囨护"),
    format_filter: Optional[str] = Query(None, description="鏍煎紡杩囨护"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    search: Optional[str] = Query(None, description="search keyword"),
    page: int = Query(1, ge=1, description="椤电爜"),
    page_size: int = Query(20, ge=1, le=100, description="姣忛〉澶у皬"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鑾峰彇缁熶竴鎶ュ憡瑙嗗浘
    
    鍖呭惈鐢熸垚鐨勬姤鍛婂拰瀵煎叆鐨勬姤鍛婄殑缁熶竴鍒楄〃
    """
    try:
        generator = ReportGenerator()
        importer = ReportImporter()
        
        unified_reports = []
        
        unified_reports.extend(_list_generated_reports())
        
        # 鑾峰彇瀵煎叆鐨勬姤鍛?
        imported_reports = await importer.list_imported_reports()
        
        for report in imported_reports:
            unified_reports.append(UnifiedReportResponse(
                id=report['import_id'],
                name=report['file_name'],
                type="imported",
                format=report['file_type'],
                size=0,  # 闇€瑕佷粠鏂囦欢绯荤粺鑾峰彇
                created_at=datetime.fromisoformat(report['import_time']),
                status="imported",
                summary=report.get('summary_stats')
            ))
        
        # 搴旂敤杩囨护鍣?
        if report_type:
            normalized_type = report_type.lower()
            unified_reports = [
                r for r in unified_reports
                if r.type == normalized_type
                or str((r.summary or {}).get("business_report_type") or "").lower() == normalized_type
                or str((r.summary or {}).get("report_type") or "").lower() == normalized_type
            ]
        
        if format_filter:
            unified_reports = [r for r in unified_reports if r.format == format_filter]

        if test_plan_id:
            unified_reports = [
                r for r in unified_reports
                if str((r.summary or {}).get("test_plan_id") or "") == str(test_plan_id)
            ]
        
        if search:
            unified_reports = [r for r in unified_reports if search.lower() in r.name.lower()]

        unified_reports.sort(key=lambda report: report.created_at, reverse=True)
        
        # 鍒嗛〉
        total = len(unified_reports)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_reports = unified_reports[start:end]
        
        return PaginatedResponse(
            success=True,
            message="鑾峰彇缁熶竴鎶ュ憡鍒楄〃鎴愬姛",
            data=paginated_reports,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"鑾峰彇缁熶竴鎶ュ憡鍒楄〃澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鑾峰彇鎶ュ憡鍒楄〃澶辫触")


@router.get("/imported", response_model=PaginatedResponse[Dict[str, Any]])
async def list_imported_reports(
    source_type: Optional[str] = Query(None, description="source type filter"),
    search: Optional[str] = Query(None, description="search keyword"),
    page: int = Query(1, ge=1, description="page"),
    page_size: int = Query(20, ge=1, le=100, description="page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        importer = ReportImporter()
        imported_reports = await importer.list_imported_reports()

        if source_type:
            imported_reports = [
                report for report in imported_reports
                if report.get("source_type") == source_type
            ]

        if search:
            keyword = search.lower()
            imported_reports = [
                report for report in imported_reports
                if keyword in report.get("file_name", "").lower()
                or keyword in report.get("report_title", "").lower()
            ]

        total = len(imported_reports)
        start = (page - 1) * page_size
        end = start + page_size

        return PaginatedResponse(
            success=True,
            message="閼惧嘲褰囩€电厧鍙嗛幎銉ユ啞閸掓銆冮幋鎰",
            data=imported_reports[start:end],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"閼惧嘲褰囩€电厧鍙嗛幎銉ユ啞閸掓銆冩径杈Е: {e}")
        raise HTTPException(status_code=500, detail="閼惧嘲褰囩€电厧鍙嗛幎銉ユ啞閸掓銆冩径杈Е")


@router.get("/imported/{import_id}", response_model=BaseResponse[ImportedReportResponse])
async def get_imported_report(
    import_id: str = PathParam(..., description="瀵煎叆ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鑾峰彇瀵煎叆鎶ュ憡璇︽儏
    
    鏍规嵁瀵煎叆ID鑾峰彇鎶ュ憡鐨勮缁嗕俊鎭?
    """
    try:
        importer = ReportImporter()
        
        imported_report = await importer.get_imported_report(import_id)
        if not imported_report:
            raise HTTPException(status_code=404, detail="imported report not found")
        
        response_data = ImportedReportResponse(
            import_id=imported_report.import_id,
            file_name=imported_report.file_name,
            file_type=imported_report.file_type.value,
            source_type=imported_report.source_type.value,
            report_title=imported_report.report_title,
            summary_stats=imported_report.summary_stats,
            test_results_count=len(imported_report.test_results) if imported_report.test_results else 0,
            import_time=imported_report.import_time
        )
        
        return BaseResponse(
            success=True,
            message="鑾峰彇瀵煎叆鎶ュ憡鎴愬姛",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"鑾峰彇瀵煎叆鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鑾峰彇鎶ュ憡璇︽儏澶辫触")


@router.get("/imported/{import_id}/test-results")
async def get_imported_report_test_results(
    import_id: str = PathParam(..., description="瀵煎叆ID"),
    page: int = Query(1, ge=1, description="椤电爜"),
    page_size: int = Query(50, ge=1, le=200, description="姣忛〉澶у皬"),
    status_filter: Optional[str] = Query(None, description="status filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鑾峰彇瀵煎叆鎶ュ憡鐨勬祴璇曠粨鏋?
    
    鍒嗛〉鑾峰彇瀵煎叆鎶ュ憡涓殑娴嬭瘯缁撴灉璇︽儏
    """
    try:
        importer = ReportImporter()
        
        imported_report = await importer.get_imported_report(import_id)
        if not imported_report:
            raise HTTPException(status_code=404, detail="imported report not found")
        
        test_results = imported_report.test_results or []
        
        # 搴旂敤鐘舵€佽繃婊?
        if status_filter:
            test_results = [r for r in test_results if r.status.upper() == status_filter.upper()]
        
        # 鍒嗛〉
        total = len(test_results)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = test_results[start:end]
        
        # 杞崲涓哄瓧鍏告牸寮?
        results_data = []
        for result in paginated_results:
            results_data.append({
                "test_name": result.test_name,
                "status": result.status,
                "duration": result.duration,
                "error_message": result.error_message,
                "test_suite": result.test_suite,
                "test_class": result.test_class,
                "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                "attachments": result.attachments,
                "metadata": result.metadata
            })
        
        return PaginatedResponse(
            success=True,
            message="鑾峰彇娴嬭瘯缁撴灉鎴愬姛",
            data=results_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"鑾峰彇娴嬭瘯缁撴灉澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鑾峰彇娴嬭瘯缁撴灉澶辫触")


@router.get("/download/{report_id}/{format}")
async def download_report(
    report_id: str = PathParam(..., description="鎶ュ憡ID"),
    format: str = PathParam(..., description="鏂囦欢鏍煎紡"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    涓嬭浇鎶ュ憡鏂囦欢
    
    涓嬭浇鎸囧畾鏍煎紡鐨勬姤鍛婃枃浠?
    """
    try:
        # 鏋勫缓鏂囦欢璺緞锛堣繖閲岄渶瑕佹牴鎹疄闄呭瓨鍌ㄦ柟寮忚皟鏁达級
        reports_dir = Path("reports")
        file_pattern = f"{report_id}_*.{format}"
        
        # 鏌ユ壘鍖归厤鐨勬枃浠?
        matching_files = list(reports_dir.glob(file_pattern))
        if not matching_files:
            exact_file = reports_dir / f"{report_id}.{format}"
            if exact_file.exists() and exact_file.is_file():
                matching_files = [exact_file]
        if not matching_files:
            matching_files = [
                path for path in reports_dir.glob(f"{report_id}*.{format}")
                if path.is_file()
            ]
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="report file not found")
        
        file_path = matching_files[0]
        
        # 纭畾MIME绫诲瀷
        mime_types = {
            'html': 'text/html',
            'pdf': 'application/pdf',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'json': 'application/json',
            'csv': 'text/csv'
        }
        
        media_type = mime_types.get(format, 'application/octet-stream')
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"涓嬭浇鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail="涓嬭浇鎶ュ憡澶辫触")


@router.post("/demo/generate", response_model=BaseResponse[GeneratedReportResponse])
async def generate_demo_report(
    formats: List[str] = Body(["html", "pdf"], description="杈撳嚭鏍煎紡"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鐢熸垚婕旂ず鎶ュ憡
    
    鐢熸垚鍖呭惈绀轰緥鏁版嵁鐨勬紨绀烘姤鍛婏紝鐢ㄤ簬鍔熻兘灞曠ず
    """
    try:
        generator = ReportGenerator()
        
        # 鍒涘缓婕旂ず閰嶇疆
        config = ReportConfig(
            report_id=f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_name="婕旂ず娴嬭瘯鎶ュ憡",
            report_type=ReportType.TEST_EXECUTION,
            include_charts=True,
            include_details=True
        )
        
        # 浣跨敤绀轰緥鏁版嵁
        data = generator.create_sample_data()
        
        # 杞崲鏍煎紡鍒楄〃
        format_objects = []
        for format_str in formats:
            try:
                format_objects.append(ReportFormat(format_str.lower()))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"涓嶆敮鎸佺殑鏍煎紡: {format_str}")
        
        # 鐢熸垚鎶ュ憡
        generated_reports = await generator.generate_report(config, data, format_objects)
        
        # 鏋勫缓鍝嶅簲
        total_size = sum(r.file_size for r in generated_reports if r.status == "completed")
        total_time = max(r.generation_time for r in generated_reports)
        
        format_list = []
        for report in generated_reports:
            format_list.append({
                "format": report.format.value,
                "file_path": report.file_path,
                "file_size": report.file_size,
                "generation_time": report.generation_time,
                "status": report.status,
                "error_message": report.error_message
            })
        
        response_data = GeneratedReportResponse(
            report_id=config.report_id,
            report_name=config.report_name,
            formats=format_list,
            generation_time=total_time,
            total_size=total_size,
            status="completed",
            created_at=datetime.now()
        )
        
        return BaseResponse(
            success=True,
            message="婕旂ず鎶ュ憡鐢熸垚鎴愬姛",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"鐢熸垚婕旂ず鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail=f"鐢熸垚婕旂ず鎶ュ憡澶辫触: {str(e)}")


@router.get("/formats", response_model=BaseResponse[Dict[str, List[str]]])
async def get_supported_formats(
    current_user: User = Depends(get_current_user)
):
    """
    鑾峰彇鏀寔鐨勬牸寮?
    
    杩斿洖鏀寔鐨勬姤鍛婄敓鎴愬拰瀵煎叆鏍煎紡鍒楄〃
    """
    try:
        generator = ReportGenerator()
        importer = ReportImporter()
        
        return BaseResponse(
            success=True,
            message="鑾峰彇鏀寔鏍煎紡鎴愬姛",
            data={
                "generation_formats": [f.value for f in ReportFormat],
                "import_formats": importer.get_supported_formats(),
                "source_types": importer.get_supported_source_types(),
                "report_types": [t.value for t in ReportType]
            }
        )
        
    except Exception as e:
        logger.error(f"鑾峰彇鏀寔鏍煎紡澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鑾峰彇鏀寔鏍煎紡澶辫触")


@router.delete("/imported/{import_id}", response_model=BaseResponse[bool])
async def delete_imported_report(
    import_id: str = PathParam(..., description="瀵煎叆ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鍒犻櫎瀵煎叆鐨勬姤鍛?
    
    鍒犻櫎鎸囧畾鐨勫鍏ユ姤鍛婂強鍏剁浉鍏虫枃浠?
    """
    try:
        importer = ReportImporter()
        
        # 妫€鏌ユ姤鍛婃槸鍚﹀瓨鍦?
        imported_report = await importer.get_imported_report(import_id)
        if not imported_report:
            raise HTTPException(status_code=404, detail="imported report not found")
        
        # 鍒犻櫎鎶ュ憡鏂囦欢鍜岃褰?
        import_dir = Path(importer.import_dir) / import_id
        if import_dir.exists():
            import shutil
            shutil.rmtree(import_dir)
        
        return BaseResponse(
            success=True,
            message="瀵煎叆鎶ュ憡鍒犻櫎鎴愬姛",
            data=True
        )
        
    except Exception as e:
        logger.error(f"鍒犻櫎瀵煎叆鎶ュ憡澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鍒犻櫎鎶ュ憡澶辫触")


@router.get("/analytics", response_model=BaseResponse[Dict[str, Any]])
async def get_reports_analytics(
    days: int = Query(30, ge=1, le=365, description="缁熻澶╂暟"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    鑾峰彇鎶ュ憡鍒嗘瀽鏁版嵁
    
    鑾峰彇鎶ュ憡浣跨敤鎯呭喌鐨勭粺璁″垎鏋?
    """
    try:
        importer = ReportImporter()
        
        # 鑾峰彇瀵煎叆鎶ュ憡鍒楄〃
        imported_reports = await importer.list_imported_reports()
        
        # 璁＄畻缁熻鏁版嵁
        total_imported = len(imported_reports)
        
        # 鎸夋牸寮忓垎缁?
        format_stats = {}
        source_stats = {}
        
        for report in imported_reports:
            file_type = report.get('file_type', 'unknown')
            source_type = report.get('source_type', 'unknown')
            
            format_stats[file_type] = format_stats.get(file_type, 0) + 1
            source_stats[source_type] = source_stats.get(source_type, 0) + 1
        
        # 璁＄畻娴嬭瘯缁撴灉缁熻
        total_test_results = sum(report.get('test_results_count', 0) for report in imported_reports)
        
        analytics_data = {
            "summary": {
                "total_imported_reports": total_imported,
                "total_test_results": total_test_results,
                "average_results_per_report": round(total_test_results / total_imported, 2) if total_imported > 0 else 0
            },
            "format_distribution": format_stats,
            "source_distribution": source_stats,
            "recent_imports": imported_reports[-10:] if imported_reports else []
        }
        
        return BaseResponse(
            success=True,
            message="鑾峰彇鎶ュ憡鍒嗘瀽鏁版嵁鎴愬姛",
            data=analytics_data
        )
        
    except Exception as e:
        logger.error(f"鑾峰彇鎶ュ憡鍒嗘瀽鏁版嵁澶辫触: {e}")
        raise HTTPException(status_code=500, detail="鑾峰彇鍒嗘瀽鏁版嵁澶辫触")
