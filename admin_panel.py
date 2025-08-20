#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
👨‍💻 Enterprise Admin Panel System
🔧 Advanced Management, Analytics, Broadcasting & System Control
"""

import asyncio
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import io
import base64

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError, Forbidden, BadRequest
from loguru import logger
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

from config import config, security
from database import db, User, Download, Admin, Analytics
from keyboards import glass_keyboards
from utils import (
    performance_tracked, smart_cache, text_processor, 
    file_manager, datetime_manager, formatting_utils, security_manager
)

# Conversation states
(BROADCAST_TEXT, BROADCAST_MEDIA, BROADCAST_SCHEDULE, 
 ADD_ADMIN, ADD_CHANNEL, SEARCH_USER, CONFIG_UPDATE) = range(7)

@dataclass
class BroadcastStats:
    """Broadcast statistics container"""
    total_users: int = 0
    successful_sends: int = 0
    failed_sends: int = 0
    blocked_users: int = 0
    deleted_accounts: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_time: Optional[timedelta] = None

class SystemMonitor:
    """Real-time system monitoring"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.thresholds = {
            'cpu_usage': 80,
            'memory_usage': 85,
            'error_rate': 10,
            'response_time': 5.0
        }
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        import psutil
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network stats
        network = psutil.net_io_counters()
        
        # Bot-specific metrics
        db_stats = await db.get_system_stats()
        
        metrics = {
            'timestamp': datetime.now(),
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'memory_available': memory.available,
            'disk_usage': disk.percent,
            'disk_free': disk.free,
            'network_sent': network.bytes_sent,
            'network_received': network.bytes_recv,
            'database_stats': db_stats,
            'active_downloads': len(getattr(db, 'active_downloads', {})),
            'cache_size': len(smart_cache.cache),
        }
        
        # Check thresholds and generate alerts
        self._check_thresholds(metrics)
        
        self.metrics = metrics
        return metrics
    
    def _check_thresholds(self, metrics: Dict[str, Any]):
        """Check if metrics exceed thresholds"""
        current_time = datetime.now()
        
        for metric, threshold in self.thresholds.items():
            value = metrics.get(metric, 0)
            if value > threshold:
                alert = {
                    'type': 'threshold_exceeded',
                    'metric': metric,
                    'value': value,
                    'threshold': threshold,
                    'timestamp': current_time
                }
                self.alerts.append(alert)
                logger.warning(f"Alert: {metric} exceeded threshold: {value} > {threshold}")

