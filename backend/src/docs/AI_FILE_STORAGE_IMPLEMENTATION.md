# AI助手文件存储系统实现文档

## 概述

AI助手文件存储系统是为AI自动化测试管理系统设计的企业级文件存储解决方案。该系统支持多种文件类型的上传、存储、管理和分享，为AI助手模块提供完整的文件处理能力。

## 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    AI文件存储系统                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│   API接口层      │   业务逻辑层      │      数据存储层          │
│                │                 │                        │
│ - 文件上传API   │ - 文件存储服务   │   MySQL数据库           │
│ - 文件下载API   │ - 文件管理服务   │   - 文件元数据          │
│ - 文件管理API   │ - 分享链接服务   │   - 分享记录            │
│ - 分享链接API   │ - 清理任务服务   │   - 访问日志            │
│                │                 │                        │
│                │                 │   物理文件存储           │
│                │                 │   - 本地存储            │
│                │                 │   - 云存储(可选)        │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### 数据模型

#### 1. AIFileStorage (文件存储表)
- **基本信息**: 文件名、路径、URL、大小、哈希值
- **文件属性**: 类型、分类、MIME类型
- **存储信息**: 存储提供商、存储桶、区域
- **关联信息**: 用户ID、会话ID、消息ID、模板ID
- **元数据**: 标签、描述、自定义元数据
- **状态管理**: 文件状态、公开性、临时性
- **访问统计**: 访问次数、下载次数、最后访问时间
- **生命周期**: 过期时间、归档时间、删除时间

#### 2. AIFileShare (文件分享表)
- **分享信息**: 分享令牌、分享链接、分享密码
- **权限控制**: 下载权限、预览权限、访问次数限制
- **统计信息**: 下载次数、查看次数、最后访问时间
- **生命周期**: 过期时间、激活状态

#### 3. AIFileAccessLog (文件访问日志表)
- **访问信息**: 操作类型、IP地址、用户代理
- **结果信息**: 成功状态、错误信息、响应时间、传输字节数

## 功能特性

### 1. 文件上传
- **多格式支持**: 图片、文档、音频、视频、压缩包等
- **大小限制**: 按文件分类设置不同的大小限制
- **类型验证**: MIME类型检查和文件头验证
- **安全扫描**: 恶意文件检测和内容过滤
- **重复检测**: 基于SHA256哈希值的重复文件检测
- **批量上传**: 支持多文件同时上传

### 2. 文件存储
- **分类存储**: 按用途分类存储（聊天附件、模板文件等）
- **路径组织**: 按日期和分类自动组织存储路径
- **多存储支持**: 本地存储、阿里云OSS、腾讯云COS、AWS S3、MinIO
- **元数据提取**: 自动提取图片、文档等文件的元数据
- **缩略图生成**: 自动为图片生成缩略图

### 3. 文件管理
- **文件列表**: 支持分页、筛选、排序的文件列表
- **文件搜索**: 基于文件名、标签、内容的搜索功能
- **文件操作**: 重命名、移动、复制、删除等操作
- **批量操作**: 批量删除、批量移动等操作
- **版本控制**: 文件版本管理和历史记录

### 4. 文件分享
- **分享链接**: 生成安全的文件分享链接
- **权限控制**: 设置下载权限、预览权限、访问次数限制
- **密码保护**: 可选的分享密码保护
- **过期控制**: 设置分享链接的过期时间
- **访问统计**: 分享链接的访问统计

### 5. 安全特性
- **访问控制**: 基于用户权限的文件访问控制
- **内容过滤**: 恶意文件和敏感内容检测
- **访问日志**: 详细的文件访问日志记录
- **数据加密**: 敏感数据的加密存储
- **防盗链**: 防止文件被恶意引用

### 6. 生命周期管理
- **自动清理**: 定时清理过期文件和临时文件
- **归档策略**: 长期不使用文件的自动归档
- **存储优化**: 重复文件去重和存储空间优化
- **备份恢复**: 重要文件的备份和恢复机制

