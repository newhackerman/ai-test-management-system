"""
认证接口速率限制工具

为"忘记密码 / 重置密码"等敏感认证接口提供基于 Redis 的频率限制。
当 Redis 不可用时，get_redis_client() 会自动退回到内存 MockRedisClient，
保证功能在测试/单机环境下依然可用。

设计目标：
- 防邮件轰炸：同一来源短时间内只能触发有限次密码重置邮件
- 防用户枚举侧信道：限流发生在业务处理之前，且不区分"用户是否存在"
- 防令牌暴力扫描：对 /reset-password 接口本身做总体与失败双重限流

实现思路与 backend/src/api/v1/meetings/security.py 中的 check_rate_limit
保持一致：使用 get/setex 计数（而非 incr），以便同时兼容真实 Redis
和 MockRedisClient（后者未实现 incr）。
"""
import logging
from typing import Optional

from fastapi import HTTPException, status

from .ip import IPUtils
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)


# 频率限制规则
# (max_requests, window_seconds, 中文提示)
RATE_LIMIT_RULES = {
    # ── 忘记密码 ──
    # 全局按邮箱（不依赖 IP）：1 小时 3 次 —— 代理换 IP 的主要防线
    "forgot_email_global": (3, 3600, "该邮箱请求重置密码过于频繁，请稍后再试"),
    # 单 (IP+邮箱)：1 小时 3 次 —— 同一 IP 对同一邮箱的额外约束
    "forgot_email": (3, 3600, "该邮箱请求重置密码过于频繁，请稍后再试"),
    # 单 IP（跨邮箱）：1 小时 10 次
    "forgot_ip": (10, 3600, "请求过于频繁，请稍后再试"),
    # 全系统总量：1 小时 60 次 —— 最后防线，防止分布式大规模滥用
    "forgot_global": (60, 3600, "系统繁忙，请稍后再试"),

    # ── 重置密码 ──
    # 单 IP：1 小时 10 次
    "reset_ip": (10, 3600, "重置密码请求过于频繁，请稍后再试"),
    # 失败尝试：10 分钟 5 次
    "reset_fail": (5, 600, "重置失败次数过多，请稍后再试"),
    # 全系统总量：1 小时 30 次 —— 防分布式 token 暴力扫描
    "reset_global": (30, 3600, "系统繁忙，请稍后再试"),
}


def _normalize_email(email: str) -> str:
    """归一化邮箱，作为限流 key 的一部分（小写 + 去空白）。"""
    return (email or "").strip().lower()[:120]


async def _check_counter(
    redis_client,
    key: str,
    max_requests: int,
    window_seconds: int,
    message: str,
) -> None:
    """
    基于 get/setex 的滑动窗口计数；超限抛 HTTP 429。

    采用"首次请求 setex、后续 incr"在真实 Redis 上更省内存，但
    MockRedisClient 未实现 incr，故统一用 get/setex 模式，两种客户端下行为一致。
    """
    try:
        current = await redis_client.get(key)
        if current is None:
            await redis_client.setex(key, window_seconds, 1)
            return

        count = int(current)
        if count >= max_requests:
            logger.warning("认证接口触发限流 key=%s count=%s", key, count)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": str(window_seconds)},
            )

        await redis_client.setex(key, window_seconds, str(count + 1))
    except HTTPException:
        raise
    except Exception as e:
        # 限流自身异常不应阻断业务（fail-open），仅记录日志
        logger.error("认证限流检查失败 key=%s: %s", key, e)


async def check_forgot_password_rate_limit(request, email: str) -> None:
    """
    /forgot-password 的四层限流。

    防御层级（按优先级从高到低，代理换 IP 靠 ① 和 ② 拦截）：
      ① 全系统总量  — 1h 60 次（最后一道防线）
      ② 全局按邮箱  — 1h 3 次（不依赖 IP，换代理无效）
      ③ 单 IP+邮箱   — 1h 3 次
      ④ 单 IP       — 1h 10 次

    超限抛 HTTP 429。Redis 不可用时自动退回内存计数。
    """
    client_ip = IPUtils.get_client_ip(request)
    safe_email = _normalize_email(email)

    redis_client = await get_redis_client()

    # ① 全系统总量（不依赖 IP/邮箱）
    max_req, window, message = RATE_LIMIT_RULES["forgot_global"]
    await _check_counter(
        redis_client,
        "rate_limit:forgot_global",
        max_req,
        window,
        message,
    )

    # ② 全局按邮箱（不依赖 IP —— 代理换 IP 的主要防线）
    max_req, window, message = RATE_LIMIT_RULES["forgot_email_global"]
    await _check_counter(
        redis_client,
        f"rate_limit:forgot_email_g:{safe_email}",
        max_req,
        window,
        message,
    )

    # ③ 单 (IP+邮箱)
    max_req, window, message = RATE_LIMIT_RULES["forgot_email"]
    await _check_counter(
        redis_client,
        f"rate_limit:forgot:{client_ip}:{safe_email}",
        max_req,
        window,
        message,
    )

    # ④ 单 IP（跨邮箱）
    max_req, window, message = RATE_LIMIT_RULES["forgot_ip"]
    await _check_counter(
        redis_client,
        f"rate_limit:forgot_ip:{client_ip}",
        max_req,
        window,
        message,
    )


async def check_reset_password_rate_limit(request) -> None:
    """
    /reset-password 的三层限流。

    防御层级：
      ① 全系统总量 — 1h 30 次（防分布式 token 暴力扫描）
      ② 单 IP      — 1h 10 次
      ③ 失败预检    — 10min 5 次失败即拒绝

    超限抛 HTTP 429。
    """
    client_ip = IPUtils.get_client_ip(request)
    redis_client = await get_redis_client()

    # ① 全系统总量（不依赖 IP —— 代理换 IP 的主要防线）
    max_req, window, message = RATE_LIMIT_RULES["reset_global"]
    await _check_counter(
        redis_client,
        "rate_limit:reset_global",
        max_req,
        window,
        message,
    )

    # ② 单 IP：1 小时 10 次
    max_req, window, message = RATE_LIMIT_RULES["reset_ip"]
    await _check_counter(
        redis_client,
        f"rate_limit:reset_ip:{client_ip}",
        max_req,
        window,
        message,
    )

    # ③ 失败次数预检：10 分钟 5 次失败则直接拒绝
    max_req, window, message = RATE_LIMIT_RULES["reset_fail"]
    fail_key = f"rate_limit:reset_fail:{client_ip}"
    try:
        current = await redis_client.get(fail_key)
        if current is not None and int(current) >= max_req:
            logger.warning("重置密码失败次数超限 ip=%s", client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
                headers={"Retry-After": str(window)},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("重置失败计数预检异常 ip=%s: %s", client_ip, e)


async def increment_reset_password_failure(request) -> None:
    """
    记录一次重置密码失败尝试，并计入失败计数窗口。
    Redis 不可用时静默（仅记录日志），不阻断业务。
    """
    client_ip = IPUtils.get_client_ip(request)
    redis_client = await get_redis_client()

    _, window, _ = RATE_LIMIT_RULES["reset_fail"]
    fail_key = f"rate_limit:reset_fail:{client_ip}"
    try:
        current = await redis_client.get(fail_key)
        if current is None:
            await redis_client.setex(fail_key, window, 1)
        else:
            await redis_client.setex(fail_key, window, str(int(current) + 1))
    except Exception as e:
        logger.error("记录重置失败计数异常 ip=%s: %s", client_ip, e)


__all__ = [
    "check_forgot_password_rate_limit",
    "check_reset_password_rate_limit",
    "increment_reset_password_failure",
]
