#!/usr/bin/env python3
"""
Professional Download Manager
Ultra Advanced Multi-Engine Download System with Telegram Integration

Features:
- Multi-engine download support (yt-dlp, aria2, requests, wget, curl)
- Professional web interface with real-time updates
- Telegram bot integration with smart upload strategies
- Comprehensive file management and analytics
- Advanced logging and monitoring
- Resume capability and error recovery
- Support for all major platforms and file types

Author: Professional Download Manager Team
Version: 2.0.0
"""

import os
import sys
import signal
import atexit
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from database import db
from downloader import downloader
from telegram_bot import telegram_bot
from file_manager import file_manager
from logger import logger
from web_interface import app
from api_routes import api

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    PROFESSIONAL DOWNLOAD MANAGER v2.0                       ║
║                                                                              ║
║                        Ultra Advanced • Multi-Engine                        ║
║                    Telegram Integration • Real-time UI                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

🚀 Starting Professional Download Manager...
"""
    print(banner)

def print_system_info():
    """Print system information"""
    print("📋 SYSTEM INFORMATION")
    print("=" * 50)
    print(f"📁 Downloads Directory: {config.DOWNLOADS_DIR}")
    print(f"📤 Uploads Directory: {config.UPLOADS_DIR}")
    print(f"💾 Database: {config.DATABASE_PATH}")
    print(f"📝 Logs Directory: {config.LOGS_DIR}")
    print(f"🔐 Login: {config.LOGIN_USERNAME} / {config.LOGIN_PASSWORD}")
    print()

def print_engine_status():
    """Print available download engines"""
    print("🔧 DOWNLOAD ENGINES")
    print("=" * 50)
    
    from engines import engine_manager
    available_engines = engine_manager.available_engines
    
    if available_engines:
        for name, engine in available_engines.items():
            priority = config.ENGINES[name].priority
            print(f"✅ {name.upper():12} | Priority: {priority} | Available")
    else:
        print("❌ No download engines available!")
        print("   Please install at least one: yt-dlp, aria2, wget, curl")
    print()

def print_telegram_status():
    """Print Telegram bot status"""
    print("🤖 TELEGRAM INTEGRATION")
    print("=" * 50)
    
    telegram_status = telegram_bot.get_queue_status()
    
    if telegram_status['bot_available']:
        print("✅ Telegram Bot: Connected & Ready")
        print(f"📤 Upload Engines: {telegram_status['engines']}")
        print(f"📋 Queue Length: {telegram_status['queue_length']}")
        print(f"🔄 Processing: {telegram_status['processing_count']}")
    else:
        print("⚠️  Telegram Bot: Not configured")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID in config.py")
        print("   Or update them in the Settings panel")
    print()

def print_server_info():
    """Print server information"""
    print("🌐 WEB SERVER")
    print("=" * 50)
    print(f"🔗 URL: http://{config.SERVER.host}:{config.SERVER.port}")
    print(f"⚙️  Max Workers: {config.SERVER.max_workers}")
    print(f"🔒 Session Timeout: {config.SERVER.session_timeout // 3600} hours")
    print(f"🐞 Debug Mode: {'ON' if config.SERVER.debug else 'OFF'}")
    print()

def print_features():
    """Print feature list"""
    features = [
        "✨ Multi-Engine Downloads (yt-dlp, aria2, requests, wget, curl)",
        "🎯 Smart Platform Detection (YouTube, Instagram, Twitter, TikTok, Facebook)",
        "📱 Professional Web Interface with Real-time Updates",
        "🤖 Advanced Telegram Integration with Multiple Upload Strategies",
        "📊 Comprehensive Analytics and Performance Monitoring",
        "🔄 Resume Capability and Automatic Error Recovery",
        "📂 Professional File Management with Analysis",
        "🛡️  Robust Security and Session Management",
        "📝 Advanced Logging and Debugging",
        "⚡ High Performance with Multi-threading",
        "🎨 Modern UI with Dark Theme",
        "📈 Real-time Progress Tracking",
        "🔧 Extensive Configuration Options",
        "💾 SQLite Database with Performance Optimization",
        "🧹 Automatic Cleanup and Maintenance"
    ]
    
    print("✨ FEATURES")
    print("=" * 50)
    for feature in features:
        print(f"   {feature}")
    print()

def register_signal_handlers():
    """Register signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        shutdown_application()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)

