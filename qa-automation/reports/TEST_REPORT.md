# AI 测试管理系统 — 自动化测试报告

生成时间：2026-11-07（第六轮优化：18 项 + 事务泄漏根因修复后更新）
被测部署：后端 http://localhost:8000（FastAPI + MySQL 8.0.46 + Redis 7.0.15，干净库重建后 120 张表，**外键约束已保留**）、前端 http://localhost:3000（Vite + React 18）
分支：`qa/automation-framework`（PR #1 开着，目标 main，未合并；第六轮新增 22 个已推送提交，含本报告更新；另有 2 个只改 workflow 文件的提交因 token 缺 `workflow` scope 暂留本地分支 `qa/workflow-ci-local`）

## 总览

| 套件 | 用例总数 | 通过 | 失败 | 错误 | 跳过 | 通过率 |
| --- | --- | --- | --- | --- | --- | --- |
| API（`tests/`） | 275 | 275 | 0 | 0 | 0 | 100% |
| E2E（`e2e/`，Playwright + Chromium 真实浏览器） | 23 | 23 | 0 | 0 | 0 | 100% |
| **合计** | **298** | **298** | **0** | **0** | **0** | **100%** |

- API 275 = 第五轮 251 + 第六轮 24（`test_round6_items.py` 20 + `test_round6_perf.py` 4）；E2E 23 = 第五轮 21 + 第六轮 2（`test_e2e_round6.py`）。
- 全量最后一次执行：API 275/275、E2E 23/23（第六轮最终回归），在干净库（`DROP DATABASE` 后 `ops/rebuild_db.py` 重建，120 张表、种子 45 权限/9 角色）上跑出。
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
| test_executions | 18 | 18 | 0 |
| test_defects | 12 | 12 | 0 |
| test_risks | 14 | 14 | 0 |
| test_reports | 5 | 5 | 0 |
| test_hardening | 70 | 70 | 0 |
| test_security | 35 | 35 | 0 |
| test_meeting_integration | 28 | 28 | 0 |
| test_ai_services | 2 | 2 | 0 |
| test_round6_items | 20 | 20 | 0 |
| test_round6_perf | 4 | 4 | 0 |

## 按模块统计（E2E）

| 模块 | 用例数 | 覆盖流程 |
| --- | --- | --- |
| test_e2e_login | 5 | 登录页渲染、正确登录、错误密码提示、未登录拦截、登出 |
| test_e2e_projects | 3 | 创建项目、项目列表出现新数据、必填校验 |
| test_e2e_requirements | 2 | 创建需求、搜索需点“查询”才生效 |
| test_e2e_requirement_project_race | 1 | U7 竞态：项目列表延迟 6 秒时打开创建弹窗，提交前 `project_id` 应随列表到达自动回填（反向验证：无修复时该用例失败） |
| test_e2e_test_cases | 3 | 创建用例、必填校验（标题/步骤为空不提交） |
| test_e2e_test_plans | 2 | 创建计划、计划列表出现新数据 |
| test_e2e_execution_defects | 3 | 手动执行（开始→步骤通过→完成保存）、提交缺陷 |
| test_e2e_full_chain | 1 | 项目→需求→用例→计划→执行→缺陷→仪表盘→登出 全链路 |
| test_e2e_security | 1 | 存储型 XSS payload 渲染为纯文本、不执行 |
| test_e2e_round6 | 2 | 追溯分析视图真实数据：矩阵出现种子需求编号与绿色链接点、覆盖率 100% |

## 失败用例

最终回归无失败用例。各轮执行中出现的失败及处理（全部已闭环）：

| 轮次 | 结果 | 失败原因分类 |
| --- | --- | --- |
| 深化+安全首轮 | 80 通过 / 23 失败 / 2 跳过（105） | 测试 bug 14 个（`api._token` 属性名错、裸 httpx 未设 `trust_env=False`、密钥路径错、`make_requirement` 缺 `project_id`、会议 payload 缺必填字段、暴力破解判据错认 429/423、建用户邮箱重复）+ 真实缺陷 9 个 |
| 深化+安全第二轮（修测试 bug + 修 #5–#11 后） | 102 通过 / 3 失败 | 真实缺陷 3 个：用户守卫的 403 被通用异常处理吞成 500（2 处）、会议文件上传 500（缺方法） |
| 深化+安全第三轮（修 #12–#14 后） | **105 通过 / 0 失败** | — |
| API 全量（213） | **213 通过 / 0 失败** | 修复无回归 |
| U6 新套件首轮 | 26 通过 / 2 失败（28） | 全部为测试 bug：`project` fixture 是 module 级共享，成员在测试间累积（硬编码人数断言错）、里程碑名在项目内唯一（重名 400） |
| U6 新套件第二轮（修测试 bug 后） | **28 通过 / 0 失败** | — |
| API 全量（241，修测试 bug 后） | 240 通过 / 0 失败 / **1 跳过** | 跳过的是 `test_meeting_file_upload_executable`：会议创建时间写死 `2026-11-05T10:00`，时钟已过该时间，创建被“开始时间不能早于当前时间”拒（400）→ 测试 bug，非应用缺陷 |
| API 全量（最终，修时间后） | **241 通过 / 0 失败 / 0 跳过** | 修复无回归 |
| 第五轮（U1–U5、U7 修复后） | **API 251 通过 / 0 失败；E2E 21 通过 / 0 失败** | U4/U3 新增用例一次通过；U7 竞态用例反向验证通过（无修复时失败）；U1/U5 为模型与迁移层改动，全量回归无新增失败 |
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

### 第三轮发现（U6 会议集成，28 个新用例）

