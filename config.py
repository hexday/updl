#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Advanced Configuration Management System
🛡️ Secure, Type-Safe, Environment-Based Configuration
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field
from pydantic import BaseSettings, validator, Field
from pydantic.env_settings import SettingsSourceCallable
from dotenv import load_dotenv
import json
from loguru import logger

# Load environment variables
load_dotenv()

@dataclass
class PlatformConfig:
    """Configuration for supported platforms"""
    name: str
    emoji: str
    domains: List[str]
    enabled: bool = True
    max_quality: str = "best"
    supports_playlist: bool = False
    requires_auth: bool = False
    rate_limit: int = 10  # requests per minute

class BotSettings(BaseSettings):
    """Main bot configuration with validation"""
    
    # Bot Identity
    bot_token: str = Field(..., env='BOT_TOKEN')
    bot_username: Optional[str] = Field(None, env='BOT_USERNAME')
    
    # Admin Configuration
    super_admin_id: int = Field(..., env='SUPER_ADMIN_ID')
    admin_ids: List[int] = Field(default_factory=list, env='ADMIN_IDS')
    
    # Database
    database_url: str = Field("sqlite+aiosqlite:///bot.db", env='DATABASE_URL')
    redis_url: Optional[str] = Field(None, env='REDIS_URL')
    
    # External APIs
    spotify_client_id: Optional[str] = Field(None, env='SPOTIFY_CLIENT_ID')
    spotify_client_secret: Optional[str] = Field(None, env='SPOTIFY_CLIENT_SECRET')
    youtube_api_key: Optional[str] = Field(None, env='YOUTUBE_API_KEY')
    
    # File Management
    downloads_path: Path = Field(Path("./downloads/"), env='DOWNLOADS_PATH')
    max_file_size_mb: int = Field(100, env='MAX_FILE_SIZE_MB')
    temp_dir: Path = Field(Path("/tmp/bot_temp/"), env='TEMP_DIR')
    
    # Security
    secret_key: str = Field(..., env='SECRET_KEY')
    encryption_key: Optional[str] = Field(None, env='ENCRYPTION_KEY')
    webhook_secret: Optional[str] = Field(None, env='WEBHOOK_SECRET')
    
    # Performance
    max_concurrent_downloads: int = Field(10, env='MAX_CONCURRENT_DOWNLOADS')
    request_timeout: int = Field(30, env='REQUEST_TIMEOUT')
    rate_limit_requests: int = Field(30, env='RATE_LIMIT_REQUESTS')
    rate_limit_window: int = Field(60, env='RATE_LIMIT_WINDOW')
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env='SENTRY_DSN')
    log_level: str = Field("INFO", env='LOG_LEVEL')
    metrics_port: int = Field(9090, env='METRICS_PORT')
    
    # Features
    enable_analytics: bool = Field(True, env='ENABLE_ANALYTICS')
    enable_caching: bool = Field(True, env='ENABLE_CACHING')
    enable_premium: bool = Field(True, env='ENABLE_PREMIUM')
    enable_watermark: bool = Field(False, env='ENABLE_WATERMARK')
    
    # Development
    debug: bool = Field(False, env='DEBUG')
    dev_mode: bool = Field(False, env='DEV_MODE')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        
    @validator('admin_ids', pre=True)
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v or []
    
    @validator('downloads_path', 'temp_dir', pre=True)
    def ensure_path(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def __post_init__(self):
        """Post-initialization validation"""
        # Validate critical settings
        if not self.bot_token or self.bot_token == 'your_bot_token_here':
            raise ValueError("BOT_TOKEN is required and must be set")
        
        # Ensure admin list includes super admin
        if self.super_admin_id not in self.admin_ids:
            self.admin_ids.append(self.super_admin_id)

class PlatformManager:
    """Manager for supported platforms"""
    
    SUPPORTED_PLATFORMS = {
        'youtube': PlatformConfig(
            name='یوتیوب',
            emoji='🔴',
            domains=['youtube.com', 'youtu.be', 'm.youtube.com', 'music.youtube.com'],
            max_quality='4K',
            supports_playlist=True,
            rate_limit=20
        ),
        'instagram': PlatformConfig(
            name='اینستاگرام',
            emoji='📷',
            domains=['instagram.com', 'instagr.am', 'ig.me'],
            max_quality='Original',
            rate_limit=15
        ),
        'spotify': PlatformConfig(
            name='اسپاتیفای',
            emoji='🎵',
            domains=['open.spotify.com', 'spotify.com'],
            max_quality='320kbps',
            requires_auth=True,
            rate_limit=10
        ),
        'pinterest': PlatformConfig(
            name='پینترست',
            emoji='📌',
            domains=['pinterest.com', 'pin.it'],
            max_quality='Original',
            rate_limit=25
        ),
        'twitter': PlatformConfig(
            name='توییتر/ایکس',
            emoji='🐦',
            domains=['twitter.com', 'x.com', 't.co'],
            max_quality='1080p',
            rate_limit=15
        ),
        'tiktok': PlatformConfig(
            name='تیک‌تاک',
            emoji='🎬',
            domains=['tiktok.com', 'vm.tiktok.com'],
            max_quality='HD',
            rate_limit=20
        ),
        'soundcloud': PlatformConfig(
            name='ساندکلود',
            emoji='🎧',
            domains=['soundcloud.com'],
            max_quality='128kbps',
            rate_limit=15
        )
    }
    
    @classmethod
    def get_platform_by_url(cls, url: str) -> Optional[str]:
        """Detect platform from URL"""
        url_lower = url.lower()
        for platform_id, config in cls.SUPPORTED_PLATFORMS.items():
            if config.enabled and any(domain in url_lower for domain in config.domains):
                return platform_id
        return None
    
    @classmethod
    def get_enabled_platforms(cls) -> Dict[str, PlatformConfig]:
        """Get only enabled platforms"""
        return {k: v for k, v in cls.SUPPORTED_PLATFORMS.items() if v.enabled}

class MessagesConfig:
    """Multilingual message templates"""
    
    MESSAGES_FA = {
        'start': """🌟 **به ربات دانلود پیشرفته خوش آمدید!**

🔥 **قابلیت‌های فوق‌العاده:**
📱 دانلود از ۷+ پلتفرم محبوب
🎵 کیفیت صدا تا ۳۲۰ کیلوبیت
📺 کیفیت ویدئو تا ۴K
📊 نمایش اطلاعات کامل (آمار، کپشن)
⚡ سرعت برق‌آسا با پردازش همزمان
🛡️ امنیت بالا و حفظ حریم خصوصی

💎 **نحوه استفاده:**
لینک مورد نظر را ارسال کنید تا فوراً دانلود شود!

🚀 **آماده برای تجربه‌ای بی‌نظیر؟**""",

        'help': """📚 **راهنمای جامع ربات**

🎯 **دستورات کاربری:**
/start - شروع ربات
/help - راهنمای استفاده
/stats - آمار شخصی
/history - تاریخچه دانلود
/settings - تنظیمات کاربری
/premium - اشتراک ویژه

🌐 **پلتفرم‌های پشتیبانی‌شده:**
🔴 یوتیوب (ویدئو، موسیقی، پلی‌لیست)
📷 اینستاگرام (پست، ریل، IGTV)
🎵 اسپاتیفای (موسیقی با متادیتا)
📌 پینترست (تصاویر HD)
🐦 توییتر/ایکس (ویدئو، تصویر)
🎬 تیک‌تاک (ویدئو کوتاه)
🎧 ساندکلود (موسیقی)

💡 **نکات کلیدی:**
• پردازش فوری لینک‌ها
• انتخاب خودکار بهترین کیفیت
• پشتیبانی از لینک‌های کوتاه‌شده
• دانلود دسته‌ای پلی‌لیست‌ها

⚡ **سیستم پیشرفته و پایدار**""",

        'invalid_url': """❌ **لینک نامعتبر!**

لطفاً لینک صحیح از یکی از پلتفرم‌های زیر ارسال کنید:
🔴 یوتیوب  📷 اینستاگرام  🎵 اسپاتیفای
📌 پینترست  🐦 توییتر  🎬 تیک‌تاک  🎧 ساندکلود

💡 **مثال‌های معتبر:**
• https://youtube.com/watch?v=...
• https://instagram.com/p/...
• https://open.spotify.com/track/...""",

        'processing': """⏳ **در حال پردازش پیشرفته...**

🔍 تجزیه و تحلیل لینک با AI
📊 استخراج حداکثر اطلاعات
🎯 انتخاب بهترین کیفیت موجود
⬇️ آماده‌سازی فایل بهینه‌شده

⚡ **سیستم پردازش موازی فعال...**""",

        'download_success': """✅ **دانلود با موفقیت کامل شد!**

📊 **اطلاعات دقیق:**
💾 حجم: {size}
🎯 کیفیت: {quality}
⚡ سرعت: {speed}
⏱️ زمان: {duration}

🎉 **از دانلود خود لذت ببرید!**""",

        'error_download': """🚨 **خطا در دانلود!**

🔍 **دلایل احتمالی:**
• محتوا خصوصی یا محفوظ
• مشکل موقت سرور
• محدودیت منطقه‌ای
• فایل بیش از حد بزرگ

🔄 **راه‌حل:** لطفاً مجدداً تلاش کنید یا با پشتیبانی تماس بگیرید."""
    }

class SecurityConfig:
    """Security configuration and utilities"""
    
    # Rate limiting presets
    RATE_LIMITS = {
        'download': (10, 60),      # 10 downloads per minute
        'message': (30, 60),       # 30 messages per minute
        'admin': (100, 60),        # 100 admin operations per minute
        'api': (1000, 3600),       # 1000 API calls per hour
    }
    
    # File security settings
    ALLOWED_EXTENSIONS = {
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
        'document': ['.pdf', '.doc', '.docx', '.txt']
    }
    
    BLOCKED_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.vbs', '.js',
        '.jar', '.com', '.app', '.deb', '.rpm'
    ]
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe"""
        dangerous_chars = ['..', '/', '\\', '<', '>', '|', ':', '*', '?', '"']
        return not any(char in filename for char in dangerous_chars)

# Initialize configuration
try:
    config = BotSettings()
    platforms = PlatformManager()
    messages = MessagesConfig()
    security = SecurityConfig()
    
    logger.info(f"✅ Configuration loaded successfully")
    logger.info(f"🤖 Bot: {config.bot_username or 'Unknown'}")
    logger.info(f"👥 Admins: {len(config.admin_ids)}")
    logger.info(f"🌐 Platforms: {len(platforms.get_enabled_platforms())}")
    
except Exception as e:
    logger.error(f"❌ Configuration error: {e}")
    sys.exit(1)

# Export main objects
__all__ = ['config', 'platforms', 'messages', 'security', 'BotSettings', 'PlatformManager']
