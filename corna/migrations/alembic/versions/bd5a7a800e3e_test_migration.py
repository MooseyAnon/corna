"""test migration

Revision ID: bd5a7a800e3e
Revises: 
Create Date: 2023-08-07 00:44:35.956362

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bd5a7a800e3e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('emails',
    sa.Column('email_address', sa.Text(), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('email_address')
    )
    op.create_table('photo_posts',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('url_extension', sa.Text(), nullable=True),
    sa.Column('path', sa.Text(), nullable=True),
    sa.Column('caption', sa.Text(), nullable=True),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('uuid')
    )
    op.create_index(op.f('ix_photo_posts_url_extension'), 'photo_posts', ['url_extension'], unique=True)
    op.create_table('testtable',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('text_posts',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('uuid')
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
    op.create_table('blogs',
    sa.Column('blog_uuid', postgresql.UUID(), nullable=False),
    sa.Column('domain_name', sa.Text(), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('user_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['user_uuid'], ['users.uuid'], ),
    sa.PrimaryKeyConstraint('blog_uuid'),
    sa.UniqueConstraint('user_uuid')
    )
    op.create_index(op.f('ix_blogs_domain_name'), 'blogs', ['domain_name'], unique=True)
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
    sa.Column('post_uuid', postgresql.UUID(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('type', sa.Text(), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('blog_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['blog_uuid'], ['blogs.blog_uuid'], ),
    sa.PrimaryKeyConstraint('post_uuid')
    )
    op.create_table('post_object_map',
    sa.Column('uuid', postgresql.UUID(), nullable=False),
    sa.Column('post_uuid', postgresql.UUID(), nullable=True),
    sa.Column('text_post_uuid', postgresql.UUID(), nullable=True),
    sa.Column('photo_post_uuid', postgresql.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['photo_post_uuid'], ['photo_posts.uuid'], ),
    sa.ForeignKeyConstraint(['post_uuid'], ['posts.post_uuid'], ),
    sa.ForeignKeyConstraint(['text_post_uuid'], ['text_posts.uuid'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('post_object_map')
    op.drop_table('posts')
    op.drop_index(op.f('ix_sessions_cookie_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_blogs_domain_name'), table_name='blogs')
    op.drop_table('blogs')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.drop_table('text_posts')
    op.drop_table('testtable')
    op.drop_index(op.f('ix_photo_posts_url_extension'), table_name='photo_posts')
    op.drop_table('photo_posts')
    op.drop_table('emails')
    # ### end Alembic commands ###
