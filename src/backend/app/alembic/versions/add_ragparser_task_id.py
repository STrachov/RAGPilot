"""Add ragparser_task_id to documents table

Revision ID: add_ragparser_task_id
Revises: 28f0e393ca16
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_ragparser_task_id'
down_revision = '28f0e393ca16'  # References the first_run migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add ragparser_task_id column to documents table"""
    op.add_column('documents', sa.Column('ragparser_task_id', sa.String(255), nullable=True))

def downgrade() -> None:
    """Remove ragparser_task_id column from documents table"""
    op.drop_column('documents', 'ragparser_task_id') 