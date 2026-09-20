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

    chats = db.relationship(
        'Chat',
        backref='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def set_password(self, raw_password: str) -> None:
        '''تنظیم رمز عبور به صورت هش شده'''
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        '''بررسی صحت رمز عبور'''
        return check_password_hash(self.password, raw_password)

    def to_dict(self) -> dict:
        '''تبدیل کاربر به دیکشنری'''
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<User {self.username}>'


class Chat(db.Model):
    '''گفتگو'''

    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False, default='گفتگوی جدید')
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
        order_by='Message.created_at'
    )

    members = db.relationship(
        'ChatMember',
        backref='chat',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def has_member(self, user_id: int) -> bool:
        '''بررسی عضویت کاربر در گفتگو'''
        return self.members.filter_by(user_id=user_id).first() is not None

    def to_dict(self, include_messages: bool = False, include_members: bool = False) -> dict:
        '''تبدیل گفتگو به دیکشنری'''
        data = {
            'id': self.id,
            'title': self.title,
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
        return f'<Chat {self.id}>'


class ChatMember(db.Model):
    '''عضو گفتگو (دسترسی با شناسه)'''

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
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('chat_id', 'user_id', name='uq_chat_member'),
    )

    def to_dict(self) -> dict:
        '''تبدیل عضو به دیکشنری'''
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'access_code': self.access_code,
            'is_owner': self.is_owner,
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        '''تبدیل پیام به دیکشنری'''
        return {
            'id': self.id,
            'content': self.content,
            'role': self.role,
            'chat_id': self.chat_id,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f'<Message {self.id}>'
