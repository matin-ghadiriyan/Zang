from app import create_app
from config import setting_run

app = create_app()

if __name__ == '__main__':
    app.run(**setting_run)