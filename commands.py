from app.models import User , Chat , Message , ChatMember
import argparse
from flask import Flask
from app.extensions import db

def remove_database():
    users = User.query.all()
    chats = Chat.query.all()
    messages = Message.query.all()
    chat_members = ChatMember.query.all()
    for user in users:
        db.session.delete(user)
    for chat in chats:
        db.session.delete(chat)
    for message in messages:
        db.session.delete(message)
    for chat_member in chat_members:
        db.session.delete(chat_member)


def update_database_from_type_terms(app: Flask)->bool:
    parser = argparse.ArgumentParser()


    parser.add_argument(
        '--remove',
        action='store_true',
        help='Remove database'
    )

    args = parser.parse_args()

    if args.remove:
        with app.app_context():
            remove_database()

        print('Database removed successfully.')
        return True
    return False