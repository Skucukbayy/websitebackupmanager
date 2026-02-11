from config import Config
from models import db, User, Site, BackupSchedule, BackupHistory
from backup_manager import get_backup_manager
import scheduler as sched
from translations import TRANSLATIONS
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
from utils import init_encryption, encrypt_password, decrypt_password
from time_utils import get_now_for_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create tables and default admin user
with app.app_context():
    db.create_all()
    # Create default backup directory
    os.makedirs(Config.DEFAULT_BACKUP_PATH, exist_ok=True)
    
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', must_change_password=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        logger.info("Default admin user created (admin/admin)")

# Initialize encryption
init_encryption(app.config['ENCRYPTION_KEY'])

# Initialize scheduler
sched.init_scheduler(app, Config.SQLALCHEMY_DATABASE_URI)

# Valid languages
LANGUAGES = ['tr', 'en']


# ============== Authentication ==============

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if password change is required
        user = User.query.get(session['user_id'])
        if user and user.must_change_password and request.endpoint != 'change_password':
            return redirect(url_for('change_password'))
        
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    """Set language from session or default"""
    if 'lang' not in session:
        # Try to match browser language
        browser_lang = request.accept_languages.best_match(LANGUAGES)
        session['lang'] = browser_lang if browser_lang else 'tr'


@app.context_processor
def inject_lang():
    """Inject language, translation function, and user to templates"""
    lang = session.get('lang', 'tr')
    
    def t(key, **kwargs):
        """Translate function"""
        text = TRANSLATIONS.get(lang, {}).get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
    
    # Get current user
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        
    return dict(lang=lang, t=t, current_lang=lang, current_user=current_user)


@app.route('/set-lang/<lang_code>')
def set_language(lang_code):
    """Switch language"""
    if lang_code in LANGUAGES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))


# ============== Auth Routes ==============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            logger.info(f"User logged in: {username}")
            
            if user.must_change_password:
                return redirect(url_for('change_password'))
            
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error=True)
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(new_password) < 4:
            return render_template('change_password.html', error='password_too_short', must_change=user.must_change_password)
        
        if new_password != confirm_password:
            return render_template('change_password.html', error='password_mismatch', must_change=user.must_change_password)
        
        if new_password == 'admin':
            return render_template('change_password.html', error='password_same_as_default', must_change=user.must_change_password)
        
        user.set_password(new_password)
        user.must_change_password = False
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        return redirect(url_for('index'))
    
    return render_template('change_password.html', must_change=user.must_change_password)


# ============== Page Routes ==============

@app.route('/')
@login_required
def index():
    """Dashboard page"""
    return render_template('index.html')

@app.route('/add-site')
@login_required
def add_site_page():
    """Add site page"""
    return render_template('add_site.html')

@app.route('/edit-site/<int:site_id>')
@login_required
def edit_site_page(site_id):
    """Edit site page"""
    site = Site.query.get_or_404(site_id)
    return render_template('add_site.html', site=site)

# ============== API Routes ==============

@app.route('/api/sites', methods=['GET'])
def get_sites():
    """Get all sites"""
    sites = Site.query.order_by(Site.created_at.desc()).all()
    return jsonify([site.to_dict() for site in sites])

@app.route('/api/sites', methods=['POST'])
def create_site():
    """Create a new site"""
    data = request.json
    
    # Validate required fields
    required = ['name', 'host', 'protocol', 'username', 'remote_path', 'local_backup_path']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create site
    site = Site(
        name=data['name'],
        host=data['host'],
        port=data.get('port', 22 if data['protocol'].upper() == 'SSH' else 21),
        protocol=data['protocol'].upper(),
        username=data['username'],
        password=encrypt_password(data.get('password')),
        ssh_key_path=data.get('ssh_key_path'),
        remote_path=data['remote_path'],
        local_backup_path=data['local_backup_path'],
        is_active=True
    )
    
    db.session.add(site)
    db.session.commit()
    
    # Create schedule if provided
    if data.get('interval_type') and data.get('interval_value'):
        schedule = BackupSchedule(
            site_id=site.id,
            interval_type=data['interval_type'],
            interval_value=int(data['interval_value']),
            is_enabled=True
        )
        db.session.add(schedule)
        db.session.commit()
        
        # Add scheduler job
        sched.add_backup_job(site.id, data['interval_type'], int(data['interval_value']))
    
    return jsonify(site.to_dict()), 201

