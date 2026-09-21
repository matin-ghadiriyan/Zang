from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    '''کاربر سیستم'''

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, nullable=True)

    chats = db.relationship(
        'Chat',
        backref='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    messages = db.relationship(
        'Message',
        backref='author',
        foreign_keys='Message.user_id',
        lazy='dynamic'
    )

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None
        }

    def __repr__(self) -> str:
        return f'<User {self.username}>'


class Chat(db.Model):
    '''گفتگو، گروه، کانال یا گفتگوی مستقیم'''

    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False, default='گفتگوی جدید')
    kind = db.Column(db.String(20), nullable=False, default='group', index=True)
    description = db.Column(db.String(280), nullable=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    messages = db.relationship(
        'Message',
        backref='chat',
        cascade='all, delete-orphan',
        lazy='dynamic',
        foreign_keys='Message.chat_id',
        order_by='Message.created_at'
    )

    members = db.relationship(
        'ChatMember',
        backref='chat',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def has_member(self, user_id: int) -> bool:
        return self.members.filter_by(user_id=user_id).first() is not None

    def to_dict(self, include_messages: bool = False, include_members: bool = False) -> dict:
        data = {
            'id': self.id,
            'title': self.title,
            'kind': self.kind,
            'description': self.description,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'messages_count': self.messages.count(),
            'members_count': self.members.count()
        }
        if include_messages:
            data['messages'] = [message.to_dict() for message in self.messages]
        if include_members:
            data['members'] = [member.to_dict() for member in self.members]
        return data

    def __repr__(self) -> str:
        return f'<Chat {self.id} {self.kind}>'


class ChatMember(db.Model):
    '''عضو گفتگو'''

    __tablename__ = 'chat_members'

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(
        db.Integer,
        db.ForeignKey('chats.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    access_code = db.Column(db.String(64), nullable=False, index=True)
    is_owner = db.Column(db.Boolean, nullable=False, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    last_read_message_id = db.Column(db.Integer, nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    member_user = db.relationship('User', foreign_keys=[user_id], lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('chat_id', 'user_id', name='uq_chat_member'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'username': self.member_user.username if self.member_user else None,
            'access_code': self.access_code,
            'is_owner': self.is_owner,
            'is_admin': self.is_admin,
            'last_read_message_id': self.last_read_message_id,
            'joined_at': self.joined_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<ChatMember chat={self.chat_id} user={self.user_id}>'


class Message(db.Model):
    '''پیام'''

    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    chat_id = db.Column(
        db.Integer,
        db.ForeignKey('chats.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    reply_to_id = db.Column(db.Integer, nullable=True, index=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship('User', foreign_keys=[user_id], lazy='joined')
    reply_to = db.relationship(
        'Message',
        primaryjoin='foreign(Message.reply_to_id) == Message.id',
        remote_side='Message.id',
        uselist=False,
        viewonly=True
    )

    def to_dict(self) -> dict:
        reply = None
        if self.reply_to:
            reply = {
                'id': self.reply_to.id,
                'username': self.reply_to.sender.username if self.reply_to.sender else None,
                'content': '' if self.reply_to.is_deleted else self.reply_to.content[:180],
                'is_deleted': self.reply_to.is_deleted
            }

        read_by_count = ChatMember.query.filter(
            ChatMember.chat_id == self.chat_id,
            ChatMember.last_read_message_id.isnot(None),
            ChatMember.last_read_message_id >= self.id
        ).count()

        return {
            'id': self.id,
            'content': '' if self.is_deleted else self.content,
            'role': self.role,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'username': self.sender.username if self.sender else None,
            'reply_to_id': self.reply_to_id,
            'reply_to': reply,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_deleted': self.is_deleted,
            'read_by_count': read_by_count,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<Message {self.id}>'