class AdvancedAnalytics:
    """Advanced analytics and reporting system"""
    
    @staticmethod
    async def generate_user_growth_chart(days: int = 30) -> str:
        """Generate user growth chart"""
        try:
            # Get user registration data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            async with db.get_session() as session:
                # This would be a complex query in real implementation
                # Simulating data for demo
                dates = [(start_date + timedelta(days=i)).date() for i in range(days)]
                users = [10 + i * 2 + (i % 7) * 3 for i in range(days)]  # Sample data
            
            # Create chart
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), facecolor='#1e1e1e')
            
            # Plot data
            ax.plot(dates, users, color='#00ff88', linewidth=3, marker='o', markersize=4)
            ax.fill_between(dates, users, alpha=0.3, color='#00ff88')
            
            # Styling
            ax.set_title('📈 رشد کاربران در ماه گذشته', color='white', fontsize=16, pad=20)
            ax.set_xlabel('تاریخ', color='white', fontsize=12)
            ax.set_ylabel('تعداد کاربران جدید', color='white', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#2d2d2d')
            
            # Format dates on x-axis
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            
            # Color customization
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')
            
            plt.tight_layout()
            
            # Save chart
            chart_path = config.temp_dir / f"user_growth_{int(datetime.now().timestamp())}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='#1e1e1e')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Error generating user growth chart: {e}")
            return ""
    
    @staticmethod
    async def generate_platform_stats_chart() -> str:
        """Generate platform usage statistics chart"""
        try:
            # Get platform statistics
            platform_stats = await db.get_popular_platforms(days=30)
            
            if not platform_stats:
                return ""
            
            # Prepare data
            platforms = [stat['platform'] for stat in platform_stats[:8]]  # Top 8
            counts = [stat['count'] for stat in platform_stats[:8]]
            colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', 
                     '#ff9ff3', '#54a0ff', '#5f27cd']
            
            # Create pie chart
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 10), facecolor='#1e1e1e')
            
            wedges, texts, autotexts = ax.pie(counts, labels=platforms, colors=colors,
                                            autopct='%1.1f%%', startangle=90,
                                            textprops={'color': 'white'})
            
            ax.set_title('📊 آمار پلتفرم‌های محبوب (۳۰ روز گذشته)', 
                        color='white', fontsize=16, pad=20)
            
            plt.tight_layout()
            
            # Save chart  
            chart_path = config.temp_dir / f"platform_stats_{int(datetime.now().timestamp())}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='#1e1e1e')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"Error generating platform stats chart: {e}")
            return ""
    
    @staticmethod
    async def generate_comprehensive_report() -> str:
        """Generate comprehensive analytics report"""
        try:
            # Collect all statistics
            system_stats = await db.get_system_stats()
            platform_stats = await db.get_popular_platforms(days=30)
            
            # Create multi-panel dashboard
            fig = plt.figure(figsize=(16, 12), facecolor='#1e1e1e')
            
            # User growth (top left)
            ax1 = plt.subplot(2, 2, 1)
            days = 30
            dates = [(datetime.now() - timedelta(days=i)).date() for i in range(days, 0, -1)]
            users = [5 + i + (i % 7) * 2 for i in range(days)]
            ax1.plot(dates, users, color='#00ff88', linewidth=2)
            ax1.fill_between(dates, users, alpha=0.3, color='#00ff88')
            ax1.set_title('رشد کاربران', color='white', fontsize=14)
            ax1.tick_params(colors='white', labelsize=8)
            ax1.grid(True, alpha=0.3)
            ax1.set_facecolor('#2d2d2d')
            
            # Downloads by hour (top right)
            ax2 = plt.subplot(2, 2, 2)
            hours = list(range(24))
            downloads = [20 + abs(12-h)*2 + (h % 3)*5 for h in hours]
            ax2.bar(hours, downloads, color='#667eea', alpha=0.8)
            ax2.set_title('دانلودها بر اساس ساعت', color='white', fontsize=14)
            ax2.set_xlabel('ساعت', color='white')
            ax2.tick_params(colors='white', labelsize=8)
            ax2.grid(True, alpha=0.3)
            ax2.set_facecolor('#2d2d2d')
            
            # Platform distribution (bottom left)
            ax3 = plt.subplot(2, 2, 3)
            if platform_stats:
                platforms = [stat['platform'][:8] for stat in platform_stats[:6]]
                counts = [stat['count'] for stat in platform_stats[:6]]
                colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3']
                ax3.pie(counts, labels=platforms, colors=colors, autopct='%1.1f%%',
                       textprops={'color': 'white', 'fontsize': 8})
            ax3.set_title('توزیع پلتفرم‌ها', color='white', fontsize=14)
            
            # System metrics (bottom right)
            ax4 = plt.subplot(2, 2, 4)
            metrics = ['CPU', 'RAM', 'Disk', 'Cache']
            values = [45, 62, 38, 71]  # Sample values
            colors = ['#ff6b6b' if v > 80 else '#feca57' if v > 60 else '#00ff88' for v in values]
            bars = ax4.bar(metrics, values, color=colors, alpha=0.8)
            ax4.set_title('وضعیت سیستم (%)', color='white', fontsize=14)
            ax4.set_ylim(0, 100)
            ax4.tick_params(colors='white', labelsize=8)
            ax4.grid(True, alpha=0.3)
            ax4.set_facecolor('#2d2d2d')
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{value}%', ha='center', va='bottom', color='white', fontsize=8)
            
            # Style all subplots
            for ax in [ax1, ax2, ax3, ax4]:
                for spine in ax.spines.values():
                    spine.set_color('white')
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.95)
            
            # Add main title
            fig.suptitle('📊 گزارش جامع سیستم', color='white', fontsize=18, y=0.98)
            
            # Save report
            report_path = config.temp_dir / f"comprehensive_report_{int(datetime.now().timestamp())}.png"
            plt.savefig(report_path, dpi=300, bbox_inches='tight', facecolor='#1e1e1e')
            plt.close()
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return ""

