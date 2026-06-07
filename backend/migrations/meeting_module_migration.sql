-- =====================================================
-- 在线会议模块数据库迁移脚本
-- 版本: 1.0.0
-- 创建时间: 2024-01-01
-- 描述: 创建在线会议模块相关的所有数据表
-- =====================================================

-- 设置字符集和存储引擎
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 会议主表 (meetings)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meetings` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '会议ID',
    `meeting_code` VARCHAR(50) NOT NULL COMMENT '会议编码',
    `title` VARCHAR(200) NOT NULL COMMENT '会议标题',
    `description` TEXT COMMENT '会议描述',
    `meeting_type` ENUM(
        'PROJECT_KICKOFF', 'REQUIREMENT_REVIEW', 'DESIGN_REVIEW', 
        'CODE_REVIEW', 'TEST_REVIEW', 'PROGRESS_SYNC', 
        'PROBLEM_SOLVING', 'PROJECT_SUMMARY', 'TRAINING', 'OTHER'
    ) NOT NULL COMMENT '会议类型',
    `status` ENUM(
        'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'POSTPONED'
    ) NOT NULL DEFAULT 'SCHEDULED' COMMENT '会议状态',
    
    -- 时间管理
    `scheduled_start_time` TIMESTAMP NOT NULL COMMENT '计划开始时间',
    `scheduled_end_time` TIMESTAMP NOT NULL COMMENT '计划结束时间',
    `actual_start_time` TIMESTAMP NULL COMMENT '实际开始时间',
    `actual_end_time` TIMESTAMP NULL COMMENT '实际结束时间',
    `timezone` VARCHAR(50) DEFAULT 'UTC' COMMENT '时区',
    
    -- 会议配置
    `max_participants` INT DEFAULT 100 COMMENT '最大参与人数',
    `is_recording_enabled` TINYINT(1) DEFAULT 0 COMMENT '是否启用录制',
    `is_waiting_room_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用等候室',
    `is_password_protected` TINYINT(1) DEFAULT 0 COMMENT '是否密码保护',
    `meeting_password` VARCHAR(100) COMMENT '会议密码',
    
    -- 关联信息
    `project_id` BIGINT COMMENT '关联项目ID',
    `organizer_id` BIGINT NOT NULL COMMENT '组织者ID',
    
    -- 会议设置 (JSON格式存储)
    `agenda` JSON COMMENT '会议议程',
    `meeting_settings` JSON COMMENT '会议设置',
    
    -- 统计信息
    `participant_count` INT DEFAULT 0 COMMENT '参与人数',
    `duration_minutes` INT DEFAULT 0 COMMENT '会议时长(分钟)',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    `deleted_at` TIMESTAMP NULL COMMENT '删除时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_meeting_code` (`meeting_code`),
    KEY `idx_meeting_type` (`meeting_type`),
    KEY `idx_status` (`status`),
    KEY `idx_project_id` (`project_id`),
    KEY `idx_organizer_id` (`organizer_id`),
    KEY `idx_scheduled_time` (`scheduled_start_time`, `scheduled_end_time`),
    KEY `idx_deleted_at` (`deleted_at`),
    
    CONSTRAINT `fk_meetings_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_meetings_organizer` FOREIGN KEY (`organizer_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议表';

-- =====================================================
-- 2. 会议参与者表 (meeting_participants)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_participants` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '参与记录ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `participant_role` ENUM(
        'ORGANIZER', 'MODERATOR', 'PRESENTER', 'PARTICIPANT', 'OBSERVER'
    ) NOT NULL DEFAULT 'PARTICIPANT' COMMENT '参与角色',
    `invitation_status` ENUM(
        'PENDING', 'ACCEPTED', 'DECLINED', 'TENTATIVE'
    ) NOT NULL DEFAULT 'PENDING' COMMENT '邀请状态',
    `attendance_status` ENUM(
        'NOT_JOINED', 'JOINED', 'LEFT', 'KICKED_OUT'
    ) NOT NULL DEFAULT 'NOT_JOINED' COMMENT '出席状态',
    
    -- 权限设置
    `can_share_screen` TINYINT(1) DEFAULT 1 COMMENT '是否可以共享屏幕',
    `can_use_chat` TINYINT(1) DEFAULT 1 COMMENT '是否可以使用聊天',
    `can_use_whiteboard` TINYINT(1) DEFAULT 1 COMMENT '是否可以使用白板',
    `can_record` TINYINT(1) DEFAULT 0 COMMENT '是否可以录制',
    
    -- 参与统计
    `join_time` TIMESTAMP NULL COMMENT '加入时间',
    `leave_time` TIMESTAMP NULL COMMENT '离开时间',
    `total_duration_minutes` INT DEFAULT 0 COMMENT '总参与时长(分钟)',
    `speak_duration_minutes` INT DEFAULT 0 COMMENT '发言时长(分钟)',
    `interaction_count` INT DEFAULT 0 COMMENT '互动次数',
    
    -- 设备信息 (JSON格式存储)
    `device_info` JSON COMMENT '设备信息',
    `network_quality` JSON COMMENT '网络质量信息',
    
    -- 审计字段
    `invited_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '邀请时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_meeting_participant` (`meeting_id`, `user_id`),
    KEY `idx_meeting_id` (`meeting_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_participant_role` (`participant_role`),
    KEY `idx_invitation_status` (`invitation_status`),
    KEY `idx_attendance_status` (`attendance_status`),
    
    CONSTRAINT `fk_meeting_participants_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_participants_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议参与者表';

-- =====================================================
-- 3. 会议录制表 (meeting_recordings)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_recordings` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '录制ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    `recording_name` VARCHAR(200) NOT NULL COMMENT '录制名称',
    `recording_type` ENUM(
        'FULL_MEETING', 'SCREEN_SHARE', 'AUDIO_ONLY', 'HIGHLIGHTS'
    ) NOT NULL DEFAULT 'FULL_MEETING' COMMENT '录制类型',
    `file_format` ENUM('MP4', 'WEBM', 'MP3', 'M4A') NOT NULL DEFAULT 'MP4' COMMENT '文件格式',
    
    -- 文件信息
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
    `file_size` BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    `duration_seconds` INT DEFAULT 0 COMMENT '录制时长(秒)',
    `resolution` VARCHAR(20) COMMENT '视频分辨率',
    
    -- 录制状态
    `recording_status` ENUM(
        'RECORDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'DELETED'
    ) NOT NULL DEFAULT 'RECORDING' COMMENT '录制状态',
    `processing_progress` INT DEFAULT 0 COMMENT '处理进度(百分比)',
    
    -- 时间信息
    `start_time` TIMESTAMP NOT NULL COMMENT '录制开始时间',
    `end_time` TIMESTAMP NULL COMMENT '录制结束时间',
    
    -- 访问控制
    `is_public` TINYINT(1) DEFAULT 0 COMMENT '是否公开',
    `access_password` VARCHAR(100) COMMENT '访问密码',
    `download_count` INT DEFAULT 0 COMMENT '下载次数',
    `view_count` INT DEFAULT 0 COMMENT '观看次数',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT NOT NULL COMMENT '创建者ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    KEY `idx_meeting_id` (`meeting_id`),
    KEY `idx_recording_type` (`recording_type`),
    KEY `idx_recording_status` (`recording_status`),
    KEY `idx_created_by` (`created_by`),
    KEY `idx_start_time` (`start_time`),
    
    CONSTRAINT `fk_meeting_recordings_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_recordings_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议录制表';

-- =====================================================
-- 4. 会议纪要表 (meeting_minutes)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_minutes` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '纪要ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    `title` VARCHAR(200) NOT NULL COMMENT '纪要标题',
    `content` TEXT COMMENT '纪要内容',
    `summary` TEXT COMMENT '会议摘要',
    
    -- 纪要类型
    `minute_type` ENUM(
        'AUTO_GENERATED', 'MANUAL_CREATED', 'AI_ENHANCED', 'COLLABORATIVE'
    ) NOT NULL DEFAULT 'MANUAL_CREATED' COMMENT '纪要类型',
    `generation_method` ENUM(
        'SPEECH_TO_TEXT', 'MANUAL_INPUT', 'AI_ANALYSIS', 'TEMPLATE_BASED'
    ) COMMENT '生成方式',
    
    -- 结构化内容 (JSON格式存储)
    `agenda_items` JSON COMMENT '议程项目',
    `decisions` JSON COMMENT '决策事项',
    `action_items` JSON COMMENT '行动项目',
    `attendees` JSON COMMENT '参会人员',
    `key_points` JSON COMMENT '关键要点',
    
    -- 状态管理
    `status` ENUM(
        'DRAFT', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED'
    ) NOT NULL DEFAULT 'DRAFT' COMMENT '纪要状态',
    `approval_required` TINYINT(1) DEFAULT 0 COMMENT '是否需要审批',
    
    -- 版本管理
    `version` VARCHAR(20) DEFAULT '1.0' COMMENT '版本号',
    `parent_minute_id` BIGINT COMMENT '父纪要ID',
    
    -- 审批信息
    `approved_by` BIGINT COMMENT '审批者ID',
    `approved_at` TIMESTAMP NULL COMMENT '审批时间',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT NOT NULL COMMENT '创建者ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    KEY `idx_meeting_id` (`meeting_id`),
    KEY `idx_minute_type` (`minute_type`),
    KEY `idx_status` (`status`),
    KEY `idx_created_by` (`created_by`),
    KEY `idx_created_at` (`created_at`),
    
    CONSTRAINT `fk_meeting_minutes_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_minutes_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_meeting_minutes_approver` FOREIGN KEY (`approved_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_meeting_minutes_parent` FOREIGN KEY (`parent_minute_id`) REFERENCES `meeting_minutes`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议纪要表';

-- =====================================================
-- 5. 会议聊天消息表 (meeting_chats)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_chats` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '消息ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    `sender_id` BIGINT NOT NULL COMMENT '发送者ID',
    
    -- 消息内容
    `message_type` ENUM('TEXT', 'IMAGE', 'FILE', 'SYSTEM', 'EMOJI') NOT NULL DEFAULT 'TEXT' COMMENT '消息类型',
    `content` TEXT NOT NULL COMMENT '消息内容',
    
    -- 消息属性
    `is_private` TINYINT(1) DEFAULT 0 COMMENT '是否私聊',
    `recipient_id` BIGINT COMMENT '接收者ID(私聊时使用)',
    
    -- 附加信息 (JSON格式存储)
    `metadata` JSON COMMENT '消息元数据',
    
    -- 时间戳
    `sent_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    KEY `idx_meeting_id` (`meeting_id`),
    KEY `idx_sender_id` (`sender_id`),
    KEY `idx_recipient_id` (`recipient_id`),
    KEY `idx_sent_at` (`sent_at`),
    
    CONSTRAINT `fk_meeting_chats_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_chats_sender` FOREIGN KEY (`sender_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_chats_recipient` FOREIGN KEY (`recipient_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议聊天消息表';

-- =====================================================
-- 6. 会议文件共享表 (meeting_files)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_files` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '文件ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    `uploader_id` BIGINT NOT NULL COMMENT '上传者ID',
    
    -- 文件信息
    `file_name` VARCHAR(255) NOT NULL COMMENT '文件名',
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
    `file_size` BIGINT NOT NULL COMMENT '文件大小(字节)',
    `file_type` VARCHAR(100) NOT NULL COMMENT '文件类型',
    `mime_type` VARCHAR(100) COMMENT 'MIME类型',
    
    -- 状态信息
    `status` ENUM(
        'UPLOADING', 'AVAILABLE', 'PROCESSING', 'FAILED', 'DELETED'
    ) NOT NULL DEFAULT 'UPLOADING' COMMENT '文件状态',
    
    -- 访问控制
    `is_public` TINYINT(1) DEFAULT 1 COMMENT '是否公开',
    `download_count` INT DEFAULT 0 COMMENT '下载次数',
    
    -- 文件描述
    `description` TEXT COMMENT '文件描述',
    
    -- 附加信息 (JSON格式存储)
    `metadata` JSON COMMENT '文件元数据',
    
    -- 上传时间
    `uploaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    KEY `idx_meeting_id` (`meeting_id`),
    KEY `idx_uploader_id` (`uploader_id`),
    KEY `idx_status` (`status`),
    KEY `idx_uploaded_at` (`uploaded_at`),
    
    CONSTRAINT `fk_meeting_files_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_meeting_files_uploader` FOREIGN KEY (`uploader_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议文件共享表';

-- =====================================================
-- 7. 会议分析数据表 (meeting_analytics)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_analytics` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '分析记录ID',
    `meeting_id` BIGINT NOT NULL COMMENT '会议ID',
    
    -- 参与度分析
    `total_participants` INT DEFAULT 0 COMMENT '总参与人数',
    `peak_participants` INT DEFAULT 0 COMMENT '峰值参与人数',
    `avg_participation_rate` DECIMAL(5,2) COMMENT '平均参与率',
    
    -- 发言分析
    `total_speaking_time` INT DEFAULT 0 COMMENT '总发言时长(秒)',
    `avg_speaking_time_per_person` INT DEFAULT 0 COMMENT '人均发言时长(秒)',
    `speaking_balance_score` DECIMAL(5,2) COMMENT '发言均衡度评分',
    
    -- 互动分析
    `total_chat_messages` INT DEFAULT 0 COMMENT '聊天消息总数',
    `total_file_shares` INT DEFAULT 0 COMMENT '文件分享总数',
    `screen_share_duration` INT DEFAULT 0 COMMENT '屏幕共享时长(秒)',
    
    -- 质量分析
    `audio_quality_score` DECIMAL(5,2) COMMENT '音频质量评分',
    `video_quality_score` DECIMAL(5,2) COMMENT '视频质量评分',
    `network_stability_score` DECIMAL(5,2) COMMENT '网络稳定性评分',
    
    -- 效率分析
    `agenda_completion_rate` DECIMAL(5,2) COMMENT '议程完成率',
    `decision_count` INT DEFAULT 0 COMMENT '决策数量',
    `action_item_count` INT DEFAULT 0 COMMENT '行动项数量',
    
    -- 情感分析
    `overall_sentiment_score` DECIMAL(5,2) COMMENT '整体情感评分',
    `engagement_score` DECIMAL(5,2) COMMENT '参与度评分',
    
    -- 详细分析数据 (JSON格式存储)
    `detailed_analytics` JSON COMMENT '详细分析数据',
    
    -- 分析时间
    `analyzed_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT COMMENT '创建人ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_meeting_analytics` (`meeting_id`),
    KEY `idx_analyzed_at` (`analyzed_at`),
    
    CONSTRAINT `fk_meeting_analytics_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `meetings`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议分析数据表';

-- =====================================================
-- 8. 会议模板表 (meeting_templates)
-- =====================================================
CREATE TABLE IF NOT EXISTS `meeting_templates` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '模板ID',
    `template_name` VARCHAR(200) NOT NULL COMMENT '模板名称',
    `description` TEXT COMMENT '模板描述',
    `category` ENUM(
        'PROJECT_MANAGEMENT', 'REQUIREMENT_REVIEW', 'DESIGN_REVIEW', 
        'TECHNICAL_DISCUSSION', 'TRAINING', 'GENERAL'
    ) NOT NULL COMMENT '模板分类',
    
    -- 模板配置
    `meeting_type` ENUM(
        'PROJECT_KICKOFF', 'REQUIREMENT_REVIEW', 'DESIGN_REVIEW', 
        'CODE_REVIEW', 'TEST_REVIEW', 'PROGRESS_SYNC', 
        'PROBLEM_SOLVING', 'PROJECT_SUMMARY', 'TRAINING', 'OTHER'
    ) NOT NULL COMMENT '会议类型',
    `default_duration_minutes` INT DEFAULT 60 COMMENT '默认时长(分钟)',
    `max_participants` INT DEFAULT 100 COMMENT '最大参与人数',
    
    -- 模板内容 (JSON格式存储)
    `agenda_template` JSON COMMENT '议程模板',
    `settings_template` JSON COMMENT '设置模板',
    `roles_template` JSON COMMENT '角色模板',
    
    -- 状态管理
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `is_public` TINYINT(1) DEFAULT 0 COMMENT '是否公开',
    
    -- 使用统计
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    
    -- 审计字段
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `created_by` BIGINT NOT NULL COMMENT '创建者ID',
    `updated_by` BIGINT COMMENT '更新人ID',
    
    PRIMARY KEY (`id`),
    KEY `idx_category` (`category`),
    KEY `idx_meeting_type` (`meeting_type`),
    KEY `idx_is_active` (`is_active`),
    KEY `idx_is_public` (`is_public`),
    KEY `idx_created_by` (`created_by`),
    
    CONSTRAINT `fk_meeting_templates_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议模板表';

-- =====================================================
-- 恢复外键检查
-- =====================================================
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 创建视图
-- =====================================================

-- 创建会议统计视图
CREATE OR REPLACE VIEW `v_meeting_statistics` AS
SELECT 
    m.id,
    m.meeting_code,
    m.title,
    m.meeting_type,
    m.status,
    m.scheduled_start_time,
    m.scheduled_end_time,
    m.actual_start_time,
    m.actual_end_time,
    m.duration_minutes,
    m.participant_count,
    COUNT(mp.id) as invited_participants,
    COUNT(CASE WHEN mp.attendance_status = 'JOINED' THEN 1 END) as actual_participants,
    COUNT(mr.id) as recording_count,
    COUNT(mm.id) as minutes_count,
    COUNT(mc.id) as chat_message_count,
    COUNT(mf.id) as shared_file_count
FROM meetings m
LEFT JOIN meeting_participants mp ON m.id = mp.meeting_id
LEFT JOIN meeting_recordings mr ON m.id = mr.meeting_id
LEFT JOIN meeting_minutes mm ON m.id = mm.meeting_id
LEFT JOIN meeting_chats mc ON m.id = mc.meeting_id
LEFT JOIN meeting_files mf ON m.id = mf.meeting_id
WHERE m.deleted_at IS NULL
GROUP BY m.id;

-- =====================================================
-- 插入初始数据
-- =====================================================

-- 插入默认会议模板
INSERT IGNORE INTO `meeting_templates` (
    `template_name`, `description`, `category`, `meeting_type`, 
    `default_duration_minutes`, `max_participants`, `is_active`, `is_public`,
    `agenda_template`, `settings_template`, `roles_template`, `created_by`
) VALUES 
(
    '项目启动会模板', 
    '用于项目启动阶段的标准会议模板，包含项目介绍、角色分工、计划讲解等议程',
    'PROJECT_MANAGEMENT', 
    'PROJECT_KICKOFF', 
    120, 
    50, 
    1, 
    1,
    JSON_OBJECT(
        'items', JSON_ARRAY(
            JSON_OBJECT('title', '项目背景介绍', 'duration', 20, 'presenter', '项目经理'),
            JSON_OBJECT('title', '团队成员介绍', 'duration', 15, 'presenter', '全体成员'),
            JSON_OBJECT('title', '项目目标和范围', 'duration', 30, 'presenter', '项目经理'),
            JSON_OBJECT('title', '角色分工和职责', 'duration', 25, 'presenter', '项目经理'),
            JSON_OBJECT('title', '项目计划和里程碑', 'duration', 20, 'presenter', '项目经理'),
            JSON_OBJECT('title', '问题讨论和答疑', 'duration', 10, 'presenter', '全体成员')
        )
    ),
    JSON_OBJECT(
        'recording_enabled', true,
        'waiting_room_enabled', true,
        'chat_enabled', true,
        'screen_share_enabled', true
    ),
    JSON_OBJECT(
        'required_roles', JSON_ARRAY('项目经理', '技术负责人', '测试负责人'),
        'optional_roles', JSON_ARRAY('产品经理', '设计师', '开发人员')
    ),
    1
);

-- =====================================================
-- 创建迁移历史记录表
-- =====================================================
CREATE TABLE IF NOT EXISTS `migration_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `migration_name` VARCHAR(255) NOT NULL,
    `executed_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `version` VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO `migration_history` (`migration_name`, `version`) 
VALUES ('meeting_module_migration', '1.0.0');

-- =====================================================
-- 验证表创建
-- =====================================================
SELECT 'Meeting module migration completed successfully!' as result;
SHOW TABLES LIKE 'meeting%';