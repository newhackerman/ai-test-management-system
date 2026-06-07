"""
测试管理模块数据库迁移脚本

创建测试管理模块的数据库表结构和初始数据
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_engine, get_async_session
from ..core.testmanager_integration import init_testmanager_permissions

logger = logging.getLogger(__name__)


class TestManagerMigration:
    """测试管理模块迁移类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def create_tables(self):
        """创建测试管理模块表结构"""
        
        # 测试计划表
        test_plans_sql = """
        CREATE TABLE IF NOT EXISTS test_plans (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试计划ID',
            plan_code VARCHAR(50) NOT NULL UNIQUE COMMENT '测试计划编码',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            plan_name VARCHAR(200) NOT NULL COMMENT '测试计划名称',
            description TEXT COMMENT '测试计划描述',
            
            -- 计划信息
            test_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','INTEGRATION','REGRESSION','ACCEPTANCE') NOT NULL COMMENT '测试类型',
            test_strategy TEXT COMMENT '测试策略',
            test_scope TEXT COMMENT '测试范围',
            
            -- 状态管理
            status ENUM('DRAFT','APPROVED','IN_PROGRESS','PAUSED','COMPLETED','CANCELLED') DEFAULT 'DRAFT' COMMENT '计划状态',
            
            -- 时间管理
            planned_start_date DATE COMMENT '计划开始日期',
            planned_end_date DATE COMMENT '计划结束日期',
            actual_start_date DATE COMMENT '实际开始日期',
            actual_end_date DATE COMMENT '实际结束日期',
            
            -- 人员管理
            test_manager_id BIGINT NOT NULL COMMENT '测试经理ID',
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            
            -- 进度管理
            total_cases INT DEFAULT 0 COMMENT '总用例数',
            executed_cases INT DEFAULT 0 COMMENT '已执行用例数',
            passed_cases INT DEFAULT 0 COMMENT '通过用例数',
            failed_cases INT DEFAULT 0 COMMENT '失败用例数',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_plan_code (plan_code),
            INDEX idx_project_id (project_id),
            INDEX idx_status (status),
            INDEX idx_test_type (test_type),
            INDEX idx_test_manager (test_manager_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试计划表';
        """
        
        # 测试用例表
        test_cases_sql = """
        CREATE TABLE IF NOT EXISTS test_cases (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试用例ID',
            case_code VARCHAR(50) NOT NULL UNIQUE COMMENT '测试用例编码',
            test_plan_id BIGINT COMMENT '所属测试计划ID',
            requirement_id BIGINT COMMENT '关联需求ID',
            
            -- 基本信息
            case_title VARCHAR(200) NOT NULL COMMENT '用例标题',
            case_description TEXT COMMENT '用例描述',
            case_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','USABILITY','COMPATIBILITY','API','UI') NOT NULL COMMENT '用例类型',
            
            -- 分类信息
            module VARCHAR(100) COMMENT '功能模块',
            priority ENUM('CRITICAL','HIGH','MEDIUM','LOW') DEFAULT 'MEDIUM' COMMENT '优先级',
            complexity ENUM('SIMPLE','MEDIUM','COMPLEX') DEFAULT 'MEDIUM' COMMENT '复杂度',
            automation_level ENUM('MANUAL','SEMI_AUTO','FULL_AUTO') DEFAULT 'MANUAL' COMMENT '自动化程度',
            
            -- 执行信息
            preconditions TEXT COMMENT '前置条件',
            test_steps JSON COMMENT '测试步骤',
            expected_result TEXT COMMENT '预期结果',
            test_data JSON COMMENT '测试数据',
            
            -- 状态管理
            status ENUM('DRAFT','APPROVED','ACTIVE','DEPRECATED','ARCHIVED') DEFAULT 'DRAFT' COMMENT '用例状态',
            
            -- 人员管理
            creator_id BIGINT NOT NULL COMMENT '创建人ID',
            assignee_id BIGINT COMMENT '负责人ID',
            reviewer_id BIGINT COMMENT '评审人ID',
            
            -- 元数据
            tags JSON COMMENT '标签',
            attachments JSON COMMENT '附件信息',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            version INT DEFAULT 1 COMMENT '版本号',
            
            INDEX idx_case_code (case_code),
            INDEX idx_test_plan_id (test_plan_id),
            INDEX idx_requirement_id (requirement_id),
            INDEX idx_case_type (case_type),
            INDEX idx_priority (priority),
            INDEX idx_status (status),
            INDEX idx_assignee_id (assignee_id),
            INDEX idx_creator_id (creator_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例表';
        """
        
        # 测试执行表
        test_executions_sql = """
        CREATE TABLE IF NOT EXISTS test_executions (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试执行ID',
            execution_code VARCHAR(50) NOT NULL UNIQUE COMMENT '执行编码',
            test_case_id BIGINT NOT NULL COMMENT '测试用例ID',
            test_plan_id BIGINT COMMENT '测试计划ID',
            
            -- 执行信息
            execution_type ENUM('MANUAL','AUTOMATED') NOT NULL COMMENT '执行类型',
            execution_status ENUM('NOT_EXECUTED','IN_PROGRESS','PASSED','FAILED','BLOCKED','SKIPPED') DEFAULT 'NOT_EXECUTED' COMMENT '执行状态',
            
            -- 结果信息
            actual_result TEXT COMMENT '实际结果',
            failure_reason TEXT COMMENT '失败原因',
            execution_notes TEXT COMMENT '执行备注',
            
            -- 环境信息
            test_environment VARCHAR(100) COMMENT '测试环境',
            browser_info VARCHAR(200) COMMENT '浏览器信息',
            os_info VARCHAR(100) COMMENT '操作系统信息',
            
            -- 时间信息
            started_at DATETIME COMMENT '开始时间',
            completed_at DATETIME COMMENT '完成时间',
            duration INT COMMENT '执行时长(秒)',
            
            -- 人员信息
            executor_id BIGINT NOT NULL COMMENT '执行人ID',
            
            -- 附件信息
            screenshots JSON COMMENT '截图信息',
            logs JSON COMMENT '日志信息',
            videos JSON COMMENT '视频信息',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_execution_code (execution_code),
            INDEX idx_test_case_id (test_case_id),
            INDEX idx_test_plan_id (test_plan_id),
            INDEX idx_execution_status (execution_status),
            INDEX idx_executor_id (executor_id),
            INDEX idx_started_at (started_at),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试执行表';
        """
        
        # 缺陷表
        defects_sql = """
        CREATE TABLE IF NOT EXISTS defects (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '缺陷ID',
            defect_code VARCHAR(50) NOT NULL UNIQUE COMMENT '缺陷编码',
            test_execution_id BIGINT COMMENT '关联测试执行ID',
            test_case_id BIGINT COMMENT '关联测试用例ID',
            requirement_id BIGINT COMMENT '关联需求ID',
            
            -- 基本信息
            title VARCHAR(200) NOT NULL COMMENT '缺陷标题',
            description TEXT NOT NULL COMMENT '缺陷描述',
            steps_to_reproduce TEXT COMMENT '重现步骤',
            
            -- 分类信息
            defect_type ENUM('FUNCTIONAL','PERFORMANCE','SECURITY','USABILITY','COMPATIBILITY','DATA','INTERFACE') NOT NULL COMMENT '缺陷类型',
            severity ENUM('CRITICAL','HIGH','MEDIUM','LOW') NOT NULL COMMENT '严重程度',
            priority ENUM('URGENT','HIGH','MEDIUM','LOW') NOT NULL COMMENT '优先级',
            
            -- 状态管理
            status ENUM('NEW','ASSIGNED','IN_PROGRESS','RESOLVED','VERIFIED','CLOSED','REOPENED','REJECTED','DEFERRED') DEFAULT 'NEW' COMMENT '缺陷状态',
            resolution ENUM('FIXED','DUPLICATE','NOT_A_BUG','WONT_FIX','CANNOT_REPRODUCE','DEFERRED') COMMENT '解决方案',
            
            -- 环境信息
            found_in_version VARCHAR(50) COMMENT '发现版本',
            fixed_in_version VARCHAR(50) COMMENT '修复版本',
            test_environment VARCHAR(100) COMMENT '测试环境',
            
            -- 人员管理
            reporter_id BIGINT NOT NULL COMMENT '报告人ID',
            assignee_id BIGINT COMMENT '分配人ID',
            resolver_id BIGINT COMMENT '解决人ID',
            
            -- 时间管理
            reported_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '报告时间',
            assigned_at DATETIME COMMENT '分配时间',
            resolved_at DATETIME COMMENT '解决时间',
            verified_at DATETIME COMMENT '验证时间',
            
            -- 附件信息
            attachments JSON COMMENT '附件信息',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_defect_code (defect_code),
            INDEX idx_test_execution_id (test_execution_id),
            INDEX idx_test_case_id (test_case_id),
            INDEX idx_status (status),
            INDEX idx_severity (severity),
            INDEX idx_priority (priority),
            INDEX idx_assignee_id (assignee_id),
            INDEX idx_reporter_id (reporter_id),
            INDEX idx_reported_at (reported_at),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='缺陷表';
        """
        
        # 测试报告表
        test_reports_sql = """
        CREATE TABLE IF NOT EXISTS test_reports (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试报告ID',
            report_code VARCHAR(50) NOT NULL UNIQUE COMMENT '报告编码',
            test_plan_id BIGINT COMMENT '关联测试计划ID',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            
            -- 报告信息
            report_name VARCHAR(200) NOT NULL COMMENT '报告名称',
            report_type ENUM('EXECUTION','DEFECT','COVERAGE','QUALITY','PERFORMANCE','SECURITY') NOT NULL COMMENT '报告类型',
            report_format ENUM('HTML','PDF','WORD','EXCEL','JSON') NOT NULL COMMENT '报告格式',
            
            -- 内容信息
            report_content LONGTEXT COMMENT '报告内容',
            report_summary TEXT COMMENT '报告摘要',
            file_path VARCHAR(500) COMMENT '报告文件路径',
            file_size BIGINT COMMENT '文件大小(字节)',
            
            -- 统计信息
            total_cases INT DEFAULT 0 COMMENT '总用例数',
            executed_cases INT DEFAULT 0 COMMENT '已执行用例数',
            passed_cases INT DEFAULT 0 COMMENT '通过用例数',
            failed_cases INT DEFAULT 0 COMMENT '失败用例数',
            blocked_cases INT DEFAULT 0 COMMENT '阻塞用例数',
            skipped_cases INT DEFAULT 0 COMMENT '跳过用例数',
            
            -- 质量指标
            pass_rate DECIMAL(5,2) COMMENT '通过率',
            coverage_rate DECIMAL(5,2) COMMENT '覆盖率',
            defect_density DECIMAL(8,2) COMMENT '缺陷密度',
            
            -- 时间信息
            report_period_start DATE COMMENT '报告周期开始',
            report_period_end DATE COMMENT '报告周期结束',
            
            -- 人员信息
            generated_by BIGINT NOT NULL COMMENT '生成人ID',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_report_code (report_code),
            INDEX idx_test_plan_id (test_plan_id),
            INDEX idx_project_id (project_id),
            INDEX idx_report_type (report_type),
            INDEX idx_generated_by (generated_by),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试报告表';
        """
        
        # 测试环境表
        test_environments_sql = """
        CREATE TABLE IF NOT EXISTS test_environments (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试环境ID',
            env_code VARCHAR(50) NOT NULL UNIQUE COMMENT '环境编码',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            
            -- 环境信息
            env_name VARCHAR(100) NOT NULL COMMENT '环境名称',
            env_type ENUM('DEV','TEST','STAGING','PROD','UAT') NOT NULL COMMENT '环境类型',
            description TEXT COMMENT '环境描述',
            
            -- 配置信息
            base_url VARCHAR(500) COMMENT '基础URL',
            database_config JSON COMMENT '数据库配置',
            service_config JSON COMMENT '服务配置',
            
            -- 状态管理
            status ENUM('ACTIVE','INACTIVE','MAINTENANCE','ERROR') DEFAULT 'ACTIVE' COMMENT '环境状态',
            
            -- 人员管理
            owner_id BIGINT COMMENT '负责人ID',
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_env_code (env_code),
            INDEX idx_project_id (project_id),
            INDEX idx_env_type (env_type),
            INDEX idx_status (status),
            INDEX idx_owner_id (owner_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试环境表';
        """
        
        # 自动化脚本表
        automation_scripts_sql = """
        CREATE TABLE IF NOT EXISTS automation_scripts (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自动化脚本ID',
            script_code VARCHAR(50) NOT NULL UNIQUE COMMENT '脚本编码',
            test_case_id BIGINT NOT NULL COMMENT '关联测试用例ID',
            
            -- 脚本信息
            script_name VARCHAR(200) NOT NULL COMMENT '脚本名称',
            framework ENUM('PLAYWRIGHT','SELENIUM','CYPRESS','PYTEST','JUNIT') NOT NULL COMMENT '自动化框架',
            language ENUM('PYTHON','JAVASCRIPT','JAVA','CSHARP') NOT NULL COMMENT '编程语言',
            
            -- 脚本内容
            script_content LONGTEXT NOT NULL COMMENT '脚本内容',
            script_path VARCHAR(500) COMMENT '脚本文件路径',
            dependencies JSON COMMENT '依赖信息',
            
            -- 执行配置
            execution_config JSON COMMENT '执行配置',
            timeout_seconds INT DEFAULT 300 COMMENT '超时时间(秒)',
            
            -- 状态管理
            status ENUM('DRAFT','ACTIVE','DEPRECATED','ERROR') DEFAULT 'DRAFT' COMMENT '脚本状态',
            
            -- 人员管理
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            updated_by BIGINT COMMENT '更新人ID',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_script_code (script_code),
            INDEX idx_test_case_id (test_case_id),
            INDEX idx_framework (framework),
            INDEX idx_language (language),
            INDEX idx_status (status),
            INDEX idx_created_by (created_by),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自动化脚本表';
        """
        
        # 执行所有建表语句
        tables = [
            ("test_plans", test_plans_sql),
            ("test_cases", test_cases_sql),
            ("test_executions", test_executions_sql),
            ("defects", defects_sql),
            ("test_reports", test_reports_sql),
            ("test_environments", test_environments_sql),
            ("automation_scripts", automation_scripts_sql)
        ]
        
        async with async_engine.begin() as conn:
            for table_name, sql in tables:
                try:
                    await conn.execute(text(sql))
                    self.logger.info(f"创建表 {table_name} 成功")
                except Exception as e:
                    self.logger.error(f"创建表 {table_name} 失败: {e}")
                    raise
    
    async def insert_initial_data(self):
        """插入初始数据"""
        
        # 测试环境初始数据
        test_environments_data = """
        INSERT IGNORE INTO test_environments (env_code, project_id, env_name, env_type, description, base_url, status, created_by) VALUES
        ('ENV-DEV-001', 1, '开发环境', 'DEV', '开发测试环境', 'http://localhost:8000', 'ACTIVE', 1),
        ('ENV-TEST-001', 1, '测试环境', 'TEST', '功能测试环境', 'http://test.example.com', 'ACTIVE', 1),
        ('ENV-STAGING-001', 1, '预生产环境', 'STAGING', '预生产测试环境', 'http://staging.example.com', 'ACTIVE', 1);
        """
        
        async with async_engine.begin() as conn:
            try:
                await conn.execute(text(test_environments_data))
                self.logger.info("插入测试环境初始数据成功")
            except Exception as e:
                self.logger.error(f"插入测试环境初始数据失败: {e}")
    
    async def create_indexes(self):
        """创建额外的索引"""
        
        indexes = [
            # 复合索引
            "CREATE INDEX IF NOT EXISTS idx_test_cases_plan_status ON test_cases (test_plan_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_test_executions_case_status ON test_executions (test_case_id, execution_status)",
            "CREATE INDEX IF NOT EXISTS idx_defects_assignee_status ON defects (assignee_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_test_reports_project_type ON test_reports (project_id, report_type)",
            
            # 全文索引
            "ALTER TABLE test_cases ADD FULLTEXT INDEX ft_case_title_desc (case_title, case_description)",
            "ALTER TABLE defects ADD FULLTEXT INDEX ft_defect_title_desc (title, description)",
            "ALTER TABLE test_reports ADD FULLTEXT INDEX ft_report_name_summary (report_name, report_summary)"
        ]
        
        async with async_engine.begin() as conn:
            for index_sql in indexes:
                try:
                    await conn.execute(text(index_sql))
                    self.logger.info(f"创建索引成功: {index_sql[:50]}...")
                except Exception as e:
                    self.logger.warning(f"创建索引失败: {e}")
    
    async def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            async with async_engine.begin() as conn:
                result = await conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name"
                ), {"table_name": table_name})
                count = result.scalar()
                return count > 0
        except Exception as e:
            self.logger.error(f"检查表 {table_name} 是否存在失败: {e}")
            return False
    
    async def migrate(self):
        """执行完整迁移"""
        try:
            self.logger.info("开始测试管理模块数据库迁移...")
            
            # 1. 创建表结构
            await self.create_tables()
            self.logger.info("表结构创建完成")
            
            # 2. 创建索引
            await self.create_indexes()
            self.logger.info("索引创建完成")
            
            # 3. 插入初始数据
            await self.insert_initial_data()
            self.logger.info("初始数据插入完成")
            
            # 4. 初始化权限
            async for db in get_async_session():
                await init_testmanager_permissions(db)
                break
            self.logger.info("权限初始化完成")
            
            self.logger.info("测试管理模块数据库迁移完成")
            
        except Exception as e:
            self.logger.error(f"数据库迁移失败: {e}")
            raise
    
    async def rollback(self):
        """回滚迁移"""
        try:
            self.logger.info("开始回滚测试管理模块数据库迁移...")
            
            tables_to_drop = [
                "automation_scripts",
                "test_environments", 
                "test_reports",
                "defects",
                "test_executions",
                "test_cases",
                "test_plans"
            ]
            
            async with async_engine.begin() as conn:
                for table_name in tables_to_drop:
                    try:
                        await conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                        self.logger.info(f"删除表 {table_name} 成功")
                    except Exception as e:
                        self.logger.error(f"删除表 {table_name} 失败: {e}")
            
            self.logger.info("测试管理模块数据库迁移回滚完成")
            
        except Exception as e:
            self.logger.error(f"数据库迁移回滚失败: {e}")
            raise


# 迁移执行函数

async def run_migration():
    """运行迁移"""
    migration = TestManagerMigration()
    await migration.migrate()


async def run_rollback():
    """运行回滚"""
    migration = TestManagerMigration()
    await migration.rollback()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(run_rollback())
    else:
        asyncio.run(run_migration())