import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import config

class ProfessionalLogger:
    def __init__(self):
        self.loggers = {}
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup different loggers for different components"""
        log_format = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Main application logger
        self._create_logger('main', log_format, 'main.log')
        
        # Download engine logger
        self._create_logger('downloader', log_format, 'downloader.log')
        
        # Telegram bot logger
        self._create_logger('telegram', log_format, 'telegram.log')
        
        # Database logger
        self._create_logger('database', log_format, 'database.log')
        
        # Error logger (only errors)
        self._create_logger('error', log_format, 'errors.log', level=logging.ERROR)
    
    def _create_logger(self, name: str, formatter: logging.Formatter, 
                      filename: str, level: int = logging.INFO):
        """Create a logger with file and console handlers"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(
            config.LOGS_DIR / filename, 
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
        
        # Console handler (only for main logger)
        if name == 'main':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            logger.addHandler(console_handler)
        
        self.loggers[name] = logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get logger by name"""
        return self.loggers.get(name, self.loggers['main'])
    
    def log_download_start(self, url: str, engine: str, download_id: str):
        """Log download start"""
        self.get_logger('downloader').info(
            f"🚀 Starting download | ID: {download_id} | Engine: {engine} | URL: {url[:100]}..."
        )
    
    def log_download_progress(self, download_id: str, progress: float, speed: float):
        """Log download progress"""
        self.get_logger('downloader').info(
            f"📊 Progress | ID: {download_id} | {progress:.1f}% | {speed/1024:.1f} KB/s"
        )
    
    def log_download_complete(self, download_id: str, filename: str, size: int):
        """Log download completion"""
        self.get_logger('downloader').info(
            f"✅ Download complete | ID: {download_id} | File: {filename} | Size: {size:,} bytes"
        )
    
    def log_download_error(self, download_id: str, engine: str, error: str):
        """Log download error"""
        self.get_logger('error').error(
            f"❌ Download failed | ID: {download_id} | Engine: {engine} | Error: {error}"
        )
    
    def log_telegram_upload(self, filename: str, file_size: int, upload_type: str):
        """Log Telegram upload"""
        self.get_logger('telegram').info(
            f"📤 Telegram upload | File: {filename} | Size: {file_size:,} bytes | Type: {upload_type}"
        )
    
    def log_telegram_error(self, filename: str, error: str):
        """Log Telegram error"""
        self.get_logger('error').error(
            f"❌ Telegram upload failed | File: {filename} | Error: {error}"
        )
    
    def log_database_operation(self, operation: str, table: str, record_id: str):
        """Log database operation"""
        self.get_logger('database').info(
            f"💾 Database {operation} | Table: {table} | ID: {record_id}"
        )

# Global logger instance
logger = ProfessionalLogger()
