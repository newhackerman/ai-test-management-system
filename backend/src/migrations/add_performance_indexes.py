"""
添加性能优化索引

本迁移脚本添加项目管理模块的性能优化索引，包括：
- 复合索引
- 全文索引
- 覆盖索引
"""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session, get_async_session_ctx

logger = logging.getLogger(__name__)


async def upgrade():
    """添加性能优化索引"""
    async with get_async_session_ctx() as db:
        try:
            # 项目表索引
            project_indexes = [
                # 复合索引用于项目列表查询
                """CREATE INDEX IF NOT EXISTS idx_projects_status_type_priority 
                   ON projects(status, project_type, priority)""",
                
                """CREATE INDEX IF NOT EXISTS idx_projects_manager_status 
                   ON projects(project_manager_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_projects_dates 
                   ON projects(planned_start_date, planned_end_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_projects_search 
                   ON projects(project_name, project_code)""",
                
                """CREATE INDEX IF NOT EXISTS idx_projects_created_updated 
                   ON projects(created_at, updated_at)""",
                
                """CREATE INDEX IF NOT EXISTS idx_projects_deleted_status 
                   ON projects(deleted_at, status)""",
                
                # 覆盖索引用于项目列表查询
                """CREATE INDEX IF NOT EXISTS idx_projects_list_covering 
                   ON projects(status, project_type, priority, project_manager_id, 
                              project_name, project_code, created_at, updated_at)""",
                
                # 全文索引用于搜索
                """CREATE FULLTEXT INDEX IF NOT EXISTS idx_projects_fulltext 
                   ON projects(project_name, description)""",
            ]
            
            # 项目成员表索引
            member_indexes = [
                """CREATE INDEX IF NOT EXISTS idx_project_members_user_status 
                   ON project_members(user_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_project_members_project_role 
                   ON project_members(project_id, role_in_project)""",
                
                """CREATE INDEX IF NOT EXISTS idx_project_members_join_leave 
                   ON project_members(join_date, leave_date)""",
                
                # 覆盖索引用于权限检查
                """CREATE INDEX IF NOT EXISTS idx_project_members_permission 
                   ON project_members(project_id, user_id, status)""",
            ]
            
            # 任务表索引
            task_indexes = [
                """CREATE INDEX IF NOT EXISTS idx_tasks_project_status 
                   ON project_tasks(project_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status 
                   ON project_tasks(assignee_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_tasks_type_priority 
                   ON project_tasks(task_type, priority)""",
                
                """CREATE INDEX IF NOT EXISTS idx_tasks_dates 
                   ON project_tasks(planned_start_date, planned_end_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_tasks_parent 
                   ON project_tasks(parent_task_id)""",
                
                """CREATE INDEX IF NOT EXISTS idx_tasks_created_updated 
                   ON project_tasks(created_at, updated_at)""",
                
                # 覆盖索引用于任务统计
                """CREATE INDEX IF NOT EXISTS idx_tasks_stats_covering 
                   ON project_tasks(project_id, status, task_type, priority, 
                                   assignee_id, created_at)""",
                
                # 全文索引
                """CREATE FULLTEXT INDEX IF NOT EXISTS idx_tasks_fulltext 
                   ON project_tasks(task_name, description)""",
            ]
            
            # 里程碑表索引
            milestone_indexes = [
                """CREATE INDEX IF NOT EXISTS idx_milestones_project_status 
                   ON project_milestones(project_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_milestones_owner_status 
                   ON project_milestones(owner_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_milestones_dates 
                   ON project_milestones(planned_date, actual_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_milestones_type 
                   ON project_milestones(milestone_type)""",
                
                # 覆盖索引用于里程碑统计
                """CREATE INDEX IF NOT EXISTS idx_milestones_stats_covering 
                   ON project_milestones(project_id, status, milestone_type, 
                                        planned_date, actual_date)""",
            ]
            
            # 工作日志表索引
            worklog_indexes = [
                """CREATE INDEX IF NOT EXISTS idx_work_logs_user_date 
                   ON work_logs(user_id, work_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_work_logs_project_date 
                   ON work_logs(project_id, work_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_work_logs_task_date 
                   ON work_logs(task_id, work_date)""",
                
                """CREATE INDEX IF NOT EXISTS idx_work_logs_status 
                   ON work_logs(status)""",
                
                # 覆盖索引用于工时统计
                """CREATE INDEX IF NOT EXISTS idx_work_logs_stats_covering 
                   ON work_logs(project_id, user_id, work_date, hours_worked, 
                              work_type, status)""",
            ]
            
            # 风险表索引
            risk_indexes = [
                """CREATE INDEX IF NOT EXISTS idx_risks_project_status 
                   ON project_risks(project_id, status)""",
                
                """CREATE INDEX IF NOT EXISTS idx_risks_level_category 
                   ON project_risks(risk_level, risk_category)""",
                
                """CREATE INDEX IF NOT EXISTS idx_risks_owner 
                   ON project_risks(owner_id)""",
                
                """CREATE INDEX IF NOT EXISTS idx_risks_dates 
                   ON project_risks(identified_date, target_resolution_date)""",
                
                # 覆盖索引用于风险统计
                """CREATE INDEX IF NOT EXISTS idx_risks_stats_covering 
                   ON project_risks(project_id, status, risk_level, risk_category, 
                                   identified_date)""",
            ]
            
            all_indexes = (project_indexes + member_indexes + task_indexes + 
                          milestone_indexes + worklog_indexes + risk_indexes)
            
            # 执行索引创建
            created_count = 0
            for index_sql in all_indexes:
                try:
                    await db.execute(text(index_sql))
                    created_count += 1
                    logger.info(f"创建索引成功: {index_sql.split()[5]}")
                except Exception as e:
                    logger.warning(f"创建索引失败: {index_sql.split()[5]}, 错误: {e}")
            
            await db.commit()
            logger.info(f"性能优化索引创建完成，成功创建 {created_count} 个索引")
            
        except Exception as e:
            logger.error(f"创建性能优化索引失败: {e}")
            await db.rollback()
            raise


