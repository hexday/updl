#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Advanced Telegram Media Download Bot - Main Application
📱 Enterprise-Grade Multi-Platform Content Downloader
🎯 Version: 3.0.0 Enterprise Edition
"""

import asyncio
import sys
import signal
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

# Third-party imports
from telegram import Update, BotCommand, BotCommandScopeDefault
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from telegram.error import TelegramError, NetworkError, TimedOut
from loguru import logger
import uvloop  # High-performance event loop
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Local imports
from config import config, platforms, messages, security
from database import db, init_db
from downloaders import downloader, MediaMetadata
from keyboards import glass_keyboards, keyboard_builder
from admin_panel import admin_manager, BROADCAST_TEXT, BROADCAST_MEDIA
from utils import (
    performance_tracked, perf_monitor, smart_cache, text_processor,
    file_manager, datetime_manager, formatting_utils, rate_limiter
)

# Configure advanced logging
logger.remove()
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level=config.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    encoding="utf-8"
)
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}"
)

# Sentry integration for error tracking
if config.sentry_dsn:
    sentry_logging = LoggingIntegration(
        level=logger.WARNING,
        event_level=logger.ERROR
    )
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        integrations=[sentry_logging],
        traces_sample_rate=0.1,
        environment="production" if not config.dev_mode else "development"
    )

class AdvancedMediaBot:
    """Main bot application with enterprise features"""
    
    def __init__(self):
        self.app: Optional[Application] = None
        self.startup_time = datetime.now()
        self.is_running = False
        self.shutdown_requested = False
        
        # Performance metrics
        self.metrics = {
            'messages_processed': 0,
            'downloads_completed': 0,
            'downloads_failed': 0,
            'users_served': set(),
            'commands_executed': {},
            'errors_count': 0,
            'uptime_start': self.startup_time
        }
        
        # Active operations tracking
        self.active_downloads = {}
        self.user_sessions = {}
        
        logger.info("🤖 Advanced Media Download Bot initialized")
    
    @asynccontextmanager
    async def lifespan_manager(self):
        """Manage bot lifecycle with proper startup/shutdown"""
        try:
            await self._startup_sequence()
            yield
        finally:
            await self._shutdown_sequence()
    
    async def _startup_sequence(self):
        """Execute startup sequence"""
        logger.info("🚀 Starting bot initialization sequence...")
        
        # Initialize database
        await init_db()
        
        # Initialize cache and rate limiter
        await smart_cache.clear()  # Start with clean cache
        
        # Clean up old temporary files
        await file_manager.cleanup_old_files(config.temp_dir, max_age_hours=1)
        
        # Initialize performance monitoring
        if config.enable_analytics:
            asyncio.create_task(self._performance_monitor_loop())
        
        self.is_running = True
        logger.success("✅ Bot startup sequence completed")
    
    async def _shutdown_sequence(self):
        """Execute shutdown sequence"""
        logger.info("🛑 Starting bot shutdown sequence...")
        
        self.shutdown_requested = True
        self.is_running = False
        
        # Cancel active downloads
        for download_id in list(self.active_downloads.keys()):
            logger.info(f"Cancelling active download: {download_id}")
        
        # Clean up temporary files
        await downloader.cleanup_temp_files()
        
        # Close database connections
        await db.close()
        
        # Final performance report
        if config.enable_analytics:
            await self._generate_shutdown_report()
        
        logger.success("✅ Bot shutdown completed successfully")
    
    async def _performance_monitor_loop(self):
        """Background performance monitoring"""
        while self.is_running and not self.shutdown_requested:
            try:
                # Collect performance metrics
                performance_data = {
                    'timestamp': datetime.now(),
                    'messages_processed': self.metrics['messages_processed'],
                    'downloads_completed': self.metrics['downloads_completed'],
                    'active_users': len(self.metrics['users_served']),
                    'cache_size': len(smart_cache.cache),
                    'memory_usage': self._get_memory_usage(),
                }
                
                # Save to analytics if enabled
                if config.enable_analytics:
                    await db.save_analytics(
                        metric_type='performance',
                        metric_name='system_metrics',
                        metric_value=performance_data['messages_processed'],
                        metadata=performance_data
                    )
                
                # Wait 5 minutes before next collection
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    # Command Handlers
    @performance_tracked
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced start command with personalization"""
        user = update.effective_user
        user_id = user.id
        
        # Update metrics
        self.metrics['messages_processed'] += 1
        self.metrics['users_served'].add(user_id)
        self._track_command('start')
        
        try:
            # Register/update user in database
            user_data = {
                'user_id': user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code or 'fa'
            }
            
            db_user = await db.add_or_update_user(user_data)
            await db.update_user_activity(user_id)
            
            # Check membership requirements
            if not await self._check_user_access(user_id):
                await self._send_membership_required(update)
                return
            
            # Personalized welcome message
            user_stats = await db.get_user(user_id)
            download_count = user_stats.download_count if user_stats else 0
            
            # Check if user is new (joined in last 24 hours)
            is_new_user = (
                user_stats and 
                user_stats.join_date and
                (datetime.now() - user_stats.join_date).days == 0
            )
            
            if is_new_user:
                welcome_text = f"""🎉 **به خانواده بزرگ ما خوش آمدید، {user.first_name}!**

{messages.MESSAGES_FA['start']}

🆕 **برای کاربران جدید:**
• از دکمه "📚 راهنما" برای یادگیری سریع استفاده کنید
• با ارسال لینک، اولین دانلود خود را تجربه کنید
• در صورت نیاز به کمک، "📞 پشتیبانی" در خدمت شماست"""
            else:
                welcome_text = f"""👋 **سلام مجدد {user.first_name} عزیز!**

{messages.MESSAGES_FA['start']}

📊 **آمار شخصی شما:**
• تعداد دانلودها: `{formatting_utils.format_number_persian(download_count)}`
• آخرین بازدید: `{datetime_manager.time_ago_persian(user_stats.last_activity) if user_stats and user_stats.last_activity else 'نامشخص'}`"""
            
            # Add premium status if enabled
            if config.enable_premium and user_stats and user_stats.is_premium:
                welcome_text += "\n\n💎 **شما کاربر ویژه هستید!**"
            
            keyboard = glass_keyboards.main_menu(user_id)
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            logger.info(f"User {user_id} ({user.username or 'no_username'}) started the bot")
            
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await update.message.reply_text(
                "❌ خطایی رخ داد. لطفاً مجدداً تلاش کنید.",
                reply_markup=glass_keyboards.main_menu()
            )
            self.metrics['errors_count'] += 1
    
    @performance_tracked
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comprehensive help system"""
        self._track_command('help')
        
        # Get enabled platforms dynamically
        enabled_platforms = platforms.get_enabled_platforms()
        platforms_text = "\n".join([
            f"{config.emoji} **{config.name}** - {', '.join(config.domains[:2])}"
            for platform_id, config in enabled_platforms.items()
        ])
        
        help_text = f"""{messages.MESSAGES_FA['help']}

