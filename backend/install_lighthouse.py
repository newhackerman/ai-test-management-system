#!/usr/bin/env python3
"""
Lighthouse安装脚本

本脚本用于安装和配置Lighthouse性能监控工具
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(command, check=True, shell=True):
    """执行命令"""
    logger.info(f"执行命令: {command}")
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(f"输出: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e}")
        if e.stderr:
            logger.error(f"错误信息: {e.stderr.strip()}")
        if check:
            raise
        return e


def check_node_npm():
    """检查Node.js和npm是否已安装"""
    logger.info("检查Node.js和npm...")
    
    try:
        # 检查Node.js
        node_result = run_command("node --version", check=False)
        if node_result.returncode == 0:
            logger.info(f"Node.js版本: {node_result.stdout.strip()}")
        else:
            logger.error("Node.js未安装")
            return False
        
        # 检查npm
        npm_result = run_command("npm --version", check=False)
        if npm_result.returncode == 0:
            logger.info(f"npm版本: {npm_result.stdout.strip()}")
        else:
            logger.error("npm未安装")
            return False
        
        return True
    except Exception as e:
        logger.error(f"检查Node.js/npm失败: {e}")
        return False


def install_lighthouse():
    """安装Lighthouse"""
    logger.info("开始安装Lighthouse...")
    
    try:
        # 全局安装Lighthouse
        result = run_command("npm install -g lighthouse")
        
        if result.returncode == 0:
            logger.info("Lighthouse安装成功")
            
            # 验证安装
            version_result = run_command("lighthouse --version", check=False)
            if version_result.returncode == 0:
                logger.info(f"Lighthouse版本: {version_result.stdout.strip()}")
                return True
            else:
                logger.error("Lighthouse安装验证失败")
                return False
        else:
            logger.error("Lighthouse安装失败")
            return False
            
    except Exception as e:
        logger.error(f"安装Lighthouse时出错: {e}")
        return False


def install_chrome_dependencies():
    """安装Chrome依赖（Linux系统）"""
    if sys.platform.startswith('linux'):
        logger.info("检测到Linux系统，安装Chrome依赖...")
        
        try:
            # 更新包列表
            run_command("apt-get update", check=False)
            
            # 安装Chrome依赖
            dependencies = [
                "wget",
                "gnupg",
                "ca-certificates",
                "apt-transport-https",
                "software-properties-common"
            ]
            
            for dep in dependencies:
                run_command(f"apt-get install -y {dep}", check=False)
            
            # 添加Google Chrome仓库
            run_command("wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -", check=False)
            run_command('echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list', check=False)
            
            # 更新并安装Chrome
            run_command("apt-get update", check=False)
            run_command("apt-get install -y google-chrome-stable", check=False)
            
            logger.info("Chrome依赖安装完成")
            
        except Exception as e:
            logger.warning(f"安装Chrome依赖时出错: {e}")
            logger.info("请手动安装Chrome浏览器")


def create_lighthouse_directories():
    """创建Lighthouse相关目录"""
    logger.info("创建Lighthouse目录...")
    
    directories = [
        "lighthouse_reports",
        "lighthouse_configs"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        logger.info(f"创建目录: {dir_path.absolute()}")


def create_lighthouse_config():
    """创建Lighthouse配置文件"""
    logger.info("创建Lighthouse配置文件...")
    
    config_content = """{
  "extends": "lighthouse:default",
  "settings": {
    "onlyAudits": [
      "first-contentful-paint",
      "largest-contentful-paint",
      "cumulative-layout-shift",
      "max-potential-fid",
      "speed-index",
      "total-blocking-time",
      "interactive"
    ],
    "skipAudits": [
      "uses-http2",
      "uses-long-cache-ttl"
    ],
    "emulatedFormFactor": "desktop",
    "throttling": {
      "rttMs": 40,
      "throughputKbps": 10240,
      "cpuSlowdownMultiplier": 1,
      "requestLatencyMs": 0,
      "downloadThroughputKbps": 0,
      "uploadThroughputKbps": 0
    },
    "auditMode": false,
    "gatherMode": false,
    "disableDeviceEmulation": false,
    "disableStorageReset": false,
    "locale": "zh-CN"
  }
}"""
    
    config_path = Path("lighthouse_configs/default.json")
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    logger.info(f"配置文件已创建: {config_path.absolute()}")


def test_lighthouse_installation():
    """测试Lighthouse安装"""
    logger.info("测试Lighthouse安装...")
    
    try:
        # 测试基本命令
        result = run_command("lighthouse --help", check=False)
        if result.returncode != 0:
            logger.error("Lighthouse命令测试失败")
            return False
        
        # 测试版本命令
        result = run_command("lighthouse --version", check=False)
        if result.returncode == 0:
            logger.info(f"Lighthouse版本: {result.stdout.strip()}")
        
        logger.info("Lighthouse安装测试通过")
        return True
        
    except Exception as e:
        logger.error(f"测试Lighthouse安装时出错: {e}")
        return False


def update_environment_variables():
    """更新环境变量"""
    logger.info("更新环境变量...")
    
    env_vars = {
        'LIGHTHOUSE_ENABLED': 'true',
        'LIGHTHOUSE_REPORTS_DIR': 'lighthouse_reports',
        'LIGHTHOUSE_CONFIG_DIR': 'lighthouse_configs'
    }
    
    env_file = Path('.env')
    
    # 读取现有环境变量
    existing_vars = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key] = value
    
    # 更新环境变量
    existing_vars.update(env_vars)
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write("# Lighthouse配置\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
        
        f.write("\n# 其他环境变量\n")
        for key, value in existing_vars.items():
            if key not in env_vars:
                f.write(f"{key}={value}\n")
    
    logger.info("环境变量已更新")


def main():
    """主函数"""
    logger.info("开始安装Lighthouse性能监控工具...")
    
    try:
        # 1. 检查Node.js和npm
        if not check_node_npm():
            logger.error("请先安装Node.js和npm")
            logger.info("下载地址: https://nodejs.org/")
            return False
        
        # 2. 安装Chrome依赖（Linux）
        install_chrome_dependencies()
        
        # 3. 安装Lighthouse
        if not install_lighthouse():
            logger.error("Lighthouse安装失败")
            return False
        
        # 4. 创建目录
        create_lighthouse_directories()
        
        # 5. 创建配置文件
        create_lighthouse_config()
        
        # 6. 测试安装
        if not test_lighthouse_installation():
            logger.error("Lighthouse安装测试失败")
            return False
        
        # 7. 更新环境变量
        update_environment_variables()
        
        logger.info("✅ Lighthouse安装完成！")
        logger.info("现在可以使用Lighthouse性能监控功能了")
        
        return True
        
    except Exception as e:
        logger.error(f"安装过程中出现错误: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)