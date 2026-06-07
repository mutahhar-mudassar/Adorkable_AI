

import asyncio
from datetime import datetime, date
from typing import Optional, List, AsyncGenerator
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, ForeignKey,
    Index, JSON, create_engine, select, text,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)

from backend.config import DATABASE_URL


# =============================================================================
# Database Engine & Session Setup
# =============================================================================

# Convert SQLite URL to async version
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# =============================================================================
# Base Model
# =============================================================================

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# =============================================================================
# User Model
# =============================================================================

class User(Base):
    """
    User account model.
    
    Attributes:
        id: Primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        gender: User's gender for clothing recommendations
        city: City for weather-based recommendations
        created_at: Account creation timestamp
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )
    wardrobe_items: Mapped[List["GarmentItem"]] = relationship(
        "GarmentItem", back_populates="user", cascade="all, delete-orphan"
    )
    outfit_logs: Mapped[List["OutfitLog"]] = relationship(
        "OutfitLog", back_populates="user", cascade="all, delete-orphan"
    )


# =============================================================================
# User Profile Model
# =============================================================================

class UserProfile(Base):
    """
    User's fashion profile including skin tone and body shape analysis.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        skin_tone: Fair, Medium, or Dark
        skin_undertone: Warm, Cool, or Neutral
        body_shape: Hourglass, Pear, Inverted Triangle, Rectangle, Apple, Athletic
        selfie_path: Path to uploaded selfie image
        body_photo_path: Path to uploaded full-body photo
        updated_at: Last update timestamp
    """
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    skin_tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    skin_undertone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    body_shape: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    selfie_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")


# =============================================================================
# Garment Item Model
# =============================================================================

class GarmentItem(Base):
    """
    Individual clothing item in user's wardrobe.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        image_path: Path to uploaded garment image
        category: Clothing category (top, bottom, dress, etc.)
        style: Clothing style (casual, formal, etc.)
        dominant_color: Fashion color name (e.g., "Navy Blue")
        color_hex: Hex color code (e.g., "#000080")
        fabric_weight: Light, medium, or heavy fabric weight
        occasion_tags: JSON list of suitable occasions
        wear_count: Number of times garment has been worn
        last_worn: Date last worn
        uploaded_at: Upload timestamp
    """
    __tablename__ = "garment_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    style: Mapped[str] = mapped_column(String(50), nullable=False)
    dominant_color: Mapped[str] = mapped_column(String(100), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=False)  # #RRGGBB
    fabric_weight: Mapped[str] = mapped_column(String(20), nullable=False)
    occasion_tags: Mapped[str] = mapped_column(String(500), default="[]")  # JSON string
    gender_fit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    wear_count: Mapped[int] = mapped_column(Integer, default=0)
    last_worn: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wardrobe_items")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_garment_user_category", "user_id", "category"),
    )
    
    def get_occasion_tags_list(self) -> List[str]:
        """Parse occasion_tags JSON string to list."""
        import json
        try:
            return json.loads(self.occasion_tags)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_occasion_tags_list(self, tags: List[str]) -> None:
        """Set occasion_tags from list."""
        import json
        self.occasion_tags = json.dumps(tags)


# =============================================================================
# Outfit Log Model
# =============================================================================

class OutfitLog(Base):
    """
    Log of outfits recommended and worn by the user.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        top_id: Foreign key to top garment (optional)
        bottom_id: Foreign key to bottom garment (optional)
        dress_id: Foreign key to dress garment (optional)
        outerwear_id: Foreign key to outerwear (optional)
        occasion: Occasion for which outfit was recommended
        score: Outfit recommendation score (0-105)
        trending_badge: Whether outfit included trending items
        worn_date: Date the outfit was worn
        created_at: Log creation timestamp
    """
    __tablename__ = "outfit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    top_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("garment_items.id", ondelete="SET NULL"), nullable=True
    )
    bottom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("garment_items.id", ondelete="SET NULL"), nullable=True
    )
    dress_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("garment_items.id", ondelete="SET NULL"), nullable=True
    )
    outerwear_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("garment_items.id", ondelete="SET NULL"), nullable=True
    )
    occasion: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    trending_badge: Mapped[bool] = mapped_column(Boolean, default=False)
    worn_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="outfit_logs")
    top: Mapped[Optional["GarmentItem"]] = relationship(
        "GarmentItem", foreign_keys=[top_id], lazy="selectin"
    )
    bottom: Mapped[Optional["GarmentItem"]] = relationship(
        "GarmentItem", foreign_keys=[bottom_id], lazy="selectin"
    )
    dress: Mapped[Optional["GarmentItem"]] = relationship(
        "GarmentItem", foreign_keys=[dress_id], lazy="selectin"
    )
    outerwear: Mapped[Optional["GarmentItem"]] = relationship(
        "GarmentItem", foreign_keys=[outerwear_id], lazy="selectin"
    )


# =============================================================================
# Database Management Functions
# =============================================================================

def _sqlite_migrate_garment_items(sync_conn) -> None:
    """Add columns missing from older SQLite DBs (create_all does not ALTER)."""
    result = sync_conn.execute(text("PRAGMA table_info(garment_items)"))
    cols = {row[1] for row in result.fetchall()}
    if "gender_fit" not in cols:
        sync_conn.execute(
            text("ALTER TABLE garment_items ADD COLUMN gender_fit VARCHAR(50)")
        )


async def create_all_tables() -> None:
    """
    Create all database tables.
    
    Call this on application startup to ensure all tables exist.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if ASYNC_DATABASE_URL.startswith("sqlite"):
            await conn.run_sync(_sqlite_migrate_garment_items)
    print("Database tables created")


async def drop_all_tables() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data. Use with caution.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("All database tables dropped")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator for database sessions.
    
    Use as FastAPI dependency:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Helper Functions
# =============================================================================

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    """Get user profile by user ID."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_wardrobe(db: AsyncSession, user_id: int) -> List[GarmentItem]:
    """Get all wardrobe items for a user."""
    result = await db.execute(
        select(GarmentItem)
        .where(GarmentItem.user_id == user_id)
        .order_by(GarmentItem.uploaded_at.desc())
    )
    return result.scalars().all()


async def get_garment_by_id(db: AsyncSession, item_id: int) -> Optional[GarmentItem]:
    """Get garment item by ID."""
    result = await db.execute(
        select(GarmentItem).where(GarmentItem.id == item_id)
    )
    return result.scalar_one_or_none()


# backend/database.py generated — Adorkable AI
