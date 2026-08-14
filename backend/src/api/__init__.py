"""
API路由模块初始化文件
"""
from fastapi import APIRouter
from ..core.config import get_route_config
from .auth import router as auth_router
from .auth_permissions import router as auth_permissions_router
from .users import router as users_router
from .roles import router as roles_router
from .permissions import router as permissions_router
from .config import router as config_router
from .settings import router as settings_router
from .dashboard import router as dashboard_router
from .audit import router as audit_router
from .config_import_export import router as import_export_router
from .websocket import router as websocket_router
from .validation_rules import router as validation_rules_router
from .advanced_permissions import router as advanced_permissions_router
from .v1.ai_assistant import router as ai_assistant_router
from .v1.ai_queue import router as ai_queue_router
from .v1.streaming import router as streaming_router
from .v1.ai_websocket import router as ai_websocket_router
from .v1.cost_control import router as cost_control_router
from .v1.ai_suggestions import router as ai_suggestions_router
from .v1.prompt_templates import router as prompt_templates_router
from .v1.ai_model_config import router as ai_model_config_router
from .v1.ai_alert_config import router as ai_alert_config_router
from .v1.health_websocket import router as health_websocket_router
from .v1.ai_permissions import router as ai_permissions_router

# 创建主路由
api_router = APIRouter()

# 使用配置文件注册路由
def register_router_with_config(router, route_name: str):
    """使用配置注册路由"""
    config = get_route_config(route_name)
    if config["prefix"]:
        api_router.include_router(router, prefix=config["prefix"], tags=config["tags"])
    else:
        api_router.include_router(router, tags=config["tags"])

# 注册认证路由
register_router_with_config(auth_router, "auth")

# 注册认证权限路由
register_router_with_config(auth_permissions_router, "auth_permissions")

# 注册用户管理路由
register_router_with_config(users_router, "users")

# 注册角色管理路由
register_router_with_config(roles_router, "roles")

# 注册权限管理路由
register_router_with_config(permissions_router, "permissions")

# 注册配置管理路由
register_router_with_config(config_router, "configs")

# 注册系统设置路由
api_router.include_router(settings_router, prefix="/settings", tags=["系统设置"])

# 注册仪表盘真实数据汇总路由
api_router.include_router(dashboard_router)

# 注册审核管理路由
register_router_with_config(audit_router, "audit")

# 注册配置导入导出路由
register_router_with_config(import_export_router, "import_export")

# 注册WebSocket路由
register_router_with_config(websocket_router, "websocket")

# 注册验证规则管理路由
register_router_with_config(validation_rules_router, "validation_rules")

# 注册高级权限管理路由
register_router_with_config(advanced_permissions_router, "advanced_permissions")

# 注册AI助手路由
register_router_with_config(ai_assistant_router, "ai_assistant")

# 注册AI队列管理路由
register_router_with_config(ai_queue_router, "ai_queue")

# 注册流式响应路由
register_router_with_config(streaming_router, "streaming")

# 注册AI WebSocket路由
register_router_with_config(ai_websocket_router, "ai_websocket")

# 注册成本控制路由
register_router_with_config(cost_control_router, "cost_control")

# 注册AI建议路由
register_router_with_config(ai_suggestions_router, "ai_suggestions")

# 注册提示词模板路由
register_router_with_config(prompt_templates_router, "prompt_templates")

# 注册AI模型配置路由
register_router_with_config(ai_model_config_router, "ai_model_config")

# 注册AI告警配置路由
register_router_with_config(ai_alert_config_router, "ai_alert_config")

# 注册健康监控WebSocket路由
register_router_with_config(health_websocket_router, "health_websocket")

# 注册AI权限管理路由
register_router_with_config(ai_permissions_router, "ai_permissions")

# 注册用户角色权限管理路由
from .v1.user_role_management import router as user_role_management_router
api_router.include_router(user_role_management_router, tags=["用户角色权限管理"])

# 注册AI操作日志路由
from .v1.ai_operation_logs import router as ai_operation_logs_router
register_router_with_config(ai_operation_logs_router, "ai_operation_logs")

# 注册缓存预热管理路由
from .v1.cache_preheating import router as cache_preheating_router
register_router_with_config(cache_preheating_router, "cache_preheating")