@app.route('/api/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    """Get a specific site"""
    site = Site.query.get_or_404(site_id)
    return jsonify(site.to_dict())

@app.route('/api/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    """Update a site"""
    site = Site.query.get_or_404(site_id)
    data = request.json
    
    # Update fields
    if 'name' in data:
        site.name = data['name']
    if 'host' in data:
        site.host = data['host']
    if 'port' in data:
        site.port = data['port']
    if 'protocol' in data:
        site.protocol = data['protocol'].upper()
    if 'username' in data:
        site.username = data['username']
    if 'password' in data:
        site.password = encrypt_password(data['password'])
    if 'ssh_key_path' in data:
        site.ssh_key_path = data['ssh_key_path']
    if 'remote_path' in data:
        site.remote_path = data['remote_path']
    if 'local_backup_path' in data:
        site.local_backup_path = data['local_backup_path']
    if 'is_active' in data:
        site.is_active = data['is_active']
    
    # Update schedule
    if data.get('interval_type') and data.get('interval_value'):
        schedule = BackupSchedule.query.filter_by(site_id=site.id).first()
        if schedule:
            schedule.interval_type = data['interval_type']
            schedule.interval_value = int(data['interval_value'])
        else:
            schedule = BackupSchedule(
                site_id=site.id,
                interval_type=data['interval_type'],
                interval_value=int(data['interval_value']),
                is_enabled=True
            )
            db.session.add(schedule)
        
        # Update scheduler job
        sched.add_backup_job(site.id, data['interval_type'], int(data['interval_value']))
    
    db.session.commit()
    return jsonify(site.to_dict())

@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Delete a site"""
    site = Site.query.get_or_404(site_id)
    
    # Remove scheduler job
    sched.remove_backup_job(site_id)
    
    db.session.delete(site)
    db.session.commit()
    
    return jsonify({'message': 'Site deleted successfully'})

@app.route('/api/sites/<int:site_id>/test', methods=['POST'])
def test_connection(site_id):
    """Test connection to a site"""
    site = Site.query.get_or_404(site_id)
    
    try:
        manager = get_backup_manager(
            protocol=site.protocol,
            host=site.host,
            port=site.port,
            username=site.username,
            password=decrypt_password(site.password),
            ssh_key_path=site.ssh_key_path
        )
        
        success, message = manager.test_connection()
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/sites/<int:site_id>/backup', methods=['POST'])
def start_backup(site_id):
    """Start a manual backup"""
    site = Site.query.get_or_404(site_id)
    
    # Create backup history entry
    history = BackupHistory(
        site_id=site.id,
        status='running'
    )
    db.session.add(history)
    db.session.commit()
    
    try:
        manager = get_backup_manager(
            protocol=site.protocol,
            host=site.host,
            port=site.port,
            username=site.username,
            password=decrypt_password(site.password),
            ssh_key_path=site.ssh_key_path
        )
        
        success, result, file_count, total_bytes = manager.backup(
            remote_path=site.remote_path,
            local_backup_path=site.local_backup_path
        )
        
        if success:
            history.status = 'success'
            history.backup_path = result
            history.file_count = file_count
            history.size_bytes = total_bytes
        else:
            history.status = 'failed'
            history.error_message = result
            
        history.completed_at = get_now_for_db()
        
        # Update schedule last_run
        schedule = BackupSchedule.query.filter_by(site_id=site.id).first()
        if schedule:
            schedule.last_run = get_now_for_db()
        
        db.session.commit()
        
        return jsonify(history.to_dict())
        
    except Exception as e:
        history.status = 'failed'
        history.error_message = str(e)
        history.completed_at = get_now_for_db()
        db.session.commit()
        
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/sites/<int:site_id>/history', methods=['GET'])
def get_site_history(site_id):
    """Get backup history for a site"""
    site = Site.query.get_or_404(site_id)
    history = BackupHistory.query.filter_by(site_id=site.id)\
        .order_by(BackupHistory.started_at.desc())\
        .limit(50).all()
    
    return jsonify([h.to_dict() for h in history])

@app.route('/api/backups', methods=['GET'])
def get_all_backups():
    """Get all backup history"""
    history = BackupHistory.query\
        .order_by(BackupHistory.started_at.desc())\
        .limit(100).all()
    
    return jsonify([h.to_dict() for h in history])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics"""
    total_sites = Site.query.count()
    active_sites = Site.query.filter_by(is_active=True).count()
    total_backups = BackupHistory.query.count()
    successful_backups = BackupHistory.query.filter_by(status='success').count()
    failed_backups = BackupHistory.query.filter_by(status='failed').count()
    
    # Total backup size
    total_size = db.session.query(db.func.sum(BackupHistory.size_bytes))\
        .filter_by(status='success').scalar() or 0
    
    return jsonify({
        'total_sites': total_sites,
        'active_sites': active_sites,
        'total_backups': total_backups,
        'successful_backups': successful_backups,
        'failed_backups': failed_backups,
        'total_size_bytes': total_size,
        'total_size_human': format_size(total_size)
    })

@app.route('/api/translations')
def get_translations():
    """Get translations for frontend JS"""
    lang = session.get('lang', 'tr')
    return jsonify(TRANSLATIONS.get(lang, {}))

@app.route('/api/system/browse', methods=['GET'])
def browse_filesystem():
    """Browse directories on the server"""
    try:
        path = request.args.get('path', '')
        
        # Default to current directory if empty
        if not path:
            path = os.getcwd()
            
        if not os.path.exists(path):
            return jsonify({'error': 'Path does not exist'}), 404
            
        if not os.path.isdir(path):
            return jsonify({'error': 'Not a directory'}), 400
            
        # Get directories
        directories = []
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir() and not entry.name.startswith('.'):
                        directories.append(entry.name)
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
            
        directories.sort()
        
        return jsonify({
            'current_path': os.path.abspath(path),
            'parent_path': os.path.dirname(os.path.abspath(path)),
            'directories': directories
        })
    except Exception as e:
        logger.error(f"Browse error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/mkdir', methods=['POST'])
def create_directory():
    """Create a new directory"""
    try:
        data = request.json
        path = data.get('path')
        
        if not path:
            return jsonify({'error': 'Path is required'}), 400
            
        if os.path.exists(path):
            return jsonify({'error': 'Directory already exists'}), 400
            
        try:
            os.makedirs(path)
            return jsonify({'success': True, 'path': path})
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
            
    except Exception as e:
        logger.error(f"Mkdir error: {e}")
        return jsonify({'error': str(e)}), 500

def format_size(size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# ============== Admin Panel ==============

@app.route('/admin')
@login_required
def admin_page():
    """Admin panel page"""
    return render_template('admin.html')


@app.route('/api/admin/change-password', methods=['POST'])
@login_required
def admin_change_password():
    """Change password via admin panel (requires current password)"""
    data = request.json
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Validate current password
    if not user.check_password(current_password):
        return jsonify({'success': False, 'message': 'current_password_wrong'}), 400
    
    # Validate new password
    if len(new_password) < 4:
        return jsonify({'success': False, 'message': 'password_too_short'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'password_mismatch'}), 400
    
    if new_password == 'admin':
        return jsonify({'success': False, 'message': 'password_same_as_default'}), 400
    
    user.set_password(new_password)
    user.must_change_password = False
    db.session.commit()
    
    logger.info(f"Password changed for user: {user.username} via admin panel")
    return jsonify({'success': True, 'message': 'password_changed'})


@app.route('/api/server-time')
@login_required
def get_server_time():
    """Get current server time (NTP-synced)"""
    from time_utils import get_now
    now = get_now()
    return jsonify({
        'time': now.strftime('%d.%m.%Y %H:%M:%S'),
        'iso': now.isoformat()
    })

# Function called by scheduler
def run_scheduled_backup(site_id):
    """Run a scheduled backup (called by APScheduler)"""
    with app.app_context():
        site = Site.query.get(site_id)
        if not site or not site.is_active:
            logger.warning(f"Skipping backup for inactive/deleted site {site_id}")
            return
        
        logger.info(f"Starting scheduled backup for site: {site.name}")
        
        history = BackupHistory(
            site_id=site.id,
            status='running'
        )
        db.session.add(history)
        db.session.commit()
        
        try:
            manager = get_backup_manager(
                protocol=site.protocol,
                host=site.host,
                port=site.port,
                username=site.username,
                password=decrypt_password(site.password),
                ssh_key_path=site.ssh_key_path
            )
            
            success, result, file_count, total_bytes = manager.backup(
                remote_path=site.remote_path,
                local_backup_path=site.local_backup_path
            )
            
            if success:
                history.status = 'success'
                history.backup_path = result
                history.file_count = file_count
                history.size_bytes = total_bytes
                logger.info(f"Backup completed for {site.name}: {file_count} files, {format_size(total_bytes)}")
            else:
                history.status = 'failed'
                history.error_message = result
                logger.error(f"Backup failed for {site.name}: {result}")
                
            history.completed_at = get_now_for_db()
            
            schedule = BackupSchedule.query.filter_by(site_id=site.id).first()
            if schedule:
                schedule.last_run = get_now_for_db()
            
            db.session.commit()
            
        except Exception as e:
            history.status = 'failed'
            history.error_message = str(e)
            history.completed_at = get_now_for_db()
            db.session.commit()
            logger.error(f"Backup error for {site.name}: {e}")


if __name__ == '__main__':
    # Start scheduler
    sched.start_scheduler()
    
    try:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        )
    finally:
        sched.stop_scheduler()
