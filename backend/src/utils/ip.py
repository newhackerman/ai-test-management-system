"""
IP地址工具类
"""
from typing import Optional
from fastapi import Request


class IPUtils:
    """IP地址工具类"""
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """
        获取客户端IP地址
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            客户端IP地址
        """
        # 检查是否有代理服务器
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # 可能有多个IP，取第一个
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            # 直接获取远程地址
            ip = request.client.host if request.client else "127.0.0.1"
        
        return ip
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """
        判断是否为私有IP地址
        
        Args:
            ip: IP地址
            
        Returns:
            是否为私有IP
        """
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except ValueError:
            return False
    
    @staticmethod
    def is_local_ip(ip: str) -> bool:
        """
        判断是否为本地IP地址
        
        Args:
            ip: IP地址
            
        Returns:
            是否为本地IP
        """
        return ip in ("127.0.0.1", "::1", "localhost")
    
    @staticmethod
    def get_ip_location(ip: str) -> Optional[dict]:
        """
        获取IP地址地理位置信息
        
        Args:
            ip: IP地址
            
        Returns:
            地理位置信息字典
        """
        # 这里可以集成第三方IP地理位置服务
        # 例如：ip-api.com, ipinfo.io, maxmind geoip2等
        # 为了简化，这里返回空字典
        return {}