| # | 问题 | 严重程度 | 优先级 | 状态 | 修复 |
| --- | --- | --- | --- | --- | --- |
| 15 | **U6：会议项目集成的 6 个方法全部未实现，所属端点一律 500**：`sync_project_team_to_meeting`、`create_milestone_review_meeting`、`link_meeting_decisions_to_tasks`、`sync_meeting_tasks_with_project`、`link_existing_task_to_meeting`、`update_task_from_meeting_progress`（与 #12、#13 同根因：路由调用了服务类不存在的方法）。6 个方法均不涉及外部会议服务（Zoom/腾讯会议等），全部是内部逻辑，无需外部密钥或账号，因此全部实现，未留“需外部集成”项。 | major | P1 | ✅ 已修复 | `src/services/meeting_project_integration_service.py`：6 个方法全部实现，语义以现有模型、接口 schema 与相邻已实现方法为准：① 同步团队成员：校验会议与访问权限，复用已修复的 `auto_invite_project_members`，返回成员总数/已有参与者/新增数，幂等；② 里程碑评审会：默认标题 `{里程碑名}评审会议`、类型 `PROGRESS_SYNC`（枚举无里程碑评审类型）、开始时间为里程碑计划日 10:00、时长 1 小时，`meeting_config` 可覆盖标题/类型/时间/描述/人数/自动邀请/议程；复用 `create_project_meeting`；③ 决议转任务：仅 `create_task=true` 的决议建任务，`task_type`/`priority` 按 Task 模型枚举校验，任务用真实列（`task_name`/`task_type`/`priority`/`status=TODO`/`assignee_id`/`reporter_id`/`planned_start_date`/`planned_end_date`/`estimated_hours`/`acceptance_criteria`）创建并写入关联表；④ 任务同步：按关联表核对会议任务与项目归属，跨项目任务移回本项目；⑤ 关联已有任务：任务须属于会议的项目（否则 400），幂等；⑥ 按会议进度更新任务：任务须已关联到会议（否则 400），更新 `status`/`actual_hours`，`progress_percentage` 仅用于派生状态（100→COMPLETED、>0→IN_PROGRESS、0→TODO，Task 模型无该列，不存储）。新增 `MeetingTask` 模型（`src/models/meeting.py`，表 `meeting_tasks`：`meeting_id`、`task_id`、`linked_by`、`linked_at`，唯一约束 `(meeting_id, task_id)`）承载会议–任务关联——Task 模型本身无 `meeting_id` 列，`get_meeting_related_tasks` 也已改走该关联表；线上库已建表（现 129 张表）。验证：28 个新用例全部通过（正常 + 异常：未知会议/任务/里程碑 → 404、非法枚举 → 400、未关联任务 → 400、非成员 → 403）。 |
| 16 | `auto_invite_project_members`（#15-① 的直接依赖）有 4 处错误，之前只是潜伏——第二轮测试无其他成员，从未触发：① 读 `member.role`（ProjectMember 只有 `role_in_project`）→ AttributeError；② 读 `member.permissions`（无此列）；③ 传 `role=` 给 `MeetingParticipant`（实际字段是 `participant_role`）；④ `invitation_status` 传小写字符串 `"pending"`（应为 `InvitationStatus.PENDING` 枚举）。另缺“已参与成员跳过”逻辑，重复邀请会撞唯一约束。 | major | P1 | ✅ 已修复 | `src/services/meeting_project_integration_service.py`：按 `role_in_project` 映射（`_map_project_role_to_meeting_role` 重写为英文角色码 → `ParticipantRole` 枚举：PROJECT_MANAGER→MODERATOR、ARCHITECT/DESIGNER/REQUIREMENT_MANAGER→PRESENTER、其余→PARTICIPANT）；`can_share_screen` 按角色给（PROJECT_MANAGER/ARCHITECT → True）；`invitation_status=InvitationStatus.PENDING`；已参与成员跳过。验证：`test_sync_team_adds_member`、`test_sync_team_idempotent` 通过。 |
| 17 | `project_integration_routes.py` 未从 `core.exceptions` 导入 `PermissionError`，文件内全部 `except PermissionError` 只捕获 Python 内置 `PermissionError`，服务层自定义的权限异常落入通用 `except Exception` → 500。实测：非项目成员调同步团队接口返回 500 而非 403。 | minor | P2 | ✅ 已修复 | 路由文件补 `PermissionError` 导入，一次性修复该文件全部处理器的权限映射。验证：非成员调 5 个写接口均返回 403（sync-team、link-existing、decisions-to-tasks、sync-tasks、update-progress）；项目成员仍 200。 |
| 18 | `get_meeting_related_tasks`（会议任务读接口）无权限校验：非项目成员 `GET .../tasks` 返回 200，可看到会议任务列表。 | minor | P2 | ✅ 已修复 | `src/services/meeting_project_integration_service.py`：`get_meeting_related_tasks` 内补 `_require_meeting_access` 校验（`user_id` 为 None 的内部调用跳过）；`get_meeting_task_progress_summary` 复用该方法，继承同一校验。验证：`test_get_tasks_outsider_forbidden` 返回 403。 |
| 19 | `get_meeting_related_tasks` 处理器引用不存在的 `task.progress_percentage`（Task 模型无该列）：关联任务一旦返回，处理器会抛 AttributeError。之前未暴露是因为该方法一直返回空列表。 | minor | P2 | ✅ 已修复 | `src/api/v1/meetings/project_integration_routes.py`：`progress_percentage` 改为按状态派生（COMPLETED→100、IN_PROGRESS→50、其余→0）。验证：`test_update_progress_status_and_hours`、`test_get_progress_summary_counts` 通过（进度 50 / 总体 50.0）。 |

第三轮观察记录（未计入缺陷，未修）：

| 项 | 说明 |
| --- | --- |
| 路由 path 的 `project_id` 仅作装饰 | 6 个方法的处理器只把 `meeting_id` 交给服务层，不校验 path 的 `project_id` 与会议所属项目是否一致（传错 `project_id` 仍返回 200）。授权仍以会议的真实项目为准（非成员 → 403），不构成安全问题；修复需改动 6 个方法签名，本轮未动。 |
| `create_tasks_from_meeting` 为死代码 | 该方法用错误的 Task 构造参数（`title`、`meeting_id`、`creator_id`、`due_date`、小写 `priority`/`status`，Task 模型均无这些列），且无任何调用方。**第四轮已删除**（见下节）。 |
| 安全测试的会议文件上传用例时间写死 | `test_meeting_file_upload_executable` 的会议开始时间写死 `2026-11-05T10:00`，时钟过后创建被拒致用例跳过（测试 bug，非应用缺陷）。本轮已改为 `2026-12-01`，用例恢复执行并通过；API 全量现为 241/241、0 跳过。 |

