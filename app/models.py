from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    chats = db.relationship(
        'Chat',
        backref='user',
        cascade='all, delete-orphan'
    )


class Chat(db.Model):
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    messages = db.relationship(
        'Message',
        backref='chat',
        cascade='all, delete-orphan'
    )


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)

    chat_id = db.Column(
        db.Integer,
        db.ForeignKey('chats.id'),
        nullable=False
    )