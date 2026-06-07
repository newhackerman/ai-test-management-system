"""
高级权限数据库模型扩展
支持临时权限、定时权限、行级权限、列级权限等
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, BigInteger, Enum as SQLEnum, Time, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import enum
from datetime import datetime, time, date
from .base import BaseModel


class PermissionLevel(enum.Enum):
    """权限级别枚举"""
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"
    OWNER = "OWNER"


class PermissionScope(enum.Enum):
    """权限范围枚举"""
    GLOBAL = "GLOBAL"
    GROUP = "GROUP"
    CONFIG = "CONFIG"
    ENVIRONMENT = "ENVIRONMENT"
    TAG = "TAG"


class TimeBasedPermissionType(enum.Enum):
    """时间权限类型枚举"""
    ALWAYS = "ALWAYS"
    SCHEDULE = "SCHEDULE"
    TEMPORARY = "TEMPORARY"
    APPROVAL = "APPROVAL"


class AdvancedPermissionRule(BaseModel):
    """高级权限规则表"""
    __tablename__ = 'sys_advanced_permission_rule'
    
    rule_name = Column(String(100), nullable=False, comment='规则名称')
    rule_code = Column(String(50), nullable=False, unique=True, comment='规则代码')
    description = Column(Text, comment='规则描述')
    
    # 权限范围和级别
    scope = Column(SQLEnum(PermissionScope), nullable=False, comment='权限范围')
    level = Column(SQLEnum(PermissionLevel), nullable=False, comment='权限级别')
    
    # 权限条件
    conditions = Column(JSON, comment='权限条件配置')
    
    # 行级权限配置
    row_filters = Column(JSON, comment='行级过滤条件')
    
    # 列级权限配置
    column_filters = Column(JSON, comment='列级过滤配置')
    
    # 时间权限配置
    time_restrictions = Column(JSON, comment='时间限制配置')
    
    # 自定义逻辑
    custom_logic = Column(Text, comment='自定义权限逻辑代码')
    
    # 规则状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    priority = Column(Integer, default=0, comment='优先级')
    
    def __repr__(self):
        return f"<AdvancedPermissionRule(name={self.rule_name}, scope={self.scope}, level={self.level})>"


class TemporaryPermission(BaseModel):
    """临时权限表"""
    __tablename__ = 'sys_temporary_permission'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False, comment='权限级别')
    
    # 权限范围
    scope_type = Column(SQLEnum(PermissionScope), nullable=False, comment='权限范围类型')
    scope_config = Column(JSON, comment='权限范围配置')
    
    # 时间配置
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, nullable=False, comment='结束时间')
    
    # 授权信息
    granted_by = Column(BigInteger, nullable=False, comment='授权人ID')
    grant_reason = Column(Text, comment='授权原因')
    approval_id = Column(String(50), comment='审批单号')
    
    # 使用记录
    used_count = Column(Integer, default=0, comment='使用次数')
    last_used_at = Column(DateTime, comment='最后使用时间')
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    is_revoked = Column(Boolean, default=False, nullable=False, comment='是否已撤销')
    revoked_by = Column(BigInteger, comment='撤销人ID')
    revoked_at = Column(DateTime, comment='撤销时间')
    revoked_reason = Column(Text, comment='撤销原因')
    
    def __repr__(self):
        return f"<TemporaryPermission(user_id={self.user_id}, level={self.permission_level}, active={self.is_active})>"
    
    @property
    def is_expired(self):
        """是否已过期"""
        return datetime.utcnow() > self.end_time
    
    @property
    def is_valid(self):
        """是否有效"""
        now = datetime.utcnow()
        return (
            self.is_active and 
            not self.is_revoked and 
            self.start_time <= now <= self.end_time
        )


class ScheduledPermission(BaseModel):
    """定时权限表"""
    __tablename__ = 'sys_scheduled_permission'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False, comment='权限级别')
    
    # 权限范围
    scope_type = Column(SQLEnum(PermissionScope), nullable=False, comment='权限范围类型')
    scope_config = Column(JSON, comment='权限范围配置')
    
    # 时间计划配置
    schedule_name = Column(String(100), nullable=False, comment='计划名称')
    schedule_config = Column(JSON, nullable=False, comment='时间计划配置')
    
    # 有效期
    valid_from = Column(Date, comment='生效日期')
    valid_until = Column(Date, comment='失效日期')
    
    # 时间规则
    work_days = Column(JSON, comment='工作日配置 [1,2,3,4,5] 表示周一到周五')
    work_hours = Column(JSON, comment='工作时间配置 {"start": "09:00", "end": "18:00"}')
    
    # 例外配置
    exceptions = Column(JSON, comment='例外日期配置')
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    
    def __repr__(self):
        return f"<ScheduledPermission(user_id={self.user_id}, schedule={self.schedule_name})>"
    
    def is_active_at(self, check_time: datetime) -> bool:
        """检查指定时间是否激活"""
        if not self.is_active:
            return False
        
        # 检查日期范围
        check_date = check_time.date()
        if self.valid_from and check_date < self.valid_from:
            return False
        if self.valid_until and check_date > self.valid_until:
            return False
        
        # 检查工作日
        if self.work_days:
            weekday = check_time.weekday() + 1  # 1=Monday, 7=Sunday
            if weekday not in self.work_days:
                return False
        
        # 检查工作时间
        if self.work_hours:
            check_time_only = check_time.time()
            start_time = time.fromisoformat(self.work_hours['start'])
            end_time = time.fromisoformat(self.work_hours['end'])
            if not (start_time <= check_time_only <= end_time):
                return False
        
        # 检查例外日期
        if self.exceptions:
            if check_date.isoformat() in self.exceptions.get('excluded_dates', []):
                return False
            if check_date.isoformat() in self.exceptions.get('included_dates', []):
                return True
        
        return True


class RowLevelPermission(BaseModel):
    """行级权限表"""
    __tablename__ = 'sys_row_level_permission'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False, comment='权限级别')
    
    # 资源标识
    resource_type = Column(String(50), nullable=False, comment='资源类型')  # config, group
    resource_id = Column(String(200), comment='资源ID')
    
    # 过滤条件
    filter_conditions = Column(JSON, nullable=False, comment='过滤条件')
    
    # 示例过滤条件：
    # {
    #   "created_by": "self",           // 只能访问自己创建的
    #   "tags": ["finance", "hr"],      // 只能访问包含指定标签的
    #   "group_path": "/finance/*",     // 只能访问指定路径下的
    #   "environment": ["dev", "test"], // 只能访问指定环境的
    #   "custom_sql": "config_key LIKE 'app.%'"  // 自定义SQL条件
    # }
    
    # 权限来源
    granted_by = Column(BigInteger, comment='授权人ID')
    grant_reason = Column(Text, comment='授权原因')
    
    # 有效期
    expires_at = Column(DateTime, comment='过期时间')
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    
    def __repr__(self):
        return f"<RowLevelPermission(user_id={self.user_id}, resource={self.resource_type})>"
    
    @property
    def is_expired(self):
        """是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class ColumnLevelPermission(BaseModel):
    """列级权限表"""
    __tablename__ = 'sys_column_level_permission'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    
    # 表和字段配置
    table_name = Column(String(100), nullable=False, comment='表名')
    column_permissions = Column(JSON, nullable=False, comment='字段权限配置')
    
    # 示例字段权限配置：
    # {
    #   "config_value": "NONE",        // 禁止访问配置值
    #   "validation_rule": "READ",     // 只读验证规则
    #   "is_core": "ADMIN",           // 只有管理员可以访问
    #   "tags": "WRITE",              // 可以修改标签
    #   "*": "READ"                   // 其他字段默认只读
    # }
    
    # 条件配置
    conditions = Column(JSON, comment='适用条件')
    
    # 权限来源
    granted_by = Column(BigInteger, comment='授权人ID')
    grant_reason = Column(Text, comment='授权原因')
    
    # 有效期
    expires_at = Column(DateTime, comment='过期时间')
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    
    def __repr__(self):
        return f"<ColumnLevelPermission(user_id={self.user_id}, table={self.table_name})>"
    
    def get_column_permission(self, column_name: str) -> str:
        """获取字段权限"""
        if not self.column_permissions:
            return "NONE"
        
        # 直接匹配
        if column_name in self.column_permissions:
            return self.column_permissions[column_name]
        
        # 通配符匹配
        if "*" in self.column_permissions:
            return self.column_permissions["*"]
        
        return "NONE"