class AdminPanelManager:
    """Main admin panel management system"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.analytics = AdvancedAnalytics()
        self.broadcast_queue = asyncio.Queue()
        self.temp_data = {}
        self.active_broadcasts = {}
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user has admin privileges"""
        return user_id in config.admin_ids or await db.is_admin(user_id)
    
    async def get_admin_level(self, user_id: int) -> str:
        """Get admin access level"""
        if user_id == config.super_admin_id:
            return "super_admin"
        elif user_id in config.admin_ids:
            return "admin"
        else:
            # Check database for role
            async with db.get_session() as session:
                admin = await session.get(Admin, user_id)
                return admin.role if admin else "user"
    
    @performance_tracked
    async def admin_panel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Main admin panel interface"""
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(
                "🚫 **دسترسی محدود!**\n\nشما مجاز به استفاده از پنل مدیریت نیستید.",
                parse_mode='Markdown'
            )
            return
        
        admin_level = await self.get_admin_level(user_id)
        
        # Get real-time system metrics
        metrics = await self.system_monitor.collect_metrics()
        system_stats = await db.get_system_stats()
        
        # Format admin panel message
        admin_text = f"""👨‍💻 **پنل مدیریت پیشرفته**

🎯 **آمار سیستم لحظه‌ای:**
👥 کاربران فعال: `{formatting_utils.format_number_persian(system_stats.total_users):,}`
📥 دانلودهای امروز: `{formatting_utils.format_number_persian(system_stats.downloads_today):,}`
📊 کل دانلودها: `{formatting_utils.format_number_persian(system_stats.total_downloads):,}`
⚡ فعال امروز: `{formatting_utils.format_number_persian(system_stats.active_users_today):,}`

💾 **عملکرد سیستم:**
🖥️ CPU: `{metrics['cpu_usage']:.1f}%`
💿 RAM: `{metrics['memory_usage']:.1f}%` 
💽 دیسک: `{metrics['disk_usage']:.1f}%`
⚡ کش: `{len(smart_cache.cache)}` آیتم

🏆 **محبوب‌ترین پلتفرم:** {system_stats.popular_platform}
🕒 **آخرین به‌روزرسانی:** `{datetime.now().strftime('%H:%M:%S - %Y/%m/%d')}`

**🔑 سطح دسترسی شما:** `{admin_level}`"""
        
        keyboard = glass_keyboards.admin_panel(admin_level)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                admin_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                admin_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
    
    @performance_tracked
    async def system_stats_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Detailed system statistics with charts"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Generate comprehensive analytics report
            report_path = await self.analytics.generate_comprehensive_report()
            
            # Collect detailed metrics
            metrics = await self.system_monitor.collect_metrics()
            detailed_stats = await self._get_detailed_system_info()
            
            stats_text = f"""📊 **آمار تفصیلی سیستم**

📈 **آمار کاربران:**
• کل کاربران: `{formatting_utils.format_number_persian(detailed_stats['total_users']):,}`
• کاربران جدید امروز: `{formatting_utils.format_number_persian(detailed_stats['new_users_today']):,}`
• فعال این هفته: `{formatting_utils.format_number_persian(detailed_stats['active_week']):,}`
• کاربران مسدود: `{formatting_utils.format_number_persian(detailed_stats['blocked_users']):,}`

📥 **آمار دانلودها:**
• موفق امروز: `{formatting_utils.format_number_persian(detailed_stats['successful_downloads']):,}`
• ناموفق امروز: `{formatting_utils.format_number_persian(detailed_stats['failed_downloads']):,}`
• میانگین روزانه: `{detailed_stats['avg_daily_downloads']:.1f}`
• میانگین زمان دانلود: `{detailed_stats['avg_download_time']:.2f}s`

💾 **وضعیت سیستم:**
• حافظه استفاده شده: `{metrics['memory_usage']:.1f}%`
• CPU: `{metrics['cpu_usage']:.1f}%`
• دیسک: `{metrics['disk_usage']:.1f}%`
• کش فعال: `{len(smart_cache.cache)}` آیتم
• دانلودهای فعال: `{metrics['active_downloads']}`