async def downgrade():
    """删除性能优化索引"""
    async with get_async_session_ctx() as db:
        try:
            # 删除索引的SQL语句
            drop_indexes = [
                # 项目表索引
                "DROP INDEX IF EXISTS idx_projects_status_type_priority ON projects",
                "DROP INDEX IF EXISTS idx_projects_manager_status ON projects",
                "DROP INDEX IF EXISTS idx_projects_dates ON projects",
                "DROP INDEX IF EXISTS idx_projects_search ON projects",
                "DROP INDEX IF EXISTS idx_projects_created_updated ON projects",
                "DROP INDEX IF EXISTS idx_projects_deleted_status ON projects",
                "DROP INDEX IF EXISTS idx_projects_list_covering ON projects",
                "DROP INDEX IF EXISTS idx_projects_fulltext ON projects",
                
                # 项目成员表索引
                "DROP INDEX IF EXISTS idx_project_members_user_status ON project_members",
                "DROP INDEX IF EXISTS idx_project_members_project_role ON project_members",
                "DROP INDEX IF EXISTS idx_project_members_join_leave ON project_members",
                "DROP INDEX IF EXISTS idx_project_members_permission ON project_members",
                
                # 任务表索引
                "DROP INDEX IF EXISTS idx_tasks_project_status ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_assignee_status ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_type_priority ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_dates ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_parent ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_created_updated ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_stats_covering ON project_tasks",
                "DROP INDEX IF EXISTS idx_tasks_fulltext ON project_tasks",
                
                # 里程碑表索引
                "DROP INDEX IF EXISTS idx_milestones_project_status ON project_milestones",
                "DROP INDEX IF EXISTS idx_milestones_owner_status ON project_milestones",
                "DROP INDEX IF EXISTS idx_milestones_dates ON project_milestones",
                "DROP INDEX IF EXISTS idx_milestones_type ON project_milestones",
                "DROP INDEX IF EXISTS idx_milestones_stats_covering ON project_milestones",
                
                # 工作日志表索引
                "DROP INDEX IF EXISTS idx_work_logs_user_date ON work_logs",
                "DROP INDEX IF EXISTS idx_work_logs_project_date ON work_logs",
                "DROP INDEX IF EXISTS idx_work_logs_task_date ON work_logs",
                "DROP INDEX IF EXISTS idx_work_logs_status ON work_logs",
                "DROP INDEX IF EXISTS idx_work_logs_stats_covering ON work_logs",
                
                # 风险表索引
                "DROP INDEX IF EXISTS idx_risks_project_status ON project_risks",
                "DROP INDEX IF EXISTS idx_risks_level_category ON project_risks",
                "DROP INDEX IF EXISTS idx_risks_owner ON project_risks",
                "DROP INDEX IF EXISTS idx_risks_dates ON project_risks",
                "DROP INDEX IF EXISTS idx_risks_stats_covering ON project_risks",
            ]
            
            # 执行索引删除
            dropped_count = 0
            for drop_sql in drop_indexes:
                try:
                    await db.execute(text(drop_sql))
                    dropped_count += 1
                    logger.info(f"删除索引成功: {drop_sql.split()[4]}")
                except Exception as e:
                    logger.warning(f"删除索引失败: {drop_sql.split()[4]}, 错误: {e}")
            
            await db.commit()
            logger.info(f"性能优化索引删除完成，成功删除 {dropped_count} 个索引")
            
        except Exception as e:
            logger.error(f"删除性能优化索引失败: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("开始创建性能优化索引...")
        await upgrade()
        print("性能优化索引创建完成！")
    
    asyncio.run(main())