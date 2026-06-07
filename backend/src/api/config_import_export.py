"""
配置文件导入导出API接口
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form, Path, status
from fastapi.responses import Response, StreamingResponse
from typing import List, Optional
import logging
from io import BytesIO

from ..schemas.config import ApiResponse
from ..services.config_import_export_service import config_import_export_service, FileFormat
from ..core.auth import get_current_user
from ..models.user import User
from ..models.config import Environment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import-export", tags=["配置导入导出"])


@router.get("/formats", response_model=ApiResponse[dict])
async def get_supported_formats():
    """获取支持的文件格式"""
    try:
        formats = config_import_export_service.get_supported_formats()
        return ApiResponse(success=True, data=formats, message="获取支持格式成功")
    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支持格式失败: {str(e)}"
        )


@router.post("/export", response_model=ApiResponse[dict])
async def export_configs(
    format_type: FileFormat = Query(..., description="导出格式"),
    environment: Environment = Query(..., description="环境"),
    group_id: Optional[int] = Query(None, description="分组ID"),
    config_keys: Optional[str] = Query(None, description="指定配置键（逗号分隔）"),
    include_sensitive: bool = Query(False, description="是否包含敏感配置"),
    current_user: User = Depends(get_current_user)
):
    """导出配置文件"""
    try:
        # 解析配置键列表
        config_key_list = None
        if config_keys:
            config_key_list = [key.strip() for key in config_keys.split(',') if key.strip()]
        
        success, error_msg, content = await config_import_export_service.export_configs(
            format_type=format_type,
            environment=environment.value,
            group_id=group_id,
            config_keys=config_key_list,
            include_sensitive=include_sensitive
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 生成文件名
        file_extension = {
            FileFormat.ENV: '.env',
            FileFormat.JSON: '.json',
            FileFormat.YAML: '.yml',
            FileFormat.XML: '.xml',
            FileFormat.PROPERTIES: '.properties'
        }.get(format_type, '.txt')
        
        filename = f"config_{environment.value}_{format_type.value}{file_extension}"
        
        # 检查内容
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="导出内容为空"
            )
        
        # 设置响应头
        media_type = {
            FileFormat.ENV: 'text/plain',
            FileFormat.JSON: 'application/json',
            FileFormat.YAML: 'application/x-yaml',
            FileFormat.XML: 'application/xml',
            FileFormat.PROPERTIES: 'text/plain'
        }.get(format_type, 'text/plain')
        
        # 创建文件流
        file_stream = BytesIO(content.encode('utf-8'))
        
        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": f"{media_type}; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出配置失败: {str(e)}"
        )


@router.post("/import/preview", response_model=ApiResponse[dict])
async def preview_import(
    file: UploadFile = File(..., description="配置文件"),
    format_type: FileFormat = Form(..., description="文件格式"),
    environment: Environment = Form(..., description="目标环境"),
    group_id: Optional[int] = Form(None, description="目标分组ID"),
    current_user: User = Depends(get_current_user)
):
    """预览导入配置文件"""
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 预览导入
        success, error_msg, result = await config_import_export_service.import_configs(
            file_content=file_content,
            format_type=format_type,
            environment=environment.value,
            user_id=current_user.id,
            group_id=group_id,
            overwrite_existing=False,
            dry_run=True  # 试运行
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data=result, message="预览导入成功")
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件编码格式不支持，请使用UTF-8编码"
        )
    except Exception as e:
        logger.error(f"预览导入失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览导入失败: {str(e)}"
        )


@router.post("/import", response_model=ApiResponse[dict])
async def import_configs(
    file: UploadFile = File(..., description="配置文件"),
    format_type: FileFormat = Form(..., description="文件格式"),
    environment: Environment = Form(..., description="目标环境"),
    group_id: Optional[int] = Form(None, description="目标分组ID"),
    overwrite_existing: bool = Form(False, description="是否覆盖已存在的配置"),
    current_user: User = Depends(get_current_user)
):
    """导入配置文件"""
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 验证文件大小（限制为10MB）
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件大小不能超过10MB"
            )
        
        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 执行导入
        success, error_msg, result = await config_import_export_service.import_configs(
            file_content=file_content,
            format_type=format_type,
            environment=environment.value,
            user_id=current_user.id,
            group_id=group_id,
            overwrite_existing=overwrite_existing,
            dry_run=False
        )
        
        if not success:
            # 如果是冲突错误，返回特殊状态码
            if "配置冲突" in str(error_msg):
                return ApiResponse(
                    success=False, 
                    data=result, 
                    message=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        
        return ApiResponse(success=True, data=result, message="导入配置成功")
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件编码格式不支持，请使用UTF-8编码"
        )
    except Exception as e:
        logger.error(f"导入配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入配置失败: {str(e)}"
        )


@router.post("/import/force", response_model=ApiResponse[dict])
async def force_import_configs(
    file: UploadFile = File(..., description="配置文件"),
    format_type: FileFormat = Form(..., description="文件格式"),
    environment: Environment = Form(..., description="目标环境"),
    group_id: Optional[int] = Form(None, description="目标分组ID"),
    current_user: User = Depends(get_current_user)
):
    """强制导入配置文件（覆盖冲突）"""
    try:
        # 验证文件格式
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 强制导入（覆盖已存在配置）
        success, error_msg, result = await config_import_export_service.import_configs(
            file_content=file_content,
            format_type=format_type,
            environment=environment.value,
            user_id=current_user.id,
            group_id=group_id,
            overwrite_existing=True,  # 强制覆盖
            dry_run=False
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ApiResponse(success=True, data=result, message="强制导入配置成功")
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件编码格式不支持，请使用UTF-8编码"
        )
    except Exception as e:
        logger.error(f"强制导入配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"强制导入配置失败: {str(e)}"
        )


@router.get("/template/{format_type}")
async def download_template(
    format_type: FileFormat = Path(..., description="模板格式"),
    current_user: User = Depends(get_current_user)
):
    """下载配置文件模板"""
    try:
        # 生成模板内容
        template_configs = {
            'app.name': {
                'value': 'My Application',
                'type': 'STRING',
                'description': '应用程序名称',
                'is_sensitive': False
            },
            'app.port': {
                'value': '8000',
                'type': 'INTEGER',
                'description': '应用程序端口',
                'is_sensitive': False
            },
            'app.debug': {
                'value': 'false',
                'type': 'BOOLEAN',
                'description': '是否开启调试模式',
                'is_sensitive': False
            },
            'database.host': {
                'value': 'localhost',
                'type': 'STRING',
                'description': '数据库主机地址',
                'is_sensitive': False
            },
            'database.password': {
                'value': '****',
                'type': 'PASSWORD',
                'description': '数据库密码',
                'is_sensitive': True
            }
        }
        
        # 根据格式生成模板内容
        if format_type == FileFormat.ENV:
            content = config_import_export_service._export_to_env(template_configs)
        elif format_type == FileFormat.JSON:
            content = config_import_export_service._export_to_json(template_configs)
        elif format_type == FileFormat.YAML:
            content = config_import_export_service._export_to_yaml(template_configs)
        elif format_type == FileFormat.XML:
            content = config_import_export_service._export_to_xml(template_configs)
        elif format_type == FileFormat.PROPERTIES:
            content = config_import_export_service._export_to_properties(template_configs)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的模板格式: {format_type}"
            )
        
        # 生成文件名
        file_extension = {
            FileFormat.ENV: '.env',
            FileFormat.JSON: '.json',
            FileFormat.YAML: '.yml',
            FileFormat.XML: '.xml',
            FileFormat.PROPERTIES: '.properties'
        }.get(format_type, '.txt')
        
        filename = f"config_template{file_extension}"
        
        # 设置响应头
        media_type = {
            FileFormat.ENV: 'text/plain',
            FileFormat.JSON: 'application/json',
            FileFormat.YAML: 'application/x-yaml',
            FileFormat.XML: 'application/xml',
            FileFormat.PROPERTIES: 'text/plain'
        }.get(format_type, 'text/plain')
        
        # 创建文件流
        file_stream = BytesIO(content.encode('utf-8'))
        
        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": f"{media_type}; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载模板失败: {str(e)}"
        )