class PermissionAuditLog(BaseModel):
    """权限审计日志表"""
    __tablename__ = 'sys_permission_audit_log'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    action = Column(String(50), nullable=False, comment='操作类型')
    
    # 权限信息
    permission_type = Column(String(50), comment='权限类型')
    permission_level = Column(String(20), comment='权限级别')
    
    # 资源信息
    resource_type = Column(String(50), comment='资源类型')
    resource_id = Column(String(200), comment='资源ID')
    
    # 操作结果
    is_allowed = Column(Boolean, nullable=False, comment='是否允许')
    deny_reason = Column(Text, comment='拒绝原因')
    
    # 权限详情
    permission_details = Column(JSON, comment='权限检查详情')
    
    # 请求信息
    request_ip = Column(String(45), comment='请求IP')
    user_agent = Column(Text, comment='用户代理')
    request_data = Column(JSON, comment='请求数据')
    
    # 时间信息
    request_time = Column(DateTime, default=func.now(), comment='请求时间')
    
    def __repr__(self):
        return f"<PermissionAuditLog(user_id={self.user_id}, action={self.action}, allowed={self.is_allowed})>"


class PermissionApproval(BaseModel):
    """权限审批表"""
    __tablename__ = 'sys_permission_approval'
    
    approval_code = Column(String(50), nullable=False, unique=True, comment='审批编号')
    
    # 申请信息
    applicant_id = Column(BigInteger, nullable=False, comment='申请人ID')
    permission_type = Column(String(50), nullable=False, comment='权限类型')
    permission_config = Column(JSON, nullable=False, comment='权限配置')
    
    # 申请原因
    apply_reason = Column(Text, nullable=False, comment='申请原因')
    business_justification = Column(Text, comment='业务理由')
    duration_hours = Column(Integer, comment='申请时长(小时)')
    
    # 审批信息
    approver_id = Column(BigInteger, comment='审批人ID')
    approval_status = Column(
        SQLEnum(enum.Enum('ApprovalStatus', 'PENDING APPROVED REJECTED CANCELLED')),
        default='PENDING',
        comment='审批状态'
    )
    approval_reason = Column(Text, comment='审批意见')
    
    # 时间信息
    applied_at = Column(DateTime, default=func.now(), comment='申请时间')
    approved_at = Column(DateTime, comment='审批时间')
    
    def __repr__(self):
        return f"<PermissionApproval(code={self.approval_code}, status={self.approval_status})>"


print("✅ 高级权限数据库模型扩展已创建完成")