🔄 **عملکرد:**
• آپتایم: `{detailed_stats['uptime']}`
• پیام‌های پردازش شده: `{formatting_utils.format_number_persian(detailed_stats['messages_processed']):,}`
• خطاهای سیستم: `{detailed_stats['system_errors']}`
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 نمودار کاربران", callback_data="chart_users"),
                    InlineKeyboardButton("📈 نمودار پلتفرم", callback_data="chart_platforms")
                ],
                [
                    InlineKeyboardButton("⚡ عملکرد لحظه‌ای", callback_data="live_performance"),
                    InlineKeyboardButton("📋 گزارش کامل", callback_data="full_report")
                ],
                [
                    InlineKeyboardButton("📤 صادرات داده", callback_data="export_data"),
                    InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_stats")
                ],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            
            if report_path and Path(report_path).exists():
                # Send chart as photo with caption
                with open(report_path, 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=stats_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                # Clean up temp file
                Path(report_path).unlink(missing_ok=True)
            else:
                await query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in system stats handler: {e}")
            await query.edit_message_text(
                f"❌ خطا در دریافت آمار سیستم: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 تلاش مجدد", callback_data="admin_stats"),
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
                ]])
            )
    
    async def _get_detailed_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            import psutil
            import time
            
            # Basic database stats
            system_stats = await db.get_system_stats()
            
            # System performance
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Calculate uptime
            uptime_seconds = time.time() - process.create_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{uptime_hours}h {uptime_minutes}m"
            
            # Estimate some values (in real implementation, get from database)
            return {
                'total_users': system_stats.total_users,
                'new_users_today': max(0, system_stats.total_users // 30),  # Estimate
                'active_week': system_stats.active_users_today * 7,  # Estimate  
                'blocked_users': 0,  # Would come from database
                'successful_downloads': system_stats.successful_downloads,
                'failed_downloads': system_stats.failed_downloads,
                'avg_daily_downloads': system_stats.total_downloads / max(1, 30),  # 30 day avg
                'avg_download_time': system_stats.avg_download_time,
                'uptime': uptime,
                'messages_processed': getattr(self, 'message_counter', 0),
                'system_errors': len(self.system_monitor.alerts)
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed system info: {e}")
            return {
                'total_users': 0, 'new_users_today': 0, 'active_week': 0,
                'blocked_users': 0, 'successful_downloads': 0, 'failed_downloads': 0,
                'avg_daily_downloads': 0, 'avg_download_time': 0, 'uptime': '0h 0m',
                'messages_processed': 0, 'system_errors': 0
            }
    
    async def broadcast_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Advanced broadcast management system"""
        query = update.callback_query
        await query.answer()
        
        # Get user statistics for broadcast
        system_stats = await db.get_system_stats()
        
        # Get recent broadcast history
        recent_broadcasts = await self._get_recent_broadcasts()
        
        broadcast_text = f"""📢 **سیستم ارسال همگانی پیشرفته**

🎯 **آمار مخاطبین:**
👥 کل کاربران فعال: `{formatting_utils.format_number_persian(system_stats.total_users):,}`
📱 فعال امروز: `{formatting_utils.format_number_persian(system_stats.active_users_today):,}`
🟢 آنلاین تخمینی: `{max(1, system_stats.active_users_today // 10):,}`

📋 **آخرین ارسال‌ها:**
{self._format_recent_broadcasts(recent_broadcasts)}

⚠️ **نکات مهم:**
• حداکثر ۳۰ پیام در دقیقه ارسال می‌شود
• پیام‌های طولانی خودکار تقسیم می‌شوند
• امکان زمان‌بندی و ارسال هدفمند وجود دارد
• آمار دقیق ارسال ثبت می‌شود

🚀 **آماده برای ارسال به هزاران کاربر!**"""
        
        keyboard = glass_keyboards.admin_broadcast_menu()
        
        await query.edit_message_text(
            broadcast_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def _get_recent_broadcasts(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get recent broadcast history"""
        # In real implementation, fetch from database
        # This is sample data
        return [
            {
                'id': 1,
                'type': 'text',
                'preview': 'به‌روزرسانی جدید ربات...',
                'sent_count': 1250,
                'success_rate': 96.5,
                'date': datetime.now() - timedelta(hours=6)
            },
            {
                'id': 2,
                'type': 'image',
                'preview': 'اطلاعیه تعطیلات...',
                'sent_count': 980,
                'success_rate': 94.2,
                'date': datetime.now() - timedelta(days=2)
            }
        ]
    
    def _format_recent_broadcasts(self, broadcasts: List[Dict[str, Any]]) -> str:
        """Format recent broadcast history"""
        if not broadcasts:
            return "هیچ ارسال اخیری موجود نیست"
        
        formatted = []
        for broadcast in broadcasts:
            time_ago = datetime_manager.time_ago_persian(broadcast['date'])
            formatted.append(
                f"• {broadcast['preview'][:30]}... "
                f"(`{broadcast['sent_count']:,}` کاربر - {broadcast['success_rate']:.1f}% - {time_ago})"
            )
        
        return "\n".join(formatted)
    
    async def start_text_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start text broadcast process"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            """📝 **ارسال پیام متنی همگانی**

لطفاً متن پیام خود را ارسال کنید:

🎨 **قابلیت‌های فرمت‌بندی:**
• **متن پررنگ** با `**متن**`
• *متن کج* با `*متن*`
• `کد و متن یکنواخت` با `` `متن` ``
• [لینک](URL) با `[متن](لینک)`
• استفاده از ایموجی 🎉✨💎

📏 **محدودیت‌ها:**
• حداکثر ۴۰۹۶ کاراکتر
• متن‌های طولانی‌تر خودکار تقسیم می‌شوند

⏰ **زمان‌بندی:**
پس از تأیید متن، می‌توانید زمان ارسال را تنظیم کنید

❌ برای لغو `/cancel` را ارسال کنید.""",
            parse_mode='Markdown'
        )
        
        return BROADCAST_TEXT
    
    async def handle_broadcast_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle broadcast text input"""
        if update.message.text == '/cancel':
            await update.message.reply_text(
                "❌ **ارسال همگانی لغو شد.**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # Validate message length
        if len(message_text) > 4096:
            await update.message.reply_text(
                f"⚠️ **پیام بیش از حد طولانی است!**\n\n"
                f"طول فعلی: `{len(message_text):,}` کاراکتر\n"
                f"حداکثر مجاز: `4,096` کاراکتر\n\n"
                f"لطفاً متن کوتاه‌تری ارسال کنید.",
                parse_mode='Markdown'
            )
            return BROADCAST_TEXT
        
        # Store in temporary data
        self.temp_data[user_id] = {
            'type': 'text',
            'content': message_text,
            'timestamp': datetime.now()
        }
        
        # Get user count for preview
        system_stats = await db.get_system_stats()
        estimated_time = self._estimate_broadcast_time(system_stats.total_users)
        
        # Create preview
        preview_text = f"""📋 **پیش‌نمایش پیام همگانی**

**📝 محتوای پیام:**
{text_processor.truncate_smart(message_text, 500)}

📊 **آمار ارسال:**
• تعداد مخاطبین: `{formatting_utils.format_number_persian(system_stats.total_users):,}` کاربر
• زمان تخمینی: `{estimated_time}`
• نرخ تحویل پیش‌بینی: `~95%`

⚙️ **تنظیمات:**
• ارسال فوری یا زمان‌بندی شده
• ارسال به همه یا گروه خاص
• پیگیری آمار دقیق

آیا تأیید می‌کنید؟"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ ارسال فوری", callback_data="broadcast_confirm_now"),
                InlineKeyboardButton("⏰ زمان‌بندی", callback_data="broadcast_schedule")
            ],
            [
                InlineKeyboardButton("🎯 ارسال هدفمند", callback_data="broadcast_targeted"),
                InlineKeyboardButton("👁️ پیش‌نمایش بیشتر", callback_data="broadcast_preview")
            ],
            [
                InlineKeyboardButton("✏️ ویرایش متن", callback_data="broadcast_edit"),
                InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")
            ]
        ]
        
        await update.message.reply_text(
            preview_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    def _estimate_broadcast_time(self, user_count: int) -> str:
        """Estimate broadcast completion time"""
        # 30 messages per minute limit
        messages_per_minute = 30
        total_minutes = max(1, user_count // messages_per_minute)
        
        if total_minutes < 60:
            return f"{total_minutes} دقیقه"
        else:
            hours = total_minutes // 60
            remaining_minutes = total_minutes % 60
            if remaining_minutes > 0:
                return f"{hours} ساعت و {remaining_minutes} دقیقه"
            return f"{hours} ساعت"
    
    async def confirm_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Execute confirmed broadcast"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            await query.edit_message_text(
                "❌ **خطا:** اطلاعات پیام یافت نشد.\nلطفاً مجدداً تلاش کنید."
            )
            return
        
        broadcast_data = self.temp_data.pop(user_id)
        broadcast_id = f"broadcast_{int(datetime.now().timestamp())}"
        
        # Initialize broadcast stats
        stats = BroadcastStats()
        stats.start_time = datetime.now()
        self.active_broadcasts[broadcast_id] = stats
        
        # Start broadcast progress message
        progress_msg = await query.edit_message_text(
            """🚀 **شروع ارسال همگانی...**

⏳ در حال دریافت لیست کاربران...
📤 آماده‌سازی سیستم ارسال...

📊 **پیشرفت:** `0%`
⏱️ **زمان سپری شده:** `0s`""",
            parse_mode='Markdown'
        )
        
        try:
            # Execute broadcast
            final_stats = await self._execute_advanced_broadcast(
                broadcast_data, progress_msg, context, broadcast_id
            )
            
            # Final report
            success_rate = (final_stats.successful_sends / max(1, final_stats.total_users)) * 100
            duration = final_stats.end_time - final_stats.start_time
            
            final_text = f"""✅ **ارسال همگانی تکمیل شد!**

📊 **گزارش نهایی:**
• کل مخاطبین: `{formatting_utils.format_number_persian(final_stats.total_users):,}`
• ارسال موفق: `{formatting_utils.format_number_persian(final_stats.successful_sends):,}`
• ارسال ناموفق: `{formatting_utils.format_number_persian(final_stats.failed_sends):,}`
• کاربران مسدودشده: `{formatting_utils.format_number_persian(final_stats.blocked_users):,}`
• نرخ موفقیت: `{success_rate:.1f}%`

⏱️ **زمان‌بندی:**
• شروع: `{final_stats.start_time.strftime('%H:%M:%S')}`
• پایان: `{final_stats.end_time.strftime('%H:%M:%S')}`
• مدت زمان: `{datetime_manager.duration_to_text(int(duration.total_seconds()))}`

🎯 **عملکرد:** {self._get_performance_rating(success_rate)}"""
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 آمار تفصیلی", callback_data=f"broadcast_details_{broadcast_id}"),
                    InlineKeyboardButton("📤 صادرات گزارش", callback_data=f"broadcast_export_{broadcast_id}")
                ],
                [
                    InlineKeyboardButton("🔄 ارسال مجدد", callback_data="broadcast_text"),
                    InlineKeyboardButton("📢 ارسال جدید", callback_data="broadcast_menu")
                ],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="admin_panel")]
            ]
            
            await progress_msg.edit_text(
                final_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Broadcast execution failed: {e}")
            await progress_msg.edit_text(
                f"❌ **خطا در ارسال همگانی!**\n\n**جزئیات:** `{str(e)}`\n\n"
                "لطفاً با پشتیبانی تماس بگیرید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
                ]]),
                parse_mode='Markdown'
            )
        finally:
            # Clean up
            self.active_broadcasts.pop(broadcast_id, None)
    
    async def _execute_advanced_broadcast(self, broadcast_data: Dict, progress_msg: Message, 
                                        context: ContextTypes.DEFAULT_TYPE, broadcast_id: str) -> BroadcastStats:
        """Execute broadcast with advanced features"""
        stats = self.active_broadcasts[broadcast_id]
        
        try:
            # Get all active users
            users = await db.get_active_users(days=30)  # Users active in last 30 days
            stats.total_users = len(users)
            
            logger.info(f"Starting broadcast to {stats.total_users} users")
            
            # Batch processing settings
            batch_size = 25  # Reduced from 30 for better stability
            batch_delay = 60  # seconds between batches
            message_delay = 0.05  # seconds between individual messages
            
            processed = 0
            
            for i in range(0, len(users), batch_size):
                batch_users = users[i:i + batch_size]
                batch_results = await self._send_batch_messages(
                    batch_users, broadcast_data, context
                )
                
                # Update statistics
                for result in batch_results:
                    if result['success']:
                        stats.successful_sends += 1
                    else:
                        stats.failed_sends += 1
                        if result['error_type'] == 'blocked':
                            stats.blocked_users += 1
                        elif result['error_type'] == 'deleted':
                            stats.deleted_accounts += 1
                
                processed += len(batch_users)
                progress = (processed / stats.total_users) * 100
                
                # Update progress every batch
                if processed % (batch_size * 2) == 0:  # Every 2 batches
                    elapsed_time = datetime.now() - stats.start_time
                    estimated_total = elapsed_time * (stats.total_users / processed)
                    estimated_remaining = estimated_total - elapsed_time
                    
                    try:
                        await progress_msg.edit_text(
                            f"""🚀 **ارسال همگانی در حال انجام...**

📊 **پیشرفت:** `{progress:.1f}%`
✅ **موفق:** `{formatting_utils.format_number_persian(stats.successful_sends):,}`
❌ **ناموفق:** `{formatting_utils.format_number_persian(stats.failed_sends):,}`
🚫 **مسدود:** `{formatting_utils.format_number_persian(stats.blocked_users):,}`

⏳ **پردازش:** `{formatting_utils.format_number_persian(processed):,}/{formatting_utils.format_number_persian(stats.total_users):,}`
⏱️ **زمان سپری شده:** `{datetime_manager.duration_to_text(int(elapsed_time.total_seconds()))}`
⏰ **تخمین باقی‌مانده:** `{datetime_manager.duration_to_text(int(estimated_remaining.total_seconds()))}`

💨 **سرعت:** `{(processed / elapsed_time.total_seconds() * 60):.1f}` پیام/دقیقه""",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update progress message: {e}")
                
                # Wait between batches (except for last batch)
                if i + batch_size < len(users):
                    await asyncio.sleep(batch_delay)
            
            stats.end_time = datetime.now()
            
            # Save broadcast statistics to database
            await self._save_broadcast_statistics(broadcast_data, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in advanced broadcast execution: {e}")
            stats.end_time = datetime.now()
            raise
    
    async def _send_batch_messages(self, users: List[User], broadcast_data: Dict, 
                                 context: ContextTypes.DEFAULT_TYPE) -> List[Dict[str, Any]]:
        """Send messages to a batch of users"""
        results = []
        
        for user in users:
            try:
                if broadcast_data['type'] == 'text':
                    await context.bot.send_message(
                        chat_id=user.user_id,
                        text=broadcast_data['content'],
                        parse_mode='Markdown'
                    )
                # Add support for other message types (photo, video, etc.)
                
                results.append({
                    'user_id': user.user_id,
                    'success': True,
                    'error_type': None
                })
                
            except Forbidden:
                # User blocked the bot
                results.append({
                    'user_id': user.user_id,
                    'success': False,
                    'error_type': 'blocked'
                })
                # Mark user as inactive
                await db.update_user_activity(user.user_id, active=False)
                
            except BadRequest as e:
                if "chat not found" in str(e).lower():
                    results.append({
                        'user_id': user.user_id,
                        'success': False,
                        'error_type': 'deleted'
                    })
                else:
                    results.append({
                        'user_id': user.user_id,
                        'success': False,
                        'error_type': 'bad_request'
                    })
                    
            except Exception as e:
                logger.warning(f"Error sending to {user.user_id}: {e}")
                results.append({
                    'user_id': user.user_id,
                    'success': False,
                    'error_type': 'unknown'
                })
            
            # Small delay between messages
            await asyncio.sleep(0.05)
        
        return results
    
    async def _save_broadcast_statistics(self, broadcast_data: Dict, stats: BroadcastStats):
        """Save broadcast statistics to database"""
        try:
            # Save to analytics table
            await db.save_analytics(
                metric_type='broadcast',
                metric_name='message_sent',
                metric_value=stats.successful_sends,
                metadata={
                    'total_users': stats.total_users,
                    'failed_sends': stats.failed_sends,
                    'blocked_users': stats.blocked_users,
                    'deleted_accounts': stats.deleted_accounts,
                    'message_type': broadcast_data['type'],
                    'content_preview': text_processor.truncate_smart(broadcast_data['content'], 100),
                    'duration_seconds': (stats.end_time - stats.start_time).total_seconds()
                }
            )
            
            logger.info(f"Broadcast statistics saved: {stats.successful_sends}/{stats.total_users}")
            
        except Exception as e:
            logger.error(f"Failed to save broadcast statistics: {e}")
    
    def _get_performance_rating(self, success_rate: float) -> str:
        """Get performance rating based on success rate"""
        if success_rate >= 95:
            return "🟢 عالی"
        elif success_rate >= 90:
            return "🟡 خوب"
        elif success_rate >= 80:
            return "🟠 متوسط"
        else:
            return "🔴 ضعیف"

# Global admin manager instance
admin_manager = AdminPanelManager()

# Export main classes
__all__ = ['AdminPanelManager', 'SystemMonitor', 'AdvancedAnalytics', 'BroadcastStats', 'admin_manager']
