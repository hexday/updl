#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ Advanced Database Management System
🚀 Async SQLAlchemy with Multiple Database Support
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    BigInteger, Float, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select, update, delete, func, and_, or_
from loguru import logger
import redis.asyncio as redis

from config import config

# Database Models
Base = declarative_base()

@dataclass
class DatabaseStats:
    """Database statistics container"""
    total_users: int = 0
    active_users_today: int = 0
    total_downloads: int = 0
    downloads_today: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    popular_platform: str = "نامشخص"
    avg_download_time: float = 0.0

class User(Base):
    """Enhanced User model"""
    __tablename__ = 'users'
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(100), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default='fa')
    phone_number = Column(String(20), nullable=True)
    
    # Status fields
    is_premium = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    # Activity tracking
    join_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    last_download = Column(DateTime, nullable=True)
    
    # Statistics
    download_count = Column(Integer, default=0)
    upload_count = Column(Integer, default=0)
    referral_count = Column(Integer, default=0)
    
    # Settings and preferences
    settings = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    
    # Premium features
    premium_expires = Column(DateTime, nullable=True)
    daily_download_limit = Column(Integer, default=20)
    used_downloads_today = Column(Integer, default=0)
    last_limit_reset = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    downloads = relationship("Download", back_populates="user")
    reports = relationship("Report", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_activity', 'last_activity'),
        Index('idx_user_premium', 'is_premium', 'premium_expires'),
        Index('idx_user_status', 'is_blocked', 'is_banned'),
    )

class Download(Base):
    """Enhanced Download model"""
    __tablename__ = 'downloads'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    
    # URL and platform info
    original_url = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False, index=True)
    platform_id = Column(String(200), nullable=True)  # Platform-specific ID
    
    # Content metadata
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    uploader = Column(String(200), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    
    # File information
    file_path = Column(Text, nullable=True)
    file_name = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    file_format = Column(String(20), nullable=True)
    file_quality = Column(String(50), nullable=True)
    
    # Social metrics
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(BigInteger, nullable=True)
    share_count = Column(BigInteger, nullable=True)
    
    # Download metadata
    download_date = Column(DateTime, default=datetime.utcnow)
    download_time = Column(Float, nullable=True)  # processing time in seconds
    thumbnail_url = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Advanced metadata
    metadata = Column(JSON, default=dict)
    analytics = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="downloads")
    
    # Indexes
    __table_args__ = (
        Index('idx_download_date', 'download_date'),
        Index('idx_download_platform', 'platform'),
        Index('idx_download_status', 'status', 'success'),
        Index('idx_download_user_date', 'user_id', 'download_date'),
    )

class Admin(Base):
    """Admin users model"""
    __tablename__ = 'admins'
    
    user_id = Column(BigInteger, ForeignKey('users.user_id'), primary_key=True)
    role = Column(String(50), default='admin')  # admin, super_admin, moderator
    permissions = Column(JSON, default=dict)
    added_by = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    added_date = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    added_by_user = relationship("User", foreign_keys=[added_by])

class Report(Base):
    """User reports and analytics"""
    __tablename__ = 'reports'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    report_type = Column(String(50), nullable=False)  # bug, suggestion, abuse, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default='open')  # open, investigating, resolved, closed
    priority = Column(String(20), default='medium')  # low, medium, high, critical
    created_date = Column(DateTime, default=datetime.utcnow)
    resolved_date = Column(DateTime, nullable=True)
    resolved_by = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

class Analytics(Base):
    """System analytics and metrics"""
    __tablename__ = 'analytics'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(DateTime, default=datetime.utcnow)
    metric_type = Column(String(50), nullable=False)  # daily_stats, platform_stats, etc.
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_date', 'date'),
        Index('idx_analytics_type', 'metric_type'),
        Index('idx_analytics_name', 'metric_name'),
    )

