# AI 测试管理系统 — 自动化测试报告

生成时间：2026-11-05（第二轮：E2E + 深化 + 安全测试后更新）
被测部署：后端 http://localhost:8000（FastAPI + MySQL 8.0.46 + Redis 7.0.15，122 张表，外键约束剥离部署）、前端 http://localhost:3000（Vite + React 18）
分支：`qa/automation-framework`（基于 main@3a64777；未 push）

## 总览

| 套件 | 用例总数 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
| --- | --- | --- | --- | --- | --- | --- |
| API（`tests/`） | 213 | 213 | 0 | 0 | 0 | 100% |
| E2E（`e2e/`，Playwright + Chromium 真实浏览器） | 20 | 20 | 0 | 0 | 0 | 100% |
| **合计** | **233** | **233** | **0** | **0** | **0** | **100%** |

- API 213 = 第一阶段 108（冒烟 5 / 鉴权 13 / 项目 17 / 需求 12 / 用例 10 / 计划 10 / 执行 10 / 缺陷 12 / 风险 14 / 报告 5）+ 深化 70（`test_hardening.py`）+ 安全 35（`test_security.py`）。
- 全量最后一次执行：API 213/213（`reports/api-full.json`）、E2E 20/20（`reports/e2e-full.json`），均在修复后、清理过的干净库上跑出。
- 本报告回答用户质疑“只发现 2 个问题不可信”：第一阶段的 108 个 API 用例确实只证实了 2 个缺陷；深化 + E2E + 安全三轮补测后，**新发现 12 个真实缺陷，全部修复并回归验证通过**（见下表 #3–#14）。失败就是失败，如实写：中途的失败全部记录在各轮执行小结里，本报告的 100% 是修复后的最终回归结果，不是放水。

## 按模块统计（API）

| 模块 | 用例数 | 通过 | 失败 |
| --- | --- | --- | --- |
| test_smoke | 5 | 5 | 0 |
| test_auth | 13 | 13 | 0 |
| test_projects | 17 | 17 | 0 |
| test_requirements | 12 | 12 | 0 |
| test_test_cases | 10 | 10 | 0 |
| test_test_plans | 10 | 10 | 0 |
| test_executions | 10 | 10 | 0 |
| test_defects | 12 | 12 | 0 |
| test_risks | 14 | 14 | 0 |
| test_reports | 5 | 5 | 0 |
| test_hardening | 70 | 70 | 0 |
| test_security | 35 | 35 | 0 |

## 按模块统计（E2E）

| 模块 | 用例数 | 覆盖流程 |
| --- | --- | --- |
| test_e2e_login | 5 | 登录页渲染、正确登录、错误密码提示、未登录拦截、登出 |
| test_e2e_projects | 3 | 创建项目、项目列表出现新数据、必填校验 |
| test_e2e_requirements | 2 | 创建需求、搜索需点“查询”才生效 |
| test_e2e_test_cases | 3 | 创建用例、必填校验（标题/步骤为空不提交） |
| test_e2e_test_plans | 2 | 创建计划、计划列表出现新数据 |
| test_e2e_execution_defects | 3 | 手动执行（开始→步骤通过→完成保存）、提交缺陷 |
| test_e2e_full_chain | 1 | 项目→需求→用例→计划→执行→缺陷→仪表盘→登出 全链路 |
| test_e2e_security | 1 | 存储型 XSS payload 渲染为纯文本、不执行 |

## 失败用例

最终回归无失败用例。各轮执行中出现的失败及处理（全部已闭环）：

