# Lighthouse性能监控集成

本文档介绍如何使用集成的Lighthouse性能监控功能来分析Web应用的性能。

## 功能概述

Lighthouse性能监控集成提供以下功能：

- **Web性能审计**: 对指定URL进行全面的性能分析
- **多设备支持**: 支持桌面端和移动端性能测试
- **历史数据追踪**: 存储和对比历史性能数据
- **性能指标分析**: 提供详细的性能指标和优化建议
- **API接口**: 完整的REST API支持自动化测试

## 核心性能指标

### Web Vitals 核心指标

1. **首次内容绘制 (FCP)**: 页面开始加载到任何内容渲染到屏幕上的时间
2. **最大内容绘制 (LCP)**: 页面开始加载到最大文本块或图像元素渲染完成的时间
3. **累积布局偏移 (CLS)**: 页面加载期间发生的所有意外布局偏移的累积分数
4. **首次输入延迟 (FID)**: 用户首次与页面交互到浏览器响应该交互的时间

### 其他重要指标

- **速度指数 (SI)**: 页面内容可见填充的速度
- **总阻塞时间 (TBT)**: FCP和TTI之间的总时间
- **可交互时间 (TTI)**: 页面完全可交互的时间

## 安装和配置

### 1. 安装Lighthouse

```bash
# 全局安装Lighthouse
npm install -g lighthouse

# 或者使用安装脚本
python backend/install_lighthouse.py
```

### 2. 环境配置

在`.env`文件中添加以下配置：

```bash
# Lighthouse配置
LIGHTHOUSE_ENABLED=true
LIGHTHOUSE_REPORTS_DIR=lighthouse_reports
LIGHTHOUSE_CONFIG_DIR=lighthouse_configs
```

### 3. 数据库迁移

运行数据库迁移创建必要的表：

```bash
# 运行Lighthouse相关的数据库迁移
python backend/src/migrations/010_create_lighthouse_results_table.py
```

## API使用指南

### 1. 运行性能审计

```http
POST /api/v1/performance/lighthouse/audit
Content-Type: application/json
Authorization: Bearer <your-token>

{
  "url": "https://example.com",
  "mobile": false,
  "throttling": true,
  "categories": ["performance", "accessibility", "best-practices", "seo"]
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "audit_id": "uuid-string",
    "url": "https://example.com",
    "device_type": "desktop",
    "lighthouse_version": "12.8.2",
    "scores": {
      "performance": 95,
      "accessibility": 88,
      "best_practices": 92,
      "seo": 90,
      "pwa": 0
    },
    "metrics": {
      "first_contentful_paint": 1200.5,
      "largest_contentful_paint": 2100.3,
      "cumulative_layout_shift": 0.05,
      "first_input_delay": 50.2,
      "speed_index": 1800.7,
      "total_blocking_time": 150.0,
      "time_to_interactive": 2500.1
    },
    "opportunities": [
      {
        "title": "Optimize images",
        "description": "Properly size images to save cellular data and improve load time.",
        "potential_savings": 500.0,
        "audit_id": "uses-optimized-images"
      }
    ],
    "created_at": "2024-01-15T10:30:00Z"
  },
  "message": "性能审计完成，总体评分: 95/100"
}
```

### 2. 获取历史数据

```http
GET /api/v1/performance/lighthouse/history/https%3A%2F%2Fexample.com?days=30&device_type=desktop
Authorization: Bearer <your-token>
```

### 3. 获取性能摘要

```http
GET /api/v1/performance/lighthouse/summary/https%3A%2F%2Fexample.com?days=7
Authorization: Bearer <your-token>
```

### 4. 性能对比分析

```http
POST /api/v1/performance/lighthouse/compare
Content-Type: application/json
Authorization: Bearer <your-token>

{
  "url": "https://example.com",
  "baseline_date": "2024-01-01T00:00:00Z",
  "comparison_date": "2024-01-15T00:00:00Z"
}
```

