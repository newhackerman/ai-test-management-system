# 在线会议模块数据库迁移说明

## 概述

本目录包含在线会议模块的数据库迁移脚本，用于创建会议相关的所有数据表、索引、外键约束和初始数据。

## 文件说明

- `meeting_module_migration.sql` - 主要的SQL迁移脚本
- `run_meeting_migration.py` - Python迁移执行器
- `MEETING_MIGRATION_README.md` - 本说明文档

## 迁移内容

### 数据表

1. **meetings** - 会议主表
   - 存储会议基本信息、时间安排、配置等
   - 包含与项目和用户的外键关联

2. **meeting_participants** - 会议参与者表
   - 存储参与者角色、权限、出席状态等
   - 包含参与统计和设备信息

3. **meeting_recordings** - 会议录制表
   - 存储录制文件信息、状态、访问控制等

4. **meeting_minutes** - 会议纪要表
   - 存储会议纪要、摘要、结构化内容等
   - 支持版本管理和审批流程

5. **meeting_chats** - 会议聊天消息表
   - 存储会议中的聊天消息和元数据

6. **meeting_files** - 会议文件共享表
   - 存储共享文件的信息和访问统计

7. **meeting_analytics** - 会议分析数据表
   - 存储会议效果分析和统计数据

8. **meeting_templates** - 会议模板表
   - 存储会议模板配置和使用统计

### 索引和约束

- 为所有外键字段创建索引
- 为常用查询字段创建复合索引
- 设置适当的外键约束和级联删除规则
- 添加唯一约束防止重复数据

### 初始数据

- 插入3个默认会议模板：
  - 项目启动会模板
  - 需求评审会模板  
  - 进度同步会模板

### 视图

- `v_meeting_statistics` - 会议统计视图，提供会议相关的汇总统计信息

## 使用方法

### 1. 直接执行SQL脚本

```bash
mysql -u username -p database_name < meeting_module_migration.sql
```

### 2. 使用Python执行器（推荐）

```bash
# 预览模式（不实际执行）
python run_meeting_migration.py --dry-run

# 正常执行
python run_meeting_migration.py

# 强制重新执行
python run_meeting_migration.py --force
```

### 参数说明

- `--dry-run`: 仅显示将要执行的SQL语句，不实际执行
- `--force`: 强制执行，即使迁移已经执行过

## 依赖要求

### 数据库表依赖

迁移脚本依赖以下表必须已存在：
- `users` - 用户表
- `projects` - 项目表

### Python依赖

- Python 3.7+
- 项目的数据库连接配置
- 相关Python包（见requirements.txt）

## 迁移验证

迁移完成后，脚本会自动验证：

1. 所有表是否创建成功
2. 视图是否创建成功
3. 初始数据是否插入成功
4. 基本的数据查询是否正常

## 回滚说明

如需回滚迁移，可以执行以下SQL：

```sql
-- 删除视图
DROP VIEW IF EXISTS v_meeting_statistics;

-- 删除表（注意顺序，先删除有外键依赖的表）
DROP TABLE IF EXISTS meeting_analytics;
DROP TABLE IF EXISTS meeting_files;
DROP TABLE IF EXISTS meeting_chats;
DROP TABLE IF EXISTS meeting_minutes;
DROP TABLE IF EXISTS meeting_recordings;
DROP TABLE IF EXISTS meeting_participants;
DROP TABLE IF EXISTS meeting_templates;
DROP TABLE IF EXISTS meetings;

-- 删除迁移记录
DELETE FROM migration_history WHERE migration_name = 'meeting_module_migration';
```

## 注意事项

1. **备份数据库**: 执行迁移前请备份数据库
2. **检查权限**: 确保数据库用户有创建表、索引、外键的权限
3. **字符集**: 所有表使用utf8mb4字符集，支持完整的Unicode字符
4. **存储引擎**: 使用InnoDB存储引擎，支持事务和外键
5. **时区**: 时间字段使用TIMESTAMP类型，注意时区设置

## 故障排除

### 常见问题

1. **外键约束失败**
   - 检查users和projects表是否存在
   - 确认字段类型匹配

2. **字符集问题**
   - 确保数据库和连接使用utf8mb4字符集

3. **权限不足**
   - 确保数据库用户有足够的权限

4. **表已存在**
   - 使用--force参数强制执行
   - 或手动删除现有表后重新执行

### 日志文件

执行过程中的详细日志会保存在 `meeting_migration.log` 文件中。

## 联系支持

如遇到问题，请检查：
1. 日志文件中的错误信息
2. 数据库连接配置
3. 依赖表是否存在
4. 用户权限是否足够

---

**重要提醒**: 在生产环境执行迁移前，请务必在测试环境中充分测试！