def shutdown_application():
    """Graceful application shutdown"""
    print("🛑 Shutting down Professional Download Manager...")
    
    try:
        # Stop Telegram bot
        telegram_bot.stop()
        print("✅ Telegram bot stopped")
    except Exception as e:
        print(f"⚠️  Error stopping Telegram bot: {e}")
    
    try:
        # Cleanup temporary files
        cleaned = file_manager.cleanup_temp_files()
        print(f"✅ Cleaned up {cleaned} temporary files")
    except Exception as e:
        print(f"⚠️  Error cleaning temp files: {e}")
    
    try:
        # Save final statistics
        stats = downloader.get_stats()
        logger.get_logger('main').info(f"Final stats: {stats}")
        print("✅ Statistics saved")
    except Exception as e:
        print(f"⚠️  Error saving stats: {e}")
    
    print("✅ Professional Download Manager shutdown complete")

def check_dependencies():
    """Check for required dependencies"""
    print("🔍 DEPENDENCY CHECK")
    print("=" * 50)
    
    required_packages = [
        ('flask', 'Flask'),
        ('requests', 'Requests'),
        ('sqlite3', 'SQLite3'),
        ('pathlib', 'Pathlib')
    ]
    
    optional_packages = [
        ('telegram', 'python-telegram-bot (for Telegram integration)'),
        ('PIL', 'Pillow (for image processing)'),
        ('subprocess', 'Subprocess (for external tools)')
    ]
    
    missing_required = []
    missing_optional = []
    
    # Check required packages
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}: Available")
        except ImportError:
            print(f"❌ {name}: MISSING (REQUIRED)")
            missing_required.append(name)
    
    # Check optional packages
    for package, name in optional_packages:
        try:
            __import__(package)
            print(f"✅ {name}: Available")
        except ImportError:
            print(f"⚠️  {name}: Missing (Optional)")
            missing_optional.append(name)
    
    print()
    
    if missing_required:
        print("❌ CRITICAL: Missing required dependencies!")
        print("Please install:", ", ".join(missing_required))
        return False
    
    if missing_optional:
        print("⚠️  Some optional features may not work due to missing dependencies:")
        for dep in missing_optional:
            print(f"   - {dep}")
        print()
    
    return True

