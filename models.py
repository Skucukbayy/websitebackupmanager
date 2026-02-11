from datetime import datetime
from time_utils import get_now_for_db
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    must_change_password = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_now_for_db)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Site(db.Model):
    """Website/Server information for backup"""
    __tablename__ = 'sites'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=22)
    protocol = db.Column(db.String(10), nullable=False)  # 'SSH' or 'FTP'
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=True)
    ssh_key_path = db.Column(db.String(500), nullable=True)
    remote_path = db.Column(db.String(500), nullable=False, default='/')
    local_backup_path = db.Column(db.String(500), nullable=False)
    backup_destination = db.Column(db.String(20), default='local')  # local, google_drive, onedrive, dropbox
    cloud_folder_id = db.Column(db.String(500), nullable=True)
    cloud_folder_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=get_now_for_db)
    updated_at = db.Column(db.DateTime, default=get_now_for_db, onupdate=get_now_for_db)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    schedules = db.relationship('BackupSchedule', backref='site', lazy=True, cascade='all, delete-orphan')
    history = db.relationship('BackupHistory', backref='site', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'username': self.username,
            'has_password': bool(self.password),
            'has_ssh_key': bool(self.ssh_key_path),
            'remote_path': self.remote_path,
            'local_backup_path': self.local_backup_path,
            'backup_destination': self.backup_destination or 'local',
            'cloud_folder_id': self.cloud_folder_id,
            'cloud_folder_path': self.cloud_folder_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'schedule': self.schedules[0].to_dict() if self.schedules else None,
            'last_backup': self.get_last_backup()
        }
    
    def get_last_backup(self):
        last = BackupHistory.query.filter_by(site_id=self.id).order_by(BackupHistory.started_at.desc()).first()
        return last.to_dict() if last else None


class BackupSchedule(db.Model):
    """Backup scheduling configuration"""
    __tablename__ = 'backup_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    interval_type = db.Column(db.String(20), nullable=False)  # minutes, hours, days, weeks
    interval_value = db.Column(db.Integer, nullable=False, default=1)
    next_run = db.Column(db.DateTime, nullable=True)
    last_run = db.Column(db.DateTime, nullable=True)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_now_for_db)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'interval_type': self.interval_type,
            'interval_value': self.interval_value,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'is_enabled': self.is_enabled
        }


class BackupHistory(db.Model):
    """Backup execution history"""
    __tablename__ = 'backup_history'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=get_now_for_db)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='running')  # running, success, failed
    size_bytes = db.Column(db.BigInteger, default=0)
    file_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    backup_path = db.Column(db.String(500), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_name': self.site.name if self.site else 'Unknown',
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'size_bytes': self.size_bytes,
            'file_count': self.file_count,
            'error_message': self.error_message,
            'backup_path': self.backup_path,
            'duration': self.format_duration()
        }
    
    def format_duration(self):
        if not self.started_at or not self.completed_at:
            return '-'
        delta = self.completed_at - self.started_at
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"


class CloudCredential(db.Model):
    """Cloud storage OAuth2 credentials"""
    __tablename__ = 'cloud_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(20), unique=True, nullable=False)  # google_drive, onedrive, dropbox
    client_id = db.Column(db.String(500), nullable=True)
    client_secret = db.Column(db.String(500), nullable=True)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    is_connected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_now_for_db)
    updated_at = db.Column(db.DateTime, default=get_now_for_db, onupdate=get_now_for_db)
    
    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'has_client_id': bool(self.client_id),
            'has_client_secret': bool(self.client_secret),
            'is_connected': self.is_connected,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None
        }