## API接口

### 文件上传
```http
POST /api/v1/ai/files/upload
Content-Type: multipart/form-data

- file: 上传的文件
- category: 文件分类
- session_id: 关联会话ID (可选)
- message_id: 关联消息ID (可选)
- description: 文件描述 (可选)
- tags: 文件标签 (可选)
```

### 文件下载
```http
GET /api/v1/ai/files/{file_id}/download
Authorization: Bearer <token>
```

### 文件预览
```http
GET /api/v1/ai/files/{file_id}/preview
Authorization: Bearer <token>
```

### 文件列表
```http
GET /api/v1/ai/files?category={category}&page={page}&size={size}
Authorization: Bearer <token>
```

### 创建分享链接
```http
POST /api/v1/ai/files/{file_id}/share
Authorization: Bearer <token>
Content-Type: application/json

{
  "expires_hours": 24,
  "password": "optional_password",
  "can_download": true,
  "can_preview": true
}
```

### 通过分享链接访问
```http
GET /api/v1/ai/files/share/{share_token}?action=preview&password=xxx
```

## 配置说明

### 环境变量配置
```env
# 基础配置
FILE_STORAGE_STORAGE_ROOT=uploads
FILE_STORAGE_STORAGE_PROVIDER=LOCAL
FILE_STORAGE_BASE_URL=http://localhost:8000

# 文件大小限制 (字节)
FILE_STORAGE_MAX_FILE_SIZE_CHAT_ATTACHMENT=52428800  # 50MB
FILE_STORAGE_MAX_FILE_SIZE_PROMPT_TEMPLATE=1048576   # 1MB
FILE_STORAGE_MAX_FILE_SIZE_EXPORT_DATA=104857600     # 100MB

# 清理配置
FILE_STORAGE_AUTO_CLEANUP_ENABLED=true
FILE_STORAGE_CLEANUP_INTERVAL_HOURS=24
FILE_STORAGE_TEMP_FILE_RETENTION_HOURS=24
FILE_STORAGE_DELETED_FILE_RETENTION_DAYS=30

# 安全配置
FILE_STORAGE_ENABLE_VIRUS_SCAN=false
FILE_STORAGE_ENABLE_CONTENT_FILTER=true
FILE_STORAGE_MAX_SHARE_DURATION_HOURS=168
FILE_STORAGE_REQUIRE_AUTH_FOR_DOWNLOAD=true

# 云存储配置 (可选)
FILE_STORAGE_ALIYUN_OSS_ACCESS_KEY_ID=your_access_key
FILE_STORAGE_ALIYUN_OSS_ACCESS_KEY_SECRET=your_secret_key
FILE_STORAGE_ALIYUN_OSS_BUCKET=your_bucket
FILE_STORAGE_ALIYUN_OSS_ENDPOINT=your_endpoint
```

### 文件分类配置
```python
# 文件分类和对应的存储路径
STORAGE_PATHS = {
    FileCategory.CHAT_ATTACHMENT: "chat_attachments",    # 聊天附件
    FileCategory.PROMPT_TEMPLATE: "prompt_templates",    # 提示词模板
    FileCategory.EXPORT_DATA: "export_data",            # 导出数据
    FileCategory.USER_UPLOAD: "user_uploads",           # 用户上传
    FileCategory.AI_GENERATED: "ai_generated",          # AI生成内容
    FileCategory.SYSTEM_BACKUP: "system_backups",       # 系统备份
    FileCategory.TEMP_FILE: "temp_files"                # 临时文件
}
```

## 部署指南

### 1. 数据库迁移
```bash
# 运行数据库迁移
cd backend
python -m alembic upgrade head
```

### 2. 创建存储目录
```bash
# 创建存储根目录
mkdir -p uploads/{chat_attachments,prompt_templates,export_data,user_uploads,ai_generated,system_backups,temp_files}

# 设置目录权限
chmod -R 755 uploads/
```

