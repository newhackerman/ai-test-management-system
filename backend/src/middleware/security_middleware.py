"""
安全中间件

提供API安全防护功能，包括：
- 输入验证中间件
- SQL注入防护
- XSS防护
- 速率限制
- 滥用防护
"""
import re
import json
import time
import hashlib
import logging
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import BaseModel, validator
import html
import bleach

logger = logging.getLogger(__name__)


class SecurityConfig:
    """安全配置"""
    
    # SQL注入检测模式
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(--|#|/\*|\*/)",
        r"(\bUNION\s+(ALL\s+)?SELECT\b)",
        r"(\bINTO\s+(OUT|DUMP)FILE\b)",
        r"(\bLOAD_FILE\s*\()",
        r"(\bEXEC\s*\()",
        r"(\bEVAL\s*\()",
        r"(\bCAST\s*\()",
        r"(\bCONVERT\s*\()",
        r"(\bSUBSTRING\s*\()",
        r"(\bCHAR\s*\()",
        r"(\bASCII\s*\()",
        r"(\bCONCAT\s*\()",
        r"(\bHEX\s*\()",
        r"(\bUNHEX\s*\()",
        r"(\bMD5\s*\()",
        r"(\bSHA1\s*\()",
        r"(\bSLEEP\s*\()",
        r"(\bBENCHMARK\s*\()",
        r"(\bWAITFOR\s+DELAY\b)",
        r"(\bIF\s*\(\s*\d+\s*=\s*\d+)",
        r"(\bCASE\s+WHEN\b)",
        r"(\b0x[0-9a-fA-F]+)",
        r"(\b\d+\s*;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION))",
    ]
    
    # XSS检测模式
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
        r"<applet[^>]*>.*?</applet>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"url\s*\(",
        r"@import",
        r"<\s*\w+[^>]*\s+on\w+\s*=",
        r"<\s*\w+[^>]*\s+href\s*=\s*['\"]?\s*javascript:",
        r"<\s*\w+[^>]*\s+src\s*=\s*['\"]?\s*javascript:",
        r"<\s*\w+[^>]*\s+style\s*=.*?expression\s*\(",
        r"<\s*\w+[^>]*\s+style\s*=.*?javascript:",
        r"<\s*\w+[^>]*\s+style\s*=.*?@import",
        r"<\s*\w+[^>]*\s+style\s*=.*?url\s*\(",
    ]
    
    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl', '.sh', '.ps1'
    }
    
    # 速率限制配置
    RATE_LIMIT_RULES = {
        'default': {'requests': 100, 'window': 60},  # 默认：60秒内100次请求
        'auth': {'requests': 5, 'window': 60},       # 认证：60秒内5次请求
        'upload': {'requests': 10, 'window': 60},    # 上传：60秒内10次请求
        'api': {'requests': 200, 'window': 60},      # API：60秒内200次请求
    }
    
    # 最大请求大小（字节）
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 最大字段长度
    MAX_FIELD_LENGTH = 10000
    
    # 允许的内容类型
    ALLOWED_CONTENT_TYPES = {
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain'
    }