| 轮次 | 结果 | 失败原因分类 |
| --- | --- | --- |
| 深化+安全首轮 | 80 通过 / 23 失败 / 2 跳过（105） | 测试 bug 14 个（`api._token` 属性名错、裸 httpx 未设 `trust_env=False`、密钥路径错、`make_requirement` 缺 `project_id`、会议 payload 缺必填字段、暴力破解判据错认 429/423、建用户邮箱重复）+ 真实缺陷 9 个 |
| 深化+安全第二轮（修测试 bug + 修 #5–#11 后） | 102 通过 / 3 失败 | 真实缺陷 3 个：用户守卫的 403 被通用异常处理吞成 500（2 处）、会议文件上传 500（缺方法） |
| 深化+安全第三轮（修 #12–#14 后） | **105 通过 / 0 失败** | — |
| API 全量（213） | **213 通过 / 0 失败** | 修复无回归 |
| E2E 首轮 | 12 通过 / 7 失败 | 全部为测试 bug（断言文本、清理路径斜杠、原生 required 校验等），应用缺陷 2 个（#3、#4） |
| E2E 全量（修复后） | 19 通过 / 1 失败 | `test_stored_xss_does_not_execute`：payload 缺 `project_manager_id` 致 422（测试 bug） |
| E2E 全量（补 `project_manager_id` 后） | 19 通过 / 1 失败 | 同一用例：Playwright 严格模式下 payload 文本匹配到 2 个元素（测试定位器问题，非应用缺陷） |
| E2E 单测（定位器改 `.first` 后） | 通过 | — |
| E2E 全量（定位器修复后） | 19 通过 / 1 失败 | `test_full_chain_via_ui` 一次闪失：提交时计划名称为空触发校验（疑似选项目后表单重渲染丢值，已加固 helper：填值后断言、选项目后复查补填） |
| E2E 全量（最终，干净库） | **20 通过 / 0 失败** | — |

## 问题清单与修复记录

### 第一阶段发现（API，108 用例）

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 1 | 创建测试计划不传 `test_manager_id` 返回 HTTP 500。根因两处：① `TestPlan.test_manager_id` 模型列 `nullable=False`，与创建接口 schema（可选）不一致，入库报 IntegrityError 1048；② `TestPlanResponse.test_manager_id` 声明为必填 `int`，`None` 值序列化时 pydantic 校验失败，同样 500。复现：`POST /api/v1/test-plans/` 不带 `test_manager_id`。 | critical | P0 | ✅ 已修复 | `src/models/test_plan.py`：`test_manager_id` 改为 `nullable=True`；`src/api/v1/test_plans.py`：`TestPlanResponse.test_manager_id` 改为 `Optional[int]`。线上表同步 `ALTER TABLE test_plans MODIFY COLUMN test_manager_id BIGINT NULL`。验证：`test_create_plan_without_manager_succeeds` 通过。 |
| 2 | 用不存在的 `project_id`（如 999999999）创建需求返回 201 并入库，产生孤儿需求，无任何项目存在性校验。复现：`POST /api/v1/requirements/` 带 `project_id=999999999`。 | major | P1 | ✅ 已修复 | `src/services/requirement_service.py`：`_validate_requirement_data` 增加项目存在性校验，不存在时抛 `ValidationError`（接口层映射为 400）。验证：`test_create_requirement_unknown_project` 通过（期望 400/404/422，实际 400）。 |

### 第二轮发现（E2E）

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 3 | **前端在真实浏览器里完全空白**：`src/routes/index.tsx:122` 懒加载 `@/pages/Reports`，但 `src/pages/Reports.tsx` 不存在（56 个路由导入中唯一缺失）。Vite 导入分析失败，整个路由模块 500，React 无法挂载。HTTP 200 只能证明首页 HTML 可达，掩盖了该缺陷。 | blocker | P0 | ✅ 已修复 | 新建 `frontend/src/pages/Reports.tsx`（真实“报告管理”总览页，链接测试报告 / Allure 报告 / 数据统计）。验证：路由模块恢复 200，登录页正常挂载，E2E 登录 5/5 通过。 |
| 4 | **CORS 缺口**：`.env.example`（及本地 `.env`）的 `CORS_ORIGINS` 只有 `http://localhost:3000,http://localhost:5173`，浏览器从 `http://127.0.0.1:3000` 访问时预检 400 且无 `Access-Control-Allow-Origin`，登录报 Failed to fetch。 | major | P1 | ✅ 已修复 | `.env.example` 与本地 `.env` 均改为 `http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173`；后端重启后预检 200 且带正确 ACAO。 |