### 第四轮：删除死代码 `create_tasks_from_meeting`（本轮唯一改动）

**处理方式：删除，不重写。理由：**

1. **全仓库无调用方**：`grep` 全仓库（含非 py 文件）仅命中定义本身（`backend/src/services/meeting_project_integration_service.py:472`）、一份过期 `.pyc` 与本报告的记录；路由文件调用了同服务的其他 12 个方法，唯独没有它；无字符串/反射引用。
2. **构造参数全错，无法“修一修就用”**：对照 `Task` 模型（`backend/src/models/project.py:224`，表 `project_tasks`），该方法传了 4 个不存在的列（`title`→实为 `task_name`；`meeting_id`→Task 无此列，会议–任务关联走 `meeting_tasks` 表；`creator_id`→实为 `created_by`，且为必填；`due_date`→实为 `planned_start_date`/`planned_end_date`），漏了 2 个必填列（`task_name`、`task_type`），`priority='medium'`/`status='todo'` 小写与枚举（`MEDIUM`/`TODO` 等大写）不符；另无权限校验、无 `task_code` 生成、无 `MeetingTask` 关联登记。调用即报 `TypeError`（非法关键字参数），修它等于重写。
3. **业务能力已有正确实现**：同文件的 `link_meeting_decisions_to_tasks`（第三轮 #15）就是“会议决策转任务”的正确实现——真实列建任务、权限校验、决议过滤、关联表登记，且已路由、已有 28 个用例覆盖。重写 `create_tasks_from_meeting` 只会造出第二条无人调用的重复路径。

**改动**：删除该方法 39 行（`backend/src/services/meeting_project_integration_service.py:472–510`）。方法内用到的 `Task`/`ValidationError`/`datetime`/`select`/`Meeting` 等符号文件内他处仍在使用，无冗余导入产生；模块导入验证通过，`hasattr(..., 'create_tasks_from_meeting')` 为 False。

**验证**：API 全量回归 241/241 通过、0 失败、0 跳过（`reports/latest.json`）；E2E 未重跑（本轮无前端改动）。

**第五轮环境说明（非应用缺陷）**：U1 验证时按新方式重建线上库（删库后用 `ops/rebuild_db.py` 重建，**外键约束保留**）：118 张表（111 张元数据表 + 7 张应用启动时建的表）、159 个外键约束、种子权限 45 个/角色 9 个、admin 正常登录；重建后后端重启、API 全量 251/251、E2E 21/21。U5 验证用的是临时库 `ai_test_u5_check`（已删），未动线上库。

**本轮环境说明（非应用缺陷）**：回归前发现 MySQL 数据目录已被清空（虚拟机重置所致：MySQL/Redis/前后端服务全部停掉，库里无 `ai_test_user`、无 `ai_test_db`）。按第一轮方式重建：建库建用户（取 `.env` 密码）→ 模型 `create_all`（外键约束剥离，见 U1）→ 129 张表 → 种子权限 11 个/角色 2 个/admin（密码 `TEST@test1`）。重建中另发现仓库自带脚本 `backend/src/scripts/simple_init.py` 已失修（给 `Permission` 传不存在的 `type=` 参数，实际列为 `permission_type`），故种子改用内联正确字段写入，未改仓库脚本。首次回归 30 通过/209 错误即因此环境问题（`1045 Access denied`），与删除无关；重建后 241/241。

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
| D1 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 无法被 pydantic 解析为 int，服务无法启动 | 本地 `.env` 改为 `104857600`；第五轮 U2 已把示例文件本身改为 `104857600` |
| D2 | `src/migrations/env.py` 使用相对导入，alembic 加载失败 | 改为绝对导入 |
| D3 | `src/models/__init__.py` 的 `__all__` 列出 14 个不存在的名字，`from src.models import *` 报错 | 移除失效条目 |
| D4 | `src/models/meeting_analytics.py` 缺少 `String` 导入，`NameError` | 补导入（后核实该模块为死代码：无任何 `src/` 模块导入它；`MeetingAnalytics` 的实际定义在 `src/models/meeting.py:546`，与该文件重复定义同一张表） |
| D5 | 迁移 002 种子插入缺失 NOT NULL 列（`is_active`/`created_at`/`updated_at`），MySQL 1364 | 补齐列 |
| D6 | 迁移 004 插入 `permissions` 表不存在的列（`type`/`is_system_permission`/`is_active`/`sort_order`/`updated_at`），且角色码大小写不符 | 按 001 的实际 schema 对齐 |
| D7 | 迁移 008 把 `projects.id` INT→BIGINT，未同步放宽 4 个引用外键列，MySQL 3780 | 先放宽外键列再改主键 |
| D8 | `requirements.txt` 缺少 9 个运行时依赖（pymysql、requests、aioredis、apscheduler、bleach、PyJWT、python-magic、psutil、scikit-learn） | 本地 venv 已补装；第五轮 U2 已把其中 8 个声明进 `requirements.txt`（`aioredis` 除外，见 U2 说明） |
| D9 | CORS 缺口（#4 的一部分）：`.env.example` 缺 `127.0.0.1` 源 | `.env.example` 与本地 `.env` 均已补齐 4 个源 |

### 第五轮修复（U1–U5、U7 全部修复；本轮后未修复项为零）

