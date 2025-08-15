from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import hashlib
import time
from datetime import datetime
from pathlib import Path
import zipfile
import io

from config import config
from database import db
from downloader import downloader
from telegram_bot import telegram_bot
from file_manager import file_manager
from logger import logger
from web_interface import login_required

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/download', methods=['POST'])
@login_required
def start_download():
    """Start a new download"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        url = data.get('url', '').strip()
        description = data.get('description', '').strip()
        tags = data.get('tags', '').strip()
        quality = data.get('quality', 'best')
        extract_audio = data.get('extract_audio', False)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            return jsonify({'success': False, 'error': 'Invalid URL format'})
        
        logger.get_logger('main').info(f"Starting download: {url}")
        
        download_id, error = downloader.start_download(url, description, tags, quality, extract_audio)
        
        if error:
            logger.get_logger('error').error(f"Download start failed: {error}")
            return jsonify({'success': False, 'error': error})
        
        logger.get_logger('main').info(f"Download started successfully: {download_id}")
        return jsonify({'success': True, 'id': download_id})
        
    except Exception as e:
        logger.get_logger('error').error(f"API download error: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@api.route('/download/control', methods=['POST'])
@login_required
def control_download():
    """Control download (pause, resume, cancel)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        download_id = data.get('id')
        action = data.get('action')
        
        if not download_id or not action:
            return jsonify({'success': False, 'error': 'Missing parameters'})
        
        logger.get_logger('main').info(f"Download control: {action} -> {download_id}")
        
        if action == 'pause':
            downloader.pause_download(download_id)
        elif action == 'resume':
            success = downloader.resume_download(download_id)
            if not success:
                return jsonify({'success': False, 'error': 'Failed to resume download'})
        elif action in ['cancel', 'remove']:
            downloader.cancel_download(download_id)
        else:
            return jsonify({'success': False, 'error': 'Invalid action'})
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.get_logger('error').error(f"Download control error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/download/pause-all', methods=['POST'])
@login_required
def pause_all_downloads():
    """Pause all active downloads"""
    try:
        count = 0
        for dl_id, dl_data in downloader.downloads.items():
            if dl_data.get('status') == 'downloading':
                downloader.pause_download(dl_id)
                count += 1
        
        logger.get_logger('main').info(f"Paused {count} downloads")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Pause all error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/download/clear-completed', methods=['POST'])
@login_required
def clear_completed_downloads():
    """Clear all completed downloads"""
    try:
        count = downloader.cleanup_completed()
        logger.get_logger('main').info(f"Cleared {count} completed downloads")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Clear completed error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """Upload files to server and queue for Telegram"""
    try:
        files = request.files.getlist('files')
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        
        if not files or not files[0].filename:
            return jsonify({'success': False, 'error': 'No files selected'})
        
        logger.get_logger('main').info(f"Upload request: {len(files)} files")
        
        uploaded_count = 0
        
        for file in files:
            if file and file.filename:
                try:
                    # Get file size
                    file.seek(0, 2)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > config.TELEGRAM.max_file_size:
                        logger.get_logger('main').warning(f"File too large: {file.filename} ({file_size} bytes)")
                        continue
                    
                    # Secure filename
                    filename = secure_filename(file.filename)
                    if not filename:
                        filename = f"upload_{int(time.time())}.bin"
                    
                    # Generate unique ID and path
                    upload_id = hashlib.md5(f"{filename}{time.time()}".encode()).hexdigest()[:16]
                    filepath = config.UPLOADS_DIR / f"{upload_id}_{filename}"
                    
                    # Save file
                    file.save(str(filepath))
                    actual_size = filepath.stat().st_size
                    
                    # Analyze file
                    analysis = file_manager.analyze_file(str(filepath))
                    
                    # Save to database
                    upload_data = {
                        'id': upload_id,
                        'original_filename': filename,
                        'filepath': str(filepath),
                        'file_type': config.detect_file_type(filename),
                        'size': actual_size,
                        'description': description,
                        'tags': tags,
                        'uploaded_at': datetime.now().isoformat(),
                        'metadata': analysis
                    }
                    
                    db.save_upload(upload_data)
                    
                    # Queue for Telegram upload with priority
                    priority = 2 if upload_data['file_type'] in ['video', 'audio'] else 1
                    telegram_bot.queue_upload(str(filepath), upload_id, 'upload', description, tags, priority)
                    
                    uploaded_count += 1
                    logger.get_logger('main').info(f"File uploaded: {filename} ({actual_size} bytes)")
                    
                except Exception as e:
                    logger.get_logger('error').error(f"Failed to upload {file.filename}: {e}")
                    continue
        
        return jsonify({'success': True, 'count': uploaded_count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': f'Upload failed: {str(e)}'})

@api.route('/upload/control', methods=['POST'])
@login_required
def control_upload():
    """Control upload (remove)"""
    try:
        data = request.get_json()
        upload_id = data.get('id')
        action = data.get('action')
        
        if action == 'remove':
            upload_data = db.get_upload(upload_id)
            if upload_data:
                filepath = Path(upload_data['filepath'])
                if filepath.exists():
                    try:
                        filepath.unlink()
                        logger.get_logger('main').info(f"Removed upload file: {filepath}")
                    except Exception as e:
                        logger.get_logger('error').error(f"Failed to remove file: {e}")
                
                db.delete_upload(upload_id)
                logger.get_logger('main').info(f"Upload removed: {upload_id}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.get_logger('error').error(f"Upload control error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/files')
@login_required
def get_files():
    """Get all files (downloads + uploads)"""
    try:
        downloads = [dict(d, type='download') for d in db.get_downloads() if d.get('status') == 'completed']
        uploads = [dict(u, type='upload') for u in db.get_uploads()]
        
        all_files = downloads + uploads
        all_files.sort(key=lambda x: x.get('finished_at') or x.get('uploaded_at') or '', reverse=True)
        
        return jsonify({'files': all_files})
        
    except Exception as e:
        logger.get_logger('error').error(f"Files fetch error: {e}")
        return jsonify({'files': []})

@api.route('/recent-activity')
@login_required
def get_recent_activity():
    """Get recent activity"""
    try:
        activities = []
        
        # Get recent downloads
        recent_downloads = db.get_downloads(limit=10)
        for download in recent_downloads:
            if download.get('finished_at'):
                activities.append({
                    'type': 'complete' if download['status'] == 'completed' else 'error',
                    'description': f"Downloaded: {download['filename']}",
                    'timestamp': download['finished_at']
                })
        
        # Get recent uploads
        recent_uploads = db.get_uploads(limit=5)
        for upload in recent_uploads:
            activities.append({
                'type': 'upload',
                'description': f"Uploaded: {upload['original_filename']}",
                'timestamp': upload['uploaded_at']
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        return jsonify(activities[:15])  # Return last 15 activities
        
    except Exception as e:
        logger.get_logger('error').error(f"Recent activity error: {e}")
        return jsonify([])

@api.route('/engine-performance')
@login_required
def get_engine_performance():
    """Get engine performance statistics"""
    try:
        performance = db.get_engine_performance()
        return jsonify(performance)
        
    except Exception as e:
        logger.get_logger('error').error(f"Engine performance error: {e}")
        return jsonify({})

@api.route('/analytics/stats')
@login_required
def get_analytics_stats():
    """Get comprehensive analytics statistics"""
    try:
        stats = db.get_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.get_logger('error').error(f"Analytics stats error: {e}")
        return jsonify({})

@api.route('/analytics/storage')
@login_required
def get_storage_info():
    """Get storage information"""
    try:
        storage_info = file_manager.get_storage_info()
        return jsonify(storage_info)
        
    except Exception as e:
        logger.get_logger('error').error(f"Storage info error: {e}")
        return jsonify({})

@api.route('/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    """Get or update settings"""
    if request.method == 'POST':
        try:
            settings = request.get_json()
            
            # Update configuration
            if 'maxConcurrent' in settings:
                config.SERVER.max_workers = int(settings['maxConcurrent'])
            
            if 'telegramToken' in settings and settings['telegramToken']:
                config.TELEGRAM.bot_token = settings['telegramToken']
            
            if 'telegramChannel' in settings and settings['telegramChannel']:
                config.TELEGRAM.channel_id = int(settings['telegramChannel'])
            
            # Save configuration
            config.save_config()
            
            logger.get_logger('main').info("Settings updated successfully")
            return jsonify({'success': True})
            
        except Exception as e:
            logger.get_logger('error').error(f"Settings update error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    else:
        # Return current settings
        try:
            return jsonify({
                'maxConcurrent': config.SERVER.max_workers,
                'telegramToken': config.TELEGRAM.bot_token[:10] + '...' if config.TELEGRAM.bot_token != "YOUR_BOT_TOKEN_HERE" else '',
                'telegramChannel': config.TELEGRAM.channel_id,
                'autoTelegramUpload': True  # This would be from actual config
            })
        except Exception as e:
            logger.get_logger('error').error(f"Settings fetch error: {e}")
            return jsonify({})

@api.route('/maintenance/cleanup', methods=['POST'])
@login_required
def cleanup_files():
    """Clean up temporary files"""
    try:
        count = file_manager.cleanup_temp_files()
        logger.get_logger('main').info(f"Cleaned up {count} temporary files")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Cleanup error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/maintenance/clear-database', methods=['POST'])
@login_required
def clear_database():
    """Clear old database records"""
    try:
        db.cleanup_old_records(days=7)  # Clean records older than 7 days
        logger.get_logger('main').info("Database cleanup completed")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.get_logger('error').error(f"Database cleanup error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/maintenance/export-logs')
@login_required
def export_logs():
    """Export log files as ZIP"""
    try:
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for log_file in config.LOGS_DIR.glob('*.log'):
                if log_file.exists():
                    zf.write(log_file, log_file.name)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        logger.get_logger('error').error(f"Export logs error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/open-folder', methods=['POST'])
@login_required
def open_downloads_folder():
    """Open downloads folder in file explorer"""
    try:
        import subprocess
        import platform
        
        folder_path = str(config.DOWNLOADS_DIR)
        system = platform.system()
        
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":
            subprocess.run(["open", folder_path])
        else:
            subprocess.run(["xdg-open", folder_path])
        
        logger.get_logger('main').info(f"Opened downloads folder: {folder_path}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.get_logger('error').error(f"Failed to open folder: {e}")
        return jsonify({'success': False, 'error': str(e)})

@api.route('/telegram/status')
@login_required
def get_telegram_status():
    """Get Telegram bot status"""
    try:
        status = telegram_bot.get_queue_status()
        return jsonify(status)
        
    except Exception as e:
        logger.get_logger('error').error(f"Telegram status error: {e}")
        return jsonify({'bot_available': False, 'queue_length': 0})

@api.route('/telegram/clear-queue', methods=['POST'])
@login_required
def clear_telegram_queue():
    """Clear Telegram upload queue"""
    try:
        count = telegram_bot.clear_queue()
        logger.get_logger('main').info(f"Cleared {count} items from Telegram queue")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.get_logger('error').error(f"Clear queue error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Error handlers
@api.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large'}), 413

@api.errorhandler(400)
def bad_request(e):
    return jsonify({'success': False, 'error': 'Bad request'}), 400

@api.errorhandler(500)
def internal_error(e):
    logger.get_logger('error').error(f"Internal server error: {e}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