### 第二轮发现（深化 API）

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 5 | 用不存在的 `test_plan_id` 创建测试用例返回 200 并入库，产生孤儿用例。根因：`_validate_case_data` 只校验 `requirement_id` 存在性，未校验 `test_plan_id`；`_validate_create_permission` 仅在计划存在时才检查权限，不存在时直接放行。 | major | P1 | ✅ 已修复 | `src/services/test_case_service.py`：`_validate_case_data` 增加 `test_plan_id` 存在性校验（不存在 → `ValidationError` → 400）。验证：`test_create_test_case_unknown_plan` 通过。 |
| 6 | 用不存在的 `project_id` 创建测试计划返回 HTTP 500。根因：服务层已抛 `NotFoundError("项目不存在")` 并原样上抛，但创建接口的异常映射链缺 `NotFoundError` 分支，落入通用 `Exception` → 500。 | major | P1 | ✅ 已修复 | `src/api/v1/test_plans.py`：创建接口补 `except NotFoundError → 404`。验证：`test_create_plan_unknown_project` 通过（实际 404）。 |
| 7 | 用不存在的 `test_case_id` 创建缺陷返回 200 并入库，产生孤儿缺陷（与 #2、#5 同类）。缺陷创建处理器直接构造实体入库，无任何关联校验。 | major | P1 | ✅ 已修复 | `src/api/v1/defects.py`：创建前校验 `test_case_id` / `test_execution_id` / `requirement_id` 存在性（不存在 → `ValidationError` → 400），并补 `Requirement` 导入。验证：`test_create_defect_unknown_case` 通过。 |

### 第二轮发现（安全测试）

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 8 | **特权提升：任意登录用户可管理用户**。`src/api/users.py` 全部 15 个端点（列表、创建、修改、删除、锁定/解锁、重置密码、分配/移除角色、导出/导入、批量操作、用户统计、高级搜索、活动日志）只有 `# TODO: 添加权限检查逻辑` 占位，无任何权限校验。实测：无角色的普通用户列出全部用户（200）、创建用户（201）、读取管理员 profile（200）。创建用户时能否赋角色未单独验证——因创建本身已是提权，修复后该路径已关闭。 | critical | P0 | ✅ 已修复 | `src/api/users.py`：新增 `_require_user_permission` 守卫（与 `src/decorators/permission.py` 的 `require_permission` 同语义：超管放行，否则需 `user:view/create/edit/delete/lock/reset_password/assign_role` 权限码），15 个端点全部守卫；本人读/改自己的资料仍放行。验证：`test_low_priv_user_cannot_list_users`、`test_low_priv_user_cannot_create_user`、`test_idor_read_admin_user_profile` 均返回 403；管理员（超管）操作不受影响，API 全量 213 通过。 |
| 9 | 普通用户可读取管理员 profile（`GET /api/v1/users/1` → 200）。与 #8 同根因（`get_user` 端点无任何校验）。 | major | P1 | ✅ 已修复 | 同 #8：`get_user` 改为本人或 `user:view` 权限方可访问。验证：`test_idor_read_admin_user_profile` 返回 403。注：项目级 IDOR 经核实不存在——普通用户读他人项目返回 403“没有访问该项目的权限”，列表也只能看到自己的项目（total 0）。 |
| 10 | 需求 PUT / DELETE 不存在资源返回 422 而非 404。根因：`requirement_service.py` 的 update/delete/status 三个方法用通用 `except Exception` 包住了服务自己抛的 `NotFoundError`，重包为 `BusinessLogicError`（接口层映射 422）；GET 接口因直接处理 `NotFoundError` 而正确返回 404。 | minor | P2 | ✅ 已修复 | `src/services/requirement_service.py` 三处补 `except (NotFoundError, ValidationError): raise`。验证：`test_update_nonexistent_is_404`、`test_delete_nonexistent_is_404` 通过。 |
| 11 | 安全响应头全部缺失（`x-content-type-options`、`x-frame-options`、`content-security-policy`、`strict-transport-security`、`referrer-policy` 均无）。 | minor | P2 | ✅ 已修复 | `src/main.py` 新增 `SecurityHeadersMiddleware`：5 个头全部下发；CSP 在 `/docs`、`/redoc`、`/openapi.json` 上跳过（Swagger UI 依赖内联脚本与 CDN，默认 CSP 会破坏文档页）。验证：`test_security_headers_present` 通过；`curl -D- /api/v1/health` 实测 5 个头齐全。 |
| 12 | 创建项目会议返回 HTTP 500。根因：`project_integration_routes.py` 调用的 `MeetingProjectIntegrationService.create_project_meeting` 方法在服务类中根本不存在（`AttributeError`），处理器吞掉异常返回通用 500（无日志）。 | major | P1 | ✅ 已修复 | `src/services/meeting_project_integration_service.py`：实现 `create_project_meeting`（项目存在性校验 → 委托已有的 `MeetingService.create_meeting` 校验/生成编码/建会 → 按需自动邀请项目成员）；处理器补 `ValidationError → 400`、`NotFoundError → 404` 映射（`ValidationError` 不是 `ValueError` 子类，原映射链兜不住）。验证：会议创建 201，安全测试的会议文件上传用例得以跑通。 |
| 13 | 会议文件上传返回 HTTP 500。根因同 #12：`collaboration_routes.py` 调用的 `MeetingService.upload_file` 方法不存在（`AttributeError`），任意文件上传都 500，无法验证可执行文件是否被拦。 | major | P1 | ✅ 已修复 | `src/services/meeting_service.py`：实现 `upload_file`（会议存在性校验 → 扩展名白名单校验 → 按 `MAX_FILE_SIZE` 限大小 → 落盘到 `UPLOAD_DIR/meetings/{meeting_id}/` 下的随机文件名，防路径穿越与同名覆盖 → 创建 `MeetingFile` 记录）。白名单与接口文档一致：文档/图片/视频/压缩包；`.php`、`.exe` 等可执行/脚本类型直接拒绝。验证：`test_meeting_file_upload_executable`（`.php`）返回 400；合法上传流程已打通。 |
| 14 | `src/api/users.py` 6 个处理器缺 `except HTTPException: raise`，守卫抛出的 403 被通用 `except Exception` 吞成 500（#8 修复后第二轮回归暴露）。 | minor | P2 | ✅ 已修复 | 6 个处理器（列表、导出、创建、用户统计、高级搜索、活动日志）补 `except HTTPException: raise`。验证：深化+安全第三轮 105/105。 |