| # | 问题 | 修复与验证 |
| --- | --- | --- |
| U1 | 模型层 39 处外键类型不匹配（INT vs BIGINT），`create_all` 带外键约束时建表失败 | 逐表把外键列类型与被引用主键对齐（BigInteger→Integer 以匹配 `users.id` 等，Integer→BigInteger 以匹配 `projects.id`），共 8 个模型文件；第 39 处在未注册的死代码 `src/models/task.py`（`tasks` 表从未建表、API 用的是 `project.py` 的 `Task`），也一并改掉并记录。验证：类型不匹配扫描归零；临时库上带外键约束的 `create_all` 成功（111 张表、158 个外键约束）；`ops/rebuild_db.py` 移除剥离外键的兜底并用新方式重建线上库（111 张元数据表全部在库、159 个外键约束、种子权限 45 个/角色 9 个/admin 正常）；全量 API 251/251 通过。附注：另有 7 张表（`audit_logs` 等）不在 `Base.metadata` 中、由应用启动时建表，是既有行为，未动。提交 `8e263f2`。 |
| U2 | `backend/.env.example` 的 `MAX_FILE_SIZE=100MB` 与 `requirements.txt` 缺依赖（D1/D8 的源头） | `.env.example` 改为 `104857600`；`requirements.txt` 补声明 8 个缺失依赖（pymysql、requests、apscheduler、bleach、PyJWT、python-magic、psutil、scikit-learn）。`aioredis` **故意未加**：其末版 2.0.1 在 Python 3.12 上根本无法导入（无 distutils 报 `ModuleNotFoundError`；有 setuptools 报 `TypeError: duplicate base class TimeoutError`，且 `cache_utils.py` 的旧 guard 只捕 `ImportError` 兜不住——新 venv 实测导入即退出 1、后端起不来）。改用官方后继 `redis.asyncio` 迁移 `src/utils/cache_utils.py`（随已声明的 `redis` 包提供）。验证：新 venv `pip install -r requirements.txt` 成功、8 个导入 + `redis.asyncio` 全过、异步 Redis 往返正常、`from src.main import app` 正常、`.env.example` 解析为 int 104857600。提交 `67cbed9`。 |
| U3 | 日志警告 `AIAssistantService` 缺少 `generate_test_strategy` 方法；启动预热任务报 `cannot import name 'get_usage_statistics_service'` | 两处都补齐：(1) 在 `AIAssistantService` 上实现 `generate_test_strategy(prompt)`（复用现有 `generate_content()`，有 JSON 回复时解析、无 AI 密钥时记 warning 并返回空结构而非抛错）；(2) 在 `enhanced_usage_statistics_service.py` 补 `get_usage_statistics_service` 工厂与 `get_system_overview()` 方法（预热调度器调用）。验证：无密钥下 `generate_test_strategy` 返回空结构；工厂 + `get_system_overview()` 对线上库跑通；预热 `_preheat_system_stats` 干净执行；后端重启无相关警告。新增 `tests/test_ai_services.py` 2/2 通过。提交 `b9f5ba7`。 |
| U4 | `test_environment` 传入 `"QA环境"` 后被存储为 `"QA"` | **复现证实为真 bug，且比报告写的更严重**：`_normalize_environment()` 会把未知值做 ASCII 剥离——`"QA环境"`→`"QA"`、`"生产"`→`"test"`（静默存错环境）、`"灰度环境"`→`"test"`、`"UAT环境"`→`"UAT"`。修复：未知值原样保留（去首尾空白、按 `String(100)` 截断），已知名称仍映射为规范码（“测试环境”→test、“生产环境”→prod），两条 start 接口均适用。新增 8 个参数化用例（`tests/test_executions.py` 10→18），模块 18/18 通过。提交 `118e3b2`。 |
| U5 | Alembic 迁移链残留问题（011 前提错误、008/009 分支重复建表等） | 空库 `alembic upgrade head` 现已干净跑完（退出 0，终点 `df4d66178796` 单 head，45 张表、61 个外键约束、无重复建表）。修了：(1) 类型与模型对齐：001 的 `users.id` 等由 BIGINT 改为 INT（011 的前提由此成立），AI 分支的 FK 列同步改为 INT，005 的 `projects.id` 与 4 个 `project_id` 改为 BIGINT；(2) 去重：005 删 5 张与 001_ai_assistant/002 重复的建表，suggestion_006 删 2 张与 002 重复的建表，008 删 5 张与 009 重复的建表及多余的 BIGINT ALTER 块；(3) 补跨分支前置依赖（005→001_ai_assistant、suggestion_006→002、007→002、001_ai_assistant→001、010→008），merge 修订的 down_revision 收敛为 5 个真正 head；(4) 4 个超长 revision id（008/006/009/010，33–35 字符）超 `alembic_version.version_num` VARCHAR(32) 上限，改短并重命名文件；(5) 两个 API 级 bug：`sa.PrimaryKey`→`PrimaryKeyConstraint`（006_operation_logs）、`create_index` 的 `comment=` 参数 36 处移除（007）。抽查迁移后 schema：`users.id` INT、`projects.id` BIGINT、项目用户列 INT 且有外键、`requirements.project_id` BIGINT。附注：迁移链只覆盖历史 schema（45 张表），线上库仍由模型 `create_all` 构建（118 张表）。提交 `e0836f`。 |
| U7 | 需求创建弹窗项目竞态：打开弹窗瞬间快照 `projects[0]`，项目列表未加载完时 `project_id` 为空导致提交被“请选择所属项目”拦住，之后也不回填 | 修复：新增 `useEffect`，列表到达后为全新创建表单（且 `project_id` 仍空时）回填首个项目或当前筛选项目，绝不覆盖用户已选值或编辑表单。新增 E2E `e2e/test_e2e_requirement_project_race.py`：延迟项目列表响应 6 秒、飞行中途打开弹窗，断言下拉初始为空、列表到达后自动填好并可保存；反向验证：无修复时该用例失败、有修复时通过。E2E 全量 21/21 通过。提交 `f85fbe7`。 |

> U6（会议模块 6 个未实现方法）已在第三轮修复，见 #15–#19。第五轮后，报告中的未修复项已清零。

## 第六轮优化（2026-11-07，18 项 + 事务泄漏根因修复）