🔗 **دامنه‌های پشتیبانی شده:**
{platforms_text}

⚡ **نکات حرفه‌ای:**
• برای دانلود سریع‌تر از دکمه "⚡ دانلود سریع" استفاده کنید
• می‌توانید چندین لینک را همزمان ارسال کنید
• برای دانلود پلی‌لیست‌ها از "🎯 دانلود دسته‌ای" استفاده کنید
• با تنظیم کیفیت خودکار، بهترین کیفیت انتخاب می‌شود

📱 **دستورات سریع:**
/start - شروع مجدد
/stats - آمار شخصی
/settings - تنظیمات
/help - این راهنما"""
        
        keyboard = glass_keyboards.help_menu()
        
        await update.message.reply_text(
            help_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    @performance_tracked
    async def stats_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Personal statistics with charts"""
        user_id = update.effective_user.id
        self._track_command('stats')
        
        try:
            # Get user statistics
            user_stats = await db.get_user(user_id)
            if not user_stats:
                await update.message.reply_text(
                    "❌ آمار شخصی شما یافت نشد.\nلطفاً ابتدا /start را بزنید."
                )
                return
            
            # Get download history
            recent_downloads = await db.get_user_downloads(user_id, limit=10)
            
            # Calculate statistics
            total_downloads = len(recent_downloads)
            successful_downloads = len([d for d in recent_downloads if d.success])
            success_rate = (successful_downloads / max(1, total_downloads)) * 100
            
            # Get platform breakdown
            platform_stats = {}
            for download in recent_downloads:
                platform = download.platform or 'نامشخص'
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
            
            # Most used platform
            top_platform = max(platform_stats.items(), key=lambda x: x[1])[0] if platform_stats else 'نامشخص'
            
            # Format last downloads
            recent_downloads_text = "\n".join([
                f"• {text_processor.truncate_smart(dl.title or 'بدون عنوان', 25)} - "
                f"{datetime_manager.time_ago_persian(dl.download_date)}"
                for dl in recent_downloads[:3]
            ]) if recent_downloads else "هیچ دانلودی موجود نیست"
            
            stats_text = f"""📊 **آمار شخصی شما**

👤 **مشخصات:**
• نام: `{user_stats.first_name or 'ندارد'}`
• نام کاربری: `@{user_stats.username or 'ندارد'}`
• کاربر از: `{datetime_manager.time_ago_persian(user_stats.join_date)}`

📈 **آمار فعالیت:**
• کل دانلودها: `{formatting_utils.format_number_persian(user_stats.download_count)}`
• دانلودهای اخیر: `{formatting_utils.format_number_persian(total_downloads)}`
• نرخ موفقیت: `{success_rate:.1f}%`
• پلتفرم محبوب: **{top_platform}**

📥 **آخرین دانلودها:**
{recent_downloads_text}

💎 **وضعیت:** {'⭐ کاربر ویژه' if user_stats.is_premium else '👤 کاربر عادی'}"""
            
            keyboard = glass_keyboards.user_stats_menu()
            
            await update.message.reply_text(
                stats_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in stats handler: {e}")
            await update.message.reply_text(
                "❌ خطا در دریافت آمار شخصی.\nلطفاً بعداً تلاش کنید."
            )
    
    @performance_tracked
    async def admin_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Admin panel access"""
        user_id = update.effective_user.id
        self._track_command('admin')
        
        if not await admin_manager.is_admin(user_id):
            await update.message.reply_text(
                "🚫 **دسترسی محدود!**\n\nشما مجاز به استفاده از پنل مدیریت نیستید.",
                parse_mode='Markdown'
            )
            return
        
        await admin_manager.admin_panel_handler(update, context)
    
    # Message Handlers
    @performance_tracked
    async def url_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle URL messages for download"""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        self.metrics['messages_processed'] += 1
        self.metrics['users_served'].add(user_id)
        
        try:
            # Check rate limiting
            rate_limit_key = f"download:{user_id}"
            if not await rate_limiter.is_allowed(rate_limit_key):
                await update.message.reply_text(
                    "⏱️ **محدودیت سرعت!**\n\n"
                    "شما بیش از حد مجاز درخواست ارسال کرده‌اید.\n"
                    "لطفاً کمی صبر کنید و مجدداً تلاش کنید.",
                    parse_mode='Markdown'
                )
                return
            
            # Check user access
            if not await self._check_user_access(user_id):
                await self._send_membership_required(update)
                return
            
            # Update user activity
            await db.update_user_activity(user_id)
            
            # Extract URLs from message
            urls = text_processor.extract_urls(message_text)
            
            if not urls:
                await update.message.reply_text(
                    messages.MESSAGES_FA['invalid_url'],
                    parse_mode='Markdown',
                    reply_markup=glass_keyboards.download_platforms()
                )
                return
            
            # Process first URL (support for multiple URLs can be added)
            url = urls[0]
            
            # Check if URL is supported
            platform = await downloader._detect_platform(url)
            if not platform:
                supported_domains = []
                for platform_config in platforms.get_enabled_platforms().values():
                    supported_domains.extend(platform_config.domains)
                
                await update.message.reply_text(
                    f"{messages.MESSAGES_FA['invalid_url']}\n\n"
                    f"**دامنه‌های پشتیبانی شده:**\n" +
                    "\n".join([f"• `{domain}`" for domain in supported_domains[:10]]),
                    parse_mode='Markdown'
                )
                return
            
            # Start download process
            await self._process_download_request(update, url, user_id, platform)
            
        except Exception as e:
            logger.error(f"Error in URL handler: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش لینک رخ داد.\nلطفاً مجدداً تلاش کنید.",
                reply_markup=glass_keyboards.main_menu()
            )
            self.metrics['errors_count'] += 1
    
    async def _process_download_request(self, update: Update, url: str, 
                                      user_id: int, platform: str) -> None:
        """Process download request with advanced features"""
        download_id = f"{user_id}_{int(datetime.now().timestamp())}"
        
        try:
            # Add to active downloads
            self.active_downloads[download_id] = {
                'user_id': user_id,
                'url': url,
                'platform': platform,
                'start_time': datetime.now()
            }
            
            # Get platform info
            platform_config = platforms.SUPPORTED_PLATFORMS.get(platform, {})
            platform_name = platform_config.get('name', platform)
            platform_emoji = platform_config.get('emoji', '📱')
            
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"""⏳ **در حال پردازش پیشرفته...**

{platform_emoji} **پلتفرم:** {platform_name}
🔗 **لینک:** `{text_processor.truncate_smart(url, 50)}`

🧠 **مراحل هوشمند:**
• 🔍 تجزیه و تحلیل URL با AI
• 📊 استخراج متادیتای کامل
• 🎯 انتخاب بهترین کیفیت
• ⬇️ دانلود بهینه‌شده

⚡ **سیستم پردازش موازی فعال...**""",
                parse_mode='Markdown',
                reply_markup=glass_keyboards.download_progress(download_id)
            )
            
            # Perform download
            download_result = await downloader.download_media(url, user_id)
            
            if download_result.success:
                await self._handle_successful_download(
                    update, download_result, processing_msg, url, user_id, download_id
                )
                self.metrics['downloads_completed'] += 1
            else:
                await self._handle_failed_download(
                    update, download_result, processing_msg, url, user_id
                )
                self.metrics['downloads_failed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing download request: {e}")
            await update.message.reply_text(
                f"❌ **خطا در پردازش درخواست**\n\n"
                f"**جزئیات:** `{str(e)}`\n\n"
                "لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode='Markdown',
                reply_markup=glass_keyboards.main_menu()
            )
            self.metrics['errors_count'] += 1
        finally:
            # Remove from active downloads
            self.active_downloads.pop(download_id, None)
    
    async def _handle_successful_download(self, update: Update, result, 
                                        processing_msg, url: str, user_id: int, download_id: str):
        """Handle successful download with rich media info"""
        try:
            # Create rich caption with metadata
            caption = await self._create_rich_caption(result.metadata, result)
            
            # Determine file type and send appropriately
            file_path = Path(result.file_path)
            file_extension = file_path.suffix.lower()
            
            keyboard = glass_keyboards.download_complete(download_id, has_variants=len(result.variants) > 0)
            
            # Send file based on type
            with open(result.file_path, 'rb') as file:
                if file_extension in ['.mp4', '.avi', '.mkv', '.mov', '.webm']:
                    await update.message.reply_video(
                        video=file,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=keyboard,
                        supports_streaming=True
                    )
                elif file_extension in ['.mp3', '.wav', '.flac', '.m4a', '.aac']:
                    await update.message.reply_audio(
                        audio=file,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    await update.message.reply_photo(
                        photo=file,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    await update.message.reply_document(
                        document=file,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
            
            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass
                
            logger.info(f"Successfully downloaded and sent file for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending downloaded file: {e}")
            await processing_msg.edit_text(
                f"✅ **دانلود موفق بود!**\n\n"
                f"📁 فایل آماده است اما ارسال با خطا مواجه شد.\n"
                f"**علت:** فایل بیش از حد بزرگ یا فرمت پشتیبانی نمی‌شود.\n\n"
                f"💾 **حجم:** {file_manager.bytes_to_human(result.metadata.file_size)}\n"
                f"📊 **عنوان:** {text_processor.truncate_smart(result.metadata.title, 50)}\n\n"
                f"📞 لطفاً با پشتیبانی تماس بگیرید.",
                parse_mode='Markdown',
                reply_markup=glass_keyboards.main_menu()
            )
        finally:
            # Cleanup temporary file
            try:
                if os.path.exists(result.file_path):
                    os.unlink(result.file_path)
            except:
                pass
    
    async def _create_rich_caption(self, metadata: MediaMetadata, result) -> str:
        """Create rich, informative caption for media"""
        platform_config = platforms.SUPPORTED_PLATFORMS.get(metadata.platform, {})
        platform_name = platform_config.get('name', metadata.platform)
        platform_emoji = platform_config.get('emoji', '📱')
        
        # Main title and source
        caption_parts = [
            f"**{text_processor.escape_markdown_v2(metadata.title)}**" if metadata.title else "**محتوای دانلود شده**",
            "",
            f"{platform_emoji} **منبع:** {platform_name}"
        ]
        
        # Content creator info
        if metadata.uploader:
            caption_parts.append(f"👤 **سازنده:** `{text_processor.escape_markdown_v2(metadata.uploader)}`")
        
        # Media properties
        details = []
        if metadata.duration > 0:
            details.append(f"⏱️ **مدت:** `{datetime_manager.duration_to_text(metadata.duration)}`")
        
        if metadata.file_size > 0:
            details.append(f"💾 **حجم:** `{file_manager.bytes_to_human(metadata.file_size)}`")
        
        if metadata.quality:
            details.append(f"🎯 **کیفیت:** `{metadata.quality}`")
        
        # Social metrics (if available)
        social_metrics = []
        if metadata.view_count > 0:
            social_metrics.append(f"👁️ `{formatting_utils.format_number_persian(metadata.view_count)}`")
        
        if metadata.like_count > 0:
            social_metrics.append(f"❤️ `{formatting_utils.format_number_persian(metadata.like_count)}`")
        
        if metadata.comment_count > 0:
            social_metrics.append(f"💬 `{formatting_utils.format_number_persian(metadata.comment_count)}`")
        
        if social_metrics:
            details.append("📊 **آمار:** " + " • ".join(social_metrics))
        
        # Technical info
        if result.download_time > 0:
            download_speed = metadata.file_size / result.download_time / 1024 / 1024  # MB/s
            details.append(f"⚡ **سرعت:** `{download_speed:.1f} MB/s` در `{result.download_time:.1f}s`")
        
        if result.quality_score > 0:
            details.append(f"🌟 **امتیاز کیفیت:** `{result.quality_score}/100`")
        
        # Add details section
        if details:
            caption_parts.extend(["", "**📋 مشخصات:**"] + details)
        
        # Description (if available and short enough)
        if metadata.description and len(metadata.description) <= 200:
            caption_parts.extend([
                "", 
                f"📝 **توضیحات:** {text_processor.truncate_smart(metadata.description, 150)}"
            ])
        
        # Footer
        caption_parts.extend([
            "",
            "🤖 **دانلود شده با ربات پیشرفته**",
            "⚡ **سریع • هوشمند • رایگان • امن**"
        ])
        
        return "\n".join(caption_parts)
    
    async def _handle_failed_download(self, update: Update, result, 
                                    processing_msg, url: str, user_id: int):
        """Handle failed download with detailed error info"""
        # Create user-friendly error message
        error_messages = {
            'UNSUPPORTED_PLATFORM': '❌ این پلتفرم پشتیبانی نمی‌شود',
            'RATE_LIMIT_EXCEEDED': '⏱️ محدودیت سرعت فعال است',
            'FILE_TOO_LARGE': '📦 فایل بیش از حد مجاز بزرگ است',
            'INVALID_URL': '🔗 لینک نامعتبر یا منقضی شده',
            'PRIVATE_CONTENT': '🔒 محتوای خصوصی قابل دانلود نیست',
            'NETWORK_ERROR': '🌐 مشکل اتصال به اینترنت',
            'SERVER_ERROR': '🔧 مشکل موقت سرور'
        }
        
        user_error = error_messages.get(
            result.error_code, 
            '❌ خطای نامشخص در دانلود'
        )
        
        error_text = f"""🚨 **دانلود ناموفق!**

{user_error}

🔍 **جزئیات:**
• **لینک:** `{text_processor.truncate_smart(url, 60)}`
• **پلتفرم:** {result.metadata.platform or 'نامشخص'}
• **کد خطا:** `{result.error_code}`

💡 **راه‌حل‌های پیشنهادی:**
• بررسی صحت لینک
• تلاش مجدد بعد از چند دقیقه
• استفاده از لینک مستقیم به جای کوتاه‌شده
• تماس با پشتیبانی در صورت تکرار مشکل

🔄 **می‌توانید مجدداً تلاش کنید یا لینک دیگری ارسال کنید.**"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"retry_download:{text_processor.truncate_smart(url, 100)}"),
                InlineKeyboardButton("📞 پشتیبانی", callback_data="support")
            ],
            [
                InlineKeyboardButton("📥 دانلود جدید", callback_data="download_menu"),
                InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
            ]
        ]
        
        try:
            await processing_msg.edit_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except:
            await update.message.reply_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        logger.warning(f"Download failed for user {user_id}: {result.error_code} - {result.error_message}")
    
    # Callback Query Handler
    @performance_tracked
    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all callback queries with routing"""
        query = update.callback_query
        data = query.data
        user_id = update.effective_user.id
        
        await query.answer()
        
        # Update user activity
        await db.update_user_activity(user_id)
        
        try:
            # Route callback queries
            if data == "main_menu":
                await self._show_main_menu(query, user_id)
            elif data == "download_menu":
                await self._show_download_menu(query)
            elif data == "user_stats":
                await self._show_user_stats(query, user_id)
            elif data == "help_menu":
                await self._show_help_menu(query)
            elif data.startswith("platform_"):
                platform = data.split("_", 1)[1]
                await self._show_platform_guide(query, platform)
            elif data.startswith("quality_"):
                quality = data.split("_", 1)[1]
                await self._handle_quality_selection(query, quality)
            elif data == "admin_panel" and await admin_manager.is_admin(user_id):
                await admin_manager.admin_panel_handler(update, context)
            elif data.startswith("admin_") and await admin_manager.is_admin(user_id):
                await self._route_admin_callback(update, context, data)
            else:
                # Handle unknown callbacks
                await query.edit_message_text(
                    "🤖 **عملیات در حال پردازش...**\n\nلطفاً منتظر بمانید.",
                    reply_markup=glass_keyboards.main_menu(user_id)
                )
                
        except Exception as e:
            logger.error(f"Error in callback query handler: {e}")
            try:
                await query.edit_message_text(
                    "❌ خطایی رخ داد. لطفاً مجدداً تلاش کنید.",
                    reply_markup=glass_keyboards.main_menu(user_id)
                )
            except:
                pass
            self.metrics['errors_count'] += 1
    
    async def _show_main_menu(self, query, user_id: int):
        """Show personalized main menu"""
        user_stats = await db.get_user(user_id)
        
        menu_text = f"""🏠 **منوی اصلی**

👋 سلام {query.from_user.first_name}!

📊 **آمار سریع:**
• دانلودهای شما: `{formatting_utils.format_number_persian(user_stats.download_count if user_stats else 0)}`
• وضعیت: {'💎 ویژه' if user_stats and user_stats.is_premium else '👤 عادی'}

🚀 **آماده برای دانلود محتوای جدید؟**"""
        
        keyboard = glass_keyboards.main_menu(user_id)
        await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_download_menu(self, query):
        """Show download platform selection"""
        enabled_platforms = platforms.get_enabled_platforms()
        
        menu_text = f"""📥 **دانلود محتوا**

🌐 **{len(enabled_platforms)} پلتفرم در دسترس**

🎯 **روش‌های دانلود:**
• **انتخاب پلتفرم:** برای راهنمای تخصصی
• **دانلود سریع:** ارسال مستقیم لینک
• **دانلود دسته‌ای:** چندین فایل همزمان

💡 **نکات مهم:**
• لینک‌های عمومی ارسال کنید
• کیفیت بهترین حالت انتخاب می‌شود
• پردازش معمولاً کمتر از یک دقیقه"""
        
        keyboard = glass_keyboards.download_platforms()
        await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _show_user_stats(self, query, user_id: int):
        """Show detailed user statistics"""
        # Implementation similar to stats_handler but for callback query
        await self.stats_handler(query, None)  # Adapt for callback context
    
    async def _show_help_menu(self, query):
        """Show help menu"""
        keyboard = glass_keyboards.help_menu()
        await query.edit_message_text(
            messages.MESSAGES_FA['help'],
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def _show_platform_guide(self, query, platform: str):
        """Show specific platform guide"""
        platform_config = platforms.SUPPORTED_PLATFORMS.get(platform)
        if not platform_config:
            await query.edit_message_text("❌ پلتفرم یافت نشد.")
            return
        
        guide_text = f"""🎯 **راهنمای {platform_config.name}**

{platform_config.emoji} **درباره:**
{platform_config.name} یکی از محبوب‌ترین پلتفرم‌های اشتراک محتوا

🌐 **دامنه‌های پشتیبانی:**
{', '.join([f'`{domain}`' for domain in platform_config.domains])}

📝 **نحوه استفاده:**
1️⃣ لینک محتوای مورد نظر را کپی کنید
2️⃣ آن را در چت ربات ارسال کنید
3️⃣ منتظر پردازش و دانلود باشید

🎯 **کیفیت‌های پشتیبانی:**
• حداکثر کیفیت: **{platform_config.max_quality}**
• پشتیبانی از پلی‌لیست: {'✅' if platform_config.supports_playlist else '❌'}
• نیاز به احراز هویت: {'✅' if platform_config.requires_auth else '❌'}

💡 **نکات مهم:**
• فقط محتوای عمومی قابل دانلود است
• لینک‌های منقضی‌شده پردازش نمی‌شوند
• برای بهترین تجربه از لینک اصلی استفاده کنید"""
        
        keyboard = [
                [InlineKeyboardButton("🔄 امتحان کنید", switch_inline_query_current_chat="")],
                [
                    InlineKeyboardButton("⚙️ تنظیمات کیفیت", callback_data=f"quality_settings_{platform}"),
                    InlineKeyboardButton("📊 آمار این پلتفرم", callback_data=f"platform_stats_{platform}")
                ],
                [
                    InlineKeyboardButton("🔙 انتخاب پلتفرم", callback_data="download_menu"),
                    InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
                ]
            ]
        
        await query.edit_message_text(
            guide_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def _handle_quality_selection(self, query, quality: str):
        """Handle quality selection for downloads"""
        # Store user's quality preference
        user_id = query.from_user.id
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}
        
        self.user_sessions[user_id]['preferred_quality'] = quality
        
        await query.edit_message_text(
            f"✅ **کیفیت انتخاب شد:** `{quality}`\n\n"
            "اکنون لینک مورد نظر خود را ارسال کنید.",
            reply_markup=glass_keyboards.main_menu(user_id),
            parse_mode='Markdown'
        )
    
    async def _route_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Route admin-related callbacks"""
        if data == "admin_stats":
            await admin_manager.system_stats_handler(update, context)
        elif data == "broadcast_menu":
            await admin_manager.broadcast_menu_handler(update, context)
        elif data == "broadcast_text":
            await admin_manager.start_text_broadcast(update, context)
        elif data == "broadcast_confirm_now":
            await admin_manager.confirm_broadcast(update, context)
        # Add more admin callback routing as needed
    
    # Utility Methods
    async def _check_user_access(self, user_id: int) -> bool:
        """Check if user has access to the bot"""
        # In this example, all users have access
        # In real implementation, check membership requirements
        return True
    
    async def _send_membership_required(self, update: Update):
        """Send membership requirement message"""
        channels = [
            "[📢 کانال اول](https://t.me/channel1)",
            "[📢 کانال دوم](https://t.me/channel2)"
        ]
        
        membership_text = f"""🔐 **عضویت اجباری**

برای استفاده از ربات ابتدا در کانال‌های زیر عضو شوید:

{chr(10).join(channels)}

پس از عضویت، دکمه "✅ عضو شدم" را بزنید."""
        
        keyboard = [
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")],
            [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
        ]
        
        await update.message.reply_text(
            membership_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    def _track_command(self, command: str):
        """Track command usage statistics"""
        if command not in self.metrics['commands_executed']:
            self.metrics['commands_executed'][command] = 0
        self.metrics['commands_executed'][command] += 1
    
    # Conversation Handler for Broadcasts
    def get_broadcast_conversation_handler(self) -> ConversationHandler:
        """Create broadcast conversation handler"""
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(admin_manager.start_text_broadcast, pattern="^broadcast_text$")],
            states={
                BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_manager.handle_broadcast_text)],
                BROADCAST_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, admin_manager.handle_broadcast_media)],
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conversation)],
            allow_reentry=True,
            conversation_timeout=300  # 5 minutes
        )
    
    async def _cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel ongoing conversation"""
        await update.message.reply_text(
            "❌ **عملیات لغو شد.**",
            reply_markup=glass_keyboards.main_menu(update.effective_user.id),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Error Handler
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler with detailed logging"""
        error = context.error
        self.metrics['errors_count'] += 1
        
        # Log error details
        logger.error(f"Exception while handling update {update}: {error}")
        
        # Handle different error types
        if isinstance(error, NetworkError):
            error_msg = "🌐 مشکل اتصال به اینترنت"
        elif isinstance(error, TimedOut):
            error_msg = "⏱️ زمان انتظار تمام شد"
        elif isinstance(error, TelegramError):
            error_msg = f"🤖 خطای تلگرام: {str(error)}"
        else:
            error_msg = "❌ خطای غیرمنتظره"
        
        # Send error message to user if possible
        if update and hasattr(update, 'effective_message') and hasattr(update, 'effective_user'):
            try:
                await update.effective_message.reply_text(
                    f"{error_msg}\n\nلطفاً مجدداً تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    reply_markup=glass_keyboards.main_menu(update.effective_user.id)
                )
            except Exception as send_error:
                logger.error(f"Could not send error message to user: {send_error}")
        
        # Report critical errors to Sentry if configured
        if config.sentry_dsn:
            import sentry_sdk
            sentry_sdk.capture_exception(error)
    
    # Bot Setup and Management
    def setup_application(self) -> Application:
        """Setup and configure the bot application"""
        # Build application with advanced settings
        application = (
            ApplicationBuilder()
            .token(config.bot_token)
            .concurrent_updates(True)
            .connection_pool_size(20)
            .pool_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .build()
        )
        
        # Set up command handlers
        application.add_handler(CommandHandler("start", self.start_handler))
        application.add_handler(CommandHandler("help", self.help_handler))
        application.add_handler(CommandHandler("stats", self.stats_handler))
        application.add_handler(CommandHandler("admin", self.admin_handler))
        
        # Add conversation handlers
        application.add_handler(self.get_broadcast_conversation_handler())
        
        # Message handlers (order matters!)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.url_handler
        ))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        # Post initialization
        application.post_init = self._post_init_setup
        
        return application
    
    async def _post_init_setup(self, application: Application) -> None:
        """Post-initialization setup"""
        # Set bot commands
        commands = [
            BotCommand("start", "شروع ربات و نمایش منوی اصلی"),
            BotCommand("help", "راهنمای کامل استفاده از ربات"),
            BotCommand("stats", "آمار شخصی و عملکرد"),
            BotCommand("admin", "پنل مدیریت (فقط مدیران)"),
        ]
        
        await application.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        
        # Set bot info
        if config.bot_username:
            logger.info(f"Bot @{config.bot_username} is ready!")
        
        logger.success("✅ Post-initialization setup completed")
    
    async def _generate_shutdown_report(self):
        """Generate shutdown performance report"""
        try:
            uptime = datetime.now() - self.startup_time
            
            report = {
                'uptime': uptime.total_seconds(),
                'messages_processed': self.metrics['messages_processed'],
                'downloads_completed': self.metrics['downloads_completed'],
                'downloads_failed': self.metrics['downloads_failed'],
                'unique_users': len(self.metrics['users_served']),
                'errors_count': self.metrics['errors_count'],
                'commands_executed': self.metrics['commands_executed']
            }
            
            # Save report to analytics
            await db.save_analytics(
                metric_type='shutdown_report',
                metric_name='session_summary',
                metric_value=report['messages_processed'],
                metadata=report
            )
            
            logger.info(f"Session report: {report}")
            
        except Exception as e:
            logger.error(f"Failed to generate shutdown report: {e}")
    
    # Main execution method
    async def run(self):
        """Main run method with lifecycle management"""
        async with self.lifespan_manager():
            # Setup application
            application = self.setup_application()
            self.app = application
            
            # Start the bot
            logger.info("🚀 Starting bot polling...")
            
            try:
                # Run the bot with polling
                await application.run_polling(
                    allowed_updates=['message', 'callback_query', 'my_chat_member'],
                    drop_pending_updates=True,
                    close_loop=False
                )
            except KeyboardInterrupt:
                logger.info("⌨️ Received keyboard interrupt")
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                raise

# Signal handlers for graceful shutdown
def signal_handler(bot_instance):
    """Create signal handler for graceful shutdown"""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        bot_instance.shutdown_requested = True
        # Note: The actual shutdown will be handled by the lifespan manager
    
    return handler

# Main execution
async def main():
    """Main entry point"""
    # Validate configuration
    validation = config.validate_config() if hasattr(config, 'validate_config') else {'valid': True, 'errors': [], 'warnings': []}
    
    if not validation['valid']:
        logger.error("❌ Configuration validation failed:")
        for error in validation['errors']:
            logger.error(f"  • {error}")
        sys.exit(1)
    
    if validation['warnings']:
        logger.warning("⚠️ Configuration warnings:")
        for warning in validation['warnings']:
            logger.warning(f"  • {warning}")
    
    # Set up uvloop for better performance (Linux/Mac only)
    if hasattr(uvloop, 'install') and os.name != 'nt':
        uvloop.install()
        logger.info("🔄 Using uvloop for enhanced performance")
    
    # Create and run bot
    bot = AdvancedMediaBot()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler(bot))
    signal.signal(signal.SIGTERM, signal_handler(bot))
    
    # Print startup banner
    logger.info(f"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║  🚀 ADVANCED TELEGRAM MEDIA DOWNLOAD BOT - ENTERPRISE EDITION                            ║
║  ════════════════════════════════════════════════════════════════════════════════════    ║
║  📅 Version: 3.0.0 Enterprise                                                           ║
║  🌐 Platforms: {len([p for p in platforms.SUPPORTED_PLATFORMS.values() if p.enabled]):<2} supported                                                      ║
║  👨‍💻 Admins: {len(config.admin_ids):<2} configured                                                        ║
║  🔧 Features: {'Premium' if config.enable_premium else 'Standard':<8} • {'Analytics' if config.enable_analytics else 'Basic':<9} • {'Cached' if config.enable_caching else 'Direct':<6}            ║
║  💾 Database: {config.database_url.split(':')[0].upper():<10}                                                        ║
║  🚀 Status: READY FOR LAUNCH                                                            ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Graceful shutdown completed")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        sys.exit(1)