### 安全测试核实为“机制存在、非问题”的项（不计入缺陷）

| 项 | 核实结果 |
| --- | --- |
| 暴力破解防护 | 锁定机制真实存在且生效：`auth.py` 的 `_increment_failed_login_attempts` 在 3 次失败后锁 15 分钟、5 次后锁 24 小时（`status=LOCKED`）。首轮测试判据错误（只认 429/423），已修正为“5 次失败后正确密码也被拒（401 + 锁定提示）”并通过。注意：锁定后返回仍是 401（非 429/423），属该应用的既有约定。 |
| JWT 篡改 | payload 篡改、alg=none、错误签名、过期 token、垃圾 token 全部 401；登出后旧 token 失效（401）；无效 refresh token 被拒。 |
| SQL 注入 | 搜索/新建字段的 4 类注入 payload 均未破坏查询、表完好；登录/注册返回不含密码哈希；错误响应不泄露堆栈与内部路径。 |
| 存储型 XSS | API 层 3 类 payload 原样返回（未执行，属存储行为本身）；E2E 证实前端 React 转义渲染为纯文本，无弹窗、无 `img[src=x]` 元素。 |
| CORS | 恶意源 `https://evil.example.com` 预检无 ACAO；`http://localhost:3000` 正常放行。 |
| 头像上传 | `.php` / `.exe` 头像上传被拒（4xx）。 |
| 报告下载目录穿越 | 3 类穿越路径均未越出（4xx/404）。 |
| /docs 与 /openapi.json | 未登录可访问（信息性记录）：FastAPI 默认行为，内含全部接口定义；是否收紧由项目方决定，本次未改。 |

### 部署阶段已修复的问题（部署即发现，非测试用例证实）

| # | 问题 | 修复 |
| --- | --- | --- |
| D1 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 无法被 pydantic 解析为 int，服务无法启动 | 本地 `.env` 改为 `104857600`（示例文件本身待修，见未修复项 U2） |
| D2 | `src/migrations/env.py` 使用相对导入，alembic 加载失败 | 改为绝对导入 |
| D3 | `src/models/__init__.py` 的 `__all__` 列出 14 个不存在的名字，`from src.models import *` 报错 | 移除失效条目 |
| D4 | `src/models/meeting_analytics.py` 缺少 `String` 导入，`NameError` | 补导入（后核实该模块为死代码：无任何 `src/` 模块导入它；`MeetingAnalytics` 的实际定义在 `src/models/meeting.py:546`，与该文件重复定义同一张表） |
| D5 | 迁移 002 种子插入缺失 NOT NULL 列（`is_active`/`created_at`/`updated_at`），MySQL 1364 | 补齐列 |
| D6 | 迁移 004 插入 `permissions` 表不存在的列（`type`/`is_system_permission`/`is_active`/`sort_order`/`updated_at`），且角色码大小写不符 | 按 001 的实际 schema 对齐 |
| D7 | 迁移 008 把 `projects.id` INT→BIGINT，未同步放宽 4 个引用外键列，MySQL 3780 | 先放宽外键列再改主键 |
| D8 | `requirements.txt` 缺少 9 个运行时依赖（pymysql、requests、aioredis、apscheduler、bleach、PyJWT、python-magic、psutil、scikit-learn） | 本地 venv 已补装（requirements.txt 本身待修，见未修复项 U2） |
| D9 | CORS 缺口（#4 的一部分）：`.env.example` 缺 `127.0.0.1` 源 | `.env.example` 与本地 `.env` 均已补齐 4 个源 |

