"""add themes table

Revision ID: d5ad8dff4f17
Revises: 29b78a584b6e
Create Date: 2024-05-17 21:51:17.342279

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5ad8dff4f17'
down_revision = '29b78a584b6e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('themes',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('path', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('creator_user_id', postgresql.UUID(), nullable=True),
    sa.Column('thumbnail', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['creator_user_id'], ['users.uuid'], ),
    sa.ForeignKeyConstraint(['thumbnail'], ['images.uuid'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('themes')
    # ### end Alembic commands ###