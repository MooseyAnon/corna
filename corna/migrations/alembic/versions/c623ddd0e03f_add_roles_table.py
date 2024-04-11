"""Add roles table

Revision ID: c623ddd0e03f
Revises: d5aee8d46665
Create Date: 2024-04-11 16:10:40.834844

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c623ddd0e03f'
down_revision = 'd5aee8d46665'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('roles',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('permissions', sa.BigInteger(), nullable=False),
    sa.Column('creator_uuid', postgresql.UUID(), nullable=False),
    sa.Column('corna_uuid', postgresql.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['corna_uuid'], ['corna.uuid'], ),
    sa.ForeignKeyConstraint(['creator_uuid'], ['users.uuid'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    op.create_table('role_user_map',
    sa.Column('role_id', postgresql.UUID(), nullable=False),
    sa.Column('user_id', postgresql.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.uuid'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ),
    sa.PrimaryKeyConstraint('role_id', 'user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('role_user_map')
    op.drop_table('roles')
    # ### end Alembic commands ###