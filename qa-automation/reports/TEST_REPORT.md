# AI 测试管理系统 — 自动化测试报告

生成时间：2026-11-05 08:00:48
执行耗时：12.8s

## 总览

| 指标 | 数值 |
| --- | --- |
| 用例总数 | 108 |
| 通过 | 108 |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| 通过率 | 100.0% |

## 按模块统计

| 模块 | 通过 | 失败 | 错误 | 跳过 |
| --- | --- | --- | --- | --- |
| test_auth | 13 | 0 | 0 | 0 |
| test_defects | 12 | 0 | 0 | 0 |
| test_executions | 10 | 0 | 0 | 0 |
| test_projects | 17 | 0 | 0 | 0 |
| test_reports | 5 | 0 | 0 | 0 |
| test_requirements | 12 | 0 | 0 | 0 |
| test_risks | 14 | 0 | 0 | 0 |
| test_smoke | 5 | 0 | 0 | 0 |
| test_test_cases | 10 | 0 | 0 | 0 |
| test_test_plans | 10 | 0 | 0 | 0 |

## 失败用例

无失败用例（修复后全量 108/108 通过）。

## 问题清单与修复记录

本次测试共发现 2 个由用例证实的真实缺陷，均已修复并经全量回归验证通过（108/108）。

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 1 | 创建测试计划不传 `test_manager_id` 返回 HTTP 500。根因两处：① `TestPlan.test_manager_id` 模型列 `nullable=False`，与创建接口 schema（可选）不一致，入库报 IntegrityError 1048；② `TestPlanResponse.test_manager_id` 声明为必填 `int`，`None` 值序列化时 pydantic 校验失败，同样 500。复现：`POST /api/v1/test-plans/` 不带 `test_manager_id`。 | critical | P0 | ✅ 已修复 | `src/models/test_plan.py`：`test_manager_id` 改为 `nullable=True`；`src/api/v1/test_plans.py`：`TestPlanResponse.test_manager_id` 改为 `Optional[int]`。线上表同步 `ALTER TABLE test_plans MODIFY COLUMN test_manager_id BIGINT NULL`。验证：`test_create_plan_without_manager_succeeds` 通过。 |
| 2 | 用不存在的 `project_id`（如 999999999）创建需求返回 201 并入库，产生孤儿需求，无任何项目存在性校验。复现：`POST /api/v1/requirements/` 带 `project_id=999999999`。 | major | P1 | ✅ 已修复 | `src/services/requirement_service.py`：`_validate_requirement_data` 增加项目存在性校验，不存在时抛 `ValidationError`（接口层映射为 400）。验证：`test_create_requirement_unknown_project` 通过（期望 400/404/422，实际 400）。 |

### 部署阶段已修复的问题（部署即发现，非测试用例证实）

| # | 问题 | 修复 |
| --- | --- | --- |
| D1 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 无法被 pydantic 解析为 int，服务无法启动 | 本地 `.env` 改为 `104857600`（示例文件本身待修，见未修复项） |
| D2 | `src/migrations/env.py` 使用相对导入，alembic 加载失败 | 改为绝对导入 |
| D3 | `src/models/__init__.py` 的 `__all__` 列出 14 个不存在的名字，`from src.models import *` 报错 | 移除失效条目 |
| D4 | `src/models/meeting_analytics.py` 缺少 `String` 导入，`NameError` | 补导入 |
| D5 | 迁移 002 种子插入缺失 NOT NULL 列（`is_active`/`created_at`/`updated_at`），MySQL 1364 | 补齐列 |
| D6 | 迁移 004 插入 `permissions` 表不存在的列（`type`/`is_system_permission`/`is_active`/`sort_order`/`updated_at`），且角色码大小写不符 | 按 001 的实际 schema 对齐 |
| D7 | 迁移 008 把 `projects.id` INT→BIGINT，未同步放宽 4 个引用外键列，MySQL 3780 | 先放宽外键列再改主键 |
| D8 | `requirements.txt` 缺少 9 个运行时依赖（pymysql、requests、aioredis、apscheduler、bleach、PyJWT、python-magic、psutil、scikit-learn） | 本地 venv 已补装（requirements.txt 本身待修，见未修复项） |

### 未修复项（附原因）

| # | 问题 | 原因 / 说明 |
| --- | --- | --- |
| U1 | 模型层存在 39 处外键类型不匹配（INT vs BIGINT），`create_all` 带外键约束时建表失败；本次部署以去掉外键约束的方式兜底 | 逐表对齐外键类型属于较大范围的模型层改动，需逐个核对并做数据迁移验证，超出本次修复范围；已在部署中验证无外键约束下功能正常 |
| U2 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 与 `requirements.txt` 缺依赖（D1/D8 的源头）未改回仓库文件 | 属于仓库配置修复，改动面小但与本次测试修复无关，建议后续单独提交 |
| U3 | 日志警告 `AIAssistantService` 缺少 `generate_test_strategy` 方法；启动预热任务报 `cannot import name 'get_usage_statistics_service'` | 均为非致命警告，不影响 API 功能；AI 相关功能无外部密钥，本次未深入 |
| U4 | `test_environment` 传入 `"QA环境"` 后被存储为 `"QA"`（疑似静默截断/归一化） | 未复现为明确缺陷，仅作观察记录 |
| U5 | Alembic 迁移链另有残留问题（011 前提错误、008/009 分支重复建表等） | 部署已绕过迁移链直接用模型建表；迁移链修复需逐个迁移验证，超出本次范围 |

## 问题清单（待分级）

下表由测试负责人根据失败用例填写：严重程度 blocker / critical / major / minor；优先级 P0 / P1 / P2。

| # | 问题 | 严重程度 | 优先级 | 状态 |
| --- | --- | --- | --- | --- |
| - | 无 | - | - | - |
