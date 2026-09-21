"""Zang v0.3 messaging features

Revision ID: a7c3d91e4f20
Revises: 71f2277cdf9f
Create Date: 2026-09-21

This migration is intentionally defensive because early Zang development databases
may have been created with db.create_all() and can already contain some columns.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c3d91e4f20'
down_revision = '71f2277cdf9f'
branch_labels = None
depends_on = None


def _columns(bind, table_name):
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column['name'] for column in inspector.get_columns(table_name)}


def _indexes(bind, table_name):
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {index['name'] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if 'users' in tables:
        user_columns = _columns(bind, 'users')
        if 'last_seen_at' not in user_columns:
            op.add_column('users', sa.Column('last_seen_at', sa.DateTime(), nullable=True))

    if 'chats' in tables:
        chat_columns = _columns(bind, 'chats')
        if 'kind' not in chat_columns:
            op.add_column(
                'chats',
                sa.Column('kind', sa.String(length=20), nullable=False, server_default='group')
            )
        if 'description' not in chat_columns:
            op.add_column('chats', sa.Column('description', sa.String(length=280), nullable=True))

        # Preserve channels made by v0.2, where # at the start of the title was used as the marker.
        op.execute("UPDATE chats SET kind='channel' WHERE title LIKE '#%' AND (kind IS NULL OR kind='group')")

        if 'ix_chats_kind' not in _indexes(bind, 'chats'):
            op.create_index('ix_chats_kind', 'chats', ['kind'], unique=False)

    if 'messages' in tables:
        message_columns = _columns(bind, 'messages')
        if 'user_id' not in message_columns:
            op.add_column('messages', sa.Column('user_id', sa.Integer(), nullable=True))
        if 'reply_to_id' not in message_columns:
            op.add_column('messages', sa.Column('reply_to_id', sa.Integer(), nullable=True))
        if 'edited_at' not in message_columns:
            op.add_column('messages', sa.Column('edited_at', sa.DateTime(), nullable=True))
        if 'is_deleted' not in message_columns:
            op.add_column(
                'messages',
                sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false())
            )

        indexes = _indexes(bind, 'messages')
        if 'ix_messages_user_id' not in indexes:
            op.create_index('ix_messages_user_id', 'messages', ['user_id'], unique=False)
        if 'ix_messages_reply_to_id' not in indexes:
            op.create_index('ix_messages_reply_to_id', 'messages', ['reply_to_id'], unique=False)

    tables = set(sa.inspect(bind).get_table_names())
    if 'chat_members' not in tables:
        op.create_table(
            'chat_members',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('chat_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('access_code', sa.String(length=64), nullable=False),
            sa.Column('is_owner', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('last_read_message_id', sa.Integer(), nullable=True),
            sa.Column('joined_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('chat_id', 'user_id', name='uq_chat_member')
        )
        op.create_index('ix_chat_members_chat_id', 'chat_members', ['chat_id'], unique=False)
        op.create_index('ix_chat_members_user_id', 'chat_members', ['user_id'], unique=False)
        op.create_index('ix_chat_members_access_code', 'chat_members', ['access_code'], unique=False)
    else:
        member_columns = _columns(bind, 'chat_members')
        if 'is_admin' not in member_columns:
            op.add_column(
                'chat_members',
                sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if 'last_read_message_id' not in member_columns:
            op.add_column('chat_members', sa.Column('last_read_message_id', sa.Integer(), nullable=True))

    # Existing owners are also administrators in v0.3.
    if 'chat_members' in set(sa.inspect(bind).get_table_names()):
        op.execute("UPDATE chat_members SET is_admin=1 WHERE is_owner=1")


def downgrade():
    bind = op.get_bind()

    if 'chat_members' in set(sa.inspect(bind).get_table_names()):
        member_columns = _columns(bind, 'chat_members')
        if 'last_read_message_id' in member_columns:
            op.drop_column('chat_members', 'last_read_message_id')
        if 'is_admin' in member_columns:
            op.drop_column('chat_members', 'is_admin')

    if 'messages' in set(sa.inspect(bind).get_table_names()):
        message_columns = _columns(bind, 'messages')
        for column in ('is_deleted', 'edited_at', 'reply_to_id'):
            if column in message_columns:
                op.drop_column('messages', column)

    if 'chats' in set(sa.inspect(bind).get_table_names()):
        chat_columns = _columns(bind, 'chats')
        if 'description' in chat_columns:
            op.drop_column('chats', 'description')
        if 'kind' in chat_columns:
            op.drop_column('chats', 'kind')

    if 'users' in set(sa.inspect(bind).get_table_names()):
        user_columns = _columns(bind, 'users')
        if 'last_seen_at' in user_columns:
            op.drop_column('users', 'last_seen_at')
