from app.routes.home import home
from flask import Blueprint

def Blue_prints() -> list[Blueprint]:
    return [
        home
    ]