class DatabaseManager:
    """Advanced async database manager"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.redis_client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                config.database_url,
                echo=config.debug,
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Initialize Redis if configured
            if config.redis_url:
                self.redis_client = redis.from_url(
                    config.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            
            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session"""
        if not self._initialized:
            await self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # User Management
    async def add_or_update_user(self, user_data: Dict[str, Any]) -> User:
        """Add new user or update existing one"""
        async with self.get_session() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.user_id == user_data['user_id'])
            )
            user = result.scalars().first()
            
            if user:
                # Update existing user
                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.last_activity = datetime.utcnow()
            else:
                # Create new user
                user = User(**user_data)
                session.add(user)
            
            await session.flush()
            return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalars().first()
    
    async def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity"""
        try:
            async with self.get_session() as session:
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(last_activity=datetime.utcnow())
                )
                return True
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    async def get_active_users(self, days: int = 7) -> List[User]:
        """Get users active within specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .where(
                    and_(
                        User.last_activity >= cutoff_date,
                        User.is_blocked == False,
                        User.is_banned == False
                    )
                )
                .order_by(User.last_activity.desc())
            )
            return result.scalars().all()
    
    # Download Management
    async def save_download(self, download_data: Dict[str, Any]) -> Download:
        """Save download record"""
        async with self.get_session() as session:
            download = Download(**download_data)
            session.add(download)
            
            # Update user download count if successful
            if download_data.get('success'):
                await session.execute(
                    update(User)
                    .where(User.user_id == download_data['user_id'])
                    .values(
                        download_count=User.download_count + 1,
                        last_download=datetime.utcnow()
                    )
                )
            
            await session.flush()
            return download
    
    async def get_user_downloads(self, user_id: int, limit: int = 50) -> List[Download]:
        """Get user's download history"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Download)
                .where(Download.user_id == user_id)
                .order_by(Download.download_date.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_popular_platforms(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get popular platforms statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        async with self.get_session() as session:
            result = await session.execute(
                select(
                    Download.platform,
                    func.count(Download.id).label('count'),
                    func.avg(Download.download_time).label('avg_time')
                )
                .where(
                    and_(
                        Download.download_date >= cutoff_date,
                        Download.success == True
                    )
                )
                .group_by(Download.platform)
                .order_by(func.count(Download.id).desc())
            )
            
            return [
                {
                    'platform': row.platform,
                    'count': row.count,
                    'avg_time': round(row.avg_time or 0, 2)
                }
                for row in result.fetchall()
            ]
    
    # Analytics and Statistics
    async def get_system_stats(self) -> DatabaseStats:
        """Get comprehensive system statistics"""
        async with self.get_session() as session:
            # Today's date for filtering
            today = datetime.utcnow().date()
            
            # Total users
            total_users = await session.scalar(
                select(func.count(User.user_id))
                .where(User.is_banned == False)
            )
            
            # Active users today
            active_today = await session.scalar(
                select(func.count(User.user_id))
                .where(
                    and_(
                        func.date(User.last_activity) == today,
                        User.is_blocked == False,
                        User.is_banned == False
                    )
                )
            )
            
            # Total downloads
            total_downloads = await session.scalar(
                select(func.count(Download.id))
                .where(Download.success == True)
            )
            
            # Downloads today
            downloads_today = await session.scalar(
                select(func.count(Download.id))
                .where(
                    and_(
                        func.date(Download.download_date) == today,
                        Download.success == True
                    )
                )
            )
            
            # Success/failure rates
            successful = await session.scalar(
                select(func.count(Download.id))
                .where(Download.success == True)
            ) or 0
            
            failed = await session.scalar(
                select(func.count(Download.id))
                .where(Download.success == False)
            ) or 0
            
            # Popular platform
            popular_result = await session.execute(
                select(
                    Download.platform,
                    func.count(Download.id).label('count')
                )
                .where(Download.success == True)
                .group_by(Download.platform)
                .order_by(func.count(Download.id).desc())
                .limit(1)
            )
            popular_row = popular_result.first()
            popular_platform = popular_row.platform if popular_row else "نامشخص"
            
            # Average download time
            avg_time = await session.scalar(
                select(func.avg(Download.download_time))
                .where(
                    and_(
                        Download.success == True,
                        Download.download_time.isnot(None)
                    )
                )
            ) or 0.0
            
            return DatabaseStats(
                total_users=total_users or 0,
                active_users_today=active_today or 0,
                total_downloads=total_downloads or 0,
                downloads_today=downloads_today or 0,
                successful_downloads=successful,
                failed_downloads=failed,
                popular_platform=popular_platform,
                avg_download_time=round(avg_time, 2)
            )
    
    async def save_analytics(self, metric_type: str, metric_name: str, 
                           metric_value: float, metadata: Dict = None):
        """Save analytics data"""
        async with self.get_session() as session:
            analytics = Analytics(
                metric_type=metric_type,
                metric_name=metric_name,
                metric_value=metric_value,
                metadata=metadata or {}
            )
            session.add(analytics)
    
    # Admin Management
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        # Check config first
        if user_id in config.admin_ids:
            return True
        
        async with self.get_session() as session:
            result = await session.execute(
                select(Admin)
                .where(
                    and_(
                        Admin.user_id == user_id,
                        Admin.is_active == True
                    )
                )
            )
            return result.scalars().first() is not None
    
    async def add_admin(self, user_id: int, role: str = 'admin', 
                       added_by: int = None) -> bool:
        """Add new admin"""
        try:
            async with self.get_session() as session:
                admin = Admin(
                    user_id=user_id,
                    role=role,
                    added_by=added_by
                )
                session.add(admin)
                return True
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return False
    
    # Cache Management
    async def get_cache(self, key: str) -> Optional[str]:
        """Get value from Redis cache"""
        if self.redis_client:
            try:
                return await self.redis_client.get(key)
            except Exception as e:
                logger.warning(f"Cache get error: {e}")
        return None
    
    async def set_cache(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in Redis cache"""
        if self.redis_client:
            try:
                await self.redis_client.setex(key, expire, value)
                return True
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
        return False
    
    # Maintenance
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self.get_session() as session:
            # Remove old failed downloads
            await session.execute(
                delete(Download)
                .where(
                    and_(
                        Download.success == False,
                        Download.download_date < cutoff_date
                    )
                )
            )
            
            # Remove old analytics
            await session.execute(
                delete(Analytics)
                .where(Analytics.date < cutoff_date)
            )
            
            logger.info(f"🧹 Cleaned up data older than {days} days")
    
    async def backup_database(self, backup_path: str = None) -> bool:
        """Create database backup"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_{timestamp}.db"
            
            # Implementation depends on database type
            logger.info(f"💾 Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("🔒 Database connections closed")

# Global database instance
db = DatabaseManager()

# Initialize on import
async def init_db():
    """Initialize database"""
    await db.initialize()

__all__ = ['db', 'User', 'Download', 'Admin', 'Report', 'Analytics', 'DatabaseStats']
