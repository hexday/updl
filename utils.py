#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ Advanced Utility Functions and Helpers
🚀 High-Performance, Type-Safe, Enterprise-Grade Utilities
"""

import os
import re
import json
import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from urllib.parse import urlparse, unquote, quote
import mimetypes
from pathlib import Path
import unicodedata
import aiofiles
import aiohttp
from cryptography.fernet import Fernet
from loguru import logger
import humanize
import jdatetime
from functools import wraps
import time
from collections import defaultdict, deque
import asyncio
import weakref

from config import config, security

class PerformanceMonitor:
    """Performance monitoring and profiling"""
    
    def __init__(self, max_history: int = 1000):
        self.call_times = defaultdict(deque)
        self.max_history = max_history
    
    def record_call(self, func_name: str, duration: float):
        """Record function call time"""
        self.call_times[func_name].append(duration)
        if len(self.call_times[func_name]) > self.max_history:
            self.call_times[func_name].popleft()
    
    def get_stats(self, func_name: str) -> Dict[str, float]:
        """Get performance statistics for function"""
        times = list(self.call_times[func_name])
        if not times:
            return {}
        
        return {
            'count': len(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'total': sum(times)
        }

# Global performance monitor
perf_monitor = PerformanceMonitor()

def performance_tracked(func: Callable) -> Callable:
    """Decorator to track function performance"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            perf_monitor.record_call(func.__name__, duration)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            perf_monitor.record_call(func.__name__, duration)
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self, max_calls: int, time_window: int, strategy: str = "sliding"):
        self.max_calls = max_calls
        self.time_window = time_window
        self.strategy = strategy
        self.calls = defaultdict(deque)
        self.call_counts = defaultdict(int)
        self.last_reset = defaultdict(float)
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        
        if self.strategy == "sliding":
            return self._sliding_window(key, now)
        elif self.strategy == "fixed":
            return self._fixed_window(key, now)
        else:
            return self._token_bucket(key, now)
    
    def _sliding_window(self, key: str, now: float) -> bool:
        """Sliding window rate limiting"""
        calls = self.calls[key]
        
        # Remove old calls
        while calls and calls[0] <= now - self.time_window:
            calls.popleft()
        
        if len(calls) < self.max_calls:
            calls.append(now)
            return True
        return False
    
    def _fixed_window(self, key: str, now: float) -> bool:
        """Fixed window rate limiting"""
        if now - self.last_reset[key] >= self.time_window:
            self.call_counts[key] = 0
            self.last_reset[key] = now
        
        if self.call_counts[key] < self.max_calls:
            self.call_counts[key] += 1
            return True
        return False
    
    def _token_bucket(self, key: str, now: float) -> bool:
        """Token bucket rate limiting"""
        if key not in self.last_reset:
            self.call_counts[key] = self.max_calls
            self.last_reset[key] = now
        
        # Add tokens based on time passed
        elapsed = now - self.last_reset[key]
        tokens_to_add = int(elapsed * self.max_calls / self.time_window)
        
        if tokens_to_add > 0:
            self.call_counts[key] = min(
                self.max_calls, 
                self.call_counts[key] + tokens_to_add
            )
            self.last_reset[key] = now
        
        if self.call_counts[key] > 0:
            self.call_counts[key] -= 1
            return True
        return False

class SmartCache:
    """Advanced caching with TTL, LRU, and compression"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.ttls = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() > self.ttls.get(key, 0):
                    await self._remove(key)
                    return None
                
                # Update access time
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            now = time.time()
            
            # Check if we need to evict
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = now
            self.ttls[key] = now + (ttl or self.default_ttl)
    
    async def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        await self._remove(lru_key)
    
    async def _remove(self, key: str):
        """Remove item from cache"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.ttls.pop(key, None)
    
    async def clear(self):
        """Clear all cache"""
        async with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.ttls.clear()

