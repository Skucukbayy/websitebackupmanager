import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'web-backup-manager-secret-key-2024'
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or b'Z_sCqX2D8XqX2D8XqX2D8XqX2D8XqX2D8XqX2D8XqX2=' # Default dev key, change in prod!
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "backups.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Default backup directory
    DEFAULT_BACKUP_PATH = os.environ.get('BACKUP_PATH') or os.path.join(BASE_DIR, 'backups')
    
    # Application settings
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Scheduler settings
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Europe/Istanbul'
