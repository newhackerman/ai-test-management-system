"""merge_all_heads

Revision ID: df4d66178796
Revises: 002_ai_assistant_extended, 006_create_ai_file_storage_tables, 007_add_performance_indexes, 008_update_project_management_tables, 012_optimize_project_models, add_ai_alert_config_tables, create_ai_suggestion_tables_006
Create Date: 2025-09-20 16:35:00.516686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df4d66178796'
down_revision = ('002_ai_assistant_extended', '006_create_ai_file_storage_tables', '007_add_performance_indexes', '008_update_project_management_tables', '012_optimize_project_models', 'add_ai_alert_config_tables', 'create_ai_suggestion_tables_006')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass