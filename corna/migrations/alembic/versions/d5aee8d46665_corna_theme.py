"""corna theme

Revision ID: d5aee8d46665
Revises: c2ce210a4826
Create Date: 2024-01-29 23:27:04.661123

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5aee8d46665'
down_revision = 'c2ce210a4826'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corna', sa.Column('theme', postgresql.UUID(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corna', 'theme')
    # ### end Alembic commands ###