### 3. 配置定时任务
```bash
# 添加到crontab，每小时执行一次清理任务
0 * * * * cd /path/to/backend && python -c "
import asyncio
from src.tasks.file_cleanup_task import run_scheduled_cleanup
asyncio.run(run_scheduled_cleanup())
"
```

### 4. 配置Nginx (可选)
```nginx
# 静态文件服务配置
location /static/ {
    alias /path/to/uploads/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # 安全配置
    location ~* \.(php|jsp|asp|sh|py)$ {
        deny all;
    }
}

# 文件上传大小限制
client_max_body_size 100M;
```

## 监控和维护

### 1. 存储空间监控
```python
# 获取存储统计信息
stats = await file_service.get_storage_stats()
print(f"总文件数: {stats['total_files']}")
print(f"总大小: {file_storage_settings.format_file_size(stats['total_size'])}")
```

### 2. 清理任务监控
```python
# 手动执行清理任务
from src.tasks.file_cleanup_task import file_cleanup_task
results = await file_cleanup_task.run_full_cleanup()
print(f"清理结果: {results}")
```

### 3. 访问日志分析
```sql
-- 查看最近的文件访问情况
SELECT 
    action,
    COUNT(*) as count,
    AVG(response_time) as avg_response_time
FROM ai_file_access_logs 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY action;

-- 查看热门文件
SELECT 
    f.original_filename,
    f.download_count,
    f.access_count
FROM ai_file_storage f
WHERE f.status = 'ACTIVE'
ORDER BY f.access_count DESC
LIMIT 10;
```

## 性能优化

### 1. 数据库优化
- 为常用查询字段添加索引
- 定期清理访问日志表
- 使用分区表存储大量日志数据

### 2. 存储优化
- 启用文件压缩
- 使用CDN加速文件访问
- 实现文件去重机制

### 3. 缓存策略
- 文件元数据缓存
- 分享链接缓存
- 缩略图缓存

## 故障排除

### 常见问题

1. **文件上传失败**
   - 检查文件大小是否超过限制
   - 检查文件类型是否被允许
   - 检查存储目录权限

2. **文件访问404**
   - 检查文件是否存在
   - 检查用户权限
   - 检查文件状态

3. **存储空间不足**
   - 运行清理任务
   - 检查磁盘空间
   - 考虑迁移到云存储

4. **分享链接无法访问**
   - 检查链接是否过期
   - 检查密码是否正确
   - 检查访问次数限制

### 日志查看
```bash
# 查看文件存储相关日志
tail -f logs/app.log | grep "file_storage"

# 查看清理任务日志
tail -f logs/app.log | grep "cleanup"
```

## 扩展开发

### 添加新的存储提供商
1. 在 `StorageProvider` 枚举中添加新的提供商
2. 在 `AIFileStorageService` 中实现对应的存储逻辑
3. 添加相应的配置参数
4. 编写测试用例

### 添加新的文件类型支持
1. 在 `FileType` 枚举中添加新类型
2. 更新 `FILE_TYPE_MAPPING` 映射
3. 添加对应的元数据提取逻辑
4. 更新允许的MIME类型列表

### 自定义文件处理器
```python
class CustomFileProcessor:
    async def process_file(self, file_path: Path, metadata: dict) -> dict:
        # 自定义文件处理逻辑
        pass

# 注册处理器
file_service.register_processor('custom_type', CustomFileProcessor())
```

## 总结

AI助手文件存储系统提供了完整的企业级文件存储解决方案，具有以下优势：

- **安全可靠**: 多层安全防护，确保文件安全
- **高性能**: 优化的存储结构和缓存策略
- **易扩展**: 模块化设计，支持多种存储后端
- **易维护**: 完善的监控和自动化清理机制
- **用户友好**: 丰富的API接口和管理功能

该系统为AI助手模块提供了强大的文件处理能力，支持各种文件操作需求，是整个AI自动化测试管理系统的重要组成部分。