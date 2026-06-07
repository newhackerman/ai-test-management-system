"""System settings API."""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..models.config import ConfigType, Environment, SystemConfig
from ..models.user import User
from ..services.auth_dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

SETTINGS_CONFIG_KEY = "system.settings"
MASKED_SECRET = "********"


class SystemSettings(BaseModel):
    systemName: str = Field(default="AI自动化测试管理系统", min_length=1, max_length=100)
    systemVersion: str = Field(default="v1.0.0", min_length=1, max_length=50)
    systemDescription: str = Field(default="基于 AI 的自动化测试管理平台", max_length=500)

    passwordMinLength: int = Field(default=8, ge=6, le=20)
    passwordRequireUppercase: bool = True
    passwordRequireLowercase: bool = True
    passwordRequireNumbers: bool = True
    passwordRequireSymbols: bool = True
    maxLoginAttempts: int = Field(default=5, ge=3, le=10)
    accountLockoutDuration: int = Field(default=30, ge=5, le=1440)
    sessionTimeout: int = Field(default=60, ge=15, le=480)
    jwtAccessTokenExpire: int = Field(default=1, ge=1, le=168)
    jwtRefreshTokenExpire: int = Field(default=7, ge=1, le=90)

    emailEnabled: bool = True
    smtpHost: str = Field(default="smtp.example.com", max_length=255)
    smtpPort: int = Field(default=587, ge=1, le=65535)
    smtpUsername: str = Field(default="noreply@example.com", max_length=255)
    smtpPassword: str = Field(default="", max_length=255)

    maxFileSize: int = Field(default=10, ge=1, le=100)
    allowedFileTypes: str = Field(default="jpg,png,pdf,doc,docx,xls,xlsx", max_length=500)

    maintenanceMode: bool = False
    maintenanceMessage: str = Field(default="系统正在维护中，请稍后再试。", max_length=500)


def _default_settings() -> Dict[str, Any]:
    return SystemSettings().model_dump()


def _mask_secret(settings: Dict[str, Any]) -> Dict[str, Any]:
    response = dict(settings)
    if response.get("smtpPassword"):
        response["smtpPassword"] = MASKED_SECRET
    return response


async def _get_settings_config(session: AsyncSession) -> SystemConfig | None:
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.config_key == SETTINGS_CONFIG_KEY,
            SystemConfig.environment == Environment.PROD,
            SystemConfig.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


def _decode_settings(config: SystemConfig | None) -> Dict[str, Any]:
    defaults = _default_settings()
    if not config or not config.config_value:
        return defaults

    try:
        stored = json.loads(config.config_value)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid system settings JSON in sys_config id=%s", getattr(config, "id", None))
        return defaults

    if not isinstance(stored, dict):
        return defaults

    try:
        return SystemSettings(**{**defaults, **stored}).model_dump()
    except Exception as exc:
        logger.warning("Invalid system settings values in sys_config id=%s: %s", getattr(config, "id", None), exc)
        return defaults


async def _save_settings(
    session: AsyncSession,
    settings: Dict[str, Any],
    current_user: User,
    config: SystemConfig | None = None,
) -> SystemConfig:
    value = json.dumps(settings, ensure_ascii=False)
    if config is None:
        config = SystemConfig(
            config_key=SETTINGS_CONFIG_KEY,
            config_value=value,
            config_type=ConfigType.JSON,
            environment=Environment.PROD,
            description="系统设置页面配置",
            default_value=json.dumps(_default_settings(), ensure_ascii=False),
            is_core=True,
            is_enabled=True,
            is_required=True,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        session.add(config)
    else:
        config.config_value = value
        config.config_type = ConfigType.JSON
        config.is_enabled = True
        config.updated_by = current_user.id

    await session.commit()
    await session.refresh(config)
    return config


@router.get("")
async def get_settings(
    _: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get persisted system settings."""
    config = await _get_settings_config(session)
    settings = _decode_settings(config)
    return {"settings": _mask_secret(settings)}


@router.put("")
async def update_settings(
    request: SystemSettings,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Persist system settings."""
    config = await _get_settings_config(session)
    existing = _decode_settings(config)
    incoming = request.model_dump()

    if incoming.get("smtpPassword") == MASKED_SECRET:
        incoming["smtpPassword"] = existing.get("smtpPassword", "")

    settings = SystemSettings(**incoming).model_dump()
    await _save_settings(session, settings, current_user, config)
    return {"message": "设置已保存", "settings": _mask_secret(settings)}


@router.post("/reset")
async def reset_settings(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Reset system settings to defaults."""
    config = await _get_settings_config(session)
    settings = _default_settings()
    try:
      await _save_settings(session, settings, current_user, config)
    except Exception as exc:
        logger.error("Reset system settings failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置系统设置失败",
        ) from exc

    return {"message": "设置已重置", "settings": _mask_secret(settings)}