### 5. 获取已测试URL列表

```http
GET /api/v1/performance/lighthouse/urls?limit=50
Authorization: Bearer <your-token>
```

## 前端界面使用

### 1. 访问性能监控页面

导航到 `/lighthouse-performance` 页面，或从监控页面点击"Lighthouse性能分析"按钮。

### 2. 运行性能审计

1. 在"性能审计"标签页中输入要测试的URL
2. 选择设备类型（桌面端/移动端）
3. 点击"开始分析"按钮
4. 等待分析完成，查看结果

### 3. 查看历史数据

1. 切换到"历史数据"标签页
2. 从下拉列表中选择要查看的URL
3. 查看性能摘要和历史趋势
4. 分析性能变化和优化效果

### 4. 管理测试URL

在"URL管理"标签页中可以：
- 查看所有已测试的URL
- 查看测试次数和平均评分
- 重新测试或查看历史数据

## 性能优化建议

### 评分标准

- **90-100分**: 优秀 (绿色)
- **50-89分**: 需要改进 (黄色)
- **0-49分**: 较差 (红色)

### 常见优化建议

1. **图片优化**
   - 使用现代图片格式 (WebP, AVIF)
   - 适当调整图片尺寸
   - 实施懒加载

2. **代码优化**
   - 压缩CSS和JavaScript
   - 移除未使用的代码
   - 使用代码分割

3. **网络优化**
   - 启用HTTP/2
   - 使用CDN
   - 优化缓存策略

4. **渲染优化**
   - 优化关键渲染路径
   - 减少布局偏移
   - 预加载关键资源

## 故障排除

### 常见问题

1. **Lighthouse命令未找到**
   ```bash
   # 重新安装Lighthouse
   npm install -g lighthouse
   
   # 检查安装
   lighthouse --version
   ```

2. **Chrome浏览器问题**
   ```bash
   # Linux系统安装Chrome
   wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
   sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
   sudo apt-get update
   sudo apt-get install google-chrome-stable
   ```

3. **权限问题**
   - 确保用户具有管理员、架构师或开发人员角色
   - 检查API认证token是否有效

4. **网络问题**
   - 检查目标URL是否可访问
   - 确保防火墙允许Chrome访问网络
   - 考虑使用代理设置

### 调试模式

启用详细日志来调试问题：

```python
import logging
logging.getLogger('lighthouse_manager').setLevel(logging.DEBUG)
```

## 测试验证

运行集成测试验证功能：

```bash
# 测试Lighthouse基本功能
python backend/test_lighthouse_integration.py

# 测试API接口
python backend/test_lighthouse_api.py
```

## 最佳实践

1. **定期监控**: 建议每日或每周运行性能测试
2. **多设备测试**: 同时测试桌面端和移动端性能
3. **基准对比**: 建立性能基准，定期对比分析
4. **自动化集成**: 将性能测试集成到CI/CD流程中
5. **团队协作**: 分享性能报告，共同优化应用性能

## 扩展功能

### 自定义配置

可以创建自定义Lighthouse配置文件：

```json
{
  "extends": "lighthouse:default",
  "settings": {
    "onlyAudits": ["first-contentful-paint", "largest-contentful-paint"],
    "throttling": {
      "rttMs": 40,
      "throughputKbps": 10240
    }
  }
}
```

### 批量测试

支持批量测试多个URL：

```python
urls = ["https://example1.com", "https://example2.com"]
for url in urls:
    result = await lighthouse_manager.run_audit(url)
    print(f"{url}: {result.scores.performance}")
```

## 支持和反馈

如果遇到问题或有改进建议，请：

1. 查看日志文件获取详细错误信息
2. 检查Lighthouse官方文档
3. 提交问题报告包含完整的错误信息和环境配置

---

**注意**: Lighthouse性能监控需要Chrome浏览器支持，确保系统已正确安装Chrome或Chromium。