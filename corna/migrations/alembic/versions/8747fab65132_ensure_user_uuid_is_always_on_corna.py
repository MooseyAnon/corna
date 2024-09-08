"""ensure user uuid is always on corna

Revision ID: 8747fab65132
Revises: 352c1778239a
Create Date: 2024-05-17 16:25:40.949140

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8747fab65132'
down_revision = '352c1778239a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('corna', 'user_uuid',
               existing_type=postgresql.UUID(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('corna', 'user_uuid',
               existing_type=postgresql.UUID(),
               nullable=True)
    # ### end Alembic commands ###