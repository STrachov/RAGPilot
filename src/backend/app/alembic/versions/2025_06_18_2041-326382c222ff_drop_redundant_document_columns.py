"""drop_redundant_document_columns

Revision ID: 326382c222ff
Revises: a27b7e62850d
Create Date: 2025-06-18 20:41:55.779412

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '326382c222ff'
down_revision = 'a27b7e62850d'
branch_labels = None
depends_on = None


def upgrade():
    """Drop redundant columns that are now accessed via JSON properties"""
    
    # Drop redundant columns that are now handled via properties
    op.drop_column('documents', 'processed_at')
    op.drop_column('documents', 'ragparser_task_id') 
    op.drop_column('documents', 'parse_config')


def downgrade():
    """Restore redundant columns (for rollback purposes)"""
    
    # Add back the redundant columns if needed for rollback
    op.add_column('documents', sa.Column('processed_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('ragparser_task_id', sa.String(255), nullable=True))
    op.add_column('documents', sa.Column('parse_config', sa.Text(), nullable=True))