### 未修复项（附原因）

| # | 问题 | 原因 / 说明 |
| --- | --- | --- |
| U1 | 模型层存在 39 处外键类型不匹配（INT vs BIGINT），`create_all` 带外键约束时建表失败；本次部署以去掉外键约束的方式兜底 | 逐表对齐外键类型属于较大范围的模型层改动，需逐个核对并做数据迁移验证，超出本次修复范围；已在部署中验证无外键约束下功能正常 |
| U2 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 与 `requirements.txt` 缺依赖（D1/D8 的源头）未改回仓库文件 | 属于仓库配置修复，改动面小但与本次测试修复无关，建议后续单独提交（`.env.example` 的 CORS 部分已在 #4 中修复） |
| U3 | 日志警告 `AIAssistantService` 缺少 `generate_test_strategy` 方法；启动预热任务报 `cannot import name 'get_usage_statistics_service'` | 均为非致命警告，不影响 API 功能；AI 相关功能无外部密钥，本次未深入 |
| U4 | `test_environment` 传入 `"QA环境"` 后被存储为 `"QA"`（疑似静默截断/归一化） | 未复现为明确缺陷，仅作观察记录 |
| U5 | Alembic 迁移链另有残留问题（011 前提错误、008/009 分支重复建表等） | 部署已绕过迁移链直接用模型建表；迁移链修复需逐个迁移验证，超出本次范围 |
| U6 | 会议项目集成路由另有 6 个未实现的方法，所属端点仍 500：`create_milestone_review_meeting`、`link_existing_task_to_meeting`、`link_meeting_decisions_to_tasks`、`sync_meeting_tasks_with_project`、`sync_project_team_to_meeting`、`update_task_from_meeting_progress`（与 #12、#13 同根因：路由调用了服务类不存在的方法） | 会议模块多处未实现，属于较大范围的功能补齐，本次只修了测试覆盖到的 2 个（创建会议、上传文件）；其余建议按模块排期补齐 |
| U7 | 需求创建弹窗存在项目竞态：打开弹窗瞬间快照 `projects[0]`，若项目列表尚未加载完，`project_id` 为空导致提交被“请选择所属项目”拦住，之后列表加载完也不会回填（E2E 观察记录） | 前端时序问题，测试通过手动选项目绕过；未修 |

## 测试数据清理

- API/E2E 夹具的清理为“尽力而为”：项目删除是软删除（`deleted_at`），列表接口不可见，但行仍留在表里；多轮执行后表里曾积到 140 个软删项目与 8 个测试用户。
- 本报告定稿前已物理清理全部测试数据：项目/需求/用例/计划/执行/缺陷/风险/会议/会议文件/用户（除 admin）/会话/审计日志等表均清空，`uploads/meetings/` 测试文件已删除。最终状态：项目 0、用户 1（admin）、会议 0；后端 `/api/v1/health` 正常，前端首页 200。

## 框架使用

```bash
cd qa-automation
# API 套件（含深化与安全）
../backend/venv/bin/python -m pytest tests -q
# E2E 套件（需前端 :3000 与后端 :8000 运行中）
../backend/venv/bin/python -m pytest e2e -q
# 全部
../backend/venv/bin/python -m pytest tests e2e -q
```

- 配置：`config.py`（`QA_BASE_URL`、`QA_FRONTEND_URL`、`QA_ADMIN_USER`、`QA_ADMIN_PASSWORD`，均可由环境变量覆盖）。
- 报告生成：`tools/report.py`（读 pytest JSON 报告产出本文件的总览与模块表；E2E/安全/问题清单章节为手工维护）。
