"""Add parse_config field to documents table

Revision ID: add_parse_config_field
Revises: db65014c2888
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_parse_config_field'
down_revision = 'db65014c2888'  # Reference the current head
branch_labels = None
depends_on = None


def upgrade():
    """Add parse_config field to documents table"""
    op.add_column('documents', sa.Column('parse_config', sa.Text(), nullable=True))


def downgrade():
    """Remove parse_config field from documents table"""
    op.drop_column('documents', 'parse_config') 