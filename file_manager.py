import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import subprocess

from config import config
from database import db
from logger import logger

class ProfessionalFileManager:
    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        self.downloads_dir = config.DOWNLOADS_DIR
        self.uploads_dir = config.UPLOADS_DIR
        
        # File locks to prevent premature deletion
        self.file_locks = set()
        self.lock_timeout = 300  # 5 minutes
        
        logger.get_logger('main').info("Professional File Manager initialized")
    
    def lock_file(self, filepath: str):
        """Lock file to prevent deletion during processing"""
        self.file_locks.add(filepath)
        logger.get_logger('main').debug(f"Locked file: {Path(filepath).name}")
    
    def unlock_file(self, filepath: str):
        """Unlock file"""
        self.file_locks.discard(filepath)
        logger.get_logger('main').debug(f"Unlocked file: {Path(filepath).name}")
    
    def is_file_locked(self, filepath: str) -> bool:
        """Check if file is locked"""
        return filepath in self.file_locks
    
    def safe_delete_file(self, filepath: str, force: bool = False) -> bool:
        """Safely delete file, respecting locks"""
        try:
            if not force and self.is_file_locked(filepath):
                logger.get_logger('main').warning(f"File is locked, cannot delete: {Path(filepath).name}")
                return False
            
            file_path = Path(filepath)
            if file_path.exists():
                file_path.unlink()
                self.unlock_file(filepath)  # Clean up lock
                logger.get_logger('main').info(f"Safely deleted file: {file_path.name}")
                return True
                
        except Exception as e:
            logger.get_logger('error').error(f"Failed to delete file {filepath}: {e}")
            
        return False
    
    def analyze_file(self, filepath: str) -> Dict:
        """Comprehensive file analysis with error handling"""
        try:
            file_path = Path(filepath)
            
            if not file_path.exists():
                return {'error': 'File not found'}
            
            # Lock file during analysis
            self.lock_file(str(file_path))
            
            try:
                # Basic file info
                stat = file_path.stat()
                
                analysis = {
                    'filepath': str(file_path),
                    'filename': file_path.name,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'extension': file_path.suffix.lower(),
                    'mime_type': mimetypes.guess_type(str(file_path))[0],
                    'file_type': config.detect_file_type(file_path.name),
                    'hash': self.calculate_file_hash(filepath)
                }
                
                # Type-specific analysis
                if analysis['file_type'] == 'image' and PIL_AVAILABLE:
                    analysis.update(self._analyze_image(file_path))
                elif analysis['file_type'] == 'video':
                    analysis.update(self._analyze_video(file_path))
                elif analysis['file_type'] == 'audio':
                    analysis.update(self._analyze_audio(file_path))
                
                return analysis
                
            finally:
                # Always unlock after analysis
                self.unlock_file(str(file_path))
                
        except Exception as e:
            logger.get_logger('error').error(f"File analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_image(self, file_path: Path) -> Dict:
        """Analyze image file safely"""
        try:
            with Image.open(file_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
        except Exception as e:
            logger.get_logger('error').error(f"Image analysis failed: {e}")
            return {'analysis_error': str(e)}
    
    def _analyze_video(self, file_path: Path) -> Dict:
        """Analyze video file using ffprobe with timeout"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                format_info = data.get('format', {})
                video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
                audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'video_codec': video_stream.get('codec_name'),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') else 0,
                    'audio_codec': audio_stream.get('codec_name'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0))
                }
            else:
                return {'analysis_error': 'ffprobe failed'}
                
        except subprocess.TimeoutExpired:
            return {'analysis_error': 'Analysis timeout'}
        except Exception as e:
            logger.get_logger('error').error(f"Video analysis failed: {e}")
            return {'analysis_error': str(e)}
    
    def _analyze_audio(self, file_path: Path) -> Dict:
        """Analyze audio file with timeout"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                format_info = data.get('format', {})
                audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'codec': audio_stream.get('codec_name'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0))
                }
            else:
                return {'analysis_error': 'ffprobe failed'}
                
        except subprocess.TimeoutExpired:
            return {'analysis_error': 'Analysis timeout'}
        except Exception as e:
            logger.get_logger('error').error(f"Audio analysis failed: {e}")
            return {'analysis_error': str(e)}
    
    def calculate_file_hash(self, filepath: str, algorithm: str = 'md5') -> str:
        """Calculate file hash with progress for large files"""
        try:
            hash_obj = hashlib.new(algorithm)
            file_size = Path(filepath).stat().st_size
            
            with open(filepath, 'rb') as f:
                # Use larger chunks for big files
                chunk_size = min(65536, max(8192, file_size // 1000))
                
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.get_logger('error').error(f"Hash calculation failed: {e}")
            return ""
    
    def generate_thumbnail(self, filepath: str, size: Tuple[int, int] = (320, 240)) -> Optional[str]:
        """Generate thumbnail for supported file types"""
        try:
            file_path = Path(filepath)
            file_type = config.detect_file_type(file_path.name)
            
            # Generate thumbnail path
            thumb_filename = f"{file_path.stem}_thumb.jpg"
            thumb_path = self.temp_dir / thumb_filename
            
            # Lock source file
            self.lock_file(str(file_path))
            
            try:
                if file_type == 'image' and PIL_AVAILABLE:
                    return self._generate_image_thumbnail(file_path, thumb_path, size)
                elif file_type == 'video':
                    return self._generate_video_thumbnail(file_path, thumb_path, size)
                
                return None
                
            finally:
                self.unlock_file(str(file_path))
            
        except Exception as e:
            logger.get_logger('error').error(f"Thumbnail generation failed: {e}")
            return None
    
    def _generate_image_thumbnail(self, source_path: Path, thumb_path: Path, size: Tuple[int, int]) -> str:
        """Generate image thumbnail with PIL"""
        with Image.open(source_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Generate thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85, optimize=True)
            
            return str(thumb_path)
    
    def _generate_video_thumbnail(self, source_path: Path, thumb_path: Path, size: Tuple[int, int]) -> str:
        """Generate video thumbnail using ffmpeg with timeout"""
        cmd = [
            'ffmpeg',
            '-i', str(source_path),
            '-vf', f'thumbnail,scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease',
            '-frames:v', '1',
            '-y',
            str(thumb_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if result.returncode == 0 and thumb_path.exists():
            return str(thumb_path)
        else:
            raise Exception(f"ffmpeg thumbnail generation failed: {result.stderr.decode()}")
    
    def cleanup_temp_files(self, older_than_hours: int = 1):
        """Clean up temporary files with lock awareness"""
        try:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
            cleaned_count = 0
            
            for file_path in self.temp_dir.iterdir():
                if (file_path.is_file() and 
                    file_path.stat().st_mtime < cutoff_time and
                    not self.is_file_locked(str(file_path))):
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except:
                        pass
            
            logger.get_logger('main').info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count
            
        except Exception as e:
            logger.get_logger('error').error(f"Temp cleanup failed: {e}")
            return 0
    
    def cleanup_expired_locks(self):
        """Clean up expired file locks"""
        try:
            current_time = time.time()
            expired_locks = []
            
            for filepath in self.file_locks:
                try:
                    file_stat = Path(filepath).stat()
                    if current_time - file_stat.st_mtime > self.lock_timeout:
                        expired_locks.append(filepath)
                except:
                    expired_locks.append(filepath)  # Remove locks for non-existent files
            
            for filepath in expired_locks:
                self.file_locks.discard(filepath)
            
            if expired_locks:
                logger.get_logger('main').info(f"Cleaned up {len(expired_locks)} expired file locks")
                
        except Exception as e:
            logger.get_logger('error').error(f"Lock cleanup failed: {e}")
    
    def get_directory_size(self, directory: Path) -> int:
        """Get total size of directory with error handling"""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except:
                        pass  # Skip files we can't access
            return total_size
        except:
            return 0
    
    def get_storage_info(self) -> Dict:
        """Get comprehensive storage information"""
        return {
            'downloads': {
                'path': str(self.downloads_dir),
                'size': self.get_directory_size(self.downloads_dir),
                'count': len([f for f in self.downloads_dir.iterdir() if f.is_file()])
            },
            'uploads': {
                'path': str(self.uploads_dir),
                'size': self.get_directory_size(self.uploads_dir),
                'count': len([f for f in self.uploads_dir.iterdir() if f.is_file()])
            },
            'temp': {
                'path': str(self.temp_dir),
                'size': self.get_directory_size(self.temp_dir),
                'count': len([f for f in self.temp_dir.iterdir() if f.is_file()])
            },
            'locked_files': len(self.file_locks)
        }

# Global file manager instance
file_manager = ProfessionalFileManager()
