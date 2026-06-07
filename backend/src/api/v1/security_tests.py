"""
安全测试管理API接口

本模块实现安全测试相关的RESTful API接口，包括：
- 安全测试计划和配置管理
- 安全扫描和渗透测试执行
- 安全漏洞管理和风险评估
- 安全测试工具集成
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging
import json
import ssl
import uuid
import urllib.parse
import urllib.request
from pathlib import Path as FilePath

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...services.test_tools_integration_service import TestToolsIntegrationService
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security-tests", tags=["安全测试管理"])
security = HTTPBearer()
STORE_PATH = FilePath("data/security_tests.json")


def _load_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {"tests": [], "executions": [], "results": []}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"tests": [], "executions": [], "results": []}


def _save_store(store: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_id(items: List[Dict[str, Any]]) -> int:
    return max([int(item.get("id", 0)) for item in items] or [0]) + 1


def _scan_target(url: str, categories: List[str]) -> Dict[str, Any]:
    vulnerabilities = []
    headers = {}
    status_code = None
    error = None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AI-Test-Management-Security-Scan/1.0"})
        with urllib.request.urlopen(request, timeout=8, context=ssl.create_default_context()) as response:
            status_code = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
    except Exception as exc:
        error = str(exc)
        vulnerabilities.append({
            "vulnerability_id": f"vuln_{uuid.uuid4().hex[:10]}",
            "vulnerability_type": "CONNECTIVITY",
            "severity": "MEDIUM",
            "title": "目标地址不可访问",
            "description": error,
            "affected_url": url,
            "parameter": None,
            "payload": None,
            "evidence": error,
            "impact": "无法完成自动安全探测",
            "recommendation": "检查目标地址、网络连通性和证书配置",
            "cwe_id": None,
            "cvss_score": 5.0,
            "is_false_positive": False,
            "status": "OPEN",
            "discovered_at": datetime.utcnow().isoformat()
        })

    header_checks = [
        ("SECURITY_HEADERS", "strict-transport-security", "缺少 HSTS 安全头", "LOW"),
        ("SECURITY_HEADERS", "x-content-type-options", "缺少 X-Content-Type-Options 安全头", "LOW"),
        ("SECURITY_HEADERS", "x-frame-options", "缺少 X-Frame-Options 安全头", "LOW"),
    ]
    enabled_categories = {category.upper() for category in categories}
    if not enabled_categories or "SECURITY_HEADERS" in enabled_categories:
        for category, header, title, severity in header_checks:
            if headers and header not in headers:
                vulnerabilities.append({
                    "vulnerability_id": f"vuln_{uuid.uuid4().hex[:10]}",
                    "vulnerability_type": category,
                    "severity": severity,
                    "title": title,
                    "description": f"响应中未发现 {header}。",
                    "affected_url": url,
                    "parameter": None,
                    "payload": None,
                    "evidence": f"HTTP {status_code}, missing header: {header}",
                    "impact": "浏览器安全防护能力降低",
                    "recommendation": f"在响应中配置 {header}。",
                    "cwe_id": None,
                    "cvss_score": 3.1,
                    "is_false_positive": False,
                    "status": "OPEN",
                    "discovered_at": datetime.utcnow().isoformat()
                })

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" and (not enabled_categories or "SSL_TLS" in enabled_categories):
        vulnerabilities.append({
            "vulnerability_id": f"vuln_{uuid.uuid4().hex[:10]}",
            "vulnerability_type": "SSL_TLS",
            "severity": "HIGH",
            "title": "未使用 HTTPS",
            "description": "目标地址使用非加密 HTTP。",
            "affected_url": url,
            "parameter": None,
            "payload": None,
            "evidence": parsed.scheme,
            "impact": "传输数据可能被窃听或篡改",
            "recommendation": "启用 HTTPS 并强制跳转到安全协议。",
            "cwe_id": "CWE-319",
            "cvss_score": 7.4,
            "is_false_positive": False,
            "status": "OPEN",
            "discovered_at": datetime.utcnow().isoformat()
        })

    return {"status_code": status_code, "error": error, "vulnerabilities": vulnerabilities}


# 请求模式
class CreateSecurityTestRequest(BaseModel):
    """创建安全测试请求"""
    test_name: str = Field(..., min_length=1, max_length=200, description="测试名称")
    description: Optional[str] = Field(None, description="测试描述")
    project_id: int = Field(..., description="项目ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    test_type: str = Field(..., description="安全测试类型")
    target_url: str = Field(..., description="目标URL")
    scan_scope: Dict[str, Any] = Field(..., description="扫描范围")
    security_policies: List[str] = Field(..., description="安全策略")
    vulnerability_categories: List[str] = Field(..., description="漏洞类别")
    scan_depth: str = Field("MEDIUM", description="扫描深度")
    authentication_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    exclusion_rules: Optional[List[str]] = Field(None, description="排除规则")


class UpdateSecurityTestRequest(BaseModel):
    """更新安全测试请求"""
    test_name: Optional[str] = Field(None, min_length=1, max_length=200, description="测试名称")
    description: Optional[str] = Field(None, description="测试描述")
    test_type: Optional[str] = Field(None, description="安全测试类型")
    target_url: Optional[str] = Field(None, description="目标URL")
    scan_scope: Optional[Dict[str, Any]] = Field(None, description="扫描范围")
    security_policies: Optional[List[str]] = Field(None, description="安全策略")
    vulnerability_categories: Optional[List[str]] = Field(None, description="漏洞类别")
    scan_depth: Optional[str] = Field(None, description="扫描深度")
    authentication_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    exclusion_rules: Optional[List[str]] = Field(None, description="排除规则")


class ExecuteSecurityTestRequest(BaseModel):
    """执行安全测试请求"""
    test_id: int = Field(..., description="安全测试ID")
    scan_tools: List[str] = Field(..., description="扫描工具")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")


# 响应模式
class SecurityTestResponse(BaseModel):
    """安全测试响应"""
    id: int = Field(..., description="安全测试ID")
    test_name: str = Field(..., description="测试名称")
    description: Optional[str] = Field(None, description="测试描述")
    project_id: int = Field(..., description="项目ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    test_type: str = Field(..., description="安全测试类型")
    target_url: str = Field(..., description="目标URL")
    scan_scope: Dict[str, Any] = Field(..., description="扫描范围")
    security_policies: List[str] = Field(..., description="安全策略")
    vulnerability_categories: List[str] = Field(..., description="漏洞类别")
    scan_depth: str = Field(..., description="扫描深度")
    authentication_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    exclusion_rules: Optional[List[str]] = Field(None, description="排除规则")
    status: str = Field(..., description="测试状态")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class SecurityTestExecutionResponse(BaseModel):
    """安全测试执行响应"""
    execution_id: str = Field(..., description="执行ID")
    test_id: int = Field(..., description="安全测试ID")
    status: str = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[int] = Field(None, description="执行时长(秒)")
    progress_percentage: float = Field(..., description="进度百分比")
    scan_tools: List[str] = Field(..., description="扫描工具")
    scanned_urls: int = Field(..., description="已扫描URL数")
    total_urls: int = Field(..., description="总URL数")
    vulnerabilities_found: int = Field(..., description="发现漏洞数")
    critical_vulnerabilities: int = Field(..., description="严重漏洞数")
    high_vulnerabilities: int = Field(..., description="高危漏洞数")
    medium_vulnerabilities: int = Field(..., description="中危漏洞数")
    low_vulnerabilities: int = Field(..., description="低危漏洞数")
    false_positives: int = Field(..., description="误报数")
    current_scan_target: Optional[str] = Field(None, description="当前扫描目标")


class SecurityVulnerabilityResponse(BaseModel):
    """安全漏洞响应"""
    vulnerability_id: str = Field(..., description="漏洞ID")
    execution_id: str = Field(..., description="执行ID")
    vulnerability_type: str = Field(..., description="漏洞类型")
    severity: str = Field(..., description="严重程度")
    title: str = Field(..., description="漏洞标题")
    description: str = Field(..., description="漏洞描述")
    affected_url: str = Field(..., description="受影响URL")
    parameter: Optional[str] = Field(None, description="受影响参数")
    payload: Optional[str] = Field(None, description="攻击载荷")
    evidence: Optional[str] = Field(None, description="证据")
    impact: str = Field(..., description="影响描述")
    recommendation: str = Field(..., description="修复建议")
    cwe_id: Optional[str] = Field(None, description="CWE编号")
    cvss_score: Optional[float] = Field(None, description="CVSS评分")
    is_false_positive: bool = Field(False, description="是否误报")
    status: str = Field(..., description="漏洞状态")
    discovered_at: datetime = Field(..., description="发现时间")


class SecurityTestResultResponse(BaseModel):
    """安全测试结果响应"""
    execution_id: str = Field(..., description="执行ID")
    test_id: int = Field(..., description="安全测试ID")
    test_name: str = Field(..., description="测试名称")
    execution_summary: Dict[str, Any] = Field(..., description="执行摘要")
    vulnerability_summary: Dict[str, Any] = Field(..., description="漏洞摘要")
    risk_assessment: Dict[str, Any] = Field(..., description="风险评估")
    compliance_status: Dict[str, Any] = Field(..., description="合规状态")
    security_score: float = Field(..., description="安全评分")
    vulnerabilities: List[SecurityVulnerabilityResponse] = Field(..., description="漏洞列表")
    recommendations: List[str] = Field(..., description="安全建议")
    remediation_plan: List[Dict[str, Any]] = Field(..., description="修复计划")
    generated_at: datetime = Field(..., description="生成时间")


# API接口实现
@router.post("/", response_model=BaseResponse[SecurityTestResponse])
async def create_security_test(
    request: CreateSecurityTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建安全测试
    
    创建新的安全测试配置，包括扫描范围、安全策略和漏洞类别。
    """
    try:
        store = _load_store()
        now = datetime.utcnow().isoformat()
        test_data = request.dict()
        test_data.update({
            "id": _next_id(store["tests"]),
            "created_by": current_user.id,
            "status": "CREATED",
            "created_at": now,
            "updated_at": now
        })
        store["tests"].append(test_data)
        _save_store(store)
        response_data = SecurityTestResponse(**test_data)
        
        return BaseResponse(
            success=True,
            message="安全测试创建成功",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"创建安全测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/execute", response_model=BaseResponse[SecurityTestExecutionResponse])
