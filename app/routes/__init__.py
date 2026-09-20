from flask import Blueprint

from app.routes.chatroom import chat_room
from app.routes.home import home
from app.routes.login_register import login_register
from app.routes.people import people


def Blue_prints() -> list[Blueprint]:
    '''ثبت تمام بلوپرینت‌های برنامه'''
    return [
        home,
        login_register,
        chat_room,
        people
    ]