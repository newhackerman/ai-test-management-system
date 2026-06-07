"""
模板分享相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class ShareType(str, Enum):
    """分享类型枚举"""
    PUBLIC = "PUBLIC"      # 公开分享
    TEAM = "TEAM"         # 团队分享
    PRIVATE = "PRIVATE"   # 私有分享（指定用户）


class ShareStatus(str, Enum):
    """分享状态枚举"""
    ACTIVE = "ACTIVE"     # 活跃
    EXPIRED = "EXPIRED"   # 已过期
    DISABLED = "DISABLED" # 已禁用
    DELETED = "DELETED"   # 已删除


class TemplateShare(BaseModel):
    """模板分享模型"""
    __tablename__ = "template_shares"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="分享创建者ID")
    share_type = Column(String(20), nullable=False, comment="分享类型")
    share_token = Column(String(64), nullable=False, unique=True, comment="分享令牌")
    
    # 分享设置
    title = Column(String(300), nullable=True, comment="分享标题")
    description = Column(Text, nullable=True, comment="分享描述")
    password = Column(String(100), nullable=True, comment="访问密码")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    max_access_count = Column(Integer, nullable=True, comment="最大访问次数")
    
    # 权限设置
    allow_download = Column(Boolean, nullable=False, default=True, comment="允许下载")
    allow_copy = Column(Boolean, nullable=False, default=True, comment="允许复制")
    allow_comment = Column(Boolean, nullable=False, default=True, comment="允许评论")
    require_login = Column(Boolean, nullable=False, default=False, comment="需要登录")
    
    # 访问控制
    allowed_users = Column(JSON, nullable=True, comment="允许访问的用户ID列表")
    allowed_teams = Column(JSON, nullable=True, comment="允许访问的团队ID列表")
    
    # 状态和统计
    status = Column(String(20), nullable=False, default='ACTIVE', comment="分享状态")
    access_count = Column(Integer, nullable=False, default=0, comment="访问次数")
    last_accessed_at = Column(DateTime, nullable=True, comment="最后访问时间")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="shares")
    # owner = relationship("User", backref="template_shares")
    access_records = relationship("TemplateShareAccess", back_populates="share", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TemplateShare(id={self.id}, template_id={self.template_id}, share_type='{self.share_type}')>"


class TemplateShareAccess(BaseModel):
    """模板分享访问记录模型"""
    __tablename__ = "template_share_access"
    
    # 基本信息
    share_id = Column(Integer, ForeignKey("template_shares.id"), nullable=False, comment="分享ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="访问用户ID（匿名访问时为空）")
    
    # 访问信息
    access_ip = Column(String(45), nullable=True, comment="访问IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    referer = Column(String(500), nullable=True, comment="来源页面")
    
    # 访问结果
    success = Column(Boolean, nullable=False, default=True, comment="访问是否成功")
    error_message = Column(String(500), nullable=True, comment="错误信息")
    
    # 关联关系
    share = relationship("TemplateShare", back_populates="access_records")
    # user = relationship("User", backref="template_access_records")
    
    def __repr__(self):
        return f"<TemplateShareAccess(id={self.id}, share_id={self.share_id}, user_id={self.user_id})>"


class TemplateFavorite(BaseModel):
    """模板收藏模型"""
    __tablename__ = "template_favorites"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    folder_name = Column(String(100), nullable=False, default="默认收藏夹", comment="收藏夹名称")
    
    # 收藏设置
    notes = Column(Text, nullable=True, comment="个人备注")
    tags = Column(JSON, nullable=True, comment="个人标签")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="favorites")
    # user = relationship("User", backref="template_favorites")
    
    # 唯一约束：同一用户不能重复收藏同一模板
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def __repr__(self):
        return f"<TemplateFavorite(id={self.id}, template_id={self.template_id}, user_id={self.user_id})>"


class TemplateRating(BaseModel):
    """模板评分模型"""
    __tablename__ = "template_ratings"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 评分信息
    rating = Column(Integer, nullable=False, comment="评分（1-5分）")
    comment = Column(Text, nullable=True, comment="评价内容")
    
    # 评分维度（可选的详细评分）
    usefulness = Column(Integer, nullable=True, comment="实用性评分（1-5分）")
    clarity = Column(Integer, nullable=True, comment="清晰度评分（1-5分）")
    creativity = Column(Integer, nullable=True, comment="创新性评分（1-5分）")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="ratings")
    # user = relationship("User", backref="template_ratings")
    
    # 唯一约束：同一用户只能对同一模板评分一次
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def __repr__(self):
        return f"<TemplateRating(id={self.id}, template_id={self.template_id}, user_id={self.user_id}, rating={self.rating})>"


class TemplateComment(BaseModel):
    """模板评论模型"""
    __tablename__ = "template_comments"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 评论内容
    content = Column(Text, nullable=False, comment="评论内容")
    parent_comment_id = Column(Integer, ForeignKey("template_comments.id"), nullable=True, comment="父评论ID")
    
    # 评论状态
    is_hidden = Column(Boolean, nullable=False, default=False, comment="是否隐藏")
    is_pinned = Column(Boolean, nullable=False, default=False, comment="是否置顶")
    
    # 互动统计
    like_count = Column(Integer, nullable=False, default=0, comment="点赞数")
    reply_count = Column(Integer, nullable=False, default=0, comment="回复数")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="comments")
    # user = relationship("User", backref="template_comments")
    parent_comment = relationship("TemplateComment", remote_side="TemplateComment.id", backref="replies")
    
    def __repr__(self):
        return f"<TemplateComment(id={self.id}, template_id={self.template_id}, user_id={self.user_id})>"


class TemplateCommentLike(BaseModel):
    """模板评论点赞模型"""
    __tablename__ = "template_comment_likes"
    
    # 基本信息
    comment_id = Column(Integer, ForeignKey("template_comments.id"), nullable=False, comment="评论ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 点赞类型
    like_type = Column(String(20), nullable=False, default='LIKE', comment="点赞类型（LIKE/DISLIKE）")
    
    # 关联关系
    comment = relationship("TemplateComment", backref="likes")
    # user = relationship("User", backref="comment_likes")
    
    # 唯一约束：同一用户只能对同一评论点赞一次
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def __repr__(self):
        return f"<TemplateCommentLike(id={self.id}, comment_id={self.comment_id}, user_id={self.user_id})>"


class TemplateCollaborator(BaseModel):
    """模板协作者模型"""
    __tablename__ = "template_collaborators"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="协作者用户ID")
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="邀请者用户ID")
    
    # 协作权限
    permission_level = Column(String(20), nullable=False, default='VIEW', comment="权限级别（VIEW/EDIT/ADMIN）")
    can_edit = Column(Boolean, nullable=False, default=False, comment="可以编辑")
    can_share = Column(Boolean, nullable=False, default=False, comment="可以分享")
    can_delete = Column(Boolean, nullable=False, default=False, comment="可以删除")
    
    # 协作状态
    status = Column(String(20), nullable=False, default='PENDING', comment="协作状态（PENDING/ACCEPTED/REJECTED）")
    accepted_at = Column(DateTime, nullable=True, comment="接受时间")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="collaborators")
    # user = relationship("User", foreign_keys=[user_id], backref="template_collaborations")
    # inviter = relationship("User", foreign_keys=[inviter_id], backref="template_invitations")
    
    # 唯一约束：同一用户不能重复成为同一模板的协作者
    __table_args__ = (
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def __repr__(self):
        return f"<TemplateCollaborator(id={self.id}, template_id={self.template_id}, user_id={self.user_id})>"


class TemplateUsageReport(BaseModel):
    """模板使用报告模型"""
    __tablename__ = "template_usage_reports"
    
    # 基本信息
    template_id = Column(Integer, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="举报者ID")
    
    # 举报信息
    report_type = Column(String(50), nullable=False, comment="举报类型")
    reason = Column(Text, nullable=False, comment="举报原因")
    description = Column(Text, nullable=True, comment="详细描述")
    
    # 处理状态
    status = Column(String(20), nullable=False, default='PENDING', comment="处理状态")
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="处理者ID")
    handled_at = Column(DateTime, nullable=True, comment="处理时间")
    handler_note = Column(Text, nullable=True, comment="处理备注")
    
    # 关联关系
    template = relationship("AIPromptTemplate", backref="usage_reports")
    # reporter = relationship("User", foreign_keys=[reporter_id], backref="template_reports")
    # handler = relationship("User", foreign_keys=[handler_id], backref="handled_reports")
    
    def __repr__(self):
        return f"<TemplateUsageReport(id={self.id}, template_id={self.template_id}, report_type='{self.report_type}')>"