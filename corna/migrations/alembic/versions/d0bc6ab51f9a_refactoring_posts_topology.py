"""refactoring posts topology

Revision ID: d0bc6ab51f9a
Revises: 
Create Date: 2023-11-13 22:31:08.115991

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd0bc6ab51f9a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('emails',
    sa.Column('email_address', sa.Text(), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=True),
    sa.PrimaryKeyConstraint('email_address')
    )
    op.create_table('testtable',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('username', sa.Text(), nullable=True),
    sa.Column('email_address', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['email_address'], ['emails.email_address'], ),
    sa.PrimaryKeyConstraint('uuid'),
    sa.UniqueConstraint('email_address')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('corna',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('domain_name', sa.Text(), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('user_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['user_uuid'], ['users.uuid'], ),
    sa.PrimaryKeyConstraint('uuid'),
    sa.UniqueConstraint('user_uuid')
    )
    op.create_index(op.f('ix_corna_domain_name'), 'corna', ['domain_name'], unique=True)
    op.create_table('sessions',
    sa.Column('session_id', sa.Text(), nullable=False),
    sa.Column('cookie_id', sa.Text(), nullable=False),
    sa.Column('user_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['user_uuid'], ['users.uuid'], ),
    sa.PrimaryKeyConstraint('session_id'),
    sa.UniqueConstraint('user_uuid')
    )
    op.create_index(op.f('ix_sessions_cookie_id'), 'sessions', ['cookie_id'], unique=True)
    op.create_table('posts',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('url_extension', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('type', sa.Text(), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('corna_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['corna_uuid'], ['corna.uuid'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index(op.f('ix_posts_url_extension'), 'posts', ['url_extension'], unique=True)
    op.create_table('images',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('url_extension', sa.Text(), nullable=True),
    sa.Column('path', sa.Text(), nullable=True),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('post_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['post_uuid'], ['posts.uuid'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index(op.f('ix_images_url_extension'), 'images', ['url_extension'], unique=True)
    op.create_table('text',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('post_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['post_uuid'], ['posts.uuid'], ),
    sa.PrimaryKeyConstraint('uuid'),
    sa.UniqueConstraint('post_uuid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('text')
    op.drop_index(op.f('ix_images_url_extension'), table_name='images')
    op.drop_table('images')
    op.drop_index(op.f('ix_posts_url_extension'), table_name='posts')
    op.drop_table('posts')
    op.drop_index(op.f('ix_sessions_cookie_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_corna_domain_name'), table_name='corna')
    op.drop_table('corna')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.drop_table('testtable')
    op.drop_table('emails')
    # ### end Alembic commands ###
