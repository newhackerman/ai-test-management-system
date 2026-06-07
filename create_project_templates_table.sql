-- 创建项目模板表
CREATE TABLE IF NOT EXISTS project_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '模板ID',
    template_name VARCHAR(200) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    
    -- 模板分类
    template_type ENUM('FUNCTIONAL', 'PERFORMANCE', 'SECURITY', 'AUTOMATION', 'INTEGRATION') NOT NULL COMMENT '模板类型',
    category VARCHAR(100) COMMENT '模板分类',
    
    -- 状态管理
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    
    -- 模板配置
    template_config JSON NOT NULL COMMENT '模板配置JSON',
    default_tasks JSON COMMENT '默认任务配置',
    default_milestones JSON COMMENT '默认里程碑配置',
    default_roles JSON COMMENT '默认角色配置',
    
    -- 统计信息
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    success_rate DECIMAL(5,2) COMMENT '成功率',
    avg_duration_days INT COMMENT '平均项目周期(天)',
    
    -- 审计字段
    created_by INT NOT NULL COMMENT '创建人ID',
    updated_by INT COMMENT '更新人ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_template_name (template_name),
    INDEX idx_template_type (template_type),
    INDEX idx_category (category),
    INDEX idx_is_active (is_active),
    INDEX idx_is_public (is_public),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at),
    
    -- 唯一约束
    UNIQUE KEY uk_template_name (template_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目模板表';

-- 添加模板ID字段到项目表（如果不存在）
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS template_id BIGINT COMMENT '使用的模板ID',
ADD INDEX IF NOT EXISTS idx_template_id (template_id);

-- 插入示例模板数据
INSERT IGNORE INTO project_templates (
    template_name, description, template_type, category, is_active, is_public,
    template_config, default_tasks, default_milestones, created_by
) VALUES 
(
    'Web功能测试模板',
    '适用于Web应用功能测试的标准模板，包含完整的测试流程和最佳实践',
    'FUNCTIONAL',
    'WEB_TESTING',
    TRUE,
    TRUE,
    JSON_OBJECT(
        'project_settings', JSON_OBJECT(
            'priority', 'MEDIUM',
            'risk_level', 'LOW',
            'custom_fields', JSON_OBJECT(
                'test_environment', 'staging',
                'browser_support', JSON_ARRAY('Chrome', 'Firefox', 'Safari')
            )
        ),
        'workflow_settings', JSON_OBJECT(
            'approval_required', TRUE,
            'auto_assign', FALSE,
            'notification_enabled', TRUE
        )
    ),
    JSON_ARRAY(
        JSON_OBJECT(
            'name', '需求分析',
            'description', '分析测试需求和范围',
            'type', 'REQUIREMENT_ANALYSIS',
            'priority', 'HIGH',
            'estimated_hours', 16,
            'acceptance_criteria', '需求文档完整，评审通过'
        ),
        JSON_OBJECT(
            'name', '测试用例设计',
            'description', '设计功能测试用例',
            'type', 'TEST_DESIGN',
            'priority', 'HIGH',
            'estimated_hours', 40,
            'acceptance_criteria', '测试用例覆盖率达到90%以上'
        ),
        JSON_OBJECT(
            'name', '测试环境搭建',
            'description', '搭建测试环境',
            'type', 'ENVIRONMENT_SETUP',
            'priority', 'MEDIUM',
            'estimated_hours', 8,
            'acceptance_criteria', '测试环境可用，数据准备完成'
        ),
        JSON_OBJECT(
            'name', '功能测试执行',
            'description', '执行功能测试用例',
            'type', 'TEST_EXECUTION',
            'priority', 'HIGH',
            'estimated_hours', 32,
            'acceptance_criteria', '所有测试用例执行完成，缺陷记录完整'
        )
    ),
    JSON_ARRAY(
        JSON_OBJECT(
            'name', '需求评审完成',
            'description', '需求分析和评审完成',
            'type', 'REQUIREMENT',
            'deliverables', JSON_ARRAY('需求文档', '测试计划')
        ),
        JSON_OBJECT(
            'name', '测试设计完成',
            'description', '测试用例设计完成',
            'type', 'DESIGN',
            'deliverables', JSON_ARRAY('测试用例', '测试数据')
        ),
        JSON_OBJECT(
            'name', '测试执行完成',
            'description', '功能测试执行完成',
            'type', 'EXECUTION',
            'deliverables', JSON_ARRAY('测试报告', '缺陷报告')
        ),
        JSON_OBJECT(
            'name', '项目交付',
            'description', '项目测试交付',
            'type', 'DELIVERY',
            'deliverables', JSON_ARRAY('最终测试报告', '质量评估报告', '项目总结')
        )
    ),
    1
),
(
    'API自动化测试模板',
    'RESTful API自动化测试模板，包含接口测试、数据验证和性能监控',
    'AUTOMATION',
    'API_TESTING',
    TRUE,
    TRUE,
    JSON_OBJECT(
        'project_settings', JSON_OBJECT(
            'priority', 'HIGH',
            'risk_level', 'MEDIUM',
            'custom_fields', JSON_OBJECT(
                'api_version', 'v1',
                'test_framework', 'pytest',
                'automation_tool', 'requests'
            )
        ),
        'workflow_settings', JSON_OBJECT(
            'approval_required', TRUE,
            'auto_assign', TRUE,
            'notification_enabled', TRUE
        )
    ),
    JSON_ARRAY(
        JSON_OBJECT(
            'name', 'API接口分析',
            'description', '分析API接口文档和规范',
            'type', 'REQUIREMENT_ANALYSIS',
            'priority', 'HIGH',
            'estimated_hours', 12,
            'acceptance_criteria', 'API接口文档分析完成，测试范围确定'
        ),
        JSON_OBJECT(
            'name', '自动化框架搭建',
            'description', '搭建API自动化测试框架',
            'type', 'AUTOMATION_DEVELOPMENT',
            'priority', 'HIGH',
            'estimated_hours', 24,
            'acceptance_criteria', '自动化框架搭建完成，基础用例可执行'
        ),
        JSON_OBJECT(
            'name', '测试用例开发',
            'description', '开发API自动化测试用例',
            'type', 'AUTOMATION_DEVELOPMENT',
            'priority', 'HIGH',
            'estimated_hours', 40,
            'acceptance_criteria', '自动化测试用例开发完成，覆盖率达到85%'
        )
    ),
    JSON_ARRAY(
        JSON_OBJECT(
            'name', 'API分析完成',
            'description', 'API接口分析和框架设计完成',
            'type', 'REQUIREMENT',
            'deliverables', JSON_ARRAY('API分析报告', '自动化测试计划')
        ),
        JSON_OBJECT(
            'name', '框架搭建完成',
            'description', '自动化测试框架搭建完成',
            'type', 'DESIGN',
            'deliverables', JSON_ARRAY('测试框架', '基础测试用例')
        ),
        JSON_OBJECT(
            'name', '自动化测试完成',
            'description', 'API自动化测试执行完成',
            'type', 'EXECUTION',
            'deliverables', JSON_ARRAY('自动化测试报告', '性能测试报告')
        )
    ),
    1
);