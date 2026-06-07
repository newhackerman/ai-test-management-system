"""
MCP配置管理模块

本模块负责加载和管理MCP服务器配置，支持从多种来源加载配置：
1. JSON配置文件
2. 环境变量
3. 数据库配置
4. 动态配置更新

主要功能：
- 配置文件解析和验证
- 配置热重载
- 配置合并策略
- 配置安全性检查
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import asyncio

from .mcp_client import MCPServerConfig

logger = logging.getLogger(__name__)


@dataclass
class MCPConfigSource:
    """MCP配置源"""
    type: str  # "file", "env", "database"
    path: Optional[str] = None
    priority: int = 0  # 优先级，数字越大优先级越高


class MCPConfigManager:
    """MCP配置管理器"""
    
    def __init__(self):
        self.configs: Dict[str, MCPServerConfig] = {}
        self.config_sources: List[MCPConfigSource] = []
        self.watchers: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        
    async def load_from_file(self, config_path: Union[str, Path], watch: bool = True) -> bool:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
            watch: 是否监控文件变化
            
        Returns:
            bool: 是否加载成功
        """
        try:
            config_path = Path(config_path)
            
            if not config_path.exists():
                logger.warning(f"MCP config file not found: {config_path}")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 解析配置
            servers_config = config_data.get('mcpServers', {})
            
            async with self._lock:
                for server_name, server_config in servers_config.items():
                    try:
                        # 创建服务器配置对象
                        mcp_config = self._parse_server_config(server_name, server_config)
                        self.configs[server_name] = mcp_config
                        
                        logger.debug(f"Loaded MCP server config: {server_name}")
                        
                    except Exception as e:
                        logger.error(f"Error parsing config for server {server_name}: {str(e)}")
                        continue
            
            # 添加配置源
            source = MCPConfigSource(type="file", path=str(config_path), priority=1)
            if source not in self.config_sources:
                self.config_sources.append(source)
            
            # 启动文件监控
            if watch:
                watcher_task = asyncio.create_task(self._watch_config_file(config_path))
                self.watchers.append(watcher_task)
            
            logger.info(f"Successfully loaded MCP config from: {config_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MCP config file {config_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error loading MCP config from {config_path}: {str(e)}")
            return False
    
    async def load_from_env(self) -> bool:
        """
        从环境变量加载配置
        
        环境变量格式：
        MCP_SERVER_<NAME>_COMMAND=uvx
        MCP_SERVER_<NAME>_ARGS=["package@latest"]
        MCP_SERVER_<NAME>_ENV_<KEY>=value
        MCP_SERVER_<NAME>_DISABLED=false
        
        Returns:
            bool: 是否加载成功
        """
        try:
            env_configs = {}
            
            # 扫描环境变量
            for key, value in os.environ.items():
                if key.startswith('MCP_SERVER_'):
                    parts = key.split('_')
                    if len(parts) < 3:
                        continue
                    
                    server_name = parts[2].lower()
                    config_key = '_'.join(parts[3:]).lower()
                    
                    if server_name not in env_configs:
                        env_configs[server_name] = {}
                    
                    # 解析配置值
                    if config_key == 'args':
                        try:
                            env_configs[server_name]['args'] = json.loads(value)
                        except json.JSONDecodeError:
                            env_configs[server_name]['args'] = [value]
                    elif config_key == 'disabled':
                        env_configs[server_name]['disabled'] = value.lower() in ('true', '1', 'yes')
                    elif config_key.startswith('env_'):
                        env_key = config_key[4:].upper()
                        if 'env' not in env_configs[server_name]:
                            env_configs[server_name]['env'] = {}
                        env_configs[server_name]['env'][env_key] = value
                    elif config_key in ['timeout', 'max_retries', 'health_check_interval']:
                        # 转换数字类型
                        try:
                            env_configs[server_name][config_key] = int(value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {config_key}: {value}")
                            env_configs[server_name][config_key] = value
                    elif config_key == 'retry_delay':
                        # 转换浮点数类型
                        try:
                            env_configs[server_name][config_key] = float(value)
                        except ValueError:
                            logger.warning(f"Invalid float value for {config_key}: {value}")
                            env_configs[server_name][config_key] = value
                    else:
                        env_configs[server_name][config_key] = value
            
            # 创建配置对象
            async with self._lock:
                for server_name, server_config in env_configs.items():
                    try:
                        mcp_config = self._parse_server_config(server_name, server_config)
                        self.configs[server_name] = mcp_config
                        
                        logger.debug(f"Loaded MCP server config from env: {server_name}")
                        
                    except Exception as e:
                        logger.error(f"Error parsing env config for server {server_name}: {str(e)}")
                        continue
            
            # 添加配置源
            source = MCPConfigSource(type="env", priority=2)
            if source not in self.config_sources:
                self.config_sources.append(source)
            
            if env_configs:
                logger.info(f"Successfully loaded {len(env_configs)} MCP server configs from environment")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading MCP config from environment: {str(e)}")
            return False
    
    def _parse_server_config(self, server_name: str, config_data: Dict[str, Any]) -> MCPServerConfig:
        """
        解析服务器配置
        
        Args:
            server_name: 服务器名称
            config_data: 配置数据
            
        Returns:
            MCPServerConfig: 解析后的配置对象
        """
        # 必需字段验证
        if 'command' not in config_data:
            raise ValueError(f"Missing 'command' in config for server {server_name}")
        
        # 创建配置对象
        config = MCPServerConfig(
            name=server_name,
            command=config_data['command'],
            args=config_data.get('args', []),
            env=config_data.get('env', {}),
            timeout=config_data.get('timeout', 30),
            max_retries=config_data.get('max_retries', 3),
            retry_delay=config_data.get('retry_delay', 1.0),
            health_check_interval=config_data.get('health_check_interval', 60),
            disabled=config_data.get('disabled', False),
            auto_approve=config_data.get('autoApprove', [])
        )
        
        # 配置验证
        self._validate_server_config(config)
        
        return config
    
    def _validate_server_config(self, config: MCPServerConfig):
        """
        验证服务器配置
        
        Args:
            config: 服务器配置
            
        Raises:
            ValueError: 配置无效时
        """
        if not config.name or not config.name.strip():
            raise ValueError("Server name cannot be empty")
        
        if not config.command or not config.command.strip():
            raise ValueError(f"Command cannot be empty for server {config.name}")
        
        if config.timeout <= 0:
            raise ValueError(f"Timeout must be positive for server {config.name}")
        
        if config.max_retries < 0:
            raise ValueError(f"Max retries cannot be negative for server {config.name}")
        
        if config.retry_delay < 0:
            raise ValueError(f"Retry delay cannot be negative for server {config.name}")
        
        if config.health_check_interval <= 0:
            raise ValueError(f"Health check interval must be positive for server {config.name}")
    
    async def _watch_config_file(self, config_path: Path):
        """
        监控配置文件变化
        
        Args:
            config_path: 配置文件路径
        """
        try:
            last_modified = config_path.stat().st_mtime
            
            while True:
                await asyncio.sleep(1)  # 每秒检查一次
                
                try:
                    current_modified = config_path.stat().st_mtime
                    
                    if current_modified > last_modified:
                        logger.info(f"MCP config file changed, reloading: {config_path}")
                        
                        # 重新加载配置
                        await self.load_from_file(config_path, watch=False)
                        
                        last_modified = current_modified
                        
                except FileNotFoundError:
                    logger.warning(f"MCP config file deleted: {config_path}")
                    break
                except Exception as e:
                    logger.error(f"Error checking config file {config_path}: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.debug(f"Config file watcher cancelled for: {config_path}")
        except Exception as e:
            logger.error(f"Config file watcher error for {config_path}: {str(e)}")
    
    async def get_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        获取服务器配置
        
        Args:
            server_name: 服务器名称
            
        Returns:
            MCPServerConfig: 服务器配置，不存在时返回None
        """
        async with self._lock:
            return self.configs.get(server_name)
    
    async def get_all_configs(self) -> Dict[str, MCPServerConfig]:
        """获取所有服务器配置"""
        async with self._lock:
            return self.configs.copy()
    
    async def add_config(self, config: MCPServerConfig) -> bool:
        """
        添加服务器配置
        
        Args:
            config: 服务器配置
            
        Returns:
            bool: 是否添加成功
        """
        try:
            self._validate_server_config(config)
            
            async with self._lock:
                self.configs[config.name] = config
            
            logger.info(f"Added MCP server config: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding MCP server config {config.name}: {str(e)}")
            return False
    
    async def remove_config(self, server_name: str) -> bool:
        """
        移除服务器配置
        
        Args:
            server_name: 服务器名称
            
        Returns:
            bool: 是否移除成功
        """
        async with self._lock:
            if server_name in self.configs:
                del self.configs[server_name]
                logger.info(f"Removed MCP server config: {server_name}")
                return True
            else:
                logger.warning(f"MCP server config not found: {server_name}")
                return False
    
    async def update_config(self, server_name: str, updates: Dict[str, Any]) -> bool:
        """
        更新服务器配置
        
        Args:
            server_name: 服务器名称
            updates: 更新的配置项
            
        Returns:
            bool: 是否更新成功
        """
        try:
            async with self._lock:
                if server_name not in self.configs:
                    logger.warning(f"MCP server config not found: {server_name}")
                    return False
                
                current_config = self.configs[server_name]
                
                # 创建更新后的配置
                config_dict = asdict(current_config)
                config_dict.update(updates)
                
                updated_config = MCPServerConfig(**config_dict)
                self._validate_server_config(updated_config)
                
                self.configs[server_name] = updated_config
            
            logger.info(f"Updated MCP server config: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating MCP server config {server_name}: {str(e)}")
            return False
    
    async def save_to_file(self, config_path: Union[str, Path]) -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            config_path = Path(config_path)
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 构建配置数据
            config_data = {
                "mcpServers": {}
            }
            
            async with self._lock:
                for server_name, server_config in self.configs.items():
                    config_dict = asdict(server_config)
                    # 移除name字段，因为它是key
                    config_dict.pop('name', None)
                    config_data["mcpServers"][server_name] = config_dict
            
            # 写入文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully saved MCP config to: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving MCP config to {config_path}: {str(e)}")
            return False
    
    async def reload_all(self) -> bool:
        """
        重新加载所有配置源
        
        Returns:
            bool: 是否重新加载成功
        """
        try:
            # 清空现有配置
            async with self._lock:
                self.configs.clear()
            
            # 按优先级排序配置源
            sorted_sources = sorted(self.config_sources, key=lambda x: x.priority)
            
            # 重新加载所有配置源
            for source in sorted_sources:
                if source.type == "file" and source.path:
                    await self.load_from_file(source.path, watch=False)
                elif source.type == "env":
                    await self.load_from_env()
            
            logger.info("Successfully reloaded all MCP configurations")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading MCP configurations: {str(e)}")
            return False
    
    async def shutdown(self):
        """关闭配置管理器"""
        logger.info("Shutting down MCP config manager")
        
        # 取消所有监控任务
        for watcher in self.watchers:
            watcher.cancel()
        
        if self.watchers:
            await asyncio.gather(*self.watchers, return_exceptions=True)
        
        self.watchers.clear()
        self.config_sources.clear()
        
        async with self._lock:
            self.configs.clear()
        
        logger.info("MCP config manager shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取配置管理器统计信息"""
        return {
            "total_servers": len(self.configs),
            "enabled_servers": len([c for c in self.configs.values() if not c.disabled]),
            "disabled_servers": len([c for c in self.configs.values() if c.disabled]),
            "config_sources": len(self.config_sources),
            "active_watchers": len(self.watchers)
        }


# 全局配置管理器实例
_config_manager: Optional[MCPConfigManager] = None


async def get_mcp_config_manager() -> MCPConfigManager:
    """获取全局MCP配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MCPConfigManager()
    return _config_manager


async def load_mcp_config(config_path: Optional[str] = None, 
                         load_env: bool = True) -> MCPConfigManager:
    """
    加载MCP配置
    
    Args:
        config_path: 配置文件路径，None表示使用默认路径
        load_env: 是否加载环境变量配置
        
    Returns:
        MCPConfigManager: 配置管理器实例
    """
    manager = await get_mcp_config_manager()
    
    # 默认配置文件路径
    if config_path is None:
        # 尝试多个可能的配置文件位置
        possible_paths = [
            ".kiro/settings/mcp.json",
            "mcp.json",
            "config/mcp.json",
            os.path.expanduser("~/.kiro/settings/mcp.json")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    # 加载文件配置
    if config_path and os.path.exists(config_path):
        await manager.load_from_file(config_path)
    
    # 加载环境变量配置
    if load_env:
        await manager.load_from_env()
    
    return manager


# 便捷函数
async def get_mcp_server_config(server_name: str) -> Optional[MCPServerConfig]:
    """获取MCP服务器配置的便捷函数"""
    manager = await get_mcp_config_manager()
    return await manager.get_config(server_name)


async def get_all_mcp_configs() -> Dict[str, MCPServerConfig]:
    """获取所有MCP服务器配置的便捷函数"""
    manager = await get_mcp_config_manager()
    return await manager.get_all_configs()