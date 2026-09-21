from flask import Blueprint

from app.routes.account import account
from app.routes.chatroom import chat_room
from app.routes.home import home
from app.routes.login_register import login_register


def Blue_prints() -> list[Blueprint]:
    '''ثبت تمام بلوپرینت‌های برنامه'''
    return [
        home,
        login_register,
        chat_room,
        account
    ]