逐项做完先测再做下一项；每项或每组提交一次并及时推送。最终干净库回归：API 275/275、E2E 23/23。

| # | 改动 | 验证 | 提交 |
| --- | --- | --- | --- |
| 1 | 审核模块空实现补齐：新增 `ConfigAuditComment` 模型（`sys_config_audit_comments` 表）；POST `/{id}/comment`（空意见/终态审核拒绝）、POST `/{id}/cancel`（申请人或 DB 核查的超级管理员，仅 PENDING/IN_REVIEW）、GET `/{id}/history`（生命周期字段 + 意见的真实时间线）、WS `/ws/{id}`（token 查询参数、连接与按需推送状态快照、ping/pong） | 探针端到端验证，含 400/403/404；API 251/251 | `ab209ef` |
| 2 | AI 文件分享：路由此前从未注册（12 个接口全 404），挂到 `/api/v1/ai/files`；同步 `get_db`→`get_async_session`（原服务每个调用都 await）；实现 GET `/share/{token}`（token/过期/密码、预览与下载权限、max_views/max_downloads 计数与访问日志、404/403/410）；分享路径进 AuthMiddleware 白名单；POST `/cleanup` 要求 DB 核查的超级管理员；分享密码改存 SHA256 摘要（原明文，旧分享为 0）；GET `/stats` 移到 `/{file_id}` 之前（路由遮蔽致 422）；补建缺失的 `src/utils/logger.py`；永久删除按日志→访问日志→分享→文件顺序删（原 IntegrityError 1451） | 全流程探针验证，永久删除后文件/分享归零；API 251/251 | `c139dfc`、`3754e77` |
| 3 | `/me`、`/profile` 返回真实角色权限（原硬编码 `[]`）：查 `user_roles` 取角色，`role_permissions` + `user_permissions` 并集合并去重（仅生效） | 线下验证：admin 两接口均得 role admin + 全部 45 个种子权限；API 251/251 | `2cc8a18` |
| 4 | 前端需求追溯三分析页接真实后端：新 `traceabilityService.ts`（矩阵/影响/覆盖率/JSON 导出）；TraceabilityMatrix、ChangeImpactAnalysis、TraceabilityCoverageAnalysis 去掉写死数据与 DES/REQ 硬编码网格，接真实接口；在 RequirementsManagement 加“需求列表 / 追溯分析”切换挂载矩阵与覆盖率。ChangeImpactAnalysis 未挂载（触发它的 ChangeRequestList 本身未挂载）。影响分 = 风险基数（LOW 25 / MEDIUM 50 / HIGH 75 / CRITICAL 90）+ 直接影响×2 + 间接×1，上限 100；排期/成本影响无后端数据，诚实置零；设计维恒空（无设计模型）。前端构建需 `NODE_OPTIONS=--max-old-space-size=4096`（默认构建 OOM） | tsc 干净；Playwright 真实浏览器探针（真实需求/任务链接、覆盖率 1.0），三视图渲染真实数据、无控制台报错；API 251/251、E2E 21/21 | `e5af75c`、`851ecec` |
| 5 | 审批权限检查：`canCurrentUserApprove` 按当前步骤指定审批人或超级管理员判断（步骤本身仍是 mock 数据，审批人张技术/李产品/王项目）；WebSocket 用户 ID 改从 `useAuthStore` 取（原硬编码 1）；录音暂停：`RecordingStatus` 加 PAUSED、MySQL 列已 ALTER、`RecordingProcess.pause/resume`（SIGSTOP/SIGCONT）、`RecordingService.pause/resume_recording`（与停止同权限，RECORDING↔PAUSED 校验；进程不在本后端进程内存时只翻状态并记 warning）、路由 POST `/meetings/recordings/{id}/pause\|resume`、GET `/meetings/{id}/recording-permissions`、前端 `recordingService.ts` 路径与双重解包、snake→camel 映射全修。顺带修同链 3 个既存 bug：停止路由多传 `request` 参数（500）、`StopRecordingResponse` 缺 `recording_id`（500）、`RecordingResponse` 拒 NULL 数值/布尔字段、通知调用缺方法改为 best-effort | 实测：暂停 200（PAUSED）/重复暂停 400/恢复 200/重复恢复 400/无权限暂停 403/权限接口 200/停止 200；API 251/251、E2E 21/21 | `c4de68b` |
| 6 | AI 适配器基类空方法：`base.py` 4 处 `pass` 是 `@abstractmethod` 接口约定（8 个 provider 适配器均已实现），改为 `raise NotImplementedError` + 文档说明实现位置；工厂 `clear_cache` 改为真实实现（同步清字典、有事件循环时后台关闭被逐出的适配器、加 awaitable `clear_cache_async`）。顺带修真 bug：工厂此前根本无法导入——6/8 个类名写错（BaiduWenxinAdapter→BaiduAdapter 等，含两个底部辅助函数），因无任何 live 代码导入它，后端一直能跑，但工厂完全不可用 | 工厂可导入；8 个 provider 均可创建与缓存复用；`clear_cache_async` 能关 baidu 的 aiohttp 会话；无循环时同步清理只记 warning 不崩；ABC 仍拦住缺方法的子类；API 251/251 | `45e5d05` |
| 7 | `/docs` 与 `/openapi.json` 访问开关：新增 `DOCS_REQUIRE_AUTH`（默认 `False`，行为不变）；开启时 AuthMiddleware 取消三处文档路径白名单（匿名 401），FastAPI 内置公开文档路由改由 `get_current_user` 守卫的自定义路由替代（Swagger UI 用 requestInterceptor 从 localStorage 取 token，ReDoc 内嵌 spec）；同时修 CSP 跳过元组（原写 `/docs` 等不带 `/api/v1` 前缀的路径，永远匹配不上，CSP 一直下发并拦 CDN 脚本）；`backend/.env.example` 与 README 写明用法与回退 | 默认模式匿名 200 且 /docs 无 CSP 头；收紧模式（临时改 `.env` 后重启）匿名 401、登录后 200、文档含 requestInterceptor、ReDoc 含内嵌 spec；验证后 `.env` 已还原并重启；API 251/251 | `37291e6` |
| 8 | 登录锁定 401→423：**决定改**。`error_responses.py` 新增 `locked_error()`（423，error_code `ACCOUNT_LOCKED`）；`auth.py` 仅 LOCKED 状态返回该码，其他非 ACTIVE 状态仍无码；登录路由按码映射 423，其余仍 401。理由：423 Locked（RFC 4918）语义正确——401 意味着凭证错，而锁定时密码正确却被拒；影响面小（仅 LOCKED 分支变，错密码/未知用户仍 401）；`test_security.py::test_brute_force_locks_account` 本就接受 (401, 403, 423)；严格 401 用例覆盖错密码与未知用户（不受影响）；前端登录页无 401 专属处理（通用拦截器显示消息）；提示语本就区分锁定与凭证错，不新增信息泄露。锁策略：≥3 次失败锁 15 分钟，≥5 次锁 24 小时，过期锁下次登录自动解。测试已同步改为精确断言 423 | 实测：锁定的测试用户用正确密码得 423“不可用”，正常用户错密码仍 401；API 251/251、E2E 21/21 | `5c34b5a` |
| 9 | 根目录 `openapi.json` 从运行中的后端重新生成：6 个路径 → 651 个路径，pretty-print（indent 2、中文不转义，2.3 MB）；README 注明快照属性与刷新命令；运行时无代码读根目录该文件 | API 251/251 | `335ce8c` |
| 10 | 删死代码 `src/models/meeting_analytics.py`（132 行）：无任何导入；与 `meeting.py:570` 的定义不同——删的是评分版（overall_score/analysis_data/suggestions），留下的参与度/发言/互动版才是 `Meeting.analytics` 关系与 `meeting_ai_integration_service` 用的 | 后端重启 200；live 表列与保留定义一致；API 251/251 | `ccd0026` |
| 11 | 收敛两套建表路径：实测 live 库 119 张表 = 共享 Base 114 + core.database Base 6（dashboard.py 定义）− `security_events`（已注册但两种路径都不建）。`security_events` 从 `audit_service.py`（服务文件里定义模型）原样移入 `src/models/audit.py`；`dashboard.py` 6 张表改用共享 Base，`models/__init__.py` 加仅注册用导入；`init_database` 三处 create_all 合并为一次共享元数据建表；alembic `env.py` target_metadata 改共享 Base；`ops/rebuild_db.py` 同步。**有意不合并** 6 个独立定义文件（color_scheme 等）：各有自己的 declarative_base 且与 live 表列数不同（dashboard_data_cache 独立版多 10 列等），无 live 查询碰那些多余列，合并要对齐列差并改 live 导入，风险大于收益，已在 `dashboard.py` 头注释写明 | 空库 create_all 得 120 张表（含 security_events + 6 张 dashboard 表）；空库 `alembic upgrade head` 45 张表、版本 `df4d66178796`；后端重启后 live 库 119→120；API 251/251 | `e0e3b23` |
| 12 | `ops/recover.sh` 三盲点：(a) `ensure_packages` 只查二进制，改为 `dpkg-query` 状态必须为 `install ok installed`，iU/iF 先 `apt --fix-broken install` + `dpkg --configure -a` 修；(b) `PermissionService.initialize_default_permissions/roles` 的“有行即完成”早返改为按 code/role 逐个跳过已存在，`rebuild_db.py` 建表后验表数、种子后验权限≥45/角色≥9/admin 已链接且链接数等于权限数，`recover.sh` 的表门禁也加权限/角色数检查；(c) Redis 单元 217/USER 的根因不是缺 redis 用户（uid 103 存在），而是单元 `PrivateUsers=true` 在本机用户命名空间建不起来，改加 drop-in `ops/systemd/redis-server.service.d/override.conf`（`PrivateUsers=false`，其余沙箱不动），`recover.sh` 每次运行都安装它；`ensure_redis` 先试 systemd 单元，失败再修包重试，最后才直启 `redis-server`（并记日志说明单元仍坏） | 半种子 10/9/10 重建后变 45/9/45 且自检通过；健康运行 RECOVER OK；模拟 iU（`dpkg --unpack` redis-server.deb）被检测并修好；删 drop-in + 停 redis 后 recover.sh 重装 drop-in、单元启动成功；API 251/251 | `d470930` |
| 13 | `recover.sh` 加 `clear_idle_transactions` 兜底清理：MySQL 起好后、建库前，只 KILL 满足 USER=后端 DB 用户、COMMAND='Sleep'、TIME>60 且 `INNODB_TRX` 有未提交事务的线程；DB_USER 为 root 时整步跳过；每条 kill 记日志并计入 REPAIRED。验证中学到：`CREATE DATABASE/TABLE IF NOT EXISTS` 不会被普通 SELECT 的共享读元数据锁挡住（瞬间返回），真正卡住的是要排他元数据锁的 DDL（如 ALTER），生产约 4 分钟卡死的阻塞点在 DDL，不在建库本身 | 健康运行 RECOVER OK（无 kill）；模拟卡死（持未提交事务的 ai_test_user 线程，TIME 75+）：recover.sh 0.76 秒跑完并记“killed idle transaction thread 143”，`INNODB_TRX` 归零，ALTER 探针立即成功；API 251/251 | `13d7463` |
| 根因修复（与第 13 项分开，源头修复 vs 兜底清理） | 后端事务泄漏源头：`get_usage_statistics_service()` 与 `get_meeting_ai_service()` 两个进程级单例会话建好后永不提交/回滚/关闭；启动预热 `_preheat_system_stats()` 首次读即隐式开启事务挂在进程生命周期。改为每次调用开短生命周期会话：usage 服务无显式会话时每次新建，用完 `aclose()`（回滚 + 关闭，仅关自有会话）；meeting_ai 服务改为 FastAPI 生成器依赖（`async with AsyncSessionLocal()`，yield 后回滚），8 个调用点全是 `Depends(...)`，无需改动；`test_usage_statistics_factory_and_overview` 在 finally 里关闭服务。未修（超出范围，已记录）：`get_prompt_service` 在 `prompt_service.py` 里不存在（每次启动预热都 ImportError，被调度器 try/except 吞掉）；另约 10 个全局单例工厂未审计 | 后端重启，预热日志“系统统计数据预热完成”，`INNODB_TRX`（root 查）为 0；`/meetings/1/summary` 200、`/meetings/1/transcription` 业务 404 后仍为 0；后端起来时跑 `recover.sh` 0.6 秒 RECOVER OK（此前约 4 分钟卡死）；带后端运行的完整 `rebuild_db.py` 5.1 秒，种子 45/9/45；API 251/251 | `2f81ed3` |
| 14 | 给第 1–6 项补测试：API `tests/test_round6_items.py` 20 用例（审核意见/取消/历史、AI 文件分享访问+清理鉴权、/me+/profile 真实角色权限、追溯矩阵/影响分析/覆盖率真实数据、录音暂停/恢复/权限），E2E `e2e/test_e2e_round6.py` 2 用例（追溯分析视图真实数据：矩阵绿点链接、覆盖率 100%）。录音暂停无 UI 按钮可点（只有 `useRecording.ts` 与本地 store 翻转），故无暂停的 E2E 点击流，由 API 用例覆盖 | 测试暴露 6 个真实缺陷，全部修复并回归（见下方缺陷表 R1–R6）；API 271/271、E2E 23/23 | `7671518` |
| 15 | 性能基线冒烟：`tests/test_round6_perf.py` 4 用例——登录、三个热列表接口、10 MB 大文件上传、5 并发列表无 5xx。实测基线（本机暖机）：登录中位 0.53s、列表 0.018–0.044s、10 MB 上传 0.12s；断言阈值放宽 5–10 倍（登录 3s、列表 2s、上传 30s、并发 5s），只防回归与 5xx，不做毫秒级抖动断言；不是完整压测 | 4/4 通过；API 275/275 | `49715d1` |
| 16 | 软删除物理清理：新脚本 `ops/cleanup_soft_deleted.py`（默认 dry-run 只计数，`--apply` 执行，`--days` 宽限默认 7 天）。先算可删 id 集（从软删项目/文件出发沿 FK 图外扩），再按子表在前批量删；覆盖 5 张软删表 + requirements/tasks/cases/plans/defects/meetings 等孤儿行；`sys_config*` 与用户/角色/权限永不碰；LOCAL 文件同步删磁盘文件（路径相对 `backend/`）。第一版逐规则删在 `requirement_status_history` 上踩过 FK 1451（子表删晚于父表），改 id 集方案后解决；干跑计数对双 FK 表会重复计数的问题已在脚本 docstring 注明（apply 计数准确） | 首跑 `--days 0`：删 1666 行（projects 329、project_members 345、meeting_participants 233、tasks 144、meetings 177、ai_file 50 等）+ 50 个孤儿磁盘文件（21 MB）；再跑 dry-run 为 nothing to purge；API 275/275 | `2497838` |
| 17 | 依赖验证：新脚本 `ops/verify_clean_install.sh`（临时 venv、从零 `pip install -r backend/requirements.txt`、`pip check`、导入 `src.main`），并在 `.github/workflows/ci-cd.yml` 新增 `dependency-check` 作业接入 unit-tests 的 needs。顺带修 CI 文件既有 YAML 错误：三处 `DATABASE_URL: sqlite:///:memory:` 的行尾冒号使解析失败，加引号后文件可解析（此前整个 workflow 文件是无效 YAML）。注意：`/tmp` 在本机是 512M tmpfs，完整安装曾因 Errno 28 失败，本地脚本改用 `$HOME/.tmp` 建 venv；CI runner 的 /tmp 够大，job 里仍用 /tmp/cleanvenv | 干净安装验证通过：最新版依赖可装（FastAPI 0.162、pydantic 2.14.3、SQLAlchemy 2.1.8 等），`pip check` 无冲突，`from src.main import app` 成功 | 脚本 `f596e07`（已推送）；workflow 改动 `27db7f3`（本地分支 `qa/workflow-ci-local`，未推送，见遗留项） |
| 18 | 部署方式定稿：`docs/deployment/README.md`（原为空）写明主推 `./deploy.sh` + `backend/docker-compose.yml`（单机），`scripts/deploy.sh`（拉镜像）、`scripts/k8s-deploy.sh` + 平铺 `k8s/*.yaml`（集群）、`start_*.sh`（本地开发）各用于什么场景；`k8s/production|staging` 模板与 `backend/requirements_async.txt` 明确为 dormant/历史文件。修 `deploy.sh`：compose 文件在 `backend/` 下（根目录根本没有），全部调用改走 `-f backend/docker-compose.yml`；Compose v2 优先、v1 兜底；建目录改到 `backend/logs`、`backend/uploads`；删 `data/mysql`、`data/redis`（命名卷，从未用过）。修 `scripts/deploy.sh` 同款 v2 兜底（它 cd 进 backend/，路径本身是对的）。修 `backend/docker-compose.yml`：删 `./sql/init.sql` 与 `./sql/migrations` 两个不存在的挂载（否则 up 直接失败）；schema 由后端启动建表，迁移只覆盖 45 张表。README：`.env` 位置改为 `backend/.env`（根目录无模板），Python 3.9+→3.11+、Node 16+→18+（与 Dockerfile 一致），测试行改为当前框架 qa-automation，加部署小节。`docs/developer/README.md` 的 compose 命令补 CWD 说明与 nginx 缺口提示 | `bash -n` 三脚本通过，compose 与 CI YAML 可解析；本机无 Docker，`docker compose up` 未实际跑过（见遗留项） | `3500554`；CI needs 修 `703af1f`（本地分支，未推送） |

