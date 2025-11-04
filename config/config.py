import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+mysqlconnector://product_user:product_password123@localhost/product_display'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 50 * 1024 * 1024))
    
    # 允许的文件扩展名
    ALLOWED_IMAGE_EXTENSIONS = set(
        os.environ.get('ALLOWED_IMAGE_EXTENSIONS', 'png,jpg,jpeg,gif,webp').split(',')
    )
    ALLOWED_VIDEO_EXTENSIONS = set(
        os.environ.get('ALLOWED_VIDEO_EXTENSIONS', 'mp4,avi,mov,webm').split(',')
    )
    
    # 应用配置
    PRODUCTS_PER_PAGE = int(os.environ.get('PRODUCTS_PER_PAGE', 10))
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))
    
    # Celery配置
    CELERY = {
        'broker_url': REDIS_URL,
        'result_backend': REDIS_URL,
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'timezone': 'Asia/Shanghai'
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
