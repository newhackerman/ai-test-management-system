"""
用户导入模板生成器
根据当前users表结构生成Excel导入模板
"""
import pandas as pd
from datetime import datetime
import os

def create_user_import_template():
    """创建用户导入Excel模板"""
    
    # 根据users表结构定义列
    columns = {
        # 必填字段
        'username': '用户名*',
        'email': '邮箱*', 
        'password': '密码*',
        
        # 可选个人信息字段
        'nickname': '昵称',
        'avatar': '头像URL',
        'phone': '手机号',
        'bio': '个人简介',
        'gender': '性别',  # MALE, FEMALE, OTHER, UNKNOWN
        'birthday': '生日',  # YYYY-MM-DD格式
        'location': '所在地',
        'website': '个人网站',
        
        # 布尔类型字段
        'is_email_verified': '邮箱已验证',  # TRUE/FALSE
        'is_phone_verified': '手机已验证',  # TRUE/FALSE
        'mfa_enabled': '启用多因素认证',  # TRUE/FALSE
        'is_active': '用户激活',  # TRUE/FALSE
        'is_superuser': '超级用户',  # TRUE/FALSE
        
        # 状态和偏好设置
        'status': '用户状态',  # ACTIVE, INACTIVE, DISABLED, LOCKED, PENDING, DELETED
        'language': '语言设置',
        'timezone': '时区',
        'theme': '主题',
        'email_notifications': '邮件通知',  # TRUE/FALSE
        'sms_notifications': '短信通知',  # TRUE/FALSE
        'push_notifications': '推送通知'  # TRUE/FALSE
    }
    
    # 创建示例数据
    sample_data = [
        {
            'username': 'user001',
            'email': 'user001@example.com',
            'password': 'Password123!',
            'nickname': '示例用户1',
            'phone': '13800138000',
            'bio': '这是一个示例用户',
            'gender': 'MALE',
            'birthday': '1990-01-01',
            'location': '北京市',
            'website': 'https://example.com',
            'is_email_verified': 'FALSE',
            'is_phone_verified': 'FALSE',
            'mfa_enabled': 'FALSE',
            'is_active': 'TRUE',
            'is_superuser': 'FALSE',
            'status': 'ACTIVE',
            'language': 'zh-CN',
            'timezone': 'Asia/Shanghai',
            'theme': 'light',
            'email_notifications': 'TRUE',
            'sms_notifications': 'FALSE',
            'push_notifications': 'TRUE'
        },
        {
            'username': 'admin001',
            'email': 'admin@example.com',
            'password': 'AdminPass123!',
            'nickname': '管理员',
            'phone': '13800138001',
            'bio': '系统管理员账户',
            'gender': 'FEMALE',
            'birthday': '1985-05-15',
            'location': '上海市',
            'website': '',
            'is_email_verified': 'TRUE',
            'is_phone_verified': 'TRUE',
            'mfa_enabled': 'TRUE',
            'is_active': 'TRUE',
            'is_superuser': 'TRUE',
            'status': 'ACTIVE',
            'language': 'zh-CN',
            'timezone': 'Asia/Shanghai',
            'theme': 'dark',
            'email_notifications': 'TRUE',
            'sms_notifications': 'TRUE',
            'push_notifications': 'TRUE'
        }
    ]
    
    # 创建DataFrame
    df = pd.DataFrame(sample_data)
    
    # 重命名列为中文
    df.rename(columns=columns, inplace=True)
    
    # 确保目录存在
    os.makedirs('templates', exist_ok=True)
    
    # 导出Excel模板
    template_file = 'templates/用户导入模板.xlsx'
    
    with pd.ExcelWriter(template_file, engine='openpyxl') as writer:
        # 写入数据工作表
        df.to_excel(writer, sheet_name='用户数据', index=False)
        
        # 创建说明工作表
        instructions = pd.DataFrame({
            '字段名': list(columns.values()),
            '字段说明': [
                '用户名，必填，3-50个字符，仅支持字母、数字、下划线',
                '邮箱地址，必填，需符合邮箱格式，系统内唯一',
                '登录密码，必填，至少8个字符，包含字母和数字',
                '用户昵称，可选，最多50个字符',
                '头像图片URL，可选，需以http://或https://开头',
                '手机号码，可选，11位数字，建议格式：138********',
                '个人简介，可选，最多500个字符',
                '性别，可选，枚举值：MALE（男）、FEMALE（女）、OTHER（其他）、UNKNOWN（未知）',
                '生日，可选，格式：YYYY-MM-DD，例如：1990-01-01',
                '所在地，可选，最多100个字符',
                '个人网站，可选，需以http://或https://开头',
                '邮箱验证状态，可选，TRUE（已验证）或FALSE（未验证）',
                '手机验证状态，可选，TRUE（已验证）或FALSE（未验证）',
                '多因素认证，可选，TRUE（启用）或FALSE（禁用）',
                '用户激活状态，可选，TRUE（激活）或FALSE（禁用）',
                '超级用户权限，可选，TRUE（是）或FALSE（否）',
                '用户状态，可选，枚举值：ACTIVE（活跃）、INACTIVE（非活跃）、DISABLED（禁用）、LOCKED（锁定）、PENDING（待激活）、DELETED（已删除）',
                '界面语言，可选，建议值：zh-CN（中文）、en-US（英文）',
                '时区设置，可选，建议值：Asia/Shanghai（北京时间）',
                '界面主题，可选，light（浅色）或dark（深色）',
                '邮件通知，可选，TRUE（开启）或FALSE（关闭）',
                '短信通知，可选，TRUE（开启）或FALSE（关闭）',
                '推送通知，可选，TRUE（开启）或FALSE（关闭）'
            ],
            '是否必填': [
                '是', '是', '是',
                '否', '否', '否', '否', '否', '否', '否', '否',
                '否', '否', '否', '否', '否', '否', '否', '否', '否', '否', '否', '否'
            ],
            '默认值': [
                '', '', '',
                '', '', '', '', 'UNKNOWN', '', '', '',
                'FALSE', 'FALSE', 'FALSE', 'TRUE', 'FALSE',
                'ACTIVE', 'zh-CN', 'Asia/Shanghai', 'light',
                'TRUE', 'FALSE', 'TRUE'
            ]
        })
        
        instructions.to_excel(writer, sheet_name='字段说明', index=False)
    
    return template_file