### 第六轮新增缺陷（测试暴露的真实缺陷，全部已修复）

| # | 缺陷 | 修复与验证 |
| --- | --- | --- |
| R1 | `recording_service.py:266`：`MeetingStatus` 是纯 PyEnum（非 str 混入），`meeting.status != 'IN_PROGRESS'` 恒为真，**开始录制永远走不通**（运行时证实 `MeetingStatus.IN_PROGRESS == 'IN_PROGRESS'` 为 False）。代码库中唯一一处 `meeting.status` 的字符串比较 | 改为与枚举比较；启动录制 201 |
| R2 | `_validate_recording_config` 把 Pydantic 请求对象当 dict 用（`.get()` 抛 500）；唯一调用方是路由 | 开头归一化：有 `model_dump` 则转 dict，再映射 `recording_name→name` 等字段；quality 默认值 `standard` 映射为校验器的 `medium`（校验档位 low/medium/high） |
| R3 | `RedisCache.set` 只接受 `ttl`，6 处调用用 `ex=`（recording_service ×4、dashboard_integration、core/redis.py），开始录制 500 | `set(..., ttl=None, ex=None)`，`ex` 作 `ttl` 别名 |
| R4 | `StartRecordingResponse` 无 `data` 字段且路由未设 `recording_id`，开始录制返回 `recording_id: null`，客户端无法暂停/停止刚建的录制；前端 `startRecording` 期望 `response.data` 是 MeetingRecording，同样是坏的 | 模型加 `data: Optional[RecordingResponse]`（与 `PauseRecordingResponse` 同构），路由回填 `recording_id=recording.id` |
| R5 | 停止录制后处理与请求共享会话：`asyncio.create_task(self.process_recording(...))` 共用请求 `self.db`，与 `get_async_session` 的 `session.close()` 并发用同一条 MySQL 连接，触发 asyncmy 2014 `Command Out of Sync`，close() 抛错 → “Exception in ASGI application” → uvicorn 关闭该 keep-alive 连接，客户端下一次复用该连接直接失败（套件里表现为随机游走的 ReadTimeout / RemoteProtocolError；原始 socket 探针证实服务端在 stop 响应后立即发 FIN，access log 里下一次请求根本没到达） | 后处理改用独立会话的新 RecordingService；stop 后同连接 GET/DELETE 均 200；套件不再随机失败 |
| R6 | `file_path` 从未持久化（恒为 `''`），后处理永远报 `Recording file not found: `（空串）；`start_recording` 的 `output_file` 只存在进程对象上 | 启动成功后回填 `recording.file_path = str(output_file)` 并 `refresh`（否则 commit 后属性过期，路由层 `from_orm` 抛 MissingGreenlet——与第 5 项 pause/resume 同类修复）；回填后 `file_path` 如 `recordings/208/recording_30_....mp4` |

