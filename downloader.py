import hashlib
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict
from config import config
from database import db
from engines import engine_manager
from logger import logger

class ProfessionalDownloader:
    def __init__(self):
        self.downloads = {}
        self.lock = threading.RLock()
        self.active_threads = {}
        logger.get_logger('main').info("Professional Downloader initialized")
    
    def generate_download_id(self, url: str) -> str:
        """Generate unique download ID"""
        return hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:16]
    
    def extract_filename(self, url: str, headers: Dict = None) -> str:
        """Extract filename from URL or headers"""
        if headers:
            cd = headers.get('content-disposition', '')
            if 'filename=' in cd:
                try:
                    filename = cd.split('filename=')[1].strip('"\'')
                    if filename and '.' in filename:
                        return filename
                except:
                    pass
        
        # Extract from URL
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            if '?' in filename:
                filename = filename.split('?')[0]
            if filename and '.' in filename:
                return unquote(filename)
        except:
            pass
        
        # Generate default filename
        timestamp = int(time.time())
        return f"download_{timestamp}.bin"
    
    def get_unique_filepath(self, filename: str) -> str:
        """Get unique file path to avoid conflicts"""
        filepath = config.DOWNLOADS_DIR / filename
        if not filepath.exists():
            return str(filepath)
        
        stem = filepath.stem
        suffix = filepath.suffix
        counter = 1
        
        while filepath.exists():
            new_filename = f"{stem}_{counter}{suffix}"
            filepath = config.DOWNLOADS_DIR / new_filename
            counter += 1
        
        return str(filepath)
    
    def start_download(self, url: str, description: str = "", tags: str = "", 
                      quality: str = "best", extract_audio: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Start a new download"""
        try:
            # Check concurrent downloads limit
            with self.lock:
                active_count = sum(1 for d in self.downloads.values() if d.get('status') == 'downloading')
            
            if active_count >= config.SERVER.max_workers:
                return None, f"Maximum concurrent downloads reached ({config.SERVER.max_workers})"
            
            # Generate download ID
            download_id = self.generate_download_id(url)
            
            # Detect platform and file type
            platform = config.detect_platform(url) or 'direct'
            
            # Initialize download data
            download_data = {
                'id': download_id,
                'url': url,
                'original_url': url,
                'filename': 'Initializing...',
                'filepath': '',
                'file_type': 'unknown',
                'status': 'initializing',
                'progress': 0,
                'speed': 0,
                'eta': 0,
                'description': description,
                'tags': tags,
                'platform': platform,
                'engine': 'unknown',
                'quality': quality,
                'extract_audio': extract_audio,
                'created_at': datetime.now().isoformat(),
                'retry_count': 0,
                'max_retries': 3
            }
            
            with self.lock:
                self.downloads[download_id] = download_data
            
            # Save to database
            db.save_download(download_data)
            
            # Start download thread
            thread = threading.Thread(
                target=self._download_worker,
                args=(download_id,),
                daemon=True,
                name=f"download-{download_id}"
            )
            
            thread.start()
            self.active_threads[download_id] = thread
            
            logger.log_download_start(url, 'multi-engine', download_id)
            return download_id, None
            
        except Exception as e:
            logger.get_logger('error').error(f"Failed to start download: {e}")
            return None, str(e)
    
    def _download_worker(self, download_id: str):
        """Download worker thread"""
        download_data = self.downloads.get(download_id)
        if not download_data:
            return
        
        start_time = time.time()
        
        try:
            url = download_data['url']
            
            # Get available engines for this URL
            engines = engine_manager.get_all_compatible_engines(url)
            
            if not engines:
                raise Exception("No compatible download engines available")
            
            # Try each engine until success
            last_error = None
            
            for engine in engines:
                if download_data['status'] == 'cancelled':
                    break
                
                try:
                    # Update status
                    download_data['status'] = 'downloading'
                    download_data['engine'] = engine.name
                    download_data['started_at'] = datetime.now().isoformat()
                    
                    with self.lock:
                        self.downloads[download_id] = download_data
                    
                    db.save_download(download_data)
                    
                    logger.get_logger('downloader').info(f"Trying engine {engine.name} for {download_id}")
                    
                    # Prepare filepath
                    if not download_data.get('filepath'):
                        filename = self.extract_filename(url)
                        filepath = self.get_unique_filepath(filename)
                        download_data['filename'] = Path(filepath).name
                        download_data['filepath'] = filepath
                        download_data['file_type'] = config.detect_file_type(filename)
                    
                    # Progress callback
                    def progress_callback(progress: float, speed: float):  
                        if download_data['status'] == 'downloading':
                            download_data['progress'] = min(progress, 100)
                            download_data['speed'] = speed
                            
                            # Calculate ETA
                            if speed > 0 and 'size' in download_data:
                                remaining = download_data.get('size', 0) - (download_data.get('size', 0) * progress / 100)
                                download_data['eta'] = remaining / speed if remaining > 0 else 0
                            
                            # Log progress periodically
                            if int(progress) % 10 == 0:  # Every 10%
                                logger.log_download_progress(download_id, progress, speed)
                    
                    # Attempt download with current engine
                    engine_start_time = time.time()
                    result = engine.download(
                        url, 
                        download_data['filepath'], 
                        progress_callback
                    )
                    engine_duration = time.time() - engine_start_time
                    
                    if result['success']:
                        # Download successful
                        download_data.update({
                            'status': 'completed',
                            'progress': 100,
                            'size': result.get('size', 0),
                            'downloaded': result.get('size', 0),
                            'finished_at': datetime.now().isoformat()
                        })
                        
                        # Save engine performance stats
                        db.save_engine_stats(
                            engine.name, 
                            url, 
                            True, 
                            engine_duration, 
                            result.get('size', 0)
                        )
                        
                        logger.log_download_complete(
                            download_id, 
                            download_data['filename'], 
                            result.get('size', 0)
                        )
                        
                        break  # Success, no need to try other engines
                    
                    else:
                        # Engine failed, try next one
                        last_error = result.get('error', 'Unknown error')
                        
                        # Save failed attempt stats
                        db.save_engine_stats(
                            engine.name, 
                            url, 
                            False, 
                            engine_duration, 
                            0, 
                            last_error
                        )
                        
                        logger.log_download_error(download_id, engine.name, last_error)
                        
                        # Clean up partial file if exists
                        if Path(download_data['filepath']).exists():
                            try:
                                Path(download_data['filepath']).unlink()
                            except:
                                pass
                        
                        continue  # Try next engine
                
                except Exception as e:
                    last_error = str(e)
                    logger.log_download_error(download_id, engine.name, last_error)
                    continue
            
            # If we get here and status is still downloading, all engines failed
            if download_data['status'] == 'downloading':
                download_data['status'] = 'error'
                download_data['error_message'] = last_error or "All download engines failed"
                logger.log_download_error(download_id, 'all-engines', download_data['error_message'])
        
        except Exception as e:
            download_data['status'] = 'error'
            download_data['error_message'] = str(e)
            logger.log_download_error(download_id, 'system', str(e))
        
        finally:
            # Final save to database
            with self.lock:
                self.downloads[download_id] = download_data
                if download_id in self.active_threads:
                    del self.active_threads[download_id]
            
            db.save_download(download_data)
            
            total_duration = time.time() - start_time
            logger.get_logger('downloader').info(
                f"Download {download_id} finished in {total_duration:.2f}s with status: {download_data['status']}"
            )
    
    def pause_download(self, download_id: str):
        """Pause download"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id]['status'] = 'paused'
                db.save_download(self.downloads[download_id])
                logger.get_logger('downloader').info(f"Paused download: {download_id}")
    
    def resume_download(self, download_id: str) -> bool:
        """Resume paused download"""
        with self.lock:
            if download_id not in self.downloads:
                return False
            
            download = self.downloads[download_id]
            if download['status'] != 'paused':
                return False
            
            # Check concurrent limit
            active_count = sum(1 for d in self.downloads.values() if d.get('status') == 'downloading')
            if active_count >= config.SERVER.max_workers:
                return False
            
            # Restart download
            download['status'] = 'downloading'
            download['retry_count'] = download.get('retry_count', 0) + 1
            
            thread = threading.Thread(
                target=self._download_worker,
                args=(download_id,),
                daemon=True,
                name=f"download-resume-{download_id}"
            )
            
            thread.start()
            self.active_threads[download_id] = thread
            
            logger.get_logger('downloader').info(f"Resumed download: {download_id}")
            return True
    
    def cancel_download(self, download_id: str):
        """Cancel and remove download"""
        with self.lock:
            if download_id not in self.downloads:
                return
            
            download = self.downloads[download_id]
            download['status'] = 'cancelled'
            
            # Remove file if exists
            filepath = download.get('filepath')
            if filepath and Path(filepath).exists():
                try:
                    Path(filepath).unlink()
                    logger.get_logger('downloader').info(f"Removed file: {filepath}")
                except Exception as e:
                    logger.get_logger('error').error(f"Failed to remove file: {e}")
            
            # Remove from memory and database
            del self.downloads[download_id]
            if download_id in self.active_threads:
                del self.active_threads[download_id]
            
            db.delete_download(download_id)
            logger.get_logger('downloader').info(f"Cancelled download: {download_id}")
    
    def get_stats(self) -> Dict:
        """Get download statistics"""
        with self.lock:
            total = len(self.downloads)
            downloading = sum(1 for d in self.downloads.values() if d.get('status') == 'downloading')
            completed = sum(1 for d in self.downloads.values() if d.get('status') == 'completed')
            paused = sum(1 for d in self.downloads.values() if d.get('status') == 'paused')
            failed = sum(1 for d in self.downloads.values() if d.get('status') == 'error')
            total_speed = sum(d.get('speed', 0) for d in self.downloads.values() if d.get('status') == 'downloading')
            
            return {
                'total': total,
                'downloading': downloading,
                'completed': completed,
                'paused': paused,
                'failed': failed,
                'total_speed': total_speed,
                'active_threads': len(self.active_threads)
            }
    
    def cleanup_completed(self) -> int:
        """Clean up completed downloads"""
        with self.lock:
            completed_ids = [
                dl_id for dl_id, dl in self.downloads.items() 
                if dl.get('status') == 'completed'
            ]
            
            for download_id in completed_ids:
                del self.downloads[download_id]
                db.delete_download(download_id)
            
            logger.get_logger('downloader').info(f"Cleaned up {len(completed_ids)} completed downloads")
            return len(completed_ids)

# Global downloader instance
downloader = ProfessionalDownloader()