def create_csv_template():
    """创建CSV格式的导入模板"""
    # 基本字段（简化版）
    csv_data = {
        'username': ['user001', 'admin001'],
        'email': ['user001@example.com', 'admin@example.com'],
        'password': ['Password123!', 'AdminPass123!'],
        'nickname': ['示例用户1', '管理员'],
        'phone': ['13800138000', '13800138001'],
        'bio': ['这是一个示例用户', '系统管理员账户'],
        'gender': ['MALE', 'FEMALE'],
        'birthday': ['1990-01-01', '1985-05-15'],
        'location': ['北京市', '上海市'],
        'website': ['https://example.com', ''],
        'is_email_verified': ['FALSE', 'TRUE'],
        'is_phone_verified': ['FALSE', 'TRUE'],
        'mfa_enabled': ['FALSE', 'TRUE'],
        'is_active': ['TRUE', 'TRUE'],
        'is_superuser': ['FALSE', 'TRUE'],
        'status': ['ACTIVE', 'ACTIVE'],
        'language': ['zh-CN', 'zh-CN'],
        'timezone': ['Asia/Shanghai', 'Asia/Shanghai'],
        'theme': ['light', 'dark'],
        'email_notifications': ['TRUE', 'TRUE'],
        'sms_notifications': ['FALSE', 'TRUE'],
        'push_notifications': ['TRUE', 'TRUE']
    }
    
    df = pd.DataFrame(csv_data)
    
    # 确保目录存在
    os.makedirs('templates', exist_ok=True)
    
    # 导出CSV模板
    template_file = 'templates/用户导入模板.csv'
    df.to_csv(template_file, index=False, encoding='utf-8-sig')
    
    return template_file

if __name__ == "__main__":
    print("正在生成用户导入模板...")
    
    # 生成Excel模板
    excel_file = create_user_import_template()
    print(f"Excel模板已生成：{excel_file}")
    
    # 生成CSV模板
    csv_file = create_csv_template()
    print(f"CSV模板已生成：{csv_file}")
    
    print("\n模板生成完成！")
    print("\n使用说明：")
    print("1. Excel模板包含示例数据和详细字段说明")
    print("2. CSV模板适合简单批量导入")
    print("3. 必填字段：username（用户名）、email（邮箱）、password（密码）")
    print("4. 导入前请检查数据格式是否正确")