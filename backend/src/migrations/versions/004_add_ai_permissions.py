"""
添加AI助手权限

Revision ID: 004_add_ai_permissions
Revises: 003_create_config_tables
Create Date: 2024-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '004_add_ai_permissions'
down_revision = '003_create_config_tables'
branch_labels = None
depends_on = None


def upgrade():
    """添加AI助手相关权限"""
    
    # AI助手权限定义
    ai_permissions = [
        # 基础权限
        {
            'code': 'ai_chat_basic',
            'name': 'AI基础对话',
            'description': '允许用户进行基础AI对话',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_chat',
            'action': 'basic_chat'
        },
        {
            'code': 'ai_chat_advanced',
            'name': 'AI高级对话',
            'description': '允许用户使用高级AI功能和模型',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_chat',
            'action': 'advanced_chat'
        },
        
        # 会话管理权限
        {
            'code': 'ai_session_create',
            'name': '创建AI会话',
            'description': '允许用户创建新的AI对话会话',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_session',
            'action': 'create'
        },
        {
            'code': 'ai_session_read',
            'name': '查看AI会话',
            'description': '允许用户查看AI对话会话',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_session',
            'action': 'read'
        },
        {
            'code': 'ai_session_update',
            'name': '编辑AI会话',
            'description': '允许用户编辑AI对话会话',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_session',
            'action': 'update'
        },
        {
            'code': 'ai_session_delete',
            'name': '删除AI会话',
            'description': '允许用户删除AI对话会话',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_session',
            'action': 'delete'
        },
        
        # 模型使用权限
        {
            'code': 'ai_model_gpt4',
            'name': '使用GPT-4模型',
            'description': '允许用户使用GPT-4系列模型',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_model',
            'action': 'use_gpt4'
        },
        {
            'code': 'ai_model_claude',
            'name': '使用Claude模型',
            'description': '允许用户使用Claude系列模型',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_model',
            'action': 'use_claude'
        },
        {
            'code': 'ai_model_chinese',
            'name': '使用中文AI模型',
            'description': '允许用户使用文心一言、通义千问等中文模型',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_model',
            'action': 'use_chinese'
        },
        
        # 提示词模板权限
        {
            'code': 'ai_template_read',
            'name': '查看提示词模板',
            'description': '允许用户查看提示词模板',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_template',
            'action': 'read'
        },
        {
            'code': 'ai_template_create',
            'name': '创建提示词模板',
            'description': '允许用户创建提示词模板',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_template',
            'action': 'create'
        },
        {
            'code': 'ai_template_update',
            'name': '编辑提示词模板',
            'description': '允许用户编辑提示词模板',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_template',
            'action': 'update'
        },
        {
            'code': 'ai_template_delete',
            'name': '删除提示词模板',
            'description': '允许用户删除提示词模板',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_template',
            'action': 'delete'
        },
        {
            'code': 'ai_template_share',
            'name': '分享提示词模板',
            'description': '允许用户分享提示词模板',
            'module': 'ai_assistant',
            'type': 'OPERATION',
            'resource': 'ai_template',
            'action': 'share'
        },
        
        # 管理权限
        {
            'code': 'ai_admin_config',
            'name': 'AI配置管理',
            'description': '允许管理员配置AI服务参数',
            'module': 'ai_assistant',
            'type': 'MODULE',
            'resource': 'ai_config',
            'action': 'manage'
        },
        {
            'code': 'ai_admin_monitor',
            'name': 'AI使用监控',
            'description': '允许管理员监控AI使用情况',
            'module': 'ai_assistant',
            'type': 'MODULE',
            'resource': 'ai_monitor',
            'action': 'view'
        },
        {
            'code': 'ai_admin_quota',
            'name': 'AI配额管理',
            'description': '允许管理员管理用户AI使用配额',
            'module': 'ai_assistant',
            'type': 'MODULE',
            'resource': 'ai_quota',
            'action': 'manage'
        },
        
        # 高级功能权限
        {
            'code': 'ai_suggestion_generate',
            'name': '生成智能建议',
            'description': '允许用户使用AI生成智能建议功能',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_suggestion',
            'action': 'generate'
        },
        {
            'code': 'ai_analysis_advanced',
            'name': '高级分析功能',
            'description': '允许用户使用AI高级分析功能',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_analysis',
            'action': 'advanced'
        },
        {
            'code': 'ai_file_upload',
            'name': 'AI文件上传',
            'description': '允许用户上传文件给AI分析',
            'module': 'ai_assistant',
            'type': 'FUNCTION',
            'resource': 'ai_file',
            'action': 'upload'
        }
    ]
    
    # 获取数据库连接
    connection = op.get_bind()
    
    # 插入AI权限
    for i, perm in enumerate(ai_permissions):
        connection.execute(
            sa.text("""
                INSERT INTO permissions (
                    code, name, description, module, resource, action,
                    created_at
                ) VALUES (
                    :code, :name, :description, :module, :resource, :action,
                    :created_at
                )
            """),
            {
                'code': perm['code'],
                'name': perm['name'],
                'description': perm['description'],
                'module': perm['module'],
                'type': perm['type'],
                'resource': perm['resource'],
                'action': perm['action'],
                'created_at': datetime.utcnow()
            }
        )
    
    # 为超级管理员角色分配所有AI权限
    # 首先获取超级管理员角色ID
    result = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = 'SUPER_ADMIN' LIMIT 1")
    )
    super_admin_role = result.fetchone()
    
    if super_admin_role:
        super_admin_role_id = super_admin_role[0]
        
        # 获取所有AI权限ID
        result = connection.execute(
            sa.text("SELECT id FROM permissions WHERE module = 'ai_assistant'")
        )
        ai_permission_ids = [row[0] for row in result.fetchall()]
        
        # 为超级管理员分配所有AI权限
        for permission_id in ai_permission_ids:
            connection.execute(
                sa.text("""
                    INSERT INTO role_permissions (role_id, permission_id, created_at)
                    VALUES (:role_id, :permission_id, :created_at)
                """),
                {
                    'role_id': super_admin_role_id,
                    'permission_id': permission_id,
                    'created_at': datetime.utcnow()
                }
            )
    
    # 为标准用户角色分配基础AI权限
    result = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = 'user' LIMIT 1")
    )
    user_role = result.fetchone()
    
    if user_role:
        user_role_id = user_role[0]
        
        # 基础用户权限列表
        basic_permissions = [
            'ai_chat_basic',
            'ai_session_create',
            'ai_session_read',
            'ai_session_update',
            'ai_session_delete',
            'ai_model_chinese',  # 默认允许使用中文模型
            'ai_template_read',
            'ai_template_create',
            'ai_template_update',
            'ai_template_delete'
        ]
        
        # 获取基础权限ID
        for perm_code in basic_permissions:
            result = connection.execute(
                sa.text("SELECT id FROM permissions WHERE code = :code LIMIT 1"),
                {'code': perm_code}
            )
            permission = result.fetchone()
            
            if permission:
                permission_id = permission[0]
                connection.execute(
                    sa.text("""
                        INSERT INTO role_permissions (role_id, permission_id, created_at)
                        VALUES (:role_id, :permission_id, :created_at)
                    """),
                    {
                        'role_id': user_role_id,
                        'permission_id': permission_id,
                        'created_at': datetime.utcnow()
                    }
                )
    
    print(f"成功添加 {len(ai_permissions)} 个AI助手权限")


def downgrade():
    """移除AI助手相关权限"""
    
    # 获取数据库连接
    connection = op.get_bind()
    
    # 删除AI权限相关的角色权限关联
    connection.execute(
        sa.text("""
            DELETE rp FROM role_permissions rp
            INNER JOIN permissions p ON rp.permission_id = p.id
            WHERE p.module = 'ai_assistant'
        """)
    )
    
    # 删除AI权限
    connection.execute(
        sa.text("DELETE FROM permissions WHERE module = 'ai_assistant'")
    )
    
    print("成功移除AI助手权限")