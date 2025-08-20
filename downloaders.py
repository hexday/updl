#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Advanced Multi-Platform Media Downloader System
📱 Enterprise-Grade Download Engine with AI-Powered Quality Selection
"""

import asyncio
import os
import re
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import hashlib

import yt_dlp
import aiohttp
import aiofiles
from PIL import Image
import ffmpeg
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER, COMM
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import instaloader
from loguru import logger

from config import config, platforms, security
from utils import (
    performance_tracked, smart_cache, text_processor, 
    file_manager, NetworkManager, rate_limiter
)

@dataclass
class MediaMetadata:
    """Enhanced media metadata container"""
    # Basic info
    title: str = ""
    description: str = ""
    uploader: str = ""
    uploader_id: str = ""
    
    # Timing
    duration: int = 0  # seconds
    upload_date: str = ""
    timestamp: Optional[datetime] = None
    
    # Social metrics
    view_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    subscriber_count: int = 0
    
    # Media properties
    width: int = 0
    height: int = 0
    fps: int = 0
    bitrate: int = 0
    codec: str = ""
    
    # File info
    file_size: int = 0
    format: str = ""
    quality: str = ""
    thumbnail_url: str = ""
    
    # Platform specific
    platform: str = ""
    platform_id: str = ""
    platform_url: str = ""
    
    # Additional data
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    language: str = ""
    license: str = ""
    
    # Technical info
    audio_codec: str = ""
    video_codec: str = ""
    container: str = ""
    chapters: List[Dict] = field(default_factory=list)
    subtitles: List[Dict] = field(default_factory=list)

@dataclass
class DownloadResult:
    """Enhanced download result container"""
    success: bool = False
    file_path: str = ""
    thumbnail_path: str = ""
    error_message: str = ""
    error_code: str = ""
    
    metadata: MediaMetadata = field(default_factory=MediaMetadata)
    processing_time: float = 0.0
    download_speed: float = 0.0  # MB/s
    quality_score: int = 0  # 0-100
    
    # File variants
    variants: List[str] = field(default_factory=list)  # Different quality versions
    
    # Post-processing info
    was_converted: bool = False
    original_format: str = ""
    compression_ratio: float = 1.0

class QualitySelector:
    """AI-powered quality selection system"""
    
    @staticmethod
    def select_best_quality(formats: List[Dict], preferences: Dict[str, Any]) -> Optional[Dict]:
        """Select best quality based on user preferences and constraints"""
        if not formats:
            return None
        
        # Filter by file size limit
        max_size = preferences.get('max_file_size', config.max_file_size_mb * 1024 * 1024)
        filtered = [f for f in formats if f.get('filesize', 0) <= max_size]
        
        if not filtered:
            filtered = formats  # Fallback to all formats
        
        # Quality scoring algorithm
        def score_format(fmt):
            score = 0
            
            # Resolution score (0-40 points)
            height = fmt.get('height', 0)
            if height >= 2160: score += 40  # 4K
            elif height >= 1080: score += 35  # 1080p
            elif height >= 720: score += 30   # 720p
            elif height >= 480: score += 20   # 480p
            else: score += 10
            
            # Audio quality score (0-20 points)
            abr = fmt.get('abr', 0)
            if abr >= 320: score += 20
            elif abr >= 256: score += 18
            elif abr >= 192: score += 15
            elif abr >= 128: score += 12
            else: score += 8
            
            # Format preference (0-20 points)
            ext = fmt.get('ext', '').lower()
            if ext in ['mp4', 'mkv']: score += 20
            elif ext in ['webm', 'avi']: score += 15
            else: score += 10
            
            # Codec preference (0-20 points)
            vcodec = fmt.get('vcodec', '').lower()
            if 'h264' in vcodec or 'avc' in vcodec: score += 20
            elif 'h265' in vcodec or 'hevc' in vcodec: score += 18
            elif 'vp9' in vcodec: score += 15
            else: score += 10
            
            return score
        
        # Sort by score and return best
        scored = [(score_format(fmt), fmt) for fmt in filtered]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored[0][1] if scored else filtered[0]

class PlatformDownloader:
    """Base class for platform-specific downloaders"""
    
    def __init__(self, platform_id: str):
        self.platform_id = platform_id
        self.config = platforms.SUPPORTED_PLATFORMS.get(platform_id)
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @performance_tracked
    async def download(self, url: str, options: Dict[str, Any]) -> DownloadResult:
        """Download media from platform"""
        raise NotImplementedError
    
    async def get_metadata(self, url: str) -> MediaMetadata:
        """Get media metadata without downloading"""
        raise NotImplementedError

class YouTubeDownloader(PlatformDownloader):
    """Advanced YouTube downloader"""
    
    def __init__(self):
        super().__init__('youtube')
        self.ytdl_opts = {
            'format': 'best[height<=1080]/best',
            'writeinfojson': False,
            'writedescription': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': True,
            'embedsubs': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'extractflat': False,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }
    
    @performance_tracked
    async def download(self, url: str, options: Dict[str, Any]) -> DownloadResult:
        """Download from YouTube with advanced options"""
        result = DownloadResult()
        start_time = datetime.now()
        
        try:
            # Configure output options
            output_dir = Path(config.temp_dir) / f"yt_{hashlib.md5(url.encode()).hexdigest()[:8]}"
            await file_manager.ensure_directory(output_dir)
            
            opts = self.ytdl_opts.copy()
            opts.update({
                'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
                'format': self._build_format_selector(options),
            })
            
            # Add progress hook
            progress_data = {'downloaded': 0, 'total': 0}
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    progress_data['downloaded'] = d.get('downloaded_bytes', 0)
                    progress_data['total'] = d.get('total_bytes', 0)
            
            opts['progress_hooks'] = [progress_hook]
            
            # Download with yt-dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                # Fill metadata
                result.metadata = await self._extract_metadata(info)
                
                # Check file size limit
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                if filesize > config.max_file_size_mb * 1024 * 1024:
                    result.error_message = f"فایل بزرگ‌تر از حد مجاز است ({filesize/(1024*1024):.1f} MB)"
                    return result
                
                # Download the file
                ydl.download([url])
                
                # Find downloaded file
                downloaded_files = list(output_dir.glob('*'))
                media_files = [f for f in downloaded_files if f.suffix.lower() in ['.mp4', '.webm', '.mkv', '.mp3', '.m4a']]
                
                if media_files:
                    result.file_path = str(media_files[0])
                    result.success = True
                    
                    # Find thumbnail
                    thumb_files = [f for f in downloaded_files if 'thumb' in f.name.lower()]
                    if thumb_files:
                        result.thumbnail_path = str(thumb_files[0])
                    
                    # Calculate quality score
                    result.quality_score = self._calculate_quality_score(info)
                
        except Exception as e:
            result.error_message = f"خطا در دانلود از یوتیوب: {str(e)}"
            result.error_code = "YOUTUBE_DOWNLOAD_ERROR"
            logger.error(f"YouTube download error: {e}")
        
        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def _build_format_selector(self, options: Dict[str, Any]) -> str:
        """Build format selector based on options"""
        quality = options.get('quality', 'best')
        format_type = options.get('format_type', 'video')
        
        if format_type == 'audio':
            return 'bestaudio[ext=m4a]/bestaudio'
        
        quality_map = {
            '2160p': 'best[height<=2160]',
            '1080p': 'best[height<=1080]',
            '720p': 'best[height<=720]',
            '480p': 'best[height<=480]',
            'best': 'best[height<=1080]',
            'worst': 'worst'
        }
        
        return quality_map.get(quality, 'best[height<=1080]') + '/best'
    
    async def _extract_metadata(self, info: Dict[str, Any]) -> MediaMetadata:
        """Extract comprehensive metadata from yt-dlp info"""
        metadata = MediaMetadata()
        
        # Basic info
        metadata.title = info.get('title', '')
        metadata.description = info.get('description', '')
        metadata.uploader = info.get('uploader', '')
        metadata.uploader_id = info.get('uploader_id', '')
        metadata.platform = 'youtube'
        metadata.platform_id = info.get('id', '')
        metadata.platform_url = info.get('webpage_url', '')
        
        # Timing
        metadata.duration = info.get('duration', 0)
        metadata.upload_date = info.get('upload_date', '')
        if metadata.upload_date:
            try:
                metadata.timestamp = datetime.strptime(metadata.upload_date, '%Y%m%d')
            except ValueError:
                pass
        
        # Social metrics
        metadata.view_count = info.get('view_count', 0)
        metadata.like_count = info.get('like_count', 0)
        metadata.dislike_count = info.get('dislike_count', 0)
        metadata.comment_count = info.get('comment_count', 0)
        metadata.subscriber_count = info.get('channel_follower_count', 0)
        
        # Media properties
        metadata.width = info.get('width', 0)
        metadata.height = info.get('height', 0)
        metadata.fps = info.get('fps', 0)
        metadata.format = info.get('ext', '')
        metadata.thumbnail_url = info.get('thumbnail', '')
        
        # Additional
        metadata.tags = info.get('tags', [])
        metadata.categories = info.get('categories', [])
        metadata.language = info.get('language', '')
        metadata.license = info.get('license', '')
        
        return metadata
    
    def _calculate_quality_score(self, info: Dict[str, Any]) -> int:
        """Calculate quality score (0-100)"""
        score = 50  # Base score
        
        # Resolution bonus
        height = info.get('height', 0)
        if height >= 2160: score += 25  # 4K
        elif height >= 1080: score += 20  # 1080p
        elif height >= 720: score += 15   # 720p
        elif height >= 480: score += 10   # 480p
        
        # Audio quality bonus
        abr = info.get('abr', 0)
        if abr >= 320: score += 15
        elif abr >= 192: score += 10
        elif abr >= 128: score += 5
        
        # Format bonus
        ext = info.get('ext', '').lower()
        if ext == 'mp4': score += 10
        elif ext in ['webm', 'mkv']: score += 5
        
        return min(100, max(0, score))

class InstagramDownloader(PlatformDownloader):
    """Advanced Instagram downloader"""
    
    def __init__(self):
        super().__init__('instagram')
        self.loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            user_agent='Mozilla/5.0 (compatible; InstagramBot/1.0)',
        )
    
    @performance_tracked
    async def download(self, url: str, options: Dict[str, Any]) -> DownloadResult:
        """Download from Instagram"""
        result = DownloadResult()
        start_time = datetime.now()
        
        try:
            # Extract shortcode from URL
            shortcode = self._extract_shortcode(url)
            if not shortcode:
                result.error_message = "لینک اینستاگرام نامعتبر است"
                result.error_code = "INVALID_INSTAGRAM_URL"
                return result
            
            # Get post data
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Fill metadata
            result.metadata = await self._extract_instagram_metadata(post)
            
            # Download media
            output_dir = Path(config.temp_dir) / f"ig_{shortcode}"
            await file_manager.ensure_directory(output_dir)
            
            if post.is_video:
                # Download video
                video_url = post.video_url
                filename = f"instagram_{shortcode}.mp4"
                file_path = output_dir / filename
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(video_url) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in resp.content.iter_chunked(8192):
                                    await f.write(chunk)
                
                result.file_path = str(file_path)
                result.metadata.format = "mp4"
                
            else:
                # Download image
                img_url = post.url
                filename = f"instagram_{shortcode}.jpg"
                file_path = output_dir / filename
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in resp.content.iter_chunked(8192):
                                    await f.write(chunk)
                
                result.file_path = str(file_path)
                result.metadata.format = "jpg"
            
            # Download thumbnail separately
            thumb_url = post.url if not post.is_video else None
            if thumb_url:
                thumb_path = output_dir / f"thumb_{shortcode}.jpg"
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumb_url) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(thumb_path, 'wb') as f:
                                async for chunk in resp.content.iter_chunked(8192):
                                    await f.write(chunk)
                result.thumbnail_path = str(thumb_path)
            
            result.success = True
            result.quality_score = 85  # Instagram generally has good quality
            
        except Exception as e:
            result.error_message = f"خطا در دانلود از اینستاگرام: {str(e)}"
            result.error_code = "INSTAGRAM_DOWNLOAD_ERROR"
            logger.error(f"Instagram download error: {e}")
        
        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def _extract_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL"""
        patterns = [
            r'/p/([A-Za-z0-9_-]+)',
            r'/reel/([A-Za-z0-9_-]+)',
            r'/tv/([A-Za-z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _extract_instagram_metadata(self, post) -> MediaMetadata:
        """Extract Instagram post metadata"""
        metadata = MediaMetadata()
        
        metadata.title = text_processor.truncate_smart(post.caption or "پست اینستاگرام", 100)
        metadata.description = post.caption or ""
        metadata.uploader = post.owner_username
        metadata.uploader_id = str(post.owner_id)
        metadata.platform = 'instagram'
        metadata.platform_id = post.shortcode
        metadata.platform_url = f"https://instagram.com/p/{post.shortcode}/"
        
        metadata.like_count = post.likes
        metadata.comment_count = post.comments
        metadata.timestamp = post.date_utc
        metadata.upload_date = post.date_utc.strftime('%Y%m%d')
        
        if post.is_video:
            metadata.format = "mp4"
            metadata.duration = post.video_duration or 0
        else:
            metadata.format = "jpg"
        
        metadata.thumbnail_url = post.url
        
        return metadata

class SpotifyDownloader(PlatformDownloader):
    """Advanced Spotify downloader (metadata + YouTube search)"""
    
    def __init__(self):
        super().__init__('spotify')
        self.spotify_client = None
        self.youtube_downloader = YouTubeDownloader()
        
        # Initialize Spotify client
        if config.spotify_client_id and config.spotify_client_secret:
            try:
                self.spotify_client = spotipy.Spotify(
                    client_credentials_manager=SpotifyClientCredentials(
                        client_id=config.spotify_client_id,
                        client_secret=config.spotify_client_secret
                    )
                )
            except Exception as e:
                logger.warning(f"Spotify API initialization failed: {e}")
    
    @performance_tracked
    async def download(self, url: str, options: Dict[str, Any]) -> DownloadResult:
        """Download Spotify track via YouTube search"""
        result = DownloadResult()
        start_time = datetime.now()
        
        if not self.spotify_client:
            result.error_message = "Spotify API غیرفعال است"
            result.error_code = "SPOTIFY_API_UNAVAILABLE"
            return result
        
        try:
            # Extract track ID
            track_id = self._extract_track_id(url)
            if not track_id:
                result.error_message = "لینک اسپاتیفای نامعتبر است"
                result.error_code = "INVALID_SPOTIFY_URL"
                return result
            
            # Get track info from Spotify
            track_info = self.spotify_client.track(track_id)
            
            # Build search query
            artists = ', '.join([artist['name'] for artist in track_info['artists']])
            search_query = f"{artists} {track_info['name']} audio"
            
            # Search and download from YouTube
            youtube_url = f"ytsearch1:{search_query}"
            yt_result = await self.youtube_downloader.download(youtube_url, {
                'format_type': 'audio',
                'quality': 'best'
            })
            
            if yt_result.success:
                # Copy YouTube result and enhance with Spotify metadata
                result = yt_result
                result.metadata = await self._extract_spotify_metadata(track_info)
                result.was_converted = True
                result.original_format = "spotify"
                
                # Add ID3 tags
                if result.file_path and result.file_path.endswith('.m4a'):
                    await self._add_id3_tags(result.file_path, track_info)
                
                result.quality_score = 90  # High score for Spotify metadata accuracy
                
            else:
                result = yt_result
                result.error_message = f"ترک در یوتیوب یافت نشد: {yt_result.error_message}"
                result.error_code = "SPOTIFY_TRACK_NOT_FOUND"
        
        except Exception as e:
            result.error_message = f"خطا در دانلود از اسپاتیفای: {str(e)}"
            result.error_code = "SPOTIFY_DOWNLOAD_ERROR"
            logger.error(f"Spotify download error: {e}")
        
        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def _extract_track_id(self, url: str) -> Optional[str]:
        """Extract track ID from Spotify URL"""
        match = re.search(r'/track/([a-zA-Z0-9]+)', url)
        return match.group(1) if match else None
    
    async def _extract_spotify_metadata(self, track_info: Dict) -> MediaMetadata:
        """Extract Spotify track metadata"""
        metadata = MediaMetadata()
        
        metadata.title = track_info['name']
        metadata.uploader = ', '.join([artist['name'] for artist in track_info['artists']])
        metadata.platform = 'spotify'
        metadata.platform_id = track_info['id']
        metadata.platform_url = track_info['external_urls']['spotify']
        
        metadata.duration = track_info['duration_ms'] // 1000
        metadata.format = "mp3"
        
        # Album info
        album = track_info.get('album', {})
        if album:
            metadata.description = f"آلبوم: {album.get('name', '')}"
            metadata.upload_date = album.get('release_date', '').replace('-', '')
            
            if album.get('images'):
                metadata.thumbnail_url = album['images'][0]['url']
        
        # Popularity as quality indicator
        popularity = track_info.get('popularity', 0)
        metadata.like_count = popularity * 100  # Approximate
        
        return metadata
    
    async def _add_id3_tags(self, file_path: str, track_info: Dict):
        """Add ID3 tags to MP3 file"""
        try:
            audio = MP3(file_path, ID3=ID3)
            
            # Add basic tags
            audio.tags.add(TIT2(encoding=3, text=track_info['name']))
            audio.tags.add(TPE1(encoding=3, text=', '.join([artist['name'] for artist in track_info['artists']])))
            
            album = track_info.get('album', {})
            if album:
                audio.tags.add(TALB(encoding=3, text=album.get('name', '')))
                release_date = album.get('release_date', '')
                if release_date:
                    audio.tags.add(TYER(encoding=3, text=release_date[:4]))
            
            # Add album art
            if album and album.get('images'):
                img_url = album['images'][0]['url']
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            img_data = await resp.read()
                            audio.tags.add(APIC(
                                encoding=3,
                                mime='image/jpeg',
                                type=3,
                                desc='Cover',
                                data=img_data
                            ))
            
            audio.save()
            logger.info(f"Added ID3 tags to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to add ID3 tags: {e}")

class UniversalDownloaderEngine:
    """Main downloader engine coordinating all platforms"""
    
    def __init__(self):
        self.downloaders = {
            'youtube': YouTubeDownloader(),
            'instagram': InstagramDownloader(),
            'spotify': SpotifyDownloader(),
        }
        self.quality_selector = QualitySelector()
        self.active_downloads = {}
        self.download_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'by_platform': {},
        }
    
    @performance_tracked
    async def download_media(self, url: str, user_id: int, 
                           options: Dict[str, Any] = None) -> DownloadResult:
        """Main download method with comprehensive error handling"""
        options = options or {}
        download_id = f"{user_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        
        # Check rate limiting
        rate_limit_key = f"download:{user_id}"
        if not await rate_limiter.is_allowed(rate_limit_key):
            result = DownloadResult()
            result.error_message = "تعداد درخواست‌های شما بیش از حد مجاز است"
            result.error_code = "RATE_LIMIT_EXCEEDED"
            return result
        
        # Check if already downloading
        if download_id in self.active_downloads:
            result = DownloadResult()
            result.error_message = "این فایل در حال دانلود است"
            result.error_code = "DOWNLOAD_IN_PROGRESS"
            return result
        
        try:
            self.active_downloads[download_id] = datetime.now()
            
            # Detect platform
            platform = await self._detect_platform(url)
            if not platform:
                result = DownloadResult()
                result.error_message = "پلتفرم پشتیبانی نمی‌شود"
                result.error_code = "UNSUPPORTED_PLATFORM"
                return result
            
            logger.info(f"Starting download from {platform} for user {user_id}: {url}")
            
            # Get platform-specific downloader
            downloader = self.downloaders.get(platform)
            if not downloader:
                # Fallback to yt-dlp for other platforms
                downloader = YouTubeDownloader()
            
            # Perform download
            result = await downloader.download(url, options)
            
            # Update statistics
            self.download_stats['total'] += 1
            if result.success:
                self.download_stats['successful'] += 1
            else:
                self.download_stats['failed'] += 1
            
            platform_stats = self.download_stats['by_platform'].get(platform, {'total': 0, 'successful': 0})
            platform_stats['total'] += 1
            if result.success:
                platform_stats['successful'] += 1
            self.download_stats['by_platform'][platform] = platform_stats
            
            # Cache successful results
            if result.success and config.enable_caching:
                cache_key = f"download_result:{hashlib.md5(url.encode()).hexdigest()}"
                await smart_cache.set(cache_key, json.dumps({
                    'file_path': result.file_path,
                    'metadata': result.metadata.__dict__,
                    'quality_score': result.quality_score,
                    'timestamp': datetime.now().isoformat()
                }), ttl=3600)
            
            logger.info(f"Download completed for {download_id}: success={result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in download_media: {e}")
            result = DownloadResult()
            result.error_message = f"خطای غیرمنتظره: {str(e)}"
            result.error_code = "UNEXPECTED_ERROR"
            return result
            
        finally:
            self.active_downloads.pop(download_id, None)
    
    async def _detect_platform(self, url: str) -> Optional[str]:
        """Enhanced platform detection"""
        # Check cache first
        cache_key = f"platform_detect:{hashlib.md5(url.encode()).hexdigest()}"
        cached = await smart_cache.get(cache_key)
        if cached:
            return cached
        
        # Use platform manager
        platform = platforms.get_platform_by_url(url)
        
        # Cache result
        if platform:
            await smart_cache.set(cache_key, platform, ttl=86400)  # 24 hours
        
        return platform
    
    async def get_media_info(self, url: str) -> Optional[MediaMetadata]:
        """Get media information without downloading"""
        platform = await self._detect_platform(url)
        if not platform:
            return None
        
        downloader = self.downloaders.get(platform)
        if not downloader:
            return None
        
        try:
            return await downloader.get_metadata(url)
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return None
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        return self.download_stats.copy()
    
    async def cleanup_temp_files(self):
        """Clean up temporary download files"""
        try:
            await file_manager.cleanup_old_files(config.temp_dir, max_age_hours=1)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

# Global downloader instance
downloader = UniversalDownloaderEngine()

# Export main classes
__all__ = [
    'MediaMetadata', 'DownloadResult', 'UniversalDownloaderEngine',
    'YouTubeDownloader', 'InstagramDownloader', 'SpotifyDownloader',
    'downloader'
]
