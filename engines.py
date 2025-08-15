import subprocess
import requests
import urllib3
import os
import time
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Callable, List  # اضافه کردن List
from urllib.parse import urlparse
from config import config
from logger import logger

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DownloadEngine(ABC):
    """Abstract base class for download engines"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = config.ENGINES.get(name, config.ENGINES['requests'])
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is available"""
        pass
    
    @abstractmethod
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download file and return result"""
        pass
    
    def can_handle_url(self, url: str) -> bool:
        """Check if engine can handle this URL"""
        return True  # Base implementation accepts all URLs

class YtDlpEngine(DownloadEngine):
    def __init__(self):
        super().__init__('yt-dlp')
    
    def is_available(self) -> bool:
        """Check if yt-dlp is available"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def can_handle_url(self, url: str) -> bool:
        """yt-dlp can handle social media and video platforms"""
        platform = config.detect_platform(url)
        return platform is not None
    
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download using yt-dlp"""
        try:
            # Determine output template
            output_dir = Path(filepath).parent
            filename_template = Path(filepath).stem + '_%(title)s.%(ext)s'
            output_template = str(output_dir / filename_template)
            
            # Detect platform for format selection
            platform = config.detect_platform(url)
            platform_config = config.PLATFORMS.get(platform, {})
            format_selector = platform_config.get('format', 'best[filesize<4G]/best')
            
            # Build command
            cmd = [
                'yt-dlp',
                '--no-playlist',
                '--output', output_template,
                '--format', format_selector,
                '--no-warnings',
                '--newline',
                '--no-check-certificate',
                '--ignore-errors',
                '--extract-flat', 'false',
                '--write-info-json',
                '--write-thumbnail',
                url
            ]
            
            # Add audio extraction if configured
            if platform_config.get('extract_audio', False):
                cmd.extend([
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0'
                ])
            
            logger.get_logger('downloader').info(f"yt-dlp command: {' '.join(cmd[:5])}...")
            
            # Execute command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            
            # Monitor progress
            last_progress = 0
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line and '[download]' in line and progress_callback:
                    try:
                        if '%' in line:
                            parts = line.split()
                            for part in parts:
                                if '%' in part:
                                    progress = float(part.replace('%', ''))
                                    if progress > last_progress:
                                        progress_callback(progress, 0)  # Speed not available from yt-dlp
                                        last_progress = progress
                                    break
                    except:
                        pass
            
            return_code = process.wait()
            
            if return_code == 0:
                # Find downloaded files
                downloaded_files = list(output_dir.glob(f"{Path(filepath).stem}_*"))
                
                if downloaded_files:
                    # Get the main file (largest one)
                    main_file = max(downloaded_files, key=lambda f: f.stat().st_size if f.is_file() else 0)
                    
                    # Move to target filepath
                    if main_file != Path(filepath):
                        shutil.move(str(main_file), filepath)
                    
                    file_size = Path(filepath).stat().st_size
                    
                    return {
                        'success': True,
                        'filepath': filepath,
                        'size': file_size,
                        'engine': self.name
                    }
                else:
                    raise Exception("No files downloaded")
            else:
                stderr_output = process.stderr.read()
                raise Exception(f"yt-dlp failed (code {return_code}): {stderr_output}")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'engine': self.name
            }

class Aria2Engine(DownloadEngine):
    def __init__(self):
        super().__init__('aria2')
    
    def is_available(self) -> bool:
        """Check if aria2c is available"""
        try:
            result = subprocess.run(['aria2c', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download using aria2c"""
        try:
            output_dir = Path(filepath).parent
            filename = Path(filepath).name
            
            cmd = [
                'aria2c',
                '--dir', str(output_dir),
                '--out', filename,
                '--max-connection-per-server', '16',
                '--min-split-size', '1M',
                '--split', '16',
                '--continue', 'true',
                '--max-tries', str(self.config.max_retries),
                '--retry-wait', '3',
                '--timeout', str(self.config.timeout),
                '--check-certificate=false',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--summary-interval', '1',
                url
            ]
            
            logger.get_logger('downloader').info(f"aria2c command: {' '.join(cmd[:5])}...")
            
            # Execute command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            # Monitor progress
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line and progress_callback:
                    try:
                        # Parse aria2c progress output
                        if '(' in line and '%' in line and ')' in line:
                            # Extract percentage
                            start = line.find('(') + 1
                            end = line.find('%', start)
                            if start > 0 and end > start:
                                progress = float(line[start:end])
                                
                                # Extract speed if available
                                speed = 0
                                if 'DL:' in line:
                                    dl_start = line.find('DL:') + 3
                                    dl_end = line.find(' ', dl_start)
                                    if dl_end > dl_start:
                                        speed_str = line[dl_start:dl_end]
                                        # Convert to bytes per second
                                        if 'KiB/s' in speed_str:
                                            speed = float(speed_str.replace('KiB/s', '')) * 1024
                                        elif 'MiB/s' in speed_str:
                                            speed = float(speed_str.replace('MiB/s', '')) * 1024 * 1024
                                
                                progress_callback(progress, speed)
                    except:
                        pass
            
            return_code = process.wait()
            
            if return_code == 0 and Path(filepath).exists():
                file_size = Path(filepath).stat().st_size
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'size': file_size,
                    'engine': self.name
                }
            else:
                stderr_output = process.stderr.read()
                raise Exception(f"aria2c failed (code {return_code}): {stderr_output}")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'engine': self.name
            }