# 注册百度文心一言路由
from .v1.baidu_wenxin import router as baidu_wenxin_router
register_router_with_config(baidu_wenxin_router, "baidu_wenxin")

# 注册阿里通义千问路由
from .v1.aliyun_tongyi import router as aliyun_tongyi_router
register_router_with_config(aliyun_tongyi_router, "aliyun_tongyi")

# 注册中文内容优化路由
from .v1.chinese_routing import router as chinese_routing_router
register_router_with_config(chinese_routing_router, "chinese_routing")

# 注册多语言响应处理路由
from .v1.multilingual_response import router as multilingual_response_router
register_router_with_config(multilingual_response_router, "multilingual")

# 注册项目管理路由
from .v1.projects import router as projects_router
register_router_with_config(projects_router, "projects")

# 注册团队管理路由
from .v1.teams import router as teams_router
register_router_with_config(teams_router, "teams")

# 注册任务管理路由
from .v1.tasks import router as tasks_router
register_router_with_config(tasks_router, "tasks")

from .v1.notifications import router as notifications_router
api_router.include_router(notifications_router, tags=["站内通知"])

# 注册风险管理路由
from .v1.risks import router as risks_router
register_router_with_config(risks_router, "risks")

# 注册里程碑管理路由
from .v1.milestones import router as milestones_router
register_router_with_config(milestones_router, "milestones")

# 注册进度管理路由
from .v1.progress import router as progress_router
register_router_with_config(progress_router, "progress")

# 注册需求管理路由
from .v1.requirements import router as requirements_router
api_router.include_router(requirements_router, tags=["需求管理"])

# 注册需求评审路由
from .v1.requirement_reviews import router as requirement_reviews_router
api_router.include_router(requirement_reviews_router, tags=["需求评审"])

# 注册需求变更路由
from .v1.requirement_changes import router as requirement_changes_router
api_router.include_router(requirement_changes_router, tags=["需求变更"])

# 注册需求追溯路由
from .v1.requirement_traceability import router as requirement_traceability_router
api_router.include_router(requirement_traceability_router, tags=["需求追溯"])

# 注册需求AI分析路由
from .v1.requirement_ai_analysis import router as requirement_ai_analysis_router
api_router.include_router(requirement_ai_analysis_router, tags=["需求AI分析"])

# 注册仪表板管理路由
from .v1.dashboards import router as dashboards_router
api_router.include_router(dashboards_router, prefix="/dashboards", tags=["仪表板管理"])

# 注册会议管理路由
from .v1.meetings import router as meetings_router
api_router.include_router(meetings_router, prefix="/meetings", tags=["会议管理"])

# 注册测试管理路由
from .v1.test_plans import router as test_plans_router
api_router.include_router(test_plans_router, tags=["测试计划"])

from .v1.test_cases import router as test_cases_router
api_router.include_router(test_cases_router, tags=["测试用例"])

from .v1.test_executions import router as test_executions_router
api_router.include_router(test_executions_router, tags=["测试执行"])

from .v1.test_reports import router as test_reports_router
api_router.include_router(test_reports_router, tags=["测试报告"])

from .v1.test_report_subscriptions import router as test_report_subscriptions_router
api_router.include_router(test_report_subscriptions_router, tags=["测试报告订阅"])

from .v1.security_tests import router as security_tests_router
api_router.include_router(security_tests_router, tags=["安全测试"])

from .v1.performance_tests import router as performance_tests_router
api_router.include_router(performance_tests_router, tags=["性能测试"])

from .v1.test_requirement_integration import router as test_requirement_integration_router
api_router.include_router(test_requirement_integration_router, tags=["测试需求集成"])

from .v1.defects import router as defects_router
api_router.include_router(defects_router, tags=["缺陷管理"])

from .v1.quality_metrics import router as quality_metrics_router
api_router.include_router(quality_metrics_router, tags=["质量指标"])

# 健康检查
from .v1.reports import router as reports_router
api_router.include_router(reports_router)

from .v1.auto_recovery import router as auto_recovery_router
api_router.include_router(auto_recovery_router)

@api_router.get("/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "message": "API服务正常运行"}
