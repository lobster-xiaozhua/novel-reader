from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.database import Base


class CrawlerTask(Base):
    __tablename__ = "crawler_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    url = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    total_chapters = Column(Integer, default=0)
    downloaded_chapters = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
