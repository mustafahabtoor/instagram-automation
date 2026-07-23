from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from database import Base

class ConfigModel(Base):
    __tablename__ = "configs"
    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, nullable=False)
    page_id = Column(String, nullable=False)
    instagram_business_account_id = Column(String, nullable=False)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True, nullable=False)
    keywords = Column(Text, nullable=False)  # Comma-separated keywords
    comment_reply = Column(Text, nullable=False)
    dm_message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

class ProcessedComment(Base):
    __tablename__ = "processed_comments"
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