### 第六轮遗留项

- **录音管线在无头环境录不到真实媒体**：ffmpeg 命令要抓 PulseAudio + X11 屏幕（`:0.0`），本机两者都没有，ffmpeg 启动即退出（只剩僵尸进程）、输出文件建不出来；后处理因此永远以“文件不存在”失败，录制最终状态 FAILED。开始/暂停/恢复/停止的状态机与权限均已验证通过；要真录制需在有桌面会话的机器上跑，或把采集命令换成 lavfi 测试源。
- **ffmpeg 僵尸进程**：`RecordingProcess` 的 Popen 对象随每次请求的 service 实例丢弃，无人 `wait()`，每次开始录制留一个 defunct 子进程，直到后端重启才回收。无实际资源占用（仅占 PID 表项），未修。
- **`get_prompt_service` 不存在**：启动预热每次 ImportError，被调度器 try/except 吞掉；另约 10 个全局单例工厂未审计（与根因修复同类风险，超出本轮范围）。
- **6 个独立模型定义文件未合并**：见第 11 项（列差未对齐，无 live 查询碰多余列）。
- **ChangeImpactAnalysis 未挂载**：见第 4 项（触发它的 ChangeRequestList 本身未挂载）。
- **CI workflow 改动未推送**：第 17 项的 `dependency-check` 作业与 YAML 修复、第 18 项的 build-and-push `needs` 修复都在本地分支 `qa/workflow-ci-local`（`27db7f3`、`703af1f`），因当前 gh OAuth token 缺 `workflow` scope，GitHub 拒绝推送 workflow 文件。需用户用有 workflow 权限的方式推送，或重新授权 gh。
- **部署未在 Docker 上实跑**：本机无 Docker，`docker compose up` 只做了语法 + 路径 + YAML 检查；`backend/nginx/` 缺失使 `--profile production` 仍起不来；`backend/.env.test`、`.env.production` 需先创建。
- **第 13 项验证中的未解小点**：一次被 timeout 杀掉的 ALTER 探针后，`users` 表上曾出现 `__probe_col` 列（探针 ALTER 明明在等锁时被杀，却留下了列）；列已删掉、schema 已验干净，成因未重建。
- **第 5 项遗留**：`meetingRoomStore.pauseRecording` 仍是本地状态翻转，未接录制服务；`process_recording` 后台任务日志里仍有 `RedisCache.set() got an unexpected keyword argument 'ex'` 的历史报错（R3 修复后新触发的应已消除；后台任务本身仍因无头环境文件缺失而失败，见上）。
- **第 4 项遗留**：4 个孤儿需求（id 7、18、29、40，所属项目已删）——第 16 项清理后已不存在（清理删了全部 8 个孤儿需求；此条留作记录）。


- API/E2E 夹具的清理为“尽力而为”：项目删除是软删除（`deleted_at`），列表接口不可见，但行仍留在表里；多轮执行后表里曾积到 140 个软删项目与 8 个测试用户。
- 本报告定稿前已物理清理全部测试数据：项目/需求/用例/计划/执行/缺陷/风险/会议/会议文件/会议任务关联/任务/里程碑/用户（除 admin）/会话/审计日志等表均清空，`uploads/meetings/` 测试文件已删除。最终状态：项目 0、用户 1（admin）、会议 0、会议任务关联 0；后端 `/api/v1/health` 正常，前端首页 200。

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