class RequestsEngine(DownloadEngine):
    def __init__(self):
        super().__init__('requests')
        self.session = self._create_session()
    
    def _create_session(self):
        """Create robust requests session"""
        session = requests.Session()
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def is_available(self) -> bool:
        """Requests is always available"""
        return True
    
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download using requests"""
        try:
            # Check for existing file to resume
            resume_pos = 0
            if Path(filepath).exists():
                resume_pos = Path(filepath).stat().st_size
            
            headers = {}
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
            
            logger.get_logger('downloader').info(f"Requests download starting, resume from: {resume_pos}")
            
            # Start download
            with self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=self.config.timeout,
                verify=False
            ) as response:
                
                response.raise_for_status()
                
                # Get file size
                total_size = int(response.headers.get('content-length', 0))
                if resume_pos > 0:
                    total_size += resume_pos
                
                # Open file for writing
                mode = 'ab' if resume_pos > 0 else 'wb'
                with open(filepath, mode) as f:
                    downloaded = resume_pos
                    start_time = time.time()
                    last_update = start_time
                    
                    for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            current_time = time.time()
                            if current_time - last_update >= 1.0 and progress_callback:  # Update every second
                                elapsed = current_time - start_time
                                if elapsed > 0:
                                    speed = (downloaded - resume_pos) / elapsed
                                    progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                    progress_callback(progress, speed)
                                
                                last_update = current_time
            
            if Path(filepath).exists():
                file_size = Path(filepath).stat().st_size
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'size': file_size,
                    'engine': self.name
                }
            else:
                raise Exception("File not created")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'engine': self.name
            }

class WgetEngine(DownloadEngine):
    def __init__(self):
        super().__init__('wget')
    
    def is_available(self) -> bool:
        """Check if wget is available"""
        try:
            result = subprocess.run(['wget', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download using wget"""
        try:
            output_dir = Path(filepath).parent
            filename = Path(filepath).name
            
            cmd = [
                'wget',
                '--continue',
                '--tries', str(self.config.max_retries),
                '--timeout', str(self.config.timeout),
                '--no-check-certificate',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--directory-prefix', str(output_dir),
                '--output-document', filename,
                '--progress=bar:force',
                url
            ]
            
            logger.get_logger('downloader').info(f"wget command: {' '.join(cmd[:5])}...")
            
            # Execute command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # wget outputs progress to stderr
                text=True
            )
            
            # Monitor progress
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line and progress_callback:
                    try:
                        # Parse wget progress output
                        if '%' in line and ('K/s' in line or 'M/s' in line):
                            # Extract percentage
                            percent_start = line.rfind(' ') + 1
                            percent_end = line.find('%', percent_start)
                            if percent_end > percent_start:
                                progress = float(line[percent_start:percent_end])
                                
                                # Extract speed
                                speed = 0
                                if 'K/s' in line:
                                    speed_start = line.rfind(' ', 0, line.find('K/s')) + 1
                                    speed_end = line.find('K/s', speed_start)
                                    speed = float(line[speed_start:speed_end]) * 1024
                                elif 'M/s' in line:
                                    speed_start = line.rfind(' ', 0, line.find('M/s')) + 1
                                    speed_end = line.find('M/s', speed_start)
                                    speed = float(line[speed_start:speed_end]) * 1024 * 1024
                                
                                progress_callback(progress, speed)
                    except:
                        pass
            
            return_code = process.wait()
            
            if return_code == 0 and Path(filepath).exists():
                file_size = Path(filepath).stat().st_size
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'size': file_size,
                    'engine': self.name
                }
            else:
                raise Exception(f"wget failed with return code {return_code}")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'engine': self.name
            }

