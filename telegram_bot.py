import os
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import json
import html
import re

try:
    from telegram import Bot
    from telegram.request import HTTPXRequest
    from telegram.constants import ParseMode
    from telegram.error import TelegramError, RetryAfter, BadRequest, NetworkError
    import httpx
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from config import config
from database import db
from logger import logger

class UltimateTelegramBot:
    def __init__(self):
        self.bot = None
        self.upload_engines = []
        self.upload_queue = []
        self.processing_files = set()
        self.failed_files = set()  # Track failed uploads
        self.worker_running = False
        self.worker_thread = None
        self.loop = None
        
        if self._should_init_bot():
            self.init_bot()
        else:
            logger.get_logger('telegram').warning("Telegram bot not configured")
    
    def _should_init_bot(self) -> bool:
        """Check if bot should be initialized"""
        return (TELEGRAM_AVAILABLE and 
                config.TELEGRAM.bot_token != "YOUR_BOT_TOKEN_HERE" and
                config.TELEGRAM.bot_token.strip())
    
    def init_bot(self):
        """Initialize Telegram bot with robust connection handling"""
        try:
            # Create ultra-robust request handler
            custom_request = HTTPXRequest(
                connection_pool_size=100,  # Increased pool size
                read_timeout=60,
                write_timeout=120,
                connect_timeout=30,
                pool_timeout=120,  # Increased timeout
                media_write_timeout=300,  # 5 minutes for large files
                http2=False,  # Disable HTTP/2 for stability
                socket_options=[(41, 1)],  # TCP_NODELAY
            )
            
            self.bot = Bot(token=config.TELEGRAM.bot_token, request=custom_request)
            
            # Initialize upload engines
            self._init_upload_engines()
            
            # Test bot connection in separate thread
            test_thread = threading.Thread(target=self._test_bot_connection, daemon=True)
            test_thread.start()
            
            # Start worker
            self.start_worker()
            
        except Exception as e:
            logger.get_logger('error').error(f"Telegram bot initialization failed: {e}")
            self.bot = None
    
    def _init_upload_engines(self):
        """Initialize different upload strategies"""
        self.upload_engines = [
            {
                'name': 'premium_ultra', 
                'max_size': 4 * 1024 * 1024 * 1024, 
                'chunk_size': 1024 * 1024,
                'timeout': 300
            },
            {
                'name': 'premium_large', 
                'max_size': 2 * 1024 * 1024 * 1024, 
                'chunk_size': 512 * 1024,
                'timeout': 240
            },
            {
                'name': 'regular_large', 
                'max_size': 50 * 1024 * 1024, 
                'chunk_size': 256 * 1024,
                'timeout': 180
            },
            {
                'name': 'regular_small', 
                'max_size': 20 * 1024 * 1024, 
                'chunk_size': 128 * 1024,
                'timeout': 120
            }
        ]
        
        logger.get_logger('telegram').info(f"Initialized {len(self.upload_engines)} upload engines")
    
    def _test_bot_connection(self):
        """Test bot connectivity with proper loop management"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Create completely isolated event loop
                test_loop = asyncio.new_event_loop()
                
                try:
                    asyncio.set_event_loop(test_loop)
                    
                    async def test_connection():
                        return await asyncio.wait_for(
                            self.bot.get_me(), 
                            timeout=15
                        )
                    
                    bot_info = test_loop.run_until_complete(test_connection())
                    logger.get_logger('telegram').info(f"Telegram bot connected: @{bot_info.username}")
                    return True
                    
                finally:
                    # Properly close the loop
                    try:
                        test_loop.close()
                    except:
                        pass
                        
            except Exception as e:
                retry_count += 1
                logger.get_logger('error').error(f"Telegram bot test failed (attempt {retry_count}): {e}")
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)  # Exponential backoff
                
        self.bot = None
        return False
    
    def start_worker(self):
        """Start upload worker thread"""
        if not self.worker_running and self.bot:
            self.worker_running = True
            self.worker_thread = threading.Thread(
                target=self._upload_worker, 
                daemon=True,
                name="TelegramWorker"
            )
            self.worker_thread.start()
            logger.get_logger('telegram').info("Professional Telegram upload worker started")
    
    def _upload_worker(self):
        """Main upload worker with bulletproof loop management"""
        logger.get_logger('telegram').info("Telegram upload worker started")
        
        try:
            # Create dedicated event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Set loop exception handler
            def exception_handler(loop, context):
                logger.get_logger('error').error(f"Loop exception: {context}")
            
            self.loop.set_exception_handler(exception_handler)
            
            # Run the main coroutine
            self.loop.run_until_complete(self._process_upload_queue())
            
        except Exception as e:
            logger.get_logger('error').error(f"Upload worker crashed: {e}")
        finally:
            self._cleanup_loop()
    
    def _cleanup_loop(self):
        """Clean up event loop safely"""
        try:
            if self.loop and not self.loop.is_closed():
                # Cancel all pending tasks
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                # Wait for cancellation with timeout
                if pending:
                    try:
                        self.loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=10
                            )
                        )
                    except asyncio.TimeoutError:
                        logger.get_logger('telegram').warning("Some tasks didn't cancel in time")
                
                # Close the loop
                self.loop.close()
                
            logger.get_logger('telegram').info("Telegram worker loop closed")
        except Exception as e:
            logger.get_logger('error').error(f"Error closing loop: {e}")
    
    async def _process_upload_queue(self):
        """Process upload queue with robust error handling"""
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while self.worker_running:
            try:
                if not self.upload_queue:
                    consecutive_failures = 0
                    await asyncio.sleep(3)
                    continue
                
                # Get next item
                item = self.upload_queue.pop(0)
                filepath = Path(item['filepath'])
                
                # Skip if already processing or failed recently
                if (str(filepath) in self.processing_files or 
                    str(filepath) in self.failed_files):
                    continue
                
                logger.get_logger('telegram').info(f"Processing upload: {filepath.name}")
                
                # Check file exists
                if not filepath.exists():
                    logger.get_logger('telegram').warning(f"File not found: {filepath}")
                    self.failed_files.add(str(filepath))
                    continue
                
                # Mark as processing
                self.processing_files.add(str(filepath))
                
                success = False
                try:
                    # Select best upload engine
                    engine = self._select_upload_engine(filepath.stat().st_size)
                    
                    # Upload with retry logic
                    result = await self._upload_file_with_engine(item, engine)
                    
                    if result:
                        # Update database
                        self._update_database(item, result)
                        
                        # Delete file from server after successful upload
                        try:
                            filepath.unlink()
                            logger.get_logger('telegram').info(f"Deleted uploaded file: {filepath.name}")
                        except Exception as e:
                            logger.get_logger('error').error(f"Failed to delete file: {e}")
                        
                        logger.get_logger('telegram').info(f"✅ Upload completed: {filepath.name}")
                        success = True
                        consecutive_failures = 0
                    else:
                        logger.get_logger('telegram').error(f"❌ Upload failed: {filepath.name}")
                        self.failed_files.add(str(filepath))
                        consecutive_failures += 1
                
                except Exception as e:
                    logger.get_logger('error').error(f"Upload processing error: {e}")
                    self.failed_files.add(str(filepath))
                    consecutive_failures += 1
                
                finally:
                    # Remove from processing set
                    self.processing_files.discard(str(filepath))
                
                # Check for too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    logger.get_logger('error').error("Too many consecutive failures, pausing worker")
                    await asyncio.sleep(60)  # Wait 1 minute
                    consecutive_failures = 0
                
                # Rate limiting based on success/failure
                if success:
                    await asyncio.sleep(2)  # Normal rate
                else:
                    await asyncio.sleep(10)  # Slower rate after failure
                
            except Exception as e:
                logger.get_logger('error').error(f"Upload queue processing error: {e}")
                consecutive_failures += 1
                await asyncio.sleep(5)
    
    def _select_upload_engine(self, file_size: int) -> Dict:
        """Select best upload engine based on file size"""
        for engine in self.upload_engines:
            if file_size <= engine['max_size']:
                return engine
        
        # Default to largest engine
        return self.upload_engines[0]
    
    async def _upload_file_with_engine(self, item: Dict, engine: Dict) -> Optional[Dict]:
        """Upload file using specific engine with comprehensive error handling"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                filepath = Path(item['filepath'])
                
                # Verify file still exists
                if not filepath.exists():
                    logger.get_logger('error').error(f"File disappeared during upload: {filepath}")
                    return None
                
                file_size = filepath.stat().st_size
                filename = filepath.name
                file_type = config.detect_file_type(filename)
                
                # Create safe caption
                caption = self._create_safe_caption(item, file_size, file_type)
                
                logger.get_logger('telegram').info(
                    f"Upload attempt {attempt + 1}/{max_retries} using {engine['name']}: {filename}"
                )
                
                # Execute upload with timeout
                result = await asyncio.wait_for(
                    self._execute_upload(filepath, caption, file_type, file_size, engine),
                    timeout=engine['timeout']
                )
                
                if result:
                    return result
                
            except asyncio.TimeoutError:
                logger.get_logger('telegram').warning(f"Upload timeout (attempt {attempt + 1})")
                await asyncio.sleep(10 * (attempt + 1))
                
            except RetryAfter as e:
                logger.get_logger('telegram').warning(f"Rate limited, waiting {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                
            except BadRequest as e:
                logger.get_logger('error').error(f"Bad request error: {e}")
                # Try with simpler caption
                if "can't parse entities" in str(e).lower():
                    try:
                        simple_caption = f"📁 {filename}\n📊 {self._format_size(file_size)}"
                        result = await asyncio.wait_for(
                            self._execute_upload(filepath, simple_caption, file_type, file_size, engine),
                            timeout=engine['timeout']
                        )
                        if result:
                            return result
                    except Exception:
                        pass
                break  # Don't retry bad requests
                
            except NetworkError as e:
                logger.get_logger('error').error(f"Network error: {e}")
                await asyncio.sleep(15 * (attempt + 1))
                
            except Exception as e:
                error_str = str(e)
                logger.get_logger('error').error(f"Upload execution failed: {error_str}")
                
                if any(x in error_str.lower() for x in ['pool', 'connection', 'timeout']):
                    await asyncio.sleep(20 * (attempt + 1))
                else:
                    break  # Don't retry other errors
        
        return None
    
    def _create_safe_caption(self, item: Dict, file_size: int, file_type: str) -> str:
        """Create safe caption that won't cause parsing errors"""
        try:
            filename = Path(item['filepath']).name
            
            # File type emoji mapping
            emoji_map = {
                'video': '🎬', 'audio': '🎵', 'image': '🖼️', 'document': '📄'
            }
            
            emoji = emoji_map.get(file_type, '📁')
            
            # Create basic caption
            lines = [f"{emoji} {self._escape_markdown(filename)}"]
            
            # Add description if present
            description = item.get('description', '').strip()
            if description:
                lines.append(f"📝 {self._escape_markdown(description)}")
            
            # Add tags if present  
            tags = item.get('tags', '').strip()
            if tags:
                lines.append(f"🏷️ {self._escape_markdown(tags)}")
            
            # Add file info
            lines.append(f"📊 Size: {self._format_size(file_size)}")
            lines.append(f"📂 Type: {file_type.title()}")
            lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n\n".join(lines)
            
        except Exception as e:
            logger.get_logger('error').error(f"Caption creation failed: {e}")
            # Return ultra-simple caption as fallback
            return f"📁 {Path(item['filepath']).name}\n📊 {self._format_size(file_size)}"
    
    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters"""
        if not text:
            return ""
        
        # Replace markdown special characters
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    async def _execute_upload(self, filepath: Path, caption: str, file_type: str, 
                            file_size: int, engine: Dict) -> Optional[Dict]:
        """Execute the actual upload with proper error handling"""
        try:
            # Open file with context manager
            with open(filepath, 'rb') as file:
                # Determine upload method
                if file_type == 'video' and file_size < 50 * 1024 * 1024:
                    logger.get_logger('telegram').info("📹 Uploading as video")
                    message = await self.bot.send_video(
                        chat_id=config.TELEGRAM.channel_id,
                        video=file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        supports_streaming=True,
                        read_timeout=engine['timeout'],
                        write_timeout=engine['timeout']
                    )
                elif file_type == 'audio':
                    logger.get_logger('telegram').info("🎵 Uploading as audio")
                    message = await self.bot.send_audio(
                        chat_id=config.TELEGRAM.channel_id,
                        audio=file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        read_timeout=engine['timeout'],
                        write_timeout=engine['timeout']
                    )
                elif file_type == 'image' and file_size < 10 * 1024 * 1024:
                    logger.get_logger('telegram').info("🖼️ Uploading as photo")
                    message = await self.bot.send_photo(
                        chat_id=config.TELEGRAM.channel_id,
                        photo=file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        read_timeout=engine['timeout'],
                        write_timeout=engine['timeout']
                    )
                else:
                    logger.get_logger('telegram').info("📄 Uploading as document")
                    message = await self.bot.send_document(
                        chat_id=config.TELEGRAM.channel_id,
                        document=file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        read_timeout=engine['timeout'],
                        write_timeout=engine['timeout']
                    )
            
            # Extract file information
            file_id = None
            file_unique_id = None
            
            if message.document:
                file_id = message.document.file_id
                file_unique_id = message.document.file_unique_id
            elif message.video:
                file_id = message.video.file_id
                file_unique_id = message.video.file_unique_id
            elif message.audio:
                file_id = message.audio.file_id
                file_unique_id = message.audio.file_unique_id
            elif message.photo:
                file_id = message.photo[-1].file_id
                file_unique_id = message.photo[-1].file_unique_id
            
            # Create share link
            bot_info = await self.bot.get_me()
            share_link = f"https://t.me/{bot_info.username}?start=file_{message.message_id}"
            
            return {
                'file_id': file_id,
                'file_unique_id': file_unique_id,
                'message_id': message.message_id,
                'share_link': share_link
            }
            
        except BadRequest as e:
            # Try again with plain text caption
            if "can't parse entities" in str(e).lower():
                try:
                    plain_caption = html.escape(caption)
                    
                    with open(filepath, 'rb') as file:
                        message = await self.bot.send_document(
                            chat_id=config.TELEGRAM.channel_id,
                            document=file,
                            caption=plain_caption,
                            read_timeout=engine['timeout'],
                            write_timeout=engine['timeout']
                        )
                    
                    file_id = message.document.file_id if message.document else None
                    file_unique_id = message.document.file_unique_id if message.document else None
                    
                    bot_info = await self.bot.get_me()
                    share_link = f"https://t.me/{bot_info.username}?start=file_{message.message_id}"
                    
                    return {
                        'file_id': file_id,
                        'file_unique_id': file_unique_id,
                        'message_id': message.message_id,
                        'share_link': share_link
                    }
                    
                except Exception:
                    pass
            
            raise e
            
        except Exception as e:
            logger.get_logger('error').error(f"Upload execution failed: {e}")
            return None
    
    def _update_database(self, item: Dict, result: Dict):
        """Update database with Telegram information"""
        try:
            update_data = {
                'telegram_file_id': result['file_id'],
                'telegram_file_unique_id': result['file_unique_id'],
                'telegram_message_id': result['message_id'],
                'share_link': result['share_link']
            }
            
            if item['type'] == 'download':
                download_data = db.get_download(item['id'])
                if download_data:
                    download_data.update(update_data)
                    db.save_download(download_data)
                    logger.get_logger('database').info(f"Updated download with Telegram info: {item['id']}")
            else:  # upload
                upload_data = db.get_upload(item['id'])
                if upload_data:
                    upload_data.update(update_data)
                    db.save_upload(upload_data)
                    logger.get_logger('database').info(f"Updated upload with Telegram info: {item['id']}")
                    
        except Exception as e:
            logger.get_logger('error').error(f"Database update error: {e}")
    
    def _format_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def queue_upload(self, filepath: str, item_id: str, item_type: str, 
                    description: str = "", tags: str = "", priority: int = 0):
        """Add file to upload queue with duplicate and existence checks"""
        if not self.bot:
            logger.get_logger('telegram').warning("Telegram bot not available, skipping upload")
            return
        
        # Verify file exists before queueing
        if not Path(filepath).exists():
            logger.get_logger('telegram').warning(f"File does not exist, skipping: {filepath}")
            return
        
        # Prevent duplicate uploads
        if filepath in self.processing_files:
            logger.get_logger('telegram').debug(f"File already being processed: {Path(filepath).name}")
            return
        
        if filepath in self.failed_files:
            logger.get_logger('telegram').debug(f"File previously failed, skipping: {Path(filepath).name}")
            return
        
        # Check if already in queue
        for existing_item in self.upload_queue:
            if existing_item['filepath'] == filepath:
                logger.get_logger('telegram').debug(f"File already in queue: {Path(filepath).name}")
                return
        
        upload_item = {
            'filepath': filepath,
            'id': item_id,
            'type': item_type,
            'description': description,
            'tags': tags,
            'priority': priority,
            'created_at': datetime.now().isoformat()
        }
        
        # Insert based on priority (higher priority first)
        inserted = False
        for i, existing_item in enumerate(self.upload_queue):
            if priority > existing_item.get('priority', 0):
                self.upload_queue.insert(i, upload_item)
                inserted = True
                break
        
        if not inserted:
            self.upload_queue.append(upload_item)
        
        logger.get_logger('telegram').info(
            f"Queued for Telegram: {Path(filepath).name} (Priority: {priority}, Queue: {len(self.upload_queue)})"
        )
        
        # Start worker if not running
        if not self.worker_running:
            self.start_worker()
    
    def get_queue_status(self) -> Dict:
        """Get comprehensive upload queue status"""
        return {
            'queue_length': len(self.upload_queue),
            'processing_count': len(self.processing_files),
            'failed_count': len(self.failed_files),
            'worker_running': self.worker_running,
            'bot_available': self.bot is not None,
            'engines': len(self.upload_engines),
            'next_files': [Path(item['filepath']).name for item in self.upload_queue[:5]]
        }
    
    def clear_queue(self):
        """Clear upload queue and failed files"""
        cleared_count = len(self.upload_queue)
        self.upload_queue.clear()
        self.failed_files.clear()
        logger.get_logger('telegram').info(f"Cleared {cleared_count} items from upload queue and failed files")
        return cleared_count
    
    def retry_failed(self):
        """Retry failed uploads"""
        retry_count = len(self.failed_files)
        self.failed_files.clear()
        logger.get_logger('telegram').info(f"Cleared {retry_count} failed files for retry")
        return retry_count
    
    def stop(self):
        """Stop the upload worker gracefully"""
        logger.get_logger('telegram').info("Stopping Professional Telegram worker...")
        self.worker_running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=30)
        
        logger.get_logger('telegram').info("Professional Telegram worker stopped")

# Global Telegram bot instance
telegram_bot = UltimateTelegramBot()