def check_external_tools():
    """Check for external tools availability"""
    print("🛠️  EXTERNAL TOOLS")
    print("=" * 50)
    
    tools = [
        ('yt-dlp', 'yt-dlp --version'),
        ('aria2c', 'aria2c --version'),
        ('wget', 'wget --version'),
        ('curl', 'curl --version'),
        ('ffmpeg', 'ffmpeg -version'),
        ('ffprobe', 'ffprobe -version')
    ]
    
    available_tools = []
    
    for tool_name, command in tools:
        try:
            import subprocess
            result = subprocess.run(command.split(), capture_output=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {tool_name}: Available")
                available_tools.append(tool_name)
            else:
                print(f"❌ {tool_name}: Not working")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            print(f"❌ {tool_name}: Not found")
    
    print()
    
    if not available_tools:
        print("⚠️  No external tools found. Only basic functionality will be available.")
        print("   Consider installing: yt-dlp, aria2, wget, curl, ffmpeg")
    
    return available_tools

def perform_startup_checks():
    """Perform comprehensive startup checks"""
    print("🔍 STARTUP CHECKS")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed. Exiting...")
        sys.exit(1)
    
    # Check external tools
    available_tools = check_external_tools()
    
    # Check directories
    print("📁 DIRECTORY STRUCTURE")
    print("=" * 50)
    directories = [
        config.DATA_DIR,
        config.DOWNLOADS_DIR,
        config.UPLOADS_DIR,
        config.TEMP_DIR,
        config.LOGS_DIR
    ]
    
    for directory in directories:
        if directory.exists():
            print(f"✅ {directory.name}: {directory}")
        else:
            print(f"❌ {directory.name}: Missing")
    
    print()
    
    # Check database
    print("💾 DATABASE CHECK")
    print("=" * 50)
    try:
        stats = db.get_stats()
        print(f"✅ Database: Connected")
        print(f"📊 Total Downloads: {stats.get('downloads', {}).get('completed', {}).get('count', 0)}")
        print(f"📤 Total Uploads: {stats.get('uploads', {}).get('count', 0)}")
    except Exception as e:
        print(f"❌ Database: Error - {e}")
    
    print()
    
    return True

def create_desktop_shortcut():
    """Create desktop shortcut (Windows only)"""
    try:
        import platform
        if platform.system() == "Windows":
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "Professional Download Manager.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = str(Path(__file__).resolve())
            shortcut.WorkingDirectory = str(Path(__file__).parent)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            
            print(f"🔗 Desktop shortcut created: {shortcut_path}")
    except Exception as e:
        pass  # Silently fail if desktop shortcut creation fails

def main():
    """Main application entry point"""
    try:
        # Print banner
        print_banner()
        
        # Register signal handlers
        register_signal_handlers()
        atexit.register(shutdown_application)
        
        # Perform startup checks
        if not perform_startup_checks():
            sys.exit(1)
        
        # Print system information
        print_system_info()
        print_engine_status()
        print_telegram_status()
        print_server_info()
        print_features()
        
        # Create desktop shortcut (Windows)
        create_desktop_shortcut()
        
        # Register API routes
        app.register_blueprint(api)
        
        # Initialize logging
        logger.get_logger('main').info("Professional Download Manager starting up")
        logger.get_logger('main').info(f"Configuration loaded from: {config.CONFIG_FILE}")
        
        # Print startup complete message
        print("🎯 READY TO SERVE")
        print("=" * 60)
        print(f"✨ Professional Download Manager is now running!")
        print(f"🌐 Open your browser and navigate to: http://{config.SERVER.host}:{config.SERVER.port}")
        print(f"🔐 Login with: {config.LOGIN_USERNAME} / {config.LOGIN_PASSWORD}")
        print()
        print("📝 Available endpoints:")
        print(f"   🏠 Main Interface: http://{config.SERVER.host}:{config.SERVER.port}/")
        print(f"   🔌 API Base: http://{config.SERVER.host}:{config.SERVER.port}/api/")
        print(f"   📊 Health Check: http://{config.SERVER.host}:{config.SERVER.port}/api/telegram/status")
        print()
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Start the web server
        app.run(
            host=config.SERVER.host,
            port=config.SERVER.port,
            debug=config.SERVER.debug,
            threaded=True,
            use_reloader=False  # Disable reloader to prevent issues with threading
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        shutdown_application()
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.get_logger('error').error(f"Fatal error: {e}")
        shutdown_application()
        sys.exit(1)



def setup_periodic_cleanup():
    """Setup periodic cleanup tasks"""
    import threading
    
    def cleanup_task():
        while True:
            try:
                time.sleep(300)  # Every 5 minutes
                file_manager.cleanup_expired_locks()
                
                # Every hour
                if datetime.now().minute == 0:
                    file_manager.cleanup_temp_files()
                    
            except Exception as e:
                logger.get_logger('error').error(f"Cleanup task error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True, name="CleanupTask")
    cleanup_thread.start()
    logger.get_logger('main').info("Periodic cleanup task started")

if __name__ == '__main__':
    # Ensure we're running with Python 3.7+
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required!")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    # Set UTF-8 encoding for Windows
    if sys.platform.startswith('win'):
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            pass
    setup_periodic_cleanup()

    # Run the application
    main()
