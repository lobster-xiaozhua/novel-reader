from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


def _utc_now():
    return datetime.now(timezone.utc)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), index=True, nullable=False)
    author = Column(String(100), index=True, nullable=True)
    folder_path = Column(String(500), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    total_chapters = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    chapters = relationship("Chapter", back_populates="book", order_by="Chapter.chapter_number")
