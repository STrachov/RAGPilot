"""move_page_count_to_metadata

Revision ID: 75e189a397ea
Revises: 326382c222ff
Create Date: 2025-06-18 20:45:08.044812

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '75e189a397ea'
down_revision = '326382c222ff'
branch_labels = None
depends_on = None


def upgrade():
    """Drop page_count column - it belongs in metadata.structure"""
    
    # Drop the page_count column and its index
    op.drop_index('ix_documents_page_count', 'documents')
    op.drop_column('documents', 'page_count')


def downgrade():
    """Restore page_count column if needed for rollback"""
    
    # Add back the page_count column and index
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    op.create_index('ix_documents_page_count', 'documents', ['page_count'])
