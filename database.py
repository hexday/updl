import sqlite3
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from config import config
from logger import logger

class ProfessionalDatabase:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.lock = threading.RLock()
        self.connection_pool = {}
        self.init_database()
        logger.get_logger('database').info("Database initialized successfully")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection for current thread"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self.connection_pool[thread_id] = conn
        
        return self.connection_pool[thread_id]
    
    def init_database(self):
        """Initialize database with all required tables"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Downloads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    original_url TEXT,
                    filename TEXT NOT NULL,
                    filepath TEXT,
                    file_type TEXT DEFAULT 'document',
                    size INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0,
                    speed REAL DEFAULT 0,
                    eta REAL DEFAULT 0,
                    description TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    platform TEXT DEFAULT 'direct',
                    engine TEXT DEFAULT 'requests',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    telegram_file_id TEXT,
                    telegram_message_id INTEGER,
                    telegram_file_unique_id TEXT,
                    share_link TEXT,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}',
                    quality TEXT DEFAULT 'best',
                    extract_audio BOOLEAN DEFAULT 0
                )
            ''')
            
            # Uploads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uploads (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    file_type TEXT DEFAULT 'document',
                    size INTEGER NOT NULL,
                    description TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    uploaded_at TEXT,
                    telegram_file_id TEXT,
                    telegram_message_id INTEGER,
                    telegram_file_unique_id TEXT,
                    share_link TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # Download engines performance tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engine_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine TEXT NOT NULL,
                    url TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    duration REAL,
                    file_size INTEGER,
                    error_message TEXT,
                    timestamp TEXT
                )
            ''')
            
            # User sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_agent TEXT,
                    ip_address TEXT,
                    created_at TEXT,
                    last_activity TEXT,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            
            # System settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT
                )
            ''')
            
            # Telegram upload queue
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telegram_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    priority INTEGER DEFAULT 0,
                    created_at TEXT,
                    processing BOOLEAN DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    last_attempt TEXT,
                    error_message TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_uploads_uploaded ON uploads(uploaded_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_engine_stats_engine ON engine_stats(engine)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_telegram_queue_processing ON telegram_queue(processing)')
            
            conn.commit()
            logger.log_database_operation("CREATE", "all_tables", "initial_setup")
    
    def execute_query(self, query: str, params: tuple = (), fetch: bool = False) -> List[Dict]:
        """Execute database query safely"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute(query, params)
                
                if fetch or query.strip().upper().startswith('SELECT'):
                    results = [dict(row) for row in cursor.fetchall()]
                else:
                    conn.commit()
                    results = []
                
                return results
                
            except Exception as e:
                conn.rollback()
                logger.get_logger('error').error(f"Database query error: {e} | Query: {query[:100]}")
                return []
    
    def save_download(self, data: Dict):
        """Save download data"""
        query = '''
            INSERT OR REPLACE INTO downloads 
            (id, url, original_url, filename, filepath, file_type, size, downloaded, status, 
             progress, speed, eta, description, tags, platform, engine, retry_count, max_retries,
             created_at, started_at, finished_at, telegram_file_id, telegram_message_id, 
             telegram_file_unique_id, share_link, error_message, metadata, quality, extract_audio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            data.get('id'), data.get('url'), data.get('original_url'),
            data.get('filename'), data.get('filepath'), data.get('file_type', 'document'),
            data.get('size', 0), data.get('downloaded', 0), data.get('status', 'pending'),
            data.get('progress', 0), data.get('speed', 0), data.get('eta', 0),
            data.get('description', ''), data.get('tags', ''), data.get('platform', 'direct'),
            data.get('engine', 'requests'), data.get('retry_count', 0), data.get('max_retries', 3),
            data.get('created_at'), data.get('started_at'), data.get('finished_at'),
            data.get('telegram_file_id'), data.get('telegram_message_id'),
            data.get('telegram_file_unique_id'), data.get('share_link'),
            data.get('error_message'), json.dumps(data.get('metadata', {})),
            data.get('quality', 'best'), data.get('extract_audio', False)
        )
        
        self.execute_query(query, params)
        logger.log_database_operation("SAVE", "downloads", data.get('id', 'unknown'))
    
    def save_upload(self, data: Dict):
        """Save upload data"""
        query = '''
            INSERT OR REPLACE INTO uploads 
            (id, original_filename, filepath, file_type, size, description, tags, uploaded_at,
             telegram_file_id, telegram_message_id, telegram_file_unique_id, share_link, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            data.get('id'), data.get('original_filename'), data.get('filepath'),
            data.get('file_type', 'document'), data.get('size'),
            data.get('description', ''), data.get('tags', ''), data.get('uploaded_at'),
            data.get('telegram_file_id'), data.get('telegram_message_id'),
            data.get('telegram_file_unique_id'), data.get('share_link'),
            json.dumps(data.get('metadata', {}))
        )
        
        self.execute_query(query, params)
        logger.log_database_operation("SAVE", "uploads", data.get('id', 'unknown'))
    
    def get_downloads(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get downloads with optional status filter"""
        if status:
            query = 'SELECT * FROM downloads WHERE status = ? ORDER BY created_at DESC LIMIT ?'
            params = (status, limit)
        else:
            query = 'SELECT * FROM downloads ORDER BY created_at DESC LIMIT ?'
            params = (limit,)
        
        results = self.execute_query(query, params, fetch=True)
        
        # Parse metadata JSON
        for result in results:
            try:
                result['metadata'] = json.loads(result.get('metadata', '{}'))
            except:
                result['metadata'] = {}
        
        return results
    
    def get_uploads(self, limit: int = 100) -> List[Dict]:
        """Get uploads"""
        query = 'SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT ?'
        results = self.execute_query(query, (limit,), fetch=True)
        
        # Parse metadata JSON
        for result in results:
            try:
                result['metadata'] = json.loads(result.get('metadata', '{}'))
            except:
                result['metadata'] = {}
        
        return results
    
    def get_download(self, download_id: str) -> Optional[Dict]:
        """Get single download"""
        results = self.execute_query(
            'SELECT * FROM downloads WHERE id = ?', 
            (download_id,), 
            fetch=True
        )
        
        if results:
            result = results[0]
            try:
                result['metadata'] = json.loads(result.get('metadata', '{}'))
            except:
                result['metadata'] = {}
            return result
        
        return None
    
    def get_upload(self, upload_id: str) -> Optional[Dict]:
        """Get single upload"""
        results = self.execute_query(
            'SELECT * FROM uploads WHERE id = ?', 
            (upload_id,), 
            fetch=True
        )
        
        if results:
            result = results[0]
            try:
                result['metadata'] = json.loads(result.get('metadata', '{}'))
            except:
                result['metadata'] = {}
            return result
        
        return None
    
    def delete_download(self, download_id: str):
        """Delete download"""
        self.execute_query('DELETE FROM downloads WHERE id = ?', (download_id,))
        logger.log_database_operation("DELETE", "downloads", download_id)
    
    def delete_upload(self, upload_id: str):
        """Delete upload"""
        self.execute_query('DELETE FROM uploads WHERE id = ?', (upload_id,))
        logger.log_database_operation("DELETE", "uploads", upload_id)
    
    def save_engine_stats(self, engine: str, url: str, success: bool, 
                         duration: float, file_size: int = 0, error: str = None):
        """Save engine performance statistics"""
        query = '''
            INSERT INTO engine_stats 
            (engine, url, success, duration, file_size, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            engine, url[:500], success, duration, file_size, 
            error[:1000] if error else None, datetime.now().isoformat()
        )
        
        self.execute_query(query, params)
    
    def get_engine_performance(self) -> Dict:
        """Get engine performance statistics"""
        query = '''
            SELECT 
                engine,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(duration) as avg_duration,
                AVG(file_size) as avg_file_size
            FROM engine_stats 
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY engine
            ORDER BY successful DESC, avg_duration ASC
        '''
        
        results = self.execute_query(query, fetch=True)
        
        performance = {}
        for result in results:
            success_rate = (result['successful'] / result['total_attempts']) * 100
            performance[result['engine']] = {
                'success_rate': success_rate,
                'avg_duration': result['avg_duration'] or 0,
                'avg_file_size': result['avg_file_size'] or 0,
                'total_attempts': result['total_attempts']
            }
        
        return performance
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        stats = {}
        
        # Download stats
        download_stats = self.execute_query('''
            SELECT 
                status,
                COUNT(*) as count,
                SUM(size) as total_size,
                AVG(speed) as avg_speed
            FROM downloads 
            GROUP BY status
        ''', fetch=True)
        
        stats['downloads'] = {
            row['status']: {
                'count': row['count'],
                'total_size': row['total_size'] or 0,
                'avg_speed': row['avg_speed'] or 0
            }
            for row in download_stats
        }
        
        # Upload stats
        upload_count = self.execute_query(
            'SELECT COUNT(*) as count, SUM(size) as total_size FROM uploads',
            fetch=True
        )
        
        if upload_count:
            stats['uploads'] = {
                'count': upload_count[0]['count'],
                'total_size': upload_count['total_size'] or 0
            }
        
        # Engine performance
        stats['engine_performance'] = self.get_engine_performance()
        
        return stats
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records"""
        cutoff_date = datetime.now().replace(
            day=datetime.now().day - days
        ).isoformat()
        
        # Clean up completed downloads older than specified days
        self.execute_query(
            "DELETE FROM downloads WHERE status = 'completed' AND finished_at < ?",
            (cutoff_date,)
        )
        
        # Clean up old engine stats
        self.execute_query(
            "DELETE FROM engine_stats WHERE timestamp < ?",
            (cutoff_date,)
        )
        
        # Clean up inactive sessions
        self.execute_query(
            "DELETE FROM sessions WHERE last_activity < ? AND active = 0",
            (cutoff_date,)
        )
        
        logger.get_logger('database').info(f"Cleaned up records older than {days} days")

# Global database instance
db = ProfessionalDatabase()
