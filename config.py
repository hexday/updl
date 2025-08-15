import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class DownloadEngineConfig:
    enabled: bool
    priority: int
    timeout: int
    max_retries: int
    chunk_size: int

@dataclass
class TelegramConfig:
    bot_token: str
    channel_id: int
    use_premium: bool
    chunk_upload: bool
    max_file_size: int
    connection_pool_size: int
    timeout: int

@dataclass
class ServerConfig:
    host: str = "65.109.183.66"
    port: int = 8000
    debug: bool = False
    max_workers: int = 4
    session_timeout: int = 86400  # 24 hours

class ProfessionalConfig:
    def __init__(self):
        # Base directories
        self.BASE_DIR = Path(__file__).parent
        self.DATA_DIR = self.BASE_DIR / "data"
        self.DOWNLOADS_DIR = self.BASE_DIR / "downloads"
        self.UPLOADS_DIR = self.BASE_DIR / "uploads"
        self.TEMP_DIR = self.BASE_DIR / "temp"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        
        # Database
        self.DATABASE_PATH = self.DATA_DIR / "professional_dm.db"
        self.CONFIG_FILE = self.DATA_DIR / "config.json"
        
        # Authentication
        self.LOGIN_USERNAME = "admin"
        self.LOGIN_PASSWORD = "UltraPro2025!"
        self.SECRET_KEY = "professional-dm-ultra-secure-2025"
        
        # Download Engines Configuration
        self.ENGINES = {
            'yt-dlp': DownloadEngineConfig(
                enabled=True,
                priority=1,
                timeout=300,
                max_retries=3,
                chunk_size=16384
            ),
            'aria2': DownloadEngineConfig(
                enabled=True,
                priority=2,
                timeout=600,
                max_retries=5,
                chunk_size=32768
            ),
            'requests': DownloadEngineConfig(
                enabled=True,
                priority=3,
                timeout=300,
                max_retries=3,
                chunk_size=8192
            ),
            'wget': DownloadEngineConfig(
                enabled=True,
                priority=4,
                timeout=600,
                max_retries=2,
                chunk_size=16384
            ),
            'curl': DownloadEngineConfig(
                enabled=True,
                priority=5,
                timeout=300,
                max_retries=2,
                chunk_size=8192
            )
        }
        
        # Telegram Configuration
        self.TELEGRAM = TelegramConfig(
            bot_token="8087530834:AAHX70wotxivusp5HQmp-FJdH0gcfxxG1GA",
            channel_id=-1002754078176,
            use_premium=False,
            chunk_upload=True,
            max_file_size=4 * 1024 * 1024 * 1024,  # 4GB for premium
            connection_pool_size=100,
            timeout=300
        )
        
        # Server Configuration
        self.SERVER = ServerConfig()
        
        # File Type Configurations
        self.FILE_TYPES = {
            'video': {
                'extensions': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
                'max_size': 4 * 1024 * 1024 * 1024,  # 4GB
                'compression': True,
                'thumbnail': True
            },
            'audio': {
                'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
                'max_size': 2 * 1024 * 1024 * 1024,  # 2GB
                'compression': False,
                'thumbnail': True
            },
            'image': {
                'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
                'max_size': 100 * 1024 * 1024,  # 100MB
                'compression': True,
                'thumbnail': False
            },
            'document': {
                'extensions': ['.pdf', '.doc', '.docx', '.txt', '.zip', '.rar', '.7z'],
                'max_size': 2 * 1024 * 1024 * 1024,  # 2GB
                'compression': False,
                'thumbnail': False
            }
        }
        
        # Platform Configurations
        self.PLATFORMS = {
            'youtube': {
                'domains': ['youtube.com', 'youtu.be', 'm.youtube.com'],
                'engine': 'yt-dlp',
                'format': 'best[height<=1080]',
                'extract_audio': True
            },
            'instagram': {
                'domains': ['instagram.com', 'instagr.am'],
                'engine': 'yt-dlp',
                'format': 'best',
                'extract_audio': False
            },
            'twitter': {
                'domains': ['twitter.com', 'x.com', 't.co'],
                'engine': 'yt-dlp',
                'format': 'best',
                'extract_audio': False
            },
            'tiktok': {
                'domains': ['tiktok.com', 'vm.tiktok.com'],
                'engine': 'yt-dlp',
                'format': 'best',
                'extract_audio': True
            },
            'facebook': {
                'domains': ['facebook.com', 'fb.com', 'fb.watch'],
                'engine': 'yt-dlp',
                'format': 'best',
                'extract_audio': False
            }
        }
        
        self.setup_directories()
        self.load_config()
    
    def setup_directories(self):
        """Create all required directories"""
        directories = [
            self.DATA_DIR, self.DOWNLOADS_DIR, self.UPLOADS_DIR,
            self.TEMP_DIR, self.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Directory ready: {directory}")
    
    def load_config(self):
        """Load configuration from JSON file"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Update configurations from file
                if 'telegram' in data:
                    for key, value in data['telegram'].items():
                        if hasattr(self.TELEGRAM, key):
                            setattr(self.TELEGRAM, key, value)
                
                if 'server' in data:
                    for key, value in data['server'].items():
                        if hasattr(self.SERVER, key):
                            setattr(self.SERVER, key, value)
                
                print("✅ Configuration loaded from file")
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}")
    
    def save_config(self):
        """Save configuration to JSON file"""
        try:
            config_data = {
                'telegram': asdict(self.TELEGRAM),
                'server': asdict(self.SERVER),
                'engines': {k: asdict(v) for k, v in self.ENGINES.items()},
                'file_types': self.FILE_TYPES,
                'platforms': self.PLATFORMS
            }
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print("✅ Configuration saved to file")
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
    
    def get_engine_by_priority(self) -> List[str]:
        """Get engines sorted by priority"""
        enabled_engines = {k: v for k, v in self.ENGINES.items() if v.enabled}
        return sorted(enabled_engines.keys(), key=lambda x: enabled_engines[x].priority)
    
    def detect_file_type(self, filename: str) -> str:
        """Detect file type from extension"""
        ext = Path(filename).suffix.lower()
        
        for file_type, config in self.FILE_TYPES.items():
            if ext in config['extensions']:
                return file_type
        
        return 'document'  # Default
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL"""
        url_lower = url.lower()
        
        for platform, config in self.PLATFORMS.items():
            if any(domain in url_lower for domain in config['domains']):
                return platform
        
        return None

# Global configuration instance
config = ProfessionalConfig()