class TextProcessor:
    """Advanced text processing utilities"""
    
    PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
    ENGLISH_DIGITS = '0123456789'
    ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'
    
    @staticmethod
    def normalize_persian(text: str) -> str:
        """Normalize Persian text"""
        if not text:
            return ""
        
        # Convert Arabic digits to Persian
        for i, arabic in enumerate(TextProcessor.ARABIC_DIGITS):
            text = text.replace(arabic, TextProcessor.PERSIAN_DIGITS[i])
        
        # Convert English digits to Persian
        for i, english in enumerate(TextProcessor.ENGLISH_DIGITS):
            text = text.replace(english, TextProcessor.PERSIAN_DIGITS[i])
        
        # Fix spacing
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize characters
        text = unicodedata.normalize('NFKC', text)
        
        return text
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text using advanced regex"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|'
            r'(?:(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)',
            re.IGNORECASE
        )
        
        urls = url_pattern.findall(text)
        
        # Add protocol if missing
        normalized_urls = []
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            normalized_urls.append(url)
        
        return normalized_urls
    
    @staticmethod
    @performance_tracked
    def clean_filename(filename: str, max_length: int = 100) -> str:
        """Clean filename for safe filesystem use"""
        # Remove dangerous characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32)
        
        # Normalize spaces
        cleaned = ' '.join(cleaned.split())
        
        # Limit length
        if len(cleaned) > max_length:
            name, ext = os.path.splitext(cleaned)
            max_name_len = max_length - len(ext)
            cleaned = name[:max_name_len] + ext
        
        return cleaned.strip() or f"file_{secrets.token_hex(4)}"
    
    @staticmethod
    def truncate_smart(text: str, max_length: int = 100, 
                      suffix: str = "...") -> str:
        """Smart text truncation preserving word boundaries"""
        if len(text) <= max_length:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.7:  # If we don't lose too much
            truncated = truncated[:last_space]
        
        return truncated.rstrip() + suffix
    
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        """Escape text for Telegram MarkdownV2"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def create_progress_bar(current: int, total: int, length: int = 20, 
                          filled: str = "█", empty: str = "░") -> str:
        """Create visual progress bar"""
        if total == 0:
            return filled * length
        
        filled_length = int(length * current / total)
        bar = filled * filled_length + empty * (length - filled_length)
        percentage = round(100.0 * current / total, 1)
        
        return f"{bar} {percentage}%"

class FileManager:
    """Advanced file management utilities"""
    
    @staticmethod
    async def ensure_directory(path: Union[str, Path]) -> bool:
        """Ensure directory exists asynchronously"""
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    @staticmethod
    @performance_tracked
    async def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get comprehensive file information"""
        path = Path(file_path)
        
        if not path.exists():
            return {}
        
        try:
            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))
            
            return {
                'name': path.name,
                'size': stat.st_size,
                'size_human': FileManager.bytes_to_human(stat.st_size),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'extension': path.suffix.lower(),
                'mime_type': mime_type,
                'is_media': FileManager.is_media_file(path),
                'is_safe': security.is_safe_filename(path.name)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            return {}
    
    @staticmethod
    def bytes_to_human(size_bytes: int, decimal_places: int = 1) -> str:
        """Convert bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.{decimal_places}f} {size_names[i]}"
    
    @staticmethod
    def is_media_file(file_path: Union[str, Path]) -> bool:
        """Check if file is a media file"""
        ext = Path(file_path).suffix.lower()
        
        all_media_extensions = []
        for category in security.ALLOWED_EXTENSIONS.values():
            all_media_extensions.extend(category)
        
        return ext in all_media_extensions
    
    @staticmethod
    async def safe_copy(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """Safely copy file asynchronously"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            # Ensure destination directory exists
            await FileManager.ensure_directory(dst_path.parent)
            
            # Copy file
            async with aiofiles.open(src_path, 'rb') as src_file:
                async with aiofiles.open(dst_path, 'wb') as dst_file:
                    while chunk := await src_file.read(8192):
                        await dst_file.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False
    
    @staticmethod
    @performance_tracked
    async def cleanup_old_files(directory: Union[str, Path], 
                               max_age_hours: int = 24,
                               pattern: str = "*") -> int:
        """Clean up old files asynchronously"""
        try:
            path = Path(directory)
            if not path.exists():
                return 0
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
            
            logger.info(f"🧹 Cleaned {cleaned_count} old files from {directory}")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning files: {e}")
            return 0

class SecurityManager:
    """Advanced security utilities"""
    
    def __init__(self):
        self.encryption_key = config.encryption_key
        self.cipher_suite = None
        
        if self.encryption_key:
            try:
                self.cipher_suite = Fernet(self.encryption_key.encode()[:32].ljust(32, b'0'))
            except Exception as e:
                logger.warning(f"Failed to initialize encryption: {e}")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.cipher_suite:
            return data
        
        try:
            encrypted = self.cipher_suite.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.cipher_suite:
            return encrypted_data
        
        try:
            decrypted = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def verify_signature(data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        try:
            expected = hmac.new(
                secret.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception:
            return False
    
    @staticmethod
    def sanitize_input(user_input: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        if not user_input:
            return ""
        
        # Limit length
        if len(user_input) > max_length:
            user_input = user_input[:max_length]
        
        # Remove control characters
        sanitized = ''.join(
            char for char in user_input 
            if unicodedata.category(char)[0] != 'C' or char in '\n\r\t'
        )
        
        return sanitized.strip()

class DateTimeManager:
    """Advanced date/time utilities with Persian support"""
    
    @staticmethod
    def to_persian_datetime(dt: datetime) -> str:
        """Convert datetime to Persian format"""
        try:
            persian_dt = jdatetime.datetime.fromgregorian(datetime=dt)
            return persian_dt.strftime('%Y/%m/%d - %H:%M:%S')
        except Exception:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def time_ago_persian(dt: datetime) -> str:
        """Get time ago in Persian"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return "دیروز"
            elif diff.days < 7:
                return f"{diff.days} روز پیش"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} هفته پیش"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} ماه پیش"
            else:
                years = diff.days // 365
                return f"{years} سال پیش"
        
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} ساعت پیش"
        
        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes} دقیقه پیش"
        
        return "همین الان"
    
    @staticmethod
    def duration_to_text(seconds: int) -> str:
        """Convert seconds to readable duration"""
        if seconds < 60:
            return f"{seconds} ثانیه"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes} دقیقه و {remaining_seconds} ثانیه"
            return f"{minutes} دقیقه"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours} ساعت و {remaining_minutes} دقیقه"
            return f"{hours} ساعت"

class NetworkManager:
    """Advanced networking utilities"""
    
    def __init__(self):
        self.session = None
        self._timeout = aiohttp.ClientTimeout(total=config.request_timeout)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=self._timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; AdvancedBot/2.0)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @performance_tracked
    async def fetch_with_retry(self, url: str, max_retries: int = 3,
                              backoff_factor: float = 1.0) -> Optional[Dict[str, Any]]:
        """Fetch URL with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        return {
                            'status': response.status,
                            'content': content,
                            'headers': dict(response.headers),
                            'url': str(response.url)
                        }
                    else:
                        raise aiohttp.ClientError(f"HTTP {response.status}")
                        
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}: {e}")
        
        logger.error(f"Failed to fetch {url} after {max_retries} attempts: {last_exception}")
        return None

class FormattingUtils:
    """Advanced formatting utilities"""
    
    @staticmethod
    def format_number_persian(number: Union[int, float], 
                            use_separators: bool = True) -> str:
        """Format number with Persian digits and separators"""
        if use_separators:
            formatted = f"{number:,}"
        else:
            formatted = str(number)
        
        # Convert to Persian digits
        for i, digit in enumerate(TextProcessor.ENGLISH_DIGITS):
            formatted = formatted.replace(digit, TextProcessor.PERSIAN_DIGITS[i])
        
        return formatted
    
    @staticmethod
    def create_info_card(title: str, data: Dict[str, Any], 
                        icon: str = "📊") -> str:
        """Create formatted info card"""
        lines = [f"{icon} **{title}**", ""]
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                value = FormattingUtils.format_number_persian(value)
            lines.append(f"• **{key}:** `{value}`")
        
        return "\n".join(lines)
    
    @staticmethod
    def create_table(headers: List[str], rows: List[List[str]], 
                    max_width: int = 30) -> str:
        """Create formatted table"""
        if not rows:
            return "جدول خالی"
        
        # Calculate column widths
        col_widths = []
        for i, header in enumerate(headers):
            max_width_col = len(header)
            for row in rows:
                if i < len(row):
                    max_width_col = max(max_width_col, len(str(row[i])))
            col_widths.append(min(max_width_col, max_width))
        
        # Create table
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        table_lines = [separator]
        
        # Header
        header_line = "|"
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]}} |"
        table_lines.extend([header_line, separator])
        
        # Rows
        for row in rows:
            row_line = "|"
            for i in range(len(headers)):
                value = str(row[i]) if i < len(row) else ""
                if len(value) > col_widths[i]:
                    value = value[:col_widths[i]-3] + "..."
                row_line += f" {value:<{col_widths[i]}} |"
            table_lines.append(row_line)
        
        table_lines.append(separator)
        return "\n".join(table_lines)

# Global utility instances
rate_limiter = RateLimiter(config.rate_limit_requests, config.rate_limit_window)
smart_cache = SmartCache(max_size=1000, default_ttl=3600)
text_processor = TextProcessor()
file_manager = FileManager()
security_manager = SecurityManager()
datetime_manager = DateTimeManager()
formatting_utils = FormattingUtils()

# Export main utilities
__all__ = [
    'performance_tracked', 'perf_monitor',
    'RateLimiter', 'SmartCache', 'TextProcessor', 'FileManager',
    'SecurityManager', 'DateTimeManager', 'NetworkManager', 'FormattingUtils',
    'rate_limiter', 'smart_cache', 'text_processor', 'file_manager',
    'security_manager', 'datetime_manager', 'formatting_utils'
]