class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.blocked_ips = defaultdict(datetime)
    
    def is_allowed(self, identifier: str, rule_name: str = 'default') -> bool:
        """检查是否允许请求"""
        now = time.time()
        rule = SecurityConfig.RATE_LIMIT_RULES.get(rule_name, SecurityConfig.RATE_LIMIT_RULES['default'])
        
        # 检查是否被阻止
        if identifier in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[identifier]:
                return False
            else:
                del self.blocked_ips[identifier]
        
        # 清理过期请求
        window_start = now - rule['window']
        request_times = self.requests[identifier]
        
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # 检查请求数量
        if len(request_times) >= rule['requests']:
            # 阻止IP一段时间
            self.blocked_ips[identifier] = datetime.utcnow() + timedelta(minutes=5)
            logger.warning(f"IP {identifier} 触发速率限制，规则: {rule_name}")
            return False
        
        # 记录请求
        request_times.append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, rule_name: str = 'default') -> int:
        """获取剩余请求数"""
        now = time.time()
        rule = SecurityConfig.RATE_LIMIT_RULES.get(rule_name, SecurityConfig.RATE_LIMIT_RULES['default'])
        
        # 清理过期请求
        window_start = now - rule['window']
        request_times = self.requests[identifier]
        
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        return max(0, rule['requests'] - len(request_times))


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_sql_injection(text: str) -> bool:
        """检测SQL注入"""
        if not text:
            return True
        
        text_upper = text.upper()
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.warning(f"检测到SQL注入尝试: {pattern}")
                return False
        
        return True
    
    @staticmethod
    def validate_xss(text: str) -> bool:
        """检测XSS攻击"""
        if not text:
            return True
        
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"检测到XSS攻击尝试: {pattern}")
                return False
        
        return True
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """清理HTML内容"""
        if not text:
            return text
        
        # 允许的HTML标签和属性
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        allowed_attributes = {}
        
        # 使用bleach清理HTML
        cleaned = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        
        # HTML转义
        return html.escape(cleaned)
    
    @staticmethod
    def validate_file_upload(filename: str, content_type: str) -> bool:
        """验证文件上传"""
        if not filename:
            return False
        
        # 检查文件扩展名
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext in SecurityConfig.DANGEROUS_EXTENSIONS:
            logger.warning(f"危险文件扩展名: {file_ext}")
            return False
        
        # 检查内容类型
        safe_content_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'text/plain', 'text/csv',
            'application/pdf',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        if content_type not in safe_content_types:
            logger.warning(f"不安全的内容类型: {content_type}")
            return False
        
        return True
    
    @staticmethod
    def validate_field_length(text: str, max_length: int = None) -> bool:
        """验证字段长度"""
        if not text:
            return True
        
        max_len = max_length or SecurityConfig.MAX_FIELD_LENGTH
        if len(text) > max_len:
            logger.warning(f"字段长度超限: {len(text)} > {max_len}")
            return False
        
        return True
    
    @staticmethod
    def validate_json_structure(data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
        """验证JSON结构深度"""
        if current_depth > max_depth:
            logger.warning(f"JSON结构深度超限: {current_depth} > {max_depth}")
            return False
        
        if isinstance(data, dict):
            for value in data.values():
                if not InputValidator.validate_json_structure(value, max_depth, current_depth + 1):
                    return False
        elif isinstance(data, list):
            for item in data:
                if not InputValidator.validate_json_structure(item, max_depth, current_depth + 1):
                    return False
        
        return True


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.validator = InputValidator()
        
        # 可疑活动检测
        self.suspicious_ips = defaultdict(int)
        self.attack_patterns = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        start_time = time.time()
        
        try:
            # 获取客户端IP
            client_ip = self._get_client_ip(request)
            
            # 检查请求大小
            if not await self._check_request_size(request):
                return self._create_error_response(
                    "请求大小超限", 
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            
            # 检查内容类型
            if not self._check_content_type(request):
                return self._create_error_response(
                    "不支持的内容类型", 
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                )
            
            # 速率限制检查
            if not self._check_rate_limit(request, client_ip):
                return self._create_error_response(
                    "请求过于频繁，请稍后再试", 
                    status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 输入验证
            validation_result = await self._validate_input(request)
            if not validation_result['valid']:
                self._record_suspicious_activity(client_ip, validation_result['reason'])
                return self._create_error_response(
                    "输入验证失败", 
                    status.HTTP_400_BAD_REQUEST
                )
            
            # 处理请求
            response = await call_next(request)
            
            # 添加安全头
            self._add_security_headers(response)
            
            # 记录请求日志
            duration = int((time.time() - start_time) * 1000)
            await self._log_request(request, response, client_ip, duration)
            
            return response
            
        except Exception as e:
            logger.error(f"安全中间件处理异常: {str(e)}")
            return self._create_error_response(
                "服务器内部错误", 
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_request_size(self, request: Request) -> bool:
        """检查请求大小"""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > SecurityConfig.MAX_REQUEST_SIZE:
                    logger.warning(f"请求大小超限: {size} > {SecurityConfig.MAX_REQUEST_SIZE}")
                    return False
            except ValueError:
                return False
        
        return True
    
    def _check_content_type(self, request: Request) -> bool:
        """检查内容类型"""
        content_type = request.headers.get("content-type", "").split(";")[0].strip()
        
        # GET请求不需要检查内容类型
        if request.method == "GET":
            return True
        
        # 检查是否为允许的内容类型
        if content_type and content_type not in SecurityConfig.ALLOWED_CONTENT_TYPES:
            logger.warning(f"不允许的内容类型: {content_type}")
            return False
        
        return True
    
    def _check_rate_limit(self, request: Request, client_ip: str) -> bool:
        """检查速率限制"""
        # 根据路径确定规则
        path = request.url.path
        rule_name = 'default'
        
        if '/auth/' in path:
            rule_name = 'auth'
        elif '/upload/' in path:
            rule_name = 'upload'
        elif '/api/' in path:
            rule_name = 'api'
        
        return self.rate_limiter.is_allowed(client_ip, rule_name)
    
    async def _validate_input(self, request: Request) -> Dict[str, Any]:
        """验证输入数据"""
        try:
            # 验证URL参数
            for key, value in request.query_params.items():
                if not self.validator.validate_field_length(value):
                    return {'valid': False, 'reason': f'URL参数长度超限: {key}'}
                
                if not self.validator.validate_sql_injection(value):
                    return {'valid': False, 'reason': f'SQL注入检测: {key}'}
                
                if not self.validator.validate_xss(value):
                    return {'valid': False, 'reason': f'XSS攻击检测: {key}'}
            
            # 验证请求体
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "").split(";")[0].strip()
                
                if content_type == "application/json":
                    try:
                        body = await request.body()
                        if body:
                            data = json.loads(body)
                            
                            # 验证JSON结构深度
                            if not self.validator.validate_json_structure(data):
                                return {'valid': False, 'reason': 'JSON结构深度超限'}
                            
                            # 递归验证JSON数据
                            validation_result = self._validate_json_data(data)
                            if not validation_result['valid']:
                                return validation_result
                    
                    except json.JSONDecodeError:
                        return {'valid': False, 'reason': 'JSON格式错误'}
            
            return {'valid': True, 'reason': None}
            
        except Exception as e:
            logger.error(f"输入验证异常: {str(e)}")
            return {'valid': False, 'reason': '输入验证异常'}
    
    def _validate_json_data(self, data: Any, path: str = "") -> Dict[str, Any]:
        """递归验证JSON数据"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # 验证键名
                if not self.validator.validate_field_length(str(key)):
                    return {'valid': False, 'reason': f'字段名长度超限: {current_path}'}
                
                # 递归验证值
                result = self._validate_json_data(value, current_path)
                if not result['valid']:
                    return result
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                result = self._validate_json_data(item, current_path)
                if not result['valid']:
                    return result
        
        elif isinstance(data, str):
            if not self.validator.validate_field_length(data):
                return {'valid': False, 'reason': f'字段长度超限: {path}'}
            
            if not self.validator.validate_sql_injection(data):
                return {'valid': False, 'reason': f'SQL注入检测: {path}'}
            
            if not self.validator.validate_xss(data):
                return {'valid': False, 'reason': f'XSS攻击检测: {path}'}
        
        return {'valid': True, 'reason': None}
    
    def _add_security_headers(self, response: Response):
        """添加安全头"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    def _record_suspicious_activity(self, client_ip: str, reason: str):
        """记录可疑活动"""
        self.suspicious_ips[client_ip] += 1
        self.attack_patterns[client_ip].append({
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 如果可疑活动过多，记录安全事件
        if self.suspicious_ips[client_ip] > 5:
            logger.critical(f"检测到可疑IP: {client_ip}, 攻击次数: {self.suspicious_ips[client_ip]}")
    
    async def _log_request(self, request: Request, response: Response, client_ip: str, duration: int):
        """记录请求日志"""
        # 这里可以集成到审计服务
        log_data = {
            'method': request.method,
            'path': request.url.path,
            'client_ip': client_ip,
            'status_code': response.status_code,
            'duration_ms': duration,
            'user_agent': request.headers.get('user-agent', ''),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 记录到日志文件
        if response.status_code >= 400:
            logger.warning(f"HTTP错误: {json.dumps(log_data)}")
        else:
            logger.info(f"HTTP请求: {json.dumps(log_data)}")
    
    def _create_error_response(self, message: str, status_code: int) -> JSONResponse:
        """创建错误响应"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": True,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class SecurityValidator(BaseModel):
    """安全验证器基类"""
    
    @validator('*', pre=True)
    def validate_security(cls, v):
        """通用安全验证"""
        if isinstance(v, str):
            # 检查字段长度
            if not InputValidator.validate_field_length(v):
                raise ValueError("字段长度超限")
            
            # 检查SQL注入
            if not InputValidator.validate_sql_injection(v):
                raise ValueError("检测到SQL注入尝试")
            
            # 检查XSS
            if not InputValidator.validate_xss(v):
                raise ValueError("检测到XSS攻击尝试")
        
        return v


def create_security_middleware() -> SecurityMiddleware:
    """创建安全中间件实例"""
    return SecurityMiddleware