async def execute_security_test(
    request: ExecuteSecurityTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    执行安全测试
    
    启动安全测试执行，支持多种扫描工具和实时监控。
    """
    try:
        store = _load_store()
        security_test = next((item for item in store["tests"] if int(item["id"]) == request.test_id), None)
        if not security_test:
            raise HTTPException(status_code=404, detail="安全测试不存在")
        start_time = datetime.utcnow()
        scan = _scan_target(security_test["target_url"], security_test.get("vulnerability_categories") or [])
        end_time = datetime.utcnow()
        vulnerabilities = scan["vulnerabilities"]
        severity_counts = {
            "CRITICAL": sum(1 for item in vulnerabilities if item["severity"].upper() == "CRITICAL"),
            "HIGH": sum(1 for item in vulnerabilities if item["severity"].upper() == "HIGH"),
            "MEDIUM": sum(1 for item in vulnerabilities if item["severity"].upper() == "MEDIUM"),
            "LOW": sum(1 for item in vulnerabilities if item["severity"].upper() == "LOW"),
        }
        execution = {
            "execution_id": f"sec_{uuid.uuid4().hex[:12]}",
            "test_id": request.test_id,
            "status": "COMPLETED",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": max(1, int((end_time - start_time).total_seconds())),
            "progress_percentage": 100,
            "scan_tools": request.scan_tools,
            "scanned_urls": 1 if not scan["error"] else 0,
            "total_urls": 1,
            "vulnerabilities_found": len(vulnerabilities),
            "critical_vulnerabilities": severity_counts["CRITICAL"],
            "high_vulnerabilities": severity_counts["HIGH"],
            "medium_vulnerabilities": severity_counts["MEDIUM"],
            "low_vulnerabilities": severity_counts["LOW"],
            "false_positives": 0,
            "current_scan_target": security_test["target_url"]
        }
        for vulnerability in vulnerabilities:
            vulnerability["execution_id"] = execution["execution_id"]
        result = {
            "execution_id": execution["execution_id"],
            "vulnerabilities": vulnerabilities,
            "generated_at": end_time.isoformat(),
            "status_code": scan["status_code"],
            "error": scan["error"]
        }
        security_test["status"] = "COMPLETED"
        security_test["updated_at"] = end_time.isoformat()
        store["executions"].append(execution)
        store["results"].append(result)
        _save_store(store)
        response_data = SecurityTestExecutionResponse(**execution)
        
        return BaseResponse(
            success=True,
            message="安全测试执行启动成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"执行安全测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/executions/{execution_id}/results", response_model=BaseResponse[SecurityTestResultResponse])
async def get_security_test_results(
    execution_id: str = Path(..., description="执行ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取安全测试结果
    
    获取安全测试执行的详细结果和漏洞信息。
    """
    try:
        store = _load_store()
        execution = next((item for item in store["executions"] if item["execution_id"] == execution_id), None)
        result = next((item for item in store["results"] if item["execution_id"] == execution_id), None)
        if not execution or not result:
            raise HTTPException(status_code=404, detail="安全测试结果不存在")
        test = next((item for item in store["tests"] if int(item["id"]) == int(execution["test_id"])), {})
        vulnerabilities = [
            SecurityVulnerabilityResponse(**{**item, "execution_id": item.get("execution_id") or execution_id})
            for item in result["vulnerabilities"]
        ]
        security_score = max(0, 100 - execution["critical_vulnerabilities"] * 25 - execution["high_vulnerabilities"] * 15 - execution["medium_vulnerabilities"] * 8 - execution["low_vulnerabilities"] * 3)
        response_data = SecurityTestResultResponse(
            execution_id=execution_id,
            test_id=execution["test_id"],
            test_name=test.get("test_name", "安全测试"),
            execution_summary={
                "status": execution["status"],
                "scanned_urls": execution["scanned_urls"],
                "total_urls": execution["total_urls"]
            },
            vulnerability_summary={
                "total": execution["vulnerabilities_found"],
                "critical": execution["critical_vulnerabilities"],
                "high": execution["high_vulnerabilities"],
                "medium": execution["medium_vulnerabilities"],
                "low": execution["low_vulnerabilities"]
            },
            risk_assessment={"security_score": security_score},
            compliance_status={"basic_header_check": "PASS" if execution["vulnerabilities_found"] == 0 else "ATTENTION"},
            security_score=security_score,
            vulnerabilities=vulnerabilities,
            recommendations=["优先处理高危漏洞并补齐缺失安全响应头"] if execution["vulnerabilities_found"] else ["未发现基础安全问题，建议继续进行认证授权专项测试"],
            remediation_plan=[],
            generated_at=result["generated_at"]
        )
        
        return BaseResponse(
            success=True,
            message="获取安全测试结果成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取安全测试结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[SecurityTestResponse])
async def list_security_tests(
    project_id: Optional[int] = Query(None, description="项目ID"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    test_type: Optional[str] = Query(None, description="测试类型"),
    status: Optional[str] = Query(None, description="测试状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取安全测试列表
    
    支持多条件过滤和分页查询。
    """
    try:
        tests = list(_load_store()["tests"])
        if project_id:
            tests = [item for item in tests if int(item.get("project_id") or 0) == project_id]
        if test_plan_id:
            tests = [item for item in tests if int(item.get("test_plan_id") or 0) == test_plan_id]
        if test_type:
            tests = [item for item in tests if item.get("test_type") == test_type]
        if status:
            tests = [item for item in tests if item.get("status") == status]
        tests.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        total = len(tests)
        paged = tests[(page - 1) * page_size: page * page_size]
        response_data = [SecurityTestResponse(**test) for test in paged]
        
        return PaginatedResponse(
            success=True,
            message="获取安全测试列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取安全测试列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
