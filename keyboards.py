#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⌨️ Advanced Glass Morphism Keyboard System
🎨 Beautiful, Interactive, Type-Safe UI Components
"""

from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass
import json

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from config import config, platforms, messages

@dataclass
class KeyboardConfig:
    """Configuration for keyboard appearance"""
    max_buttons_per_row: int = 2
    use_emojis: bool = True
    show_back_button: bool = True
    back_button_text: str = "🔙 بازگشت"
    home_button_text: str = "🏠 خانه"

class GlassMorphKeyboards:
    """Advanced Glass Morphism keyboard system"""
    
    def __init__(self, keyboard_config: KeyboardConfig = None):
        self.config = keyboard_config or KeyboardConfig()
    
    # Main Navigation Keyboards
    def main_menu(self, user_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """Dynamic main menu based on user permissions"""
        keyboard = [
            [
                InlineKeyboardButton("📥 دانلود محتوا", callback_data="download_menu"),
                InlineKeyboardButton("📊 آمار شخصی", callback_data="user_stats")
            ],
            [
                InlineKeyboardButton("📜 تاریخچه", callback_data="download_history"),
                InlineKeyboardButton("⚙️ تنظیمات", callback_data="user_settings")
            ],
            [
                InlineKeyboardButton("🔍 جستجو", callback_data="search_menu"),
                InlineKeyboardButton("📚 راهنما", callback_data="help_menu")
            ]
        ]
        
        # Add premium features if enabled
        if config.enable_premium:
            keyboard.append([
                InlineKeyboardButton("💎 اشتراک ویژه", callback_data="premium_menu"),
                InlineKeyboardButton("🎁 کدهای تخفیف", callback_data="promo_codes")
            ])
        
        # Add admin panel for admins
        if user_id and user_id in config.admin_ids:
            keyboard.append([
                InlineKeyboardButton("👨‍💻 پنل مدیریت", callback_data="admin_panel")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🌟 درباره ربات", callback_data="about"),
            InlineKeyboardButton("📞 پشتیبانی", callback_data="support")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def download_platforms(self) -> InlineKeyboardMarkup:
        """Platform selection with dynamic loading"""
        keyboard = []
        row = []
        
        enabled_platforms = platforms.get_enabled_platforms()
        
        for platform_id, platform_config in enabled_platforms.items():
            button = InlineKeyboardButton(
                f"{platform_config.emoji} {platform_config.name}",
                callback_data=f"platform_{platform_id}"
            )
            row.append(button)
            
            # Create new row after max buttons
            if len(row) >= self.config.max_buttons_per_row:
                keyboard.append(row)
                row = []
        
        # Add remaining buttons
        if row:
            keyboard.append(row)
        
        # Quick download section
        keyboard.extend([
            [InlineKeyboardButton("⚡ دانلود سریع", callback_data="quick_download")],
            [InlineKeyboardButton("🎯 دانلود دسته‌ای", callback_data="batch_download")],
        ])
        
        # Navigation
        if self.config.show_back_button:
            keyboard.append([
                InlineKeyboardButton(self.config.back_button_text, callback_data="main_menu")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def quality_selection(self, platform: str, media_type: str = "video") -> InlineKeyboardMarkup:
        """Dynamic quality selection based on platform and media type"""
        keyboard = []
        
        if platform == 'youtube':
            if media_type == "video":
                keyboard = [
                    [
                        InlineKeyboardButton("🔥 4K Ultra", callback_data="quality_2160p"),
                        InlineKeyboardButton("⭐ Full HD", callback_data="quality_1080p")
                    ],
                    [
                        InlineKeyboardButton("💎 HD Ready", callback_data="quality_720p"),
                        InlineKeyboardButton("📱 Mobile", callback_data="quality_480p")
                    ],
                    [InlineKeyboardButton("🎵 صدا فقط", callback_data="quality_audio")]
                ]
            else:  # audio
                keyboard = [
                    [
                        InlineKeyboardButton("🔥 320 kbps", callback_data="quality_320"),
                        InlineKeyboardButton("⭐ 256 kbps", callback_data="quality_256")
                    ],
                    [
                        InlineKeyboardButton("💎 192 kbps", callback_data="quality_192"),
                        InlineKeyboardButton("📱 128 kbps", callback_data="quality_128")
                    ]
                ]
        
        elif platform == 'instagram':
            keyboard = [
                [
                    InlineKeyboardButton("🔥 کیفیت اصلی", callback_data="quality_original"),
                    InlineKeyboardButton("💎 بهینه شده", callback_data="quality_optimized")
                ]
            ]
        
        elif platform == 'spotify':
            keyboard = [
                [
                    InlineKeyboardButton("🎵 320 kbps", callback_data="quality_320"),
                    InlineKeyboardButton("🎶 256 kbps", callback_data="quality_256")
                ],
                [InlineKeyboardButton("🎼 128 kbps", callback_data="quality_128")]
            ]
        
        else:
            # Generic quality options
            keyboard = [
                [
                    InlineKeyboardButton("⭐ بهترین", callback_data="quality_best"),
                    InlineKeyboardButton("💎 متوسط", callback_data="quality_medium")
                ],
                [InlineKeyboardButton("📱 پایین", callback_data="quality_low")]
            ]
        
        # Add format selection for some platforms
        if platform in ['youtube', 'twitter']:
            keyboard.append([
                InlineKeyboardButton("🎥 ویدئو", callback_data=f"format_video_{platform}"),
                InlineKeyboardButton("🎵 صدا", callback_data=f"format_audio_{platform}")
            ])
        
        # Navigation
        keyboard.extend([
            [
                InlineKeyboardButton("🔙 انتخاب پلتفرم", callback_data="download_menu"),
                InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
            ]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def download_progress(self, download_id: str, progress: int = 0) -> InlineKeyboardMarkup:
        """Dynamic download progress keyboard"""
        keyboard = [
            [InlineKeyboardButton(f"📊 پیشرفت: {progress}%", callback_data=f"progress_{download_id}")],
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_{download_id}"),
                InlineKeyboardButton("⏸️ توقف", callback_data=f"pause_{download_id}")
            ],
            [InlineKeyboardButton("❌ لغو دانلود", callback_data=f"cancel_{download_id}")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def download_complete(self, download_id: str, has_variants: bool = False) -> InlineKeyboardMarkup:
        """Post-download actions keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📤 اشتراک‌گذاری", callback_data=f"share_{download_id}"),
                InlineKeyboardButton("💾 ذخیره", callback_data=f"save_{download_id}")
            ],
            [
                InlineKeyboardButton("🔄 دانلود مجدد", callback_data=f"redownload_{download_id}"),
                InlineKeyboardButton("ℹ️ جزئیات", callback_data=f"details_{download_id}")
            ]
        ]
        
        if has_variants:
            keyboard.insert(0, [
                InlineKeyboardButton("🎯 کیفیت‌های دیگر", callback_data=f"variants_{download_id}")
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("⭐ امتیاز دهید", callback_data=f"rate_{download_id}"),
                InlineKeyboardButton("🐛 گزارش مشکل", callback_data=f"report_{download_id}")
            ],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    # User Interface Keyboards
    def user_stats_menu(self) -> InlineKeyboardMarkup:
        """User statistics and analytics"""
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار کلی", callback_data="stats_general"),
                InlineKeyboardButton("📈 نمودار فعالیت", callback_data="stats_chart")
            ],
            [
                InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="stats_ranking"),
                InlineKeyboardButton("📱 پلتفرم‌ها", callback_data="stats_platforms")
            ],
            [
                InlineKeyboardButton("📅 آمار ماهانه", callback_data="stats_monthly"),
                InlineKeyboardButton("⏰ آمار زمانی", callback_data="stats_timeline")
            ],
            [
                InlineKeyboardButton("📄 گزارش PDF", callback_data="stats_export"),
                InlineKeyboardButton("📊 مقایسه", callback_data="stats_compare")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def settings_menu(self, user_settings: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """User settings with current values"""
        settings = user_settings or {}
        
        # Dynamic settings based on current values
        lang_emoji = "🇮🇷" if settings.get('language', 'fa') == 'fa' else "🇺🇸"
        notif_emoji = "🔔" if settings.get('notifications', True) else "🔕"
        quality_emoji = "🔥" if settings.get('auto_quality', True) else "⚙️"
        
        keyboard = [
            [
                InlineKeyboardButton(f"{lang_emoji} زبان", callback_data="settings_language"),
                InlineKeyboardButton(f"{notif_emoji} اعلان‌ها", callback_data="settings_notifications")
            ],
            [
                InlineKeyboardButton(f"{quality_emoji} کیفیت خودکار", callback_data="settings_quality"),
                InlineKeyboardButton("📁 مدیریت فایل", callback_data="settings_files")
            ],
            [
                InlineKeyboardButton("🔐 حریم خصوصی", callback_data="settings_privacy"),
                InlineKeyboardButton("🎨 ظاهر", callback_data="settings_theme")
            ],
            [
                InlineKeyboardButton("📞 مخاطبین", callback_data="settings_contacts"),
                InlineKeyboardButton("💾 پشتیبان", callback_data="settings_backup")
            ],
            [
                InlineKeyboardButton("🔄 بازنشانی", callback_data="settings_reset"),
                InlineKeyboardButton("📤 صادرات", callback_data="settings_export")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def help_menu(self) -> InlineKeyboardMarkup:
        """Comprehensive help system"""
        keyboard = [
            [
                InlineKeyboardButton("🚀 شروع سریع", callback_data="help_quickstart"),
                InlineKeyboardButton("📖 راهنمای کامل", callback_data="help_complete")
            ],
            [
                InlineKeyboardButton("❓ سوالات متداول", callback_data="help_faq"),
                InlineKeyboardButton("🎥 آموزش ویدئویی", callback_data="help_video")
            ],
            [
                InlineKeyboardButton("🌐 پلتفرم‌ها", callback_data="help_platforms"),
                InlineKeyboardButton("🔧 عیب‌یابی", callback_data="help_troubleshooting")
            ],
            [
                InlineKeyboardButton("💡 نکات و ترفندها", callback_data="help_tips"),
                InlineKeyboardButton("🆕 ویژگی‌های جدید", callback_data="help_new_features")
            ],
            [
                InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="help_contact"),
                InlineKeyboardButton("🐛 گزارش باگ", callback_data="help_report_bug")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    # Premium Features Keyboards
    def premium_menu(self, is_premium: bool = False) -> InlineKeyboardMarkup:
        """Premium subscription management"""
        if is_premium:
            keyboard = [
                [
                    InlineKeyboardButton("✨ وضعیت اشتراک", callback_data="premium_status"),
                    InlineKeyboardButton("📊 مصرف", callback_data="premium_usage")
                ],
                [
                    InlineKeyboardButton("🎯 ویژگی‌های ویژه", callback_data="premium_features"),
                    InlineKeyboardButton("🔄 تمدید", callback_data="premium_renew")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("⭐ خرید اشتراک", callback_data="premium_buy"),
                    InlineKeyboardButton("🎁 امتحان رایگان", callback_data="premium_trial")
                ],
                [
                    InlineKeyboardButton("💎 مزایای ویژه", callback_data="premium_benefits"),
                    InlineKeyboardButton("💰 قیمت‌ها", callback_data="premium_pricing")
                ]
            ]
        
        keyboard.extend([
            [
                InlineKeyboardButton("🎟️ کد تخفیف", callback_data="premium_promo"),
                InlineKeyboardButton("🎁 معرفی دوستان", callback_data="premium_referral")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    # Admin Panel Keyboards
    def admin_panel(self, admin_level: str = "admin") -> InlineKeyboardMarkup:
        """Multi-level admin panel"""
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار سیستم", callback_data="admin_stats"),
                InlineKeyboardButton("👥 کاربران", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("📥 دانلودها", callback_data="admin_downloads"),
                InlineKeyboardButton("🔧 سیستم", callback_data="admin_system")
            ],
            [
                InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast"),
                InlineKeyboardButton("🎯 تحلیل‌ها", callback_data="admin_analytics")
            ]
        ]
        
        if admin_level == "super_admin":
            keyboard.extend([
                [
                    InlineKeyboardButton("👨‍💻 مدیران", callback_data="admin_manage_admins"),
                    InlineKeyboardButton("🛠️ پیکربندی", callback_data="admin_config")
                ],
                [
                    InlineKeyboardButton("💾 پشتیبان", callback_data="admin_backup"),
                    InlineKeyboardButton("🚨 امنیت", callback_data="admin_security")
                ]
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs"),
                InlineKeyboardButton("⚡ عملکرد", callback_data="admin_performance")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def admin_broadcast_menu(self) -> InlineKeyboardMarkup:
        """Broadcast message management"""
        keyboard = [
            [
                InlineKeyboardButton("📝 پیام متنی", callback_data="broadcast_text"),
                InlineKeyboardButton("🖼️ پیام تصویری", callback_data="broadcast_image")
            ],
            [
                InlineKeyboardButton("🎥 پیام ویدئویی", callback_data="broadcast_video"),
                InlineKeyboardButton("🎵 پیام صوتی", callback_data="broadcast_audio")
            ],
            [
                InlineKeyboardButton("📁 ارسال فایل", callback_data="broadcast_file"),
                InlineKeyboardButton("🔗 پیام لینکی", callback_data="broadcast_link")
            ],
            [
                InlineKeyboardButton("🎯 ارسال هدفمند", callback_data="broadcast_targeted"),
                InlineKeyboardButton("📅 زمان‌بندی", callback_data="broadcast_scheduled")
            ],
            [
                InlineKeyboardButton("📊 آمار ارسال", callback_data="broadcast_stats"),
                InlineKeyboardButton("📜 تاریخچه", callback_data="broadcast_history")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    # Utility Keyboards
    def confirmation_dialog(self, action: str, item_id: str = "", 
                          custom_text: Dict[str, str] = None) -> InlineKeyboardMarkup:
        """Confirmation dialog with custom text"""
        texts = custom_text or {
            'confirm': '✅ تأیید',
            'cancel': '❌ لغو'
        }
        
        keyboard = [
            [
                InlineKeyboardButton(texts['confirm'], callback_data=f"confirm_{action}_{item_id}"),
                InlineKeyboardButton(texts['cancel'], callback_data=f"cancel_{action}")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def pagination(self, current_page: int, total_pages: int, prefix: str,
                   show_numbers: bool = True) -> InlineKeyboardMarkup:
        """Advanced pagination with jump options"""
        keyboard = []
        
        if total_pages <= 1:
            return InlineKeyboardMarkup(keyboard)
        
        # Navigation row
        nav_row = []
        
        # First page
        if current_page > 1:
            nav_row.append(InlineKeyboardButton("⏪", callback_data=f"{prefix}_page_1"))
        
        # Previous page
        if current_page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}_page_{current_page-1}"))
        
        # Current page indicator
        if show_numbers:
            nav_row.append(InlineKeyboardButton(
                f"📄 {current_page}/{total_pages}", 
                callback_data=f"{prefix}_current"
            ))
        
        # Next page
        if current_page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}_page_{current_page+1}"))
        
        # Last page
        if current_page < total_pages:
            nav_row.append(InlineKeyboardButton("⏩", callback_data=f"{prefix}_page_{total_pages}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Jump to page options for large page counts
        if total_pages > 10:
            jump_row = []
            jump_options = []
            
            # Calculate jump points
            if total_pages <= 50:
                step = max(1, total_pages // 5)
                jump_options = list(range(step, total_pages, step))
            else:
                # For very large page counts, show percentile jumps
                jump_options = [
                    total_pages // 4,    # 25%
                    total_pages // 2,    # 50%  
                    total_pages * 3 // 4 # 75%
                ]
            
            for page in jump_options[:3]:  # Limit to 3 jump options
                if page != current_page and 1 <= page <= total_pages:
                    jump_row.append(InlineKeyboardButton(
                        f"{page}", 
                        callback_data=f"{prefix}_page_{page}"
                    ))
            
            if jump_row:
                keyboard.append(jump_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def inline_search(self, query: str = "", results_count: int = 0) -> InlineKeyboardMarkup:
        """Inline search interface"""
        keyboard = [
            [InlineKeyboardButton(f"🔍 جستجو: {query}", switch_inline_query_current_chat=query)]
        ]
        
        if results_count > 0:
            keyboard.append([
                InlineKeyboardButton(f"📊 {results_count} نتیجه", callback_data="search_results")
            ])
        
        keyboard.extend([
            [
                InlineKeyboardButton("🔄 جستجوی جدید", switch_inline_query_current_chat=""),
                InlineKeyboardButton("📚 راهنما جستجو", callback_data="search_help")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)

# Specialized keyboard builders
class KeyboardBuilder:
    """Advanced keyboard builder with templates"""
    
    @staticmethod
    def build_from_config(config_data: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Build keyboard from JSON configuration"""
        keyboard = []
        
        for row_config in config_data.get('rows', []):
            row = []
            for button_config in row_config:
                button = InlineKeyboardButton(
                    text=button_config['text'],
                    callback_data=button_config.get('callback_data'),
                    url=button_config.get('url'),
                    switch_inline_query=button_config.get('switch_inline_query'),
                    switch_inline_query_current_chat=button_config.get('switch_inline_query_current_chat')
                )
                row.append(button)
            keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def build_list_keyboard(items: List[Dict[str, str]], prefix: str = "item",
                          columns: int = 1) -> InlineKeyboardMarkup:
        """Build keyboard from list of items"""
        keyboard = []
        row = []
        
        for i, item in enumerate(items):
            button = InlineKeyboardButton(
                item['text'],
                callback_data=f"{prefix}_{item.get('id', i)}"
            )
            row.append(button)
            
            if len(row) >= columns:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)

# Reply keyboard utilities
class ReplyKeyboards:
    """Reply keyboard management"""
    
    @staticmethod
    def contact_request() -> ReplyKeyboardMarkup:
        """Request contact information"""
        keyboard = [
            [KeyboardButton("📱 اشتراک شماره تماس", request_contact=True)],
            [KeyboardButton("❌ انصراف")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def location_request() -> ReplyKeyboardMarkup:
        """Request location information"""
        keyboard = [
            [KeyboardButton("📍 اشتراک موقعیت مکانی", request_location=True)],
            [KeyboardButton("❌ انصراف")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def quick_actions() -> ReplyKeyboardMarkup:
        """Quick action shortcuts"""
        keyboard = [
            ["📥 دانلود", "📊 آمار"],
            ["📚 راهنما", "⚙️ تنظیمات"],
            ["🏠 منوی اصلی"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def remove() -> ReplyKeyboardRemove:
        """Remove reply keyboard"""
        return ReplyKeyboardRemove()

# Global instances
glass_keyboards = GlassMorphKeyboards()
keyboard_builder = KeyboardBuilder()
reply_keyboards = ReplyKeyboards()

# Export main classes
__all__ = [
    'GlassMorphKeyboards', 'KeyboardBuilder', 'ReplyKeyboards', 'KeyboardConfig',
    'glass_keyboards', 'keyboard_builder', 'reply_keyboards'
]