class CurlEngine(DownloadEngine):
    def __init__(self):
        super().__init__('curl')
    
    def is_available(self) -> bool:
        """Check if curl is available"""
        try:
            result = subprocess.run(['curl', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def download(self, url: str, filepath: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download using curl"""
        try:
            cmd = [
                'curl',
                '--location',
                '--continue-at', '-',  # Resume if possible
                '--max-time', str(self.config.timeout),
                '--retry', str(self.config.max_retries),
                '--retry-delay', '3',
                '--insecure',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--output', filepath,
                '--progress-bar',
                url
            ]
            
            logger.get_logger('downloader').info(f"curl command: {' '.join(cmd[:5])}...")
            
            # Execute command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            return_code = process.wait()
            
            if return_code == 0 and Path(filepath).exists():
                file_size = Path(filepath).stat().st_size
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'size': file_size,
                    'engine': self.name
                }
            else:
                stderr_output = process.stderr.read()
                raise Exception(f"curl failed (code {return_code}): {stderr_output}")
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'engine': self.name
            }

class EngineManager:
    """Manager for all download engines"""
    
    def __init__(self):
        self.engines = {
            'yt-dlp': YtDlpEngine(),
            'aria2': Aria2Engine(),
            'requests': RequestsEngine(),
            'wget': WgetEngine(),
            'curl': CurlEngine()
        }
        
        self.available_engines = self._check_available_engines()
        logger.get_logger('downloader').info(f"Available engines: {list(self.available_engines.keys())}")
    
    def _check_available_engines(self) -> Dict[str, DownloadEngine]:
        """Check which engines are available"""
        available = {}
        
        for name, engine in self.engines.items():
            if config.ENGINES[name].enabled and engine.is_available():
                available[name] = engine
        
        return available
    
    def get_best_engine(self, url: str) -> Optional[DownloadEngine]:
        """Get the best engine for a URL based on priority and capability"""
        # Get engines sorted by priority
        engine_priority = config.get_engine_by_priority()
        
        for engine_name in engine_priority:
            if engine_name in self.available_engines:
                engine = self.available_engines[engine_name]
                if engine.can_handle_url(url):
                    return engine
        
        return None
    
    def get_all_compatible_engines(self, url: str) -> List[DownloadEngine]:
        """Get all engines that can handle a URL, sorted by priority"""
        compatible = []
        engine_priority = config.get_engine_by_priority()
        
        for engine_name in engine_priority:
            if engine_name in self.available_engines:
                engine = self.available_engines[engine_name]
                if engine.can_handle_url(url):
                    compatible.append(engine)
        
        return compatible

# Global engine manager
engine_manager = EngineManager()
