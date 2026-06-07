"""
创建需求管理模块数据库表

这个脚本创建需求管理模块所需的所有数据库表，包括：
- requirements: 需求表
- requirement_status_history: 需求状态历史表
- requirement_dependencies: 需求依赖关系表
- requirement_reviews: 需求评审表
- requirement_review_comments: 需求评审意见表
- requirement_change_requests: 需求变更请求表
- requirement_traceability_links: 需求追溯链接表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
import logging
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_requirement_tables():
    """创建需求管理模块的数据库表"""
    
    # 从环境变量获取数据库URL
    database_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:123456@localhost:3306/ai_test_management")
    
    # 确保使用同步驱动
    if "mysql+asyncmy://" in database_url:
        database_url = database_url.replace("mysql+asyncmy://", "mysql+pymysql://")
    
    engine = create_engine(database_url)
    
    # SQL语句列表
    sql_statements = [
        # 1. 需求表
        """
        CREATE TABLE IF NOT EXISTS requirements (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '需求ID',
            requirement_code VARCHAR(50) NOT NULL UNIQUE COMMENT '需求编码',
            project_id BIGINT NOT NULL COMMENT '所属项目ID',
            parent_id BIGINT COMMENT '父需求ID',
            title VARCHAR(200) NOT NULL COMMENT '需求标题',
            description TEXT COMMENT '需求描述',
            acceptance_criteria TEXT COMMENT '验收标准',
            
            -- 分类和优先级
            requirement_type ENUM('FUNCTIONAL','NON_FUNCTIONAL','CONSTRAINT','INTERFACE') NOT NULL COMMENT '需求类型',
            category VARCHAR(100) COMMENT '需求分类',
            priority ENUM('CRITICAL','HIGH','MEDIUM','LOW','OPTIONAL') DEFAULT 'MEDIUM' COMMENT '优先级',
            business_value ENUM('CORE','IMPORTANT','NORMAL','OPTIONAL') DEFAULT 'NORMAL' COMMENT '业务价值',
            
            -- 状态管理
            status ENUM('DRAFT','PENDING_REVIEW','REVIEWING','NEEDS_REVISION','APPROVED','IN_DEVELOPMENT','PAUSED','TESTING','TEST_FAILED','COMPLETED','DEPLOYED','CLOSED','CANCELLED') DEFAULT 'DRAFT' COMMENT '需求状态',
            
            -- 复杂度和工作量
            complexity ENUM('SIMPLE','MEDIUM','COMPLEX','VERY_COMPLEX') COMMENT '技术复杂度',
            estimated_effort DECIMAL(6,2) COMMENT '预估工作量(人天)',
            actual_effort DECIMAL(6,2) COMMENT '实际工作量(人天)',
            
            -- 人员管理
            creator_id BIGINT NOT NULL COMMENT '创建人ID',
            assignee_id BIGINT COMMENT '负责人ID',
            reviewer_id BIGINT COMMENT '评审人ID',
            
            -- 时间管理
            planned_start_date DATE COMMENT '计划开始日期',
            planned_end_date DATE COMMENT '计划完成日期',
            actual_start_date DATE COMMENT '实际开始日期',
            actual_end_date DATE COMMENT '实际完成日期',
            
            -- 质量管理
            quality_score DECIMAL(3,1) COMMENT '质量评分(0-10)',
            completeness_score DECIMAL(3,1) COMMENT '完整性评分(0-10)',
            
            -- 元数据
            tags JSON COMMENT '标签',
            custom_fields JSON COMMENT '自定义字段',
            attachments JSON COMMENT '附件信息',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            updated_by BIGINT COMMENT '更新人ID',
            version INT DEFAULT 1 COMMENT '版本号',
            
            INDEX idx_requirement_code (requirement_code),
            INDEX idx_project_id (project_id),
            INDEX idx_parent_id (parent_id),
            INDEX idx_status (status),
            INDEX idx_priority (priority),
            INDEX idx_assignee_id (assignee_id),
            INDEX idx_created_at (created_at),
            INDEX idx_planned_dates (planned_start_date, planned_end_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求表';
        """,
        
        # 2. 需求状态历史表
        """
        CREATE TABLE IF NOT EXISTS requirement_status_history (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '历史记录ID',
            requirement_id BIGINT NOT NULL COMMENT '需求ID',
            old_status ENUM('DRAFT','PENDING_REVIEW','REVIEWING','NEEDS_REVISION','APPROVED','IN_DEVELOPMENT','PAUSED','TESTING','TEST_FAILED','COMPLETED','DEPLOYED','CLOSED','CANCELLED') COMMENT '变更前状态',
            new_status ENUM('DRAFT','PENDING_REVIEW','REVIEWING','NEEDS_REVISION','APPROVED','IN_DEVELOPMENT','PAUSED','TESTING','TEST_FAILED','COMPLETED','DEPLOYED','CLOSED','CANCELLED') NOT NULL COMMENT '变更后状态',
            change_reason TEXT COMMENT '变更原因',
            change_description TEXT COMMENT '变更描述',
            changed_by BIGINT NOT NULL COMMENT '变更人ID',
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            INDEX idx_requirement_id (requirement_id),
            INDEX idx_changed_at (changed_at),
            INDEX idx_changed_by (changed_by)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求状态历史表';
        """,
        
        # 3. 需求依赖关系表
        """
        CREATE TABLE IF NOT EXISTS requirement_dependencies (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '依赖关系ID',
            source_requirement_id BIGINT NOT NULL COMMENT '源需求ID',
            target_requirement_id BIGINT NOT NULL COMMENT '目标需求ID',
            dependency_type ENUM('DEPENDS_ON','BLOCKS','RELATES_TO','CONFLICTS_WITH','DUPLICATES','REPLACES') NOT NULL COMMENT '依赖类型',
            description TEXT COMMENT '依赖描述',
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            FOREIGN KEY (source_requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            FOREIGN KEY (target_requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            UNIQUE KEY uk_requirement_dependency (source_requirement_id, target_requirement_id, dependency_type),
            INDEX idx_source_requirement (source_requirement_id),
            INDEX idx_target_requirement (target_requirement_id),
            INDEX idx_dependency_type (dependency_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求依赖关系表';
        """,
        
        # 4. 需求评审表
        """
        CREATE TABLE IF NOT EXISTS requirement_reviews (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '评审ID',
            requirement_id BIGINT NOT NULL COMMENT '需求ID',
            review_type ENUM('FORMAL','INFORMAL','WALKTHROUGH','INSPECTION') NOT NULL COMMENT '评审类型',
            review_status ENUM('PENDING','IN_PROGRESS','COMPLETED','CANCELLED') DEFAULT 'PENDING' COMMENT '评审状态',
            
            -- 评审信息
            title VARCHAR(200) NOT NULL COMMENT '评审标题',
            description TEXT COMMENT '评审描述',
            review_criteria TEXT COMMENT '评审标准',
            
            -- 人员管理
            moderator_id BIGINT NOT NULL COMMENT '评审主持人ID',
            reviewers JSON COMMENT '评审人员列表',
            
            -- 时间管理
            scheduled_date DATETIME COMMENT '计划评审时间',
            started_at DATETIME COMMENT '实际开始时间',
            completed_at DATETIME COMMENT '完成时间',
            
            -- 评审结果
            decision ENUM('APPROVED','APPROVED_WITH_MINOR_CHANGES','NEEDS_MAJOR_REVISION','REJECTED') COMMENT '评审决策',
            summary TEXT COMMENT '评审总结',
            
            -- 审计字段
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            INDEX idx_requirement_id (requirement_id),
            INDEX idx_review_status (review_status),
            INDEX idx_moderator_id (moderator_id),
            INDEX idx_scheduled_date (scheduled_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求评审表';
        """,
        
        # 5. 需求评审意见表
        """
        CREATE TABLE IF NOT EXISTS requirement_review_comments (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '评审意见ID',
            review_id BIGINT NOT NULL COMMENT '评审ID',
            requirement_id BIGINT NOT NULL COMMENT '需求ID',
            
            -- 意见内容
            comment_type ENUM('ISSUE','SUGGESTION','QUESTION','APPROVAL','REJECTION') NOT NULL COMMENT '意见类型',
            severity ENUM('CRITICAL','MAJOR','MINOR','TRIVIAL') COMMENT '严重程度',
            content TEXT NOT NULL COMMENT '意见内容',
            suggestion TEXT COMMENT '改进建议',
            
            -- 位置信息
            section VARCHAR(100) COMMENT '相关章节',
            line_number INT COMMENT '行号',
            
            -- 处理状态
            status ENUM('OPEN','IN_PROGRESS','RESOLVED','CLOSED','REJECTED') DEFAULT 'OPEN' COMMENT '处理状态',
            resolution TEXT COMMENT '解决方案',
            resolved_by BIGINT COMMENT '解决人ID',
            resolved_at DATETIME COMMENT '解决时间',
            
            -- 审计字段
            reviewer_id BIGINT NOT NULL COMMENT '评审人ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            FOREIGN KEY (review_id) REFERENCES requirement_reviews(id) ON DELETE CASCADE,
            FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            INDEX idx_review_id (review_id),
            INDEX idx_requirement_id (requirement_id),
            INDEX idx_reviewer_id (reviewer_id),
            INDEX idx_status (status),
            INDEX idx_severity (severity)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求评审意见表';
        """,
        
        # 6. 需求变更请求表
        """
        CREATE TABLE IF NOT EXISTS requirement_change_requests (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '变更请求ID',
            requirement_id BIGINT NOT NULL COMMENT '需求ID',
            change_request_code VARCHAR(50) NOT NULL UNIQUE COMMENT '变更请求编码',
            
            -- 变更信息
            title VARCHAR(200) NOT NULL COMMENT '变更标题',
            description TEXT NOT NULL COMMENT '变更描述',
            reason TEXT NOT NULL COMMENT '变更原因',
            change_type ENUM('ADDITION','MODIFICATION','DELETION','CLARIFICATION') NOT NULL COMMENT '变更类型',
            
            -- 影响分析
            impact_analysis TEXT COMMENT '影响分析',
            effort_estimate DECIMAL(6,2) COMMENT '工作量估算',
            cost_estimate DECIMAL(10,2) COMMENT '成本估算',
            risk_assessment TEXT COMMENT '风险评估',
            
            -- 审批流程
            status ENUM('SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED','IMPLEMENTED','CLOSED') DEFAULT 'SUBMITTED' COMMENT '变更状态',
            priority ENUM('EMERGENCY','HIGH','MEDIUM','LOW') DEFAULT 'MEDIUM' COMMENT '变更优先级',
            
            -- 人员管理
            requestor_id BIGINT NOT NULL COMMENT '申请人ID',
            approver_id BIGINT COMMENT '审批人ID',
            implementer_id BIGINT COMMENT '实施人ID',
            
            -- 时间管理
            requested_date DATE NOT NULL COMMENT '申请日期',
            target_date DATE COMMENT '目标完成日期',
            approved_date DATE COMMENT '审批日期',
            implemented_date DATE COMMENT '实施日期',
            
            -- 审计字段
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
            INDEX idx_requirement_id (requirement_id),
            INDEX idx_change_request_code (change_request_code),
            INDEX idx_status (status),
            INDEX idx_priority (priority),
            INDEX idx_requestor_id (requestor_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求变更请求表';
        """,
        
        # 7. 需求追溯链接表
        """
        CREATE TABLE IF NOT EXISTS requirement_traceability_links (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '追溯链接ID',
            source_type VARCHAR(50) NOT NULL COMMENT '源对象类型',
            source_id BIGINT NOT NULL COMMENT '源对象ID',
            target_type VARCHAR(50) NOT NULL COMMENT '目标对象类型',
            target_id BIGINT NOT NULL COMMENT '目标对象ID',
            link_type ENUM('DERIVES_FROM','IMPLEMENTS','TESTS','VALIDATES','REFINES') NOT NULL COMMENT '链接类型',
            description TEXT COMMENT '链接描述',
            created_by BIGINT NOT NULL COMMENT '创建人ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            UNIQUE KEY uk_traceability_link (source_type, source_id, target_type, target_id, link_type),
            INDEX idx_source (source_type, source_id),
            INDEX idx_target (target_type, target_id),
            INDEX idx_link_type (link_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求追溯链接表';
        """
    ]
    
    try:
        with engine.connect() as connection:
            logger.info("开始创建需求管理模块数据库表...")
            
            for i, sql in enumerate(sql_statements, 1):
                logger.info(f"执行第 {i} 个SQL语句...")
                connection.execute(text(sql))
                connection.commit()
                logger.info(f"第 {i} 个SQL语句执行成功")
            
            logger.info("所有需求管理模块数据库表创建完成！")
            
    except Exception as e:
        logger.error(f"创建数据库表时发生错误: {str(e)}")
        raise e
    finally:
        engine.dispose()

if __name__ == "__main__":
    create_requirement_tables()