"""Change document status to JSON structure

Revision ID: db65014c2888
Revises: add_ragparser_task_id
Create Date: 2025-06-09 17:15:16.596653

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'db65014c2888'
down_revision = 'add_ragparser_task_id'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('documents', 'status',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('documents', 'status',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    # ### end Alembic commands ###
