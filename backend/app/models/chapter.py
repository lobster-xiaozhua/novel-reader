from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


def _utc_now():
    return datetime.now(timezone.utc)


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), index=True, nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utc_now)

    book = relationship("Book", back_populates="chapters")
