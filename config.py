from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    ''' Config class '''
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class RunningConfig:
    ''' RunningConfig class '''
    DEBUG = os.getenv('DEBUG' , '1') == '1'
    PORT = int(os.getenv('PORT' , '5000'))
    HOST = os.getenv('HOST' , '0.0.0.0')

setting_run = {
    'debug': RunningConfig.DEBUG,
    'port': RunningConfig.PORT,
    'host': RunningConfig.HOST
}