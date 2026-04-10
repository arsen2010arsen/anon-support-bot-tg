from datetime import datetime
from sqlalchemy import BigInteger, Integer, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class BannedUser(Base):
    """Stores users who have been banned from using the bot."""
    __tablename__ = "banned_users"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

class Session(Base):
    """Tracks active support sessions between a user and potentially an admin."""
    __tablename__ = "sessions"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=True) # Null if unclaimed
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AdminState(Base):
    """Tracks the currently 'focused' session for a specific admin to enable standalone messaging."""
    __tablename__ = "admin_state"
    
    admin_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    active_user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

class MessageMap(Base):
    """Maps forwarded messages in the admin's DM to the original user's message."""
    __tablename__ = "message_map"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_message_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_message_id: Mapped[int] = mapped_column(Integer)
