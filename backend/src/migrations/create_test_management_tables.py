"""
测试管理模块数据库迁移脚本

创建测试管理相关的数据库表结构
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_test_management_tables(session: AsyncSession):
    """创建测试管理模块的数据库表"""
    
    # 创建测试计划表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_plans (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试计划ID',
            plan_code VARCHAR(50) NOT NULL UNIQUE COMMENT '测试计划编码',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            plan_name VARCHAR(200) NOT NULL COMMENT '测试计划名称',
            description TEXT COMMENT '测试计划描述',
            
            test_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','INTEGRATION','REGRESSION','ACCEPTANCE') NOT NULL COMMENT '测试类型',
            test_strategy TEXT COMMENT '测试策略',
            test_scope TEXT COMMENT '测试范围',
            
            status ENUM('DRAFT','APPROVED','IN_PROGRESS','PAUSED','COMPLETED','CANCELLED') DEFAULT 'DRAFT' COMMENT '计划状态',
            
            planned_start_date DATE COMMENT '计划开始日期',
            planned_end_date DATE COMMENT '计划结束日期',
            actual_start_date DATE COMMENT '实际开始日期',
            actual_end_date DATE COMMENT '实际结束日期',
            
            test_manager_id BIGINT NOT NULL COMMENT '测试经理ID',
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            
            total_cases INT DEFAULT 0 COMMENT '总用例数',
            executed_cases INT DEFAULT 0 COMMENT '已执行用例数',
            passed_cases INT DEFAULT 0 COMMENT '通过用例数',
            failed_cases INT DEFAULT 0 COMMENT '失败用例数',
            
            pass_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '通过率',
            execution_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '执行率',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_test_plans_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            
            INDEX idx_test_plans_code (plan_code),
            INDEX idx_test_plans_project (project_id),
            INDEX idx_test_plans_status (status),
            INDEX idx_test_plans_type (test_type),
            INDEX idx_test_plans_manager (test_manager_id),
            INDEX idx_test_plans_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试计划表';
    """))
    
    # 创建测试阶段表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_phases (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试阶段ID',
            test_plan_id BIGINT NOT NULL COMMENT '测试计划ID',
            phase_name VARCHAR(100) NOT NULL COMMENT '阶段名称',
            description TEXT COMMENT '阶段描述',
            
            phase_type ENUM('UNIT_TEST','INTEGRATION_TEST','SYSTEM_TEST','ACCEPTANCE_TEST','REGRESSION_TEST') NOT NULL COMMENT '阶段类型',
            status ENUM('PENDING','IN_PROGRESS','COMPLETED','OVERDUE','CANCELLED') DEFAULT 'PENDING' COMMENT '阶段状态',
            
            planned_start_date DATE COMMENT '计划开始日期',
            planned_end_date DATE COMMENT '计划结束日期',
            actual_start_date DATE COMMENT '实际开始日期',
            actual_end_date DATE COMMENT '实际结束日期',
            
            entry_criteria TEXT COMMENT '进入标准',
            exit_criteria TEXT COMMENT '退出标准',
            
            total_cases INT DEFAULT 0 COMMENT '阶段用例总数',
            executed_cases INT DEFAULT 0 COMMENT '已执行用例数',
            passed_cases INT DEFAULT 0 COMMENT '通过用例数',
            failed_cases INT DEFAULT 0 COMMENT '失败用例数',
            
            phase_manager_id BIGINT COMMENT '阶段负责人ID',
            dependency_phases JSON COMMENT '依赖阶段ID列表',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_test_phases_plan FOREIGN KEY (test_plan_id) REFERENCES test_plans(id) ON DELETE CASCADE,
            
            INDEX idx_test_phases_plan (test_plan_id),
            INDEX idx_test_phases_status (status),
            INDEX idx_test_phases_type (phase_type),
            INDEX idx_test_phases_manager (phase_manager_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试阶段表';
    """))
    
    # 创建测试资源表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_resources (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '资源ID',
            test_plan_id BIGINT NOT NULL COMMENT '测试计划ID',
            user_id BIGINT NOT NULL COMMENT '用户ID',
            
            role_in_test ENUM('TEST_MANAGER','TEST_LEAD','TEST_ENGINEER','AUTOMATION_ENGINEER','PERFORMANCE_TESTER','SECURITY_TESTER') NOT NULL COMMENT '测试角色',
            allocation_percentage DECIMAL(5,2) DEFAULT 100.00 COMMENT '分配百分比',
            
            start_date DATE COMMENT '开始日期',
            end_date DATE COMMENT '结束日期',
            
            skills JSON COMMENT '技能标签',
            responsibilities TEXT COMMENT '职责描述',
            
            estimated_hours DECIMAL(6,2) COMMENT '预估工时',
            actual_hours DECIMAL(6,2) DEFAULT 0.00 COMMENT '实际工时',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_test_resources_plan FOREIGN KEY (test_plan_id) REFERENCES test_plans(id) ON DELETE CASCADE,
            
            INDEX idx_test_resources_plan (test_plan_id),
            INDEX idx_test_resources_user (user_id),
            INDEX idx_test_resources_role (role_in_test)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试资源表';
    """))
    
    # 更新测试用例表结构
    await session.execute(text("""
        ALTER TABLE test_cases 
        ADD COLUMN IF NOT EXISTS case_code VARCHAR(50) UNIQUE COMMENT '测试用例编码' AFTER id,
        ADD COLUMN IF NOT EXISTS test_plan_id BIGINT COMMENT '所属测试计划ID' AFTER case_code,
        ADD COLUMN IF NOT EXISTS case_title VARCHAR(200) NOT NULL COMMENT '测试用例标题' AFTER requirement_id,
        ADD COLUMN IF NOT EXISTS case_description TEXT COMMENT '测试用例描述' AFTER case_title,
        ADD COLUMN IF NOT EXISTS case_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','USABILITY','COMPATIBILITY','API','UI') NOT NULL COMMENT '用例类型' AFTER case_description,
        ADD COLUMN IF NOT EXISTS module VARCHAR(100) COMMENT '功能模块' AFTER case_type,
        ADD COLUMN IF NOT EXISTS complexity ENUM('SIMPLE','MEDIUM','COMPLEX') DEFAULT 'MEDIUM' COMMENT '复杂度' AFTER priority,
        ADD COLUMN IF NOT EXISTS automation_level ENUM('MANUAL','SEMI_AUTO','FULL_AUTO') DEFAULT 'MANUAL' COMMENT '自动化程度' AFTER complexity,
        ADD INDEX IF NOT EXISTS idx_test_cases_code (case_code),
        ADD INDEX IF NOT EXISTS idx_test_cases_plan (test_plan_id),
        ADD INDEX IF NOT EXISTS idx_test_cases_module (module),
        ADD CONSTRAINT fk_test_cases_plan FOREIGN KEY (test_plan_id) REFERENCES test_plans(id) ON DELETE SET NULL;
    """))
    
    # 创建自动化脚本表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS automation_scripts (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '脚本ID',
            test_case_id BIGINT NOT NULL COMMENT '测试用例ID',
            
            script_name VARCHAR(200) NOT NULL COMMENT '脚本名称',
            framework ENUM('PLAYWRIGHT','SELENIUM','CYPRESS','PYTEST','JEST') NOT NULL COMMENT '自动化框架',
            language ENUM('PYTHON','JAVASCRIPT','JAVA','CSHARP') NOT NULL COMMENT '编程语言',
            
            script_content TEXT NOT NULL COMMENT '脚本内容',
            script_path VARCHAR(500) COMMENT '脚本文件路径',
            
            browser VARCHAR(50) COMMENT '目标浏览器',
            environment_config JSON COMMENT '环境配置',
            dependencies JSON COMMENT '依赖项',
            
            is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            last_execution_date DATETIME COMMENT '最后执行日期',
            last_execution_status ENUM('NOT_EXECUTED','PASSED','FAILED','BLOCKED','SKIPPED','IN_PROGRESS') COMMENT '最后执行状态',
            execution_count INT DEFAULT 0 COMMENT '执行次数',
            success_count INT DEFAULT 0 COMMENT '成功次数',
            
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            updated_by BIGINT COMMENT '更新人ID',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_automation_scripts_case FOREIGN KEY (test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            
            INDEX idx_automation_scripts_case (test_case_id),
            INDEX idx_automation_scripts_framework (framework),
            INDEX idx_automation_scripts_language (language),
            INDEX idx_automation_scripts_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自动化脚本表';
    """))
    
    # 更新测试执行表结构
    await session.execute(text("""
        ALTER TABLE test_executions
        ADD COLUMN IF NOT EXISTS execution_code VARCHAR(50) UNIQUE COMMENT '执行编码' AFTER id,
        ADD COLUMN IF NOT EXISTS test_plan_id BIGINT COMMENT '测试计划ID' AFTER test_case_id,
        ADD COLUMN IF NOT EXISTS execution_type ENUM('MANUAL','AUTOMATED') NOT NULL COMMENT '执行类型' AFTER test_plan_id,
        ADD COLUMN IF NOT EXISTS failure_reason TEXT COMMENT '失败原因' AFTER actual_result,
        ADD COLUMN IF NOT EXISTS browser_info VARCHAR(200) COMMENT '浏览器信息' AFTER test_environment,
        ADD COLUMN IF NOT EXISTS os_info VARCHAR(100) COMMENT '操作系统信息' AFTER browser_info,
        ADD COLUMN IF NOT EXISTS started_at DATETIME COMMENT '开始时间' AFTER os_info,
        ADD COLUMN IF NOT EXISTS completed_at DATETIME COMMENT '完成时间' AFTER started_at,
        ADD COLUMN IF NOT EXISTS duration INT COMMENT '执行时长(秒)' AFTER completed_at,
        ADD COLUMN IF NOT EXISTS videos JSON COMMENT '视频信息' AFTER logs,
        ADD INDEX IF NOT EXISTS idx_test_executions_code (execution_code),
        ADD INDEX IF NOT EXISTS idx_test_executions_plan (test_plan_id),
        ADD INDEX IF NOT EXISTS idx_test_executions_type (execution_type),
        ADD INDEX IF NOT EXISTS idx_test_executions_started (started_at),
        ADD CONSTRAINT fk_test_executions_plan FOREIGN KEY (test_plan_id) REFERENCES test_plans(id) ON DELETE SET NULL;
    """))
    
    # 更新缺陷表结构
    await session.execute(text("""
        ALTER TABLE defects
        ADD COLUMN IF NOT EXISTS test_execution_id BIGINT COMMENT '关联测试执行ID' AFTER defect_code,
        ADD COLUMN IF NOT EXISTS defect_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','USABILITY','COMPATIBILITY','DATA','INTERFACE') NOT NULL COMMENT '缺陷类型' AFTER steps_to_reproduce,
        ADD COLUMN IF NOT EXISTS found_in_version VARCHAR(50) COMMENT '发现版本' AFTER defect_type,
        ADD COLUMN IF NOT EXISTS fixed_in_version VARCHAR(50) COMMENT '修复版本' AFTER found_in_version,
        ADD COLUMN IF NOT EXISTS reported_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '报告时间' AFTER resolver_id,
        ADD COLUMN IF NOT EXISTS assigned_at DATETIME COMMENT '分配时间' AFTER reported_at,
        ADD COLUMN IF NOT EXISTS resolved_at DATETIME COMMENT '解决时间' AFTER assigned_at,
        ADD COLUMN IF NOT EXISTS verified_at DATETIME COMMENT '验证时间' AFTER resolved_at,
        MODIFY COLUMN resolution ENUM('FIXED','DUPLICATE','NOT_A_BUG','WONT_FIX','CANNOT_REPRODUCE','DEFERRED') COMMENT '解决方案',
        ADD INDEX IF NOT EXISTS idx_defects_execution (test_execution_id),
        ADD INDEX IF NOT EXISTS idx_defects_type (defect_type),
        ADD INDEX IF NOT EXISTS idx_defects_reported (reported_at),
        ADD CONSTRAINT fk_defects_execution FOREIGN KEY (test_execution_id) REFERENCES test_executions(id) ON DELETE SET NULL;
    """))
    
    # 创建测试报告表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_reports (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试报告ID',
            report_code VARCHAR(50) NOT NULL UNIQUE COMMENT '报告编码',
            test_plan_id BIGINT COMMENT '关联测试计划ID',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            
            report_name VARCHAR(200) NOT NULL COMMENT '报告名称',
            report_type ENUM('EXECUTION','DEFECT','COVERAGE','QUALITY','PERFORMANCE','SECURITY') NOT NULL COMMENT '报告类型',
            report_format ENUM('HTML','PDF','WORD','EXCEL','JSON') NOT NULL COMMENT '报告格式',
            
            report_content TEXT COMMENT '报告内容',
            report_summary TEXT COMMENT '报告摘要',
            file_path VARCHAR(500) COMMENT '报告文件路径',
            file_size BIGINT COMMENT '文件大小(字节)',
            
            total_cases INT DEFAULT 0 COMMENT '总用例数',
            executed_cases INT DEFAULT 0 COMMENT '已执行用例数',
            passed_cases INT DEFAULT 0 COMMENT '通过用例数',
            failed_cases INT DEFAULT 0 COMMENT '失败用例数',
            blocked_cases INT DEFAULT 0 COMMENT '阻塞用例数',
            skipped_cases INT DEFAULT 0 COMMENT '跳过用例数',
            
            pass_rate DECIMAL(5,2) COMMENT '通过率',
            coverage_rate DECIMAL(5,2) COMMENT '覆盖率',
            defect_density DECIMAL(8,2) COMMENT '缺陷密度',
            
            report_period_start DATE COMMENT '报告周期开始',
            report_period_end DATE COMMENT '报告周期结束',
            
            status ENUM('GENERATING','COMPLETED','FAILED','ARCHIVED') DEFAULT 'GENERATING' COMMENT '报告状态',
            
            generated_by BIGINT NOT NULL COMMENT '生成人ID',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_test_reports_plan FOREIGN KEY (test_plan_id) REFERENCES test_plans(id) ON DELETE SET NULL,
            CONSTRAINT fk_test_reports_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            
            INDEX idx_test_reports_code (report_code),
            INDEX idx_test_reports_plan (test_plan_id),
            INDEX idx_test_reports_project (project_id),
            INDEX idx_test_reports_type (report_type),
            INDEX idx_test_reports_status (status),
            INDEX idx_test_reports_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试报告表';
    """))
    
    # 创建报告模板表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS report_templates (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '模板ID',
            template_name VARCHAR(200) NOT NULL COMMENT '模板名称',
            description TEXT COMMENT '模板描述',
            
            report_type ENUM('EXECUTION','DEFECT','COVERAGE','QUALITY','PERFORMANCE','SECURITY') NOT NULL COMMENT '报告类型',
            template_content TEXT NOT NULL COMMENT '模板内容',
            
            is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认模板',
            is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_report_templates_type (report_type),
            INDEX idx_report_templates_active (is_active),
            INDEX idx_report_templates_default (is_default)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报告模板表';
    """))
    
    # 创建报告订阅表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS report_subscriptions (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '订阅ID',
            user_id BIGINT NOT NULL COMMENT '用户ID',
            project_id BIGINT COMMENT '项目ID',
            
            report_type ENUM('EXECUTION','DEFECT','COVERAGE','QUALITY','PERFORMANCE','SECURITY') NOT NULL COMMENT '报告类型',
            frequency ENUM('DAILY','WEEKLY','MONTHLY','ON_COMPLETION') NOT NULL COMMENT '订阅频率',
            
            email_enabled BOOLEAN DEFAULT TRUE COMMENT '邮件通知',
            sms_enabled BOOLEAN DEFAULT FALSE COMMENT '短信通知',
            
            is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            CONSTRAINT fk_report_subscriptions_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            
            INDEX idx_report_subscriptions_user (user_id),
            INDEX idx_report_subscriptions_project (project_id),
            INDEX idx_report_subscriptions_type (report_type),
            INDEX idx_report_subscriptions_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报告订阅表';
    """))
    
    await session.commit()
    print("测试管理模块数据库表创建完成")


async def drop_test_management_tables(session: AsyncSession):
    """删除测试管理模块的数据库表"""
    
    # 按依赖关系逆序删除表
    tables = [
        'report_subscriptions',
        'report_templates', 
        'test_reports',
        'automation_scripts',
        'test_resources',
        'test_phases',
        'test_plans'
    ]
    
    for table in tables:
        await session.execute(text(f"DROP TABLE IF EXISTS {table}"))
    
    await session.commit()
    print("测试管理模块数据库表删除完成")